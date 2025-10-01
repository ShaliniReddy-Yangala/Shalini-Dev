from fastapi import APIRouter, Body, Depends, HTTPException, Path ,Query, status
from sqlalchemy.orm import Session
from sqlalchemy import case, text
from typing import List, Optional
from sqlalchemy.sql import func
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel 
import bleach
from app.models import Candidate, CandidateProgress, JobTypeDB, ModeDB, Discussion, Job, Department, Jobs, JobSkills, Client, PriorityDB, RequisitionTypeDB
from app.dependencies import get_current_user  
import logging
from bleach.css_sanitizer import CSSSanitizer



from .. import models, schemas, database

router = APIRouter(prefix="/jobs", tags=["jobs"])
logger = logging.getLogger(__name__)

CSS_ALLOWED = [
    'color', 'background-color', 'font-weight', 'text-align',
    'margin', 'margin-top', 'margin-bottom', 'margin-left', 'margin-right',
    'padding', 'padding-top', 'padding-bottom', 'padding-left', 'padding-right'
]

css_sanitizer = CSSSanitizer(allowed_css_properties=CSS_ALLOWED)

# Define allowed HTML tags and attributes for rich text formatting
ALLOWED_TAGS = [
    'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
    'ul', 'ol', 'li', 'strong', 'em', 'b', 'i', 
    'u', 'br', 'span', 'div', 'table', 'tr', 'td', 
    'th', 'tbody', 'thead', 'blockquote'
]
ALLOWED_ATTRIBUTES = {
    '*': ['class', 'style'],
    'a': ['href', 'target', 'rel'],
    'img': ['src', 'alt', 'width', 'height'],
    'td': ['colspan', 'rowspan'],
    'th': ['colspan', 'rowspan']
}

def sanitize_html(html_content):
    """Sanitize HTML content to prevent XSS attacks while preserving formatting"""
    if not html_content:
        return None
        
    return bleach.clean(
        html_content,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=False,
        css_sanitizer=css_sanitizer  # Add this line
    )

class PaginatedJobResponse(BaseModel):
    jobs: List[schemas.JobListResponse]
    total_jobs: int
    total_pages: int
    current_page: int
    limit: int

@router.post("/", response_model=dict, status_code=201)
def create_job(job_data: schemas.JobCreate, db: Session = Depends(database.get_db)):
    """
    Creates a new job based on the provided data
    """
    try:
        # Perform your existing validations
        if job_data.requisition_type == "Replacement" and not job_data.employee_to_be_replaced:
            raise HTTPException(
                status_code=400, 
                detail="Employee to be replaced is required for replacement requisitions"
            )

        if job_data.priority =="High" and not job_data.target_hiring_date:
                    raise HTTPException(
                        status_code=400, 
                        detail="Target hiring date is required for high priority requisitions"
                    )

        # Sanitize the HTML in job_description and additional_notes
        sanitized_job_description = sanitize_html(job_data.job_description)
        sanitized_additional_notes = sanitize_html(job_data.additional_notes)

        # Create new job object (same as your existing code but with sanitized description)
        new_job = models.Job(
            job_title=job_data.job_title,
            no_of_positions=job_data.no_of_positions,
            requisition_type=job_data.requisition_type,
            employee_to_be_replaced=job_data.employee_to_be_replaced,
            job_type=job_data.job_type,
            # primary_skills=job_data.primary_skills,
            # secondary_skills=job_data.secondary_skills,
            skill_set=job_data.skill_set,
            department=job_data.department,
            required_experience_min=job_data.required_experience_min,
            required_experience_max=job_data.required_experience_max,
            ctc_budget_min=job_data.ctc_budget_min,
            ctc_budget_max=job_data.ctc_budget_max,
            mode_of_work=job_data.mode_of_work,
            office_location=job_data.office_location or "Hyderabad",
            job_description=sanitized_job_description,  
            target_hiring_date=datetime.strptime(job_data.target_hiring_date, '%d-%m-%Y').date() if job_data.target_hiring_date else None,
            priority=job_data.priority, 
            client_name=job_data.client_name,
            head_of_department=job_data.head_of_department,
            additional_notes=sanitized_additional_notes,
            # reason_for_hiring=job_data.reason_for_hiring,
            created_by=job_data.created_by,
            created_on=job_data.created_on,
            status=job_data.status,
            
            

        )

        # # Business rule for reason_for_hiring based on client_name
        # if not new_job.reason_for_hiring and new_job.client_name:
        #     new_job.reason_for_hiring = f"Hiring for client: {new_job.client_name}"

        db.add(new_job)
        db.commit()
        db.refresh(new_job)

        return {
            'message': 'Job requisition created successfully',
            'job_id': new_job.job_id,
            'id': new_job.id
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/job-titles", response_model=List[schemas.JobListResponse])
def get_job_titles(db: Session = Depends(database.get_db)):
    """
    Get a list of all job IDs with their titles
    Returns:
        List of objects containing job_id and job_title for all jobs
    """
    try:
        # Query all jobs with only the fields we need
        jobs = db.query(models.Job).all()
        
        if not jobs:
            raise HTTPException(status_code=404, detail="No jobs found")
            
        # Format the response to match JobListResponse schema
        result = []
        for job in jobs:
            result.append({
                "id": job.id,
                "job_id": job.job_id,
                "job_title": job.job_title,
                "no_of_positions": job.no_of_positions or 0,
                "requisition_type": job.requisition_type or "",
                "job_type": job.job_type or "",
                "department": job.department or "",
                "required_experience_min": job.required_experience_min or 0,
                "required_experience_max": job.required_experience_max or 0,
                "mode_of_work": job.mode_of_work or "",
                "office_location": job.office_location or "",
                "status": job.status or ""
            })
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/all-jobs-simple", response_model=List[dict])
def get_all_jobs_simple(db: Session = Depends(database.get_db)):
    """
    Get all jobs with only job_id and job_title
    Returns:
        List of objects containing only job_id and job_title for all jobs
    """
    try:
        # Query all jobs with only the fields we need
        jobs = db.query(models.Job).all()
        
        if not jobs:
            raise HTTPException(status_code=404, detail="No jobs found")
            
        # Format the response to return only job_id and job_title
        result = []
        for job in jobs:
            result.append({
                "job_id": job.job_id,
                "job_title": job.job_title
            })
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))    
    
    
@router.get("/all-jobs", response_model=List[schemas.JobListMinimal])
def get_all_jobs(db: Session = Depends(database.get_db)):
    """
    Get all jobs with minimal data (title, department, created_at, created_by, updated_at, updated_by)
    """
    try:
        jobs = db.query(Jobs).all()
        if not jobs:
            raise HTTPException(status_code=404, detail="No jobs found")
        # Return the required fields
        return [
            {
                "id": job.id,
                "title": job.title,
                "department_id": job.department_id,
                "created_at": job.created_at,
                "created_by": job.created_by,
                "updated_at": job.updated_at,
                "updated_by": job.updated_by
            }
            for job in jobs
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/job-title/{job_id}", response_model=dict)
def get_job_title_by_id(job_id: str, db: Session = Depends(database.get_db)):
    """
    Get job title by job ID
    """
    try:
        job = db.query(Job).filter(Job.job_id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {"job_title": job.job_title}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/job-titles", response_model=List[schemas.JobTitleMinimal])
def get_job_titles(db: Session = Depends(database.get_db)):
    """
    Get all job titles with their IDs from job_requisitions table
    """
    try:
        jobs = db.query(Job).all()  # Query Job model
        if not jobs:
            raise HTTPException(status_code=404, detail="No jobs found")
        # Return only id and job_title
        return [
            {
                "id": job.id,
                "job_title": job.job_title
            }
            for job in jobs
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))    
    
@router.get("/job/{job_id}", response_model=schemas.JobRead)
def get_job(job_id: int, db: Session = Depends(database.get_db)):
    """
    Get detailed information for a specific job by ID
    """
    try:
        job = db.query(Jobs).get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))    


