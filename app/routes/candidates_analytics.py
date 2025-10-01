from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import Dict, Any, Optional, List
from datetime import date
from urllib.parse import unquote

from .. import models
from ..database import get_db
from ..schemas import PaginatedCandidateStageDetails, CandidateStageDetail, CandidateStageDepartmentBreakdownResponse, DemandSupplyDepartmentBreakdownItem

router = APIRouter(
    prefix="/analytics",
    tags=["Candidates Analytics"],
    responses={404: {"description": "Not found"}},
)

@router.get("/candidates/stages/count", response_model=Dict[str, Any])
def get_candidate_stage_counts(
    db: Session = Depends(get_db),
    department: Optional[str] = Query(None, description="Filter by department name"),
    from_date: Optional[date] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)"),
    overall: bool = Query(False, description="Set to true to get overall metrics across all departments")
):
    """
    Get the count of candidates for specific stages with optional filtering:
    1. Total candidates created
    2. Pending (not assigned to a job)
    3. In Progress (assigned to a job, up to docs upload)
    4. Offered (offer email sent)
    5. Onboarded (has an employee ID)
    
    Query Parameters:
    - department: Filter by specific department name
    - from_date: Start date for filtering (format: YYYY-MM-DD)
    - to_date: End date for filtering (format: YYYY-MM-DD)
    - overall: Set to true to get metrics across all departments
    """
    # Base query for all candidates
    base_query = db.query(models.Candidate)
    
    # Apply date filters if provided
    if from_date and to_date:
        base_query = base_query.filter(models.Candidate.application_date.between(from_date, to_date))
    elif from_date:
        base_query = base_query.filter(models.Candidate.application_date >= from_date)
    elif to_date:
        base_query = base_query.filter(models.Candidate.application_date <= to_date)
    
    # Apply department filter if provided and not overall
    if department and not overall:
        # Join with Job table to also filter by job department
        department_filtered_query = base_query.outerjoin(models.Job, models.Candidate.associated_job_id == models.Job.job_id).filter(
            or_(
                models.Candidate.department.ilike(f"%{department}%"),
                models.Job.department.ilike(f"%{department}%")
            )
        )
        base_query = department_filtered_query

    # 1. No of candidates created
    total_candidates_count = base_query.with_entities(models.Candidate.candidate_id).count()

    # 2. Pending (not assigned to job id)
    pending_count = base_query.filter(models.Candidate.associated_job_id.is_(None)).count()

    # 3. Onboarded (associated with an employee record)
    onboarded_count = base_query.join(models.Employee).count()

    # 4. Offered (status is 'Offer Initiated')
    # Case-insensitive check for status.
    offered_count = base_query.filter(func.lower(models.Candidate.current_status) == 'offer initiated').count()

    # 5. In Progress
    onboarded_candidate_ids = db.query(models.Employee.candidate_id).subquery()

    # Statuses to exclude from 'In Progress'
    excluded_statuses = [
        'Offer Initiated', 'Offer Declined', 'Onboarded', 'Rejected', 'Screening Rejected'
    ]
    excluded_statuses_lower = [s.lower() for s in excluded_statuses]

    in_progress_count = base_query.filter(
        models.Candidate.associated_job_id.isnot(None),
        models.Candidate.candidate_id.notin_(onboarded_candidate_ids),
        func.lower(models.Candidate.current_status).notin_(excluded_statuses_lower)
    ).count()

    result = {
        "All Candidates": {"count": total_candidates_count, "weight": 1},
        "Pending": {"count": pending_count, "weight": 2},
        "In Progress": {"count": in_progress_count, "weight": 3},
        "Offered": {"count": offered_count, "weight": 4},
        "Onboarded": {"count": onboarded_count, "weight": 5},
    }

    return result

