from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, case
from typing import Optional, List, Generic, TypeVar, Union
from datetime import datetime, date
from pydantic import BaseModel, Field
from enum import Enum

from app.models import Job, Candidate, Department
from app.database import get_db
from app import schemas

router = APIRouter(prefix="/job-stats", tags=["Job Statistics"])

# Generic type for paginated response data
T = TypeVar('T')

class JobListItem(BaseModel):
    """Schema for a single job item in a list response."""
    id: int
    job_id: str
    job_title: str
    department: str
    status: str
    no_of_positions: int
    created_on: datetime

    class Config:
        from_attributes = True

class PositionListItem(BaseModel):
    """Schema for a position-focused list item."""
    id: int
    job_title: str
    department: str
    status: str
    no_of_positions: int

    class Config:
        from_attributes = True

class PaginatedResponse(BaseModel, Generic[T]):
    """Generic schema for a paginated response."""
    data: List[T]
    total_items: int
    total_pages: int
    page: int
    page_size: int
    filter_applied: dict

class JobStatsResponse(BaseModel):
    """Response schema for job statistics"""
    # Total Jobs
    total_jobs_active: int
    total_jobs_past: int
    total_jobs_overall: int
    
    # Total Positions
    total_positions_open: int
    total_positions_closed: int
    total_positions_overall: int
    
    # Additional metadata
    filter_applied: dict
    
    class Config:
        from_attributes = True

class DemandSupplyGapItem(BaseModel):
    """Schema for demand, supply and gap category responses."""
    id: int
    job_id: str
    job_title: str
    department: str
    status: str
    no_of_positions: int

    class Config:
        from_attributes = True

class InterviewProcessItem(BaseModel):
    """Schema for interview process category response."""
    candidate_id: str
    candidate_name: str
    job_id: Optional[str] = None
    job_title: Optional[str] = None
    department: str
    job_status: Optional[str] = None
    candidate_status: Optional[str] = None
    
    class Config:
        from_attributes = True

class SupplyItem(BaseModel):
    """Schema for supply (onboarded candidates) category response."""
    candidate_id: str
    candidate_name: str
    department: str
    designation: Optional[str] = None
    date_of_joining: Optional[str] = None
    candidate_status: Optional[str] = None
    
    class Config:
        from_attributes = True

class DemandCategory(str, Enum):
    DEMAND = "demand"
    SUPPLY = "supply"
    INTERVIEW = "interview"
    GAP = "gap"
    IN_PROGRESS = "in_progress"

T_demand = TypeVar('T_demand')

class PaginatedDemandResponse(BaseModel, Generic[T_demand]):
    """Generic schema for a paginated response for demand/supply."""
    data: List[T_demand]
    total_items: int
    total_pages: int
    page: int
    page_size: int
    filter_applied: dict

def _build_base_query(
    db: Session,
    status_filter: Optional[str] = None,
    department: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    search: Optional[str] = None,
):
    """Helper to construct the base query with filters."""
    query = db.query(Job)
    filters_applied = {}

    if status_filter:
        query = query.filter(Job.status == status_filter)
        filters_applied["status"] = status_filter
    
    if department:
        # Check if the department is an ID (integer) or a name (string)
        if department.isdigit():
            # If it's a digit, assume it's a department ID and join with the Department table
            query = query.join(Department, Job.department == Department.name).filter(Department.id == int(department))
        else:
            # Otherwise, filter by department name directly
            query = query.filter(Job.department.ilike(f"%{department}%"))
        filters_applied["department"] = department
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Job.job_title.ilike(search_term),
                Job.job_id.ilike(search_term)
            )
        )
        filters_applied["search"] = search

    if date_from:
        try:
            from_date = datetime.strptime(date_from, "%Y-%m-%d").date()
            query = query.filter(Job.created_on >= from_date)
            filters_applied["date_from"] = date_from
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_from format. Use YYYY-MM-DD")
            
    if date_to:
        try:
            to_date = datetime.strptime(date_to, "%Y-%m-%d")
            to_date = to_date.replace(hour=23, minute=59, second=59)
            query = query.filter(Job.created_on <= to_date)
            filters_applied["date_to"] = date_to
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_to format. Use YYYY-MM-DD")

    return query, filters_applied

