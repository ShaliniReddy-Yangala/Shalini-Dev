from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from typing import List, Optional, Union
from datetime import date, datetime

from app import models, schemas

from app.dependencies import get_db
router = APIRouter()

@router.get("/demand", response_model=Union[schemas.DemandSupplyMetrics, List[schemas.DepartmentDemandSupply], dict, List[schemas.OnboardedCandidate]])
def get_demand_supply_metrics(
    db: Session = Depends(get_db),
    department: Optional[str] = Query(None),
    detailed: Optional[str] = Query(None, description="Use 'demand' for job details, 'supply' for onboarded candidate details, or 'gap' for details on jobs with a gap."),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    overall: bool = Query(False, description="Set to true to get overall metrics across all departments."),
    page: int = Query(1, ge=1, description="Page number for pagination (only for detailed=gap/demand)"),
    page_size: int = Query(10, ge=1, le=100, description="Page size for pagination (only for detailed=gap/demand)")
):
    """
    Provides demand and supply metrics for jobs and candidates.
    - **Demand**: No of positions created(not jobs)
    - **Supply**: onboarded
    - **In Progress**: Scheduled to Docs upload
    - **Gap**: Demand - Supply
    """
    
    # Base queries
    jobs_query = db.query(models.Job)
    candidates_query = db.query(models.Candidate)

    # Date filtering
    if from_date and to_date:
        jobs_query = jobs_query.filter(models.Job.created_on.between(from_date, to_date))
        candidates_query = candidates_query.filter(models.Candidate.application_date.between(from_date, to_date))
    elif from_date:
        jobs_query = jobs_query.filter(models.Job.created_on >= from_date)
        candidates_query = candidates_query.filter(models.Candidate.application_date >= from_date)
    elif to_date:
        jobs_query = jobs_query.filter(models.Job.created_on <= to_date)
        candidates_query = candidates_query.filter(models.Candidate.application_date <= to_date)

    # Department filtering
    if department:
        jobs_query = jobs_query.filter(models.Job.department == department)
        candidates_query = candidates_query.filter(models.Candidate.department == department)

    # Overall metrics across all departments
    if overall:
        demand = jobs_query.with_entities(func.sum(models.Job.no_of_positions)).scalar() or 0
        supply = candidates_query.filter(models.Candidate.current_status == 'Onboarded').count()
        # Define interview statuses for in_process count (same as used in detailed stats API)
        # Note: "Scheduled" is explicitly excluded from candidates in progress
        interview_statuses = [
            'L1 Interview', 'L2 Interview', 'HR Round', 'CTC Breakup', 
            'Docs Upload', 'Create Offer', 'Offer Initiated', 'Offer Accepted'
        ]
        in_process = candidates_query.filter(models.Candidate.current_status.in_(interview_statuses)).count()
        gap = demand - supply
        return schemas.DemandSupplyMetrics(
            demand=demand,
            supply=supply,
            in_process=in_process,
            gap=gap
        )

    # Detailed view for onboarded candidates
    if detailed == 'supply':
        # Start a fresh query for supply details to ignore department filters from the main scope
        supply_details_query = db.query(models.Candidate).filter(models.Candidate.current_status == 'Onboarded')

        if department:
            supply_details_query = supply_details_query.filter(models.Candidate.department == department)
            
        # Apply date filters if they exist
        if from_date and to_date:
            supply_details_query = supply_details_query.filter(models.Candidate.application_date.between(from_date, to_date))
        elif from_date:
            supply_details_query = supply_details_query.filter(models.Candidate.application_date >= from_date)
        elif to_date:
            supply_details_query = supply_details_query.filter(models.Candidate.application_date <= to_date)
        
        # Filter for onboarded candidates and join with jobs to get job_title
        onboarded_with_jobs = supply_details_query.join(
            models.Job, models.Candidate.associated_job_id == models.Job.job_id, isouter=True
        ).with_entities(
            models.Candidate,
            models.Job.job_title
        ).all()
        
        response = []
        for candidate, job_title in onboarded_with_jobs:
            response.append(schemas.OnboardedCandidate(
                candidate_id=candidate.candidate_id,
                candidate_name=candidate.candidate_name,
                job_id=candidate.associated_job_id,
                job_title=job_title,
                date_of_joining=candidate.date_of_joining,
                department=candidate.department,
                designation=job_title
            ))
        return response

    # Detailed view for demand (job-wise) or gap details
    if detailed in ['demand', 'gap']:
        # Define interview statuses for in_process count (same as used in detailed stats API)
        # Note: "Scheduled" is explicitly excluded from candidates in progress
        interview_statuses = [
            'L1 Interview', 'L2 Interview', 'HR Round', 'CTC Breakup', 
            'Docs Upload', 'Create Offer', 'Offer Initiated', 'Offer Accepted'
        ]

        # Subquery for supply count (onboarded candidates)
        supply_subquery = db.query(
            models.Candidate.associated_job_id,
            func.count(models.Candidate.candidate_id).label('supply_count')
        ).filter(models.Candidate.current_status == 'Onboarded').group_by(models.Candidate.associated_job_id).subquery()

        # Subquery for in_process count (candidates in interview stages)
        in_process_subquery = db.query(
            models.Candidate.associated_job_id,
            func.count(models.Candidate.candidate_id).label('in_process_count')
        ).filter(models.Candidate.current_status.in_(interview_statuses)).group_by(models.Candidate.associated_job_id).subquery()

        # Join jobs with subqueries to get all counts in one go
        jobs_with_counts = jobs_query.outerjoin(
            supply_subquery, models.Job.job_id == supply_subquery.c.associated_job_id
        ).outerjoin(
            in_process_subquery, models.Job.job_id == in_process_subquery.c.associated_job_id
        ).with_entities(
            models.Job.job_id,
            models.Job.job_title,
            models.Job.department,
            models.Job.status,
            models.Job.no_of_positions,
            func.coalesce(supply_subquery.c.supply_count, 0).label('supply'),
            func.coalesce(in_process_subquery.c.in_process_count, 0).label('in_process')
        ).all()
        
        response = []
        for job_id, job_title, department, status, demand, supply, in_process in jobs_with_counts:
            gap = demand - supply
            if detailed == 'gap' and gap <= 0:
                continue
            response.append(schemas.JobDemandSupply(
                job_id=job_id,
                job_title=job_title,
                department=department,
                status=status,
                demand=demand,
                supply=supply,
                in_process=in_process,
                gap=gap
            ))
        # PAGINATION LOGIC
        total = len(response)
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1
        if page > total_pages and total > 0:
            raise HTTPException(status_code=404, detail="Page not found")
        start = (page - 1) * page_size
        end = start + page_size
        paginated_items = response[start:end]
        return {
            "items": paginated_items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }

    # Department-wise breakdown or overall
    if department is None:
        # Group by department
        department_metrics = db.query(
            models.Job.department,
            func.sum(models.Job.no_of_positions).label('demand')
        ).group_by(models.Job.department).all()

        results = []
        # Define interview statuses for in_process count (same as used in detailed stats API)
        # Note: "Scheduled" is explicitly excluded from candidates in progress
        interview_statuses = [
            'L1 Interview', 'L2 Interview', 'HR Round', 'CTC Breakup', 
            'Docs Upload', 'Create Offer', 'Offer Initiated', 'Offer Accepted'
        ]
        for dept_name, demand_count in department_metrics:
            supply = candidates_query.filter(models.Candidate.department == dept_name, models.Candidate.current_status == 'Onboarded').count()
            in_process = candidates_query.filter(models.Candidate.department == dept_name, models.Candidate.current_status.in_(interview_statuses)).count()
            gap = demand_count - supply
            results.append(schemas.DepartmentDemandSupply(
                department=dept_name,
                demand=demand_count,
                supply=supply,
                in_process=in_process,
                gap=gap
            ))
        return results

    # Overall metrics for a specific department
    demand = jobs_query.with_entities(func.sum(models.Job.no_of_positions)).scalar() or 0
    supply = candidates_query.filter(models.Candidate.current_status == 'Onboarded').count()
    # Define interview statuses for in_process count (same as used in detailed stats API)
    # Note: "Scheduled" is explicitly excluded from candidates in progress
    interview_statuses = [
        'L1 Interview', 'L2 Interview', 'HR Round', 'CTC Breakup', 
        'Docs Upload', 'Create Offer', 'Offer Initiated', 'Offer Accepted'
    ]
    in_process = candidates_query.filter(models.Candidate.current_status.in_(interview_statuses)).count()
    gap = demand - supply

    return schemas.DemandSupplyMetrics(
        demand=demand,
        supply=supply,
        in_process=in_process,
        gap=gap
    )