def _build_candidate_analytics_query(
    db: Session,
    status: str,
    search: Optional[str] = None,
    department: Optional[str] = None
):
    """Helper function to build the base query for candidate analytics with filters."""
    # Base query - join candidates with jobs to get job details
    base_query = (
        db.query(
            models.Candidate.candidate_id.label("candidate_id"),
            models.Candidate.candidate_name.label("candidate_name"),
            models.Candidate.associated_job_id.label("associated_job_id"),
            models.Candidate.department.label('candidate_department'),
            models.Candidate.current_status.label("current_status"),
            models.Job.job_title.label("job_title"),
            models.Job.department.label('job_department')
        )
        .outerjoin(models.Job, models.Candidate.associated_job_id == models.Job.job_id)
    )

    # Apply status filter
    if status == "All Candidates":
        # No additional filter needed
        pass
    elif status == "Pending":
        base_query = base_query.filter(models.Candidate.associated_job_id.is_(None))
    elif status == "Onboarded":
        base_query = base_query.join(models.Employee, models.Candidate.candidate_id == models.Employee.candidate_id)
    elif status == "Offered":
        base_query = base_query.filter(func.lower(models.Candidate.current_status) == 'offer initiated')
    elif status == "In Progress":
        onboarded_candidate_ids = db.query(models.Employee.candidate_id).subquery()
        excluded_statuses = [
            'Offer Initiated', 'Offer Declined', 'Onboarded', 'Rejected', 'Screening Rejected'
        ]
        excluded_statuses_lower = [s.lower() for s in excluded_statuses]
        base_query = base_query.filter(
            models.Candidate.associated_job_id.isnot(None),
            models.Candidate.candidate_id.notin_(onboarded_candidate_ids),
            func.lower(models.Candidate.current_status).notin_(excluded_statuses_lower)
        )
    else:
        # Fallback for any other status to maintain backward compatibility
        base_query = base_query.filter(models.Candidate.current_status == status)

    # Apply filters
    filters_applied = {"status": status}
    
    if search:
        search_filter = or_(
            models.Candidate.candidate_name.ilike(f"%{search}%"),
            models.Job.job_title.ilike(f"%{search}%"),
            models.Candidate.department.ilike(f"%{search}%"),
            models.Job.department.ilike(f"%{search}%")
        )
        base_query = base_query.filter(search_filter)
        filters_applied["search"] = search
    
    if department:
        # Filter by candidate department or job department
        department_filter = or_(
            models.Candidate.department.ilike(f"%{department}%"),
            models.Job.department.ilike(f"%{department}%")
        )
        base_query = base_query.filter(department_filter)
        filters_applied["department"] = department
    
    return base_query, filters_applied

