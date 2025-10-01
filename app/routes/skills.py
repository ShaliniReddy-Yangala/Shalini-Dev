from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import distinct, func, text
from typing import List, Dict, Set
from collections import defaultdict
import re

from app import database, models, schemas
from app.database import get_db

router = APIRouter(prefix="/skills", tags=["skills"])

def clean_skill(skill: str) -> str:
    """Clean and normalize skill names"""
    if not skill:
        return ""
    # Remove extra whitespace and convert to title case
    return skill.strip().title()

def parse_skills_string(skills_string: str) -> List[str]:
    """Parse comma-separated skills string into list of clean skills"""
    if not skills_string:
        return []
    
    # Split by comma and clean each skill
    skills = [clean_skill(skill) for skill in skills_string.split(',')]
    # Filter out empty skills
    return [skill for skill in skills if skill]

@router.get("/all-comprehensive", response_model=schemas.AllSkillsResponse)
def get_all_skills_comprehensive(db: Session = Depends(get_db)):
    """
    Comprehensive endpoint to fetch all skills from:
    1. Job requisitions (primary_skills, secondary_skills)
    2. JobSkills table (primary_skills, secondary_skills)  
    3. Candidate skills (skills_set)
    
    Returns detailed breakdown with sources and counts.
    """
    try:
        primary_skills_data = defaultdict(list)
        secondary_skills_data = defaultdict(list)
        candidate_skills_data = defaultdict(list)
        
        # 1. Get skills from job_requisitions table
        job_requisitions = db.query(models.Job).filter(
            (models.Job.primary_skills.isnot(None)) | 
            (models.Job.secondary_skills.isnot(None))
        ).all()
        
        for job in job_requisitions:
            if job.primary_skills:
                skills = parse_skills_string(job.primary_skills)
                for skill in skills:
                    primary_skills_data[skill].append(schemas.SkillSource(
                        job_id=job.job_id,
                        job_title=job.job_title,
                        source_type="job_requisition"
                    ))
            
            if job.secondary_skills:
                skills = parse_skills_string(job.secondary_skills)
                for skill in skills:
                    secondary_skills_data[skill].append(schemas.SkillSource(
                        job_id=job.job_id,
                        job_title=job.job_title,
                        source_type="job_requisition"
                    ))
        
        # 2. Get skills from job_skills table (if exists)
        try:
            job_skills = db.query(models.JobSkills).join(
                models.Jobs, models.JobSkills.job_id == models.Jobs.id
            ).all()
            
            for job_skill in job_skills:
                if job_skill.primary_skills:
                    skills = parse_skills_string(job_skill.primary_skills)
                    for skill in skills:
                        primary_skills_data[skill].append(schemas.SkillSource(
                            job_id=str(job_skill.job_id),
                            job_title=job_skill.job.title if job_skill.job else None,
                            source_type="job_skills"
                        ))
                
                if job_skill.secondary_skills:
                    skills = parse_skills_string(job_skill.secondary_skills)
                    for skill in skills:
                        secondary_skills_data[skill].append(schemas.SkillSource(
                            job_id=str(job_skill.job_id),
                            job_title=job_skill.job.title if job_skill.job else None,
                            source_type="job_skills"
                        ))
        except Exception as e:
            print(f"Warning: Could not fetch from job_skills table: {e}")
        
        # 3. Get skills from candidates table
        candidates = db.query(models.Candidate).filter(
            models.Candidate.skills_set.isnot(None),
            models.Candidate.skills_set != ""
        ).all()
        
        for candidate in candidates:
            if candidate.skills_set:
                skills = parse_skills_string(candidate.skills_set)
                for skill in skills:
                    candidate_skills_data[skill].append(schemas.SkillSource(
                        candidate_id=candidate.candidate_id,
                        candidate_name=candidate.candidate_name,
                        source_type="candidate"
                    ))
        
        # 4. Build response data
        primary_skills = [
            schemas.SkillDetail(
                skill=skill,
                total_count=len(sources),
                sources=sources
            )
            for skill, sources in primary_skills_data.items()
        ]
        
        secondary_skills = [
            schemas.SkillDetail(
                skill=skill,
                total_count=len(sources),
                sources=sources
            )
            for skill, sources in secondary_skills_data.items()
        ]
        
        candidate_skills = [
            schemas.SkillDetail(
                skill=skill,
                total_count=len(sources),
                sources=sources
            )
            for skill, sources in candidate_skills_data.items()
        ]
        
        # Get all unique skills
        all_skills_set = set()
        all_skills_set.update(primary_skills_data.keys())
        all_skills_set.update(secondary_skills_data.keys())
        all_skills_set.update(candidate_skills_data.keys())
        
        unique_skills = sorted(list(all_skills_set))
        
        # Sort skills by count (descending)
        primary_skills.sort(key=lambda x: x.total_count, reverse=True)
        secondary_skills.sort(key=lambda x: x.total_count, reverse=True)
        candidate_skills.sort(key=lambda x: x.total_count, reverse=True)
        
        return schemas.AllSkillsResponse(
            primary_skills=primary_skills,
            secondary_skills=secondary_skills,
            candidate_skills=candidate_skills,
            unique_skills=unique_skills,
            total_skills_count=len(unique_skills)
        )
        
    except Exception as e:
        print(f"Error in get_all_skills_comprehensive: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching skills: {str(e)}")