@router.get("/job-stats/demands/download", response_model=dict)
def download_demands_details(
    db: Session = Depends(get_db),
    department: Optional[str] = Query(None),
    detailed: Optional[str] = Query("demand", description="Use 'demand' for job details, 'gap' for jobs with gaps, 'supply' for onboarded candidates, or 'in_process' for candidates in progress."),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None)
):
    """
    Provides an unpaginated list of demand/gap details for download.
    """
    jobs_query = db.query(models.Job)

    if from_date and to_date:
        jobs_query = jobs_query.filter(models.Job.created_on.between(from_date, to_date))
    elif from_date:
        jobs_query = jobs_query.filter(models.Job.created_on >= from_date)
    elif to_date:
        jobs_query = jobs_query.filter(models.Job.created_on <= to_date)
    
    if department:
        jobs_query = jobs_query.filter(models.Job.department == department)
    
    # Define interview statuses for in_process count (same as used in detailed stats API)
    # Note: "Scheduled" is explicitly excluded from candidates in progress
    interview_statuses = [
        'L1 Interview', 'L2 Interview', 'HR Round', 'CTC Breakup', 
        'Docs Upload', 'Create Offer', 'Offer Initiated', 'Offer Accepted'
    ]

    supply_subquery = db.query(
        models.Candidate.associated_job_id,
        func.count(models.Candidate.candidate_id).label('supply_count')
    ).filter(models.Candidate.current_status == 'Onboarded').group_by(models.Candidate.associated_job_id).subquery()

    in_process_subquery = db.query(
        models.Candidate.associated_job_id,
        func.count(models.Candidate.candidate_id).label('in_process_count')
    ).filter(models.Candidate.current_status.in_(interview_statuses)).group_by(models.Candidate.associated_job_id).subquery()

    jobs_with_counts = jobs_query.outerjoin(
        supply_subquery, models.Job.job_id == supply_subquery.c.associated_job_id
    ).outerjoin(
        in_process_subquery, models.Job.job_id == in_process_subquery.c.associated_job_id
    ).with_entities(
        models.Job.job_id,
        models.Job.job_title,
        models.Job.department,
        models.Job.status,
        models.Job.no_of_positions,
        func.coalesce(supply_subquery.c.supply_count, 0).label('supply'),
        func.coalesce(in_process_subquery.c.in_process_count, 0).label('in_process')
    ).all()
    
    # Handle supply download (onboarded candidates)
    if detailed == 'supply':
        supply_details_query = db.query(models.Candidate).filter(models.Candidate.current_status == 'Onboarded')
        
        if department:
            supply_details_query = supply_details_query.filter(models.Candidate.department == department)
            
        if from_date and to_date:
            supply_details_query = supply_details_query.filter(models.Candidate.application_date.between(from_date, to_date))
        elif from_date:
            supply_details_query = supply_details_query.filter(models.Candidate.application_date >= from_date)
        elif to_date:
            supply_details_query = supply_details_query.filter(models.Candidate.application_date <= to_date)
        
        onboarded_with_jobs = supply_details_query.join(
            models.Job, models.Candidate.associated_job_id == models.Job.job_id, isouter=True
        ).with_entities(
            models.Candidate,
            models.Job.job_title
        ).all()
        
        response = []
        for candidate, job_title in onboarded_with_jobs:
            response.append(schemas.OnboardedCandidate(
                candidate_id=candidate.candidate_id,
                candidate_name=candidate.candidate_name,
                job_id=candidate.associated_job_id,
                job_title=job_title,
                date_of_joining=candidate.date_of_joining,
                department=candidate.department,
                designation=job_title
            ))
        return {"items": response}
    
    # Handle in_process download (candidates in interview stages)
    if detailed == 'in_process':
        # Use the same interview statuses as defined above for consistency
        # interview_statuses is already defined above in the same function
        
        in_process_query = db.query(models.Candidate).filter(models.Candidate.current_status.in_(interview_statuses))
        
        if department:
            in_process_query = in_process_query.filter(models.Candidate.department == department)
            
        if from_date and to_date:
            in_process_query = in_process_query.filter(models.Candidate.application_date.between(from_date, to_date))
        elif from_date:
            in_process_query = in_process_query.filter(models.Candidate.application_date >= from_date)
        elif to_date:
            in_process_query = in_process_query.filter(models.Candidate.application_date <= to_date)
        
        in_process_with_jobs = in_process_query.join(
            models.Job, models.Candidate.associated_job_id == models.Job.job_id, isouter=True
        ).with_entities(
            models.Candidate,
            models.Job.job_title
        ).all()
        
        response = []
        for candidate, job_title in in_process_with_jobs:
            response.append(schemas.OnboardedCandidate(
                candidate_id=candidate.candidate_id,
                candidate_name=candidate.candidate_name,
                job_id=candidate.associated_job_id,
                job_title=job_title,
                date_of_joining=candidate.date_of_joining,
                department=candidate.department,
                designation=job_title
            ))
        return {"items": response}

    # Handle demand and gap downloads (job details)
    response = []
    for job_id, job_title, department_name, status, demand, supply, in_process in jobs_with_counts:
        gap = demand - supply
        if detailed == 'gap' and gap <= 0:
            continue
        response.append(schemas.JobDemandSupply(
            job_id=job_id,
            job_title=job_title,
            department=department_name,
            status=status,
            demand=demand,
            supply=supply,
            in_process=in_process,
            gap=gap
        ))
    
    return {"items": response}