@router.get("/", response_model=PaginatedJobResponse)
def get_jobs(
    job_title: Optional[str] = None,
    job_id: Optional[str] = None,
    status: Optional[str] = None,
    department: Optional[str] = None,
    created_from: Optional[str] = None,
    created_to: Optional[str] = None,
    updated_from: Optional[str] = None,  # New filter for updated date
    updated_to: Optional[str] = None, 
    skill: Optional[str] = None,
    office_location: Optional[str] = None,
    ctc_min: Optional[float] = None,
    ctc_max: Optional[float] = None,
    job_type: Optional[str] = None,
    priority: Optional[str] = None,
    sort: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(database.get_db)
):
    try:
        offset = (page - 1) * limit
        query = db.query(models.Job)

        # Apply filters
        if job_title:
            query = query.filter(models.Job.job_title.ilike(f'%{job_title}%'))

        if job_id:
            query = query.filter(models.Job.job_id.ilike(f'%{job_id}%'))

        if status:
            query = query.filter(models.Job.status.ilike(status))

        if department:
            query = query.filter(models.Job.department == department)

        if office_location:
            query = query.filter(models.Job.office_location == office_location)

        if priority:
            query = query.filter(models.Job.priority.ilike(priority))

        if created_from:
            try:
                from_date = datetime.strptime(created_from, '%d-%m-%Y').date()
                query = query.filter(models.Job.created_on >= from_date)
            except ValueError:
                raise HTTPException(status_code=400, detail='Invalid created_from date format. Use DD-MM-YYYY')

        if created_to:
            try:
                to_date = datetime.strptime(created_to, '%d-%m-%Y').date()
                to_date_end = to_date + timedelta(days=1)
                query = query.filter(models.Job.created_on < to_date_end)
            except ValueError:
                raise HTTPException(status_code=400, detail='Invalid created_to date format. Use DD-MM-YYYY')
        # New filters for updated date
        if updated_from:
            try:
                from_date = datetime.strptime(updated_from, '%d-%m-%Y').date()
                query = query.filter(models.Job.updated_on >= from_date)
            except ValueError:
                raise HTTPException(status_code=400, detail='Invalid updated_from date format. Use DD-MM-YYYY')

        if updated_to:
            try:
                to_date = datetime.strptime(updated_to, '%d-%m-%Y').date()
                to_date_end = to_date + timedelta(days=1)
                query = query.filter(models.Job.updated_on < to_date_end)
            except ValueError:
                raise HTTPException(status_code=400, detail='Invalid updated_to date format. Use DD-MM-YYYY')

        # if skill:
        #     skills = [s.strip() for s in skill.split(',') if s.strip()]
        #     for s in skills:
        #         query = query.filter(
        #             (models.Job.primary_skills.ilike(f'%{s}%')) | 
        #             (models.Job.secondary_skills.ilike(f'%{s}%'))
        #         )
        if skill:
            skills = [s.strip() for s in skill.split(',') if s.strip()]
            for s in skills:
                query = query.filter(models.Job.skill_set.ilike(f'%{s}%'))

        if ctc_min is not None:
            query = query.filter(models.Job.ctc_budget_min >= ctc_min)

        if ctc_max is not None:
            query = query.filter(models.Job.ctc_budget_max <= ctc_max)

        if job_type:
            query = query.filter(models.Job.job_type.ilike(job_type))

        # Apply sorting
        if sort == 'created_on_desc':
            query = query.order_by(models.Job.created_on.desc())
        elif sort == 'created_on_asc':
            query = query.order_by(models.Job.created_on.asc())
        elif sort == 'updated_on_desc':
            query = query.order_by(models.Job.updated_on.desc())
        elif sort == 'updated_on_asc':
            query = query.order_by(models.Job.updated_on.asc())
        elif sort == 'job_title_asc':
            query = query.order_by(models.Job.job_title.asc())
        elif sort == 'job_title_desc':
            query = query.order_by(models.Job.job_title.desc())
        else:
            query = query.order_by(models.Job.created_on.desc())  # Default sorting

        # Get total count and paginate
        total_jobs = query.count()
        jobs = query.offset(offset).limit(limit).all()

        # Format response
        result = []
        for job in jobs:
            job_dict = {
                'id': job.id,
                'job_id': job.job_id,
                'job_title': job.job_title,
                'no_of_positions': job.no_of_positions,
                'requisition_type': job.requisition_type,
                'employee_to_be_replaced': job.employee_to_be_replaced,
                'job_type': job.job_type,
                # 'primary_skills': job.primary_skills,
                # 'secondary_skills': job.secondary_skills,
                'skill_set': job.skill_set,
                'department': job.department,
                'required_experience_min': job.required_experience_min,
                'required_experience_max': job.required_experience_max,
                'mode_of_work': job.mode_of_work,
                'office_location': job.office_location,
                'status': job.status,
                'created_by':job.created_by,
                'created_by':job.created_by,
                'created_on': job.created_on.isoformat() if job.created_on else None,
                'updated_on': job.updated_on.isoformat() if job.updated_on else None,  # New field
                'updated_by': job.updated_by,  # New field
                'target_hiring_date': job.target_hiring_date.isoformat() if job.target_hiring_date else None,
                'priority': job.priority,
                'ctc_budget_min': job.ctc_budget_min,
                'ctc_budget_max': job.ctc_budget_max
            }
            result.append(schemas.JobListResponse(**job_dict))

        return {
            "jobs": result,
            "total_jobs": total_jobs,
            "total_pages": (total_jobs + limit - 1) // limit,
            "current_page": page,
            "limit": limit
        }
    except Exception as e:
        import traceback
        error_detail = f"Error in get_jobs: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)  # Log the full error for debugging
        raise HTTPException(status_code=500, detail=str(e))



################################ SKILLS ROUTES (Must be before generic /{job_id} route) ################################

# Update a specific skill
@router.put("/skill/{skill_id}", response_model=dict)
def update_skill(skill_id: int, update_data: schemas.JobSkillUpdate, db: Session = Depends(database.get_db)):
    try:
        skill = db.query(JobSkills).get(skill_id)
        if not skill:
            raise HTTPException(status_code=404, detail="Skill not found")

        if update_data.job_id is not None:
            job = db.query(Jobs).filter(Jobs.id == update_data.job_id).first()
            if not job:
                raise HTTPException(status_code=400, detail="Job not found")

        for key, value in update_data.model_dump(exclude_unset=True).items():
            setattr(skill, key, value)

        # Set updated_by to given value or default to "taadmin"
        skill.updated_by = update_data.updated_by or "taadmin"
        skill.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(skill)

        job_title = db.query(Jobs.title).filter(Jobs.id == skill.job_id).scalar()
        return format_skill_response_with_skillset_only(skill, job_title)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# Delete a specific skill
@router.delete("/skill/{skill_id}", response_model=dict)
def delete_skill(skill_id: int, db: Session = Depends(database.get_db)):
    try:
        skill = db.query(JobSkills).get(skill_id)
        if not skill:
            raise HTTPException(status_code=404, detail="Skill not found")
        db.delete(skill)
        db.commit()
        return {"detail": "Skill deleted successfully"}
    except Exception as e:  
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# Create new skills
@router.post("/create-skill/", response_model=dict)
def create_skill(skill: schemas.JobSkillCreate, db: Session = Depends(database.get_db)):
    try:
        print(f"Received skill data: {skill.model_dump()}")
        
        # Check if the job exists
        job = db.query(Jobs).filter(Jobs.id == skill.job_id).first()
        if job is None:
            raise HTTPException(status_code=400, detail="Job not found")

        # Create a new skill (no skill_set column in database)
        skill_data = skill.model_dump()
        
        # Set created_by to provided value or default to "taadmin" instead of "system"
        skill_data["created_by"] = skill_data.get("created_by") or "taadmin"
        
        print(f"Creating skill with data: {skill_data}")
        
        db_skill = JobSkills(**skill_data)
        db.add(db_skill)
        db.commit()
        db.refresh(db_skill)
        
        # Get job title for response
        job_title = db.query(Jobs.title).filter(Jobs.id == db_skill.job_id).scalar()
        
        # Return response with ONLY skill_set (no individual skills)
        return format_skill_response_with_skillset_only(db_skill, job_title)
        
    except Exception as e:
        db.rollback()
        print(f"Error creating skill: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating skill: {str(e)}")