@router.get("/candidates/stages/details", response_model=PaginatedCandidateStageDetails)
def get_candidate_stage_details(
    status: str = Query(..., description="The current status to filter candidates by"),
    page: int = Query(1, ge=1, description="Page number"),
    items_per_page: int = Query(10, ge=1, le=100, description="Number of items per page"),
    search: Optional[str] = Query(None, description="Search term for candidate name, job title, or department"),
    department: Optional[str] = Query(None, description="Filter by department name"),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about candidates in a specific stage/status with filtering and pagination.
    
    The status can be one of: 'All Candidates', 'Pending', 'In Progress', 'Offered', 'Onboarded'.
    Returns candidate ID, name, associated job, job ID, and department.
    Supports pagination, search, and department filtering.
    
    Query Parameters:
    - status: Required status to filter by
    - page: Page number (starts from 1) 
    - items_per_page: Number of items per page (1-100)
    - search: Search term for candidate name, job title, or department
    - department: Filter by specific department name
    """
    try:
        # Pagination validation
        if page <= 0:
            raise HTTPException(status_code=400, detail="Page number must be positive.")
        if items_per_page <= 0 or items_per_page > 100:
            raise HTTPException(status_code=400, detail="Items per page must be between 1 and 100.")

        # Build base query with filters
        base_query, filters_applied = _build_candidate_analytics_query(db, status, search, department)

        # Get total count
        total_count = base_query.count()

        # Apply pagination
        offset = (page - 1) * items_per_page
        candidates_data = (
            base_query
            .offset(offset)
            .limit(items_per_page)
            .all()
        )

        # Transform the data
        candidates_list = []
        for candidate_data in candidates_data:
            candidates_list.append(CandidateStageDetail(
                candidate_id=getattr(candidate_data, 'candidate_id', None),
                candidate_name=getattr(candidate_data, 'candidate_name', None),
                associated_job_id=getattr(candidate_data, 'associated_job_id', None),
                job_title=getattr(candidate_data, 'job_title', None),
                department=getattr(candidate_data, 'candidate_department', None) or getattr(candidate_data, 'job_department', None),
                current_status=getattr(candidate_data, 'current_status', None)
            ))

        return PaginatedCandidateStageDetails(
            total=total_count,
            page=page,
            items_per_page=items_per_page,
            status=status,
            items=candidates_list,
            filter_applied=filters_applied
        )
        
    except HTTPException:
        # Re-raise HTTPExceptions (like 400)
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/candidates/stages/details/download", response_model=List[CandidateStageDetail])
def get_candidate_stage_details_download(
    status: str = Query(..., description="The current status to filter candidates by"),
    search: Optional[str] = Query(None, description="Search term for candidate name, job title, or department"),
    department: Optional[str] = Query(None, description="Filter by department name"),
    db: Session = Depends(get_db)
):
    """
    Download detailed candidate stage data with filtering (no pagination).
    
    The status can be one of: 'All Candidates', 'Pending', 'In Progress', 'Offered', 'Onboarded'.
    Returns candidate ID, name, associated job, job ID, and department.
    
    Query Parameters:
    - status: Required status to filter by
    - search: Search term for candidate name, job title, or department
    - department: Filter by specific department name
    """
    try:
        base_query, _ = _build_candidate_analytics_query(db, status, search, department)
        candidates_data = base_query.all()
        
        # Transform data
        result = [
            CandidateStageDetail(
                candidate_id=getattr(c, 'candidate_id', None),
                candidate_name=getattr(c, 'candidate_name', None),
                associated_job_id=getattr(c, 'associated_job_id', None),
                job_title=getattr(c, 'job_title', None),
                department=getattr(c, 'candidate_department', None) or getattr(c, 'job_department', None),
                current_status=getattr(c, 'current_status', None),
            ) for c in candidates_data
        ]
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/candidates/stages/{stage_name}/department-breakdown", response_model=CandidateStageDepartmentBreakdownResponse)
def get_candidate_stage_department_breakdown(
    stage_name: str,
    department: Optional[str] = Query(None, description="Filter by specific department"),
    from_date: Optional[date] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)"),
    overall: Optional[str] = Query(None, description="When set to 'true', returns data for all departments"),
    db: Session = Depends(get_db)
):
    """
    Get department-wise breakdown of candidates in a specific stage.
    
    Dynamic endpoint that accepts any stage name and returns count of candidates
    in that stage grouped by department with percentage calculations.
    
    Examples:
    - /analytics/candidates/stages/Screening/department-breakdown
    - /analytics/candidates/stages/Yet%20to%20call/department-breakdown
    - /analytics/candidates/stages/In%20Pipeline/department-breakdown
    
    Query Parameters:
    - department: Filter by specific department name
    - from_date: Start date filter (YYYY-MM-DD)
    - to_date: End date filter (YYYY-MM-DD)  
    - overall: When set to 'true', returns data for all departments
    """
    try:
        # URL decode the stage name to handle special characters and spaces
        decoded_stage_name = unquote(stage_name)
        
        # Build the base query to get candidates with their departments
        base_query = (
            db.query(
                models.Candidate.candidate_id,
                models.Candidate.department.label('candidate_department'),
                models.Job.department.label('job_department')
            )
            .outerjoin(models.Job, models.Candidate.associated_job_id == models.Job.job_id)
        )
        
        # Apply stage filter using the same logic as the existing analytics
        if decoded_stage_name == "All Candidates":
            # No additional filter needed
            pass
        elif decoded_stage_name == "Pending":
            base_query = base_query.filter(models.Candidate.associated_job_id.is_(None))
        elif decoded_stage_name == "Onboarded":
            base_query = base_query.join(models.Employee, models.Candidate.candidate_id == models.Employee.candidate_id)
        elif decoded_stage_name == "Offered":
            base_query = base_query.filter(func.lower(models.Candidate.current_status) == 'offer initiated')
        elif decoded_stage_name == "In Progress":
            onboarded_candidate_ids = db.query(models.Employee.candidate_id).subquery()
            excluded_statuses = [
                'Offer Initiated', 'Offer Declined', 'Onboarded', 'Rejected', 'Screening Rejected'
            ]
            excluded_statuses_lower = [s.lower() for s in excluded_statuses]
            base_query = base_query.filter(
                models.Candidate.associated_job_id.isnot(None),
                models.Candidate.candidate_id.notin_(onboarded_candidate_ids),
                func.lower(models.Candidate.current_status).notin_(excluded_statuses_lower)
            )
        else:
            # For any other stage name, try to match as direct status
            stage_filter = or_(
                models.Candidate.current_status == decoded_stage_name,
                func.lower(models.Candidate.current_status) == decoded_stage_name.lower()
            )
            base_query = base_query.filter(stage_filter)
        
        # Apply date filters if provided
        if from_date:
            base_query = base_query.filter(
                or_(
                    models.Candidate.status_updated_on >= from_date,
                    models.Candidate.application_date >= from_date
                )
            )
        
        if to_date:
            base_query = base_query.filter(
                or_(
                    models.Candidate.status_updated_on <= to_date,
                    models.Candidate.application_date <= to_date
                )
            )
        
        # Apply department filter if provided and not 'overall'
        if department and overall != 'true':
            department_filter = or_(
                models.Candidate.department.ilike(f"%{department}%"),
                models.Job.department.ilike(f"%{department}%")
            )
            base_query = base_query.filter(department_filter)
        
        # Get all candidates matching the criteria
        candidates_data = base_query.all()
        
        # Count candidates by department
        department_counts = {}
        total_count = 0
        
        for candidate_data in candidates_data:
            # Use job department if available, otherwise candidate department
            dept = candidate_data.job_department or candidate_data.candidate_department or "Unspecified"
            
            if dept not in department_counts:
                department_counts[dept] = 0
            department_counts[dept] += 1
            total_count += 1
        
        # Handle case where no candidates found for the stage
        if total_count == 0:
            # Valid stage names that are logical groupings (don't need database validation)
            valid_logical_stages = ["All Candidates", "Pending", "In Progress", "Offered", "Onboarded"]
            
            if decoded_stage_name not in valid_logical_stages:
                # Check if the stage name exists at all in the database as a direct status
                stage_exists = db.query(models.Candidate).filter(
                    or_(
                        models.Candidate.current_status == decoded_stage_name,
                        func.lower(models.Candidate.current_status) == decoded_stage_name.lower()
                    )
                ).first()
                
                if not stage_exists:
                    raise HTTPException(
                        status_code=404, 
                        detail=f"Stage '{decoded_stage_name}' not found. Please check the stage name and try again."
                    )
            
            return CandidateStageDepartmentBreakdownResponse(
                total=0,
                departments=0,
                stage_name=decoded_stage_name,
                breakdown=[]
            )
        
        # Create breakdown list with percentages
        breakdown = []
        for dept, count in department_counts.items():
            percentage = round((count / total_count) * 100, 1) if total_count > 0 else 0
            breakdown.append(DemandSupplyDepartmentBreakdownItem(
                department=dept,
                count=count,
                percentage=percentage
            ))
        
        # Sort by count in descending order
        breakdown.sort(key=lambda x: x.count, reverse=True)
        
        return CandidateStageDepartmentBreakdownResponse(
            total=total_count,
            departments=len(department_counts),
            stage_name=decoded_stage_name,
            breakdown=breakdown
        )
        
    except HTTPException:
        # Re-raise HTTPExceptions (like 404)
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") 