@router.get("/debug/onboarded-count", response_model=dict)
def debug_onboarded_count(db: Session = Depends(get_db)):
    """Debug: Check onboarded candidate count and statuses."""
    # Total candidates with 'Onboarded' status
    onboarded_count = db.query(models.Candidate).filter(models.Candidate.current_status == 'Onboarded').count()
    
    # Sample of onboarded candidates
    onboarded_sample = db.query(models.Candidate).filter(models.Candidate.current_status == 'Onboarded').limit(5).all()
    sample_data = [{
        "candidate_id": c.candidate_id,
        "name": c.candidate_name,
        "status": c.current_status,
        "department": c.department
    } for c in onboarded_sample]
    
    return {
        "total_onboarded": onboarded_count,
        "sample_onboarded": sample_data
    }

# New lightweight department breakdown endpoints for demand & supply statistics
@router.get("/demand-supply-stats/demand/department-breakdown", response_model=schemas.DemandSupplyDepartmentBreakdownResponse)
def get_demand_department_breakdown(
    db: Session = Depends(get_db),
    from_date: Optional[date] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)"),
    department: Optional[str] = Query(None, description="Department filter")
):
    """
    Get demand (positions needed) breakdown by department.
    Returns count of positions needed by department with percentages.
    """
    # Base query for jobs
    jobs_query = db.query(models.Job)
    
    # Apply date filters
    if from_date and to_date:
        jobs_query = jobs_query.filter(models.Job.created_on.between(from_date, to_date))
    elif from_date:
        jobs_query = jobs_query.filter(models.Job.created_on >= from_date)
    elif to_date:
        jobs_query = jobs_query.filter(models.Job.created_on <= to_date)
    
    # Apply department filter if provided
    if department and department.lower() != "all":
        jobs_query = jobs_query.filter(models.Job.department.ilike(f"%{department}%"))
    
    # Group by department and sum positions
    department_demand = jobs_query.with_entities(
        models.Job.department,
        func.sum(models.Job.no_of_positions).label('count')
    ).group_by(models.Job.department).all()
    
    # Calculate totals and percentages
    total = sum(count for _, count in department_demand)
    departments_count = len(department_demand)
    
    breakdown = []
    for dept_name, count in department_demand:
        percentage = round((count / total * 100), 1) if total > 0 else 0.0
        breakdown.append(schemas.DemandSupplyDepartmentBreakdownItem(
            department=dept_name,
            count=int(count) if count else 0,
            percentage=percentage
        ))
    
    # Sort by count descending
    breakdown.sort(key=lambda x: x.count, reverse=True)
    
    return schemas.DemandSupplyDepartmentBreakdownResponse(
        total=total,
        departments=departments_count,
        breakdown=breakdown
    )