def _get_paginated_job_list(
    response_model: BaseModel,
    db: Session,
    department: Optional[str],
    date_from: Optional[str],
    date_to: Optional[str],
    page: int,
    page_size: int,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
):
    """Generic function to get a paginated list of jobs or positions."""
    if page <= 0:
        raise HTTPException(status_code=400, detail="Page number must be positive.")
    if page_size <= 0 or page_size > 100:
        raise HTTPException(status_code=400, detail="Page size must be between 1 and 100.")

    base_query, filters_applied = _build_base_query(
        db, status_filter, department, date_from, date_to, search
    )

    total_items = base_query.count()
    if total_items == 0:
        return PaginatedResponse(
            data=[], total_items=0, total_pages=0, page=page, page_size=page_size, filter_applied=filters_applied
        )

    total_pages = (total_items + page_size - 1) // page_size

    if page > total_pages:
        raise HTTPException(status_code=404, detail="Page not found")

    offset = (page - 1) * page_size
    results = base_query.order_by(Job.created_on.desc()).offset(offset).limit(page_size).all()

    return PaginatedResponse(
        data=results,
        total_items=total_items,
        total_pages=total_pages,
        page=page,
        page_size=page_size,
        filter_applied=filters_applied,
    )

def _get_filtered_job_list(
    db: Session,
    status_filter: Optional[str] = None,
    department: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    search: Optional[str] = None,
):
    """Generic function to get a filtered list of jobs or positions for download."""
    base_query, _ = _build_base_query(
        db, status_filter, department, date_from, date_to, search
    )
    
    results = base_query.order_by(Job.created_on.desc()).all()
    return results