# Bulk create skills - returns only skill_set
@router.post("/bulk-create-skills/", response_model=List[dict])
def bulk_create_skills(skills_data: List[schemas.JobSkillCreate], db: Session = Depends(database.get_db)):
    """
    Create multiple skills at once for jobs.
    Returns skills with ONLY combined skill_set (no individual skills).
    """
    try:
        created_skills = []
        
        for skill_data in skills_data:
            # Check if the job exists
            job = db.query(Jobs).filter(Jobs.id == skill_data.job_id).first()
            if job is None:
                raise HTTPException(status_code=400, detail=f"Job with ID {skill_data.job_id} not found")

            # Create a new skill with proper created_by handling
            skill_dict = skill_data.model_dump()
            skill_dict["created_by"] = skill_dict.get("created_by") or "taadmin"
            
            db_skill = JobSkills(**skill_dict)
            db.add(db_skill)
            created_skills.append(db_skill)
        
        db.commit()
        
        # Refresh all created skills and format response with ONLY skill_set
        result = []
        for skill in created_skills:
            db.refresh(skill)
            job_title = db.query(Jobs.title).filter(Jobs.id == skill.job_id).scalar()
            result.append(format_skill_response_with_skillset_only(skill, job_title))
        
        return result
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# Get all skills with combined skill_set - returns only skill_set
@router.get("/skills/with-job-titles", response_model=List[dict])
def get_all_skills_with_job_titles(db: Session = Depends(database.get_db)):
    """
    Get all skills with their combined skill_set ONLY.
    Does not return individual primary/secondary skills.
    """
    try:
        skills = (
            db.query(JobSkills, Jobs.title.label("job_title"))
            .join(Jobs, JobSkills.job_id == Jobs.id)
            .all()
        )
        
        if not skills:
            return []

        result = []
        for skill, job_title in skills:
            result.append(format_skill_response_with_skillset_only(skill, job_title))

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get all primary skills across all jobs with skill_set
@router.get("/skills/primary/all", response_model=List[dict])
def get_all_primary_skills(db: Session = Depends(database.get_db)):
    try:
        skills = (
            db.query(JobSkills, Jobs.title.label("job_title"))
            .join(Jobs, JobSkills.job_id == Jobs.id)
            .filter(JobSkills.primary_skills.isnot(None))
            .all()
        )
        
        if not skills:
            return []

        result = []
        for skill, job_title in skills:
            result.append({
                "id": skill.id,
                "primary_skills": skill.primary_skills,
                "secondary_skills": None,
                "skill_set": skill.primary_skills,  # Only primary skills
                "job_id": skill.job_id,
                "job_title": job_title,
                "created_at": skill.created_at.isoformat() if skill.created_at else None,
                "updated_at": skill.updated_at.isoformat() if skill.updated_at else None,
            })

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get all secondary skills across all jobs with skill_set
@router.get("/skills/secondary/all", response_model=List[dict])
def get_all_secondary_skills(db: Session = Depends(database.get_db)):
    try:
        skills = (
            db.query(JobSkills, Jobs.title.label("job_title"))
            .join(Jobs, JobSkills.job_id == Jobs.id)
            .filter(JobSkills.secondary_skills.isnot(None))
            .all()
        )
        
        if not skills:
            return []

        result = []
        for skill, job_title in skills:
            result.append({
                "id": skill.id,
                "primary_skills": None,
                "secondary_skills": skill.secondary_skills,
                "skill_set": skill.secondary_skills,  # Only secondary skills
                "job_id": skill.job_id,
                "job_title": job_title,
                "created_at": skill.created_at.isoformat() if skill.created_at else None,
                "updated_at": skill.updated_at.isoformat() if skill.updated_at else None,
            })

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get all skills with combined skill_set (backward compatibility)
@router.get("/skills/all", response_model=List[dict])
def get_all_skills(db: Session = Depends(database.get_db)):
    try:
        skills = (
            db.query(JobSkills, Jobs.title.label("job_title"))
            .join(Jobs, JobSkills.job_id == Jobs.id)
            .all()
        )
        
        if not skills:
            return []

        result = []
        for skill, job_title in skills:
            result.append(format_skill_response_with_skillset(skill, job_title))

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# CLEANUP ENDPOINT - Delete all skills data
@router.delete("/skills/cleanup/all")
def cleanup_all_skills(db: Session = Depends(database.get_db)):
    """
    DANGER: This endpoint will delete ALL skills data from the job_skills table.
    Use with caution - this action cannot be undone!
    """
    try:
        # Count existing records before deletion
        count_before = db.query(JobSkills).count()
        
        # Delete all records from job_skills table
        deleted_count = db.query(JobSkills).delete()
        db.commit()
        
        return {
            "message": "All skills data has been successfully deleted",
            "records_deleted": deleted_count,
            "count_before_deletion": count_before,
            "table_cleaned": "job_skills"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error cleaning up skills data: {str(e)}")

# CLEANUP ENDPOINT - Reset skills auto-increment ID
@router.post("/skills/cleanup/reset-ids")
def reset_skills_auto_increment(db: Session = Depends(database.get_db)):
    """
    Reset the auto-increment counter for the job_skills table to start from 1 again.
    Use this after cleanup to ensure clean ID sequence.
    """
    try:
        # Reset the auto-increment sequence for PostgreSQL
        db.execute(text("ALTER SEQUENCE job_skills_id_seq RESTART WITH 1"))
        db.commit()
        
        return {
            "message": "Auto-increment sequence reset successfully",
            "table": "job_skills",
            "next_id": 1
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error resetting auto-increment: {str(e)}")

# CLEANUP ENDPOINT - Soft cleanup (set skills to NULL instead of deleting records)
@router.put("/skills/cleanup/soft")
def soft_cleanup_skills(db: Session = Depends(database.get_db)):
    """
    Soft cleanup: Set all primary_skills and secondary_skills to NULL instead of deleting records.
    This preserves the records but clears the skill data.
    """
    try:
        # Count existing records with skills data
        count_with_skills = db.query(JobSkills).filter(
            (JobSkills.primary_skills.isnot(None)) | 
            (JobSkills.secondary_skills.isnot(None))
        ).count()
        
        # Update all records to set skills to NULL
        updated_count = db.query(JobSkills).update({
            JobSkills.primary_skills: None,
            JobSkills.secondary_skills: None
        })
        
        db.commit()
        
        return {
            "message": "Soft cleanup completed - all skills data cleared but records preserved",
            "records_updated": updated_count,
            "records_with_skills_before": count_with_skills,
            "table": "job_skills",
            "action": "set_skills_to_null"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error during soft cleanup: {str(e)}")

# Helper function to combine skills dynamically
def combine_skills(primary_skills, secondary_skills):
    """
    Combines primary and secondary skills into a single skill_set string.
    Primary skills are displayed first, followed by secondary skills.
    No physical skill_set column needed in database.
    """
    skills = []
    
    # Add primary skills first
    if primary_skills:
        primary_list = [skill.strip() for skill in primary_skills.split(',') if skill.strip()]
        skills.extend(primary_list)
    
    # Add secondary skills after primary
    if secondary_skills:
        secondary_list = [skill.strip() for skill in secondary_skills.split(',') if skill.strip()]
        skills.extend(secondary_list)
    
    return ', '.join(skills) if skills else None

# Enhanced response formatting function - Returns only skill_set
def format_skill_response_with_skillset_only(skill, job_title):
    """
    Format skill response with ONLY dynamically combined skill_set field
    Excludes primary_skills and secondary_skills from response
    """
    skill_set = combine_skills(skill.primary_skills, skill.secondary_skills)
    
    return {
        "id": skill.id,
        "skill_set": skill_set,  # Only the combined skill set
        "job_id": skill.job_id,
        "job_title": job_title,
        "therapeutic_area": getattr(skill, "therapeutic_area", None),
        "created_at": skill.created_at.isoformat() if skill.created_at else None,
        "updated_at": skill.updated_at.isoformat() if skill.updated_at else None,
    }

# Alternative: Keep the original function but add a parameter to control what to include
def format_skill_response_with_skillset(skill, job_title, include_individual_skills=False):
    """
    Format skill response with dynamically combined skill_set field
    """
    skill_set = combine_skills(skill.primary_skills, skill.secondary_skills)
    
    response = {
        "id": skill.id,
        "skill_set": skill_set,  # Dynamically combined: primary + secondary
        "job_id": skill.job_id,
        "job_title": job_title,
        "therapeutic_area": getattr(skill, "therapeutic_area", None),
        "created_at": skill.created_at.isoformat() if skill.created_at else None,
        "updated_at": skill.updated_at.isoformat() if skill.updated_at else None,
    }
    
    # Only include individual skills if requested
    if include_individual_skills:
        response["primary_skills"] = skill.primary_skills
        response["secondary_skills"] = skill.secondary_skills
    
    return response

################################ END SKILLS ROUTES ################################

@router.put("/{job_id}", response_model=dict)
def update_job(job_id: str, job_update: schemas.JobUpdate, db: Session = Depends(database.get_db)):
    """
    Updates an existing job requisition 
    """
    # Find the job - modified to handle JR009XXXXX format
    job = db.query(models.Job).filter(models.Job.job_id == job_id).first()


    if not job:
        raise HTTPException(status_code=404, detail="Job requisition not found")

    try:
        # Update fields if provided
        update_data = job_update.dict(exclude_unset=True)
        
        # Sanitize HTML fields
        if 'job_description' in update_data and update_data['job_description']:
            update_data['job_description'] = sanitize_html(update_data['job_description'])
        if 'additional_notes' in update_data and update_data['additional_notes']:
            update_data['additional_notes'] = sanitize_html(update_data['additional_notes'])
        
        # Parse updated_on if provided, otherwise use current datetime
        if 'updated_on' in update_data and update_data['updated_on']:
            try:
                update_data['updated_on'] = datetime.strptime(update_data['updated_on'], '%d-%m-%Y %H:%M:%S')
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format for updated_on. Use DD-MM-YYYY HH:MM:SS")
        else:
            update_data['updated_on'] = datetime.utcnow()
        
        for key, value in update_data.items():
            if key == 'updated_by':
                continue
            # Handle date format conversion for target_hiring_date
            if key == 'target_hiring_date' and value:
                try:
                    # Try ISO format (YYYY-MM-DD) first
                    value = datetime.strptime(value, '%Y-%m-%d').date()
                except ValueError:
                    # Fallback to DD-MM-YYYY
                    try:
                        value = datetime.strptime(value, '%d-%m-%Y').date()
                    except ValueError:
                        raise HTTPException(status_code=400, detail="Invalid date format for target_hiring_date. Use YYYY-MM-DD or DD-MM-YYYY")
            # Convert numeric fields to integers
            elif key in ['ctc_budget_min', 'ctc_budget_max', 'no_of_positions', 'required_experience_min', 'required_experience_max']:
                if value is not None and value != '':
                    try:
                        value = int(float(value))  # Handle string or float inputs
                    except (ValueError, TypeError):
                        raise HTTPException(status_code=400, detail=f"Invalid value for {key}: must be a number")
                else:
                    value = None  # Handle empty strings or null
            setattr(job, key, value)
        
        # Clear employee_to_be_replaced if requisition_type is not Replacement
        if 'requisition_type' in update_data and job.requisition_type != "Replacement":
            job.employee_to_be_replaced = None
            
        # Check if target_hiring_date is required for high priority
# Validation logic (this part is fine)
        if (update_data.get('priority') == "High" or 
            (job.priority == "High" and 'priority' not in update_data)) and not job.target_hiring_date:
            raise HTTPException(
                status_code=400, 
                detail="Target hiring date is required for high priority requisitions"
            )
            
        job.updated_by = update_data.get('updated_by', 'taadmin')
        job.updated_on = update_data['updated_on']
        
        db.commit()
        db.refresh(job)
        
        return {'message': 'Job requisition updated successfully'}
    except ValueError as ve:
        db.rollback()
        logger.error(f"Error updating job {job_id}: {str(ve)}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Invalid data format: {str(ve)}")
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update job: {str(e)}")
    
##### notification - functionality #####

def create_notification_for_job(db: Session, user_id: str, job_id: str, notification_type: str="Job Approval"):
    """
    Create a notification for a job action
    """
    job = db.query(models.Job).filter(models.Job.job_id == job_id).first()
    if not job:
        return
    
    if notification_type == "JOB_APPROVAL":
        notification = models.Notification(
            user_id=user_id,
            notification_type=notification_type,
            title=f"TA team has approved {job.job_title} job post",
            message=f"Job requisition for {job.job_title} ({job.job_id}) has been approved by the TA team",
            job_id=job_id,
            is_read=False
        )
    
    db.add(notification)
    db.commit()


#########################closed functionality

@router.put("/{job_id}/close", response_model=dict)
async def close_job(
    job_id: str,
    db: Session = Depends(database.get_db)
):
    """
    Endpoint to close a job by setting its status to CLOSED
    """
    try:
        # Check if job exists
        job = db.query(models.Job).filter(models.Job.job_id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail=f"Job with ID {job_id} not found")
        
        # Update job status to CLOSED
        job.status = "CLOSED"
        job.closed_on = datetime.now().date()
        job.closed_by = "System"

        db.commit()
        db.refresh(job)
        
        return {
            "message": "Job closed successfully",
            "job_id": job_id,
            "status": "CLOSED"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
#####################Department
@router.post("/create/department/", response_model=schemas.DepartmentRead)
async def create_department(department: schemas.DepartmentCreate, db: Session = Depends(database.get_db)):
    """Create a new department"""
    try:
        # Check if department already exists
        existing_department = db.query(Department).filter(Department.name == department.name).first()
        if existing_department:
            raise HTTPException(status_code=400, detail="Department already exists")
        
        # Convert Pydantic model to dictionary first
        department_data = department.model_dump()
        
        # Set default value for created_by if not provided
        department_data["created_by"] = department_data.get("created_by") or "taadmin"
        
        # Don't set updated_by during creation - remove it if it exists
        department_data.pop("updated_by", None)
        
        # Create the Department instance
        db_department = Department(**department_data)
        
        db.add(db_department)
        db.commit()
        db.refresh(db_department)
        return db_department
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/departments", response_model=List[schemas.DepartmentRead])
async def get_departments(db: Session = Depends(database.get_db)):
    """Get all the departments"""
    try:
        departments = db.query(Department).all()
        # Handle NULL values before returning
        return [{
            **dept.__dict__,
            'updated_by': dept.updated_by or "system",
            'updated_at': dept.updated_at or dept.created_at
        } for dept in departments]
    except Exception as e: 
        raise HTTPException(status_code=500, detail=str(e))
    

@router.get("/department/{department_id}", response_model=schemas.DepartmentRead)
async def get_department(department_id: int, db: Session = Depends(database.get_db)):
    """Get a specific department by ID"""
    try:
        if not isinstance(department_id, int):
            raise HTTPException(status_code=400, detail="Invalid department ID")
        dept = db.query(Department).get(department_id)
        if not dept:
            raise HTTPException(status_code=404, detail="Department not found")
        return dept
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/department/{department_id}", response_model=schemas.DepartmentRead)
async def update_department(department_id: int, update_data: schemas.DepartmentUpdate, db: Session = Depends(database.get_db)):
    """Update a specific department by ID"""
    try:
        dept = db.query(Department).filter(Department.id == department_id).first()
        if not dept:
            raise HTTPException(status_code=404, detail="Department not found")
        
        # Get update data and remove protected fields
        update_dict = update_data.model_dump(exclude_unset=True)
        
        # Remove audit fields that shouldn't be modified by users
        protected_fields = ['created_by', 'created_at', 'updated_at', 'id']  # <-- allow updated_by from frontend
        for field in protected_fields:
            update_dict.pop(field, None)
        
        # Apply the updates
        for key, value in update_dict.items():
            setattr(dept, key, value)
        
        # Do NOT forcibly set updated_by; accept what frontend sends
        
        db.commit()
        db.refresh(dept)
        return dept
    except Exception as e:  
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/department/{department_id}")
async def delete_department(department_id: int, db: Session = Depends(database.get_db)):
    """Delete a specific department by ID"""
    try:
        if not isinstance(department_id, int):
            raise HTTPException(status_code=400, detail="Invalid department ID")
        dept = db.query(Department).get(department_id)
        if not dept:
            raise HTTPException(status_code=404, detail="Department not found")
        db.delete(dept)
        db.commit()
        return {"detail": "Department deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/create/department/", response_model=schemas.DepartmentRead)
async def create_department(department: schemas.DepartmentCreate, db: Session = Depends(database.get_db)):
    """Create a new department"""
    try:
        existing_department = db.query(Department).filter(Department.name == department.name).first()
        if existing_department:
            raise HTTPException(status_code=400, detail="Department already exists")
        
        # Convert to dict first, then modify
        department_data = department.model_dump()
        department_data["created_by"] = department_data.get("created_by") or "taadmin"
        
        # ✅ REMOVE updated_by during creation - let it be NULL
        department_data.pop("updated_by", None)  # Remove if it exists
        
        # Create the Department instance
        db_department = Department(**department_data)
        
        db.add(db_department)
        db.commit()
        db.refresh(db_department)
        return db_department
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/department/{department_id}", response_model=schemas.DepartmentRead)
async def get_department(department_id: int, db: Session = Depends(database.get_db)):
    """Get a specific department by ID"""
    try:
        dept = db.query(Department).filter(Department.id == department_id).first()
        if not dept:
            raise HTTPException(status_code=404, detail="Department not found")
        return dept
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/department/{department_id}", response_model=schemas.DepartmentRead)
async def update_department(department_id: int, update_data: schemas.DepartmentUpdate, db: Session = Depends(database.get_db)):
    """Update a specific department by ID"""
    try:
        dept = db.query(Department).filter(Department.id == department_id).first()
        if not dept:
            raise HTTPException(status_code=404, detail="Department not found")
        
        # Get update data and remove protected fields
        update_dict = update_data.model_dump(exclude_unset=True)
        
        # Remove audit fields that shouldn't be modified by users
        protected_fields = ['created_by', 'created_at', 'updated_at', 'id']  # <-- allow updated_by from frontend
        for field in protected_fields:
            update_dict.pop(field, None)
        
        # Apply the updates
        for key, value in update_dict.items():
            setattr(dept, key, value)
        
        # Do NOT forcibly set updated_by; accept what frontend sends
        
        db.commit()
        db.refresh(dept)
        return dept
    except Exception as e:  
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
@router.delete("/department/{department_id}")
async def delete_department(department_id: int, db: Session = Depends(database.get_db)):
    """Delete a specific department by ID"""
    try:
        dept = db.query(Department).filter(Department.id == department_id).first()
        if not dept:
            raise HTTPException(status_code=404, detail="Department not found")
        
        db.delete(dept)
        db.commit()
        return {"detail": "Department deleted"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
###############################################################################

@router.post("/create-job/", response_model=schemas.JobRead)
def create_job(job: schemas.JobTitleCreate, db: Session = Depends(database.get_db)):
    try:
        # Create a new job
        job_data = job.model_dump()
        job_data['created_by'] = job_data.get('created_by') or "taadmin"
        # Remove updated_by default assignment during creation
        db_job = Jobs(**job_data)
        db.add(db_job)
        db.commit()
        db.refresh(db_job)
        return db_job
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/departments/{department_id}/jobs", response_model=List[schemas.JobRead])
def get_jobs_by_department(department_id: int, db: Session = Depends(database.get_db)):
    try:
        dept = db.query(Department).get(department_id)
        if not dept:
            raise HTTPException(status_code=404, detail="Department not found")
        
        jobs = db.query(Jobs).filter(Jobs.department_id == department_id).all()
        if not jobs:
            raise HTTPException(status_code=404, detail="No jobs found for this department")
        return jobs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/update-job/{job_id}", response_model=schemas.JobRead)
def update_job(job_id: int, update_data: schemas.JobTitleUpdate, db: Session = Depends(database.get_db)):
    try:
        job = db.query(Jobs).get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict.get('updated_by'):
            update_dict['updated_by'] = "taadmin"
           
        for key, value in update_dict.items():
            setattr(job, key, value)
        db.commit()
        db.refresh(job)
        return job
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
@router.delete("/delete-job/{job_id}")
def delete_job(job_id: int, db: Session = Depends(database.get_db)):
    try:
        job = db.query(Jobs).get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        db.delete(job)
        db.commit()
    except Exception as e:  
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    return {"detail": "Job deleted"}

###################################Create Client

@router.post("/create-client/", response_model=schemas.ClientRead)
def create_client(client: schemas.ClientCreate, db: Session = Depends(database.get_db)):
    try:
        # Check if the client already exists
        existing_client = db.query(Client).filter(Client.name == client.name).first()
        if existing_client:
            raise HTTPException(status_code=400, detail="Client with this name already exists")
       
        # Create a new client
        client_data = client.model_dump()
        client_data['created_by'] = client.created_by or "taadmin"
        client_data['created_at'] = client.created_at or datetime.utcnow()
        # Remove updated_by and updated_at default assignment during creation
        db_client = Client(**client_data)
        db.add(db_client)
        db.commit()
        db.refresh(db_client)
        return db_client
    except HTTPException:
        # Re-raise HTTPException as-is (don't convert to 500)
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/client/{client_id}", response_model=schemas.ClientRead)
def update_client(client_id: int, update_data: schemas.ClientUpdate, db: Session = Depends(database.get_db)):
    try:
        # Fetch a specific client by ID
        if not isinstance(client_id, int):
            raise HTTPException(status_code=400, detail="Invalid client ID")
        if client_id <= 0:
            raise HTTPException(status_code=400, detail="Client ID must be a positive integer")
        # Update the client
        client = db.query(Client).get(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
       
        update_dict = update_data.model_dump(exclude_unset=True)
        update_dict['updated_by'] = update_data.updated_by or "taadmin"
        update_dict['updated_at'] = update_data.updated_at or datetime.utcnow()
           
        for key, value in update_dict.items():
            setattr(client, key, value)
       
        db.commit()
        db.refresh(client)
        return client
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clients/", response_model=List[schemas.ClientRead])
def get_clients(db: Session = Depends(database.get_db)):
    """
    Get all clients
    """
    try:
        clients = db.query(Client).all()
        if not clients:
            raise HTTPException(status_code=404, detail="No clients found")
        # Only set updated_by default for display if it's None (for existing records)
        for client in clients:
            if client.updated_by is None:
                client.updated_by = "taadmin"
        return clients
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/client/{client_id}", response_model=schemas.ClientRead)
def get_client(client_id: int, db: Session = Depends(database.get_db)):
    try:
        # Fetch a specific client by ID
        if not isinstance(client_id, int):
            raise HTTPException(status_code=400, detail="Invalid client ID")
        if client_id <= 0:
            raise HTTPException(status_code=400, detail="Client ID must be a positive integer")

        client = db.query(Client).get(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        return client
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




@router.delete("/client/{client_id}")
def delete_client(client_id: int, db: Session = Depends(database.get_db)):
    try:
        # Fetch a specific client by ID
        if not isinstance(client_id, int):
            raise HTTPException(status_code=400, detail="Invalid client ID")
        if client_id <= 0:
            raise HTTPException(status_code=400, detail="Client ID must be a positive integer")

        # Delete the client
        client = db.query(Client).get(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        db.delete(client)
        db.commit()
        return {"detail": "Client deleted"}
    except Exception as e:  
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

#################### Mode of work ####################################

@router.get("/mode-of-work/all", response_model=List[schemas.ModeOfWorkModel])
async def get_all_modes(db: Session = Depends(database.get_db)):
    """Get all modes of work sorted by weight in ascending order"""
    try:
        db_modes = db.query(models.ModeDB).order_by(models.ModeDB.weight.asc()).all()
        logger.info(f"Fetched {len(db_modes)} modes of work")
       
        modes = []
        for m in db_modes:
            if m.weight is None:
                logger.warning(f"Mode ID {m.id} has NULL weight, setting to 0")
                m.weight = 0  # Temporary fallback
                db.commit()
            modes.append({
                "id": m.id,
                "mode": m.mode,
                "weight": m.weight,
                "created_by": getattr(m, 'created_by', 'taadmin'),
                "updated_by": getattr(m, 'updated_by', 'taadmin')
            })
       
        if not modes:
            logger.info("No modes of work found")
            return []
       
        return modes
    except Exception as e:
        logger.error(f"Error fetching modes of work: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving modes: {str(e)}"
        )

@router.get("/mode-of-work/{mode_id}", response_model=schemas.ModeOfWorkModel)
async def get_mode(mode_id: int = Path(..., gt=0), db: Session = Depends(database.get_db)):
    """Get a specific mode of work by ID"""
    try:
        db_mode = db.query(models.ModeDB).filter(models.ModeDB.id == mode_id).first()
        if db_mode is None:
            logger.warning(f"Mode ID {mode_id} not found")
            raise HTTPException(status_code=404, detail="Mode not found")
       
        if db_mode.weight is None:
            logger.warning(f"Mode ID {mode_id} has NULL weight, setting to 0")
            db_mode.weight = 0
            db.commit()
       
        return {
            "id": db_mode.id,
            "mode": db_mode.mode,
            "weight": db_mode.weight,
            "created_by": getattr(db_mode, 'created_by', 'taadmin'),
            "updated_by": getattr(db_mode, 'updated_by', 'taadmin')
        }
    except Exception as e:
        logger.error(f"Error fetching mode {mode_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving mode: {str(e)}"
        )

@router.post("/mode-of-work", response_model=schemas.ModeOfWorkModel, status_code=status.HTTP_201_CREATED)
async def create_mode(mode_model: schemas.ModeOfWorkModel = Body(...), db: Session = Depends(database.get_db), current_user: str = "taadmin"):
    """Create a new mode of work"""
    try:
        # Check for duplicate mode (case-insensitive)
        existing_mode = db.query(models.ModeDB).filter(
            models.ModeDB.mode.ilike(mode_model.mode)
        ).first()
        if existing_mode:
            logger.warning(f"Mode {mode_model.mode} already exists")
            raise HTTPException(status_code=400, detail="Mode already exists")
       
        # Check for duplicate weight
        existing_weight = db.query(models.ModeDB).filter(
            models.ModeDB.weight == mode_model.weight
        ).first()
        if existing_weight:
            logger.warning(f"Weight {mode_model.weight} already assigned")
            raise HTTPException(status_code=400, detail="Weight already assigned")
       
        db_mode = models.ModeDB(
            mode=mode_model.mode,
            weight=mode_model.weight,
            created_by=mode_model.created_by  # Use value from frontend
            # Remove updated_by assignment during creation
        )
        db.add(db_mode)
        db.commit()
        db.refresh(db_mode)
       
        logger.info(f"Created mode {db_mode.mode} with weight {db_mode.weight}")
       
        return {
            "id": db_mode.id,
            "mode": db_mode.mode,
            "weight": db_mode.weight,
            "created_by": db_mode.created_by,
            "updated_by": db_mode.updated_by
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating mode: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error creating mode: {str(e)}"
        )
    
@router.put("/mode-of-work/{mode_id}", response_model=schemas.ModeOfWorkModel)
async def update_mode(
    mode_model: schemas.ModeOfWorkModel = Body(...),
    mode_id: int = Path(..., gt=0),
    db: Session = Depends(database.get_db),
    current_user: str = "taadmin"
):
    """Update an existing mode of work with weight swapping"""
    try:
        db_mode = db.query(models.ModeDB).filter(models.ModeDB.id == mode_id).first()
        if db_mode is None:
            logger.warning(f"Mode ID {mode_id} not found")
            raise HTTPException(status_code=404, detail="Mode not found")
       
        # Check for duplicate mode (case-insensitive, excluding current mode)
        existing_mode = db.query(models.ModeDB).filter(
            models.ModeDB.mode.ilike(mode_model.mode),
            models.ModeDB.id != mode_id
        ).first()
        if existing_mode:
            logger.warning(f"Mode {mode_model.mode} already exists")
            raise HTTPException(status_code=400, detail="Mode already exists")
       
        # Check if another mode has the desired weight
        existing_weight_mode = db.query(models.ModeDB).filter(
            models.ModeDB.weight == mode_model.weight,
            models.ModeDB.id != mode_id
        ).first()
       
        # Start a transaction
        try:
            if existing_weight_mode:
                # Swap weights: assign current mode's weight to the other mode
                existing_weight_mode.weight = db_mode.weight
                existing_weight_mode.updated_at = datetime.utcnow()
                existing_weight_mode.updated_by = mode_model.updated_by  # Use value from frontend
                logger.info(f"Swapping weight: setting weight {db_mode.weight} for mode ID {existing_weight_mode.id}")
           
            # Update the current mode
            db_mode.mode = mode_model.mode
            db_mode.weight = mode_model.weight
            db_mode.updated_at = datetime.utcnow()
            db_mode.updated_by = mode_model.updated_by  # Use value from frontend
           
            db.commit()
            db.refresh(db_mode)
            if existing_weight_mode:
                db.refresh(existing_weight_mode)
               
            logger.info(f"Updated mode ID {mode_id} with weight {db_mode.weight} by {db_mode.updated_by}")
            if existing_weight_mode:
                logger.info(f"Swapped weight with mode ID {existing_weight_mode.id}, new weight {existing_weight_mode.weight}")
           
            return {
                "id": db_mode.id,
                "mode": db_mode.mode,
                "weight": db_mode.weight,
                "created_at": db_mode.created_at,
                "updated_at": db_mode.updated_at,
                "created_by": db_mode.created_by,
                "updated_by": db_mode.updated_by
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Error during weight swap for mode ID {mode_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error updating mode: {str(e)}"
            )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating mode {mode_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error updating mode: {str(e)}"
        )


@router.delete("/mode-of-work/{mode_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mode(mode_id: int = Path(..., gt=0), db: Session = Depends(database.get_db), current_user: str = "taadmin"):
    """Delete a mode of work by ID"""
    try:
        db_mode = db.query(models.ModeDB).filter(models.ModeDB.id == mode_id).first()
        if db_mode is None:
            logger.warning(f"Mode ID {mode_id} not found")
            raise HTTPException(status_code=404, detail="Mode not found")
       
        db.delete(db_mode)
        db.commit()
        logger.info(f"Deleted mode ID {mode_id}")
        return None
    except Exception as e:
        logger.error(f"Error deleting mode {mode_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error deleting mode: {str(e)}"
        )

@router.get("/mode-of-work/next_weight", response_model=int)
async def get_next_weight(db: Session = Depends(database.get_db)):
    """Get the next available weight for a mode of work."""
    try:
        max_weight = db.query(func.max(models.ModeDB.weight)).scalar()
        next_weight = (max_weight or -1) + 1
        logger.info(f"Suggested next weight: {next_weight}")
        return next_weight
    except Exception as e:
        logger.error(f"Error fetching next weight: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching next weight"
        )


####################### Job Type Endpoints

@router.get("/job-type/all", response_model=List[schemas.JobTypeModel])
async def get_all_job_types(db: Session = Depends(database.get_db)):
    """Get all job types sorted by weight in ascending order"""
    try:
        db_job_types = db.query(models.JobTypeDB).order_by(models.JobTypeDB.weight.asc()).all()
        logger.info(f"Fetched {len(db_job_types)} job types")
        
        job_types = []
        for jt in db_job_types:
            if jt.weight is None:
                logger.warning(f"Job type ID {jt.id} has NULL weight, setting to 0")
                jt.weight = 0  # Temporary fallback
                db.commit()
            job_types.append({
                "id": jt.id,
                "job_type": jt.job_type,
                "weight": jt.weight,
                "created_at": jt.created_at,
                "updated_at": jt.updated_at,
                "created_by": getattr(jt, 'created_by', 'taadmin'),
                "updated_by": getattr(jt, 'updated_by', 'taadmin')
            })
        
        if not job_types:
            logger.info("No job types found")
            return []
        
        return job_types
    except Exception as e:
        logger.error(f"Error fetching job types: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving job types: {str(e)}"
        )

@router.get("/job-type/{job_type_id}", response_model=schemas.JobTypeModel)
async def get_job_type(job_type_id: int = Path(..., gt=0), db: Session = Depends(database.get_db)):
    """Get a specific job type by ID"""
    try:
        db_job_type = db.query(models.JobTypeDB).filter(models.JobTypeDB.id == job_type_id).first()
        if db_job_type is None:
            logger.warning(f"Job type ID {job_type_id} not found")
            raise HTTPException(status_code=404, detail="Job type not found")
        
        if db_job_type.weight is None:
            logger.warning(f"Job type ID {job_type_id} has NULL weight, setting to 0")
            db_job_type.weight = 0
            db.commit()
        
        return {
            "id": db_job_type.id,
            "job_type": db_job_type.job_type,
            "weight": db_job_type.weight,
            "created_at": db_job_type.created_at,
            "updated_at": db_job_type.updated_at,
            "created_by": getattr(db_job_type, 'created_by', 'taadmin'),
            "updated_by": getattr(db_job_type, 'updated_by', 'taadmin')
        }
    except Exception as e:
        logger.error(f"Error fetching job type {job_type_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving job type: {str(e)}"
        )

@router.post("/job-type", response_model=schemas.JobTypeModel, status_code=status.HTTP_201_CREATED)
async def create_job_type(
    job_type_model: schemas.JobTypeCreate = Body(...), 
    db: Session = Depends(database.get_db),
    current_user: str = "taadmin"  # You can replace this with actual user authentication
):
    """Create a new job type"""
    try:
        # Check for duplicate job type (case-insensitive)
        existing = db.query(models.JobTypeDB).filter(
            models.JobTypeDB.job_type.ilike(job_type_model.job_type)
        ).first()
        if existing:
            logger.warning(f"Job type {job_type_model.job_type} already exists")
            raise HTTPException(status_code=400, detail="Job type already exists")
        
        # Check for duplicate weight
        existing_weight = db.query(models.JobTypeDB).filter(
            models.JobTypeDB.weight == job_type_model.weight
        ).first()
        if existing_weight:
            logger.warning(f"Weight {job_type_model.weight} already assigned")
            raise HTTPException(status_code=400, detail="Weight already assigned")
        
        db_job_type = models.JobTypeDB(
            job_type=job_type_model.job_type,
            weight=job_type_model.weight,
            created_by=job_type_model.created_by
            # Remove updated_by assignment during creation
        )
        db.add(db_job_type)
        db.commit()
        db.refresh(db_job_type)
        
        logger.info(f"Created job type {db_job_type.job_type} with weight {db_job_type.weight} by {db_job_type.created_by}")
        
        return {
            "id": db_job_type.id,
            "job_type": db_job_type.job_type,
            "weight": db_job_type.weight,
            "created_at": db_job_type.created_at,
            "updated_at": db_job_type.updated_at,
            "created_by": db_job_type.created_by,
            "updated_by": db_job_type.updated_by
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating job type: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error creating job type: {str(e)}"
        )

@router.put("/job-type/{job_type_id}", response_model=schemas.JobTypeModel)
async def update_job_type(
    job_type_model: schemas.JobTypeCreate = Body(...),
    job_type_id: int = Path(..., gt=0),
    db: Session = Depends(database.get_db),
    current_user: str = "taadmin"  # You can replace this with actual user authentication
):
    """Update an existing job type with weight swapping"""
    try:
        db_job_type = db.query(models.JobTypeDB).filter(models.JobTypeDB.id == job_type_id).first()
        if db_job_type is None:
            logger.warning(f"Job type ID {job_type_id} not found")
            raise HTTPException(status_code=404, detail="Job type not found")
        
        # Check for duplicate job type (case-insensitive, excluding current job type)
        existing = db.query(models.JobTypeDB).filter(
            models.JobTypeDB.job_type.ilike(job_type_model.job_type),
            models.JobTypeDB.id != job_type_id
        ).first()
        if existing:
            logger.warning(f"Job type {job_type_model.job_type} already exists")
            raise HTTPException(status_code=400, detail="Job type already exists")
        
        # Check if another job type has the desired weight
        existing_weight_job_type = db.query(models.JobTypeDB).filter(
            models.JobTypeDB.weight == job_type_model.weight,
            models.JobTypeDB.id != job_type_id
        ).first()
        
        # Start a transaction
        try:
            if existing_weight_job_type:
                # Swap weights: assign current job type's weight to the other job type
                existing_weight_job_type.weight = db_job_type.weight
                existing_weight_job_type.updated_at = datetime.utcnow()
                existing_weight_job_type.updated_by = job_type_model.updated_by
                logger.info(f"Swapping weight: setting weight {db_job_type.weight} for job type ID {existing_weight_job_type.id}")
            
            # Update the current job type
            db_job_type.job_type = job_type_model.job_type
            db_job_type.weight = job_type_model.weight
            db_job_type.updated_at = datetime.utcnow()
            db_job_type.updated_by = job_type_model.updated_by
                        
            db.commit()
            db.refresh(db_job_type)
            if existing_weight_job_type:
                db.refresh(existing_weight_job_type)
                
            logger.info(f"Updated job type ID {job_type_id} with weight {db_job_type.weight} by {db_job_type.updated_by}")
            if existing_weight_job_type:
                logger.info(f"Swapped weight with job type ID {existing_weight_job_type.id}, new weight {existing_weight_job_type.weight}")
            
            return {
                "id": db_job_type.id,
                "job_type": db_job_type.job_type,
                "weight": db_job_type.weight,
                "created_at": db_job_type.created_at,
                "updated_at": db_job_type.updated_at,
                "created_by": db_job_type.created_by,
                "updated_by": db_job_type.updated_by
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Error during weight swap for job type ID {job_type_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error updating job type: {str(e)}"
            )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating job type {job_type_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error updating job type: {str(e)}"
        )

@router.delete("/job-type/{job_type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job_type(
    job_type_id: int = Path(..., gt=0), 
    db: Session = Depends(database.get_db),
    current_user: str = "taadmin"  # You can replace this with actual user authentication
):
    """Delete a job type"""
    try:
        db_job_type = db.query(models.JobTypeDB).filter(models.JobTypeDB.id == job_type_id).first()
        if db_job_type is None:
            logger.warning(f"Job type ID {job_type_id} not found")
            raise HTTPException(status_code=404, detail="Job type not found")
        
        db.delete(db_job_type)
        db.commit()
        logger.info(f"Deleted job type ID {job_type_id} by {current_user}")
        return None
    except Exception as e:
        logger.error(f"Error deleting job type {job_type_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error deleting job type: {str(e)}"
        )

@router.get("/job-type/next_weight", response_model=int)
async def get_next_weight(db: Session = Depends(database.get_db)):
    """Get the next available weight for a job type."""
    try:
        max_weight = db.query(func.max(models.JobTypeDB.weight)).scalar()
        next_weight = (max_weight or -1) + 1
        logger.info(f"Suggested next weight: {next_weight}")
        return next_weight
    except Exception as e:
        logger.error(f"Error fetching next weight: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching next weight"
        )
######################################## Requisition Type Endpoints

@router.get("/requisition-type/all", response_model=List[schemas.RequisitionTypeModel])
async def get_all_requisition_types(db: Session = Depends(database.get_db)):
    """Get all requisition types sorted by weight in ascending order"""
    try:
        db_requisition_types = db.query(RequisitionTypeDB).order_by(RequisitionTypeDB.weight.asc()).all()
        logger.info(f"Fetched {len(db_requisition_types)} requisition types")
       
        requisition_types = []
        for rt in db_requisition_types:
            # Check if the record has been updated (updated_at is different from created_at)
            # or if updated_by field exists and has a value
            updated_by_value = None
            if hasattr(rt, 'updated_by') and rt.updated_by is not None:
                updated_by_value = rt.updated_by
            elif (hasattr(rt, 'updated_at') and hasattr(rt, 'created_at') and 
                  rt.updated_at and rt.created_at and rt.updated_at != rt.created_at):
                # Record has been updated but updated_by is not set, use default
                updated_by_value = 'taadmin'
            
            requisition_types.append({
                "id": rt.id,
                "requisition_type": rt.requisition_type,
                "weight": rt.weight,
                "created_at": rt.created_at,
                "updated_at": rt.updated_at,
                "created_by": getattr(rt, 'created_by', None) or 'taadmin',  # Use actual value or fallback
                "updated_by": updated_by_value  # Will be None for newly created records, 'admin' or actual user for updated records
            })
       
        return requisition_types
    except Exception as e:
        logger.error(f"Error fetching requisition types: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving requisition types: {str(e)}"
        )

@router.post("/requisition-type", response_model=schemas.RequisitionTypeModel, status_code=status.HTTP_201_CREATED)
async def create_requisition_type(
    requisition_type_model: schemas.RequisitionTypeModel = Body(...), 
    db: Session = Depends(database.get_db),
    current_user: str = "taadmin"  # You can replace this with actual user authentication
):
    """Create a new requisition type"""
    try:
        # Check if requisition type already exists (case-insensitive)
        existing_type = db.query(RequisitionTypeDB).filter(
            RequisitionTypeDB.requisition_type.ilike(requisition_type_model.requisition_type)
        ).first()
        if existing_type:
            logger.warning(f"Requisition type {requisition_type_model.requisition_type} already exists")
            raise HTTPException(status_code=400, detail="Requisition type already exists")

        # Check if weight already exists
        existing_weight = db.query(RequisitionTypeDB).filter(
            RequisitionTypeDB.weight == requisition_type_model.weight
        ).first()
        if existing_weight:
            logger.warning(f"Weight {requisition_type_model.weight} already assigned")
            raise HTTPException(status_code=400, detail="Weight already assigned to another requisition type")

        # Create new requisition type - don't set updated_by during creation
        db_requisition_type = RequisitionTypeDB(
            requisition_type=requisition_type_model.requisition_type,
            weight=requisition_type_model.weight,
            created_by=requisition_type_model.created_by or current_user
            # Don't set updated_by here - it should remain None until first update
        )
        db.add(db_requisition_type)
        db.commit()
        db.refresh(db_requisition_type)
        
        logger.info(f"Created requisition type {db_requisition_type.requisition_type} with weight {db_requisition_type.weight} by {db_requisition_type.created_by}")
        
        return {
            "id": db_requisition_type.id,
            "requisition_type": db_requisition_type.requisition_type,
            "weight": db_requisition_type.weight,
            "created_at": db_requisition_type.created_at,
            "updated_at": db_requisition_type.updated_at,
            "created_by": db_requisition_type.created_by,
            "updated_by": db_requisition_type.updated_by
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating requisition type: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error creating requisition type: {str(e)}"
        )

@router.put("/requisition-type/{requisition_type_id}", response_model=schemas.RequisitionTypeModel)
async def update_requisition_type(
    requisition_type_model: schemas.RequisitionTypeModel = Body(...),
    requisition_type_id: int = Path(..., gt=0),
    db: Session = Depends(database.get_db),
    current_user: str = "taadmin"  # Changed default to 'admin' to match the pattern
):
    """Update an existing requisition type with weight swapping"""
    try:
        db_requisition_type = db.query(RequisitionTypeDB).filter(RequisitionTypeDB.id == requisition_type_id).first()
        if db_requisition_type is None:
            logger.warning(f"Requisition type ID {requisition_type_id} not found")
            raise HTTPException(status_code=404, detail="Requisition type not found")

        # Check for duplicate requisition type (case-insensitive, excluding current type)
        existing_type = db.query(RequisitionTypeDB).filter(
            RequisitionTypeDB.requisition_type.ilike(requisition_type_model.requisition_type),
            RequisitionTypeDB.id != requisition_type_id
        ).first()
        if existing_type:
            logger.warning(f"Requisition type {requisition_type_model.requisition_type} already exists")
            raise HTTPException(status_code=400, detail="Requisition type already exists")

        # Check if another requisition type has the desired weight
        existing_weight_type = db.query(RequisitionTypeDB).filter(
            RequisitionTypeDB.weight == requisition_type_model.weight,
            RequisitionTypeDB.id != requisition_type_id
        ).first()

        # Start a transaction
        try:
            if existing_weight_type:
                # Swap weights: assign current type's weight to the other type
                existing_weight_type.weight = db_requisition_type.weight
                existing_weight_type.updated_at = datetime.utcnow()
                existing_weight_type.updated_by = requisition_type_model.updated_by
                logger.info(f"Swapping weight: setting weight {db_requisition_type.weight} for type ID {existing_weight_type.id}")

            # Update the current type
            db_requisition_type.requisition_type = requisition_type_model.requisition_type
            db_requisition_type.weight = requisition_type_model.weight
            db_requisition_type.updated_at = datetime.utcnow()
            db_requisition_type.updated_by = requisition_type_model.updated_by

            db.commit()
            db.refresh(db_requisition_type)
            if existing_weight_type:
                db.refresh(existing_weight_type)

            logger.info(f"Updated requisition type ID {requisition_type_id} with weight {db_requisition_type.weight} by {db_requisition_type.updated_by}")
            if existing_weight_type:
                logger.info(f"Swapped weight with type ID {existing_weight_type.id}, new weight {existing_weight_type.weight}")

            return {
                "id": db_requisition_type.id,
                "requisition_type": db_requisition_type.requisition_type,
                "weight": db_requisition_type.weight,
                "created_at": db_requisition_type.created_at,
                "updated_at": db_requisition_type.updated_at,
                "created_by": db_requisition_type.created_by,
                "updated_by": db_requisition_type.updated_by
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Error during weight swap for requisition type ID {requisition_type_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error updating requisition type: {str(e)}"
            )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating requisition type {requisition_type_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error updating requisition type: {str(e)}"
        )

@router.delete("/requisition-type/{requisition_type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_requisition_type(
    requisition_type_id: int = Path(..., gt=0), 
    db: Session = Depends(database.get_db),
    current_user: str = "taadmin"  # Changed default to 'admin' to match the pattern
):
    """Delete a requisition type"""
    try:
        db_requisition_type = db.query(RequisitionTypeDB).filter(RequisitionTypeDB.id == requisition_type_id).first()
        if db_requisition_type is None:
            logger.warning(f"Requisition type ID {requisition_type_id} not found")
            raise HTTPException(status_code=404, detail="Requisition type not found")

        db.delete(db_requisition_type)
        db.commit()
        logger.info(f"Deleted requisition type ID {requisition_type_id} by {current_user}")
        return None
    except Exception as e:
        logger.error(f"Error deleting requisition type {requisition_type_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error deleting requisition type: {str(e)}"
        )

@router.get("/requisition-type/next_weight", response_model=int)
async def get_next_weight(db: Session = Depends(database.get_db)):
    """Get the next available weight for a requisition type."""
    try:
        max_weight = db.query(func.max(RequisitionTypeDB.weight)).scalar()
        next_weight = (max_weight or -1) + 1
        logger.info(f"Suggested next weight: {next_weight}")
        return next_weight
    except Exception as e:
        logger.error(f"Error fetching next weight: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching next weight"
        )
######################################## Priority Endpoints
@router.get("/priority/all", response_model=List[schemas.PriorityModel])
async def get_all_priorities(db: Session = Depends(database.get_db)):
    """Get all priorities sorted by weight in ascending order"""
    try:
        priorities = db.query(PriorityDB).order_by(PriorityDB.weight.asc()).all()
        logger.info(f"Fetched {len(priorities)} priorities")
        
        result = []
        for priority in priorities:
            if priority.weight is None:
                logger.warning(f"Priority ID {priority.id} has NULL weight, setting to 0")
                priority.weight = 0
                db.commit()
            
            # Apply consistent updated_by logic
            updated_by_value = None
            if hasattr(priority, 'updated_by') and priority.updated_by is not None:
                updated_by_value = priority.updated_by
            elif (hasattr(priority, 'updated_at') and hasattr(priority, 'created_at') and 
                  priority.updated_at and priority.created_at and priority.updated_at != priority.created_at):
                # Record has been updated but updated_by is not set, use default
                updated_by_value = 'taadmin'
            
            result.append({
                "id": priority.id,
                "priority": priority.priority,
                "weight": priority.weight,
                "created_at": priority.created_at,
                "updated_at": priority.updated_at,
                "created_by": getattr(priority, 'created_by', None) or 'taadmin',  # Use actual value or fallback
                "updated_by": updated_by_value
            })
        
        return result
    except Exception as e:
        logger.error(f"Error fetching priorities: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving priorities: {str(e)}"
        )

@router.get("/priority/{priority_id}", response_model=schemas.PriorityModel)
async def get_priority(priority_id: int = Path(..., gt=0), db: Session = Depends(database.get_db)):
    """Get a specific priority by ID"""
    try:
        priority = db.query(PriorityDB).filter(PriorityDB.id == priority_id).first()
        if not priority:
            logger.warning(f"Priority ID {priority_id} not found")
            raise HTTPException(status_code=404, detail="Priority not found")
        
        if priority.weight is None:
            logger.warning(f"Priority ID {priority_id} has NULL weight, setting to 0")
            priority.weight = 0
            db.commit()
        
        # Apply consistent updated_by logic
        updated_by_value = None
        if hasattr(priority, 'updated_by') and priority.updated_by is not None:
            updated_by_value = priority.updated_by
        elif (hasattr(priority, 'updated_at') and hasattr(priority, 'created_at') and 
              priority.updated_at and priority.created_at and priority.updated_at != priority.created_at):
            # Record has been updated but updated_by is not set, use default
            updated_by_value = 'taadmin'
        
        return {
            "id": priority.id,
            "priority": priority.priority,
            "weight": priority.weight,
            "created_at": priority.created_at,
            "updated_at": priority.updated_at,
            "created_by": getattr(priority, 'created_by', None) or 'taadmin',  # Use actual value or fallback
            "updated_by": updated_by_value
        }
    except Exception as e:
        logger.error(f"Error fetching priority {priority_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving priority: {str(e)}"
        )

@router.post("/priority", response_model=schemas.PriorityModel, status_code=status.HTTP_201_CREATED)
async def create_priority(
    priority_model: schemas.PriorityCreate = Body(...), 
    db: Session = Depends(database.get_db),
    current_user: str = "taadmin"  # You can replace this with actual user authentication
):
    """Create a new priority"""
    try:
        # Check for duplicate priority (case-insensitive)
        existing_priority = db.query(PriorityDB).filter(
            PriorityDB.priority.ilike(priority_model.priority)
        ).first()
        if existing_priority:
            logger.warning(f"Priority {priority_model.priority} already exists")
            raise HTTPException(status_code=400, detail="Priority already exists")

        # Check for duplicate weight
        existing_weight = db.query(PriorityDB).filter(
            PriorityDB.weight == priority_model.weight
        ).first()
        if existing_weight:
            logger.warning(f"Weight {priority_model.weight} already assigned")
            raise HTTPException(status_code=400, detail="Weight already assigned to another priority")

        # Create new priority - don't set updated_by during creation
        new_priority = PriorityDB(
            priority=priority_model.priority, 
            weight=priority_model.weight,
            created_by=priority_model.created_by or current_user,
            created_at=priority_model.created_at
            # Don't set updated_by or updated_at here - they should remain None until first update
        )
        db.add(new_priority)
        db.commit()
        db.refresh(new_priority)
        
        logger.info(f"Created priority {new_priority.priority} with weight {new_priority.weight} by {new_priority.created_by}")
        
        return {
            "id": new_priority.id,
            "priority": new_priority.priority,
            "weight": new_priority.weight,
            "created_at": new_priority.created_at,
            "updated_at": new_priority.updated_at,
            "created_by": new_priority.created_by,
            "updated_by": getattr(new_priority, 'updated_by', None)  # Will be None for new records
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating priority: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error creating priority: {str(e)}"
        )

@router.put("/priority/{priority_id}", response_model=schemas.PriorityModel)
async def update_priority(
    priority_id: int = Path(..., gt=0),
    priority_model: schemas.PriorityCreate = Body(...),
    db: Session = Depends(database.get_db),
    current_user: str = "taadmin"  # Changed default to 'admin' for consistency
):
    """Update an existing priority with weight swapping"""
    try:
        priority = db.query(PriorityDB).filter(PriorityDB.id == priority_id).first()
        if not priority:
            logger.warning(f"Priority ID {priority_id} not found")
            raise HTTPException(status_code=404, detail="Priority not found")

        # Check for duplicate priority (case-insensitive, excluding current priority)
        duplicate_priority = db.query(PriorityDB).filter(
            PriorityDB.priority.ilike(priority_model.priority),
            PriorityDB.id != priority_id
        ).first()
        if duplicate_priority:
            logger.warning(f"Priority {priority_model.priority} already exists")
            raise HTTPException(status_code=400, detail="Priority already exists")

        # Check if another priority has the desired weight
        duplicate_weight = db.query(PriorityDB).filter(
            PriorityDB.weight == priority_model.weight,
            PriorityDB.id != priority_id
        ).first()

        # Start a transaction
        try:
            if duplicate_weight:
                # Swap weights: assign current priority's weight to the other priority
                duplicate_weight.weight = priority.weight
                duplicate_weight.updated_at = priority_model.updated_at
                duplicate_weight.updated_by = priority_model.updated_by
                logger.info(f"Swapping weight: setting weight {priority.weight} for priority ID {duplicate_weight.id}")

            # Update the current priority
            priority.priority = priority_model.priority
            priority.weight = priority_model.weight
            priority.updated_at = priority_model.updated_at
            priority.updated_by = priority_model.updated_by

            db.commit()
            db.refresh(priority)
            if duplicate_weight:
                db.refresh(duplicate_weight)

            logger.info(f"Updated priority ID {priority_id} with weight {priority.weight} by {priority.updated_by}")
            if duplicate_weight:
                logger.info(f"Swapped weight with priority ID {duplicate_weight.id}, new weight {duplicate_weight.weight}")

            return {
                "id": priority.id,
                "priority": priority.priority,
                "weight": priority.weight,
                "created_at": priority.created_at,
                "updated_at": priority.updated_at,
                "created_by": priority.created_by,
                "updated_by": priority.updated_by
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Error during weight swap for priority ID {priority_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error updating priority: {str(e)}"
            )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating priority {priority_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error updating priority: {str(e)}"
        )

@router.delete("/priority/{priority_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_priority(
    priority_id: int = Path(..., gt=0), 
    db: Session = Depends(database.get_db),
    current_user: str = "taadmin"  # Changed default to 'admin' for consistency
):
    """Delete a priority"""
    try:
        priority = db.query(PriorityDB).filter(PriorityDB.id == priority_id).first()
        if not priority:
            logger.warning(f"Priority ID {priority_id} not found")
            raise HTTPException(status_code=404, detail="Priority not found")

        db.delete(priority)
        db.commit()
        logger.info(f"Deleted priority ID {priority_id} by {current_user}")
        return None
    except Exception as e:
        logger.error(f"Error deleting priority {priority_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error deleting priority: {str(e)}"
        )
    
@router.get("/priority/next_weight", response_model=int)
async def get_next_weight(db: Session = Depends(database.get_db)):
    """Get the next available weight for a priority."""
    try:
        max_weight = db.query(func.max(PriorityDB.weight)).scalar()
        next_weight = (max_weight or -1) + 1
        logger.info(f"Suggested next weight: {next_weight}")
        return next_weight
    except Exception as e:
        logger.error(f"Error fetching next weight: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching next weight"
        )

@router.get("/debug/jobs", response_model=List[dict])
def debug_get_all_jobs(db: Session = Depends(database.get_db)):
    """Debug endpoint to see all available jobs"""
    try:
        jobs = db.query(Jobs).all()
        result = []
        for job in jobs:
            result.append({
                "id": job.id,
                "title": job.title,
                "description": job.description,
                "department_id": job.department_id,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "created_by": getattr(job, 'created_by', 'taadmin'),
                "updated_by": job.updated_by if job.updated_by else None

            })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
################################Create skills

# # Create a new skill for a job
# @router.post("/create-skill/", response_model=schemas.JobSkillRead)
# def create_skill(skill: schemas.JobSkillCreate, db: Session = Depends(database.get_db)):
#     try:
#         # Check if the job exists
#         job = db.query(Jobs).filter(Jobs.id == skill.job_id).first()
#         if job is None:
#             raise HTTPException(status_code=400, detail="Job not found")

#         # Create a new skill
#         db_skill = JobSkills(
#             primary_skills=skill.primary_skills,
#             secondary_skills=skill.secondary_skills,
#             job_id=skill.job_id
#         )
#         db.add(db_skill)
#         db.commit()
#         db.refresh(db_skill)
#         return db_skill
#     except Exception as e:
#         db.rollback()
#         raise HTTPException(status_code=500, detail=str(e))


# # Get skills for a specific job
# @router.get("/{job_id}/skills", response_model=List[schemas.JobSkillRead])
# def get_skills_by_job(job_id: int, db: Session = Depends(database.get_db)):
#     try:
#         # First check if the job exists
#         job = db.query(Jobs).get(job_id)
#         if not job:
#             raise HTTPException(status_code=404, detail="Job not found")
        
#         # Get all skills for the job
#         skills = db.query(JobSkills).filter(JobSkills.job_id == job_id).all()
#         if not skills:
#             return []
            
#         return skills
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# # Get primary skills for a specific job
# @router.get("/{job_id}/skills/primary", response_model=List[schemas.JobSkillRead])
# def get_primary_skills_by_job(job_id: int, db: Session = Depends(database.get_db)):
#     try:
#         # First check if the job exists
#         job = db.query(Jobs).get(job_id)
#         if not job:
#             raise HTTPException(status_code=404, detail="Job not found")
        
#         # Get primary skills for the job
#         skills = db.query(JobSkills).filter(
#             JobSkills.job_id == job_id,
#             JobSkills.primary_skills.isnot(None)
#         ).all()
        
#         if not skills:
#             return []
            
#         return skills
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# # Get secondary skills for a specific job
# @router.get("/{job_id}/skills/secondary", response_model=List[schemas.JobSkillRead])
# def get_secondary_skills_by_job(job_id: int, db: Session = Depends(database.get_db)):
#     try:
#         # First check if the job exists
#         job = db.query(Jobs).get(job_id)
#         if not job:
#             raise HTTPException(status_code=404, detail="Job not found")
        
#         # Get secondary skills for the job
#         skills = db.query(JobSkills).filter(
#             JobSkills.job_id == job_id,
#             JobSkills.secondary_skills.isnot(None)
#         ).all()
        
#         if not skills:
#             return []
            
#         return skills
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))



# Get skills for a specific job
@router.get("/{job_id}/skills", response_model=List[dict])
def get_skills_by_job(job_id: int, db: Session = Depends(database.get_db)):
    try:
        job = db.query(Jobs).get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        skills = (
            db.query(JobSkills, Jobs.title.label("job_title"))
            .join(Jobs, JobSkills.job_id == Jobs.id)
            .filter(JobSkills.job_id == job_id)
            .all()
        )
        
        if not skills:
            return []
            
        result = []
        for skill, job_title in skills:
            result.append(format_skill_response_with_skillset_only(skill, job_title))
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Optional: New endpoint to get skills WITH individual skills if needed
@router.get("/{job_id}/skills/detailed", response_model=List[dict])
def get_detailed_skills_by_job(job_id: int, db: Session = Depends(database.get_db)):
    """
    Get skills with both skill_set AND individual primary/secondary skills.
    Use this endpoint only when you need to see the breakdown.
    """
    try:
        job = db.query(Jobs).get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        skills = (
            db.query(JobSkills, Jobs.title.label("job_title"))
            .join(Jobs, JobSkills.job_id == Jobs.id)
            .filter(JobSkills.job_id == job_id)
            .all()
        )
        
        if not skills:
            return []
            
        result = []
        for skill, job_title in skills:
            result.append(format_skill_response_with_skillset(skill, job_title, include_individual_skills=True))
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

    # Get primary skills for a specific job with skill_set
@router.get("/{job_id}/skills/primary", response_model=List[dict])
def get_primary_skills_by_job(job_id: int, db: Session = Depends(database.get_db)):
    try:
        job = db.query(Jobs).get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        skills = (
            db.query(JobSkills, Jobs.title.label("job_title"))
            .join(Jobs, JobSkills.job_id == Jobs.id)
            .filter(JobSkills.job_id == job_id, JobSkills.primary_skills.isnot(None))
            .all()
        )
        
        if not skills:
            return []
            
        result = []
        for skill, job_title in skills:
            # For primary skills endpoint, show only primary skills in skill_set
            result.append({
                "id": skill.id,
                "primary_skills": skill.primary_skills,
                "secondary_skills": None,
                "skill_set": skill.primary_skills,  # Only primary skills
                "job_id": skill.job_id,
                "job_title": job_title,
                "created_at": skill.created_at.isoformat() if skill.created_at else None,
                "updated_at": skill.updated_at.isoformat() if skill.updated_at else None,
                "created_by": skill.created_by,
                "updated_by": skill.updated_by,
            })
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    # Get secondary skills for a specific job with skill_set
@router.get("/{job_id}/skills/secondary", response_model=List[dict])
def get_secondary_skills_by_job(job_id: int, db: Session = Depends(database.get_db)):
    try:
        job = db.query(Jobs).get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        skills = (
            db.query(JobSkills, Jobs.title.label("job_title"))
            .join(Jobs, JobSkills.job_id == Jobs.id)
            .filter(JobSkills.job_id == job_id, JobSkills.secondary_skills.isnot(None))
            .all()
        )
        
        if not skills:
            return []
            
        result = []
        for skill, job_title in skills:
            # For secondary skills endpoint, show only secondary skills in skill_set
            result.append({
                "id": skill.id,
                "primary_skills": None,
                "secondary_skills": skill.secondary_skills,
                "skill_set": skill.secondary_skills,  # Only secondary skills
                "job_id": skill.job_id,
                "job_title": job_title,
                "created_at": skill.created_at.isoformat() if skill.created_at else None,
                "updated_at": skill.updated_at.isoformat() if skill.updated_at else None,
                "created_by": skill.created_by,
                "updated_by": skill.updated_by,
            })
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    





################################ Special Endpoints for Job Requisition ################################

# Get only skill_set for a specific job (for job requisition table)
@router.get("/{job_id}/skillset-only")
def get_job_skillset_only(job_id: int, db: Session = Depends(database.get_db)):
    """
    Get only the combined skill_set for a specific job.
    Perfect for populating the skill_set column in your job requisition table.
    Returns: primary_skills + secondary_skills (primary first)
    """
    try:
        job = db.query(Jobs).get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        skills = db.query(JobSkills).filter(JobSkills.job_id == job_id).all()
        
        if not skills:
            return {"job_id": job_id, "skill_set": None}
        
        # Combine all skills for this job
        all_combined_skills = []
        for skill in skills:
            combined_skill = combine_skills(skill.primary_skills, skill.secondary_skills)
            if combined_skill:
                all_combined_skills.append(combined_skill)
        
        # Join all skill combinations
        final_skill_set = ', '.join(all_combined_skills) if all_combined_skills else None
        
        return {
            "job_id": job_id,
            "skill_set": final_skill_set
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Bulk operation to get skill_set for multiple jobs
@router.post("/jobs/skillsets", response_model=List[dict])
def get_skillsets_for_multiple_jobs(job_ids: List[int], db: Session = Depends(database.get_db)):
    """
    Get skill_set for multiple jobs at once.
    Perfect for bulk populating job requisition table.
    """
    try:
        result = []
        
        for job_id in job_ids:
            job = db.query(Jobs).get(job_id)
            if not job:
                result.append({"job_id": job_id, "skill_set": None, "error": "Job not found"})
                continue
            
            skills = db.query(JobSkills).filter(JobSkills.job_id == job_id).all()
            
            if not skills:
                result.append({"job_id": job_id, "skill_set": None})
                continue
            
            # Combine all skills for this job
            all_combined_skills = []
            for skill in skills:
                combined_skill = combine_skills(skill.primary_skills, skill.secondary_skills)
                if combined_skill:
                    all_combined_skills.append(combined_skill)
            
            final_skill_set = ', '.join(all_combined_skills) if all_combined_skills else None
            result.append({"job_id": job_id, "skill_set": final_skill_set})
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

################################ GENERIC JOB DETAILS - MUST BE LAST ################################
# This route MUST be at the end because it uses a generic /{job_id} pattern
# that could match other specific routes if placed earlier

@router.get("/{job_id}", response_model=schemas.JobResponse)
def get_job_details(job_id: str, db: Session = Depends(database.get_db)):
    """
    Retrieves details for a specific job requisition by job_id or database id.
    WARNING: This route MUST be at the end due to its generic pattern.
    """
    # Try to find by job_id first
    job = db.query(models.Job).filter(models.Job.job_id == job_id).first()

    # If not found, try by database id (if job_id is a number)
    if not job and job_id.isdigit():
        job = db.query(models.Job).filter(models.Job.id == int(job_id)).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job requisition not found")

    # Format job details
    job_dict = {
        'id': job.id,
        'job_id': job.job_id,
        'job_title': job.job_title,
        'no_of_positions': job.no_of_positions,
        'requisition_type': job.requisition_type,
        'employee_to_be_replaced': job.employee_to_be_replaced,
        'job_type': job.job_type,
        # 'primary_skills': job.primary_skills,
        # 'secondary_skills': job.secondary_skills,
        'skill_set': job.skill_set,
        'department': job.department,
        'required_experience_min': job.required_experience_min,
        'required_experience_max': job.required_experience_max,
        'ctc_budget_min': job.ctc_budget_min,
        'ctc_budget_max': job.ctc_budget_max,
        'mode_of_work': job.mode_of_work,
        'office_location': job.office_location,
        'job_description': job.job_description,
        'target_hiring_date': job.target_hiring_date.isoformat() if job.target_hiring_date else None,
        'priority': job.priority,
        'client_name': job.client_name,
        'head_of_department': job.head_of_department,
        # 'date_of_request': job.date_of_request.isoformat() if job.date_of_request else None,
        'status': job.status,
        'created_on': job.created_on.isoformat() if job.created_on else None,
        'created_by': job.created_by,
        'additional_notes': job.additional_notes
    }

    return schemas.JobResponse(**job_dict)
    