@router.get("/demand-supply-stats/supply/department-breakdown", response_model=schemas.DemandSupplyDepartmentBreakdownResponse)
def get_supply_department_breakdown(
    db: Session = Depends(get_db),
    from_date: Optional[date] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)"),
    department: Optional[str] = Query(None, description="Department filter")
):
    """
    Get supply (onboarded candidates) breakdown by department.
    Returns count of onboarded candidates by department with percentages.
    """
    # Base query for onboarded candidates
    candidates_query = db.query(models.Candidate).filter(models.Candidate.current_status == 'Onboarded')
    
    # Apply date filters
    if from_date and to_date:
        candidates_query = candidates_query.filter(models.Candidate.application_date.between(from_date, to_date))
    elif from_date:
        candidates_query = candidates_query.filter(models.Candidate.application_date >= from_date)
    elif to_date:
        candidates_query = candidates_query.filter(models.Candidate.application_date <= to_date)
    
    # Apply department filter if provided
    if department and department.lower() != "all":
        candidates_query = candidates_query.filter(models.Candidate.department.ilike(f"%{department}%"))
    
    # Group by department and count candidates
    department_supply = candidates_query.with_entities(
        models.Candidate.department,
        func.count(models.Candidate.candidate_id).label('count')
    ).group_by(models.Candidate.department).all()
    
    # Calculate totals and percentages
    total = sum(count for _, count in department_supply)
    departments_count = len(department_supply)
    
    breakdown = []
    for dept_name, count in department_supply:
        percentage = round((count / total * 100), 1) if total > 0 else 0.0
        breakdown.append(schemas.DemandSupplyDepartmentBreakdownItem(
            department=dept_name,
            count=int(count) if count else 0,
            percentage=percentage
        ))
    
    # Sort by count descending
    breakdown.sort(key=lambda x: x.count, reverse=True)
    
    return schemas.DemandSupplyDepartmentBreakdownResponse(
        total=total,
        departments=departments_count,
        breakdown=breakdown
    )

