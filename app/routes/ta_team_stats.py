from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date, datetime
from ..database import get_db
from .. import models, schemas
from sqlalchemy import func, or_

router = APIRouter(prefix="/ta-team-stats", tags=["TA Team Stats"])

@router.get("/count", response_model=schemas.TATeamOverview)
def get_ta_team_count(
    db: Session = Depends(get_db),
    department: Optional[str] = Query(None, description="Filter by department name"),
    from_date: Optional[date] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)"),
    overall: bool = Query(False, description="Set to true to get overall metrics across all departments")
):
    """
    Get TA team count statistics with optional filtering by department and date range.
    
    Returns:
    - Total TA Teams: Count of teams
    - Total TA Members: Count of all team members
    - Team Stats: Individual team statistics with candidate counts
    
    Query Parameters:
    - department: Filter by specific department name
    - from_date: Start date for filtering (format: YYYY-MM-DD)
    - to_date: End date for filtering (format: YYYY-MM-DD)
    - overall: Set to true to get metrics across all departments
    """
    try:
        # Total TA teams (not affected by filters as teams are static)
        total_ta_teams = db.query(models.TalentAcquisitionTeam).count()

        # Total TA members (not affected by filters as teams are static)
        total_ta_members = db.query(func.sum(func.cardinality(models.TalentAcquisitionTeam.team_members))).scalar() or 0

        # Get all teams
        teams = db.query(models.TalentAcquisitionTeam).all()
        team_stats = []
        
        for team in teams:
            # Format team name using first names
            first_names = [name.split()[0] for name in team.team_members]
            if len(first_names) > 1:
                team_display_name = f"{', '.join(first_names[:-1])} & {first_names[-1]}'s team"
            elif len(first_names) == 1:
                team_display_name = f"{first_names[0]}'s team"
            else:
                team_display_name = team.team_name
            
            # Create variations of member names for matching
            member_variations = _get_team_member_variations(team.team_members)
            or_conditions = _build_team_involvement_conditions(member_variations)
            
            # Count candidates where this team has been involved
            candidate_query = db.query(models.Candidate).filter(or_(*or_conditions))
            
            # Apply date filters if provided
            if from_date and to_date:
                candidate_query = candidate_query.filter(models.Candidate.application_date.between(from_date, to_date))
            elif from_date:
                candidate_query = candidate_query.filter(models.Candidate.application_date >= from_date)
            elif to_date:
                candidate_query = candidate_query.filter(models.Candidate.application_date <= to_date)
            
            # Apply department filter if provided and not overall
            if department and not overall:
                candidate_query = candidate_query.filter(models.Candidate.department.ilike(f"%{department}%"))
            
            candidate_count = candidate_query.count()

            team_stats.append(schemas.TATeamStats(
                team_id=team.id,
                team_name=team_display_name,
                candidate_count=candidate_count
            ))

        return schemas.TATeamOverview(
            total_ta_teams=total_ta_teams,
            total_ta_members=total_ta_members,
            team_stats=team_stats,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/overview", response_model=schemas.TATeamOverview)
def get_ta_team_overview(
    db: Session = Depends(get_db),
    department: Optional[str] = Query(None, description="Filter by department name"),
    from_date: Optional[date] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)"),
    overall: bool = Query(False, description="Set to true to get overall metrics across all departments")
):
    """
    Get TA team overview with optional filtering by department and date range.
    
    Returns:
    - Total TA Teams: Count of teams
    - Total TA Members: Count of all team members  
    - Team Stats: Individual team statistics with candidate counts
    
    Query Parameters:
    - department: Filter by specific department name
    - from_date: Start date for filtering (format: YYYY-MM-DD)
    - to_date: End date for filtering (format: YYYY-MM-DD)
    - overall: Set to true to get metrics across all departments
    """
    try:
        # Total TA teams (not affected by filters as teams are static)
        total_ta_teams = db.query(models.TalentAcquisitionTeam).count()

        # Total TA members (not affected by filters as teams are static)
        total_ta_members = db.query(func.sum(func.cardinality(models.TalentAcquisitionTeam.team_members))).scalar() or 0

        # Get all teams
        teams = db.query(models.TalentAcquisitionTeam).all()
        team_stats = []
        
        for team in teams:
            # Format team name using first names
            first_names = [name.split()[0] for name in team.team_members]
            if len(first_names) > 1:
                team_display_name = f"{', '.join(first_names[:-1])} & {first_names[-1]}'s team"
            elif len(first_names) == 1:
                team_display_name = f"{first_names[0]}'s team"
            else:
                team_display_name = team.team_name
            
            # Create variations of member names for matching
            member_variations = _get_team_member_variations(team.team_members)
            or_conditions = _build_team_involvement_conditions(member_variations)
            
            # Count candidates where this team has been involved
            candidate_query = db.query(models.Candidate).filter(or_(*or_conditions))
            
            # Apply date filters if provided
            if from_date and to_date:
                candidate_query = candidate_query.filter(models.Candidate.application_date.between(from_date, to_date))
            elif from_date:
                candidate_query = candidate_query.filter(models.Candidate.application_date >= from_date)
            elif to_date:
                candidate_query = candidate_query.filter(models.Candidate.application_date <= to_date)
            
            # Apply department filter if provided and not overall
            if department and not overall:
                candidate_query = candidate_query.filter(models.Candidate.department.ilike(f"%{department}%"))
            
            candidate_count = candidate_query.count()

            team_stats.append(schemas.TATeamStats(
                team_id=team.id,
                team_name=team_display_name,
                candidate_count=candidate_count
            ))

        return schemas.TATeamOverview(
            total_ta_teams=total_ta_teams,
            total_ta_members=total_ta_members,
            team_stats=team_stats,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def _build_ta_team_candidate_query(
    db: Session,
    team: models.TalentAcquisitionTeam,
    search: Optional[str] = None,
    department: Optional[str] = None
):
    """Helper function to build the base query for TA team candidates with filters."""
    # Create member variations for matching
    member_variations = []
    for member in team.team_members:
        member_variations.append(member.lower())
        name_parts = member.split()
        if len(name_parts) >= 2:
            member_variations.append(f"{name_parts[0].lower()}.{name_parts[1].lower()}")
        member_variations.append(name_parts[0].lower())
    
    # Build base OR conditions for team involvement
    or_conditions = [
        func.lower(models.Candidate.ta_team).contains(variation) for variation in member_variations
    ]
    interview_fields = [
        models.Candidate.l1_interviewers_name, models.Candidate.l2_interviewers_name,
        models.Candidate.hr_interviewer_name, models.Candidate.discussion1_done_by,
        models.Candidate.discussion2_done_by, models.Candidate.discussion3_done_by,
        models.Candidate.discussion4_done_by, models.Candidate.discussion5_done_by,
        models.Candidate.discussion6_done_by
    ]
    for field in interview_fields:
        or_conditions.extend([func.lower(field).contains(variation) for variation in member_variations])

    base_query = db.query(models.Candidate).filter(or_(*or_conditions))
    
    # Apply filters
    filters_applied = {}
    
    if search:
        search_filter = f"%{search.lower()}%"
        base_query = base_query.filter(
            or_(
                func.lower(models.Candidate.candidate_name).like(search_filter),
                func.lower(models.Candidate.candidate_id).like(search_filter),
                func.lower(models.Candidate.department).like(search_filter)
            )
        )
        filters_applied["search"] = search
    
    if department:
        base_query = base_query.filter(models.Candidate.department.ilike(f"%{department}%"))
        filters_applied["department"] = department
    
    return base_query, filters_applied

def _get_team_member_variations(team_members):
    """Helper function to get all variations of team member names for matching."""
    member_variations = []
    for member in team_members:
        member_variations.append(member.lower())
        name_parts = member.split()
        if len(name_parts) >= 2:
            member_variations.append(f"{name_parts[0].lower()}.{name_parts[1].lower()}")
        member_variations.append(name_parts[0].lower())
    return member_variations

def _build_team_involvement_conditions(member_variations):
    """Helper function to build OR conditions for team involvement in candidates."""
    or_conditions = [
        func.lower(models.Candidate.ta_team).contains(variation) for variation in member_variations
    ]
    interview_fields = [
        models.Candidate.l1_interviewers_name, models.Candidate.l2_interviewers_name,
        models.Candidate.hr_interviewer_name, models.Candidate.discussion1_done_by,
        models.Candidate.discussion2_done_by, models.Candidate.discussion3_done_by,
        models.Candidate.discussion4_done_by, models.Candidate.discussion5_done_by,
        models.Candidate.discussion6_done_by
    ]
    for field in interview_fields:
        or_conditions.extend([func.lower(field).contains(variation) for variation in member_variations])
    
    return or_conditions

@router.get("/details/{team_id}", response_model=schemas.TATeamDetailedStatsResponse)
def get_ta_team_details(
    team_id: int, 
    page: int = Query(1, ge=1),
    items_per_page: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None, description="Search by candidate name, ID, or department"),
    department: Optional[str] = Query(None, description="Filter by department name"),
    db: Session = Depends(get_db)
):
    """
    Get detailed TA team statistics with filtering and pagination.
    
    Query Parameters:
    - team_id: ID of the TA team
    - page: Page number (starts from 1)
    - items_per_page: Number of items per page (1-100)
    - search: Search term for candidate name, ID, or department
    - department: Filter by specific department name
    """
    try:
        team = db.query(models.TalentAcquisitionTeam).filter(models.TalentAcquisitionTeam.id == team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="TA team not found")
        
        # Format team display name
        first_names = [name.split()[0] for name in team.team_members]
        team_display_name = f"{first_names[0]}'s team"
        if len(first_names) > 1:
            team_display_name = f"{', '.join(first_names[:-1])} & {first_names[-1]}'s team"
        
        # Build base query with filters
        base_query, filters_applied = _build_ta_team_candidate_query(db, team, search, department)
        
        total_candidates = base_query.count()
        
        # Pagination
        if page <= 0:
            raise HTTPException(status_code=400, detail="Page number must be positive.")
        if items_per_page <= 0 or items_per_page > 100:
            raise HTTPException(status_code=400, detail="Items per page must be between 1 and 100.")
        
        offset = (page - 1) * items_per_page
        paginated_candidates = base_query.offset(offset).limit(items_per_page).all()
        
        candidate_details_list = [
            schemas.TATeamCandidateDetails(
                candidate_id=c.candidate_id,
                candidate_name=c.candidate_name,
                department=c.department,
                status=c.current_status
            ) for c in paginated_candidates
        ]
        
        # Get all team candidates for interview round stats (without pagination)
        all_team_candidates = base_query.all()
        
        # Create member variations for matching
        member_variations = _get_team_member_variations(team.team_members)
        
        interview_round_stats = []
        round_definitions = {
            "L1 Interview": [c for c in all_team_candidates if any(variation in (c.l1_interviewers_name or "").lower() for variation in member_variations)],
            "L2 Interview": [c for c in all_team_candidates if any(variation in (c.l2_interviewers_name or "").lower() for variation in member_variations)],
            "HR Round": [c for c in all_team_candidates if any(variation in (c.hr_interviewer_name or "").lower() for variation in member_variations)],
            "Discussions": [c for c in all_team_candidates if any(
                variation in (getattr(c, f"discussion{i}_done_by", None) or "").lower() 
                for variation in member_variations 
                for i in range(1, 7)
            )]
        }
        
        for round_name, candidates in round_definitions.items():
            interview_round_stats.append(schemas.TATeamInterviewRoundStats(
                round_name=round_name,
                count=len(candidates)
            ))
        
        # Create paginated response
        paginated_candidates_response = schemas.PaginatedTeamCandidates(
            total=total_candidates,
            page=page,
            items_per_page=items_per_page,
            items=candidate_details_list
        )
        
        return schemas.TATeamDetailedStatsResponse(
            team_id=team.id,
            team_name=team_display_name,
            total_candidates=total_candidates,
            interview_round_stats=interview_round_stats,
            candidates=paginated_candidates_response,
            filter_applied=filters_applied
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/details/{team_id}/download", response_model=List[schemas.TATeamCandidateDetails])
def get_ta_team_details_download(
    team_id: int,
    search: Optional[str] = Query(None, description="Search by candidate name, ID, or department"),
    department: Optional[str] = Query(None, description="Filter by department name"),
    db: Session = Depends(get_db)
):
    """
    Download all TA team candidate details without pagination.
    """
    try:
        team = db.query(models.TalentAcquisitionTeam).filter(models.TalentAcquisitionTeam.id == team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="TA team not found")
        
        # Build base query with filters
        base_query, _ = _build_ta_team_candidate_query(db, team, search, department)
        
        all_candidates = base_query.all()
        
        candidate_details_list = [
            schemas.TATeamCandidateDetails(
                candidate_id=c.candidate_id,
                candidate_name=c.candidate_name,
                department=c.department,
                status=c.current_status
            ) for c in all_candidates
        ]
        
        return candidate_details_list
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# New TA Team Department Breakdown APIs

@router.get("/total-teams/department-breakdown", response_model=schemas.DemandSupplyDepartmentBreakdownResponse)
def get_total_teams_department_breakdown(
    db: Session = Depends(get_db),
    from_date: Optional[date] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)"),
    department: Optional[str] = Query(None, description="Department filter"),
    overall: Optional[bool] = Query(False, description="Include all departments when true")
):
    """
    Get total TA teams breakdown by department.
    Returns count of TA teams working on each department with percentages.
    """
    try:
        # Get all TA teams
        teams = db.query(models.TalentAcquisitionTeam).all()
        
        # Track which teams work on which departments
        department_teams = {}
        
        for team in teams:
            # Create member variations for matching
            member_variations = _get_team_member_variations(team.team_members)
            or_conditions = _build_team_involvement_conditions(member_variations)
            
            # Base query for candidates this team has worked on
            candidates_query = db.query(models.Candidate).filter(or_(*or_conditions))
            
            # Apply date filters
            if from_date and to_date:
                candidates_query = candidates_query.filter(models.Candidate.application_date.between(from_date, to_date))
            elif from_date:
                candidates_query = candidates_query.filter(models.Candidate.application_date >= from_date)
            elif to_date:
                candidates_query = candidates_query.filter(models.Candidate.application_date <= to_date)
            
            # Apply department filter if provided
            if department and department.lower() != "all" and not overall:
                candidates_query = candidates_query.filter(models.Candidate.department.ilike(f"%{department}%"))
            
            # Get departments this team has worked on
            team_departments = candidates_query.with_entities(models.Candidate.department).distinct().all()
            
            for dept_tuple in team_departments:
                dept_name = dept_tuple[0]
                if dept_name:  # Skip None departments
                    if dept_name not in department_teams:
                        department_teams[dept_name] = set()
                    department_teams[dept_name].add(team.id)
        
        # Calculate counts and percentages
        breakdown = []
        total_teams = len(teams)
        total_assignments = sum(len(team_set) for team_set in department_teams.values())
        departments_count = len(department_teams)
        
        for dept_name, team_set in department_teams.items():
            count = len(team_set)
            percentage = round((count / total_assignments * 100), 1) if total_assignments > 0 else 0.0
            breakdown.append(schemas.DemandSupplyDepartmentBreakdownItem(
                department=dept_name,
                count=count,
                percentage=percentage
            ))
        
        # Sort by count descending
        breakdown.sort(key=lambda x: x.count, reverse=True)
        
        return schemas.DemandSupplyDepartmentBreakdownResponse(
            total=total_assignments,
            departments=departments_count,
            breakdown=breakdown
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/total-members/department-breakdown", response_model=schemas.DemandSupplyDepartmentBreakdownResponse)
def get_total_members_department_breakdown(
    db: Session = Depends(get_db),
    from_date: Optional[date] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)"),
    department: Optional[str] = Query(None, description="Department filter"),
    overall: Optional[bool] = Query(False, description="Include all departments when true")
):
    """
    Get total TA members breakdown by department.
    Returns count of TA members assigned to each department with percentages.
    """
    try:
        # Get all TA teams
        teams = db.query(models.TalentAcquisitionTeam).all()
        
        # Track which departments each team member works on
        department_members = {}
        
        for team in teams:
            # Create member variations for matching
            member_variations = _get_team_member_variations(team.team_members)
            or_conditions = _build_team_involvement_conditions(member_variations)
            
            # Base query for candidates this team has worked on
            candidates_query = db.query(models.Candidate).filter(or_(*or_conditions))
            
            # Apply date filters
            if from_date and to_date:
                candidates_query = candidates_query.filter(models.Candidate.application_date.between(from_date, to_date))
            elif from_date:
                candidates_query = candidates_query.filter(models.Candidate.application_date >= from_date)
            elif to_date:
                candidates_query = candidates_query.filter(models.Candidate.application_date <= to_date)
            
            # Apply department filter if provided
            if department and department.lower() != "all" and not overall:
                candidates_query = candidates_query.filter(models.Candidate.department.ilike(f"%{department}%"))
            
            # Get departments this team has worked on
            team_departments = candidates_query.with_entities(models.Candidate.department).distinct().all()
            
            # If team has worked on any department, count all its members for those departments
            for dept_tuple in team_departments:
                dept_name = dept_tuple[0]
                if dept_name:  # Skip None departments
                    if dept_name not in department_members:
                        department_members[dept_name] = 0
                    department_members[dept_name] += len(team.team_members)
        
        # Calculate counts and percentages
        breakdown = []
        total_member_assignments = sum(department_members.values())
        departments_count = len(department_members)
        
        for dept_name, member_count in department_members.items():
            percentage = round((member_count / total_member_assignments * 100), 1) if total_member_assignments > 0 else 0.0
            breakdown.append(schemas.DemandSupplyDepartmentBreakdownItem(
                department=dept_name,
                count=member_count,
                percentage=percentage
            ))
        
        # Sort by count descending
        breakdown.sort(key=lambda x: x.count, reverse=True)
        
        return schemas.DemandSupplyDepartmentBreakdownResponse(
            total=total_member_assignments,
            departments=departments_count,
            breakdown=breakdown
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/team/{team_id}/department-breakdown", response_model=schemas.TATeamDepartmentBreakdownResponse)
def get_team_department_breakdown(
    team_id: int,
    db: Session = Depends(get_db),
    from_date: Optional[date] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)"),
    department: Optional[str] = Query(None, description="Department filter"),
    overall: Optional[bool] = Query(False, description="Include all departments when true")
):
    """
    Get department-wise distribution of candidates handled by a specific TA team.
    Returns count of candidates from each department handled by the team with percentages.
    """
    try:
        # Get the specific team
        team = db.query(models.TalentAcquisitionTeam).filter(models.TalentAcquisitionTeam.id == team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="TA team not found")
        
        # Format team display name
        first_names = [name.split()[0] for name in team.team_members]
        if len(first_names) > 1:
            team_display_name = f"{', '.join(first_names[:-1])} & {first_names[-1]}'s team"
        elif len(first_names) == 1:
            team_display_name = f"{first_names[0]}'s team"
        else:
            team_display_name = team.team_name
        
        # Create member variations for matching
        member_variations = _get_team_member_variations(team.team_members)
        or_conditions = _build_team_involvement_conditions(member_variations)
        
        # Base query for candidates this team has worked on
        candidates_query = db.query(models.Candidate).filter(or_(*or_conditions))
        
        # Apply date filters
        if from_date and to_date:
            candidates_query = candidates_query.filter(models.Candidate.application_date.between(from_date, to_date))
        elif from_date:
            candidates_query = candidates_query.filter(models.Candidate.application_date >= from_date)
        elif to_date:
            candidates_query = candidates_query.filter(models.Candidate.application_date <= to_date)
        
        # Apply department filter if provided
        if department and department.lower() != "all" and not overall:
            candidates_query = candidates_query.filter(models.Candidate.department.ilike(f"%{department}%"))
        
        # Group by department and count candidates
        department_candidates = candidates_query.with_entities(
            models.Candidate.department,
            func.count(models.Candidate.candidate_id).label('count')
        ).group_by(models.Candidate.department).all()
        
        # Calculate totals and percentages
        total = sum(count for _, count in department_candidates)
        departments_count = len(department_candidates)
        
        breakdown = []
        for dept_name, count in department_candidates:
            if dept_name:  # Skip None departments
                percentage = round((count / total * 100), 1) if total > 0 else 0.0
                breakdown.append(schemas.DemandSupplyDepartmentBreakdownItem(
                    department=dept_name,
                    count=int(count) if count else 0,
                    percentage=percentage
                ))
        
        # Sort by count descending
        breakdown.sort(key=lambda x: x.count, reverse=True)
        
        return schemas.TATeamDepartmentBreakdownResponse(
            total=total,
            departments=departments_count,
            team_name=team_display_name,
            breakdown=breakdown
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 