@router.get("/unique", response_model=List[str])
def get_unique_skills_list(db: Session = Depends(get_db)):
    """
    Simple endpoint to get a flat list of all unique skills across the system.
    Useful for dropdowns and autocomplete.
    """
    try:
        all_skills_set = set()
        
        # From job requisitions
        job_requisitions = db.query(models.Job).filter(
            models.Job.skill_set.isnot(None)
        ).all()
        
        for job in job_requisitions:
            if job.skill_set:
                skills = parse_skills_string(job.skill_set)
                all_skills_set.update(skills)
        
        # From job_skills table (if exists)
        try:
            job_skills = db.query(models.JobSkills).all()
            for job_skill in job_skills:
                if job_skill.primary_skills:
                    skills = parse_skills_string(job_skill.primary_skills)
                    all_skills_set.update(skills)
                
                if job_skill.secondary_skills:
                    skills = parse_skills_string(job_skill.secondary_skills)
                    all_skills_set.update(skills)
        except Exception as e:
            print(f"Warning: Could not fetch from job_skills table: {e}")
        
        # From candidates
        candidates = db.query(models.Candidate).filter(
            models.Candidate.skills_set.isnot(None),
            models.Candidate.skills_set != ""
        ).all()
        
        for candidate in candidates:
            if candidate.skills_set:
                skills = parse_skills_string(candidate.skills_set)
                all_skills_set.update(skills)
        
        return sorted(list(all_skills_set))
        
    except Exception as e:
        print(f"Error in get_unique_skills_list: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching unique skills: {str(e)}")

@router.get("/summary", response_model=Dict[str, int])
def get_skills_summary(db: Session = Depends(get_db)):
    """
    Get a summary count of skills from different sources.
    """
    try:
        summary = {
            "total_unique_skills": 0,
            "job_requisition_skills": 0,
            "job_skills_table_skills": 0,
            "candidate_skills": 0,
            "primary_skills_count": 0,
            "secondary_skills_count": 0
        }
        
        all_skills_set = set()
        primary_skills_set = set()
        secondary_skills_set = set()
        candidate_skills_set = set()
        
        # From job requisitions
        job_requisitions = db.query(models.Job).filter(
            (models.Job.primary_skills.isnot(None)) | 
            (models.Job.secondary_skills.isnot(None))
        ).all()
        
        job_req_skills = set()
        for job in job_requisitions:
            if job.primary_skills:
                skills = parse_skills_string(job.primary_skills)
                primary_skills_set.update(skills)
                job_req_skills.update(skills)
                all_skills_set.update(skills)
            
            if job.secondary_skills:
                skills = parse_skills_string(job.secondary_skills)
                secondary_skills_set.update(skills)
                job_req_skills.update(skills)
                all_skills_set.update(skills)
        
        summary["job_requisition_skills"] = len(job_req_skills)
        
        # From job_skills table (if exists)
        try:
            job_skills = db.query(models.JobSkills).all()
            job_skills_set = set()
            for job_skill in job_skills:
                if job_skill.primary_skills:
                    skills = parse_skills_string(job_skill.primary_skills)
                    primary_skills_set.update(skills)
                    job_skills_set.update(skills)
                    all_skills_set.update(skills)
                
                if job_skill.secondary_skills:
                    skills = parse_skills_string(job_skill.secondary_skills)
                    secondary_skills_set.update(skills)
                    job_skills_set.update(skills)
                    all_skills_set.update(skills)
            
            summary["job_skills_table_skills"] = len(job_skills_set)
        except Exception as e:
            print(f"Warning: Could not fetch from job_skills table: {e}")
        
        # From candidates
        candidates = db.query(models.Candidate).filter(
            models.Candidate.skills_set.isnot(None),
            models.Candidate.skills_set != ""
        ).all()
        
        for candidate in candidates:
            if candidate.skills_set:
                skills = parse_skills_string(candidate.skills_set)
                candidate_skills_set.update(skills)
                all_skills_set.update(skills)
        
        summary["candidate_skills"] = len(candidate_skills_set)
        summary["total_unique_skills"] = len(all_skills_set)
        summary["primary_skills_count"] = len(primary_skills_set)
        summary["secondary_skills_count"] = len(secondary_skills_set)
        
        return summary
        
    except Exception as e:
        print(f"Error in get_skills_summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching skills summary: {str(e)}") 