@router.get("/demand-supply-stats/in-process/department-breakdown", response_model=schemas.DemandSupplyDepartmentBreakdownResponse)
def get_in_process_department_breakdown(
    db: Session = Depends(get_db),
    from_date: Optional[date] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)"),
    department: Optional[str] = Query(None, description="Department filter")
):
    """
    Get in-process candidates breakdown by department.
    Returns count of candidates currently in hiring process by department with percentages.
    """
    # Define interview statuses for in_process count (consistent with existing logic)
    interview_statuses = [
        'L1 Interview', 'L2 Interview', 'HR Round', 'CTC Breakup', 
        'Docs Upload', 'Create Offer', 'Offer Initiated', 'Offer Accepted'
    ]
    
    # Base query for candidates in interview process
    candidates_query = db.query(models.Candidate).filter(models.Candidate.current_status.in_(interview_statuses))
    
    # Apply date filters
    if from_date and to_date:
        candidates_query = candidates_query.filter(models.Candidate.application_date.between(from_date, to_date))
    elif from_date:
        candidates_query = candidates_query.filter(models.Candidate.application_date >= from_date)
    elif to_date:
        candidates_query = candidates_query.filter(models.Candidate.application_date <= to_date)
    
    # Apply department filter if provided
    if department and department.lower() != "all":
        candidates_query = candidates_query.filter(models.Candidate.department.ilike(f"%{department}%"))
    
    # Group by department and count candidates
    department_in_process = candidates_query.with_entities(
        models.Candidate.department,
        func.count(models.Candidate.candidate_id).label('count')
    ).group_by(models.Candidate.department).all()
    
    # Calculate totals and percentages
    total = sum(count for _, count in department_in_process)
    departments_count = len(department_in_process)
    
    breakdown = []
    for dept_name, count in department_in_process:
        percentage = round((count / total * 100), 1) if total > 0 else 0.0
        breakdown.append(schemas.DemandSupplyDepartmentBreakdownItem(
            department=dept_name,
            count=int(count) if count else 0,
            percentage=percentage
        ))
    
    # Sort by count descending
    breakdown.sort(key=lambda x: x.count, reverse=True)
    
    return schemas.DemandSupplyDepartmentBreakdownResponse(
        total=total,
        departments=departments_count,
        breakdown=breakdown
    )

