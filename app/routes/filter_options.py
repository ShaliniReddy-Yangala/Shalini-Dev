from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app import models  # for optional JobSkills usage and TalentAcquisitionTeam
from app.routes.skills import parse_skills_string  # reuse same skills parsing
from app.models import (
    Candidate,
    StatusDB,
    FinalStatusDB,
    Department,
    InterviewStatusDB,
    Job,
    RatingDB,
    TATeam,
)

router = APIRouter(prefix="/filters", tags=["filters"])


@router.get("/options", response_model=dict)
def get_filter_options(db: Session = Depends(get_db)):
    """Return filter option lists only, aggregated from multiple tables, optimized for speed."""

    # Current statuses
    current_status_values = [
        s[0]
        for s in db.query(StatusDB.status)
        .order_by(StatusDB.weight.asc())
        .all()
        if s[0]
    ]

    # Final statuses
    final_status_values = [
        s[0]
        for s in db.query(FinalStatusDB.status)
        .order_by(FinalStatusDB.weight.asc())
        .all()
        if s[0]
    ]

    # Departments
    department_values = [
        d[0]
        for d in db.query(Department.name)
        .order_by(Department.name.asc())
        .all()
        if d[0]
    ]

    # Interview statuses
    interview_status_values = [
        s[0]
        for s in db.query(InterviewStatusDB.status)
        .order_by(InterviewStatusDB.weight.asc())
        .all()
        if s[0]
    ]

    # Open jobs (from job_requisitions)
    open_jobs = [
        {"job_id": j[0], "job_title": j[1]}
        for j in db.query(Job.job_id, Job.job_title)
        .filter(Job.status == "OPEN")
        .order_by(Job.created_on.desc())
        .all()
    ]

    # Ratings (static table)
    rating_values = [
        r[0]
        for r in db.query(RatingDB.rating)
        .order_by(RatingDB.id.asc())
        .all()
        if r[0]
    ]

    # TA team members (same as /TAteam/get_ta_team endpoint)
    ta_teams = db.query(models.TalentAcquisitionTeam).order_by(models.TalentAcquisitionTeam.weight).all()
    ta_member_set = set()
    for team in ta_teams:
        if team.team_members:
            for member in team.team_members:
                if member and member.strip():
                    ta_member_set.add(member.strip())
    ta_team_members_values = sorted(ta_member_set)

    # Referred by (distinct non-null from candidates)
    referred_by_values = [
        v[0]
        for v in db.query(Candidate.referred_by).distinct().all()
        if v[0]
    ]
    referred_by_values.sort()

    # Created by (distinct non-null emails in candidates.created_by)
    created_by_values = [
        v[0]
        for v in db.query(Candidate.created_by).distinct().all()
        if v[0]
    ]
    created_by_values.sort()

    # Updated by (distinct non-null emails in candidates.updated_by)
    updated_by_values = [
        v[0]
        for v in db.query(Candidate.updated_by).distinct().all()
        if v[0]
    ]
    updated_by_values.sort()

    # Unique skills (same data as /skills/unique)
    all_skills_set = set()

    # From job requisitions skill_set
    job_requisitions = db.query(Job).filter(Job.skill_set.isnot(None)).all()
    for job in job_requisitions:
        if job.skill_set:
            skills = parse_skills_string(job.skill_set)
            all_skills_set.update(skills)

    # From job_skills table if exists
    try:
        job_skills_rows = db.query(models.JobSkills).all()
        for job_skill in job_skills_rows:
            if getattr(job_skill, 'primary_skills', None):
                all_skills_set.update(parse_skills_string(job_skill.primary_skills))
            if getattr(job_skill, 'secondary_skills', None):
                all_skills_set.update(parse_skills_string(job_skill.secondary_skills))
    except Exception as e:
        # Table may not exist in some deployments; ignore gracefully
        pass    

    # From candidates
    candidates_with_skills = db.query(Candidate).filter(
        Candidate.skills_set.isnot(None),
        Candidate.skills_set != ""
    ).all()
    for c in candidates_with_skills:
        if c.skills_set:
            all_skills_set.update(parse_skills_string(c.skills_set))

    skills_unique_values = sorted(list(all_skills_set))

    return {
        "current_status": {"values": current_status_values},
        "final_status": {"values": final_status_values},
        "department": {"values": department_values},
        "interview_status": {"values": interview_status_values},
        "open_jobs": {"values": open_jobs},
        "ratings": {"values": rating_values},
        "ta_team_members": {"values": ta_team_members_values},
        "referred_by": {"values": referred_by_values},
        "created_by": {"values": created_by_values},
        "updated_by": {"values": updated_by_values},
        "skills_unique": {"values": skills_unique_values},
    }