@router.get("/count", response_model=JobStatsResponse)
def get_job_statistics(
    department: Optional[str] = Query(None, description="Filter by department name"),
    startDate: Optional[str] = Query(None, description="Filter jobs created from this date (YYYY-MM-DD)"),
    endDate: Optional[str] = Query(None, description="Filter jobs created until this date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Get job statistics with optional filtering by department and date range.
    
    Returns:
    - Total Jobs: Active (OPEN) and Past (CLOSED) separately, plus overall total
    - Total Positions: Open and Closed separately, plus overall total
    
    Query Parameters:
    - department: Filter by specific department name
    - startDate: Start date for filtering (format: YYYY-MM-DD)
    - endDate: End date for filtering (format: YYYY-MM-DD)
    """
    try:
        # Build base query
        query = db.query(Job)
        
        # Track applied filters for response metadata
        filters_applied = {}
        
        # Apply department filter if provided
        if department:
            query = query.filter(Job.department.ilike(f"%{department}%"))
            filters_applied["department"] = department
        
        # Apply date filters if provided
        if startDate:
            try:
                from_date = datetime.strptime(startDate, "%Y-%m-%d")
                query = query.filter(Job.created_on >= from_date)
                filters_applied["startDate"] = startDate
            except ValueError:
                raise HTTPException(
                    status_code=400, 
                    detail="Invalid startDate format. Use YYYY-MM-DD"
                )
        
        if endDate:
            try:
                to_date = datetime.strptime(endDate, "%Y-%m-%d")
                # Include the entire day by adding 23:59:59
                to_date = to_date.replace(hour=23, minute=59, second=59)
                query = query.filter(Job.created_on <= to_date)
                filters_applied["endDate"] = endDate
            except ValueError:
                raise HTTPException(
                    status_code=400, 
                    detail="Invalid endDate format. Use YYYY-MM-DD"
                )
        
        # Execute aggregation query for statistics with same filters
        stats = db.query(
            # Job counts by status
            func.sum(case((Job.status == "OPEN", 1), else_=0)).label("active_jobs"),
            func.sum(case((Job.status == "CLOSED", 1), else_=0)).label("past_jobs"),
            func.count(Job.id).label("total_jobs"),
            
            # Position counts by status
            func.sum(case(
                (Job.status == "OPEN", Job.no_of_positions), 
                else_=0
            )).label("open_positions"),
            func.sum(case(
                (Job.status == "CLOSED", Job.no_of_positions), 
                else_=0
            )).label("closed_positions"),
            func.sum(Job.no_of_positions).label("total_positions")
        )
        
        # Apply filters to stats query
        if department:
            stats = stats.filter(Job.department.ilike(f"%{department}%"))
        if startDate:
            from_date = datetime.strptime(startDate, "%Y-%m-%d")
            stats = stats.filter(Job.created_on >= from_date)
        if endDate:
            to_date = datetime.strptime(endDate, "%Y-%m-%d")
            to_date = to_date.replace(hour=23, minute=59, second=59)
            stats = stats.filter(Job.created_on <= to_date)
        
        result = stats.first()
        
        # Handle None values and ensure integers
        active_jobs = int(result.active_jobs or 0)
        past_jobs = int(result.past_jobs or 0)
        total_jobs = int(result.total_jobs or 0)
        open_positions = int(result.open_positions or 0)
        closed_positions = int(result.closed_positions or 0)
        total_positions = int(result.total_positions or 0)
        
        return JobStatsResponse(
            total_jobs_active=active_jobs,
            total_jobs_past=past_jobs,
            total_jobs_overall=total_jobs,
            total_positions_open=open_positions,
            total_positions_closed=closed_positions,
            total_positions_overall=total_positions,
            filter_applied=filters_applied
        )
        
    except HTTPException:
        # Re-raise HTTPExceptions (like date format errors)
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"An error occurred while fetching job statistics: {str(e)}"
        ) 

@router.get("/jobs", response_model=PaginatedResponse[JobListItem], tags=["Job Statistics Details"])
def get_all_jobs_detailed(
    department: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Search by job title or ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Lists all jobs with filters and pagination."""
    return _get_paginated_job_list(
        response_model=JobListItem,
        db=db,
        department=department,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
        search=search,
    )

@router.get("/jobs/open", response_model=PaginatedResponse[JobListItem], tags=["Job Statistics Details"])
def get_open_jobs_detailed(
    department: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Search by job title or ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Lists open jobs with filters and pagination."""
    return _get_paginated_job_list(
        response_model=JobListItem,
        db=db,
        department=department,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
        status_filter="OPEN",
        search=search,
    )

@router.get("/jobs/closed", response_model=PaginatedResponse[JobListItem], tags=["Job Statistics Details"])
def get_closed_jobs_detailed(
    department: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Search by job title or ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Lists closed jobs with filters and pagination."""
    return _get_paginated_job_list(
        response_model=JobListItem,
        db=db,
        department=department,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
        status_filter="CLOSED",
        search=search,
    )

@router.get("/positions", response_model=PaginatedResponse[PositionListItem], tags=["Job Statistics Details"])
def get_all_positions_detailed(
    department: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Search by job title or ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Lists all job positions with filters and pagination."""
    return _get_paginated_job_list(
        response_model=PositionListItem,
        db=db,
        department=department,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
        search=search,
    )

@router.get("/positions/open", response_model=PaginatedResponse[PositionListItem], tags=["Job Statistics Details"])
def get_open_positions_detailed(
    department: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Search by job title or ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Lists open job positions with filters and pagination."""
    return _get_paginated_job_list(
        response_model=PositionListItem,
        db=db,
        department=department,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
        status_filter="OPEN",
        search=search,
    )

@router.get("/positions/closed", response_model=PaginatedResponse[PositionListItem], tags=["Job Statistics Details"])
def get_closed_positions_detailed(
    department: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Search by job title or ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Lists closed job positions with filters and pagination."""
    return _get_paginated_job_list(
        response_model=PositionListItem,
        db=db,
        department=department,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
        status_filter="CLOSED",
        search=search,
    )

@router.get("/demand-supply-details", response_model=PaginatedDemandResponse[Union[DemandSupplyGapItem, InterviewProcessItem, SupplyItem]], tags=["Job Statistics Details"])
def get_demand_supply_details(
    category: DemandCategory = Query(..., description="Category of details to fetch"),
    department: Optional[str] = Query(None, description="Filter by department name"),
    date_from: Optional[str] = Query(None, description="Filter jobs created from this date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter jobs created until this date (YYYY-MM-DD)"),
    search: Optional[str] = Query(None, description="Search term for job titles, IDs, or candidate names"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Provides detailed, paginated lists for demand and supply statistics.
    - **Demand**: All created jobs.
    - **Supply**: Jobs with successfully onboarded candidates.
    - **Interview**: Candidates in the interview process (L1 or later for open jobs).
    - **Gap**: Jobs without any successfully onboarded candidates.
    - **In_Progress**: All candidates who are in any process except being onboarded or in screening.
    """
    if page <= 0:
        raise HTTPException(status_code=400, detail="Page number must be positive.")
    if page_size <= 0 or page_size > 100:
        raise HTTPException(status_code=400, detail="Page size must be between 1 and 100.")

    filters_applied = {}
    
    base_query = None
    response_data = []

    # Common filters
    if department:
        filters_applied["department"] = department
    if date_from:
        try:
            datetime.strptime(date_from, "%Y-%m-%d")
            filters_applied["date_from"] = date_from
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_from format. Use YYYY-MM-DD")
    if date_to:
        try:
            datetime.strptime(date_to, "%Y-%m-%d")
            filters_applied["date_to"] = date_to
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_to format. Use YYYY-MM-DD")
    if search:
        filters_applied["search"] = search

    if category == DemandCategory.SUPPLY:
        # Special query for supply category to get the required fields
        base_query = db.query(
            Candidate.candidate_id,
            Candidate.candidate_name,
            func.coalesce(Job.department, Candidate.department).label("department"),
            func.coalesce(Job.job_title, Candidate.current_designation).label("designation"),
            Candidate.date_of_joining,
            Candidate.current_status.label("candidate_status")
        ).outerjoin(Job, Candidate.associated_job_id == Job.job_id)
        # Filter for onboarded candidates only
        base_query = base_query.filter(Candidate.current_status == 'Onboarded')
        
    elif category in [DemandCategory.INTERVIEW, DemandCategory.IN_PROGRESS]:
        base_query = db.query(
            Candidate.candidate_id,
            Candidate.candidate_name,
            Candidate.current_status.label("candidate_status"),
            Job.job_id,
            Job.job_title,
            func.coalesce(Job.department, Candidate.department).label("department"),
            Job.status.label("job_status")
        ).outerjoin(Job, Candidate.associated_job_id == Job.job_id)

        if category == DemandCategory.INTERVIEW:
            # Note: "Scheduled" is explicitly excluded from candidates in interview process
            INTERVIEW_STATUSES = [
                'L1 Interview', 'L2 Interview', 'HR Round', 'CTC Breakup', 
                'Docs Upload', 'Create Offer', 'Offer Initiated', 'Offer Accepted'
            ]
            base_query = base_query.filter(Job.status == 'OPEN', Candidate.current_status.in_(INTERVIEW_STATUSES))
        
        elif category == DemandCategory.IN_PROGRESS:
            # Exclude both 'Onboarded' and 'SCREENING' candidates from in_progress
            base_query = base_query.filter(
                and_(
                    Candidate.current_status != 'Onboarded',
                    Candidate.current_status != 'SCREENING'
                )
            )
        
        if search:
            search_term = f"%{search}%"
            base_query = base_query.filter(
                or_(
                    Candidate.candidate_name.ilike(search_term),
                    Candidate.candidate_id.ilike(search_term),
                    Job.job_title.ilike(search_term),
                    Job.job_id.ilike(search_term) if category != DemandCategory.SUPPLY else None
                )
            )
    else:
        base_query = db.query(Job)
        if category == DemandCategory.GAP:
            subquery = db.query(Candidate.associated_job_id).filter(Candidate.current_status == 'Onboarded').distinct()
            base_query = base_query.filter(Job.job_id.notin_(subquery))

        if search:
            search_term = f"%{search}%"
            base_query = base_query.filter(or_(Job.job_title.ilike(search_term), Job.job_id.ilike(search_term)))

    if department:
        if category in [DemandCategory.INTERVIEW, DemandCategory.IN_PROGRESS, DemandCategory.SUPPLY]:
            # For candidate-based queries, filter by candidate department
            base_query = base_query.filter(Candidate.department.ilike(f"%{department}%"))
        else:
            # For job-based queries, filter by job department
            base_query = base_query.filter(Job.department.ilike(f"%{department}%"))
            
    if date_from:
        from_date_obj = datetime.strptime(date_from, "%Y-%m-%d").date()
        if category in [DemandCategory.INTERVIEW, DemandCategory.IN_PROGRESS, DemandCategory.SUPPLY]:
            # For candidate-based queries, filter by candidate application_date
            base_query = base_query.filter(Candidate.application_date >= from_date_obj)
        else:
            # For job-based queries, filter by job created_on
            base_query = base_query.filter(Job.created_on >= from_date_obj)
            
    if date_to:
        to_date_obj = datetime.strptime(date_to, "%Y-%m-%d").date()
        if category in [DemandCategory.INTERVIEW, DemandCategory.IN_PROGRESS, DemandCategory.SUPPLY]:
            # For candidate-based queries, filter by candidate application_date
            base_query = base_query.filter(Candidate.application_date <= to_date_obj)
        else:
            # For job-based queries, filter by job created_on
            to_date_obj = datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            base_query = base_query.filter(Job.created_on <= to_date_obj)

    total_items = base_query.count()
    total_pages = (total_items + page_size - 1) // page_size

    if page > total_pages and total_items > 0:
        raise HTTPException(status_code=404, detail="Page not found")

    offset = (page - 1) * page_size
    
    if category == DemandCategory.SUPPLY:
        results = base_query.offset(offset).limit(page_size).all()
        response_data = [SupplyItem.model_validate(r) for r in results]
    elif category in [DemandCategory.INTERVIEW, DemandCategory.IN_PROGRESS]:
        results = base_query.order_by(Job.created_on.desc()).offset(offset).limit(page_size).all()
        response_data = [InterviewProcessItem.model_validate(r) for r in results]
    else:
        base_query = base_query.order_by(Job.created_on.desc())
        results = base_query.offset(offset).limit(page_size).all()
        response_data = [DemandSupplyGapItem.model_validate(r) for r in results]

    return PaginatedDemandResponse(
        data=response_data,
        total_items=total_items,
        total_pages=total_pages,
        page=page,
        page_size=page_size,
        filter_applied=filters_applied,
    ) 

@router.get("/jobs/download", response_model=List[JobListItem], tags=["Job Statistics Details"])
def get_all_jobs_detailed_download(
    department: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Search by job title or ID"),
    db: Session = Depends(get_db)
):
    """
    Downloads a detailed list of all jobs with optional filters.
    """
    results = _get_filtered_job_list(
        db=db,
        department=department,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )
    return results

@router.get("/jobs/open/download", response_model=List[JobListItem], tags=["Job Statistics Details"])
def get_open_jobs_detailed_download(
    department: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Search by job title or ID"),
    db: Session = Depends(get_db)
):
    """
    Downloads a detailed list of all open jobs with optional filters.
    """
    results = _get_filtered_job_list(
        db=db,
        status_filter="OPEN",
        department=department,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )
    return results

@router.get("/jobs/closed/download", response_model=List[JobListItem], tags=["Job Statistics Details"])
def get_closed_jobs_detailed_download(
    department: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Search by job title or ID"),
    db: Session = Depends(get_db)
):
    """
    Downloads a detailed list of all closed jobs with optional filters.
    """
    results = _get_filtered_job_list(
        db=db,
        status_filter="CLOSED",
        department=department,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )
    return results

@router.get("/positions/download", response_model=List[PositionListItem], tags=["Job Statistics Details"])
def get_all_positions_detailed_download(
    department: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Search by job title or ID"),
    db: Session = Depends(get_db)
):
    """
    Downloads a detailed list of all positions with optional filters.
    """
    results = _get_filtered_job_list(
        db=db,
        department=department,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )
    return results

@router.get("/positions/open/download", response_model=List[PositionListItem], tags=["Job Statistics Details"])
def get_open_positions_detailed_download(
    department: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Search by job title or ID"),
    db: Session = Depends(get_db)
):
    """
    Downloads a detailed list of all open positions with optional filters.
    """
    results = _get_filtered_job_list(
        db=db,
        status_filter="OPEN",
        department=department,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )
    return results

@router.get("/positions/closed/download", response_model=List[PositionListItem], tags=["Job Statistics Details"])
def get_closed_positions_detailed_download(
    department: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Search by job title or ID"),
    db: Session = Depends(get_db)
):
    """Get all closed positions for download (without pagination)."""
    try:
        jobs, _ = _get_filtered_job_list(
            db=db,
            status_filter="CLOSED",
            department=department,
            date_from=date_from,
            date_to=date_to,
            search=search
        )
        
        return [
            PositionListItem(
                id=job.id,
                job_title=job.job_title,
                department=job.department,
                status=job.status,
                no_of_positions=job.no_of_positions
            )
            for job in jobs
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch closed positions: {str(e)}")

@router.get("/debug/supply-query", response_model=dict)
def debug_supply_query(db: Session = Depends(get_db)):
    """
    Debug endpoint to test the supply query logic.
    """
    # Test the exact query we're using for supply
    base_query = db.query(
        Candidate.candidate_id,
        Candidate.candidate_name,
        Candidate.current_status.label("candidate_status"),
        Job.job_id,
        Job.job_title,
        Job.department,
        Job.status.label("job_status")
    ).join(Job, Candidate.associated_job_id == Job.job_id)
    
    # Filter for onboarded
    base_query = base_query.filter(Candidate.current_status == 'Onboarded')
    
    # Get raw results
    results = base_query.all()
    
    # Convert to list of dicts for debugging
    debug_results = []
    for r in results:
        debug_results.append({
            "candidate_id": r.candidate_id,
            "candidate_name": r.candidate_name,
            "candidate_status": r.candidate_status,
            "job_id": r.job_id,
            "job_title": r.job_title,
            "department": r.department,
            "job_status": r.job_status
        })
    
    return {
        "total_results": len(results),
        "results": debug_results
    }

@router.get("/debug/candidate-job-mismatch", response_model=dict)
def debug_candidate_job_mismatch(db: Session = Depends(get_db)):
    """
    Debug endpoint to check candidate-job relationship issues.
    """
    # Get all onboarded candidates
    onboarded_candidates = db.query(Candidate).filter(Candidate.current_status == 'Onboarded').all()
    
    candidate_info = []
    for candidate in onboarded_candidates:
        # Try to find the associated job
        job = db.query(Job).filter(Job.job_id == candidate.associated_job_id).first()
        
        candidate_info.append({
            "candidate_id": candidate.candidate_id,
            "candidate_name": candidate.candidate_name,
            "associated_job_id": candidate.associated_job_id,
            "candidate_department": candidate.department,
            "job_found": job is not None,
            "job_title": job.job_title if job else None,
            "job_department": job.department if job else None
        })
    
    # Also check all unique job_ids from jobs table
    job_ids = [job.job_id for job in db.query(Job.job_id).all()]
    
    return {
        "total_onboarded_candidates": len(onboarded_candidates),
        "candidate_details": candidate_info,
        "total_jobs": len(job_ids),
        "sample_job_ids": job_ids[:5]  # First 5 job IDs for comparison
    }

@router.get("/debug/candidate-specific/{candidate_id}", response_model=dict)
def debug_specific_candidate(candidate_id: str, db: Session = Depends(get_db)):
    """
    Debug a specific candidate to understand join issues.
    """
    # Get the specific candidate
    candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    
    if not candidate:
        return {"error": "Candidate not found"}
    
    # Try to find the associated job
    job = None
    if candidate.associated_job_id:
        job = db.query(Job).filter(Job.job_id == candidate.associated_job_id).first()
    
    # Try the exact join query we're using
    join_result = db.query(
        Candidate.candidate_id,
        Candidate.candidate_name,
        Candidate.current_status.label("candidate_status"),
        Job.job_id,
        Job.job_title,
        Job.department,
        Job.status.label("job_status")
    ).join(Job, Candidate.associated_job_id == Job.job_id).filter(
        Candidate.candidate_id == candidate_id
    ).first()
    
    return {
        "candidate_exists": candidate is not None,
        "candidate_status": candidate.current_status if candidate else None,
        "associated_job_id": candidate.associated_job_id if candidate else None,
        "candidate_department": candidate.department if candidate else None,
        "job_exists": job is not None,
        "job_id": job.job_id if job else None,
        "job_title": job.job_title if job else None,
        "job_department": job.department if job else None,
        "join_query_result": join_result is not None,
        "join_data": {
            "candidate_id": join_result.candidate_id if join_result else None,
            "candidate_name": join_result.candidate_name if join_result else None,
            "job_title": join_result.job_title if join_result else None
        } if join_result else None
    } 

# New Department Breakdown APIs
@router.get("/total-jobs/department-breakdown", response_model=schemas.DepartmentBreakdownResponse, tags=["Department Breakdown"])
async def get_total_jobs_department_breakdown(
    date_from: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)"),
    department: Optional[str] = Query("all", description="Department filter ('all' for all departments)"),
    db: Session = Depends(get_db)
):
    """Get total jobs breakdown by department."""
    try:
        # Build base query
        query = db.query(Job.department, func.count(Job.id).label('count'))
        
        # Apply date filters
        if date_from:
            try:
                from_date = datetime.strptime(date_from, "%Y-%m-%d").date()
                query = query.filter(Job.created_on >= from_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_from format. Use YYYY-MM-DD")
                
        if date_to:
            try:
                to_date = datetime.strptime(date_to, "%Y-%m-%d")
                to_date = to_date.replace(hour=23, minute=59, second=59)
                query = query.filter(Job.created_on <= to_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_to format. Use YYYY-MM-DD")
        
        # Apply department filter
        if department and department.lower() != "all":
            query = query.filter(Job.department.ilike(f"%{department}%"))
        
        # Group by department and get counts
        results = query.group_by(Job.department).all()
        
        breakdown = [{"department": dept, "count": count} for dept, count in results]
        total = sum(item["count"] for item in breakdown)
        
        return {"breakdown": breakdown, "total": total}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch total jobs breakdown: {str(e)}")

@router.get("/open-jobs/department-breakdown", response_model=schemas.DepartmentBreakdownResponse, tags=["Department Breakdown"])
async def get_open_jobs_department_breakdown(
    date_from: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)"),
    department: Optional[str] = Query("all", description="Department filter ('all' for all departments)"),
    db: Session = Depends(get_db)
):
    """Get open jobs breakdown by department."""
    try:
        # Build base query with OPEN status filter
        query = db.query(Job.department, func.count(Job.id).label('count')).filter(Job.status == "OPEN")
        
        # Apply date filters
        if date_from:
            try:
                from_date = datetime.strptime(date_from, "%Y-%m-%d").date()
                query = query.filter(Job.created_on >= from_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_from format. Use YYYY-MM-DD")
                
        if date_to:
            try:
                to_date = datetime.strptime(date_to, "%Y-%m-%d")
                to_date = to_date.replace(hour=23, minute=59, second=59)
                query = query.filter(Job.created_on <= to_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_to format. Use YYYY-MM-DD")
        
        # Apply department filter
        if department and department.lower() != "all":
            query = query.filter(Job.department.ilike(f"%{department}%"))
        
        # Group by department and get counts
        results = query.group_by(Job.department).all()
        
        breakdown = [{"department": dept, "count": count} for dept, count in results]
        total = sum(item["count"] for item in breakdown)
        
        return {"breakdown": breakdown, "total": total}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch open jobs breakdown: {str(e)}")

@router.get("/closed-jobs/department-breakdown", response_model=schemas.DepartmentBreakdownResponse, tags=["Department Breakdown"])
async def get_closed_jobs_department_breakdown(
    date_from: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)"),
    department: Optional[str] = Query("all", description="Department filter ('all' for all departments)"),
    db: Session = Depends(get_db)
):
    """Get closed jobs breakdown by department."""
    try:
        # Build base query with CLOSED status filter
        query = db.query(Job.department, func.count(Job.id).label('count')).filter(Job.status == "CLOSED")
        
        # Apply date filters
        if date_from:
            try:
                from_date = datetime.strptime(date_from, "%Y-%m-%d").date()
                query = query.filter(Job.created_on >= from_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_from format. Use YYYY-MM-DD")
                
        if date_to:
            try:
                to_date = datetime.strptime(date_to, "%Y-%m-%d")
                to_date = to_date.replace(hour=23, minute=59, second=59)
                query = query.filter(Job.created_on <= to_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_to format. Use YYYY-MM-DD")
        
        # Apply department filter
        if department and department.lower() != "all":
            query = query.filter(Job.department.ilike(f"%{department}%"))
        
        # Group by department and get counts
        results = query.group_by(Job.department).all()
        
        breakdown = [{"department": dept, "count": count} for dept, count in results]
        total = sum(item["count"] for item in breakdown)
        
        return {"breakdown": breakdown, "total": total}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch closed jobs breakdown: {str(e)}")

@router.get("/total-positions/department-breakdown", response_model=schemas.DepartmentBreakdownResponse, tags=["Department Breakdown"])
async def get_total_positions_department_breakdown(
    date_from: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)"),
    department: Optional[str] = Query("all", description="Department filter ('all' for all departments)"),
    db: Session = Depends(get_db)
):
    """Get total positions breakdown by department."""
    try:
        # Build base query to sum positions
        query = db.query(Job.department, func.sum(Job.no_of_positions).label('count'))
        
        # Apply date filters
        if date_from:
            try:
                from_date = datetime.strptime(date_from, "%Y-%m-%d").date()
                query = query.filter(Job.created_on >= from_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_from format. Use YYYY-MM-DD")
                
        if date_to:
            try:
                to_date = datetime.strptime(date_to, "%Y-%m-%d")
                to_date = to_date.replace(hour=23, minute=59, second=59)
                query = query.filter(Job.created_on <= to_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_to format. Use YYYY-MM-DD")
        
        # Apply department filter
        if department and department.lower() != "all":
            query = query.filter(Job.department.ilike(f"%{department}%"))
        
        # Group by department and get sums
        results = query.group_by(Job.department).all()
        
        breakdown = [{"department": dept, "count": int(count) if count else 0} for dept, count in results]
        total = sum(item["count"] for item in breakdown)
        
        return {"breakdown": breakdown, "total": total}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch total positions breakdown: {str(e)}")

@router.get("/open-positions/department-breakdown", response_model=schemas.DepartmentBreakdownResponse, tags=["Department Breakdown"])
async def get_open_positions_department_breakdown(
    date_from: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)"),
    department: Optional[str] = Query("all", description="Department filter ('all' for all departments)"),
    db: Session = Depends(get_db)
):
    """Get open positions breakdown by department."""
    try:
        # Build base query to sum positions for OPEN jobs
        query = db.query(Job.department, func.sum(Job.no_of_positions).label('count')).filter(Job.status == "OPEN")
        
        # Apply date filters
        if date_from:
            try:
                from_date = datetime.strptime(date_from, "%Y-%m-%d").date()
                query = query.filter(Job.created_on >= from_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_from format. Use YYYY-MM-DD")
                
        if date_to:
            try:
                to_date = datetime.strptime(date_to, "%Y-%m-%d")
                to_date = to_date.replace(hour=23, minute=59, second=59)
                query = query.filter(Job.created_on <= to_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_to format. Use YYYY-MM-DD")
        
        # Apply department filter
        if department and department.lower() != "all":
            query = query.filter(Job.department.ilike(f"%{department}%"))
        
        # Group by department and get sums
        results = query.group_by(Job.department).all()
        
        breakdown = [{"department": dept, "count": int(count) if count else 0} for dept, count in results]
        total = sum(item["count"] for item in breakdown)
        
        return {"breakdown": breakdown, "total": total}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch open positions breakdown: {str(e)}")

@router.get("/closed-positions/department-breakdown", response_model=schemas.DepartmentBreakdownResponse, tags=["Department Breakdown"])
async def get_closed_positions_department_breakdown(
    date_from: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)"),
    department: Optional[str] = Query("all", description="Department filter ('all' for all departments)"),
    db: Session = Depends(get_db)
):
    """Get closed positions breakdown by department."""
    try:
        # Build base query to sum positions for CLOSED jobs
        query = db.query(Job.department, func.sum(Job.no_of_positions).label('count')).filter(Job.status == "CLOSED")
        
        # Apply date filters
        if date_from:
            try:
                from_date = datetime.strptime(date_from, "%Y-%m-%d").date()
                query = query.filter(Job.created_on >= from_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_from format. Use YYYY-MM-DD")
                
        if date_to:
            try:
                to_date = datetime.strptime(date_to, "%Y-%m-%d")
                to_date = to_date.replace(hour=23, minute=59, second=59)
                query = query.filter(Job.created_on <= to_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_to format. Use YYYY-MM-DD")
        
        # Apply department filter
        if department and department.lower() != "all":
            query = query.filter(Job.department.ilike(f"%{department}%"))
        
        # Group by department and get sums
        results = query.group_by(Job.department).all()
        
        breakdown = [{"department": dept, "count": int(count) if count else 0} for dept, count in results]
        total = sum(item["count"] for item in breakdown)
        
        return {"breakdown": breakdown, "total": total}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch closed positions breakdown: {str(e)}") 