@router.get("/demand-supply-stats/gap/department-breakdown", response_model=schemas.DemandSupplyDepartmentBreakdownResponse)
def get_gap_department_breakdown(
    db: Session = Depends(get_db),
    from_date: Optional[date] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)"),
    department: Optional[str] = Query(None, description="Department filter")
):
    """
    Get gap (unfilled positions) breakdown by department.
    Returns count of unfilled positions by department with percentages.
    Gap = Demand - Supply
    """
    # Get demand by department
    jobs_query = db.query(models.Job)
    
    # Apply date filters to jobs
    if from_date and to_date:
        jobs_query = jobs_query.filter(models.Job.created_on.between(from_date, to_date))
    elif from_date:
        jobs_query = jobs_query.filter(models.Job.created_on >= from_date)
    elif to_date:
        jobs_query = jobs_query.filter(models.Job.created_on <= to_date)
    
    # Apply department filter if provided
    if department and department.lower() != "all":
        jobs_query = jobs_query.filter(models.Job.department.ilike(f"%{department}%"))
    
    # Get demand by department
    department_demand = dict(jobs_query.with_entities(
        models.Job.department,
        func.sum(models.Job.no_of_positions).label('count')
    ).group_by(models.Job.department).all())
    
    # Get supply by department
    candidates_query = db.query(models.Candidate).filter(models.Candidate.current_status == 'Onboarded')
    
    # Apply date filters to candidates
    if from_date and to_date:
        candidates_query = candidates_query.filter(models.Candidate.application_date.between(from_date, to_date))
    elif from_date:
        candidates_query = candidates_query.filter(models.Candidate.application_date >= from_date)
    elif to_date:
        candidates_query = candidates_query.filter(models.Candidate.application_date <= to_date)
    
    # Apply department filter if provided
    if department and department.lower() != "all":
        candidates_query = candidates_query.filter(models.Candidate.department.ilike(f"%{department}%"))
    
    # Get supply by department
    department_supply = dict(candidates_query.with_entities(
        models.Candidate.department,
        func.count(models.Candidate.candidate_id).label('count')
    ).group_by(models.Candidate.department).all())
    
    # Calculate gap for each department
    department_gaps = []
    for dept_name in department_demand.keys():
        demand_count = department_demand.get(dept_name, 0)
        supply_count = department_supply.get(dept_name, 0)
        gap = demand_count - supply_count
        
        # Only include departments with positive gaps
        if gap > 0:
            department_gaps.append((dept_name, gap))
    
    # Calculate totals and percentages
    total = sum(gap for _, gap in department_gaps)
    departments_count = len(department_gaps)
    
    breakdown = []
    for dept_name, gap in department_gaps:
        percentage = round((gap / total * 100), 1) if total > 0 else 0.0
        breakdown.append(schemas.DemandSupplyDepartmentBreakdownItem(
            department=dept_name,
            count=int(gap),
            percentage=percentage
        ))
    
    # Sort by count descending
    breakdown.sort(key=lambda x: x.count, reverse=True)
    
    return schemas.DemandSupplyDepartmentBreakdownResponse(
        total=total,
        departments=departments_count,
        breakdown=breakdown
    ) 