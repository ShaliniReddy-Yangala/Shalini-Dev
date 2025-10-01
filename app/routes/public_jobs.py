from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile, Form
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, or_, and_, func
from typing import Optional, List
import math
from datetime import datetime, date
import os
import uuid
import boto3
from botocore.exceptions import ClientError

from app.models import Job, JobTypeDB, JobSkills, Candidate, Department
from app.schemas import PublicJobsOverviewResponse, PublicJobOverviewItem, PublicJobDetailsResponse, PublicJobApplicationCreate, PublicJobApplicationResponse, DepartmentRead
from app.database import get_db

# S3 Configuration (should match your existing setup)
S3_BUCKET = os.getenv("S3_BUCKET", "upload-media00")
AWS_REGION = os.getenv("AWS_REGION", "ap-south-2")
s3_client = boto3.client(
    's3',
    region_name=AWS_REGION,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
)

# Allowed file extensions for resume uploads
ALLOWED_RESUME_EXTENSIONS = {'pdf', 'doc', 'docx'}

router = APIRouter(prefix="/public", tags=["public"])

@router.get("/jobs/{job_id}/details", response_model=PublicJobDetailsResponse)
def get_public_job_details(
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed information for a specific job by job_id.
    
    This endpoint provides comprehensive job details for public viewing.
    Only returns jobs with 'OPEN' status.
    
    Args:
        job_id: The unique job identifier (e.g., 'JR00900056')
        
    Returns:
        PublicJobDetailsResponse with detailed job information
        
    Raises:
        404: If job not found or not in OPEN status
        500: For server errors
    """
    
    try:
        # Query for the specific job - only return if status is OPEN
        job = db.query(Job).filter(
            Job.job_id == job_id,
            Job.status == "OPEN"
        ).first()
        
        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Job with ID '{job_id}' not found or not available"
            )
        
        # Format experience range
        experience_required = f"{job.required_experience_min}-{job.required_experience_max} years"
        
        # Create response
        job_details = PublicJobDetailsResponse(
            posted_on=job.created_on,
            title=job.job_title,
            summary=job.job_description,
            job_type=job.job_type,
            department=job.department,
            experience_required=experience_required,
            mode_of_work=job.mode_of_work,
            no_of_positions=job.no_of_positions,
            must_have_skills=job.skill_set
        )
        
        return job_details
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 404)
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while retrieving job details: {str(e)}"
        )

@router.get("/jobs/overview", response_model=PublicJobsOverviewResponse)
def get_public_jobs_overview(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Number of items per page"),
    job_type: Optional[str] = Query(None, description="Filter by job type"),
    sort_by: Optional[str] = Query("latest", regex="^(latest|oldest)$", description="Sort by latest or oldest"),
    skills: Optional[str] = Query(None, description="Filter by skills (partial match)"),
    search: Optional[str] = Query(None, description="Search in job title"),
    department: Optional[str] = Query(None, description="Filter by department"),  # Added department filter
    db: Session = Depends(get_db)
):
    """
    Get public jobs overview with pagination, filtering, and search capabilities.
    
    This endpoint is read-only and provides lightweight access to job listings.
    
    Args:
        page: Page number (default: 1)
        limit: Items per page (default: 10, max: 100)
        job_type: Filter by job type (optional)
        sort_by: Sort by 'latest' or 'oldest' posting date (default: 'latest')
        skills: Filter by skills - partial match (optional)
        search: Search in job title - partial match (optional)
        
    Returns:
        PublicJobsOverviewResponse with paginated job listings
    """
    
    try:
        # Start with base query - only include open jobs for public viewing
        query = db.query(Job).filter(Job.status == "OPEN")
        
        # Apply filters
        if job_type:
            query = query.filter(Job.job_type.ilike(f"%{job_type}%"))
            
        if skills:
            query = query.filter(Job.skill_set.ilike(f"%{skills}%"))
            
        if search:
            query = query.filter(Job.job_title.ilike(f"%{search}%"))
        if department:
            query = query.filter(func.lower(Job.department) == func.lower(department))  # Department exact, case-insensitive match
        
        # Apply sorting
        if sort_by == "oldest":
            query = query.order_by(asc(Job.created_on))
        else:  # default to latest
            query = query.order_by(desc(Job.created_on))
        
        # Get total count before pagination
        total = query.count()
        
        # Calculate total pages
        total_pages = math.ceil(total / limit) if total > 0 else 1
        
        # Apply pagination
        offset = (page - 1) * limit
        jobs = query.offset(offset).limit(limit).all()
        
        # Transform to response model
        job_items = []
        for job in jobs:
            job_items.append(PublicJobOverviewItem(
                job_id=job.job_id,
                job_title=job.job_title,
                job_type=job.job_type,
                posting_date=job.created_on,
                skills=job.skill_set,
                department=job.department  # Add department to response
            ))
        
        return PublicJobsOverviewResponse(
            jobs=job_items,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while retrieving jobs: {str(e)}"
        )

@router.get("/job-types", response_model=List[str])
def get_public_job_types(db: Session = Depends(get_db)):
    """
    Get list of job types for dropdown options from OPEN jobs only.
    Returns a simple list of job type names sorted alphabetically.
    """
    try:
        # Get job types only from OPEN jobs
        job_types = (
            db.query(Job.job_type)
            .filter(Job.status == "OPEN")
            .filter(Job.job_type.isnot(None))
            .distinct()
            .all()
        )
        
        # Extract job type names from tuples and remove duplicates
        job_type_list = list(set([jt[0] for jt in job_types if jt[0] and jt[0].strip()]))
        job_type_list.sort()  # Sort alphabetically
        
        return job_type_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching job types: {str(e)}")

@router.get("/skills", response_model=List[str])
def get_public_skills(db: Session = Depends(get_db)):
    """
    Get list of all unique skills for public-facing dropdowns.
    Returns a simple list of all skill names, sorted alphabetically.
    """
    try:
        # Get all skills from the JobSkills table, regardless of job status
        skills_data = (
            db.query(JobSkills.primary_skills, JobSkills.secondary_skills)
            .filter(
                or_(
                    JobSkills.primary_skills.isnot(None),
                    JobSkills.secondary_skills.isnot(None)
                )
            )
            .all()
        )
        
        # Extract and combine all unique skills
        all_skills = set()
        
        for primary, secondary in skills_data:
            # Process primary skills
            if primary:
                primary_list = [skill.strip() for skill in primary.split(',') if skill.strip()]
                all_skills.update(primary_list)
            
            # Process secondary skills  
            if secondary:
                secondary_list = [skill.strip() for skill in secondary.split(',') if skill.strip()]
                all_skills.update(secondary_list)
        
        # Convert to sorted list
        skills_list = sorted(list(all_skills))
        
        return skills_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching skills: {str(e)}") 

@router.get("/skills/by-department", response_model=List[str])
def get_public_skills_by_department(
    department: str = Query(..., description="Department name to filter skills by"),
    db: Session = Depends(get_db)
):
    """
    Get list of all unique skills for a given department for public-facing dropdowns.
    Returns a simple list of all skill names, sorted alphabetically.
    """
    try:
        # Join JobSkills -> Jobs -> Department and filter by department name
        from app.models import JobSkills, Jobs, Department
        skills_data = (
            db.query(JobSkills.primary_skills, JobSkills.secondary_skills)
            .join(Jobs, JobSkills.job_id == Jobs.id)
            .join(Department, Jobs.department_id == Department.id)
            .filter(func.lower(Department.name) == func.lower(department))
            .all()
        )
        all_skills = set()
        for primary, secondary in skills_data:
            if primary:
                primary_list = [skill.strip() for skill in primary.split(',') if skill.strip()]
                all_skills.update(primary_list)
            if secondary:
                secondary_list = [skill.strip() for skill in secondary.split(',') if skill.strip()]
                all_skills.update(secondary_list)
        skills_list = sorted(list(all_skills))
        return skills_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching skills for department: {str(e)}")

@router.get("/departments", response_model=List[DepartmentRead])
def get_public_departments(db: Session = Depends(get_db)):
    """
    Get list of all department details for public-facing dropdowns.
    Returns a list of DepartmentRead objects, sorted alphabetically by name.
    Ensures 'updated_by' and 'created_by' are always strings for Pydantic validation.
    """
    try:
        departments = db.query(Department).order_by(Department.name.asc()).all()
        # Patch nulls for Pydantic
        for dept in departments:
            if getattr(dept, 'updated_by', None) is None:
                dept.updated_by = "system"
            if getattr(dept, 'created_by', None) is None:
                dept.created_by = "system"
        return departments
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching departments: {str(e)}") 

@router.get("/departments/all", response_model=List[DepartmentRead])
def get_all_public_departments(db: Session = Depends(get_db)):
    """
    New public route: Get all department details (separate from /departments).
    Returns a list of DepartmentRead objects, sorted alphabetically by name.
    Ensures 'updated_by' and 'created_by' are always strings for Pydantic validation.
    """
    try:
        departments = db.query(Department).order_by(Department.name.asc()).all()
        # Patch nulls for Pydantic
        for dept in departments:
            if getattr(dept, 'updated_by', None) is None:
                dept.updated_by = "system"
            if getattr(dept, 'created_by', None) is None:
                dept.created_by = "system"
        return departments
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching all departments: {str(e)}")

@router.post("/jobs/{job_id}/apply", response_model=PublicJobApplicationResponse)
async def apply_to_job(
    job_id: str,
    full_name: str = Form(...),
    phone: str = Form(...),
    email: str = Form(...),
    skills: str = Form(...),
    city_location: str = Form(...),
    resume: UploadFile = File(...),
    pan_card_no: Optional[str] = Form(None),
    referred_by: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Public endpoint for applying to a job with direct resume upload.
    Now also accepts PAN card and referred by fields.
    """
    try:
        # Validate file type
        if not resume.filename:
            raise HTTPException(status_code=400, detail="No resume file provided")
        file_extension = os.path.splitext(resume.filename)[1].lower().lstrip('.')
        if file_extension not in ALLOWED_RESUME_EXTENSIONS:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_RESUME_EXTENSIONS)}"
            )
        # Validate form data
        if not full_name.strip():
            raise HTTPException(status_code=400, detail="Full name cannot be empty")
        if not skills.strip():
            raise HTTPException(status_code=400, detail="Skills cannot be empty")
        if not city_location.strip():
            raise HTTPException(status_code=400, detail="City/Location cannot be empty")
        digits_only = ''.join(filter(str.isdigit, phone))
        if len(digits_only) < 10:
            raise HTTPException(status_code=400, detail="Phone number must contain at least 10 digits")
        # PAN card validation (if provided)
        if pan_card_no:
            pan_card = pan_card_no.replace(" ", "").upper()
            import re
            pan_pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$'
            if not re.match(pan_pattern, pan_card):
                raise HTTPException(status_code=400, detail="Invalid PAN card format. Expected format: ABCDE1234F")
            pan_card_no = pan_card
        # Verify that the job exists and is open
        job = db.query(Job).filter(
            Job.job_id == job_id,
            Job.status == "OPEN"
        ).first()
        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Job with ID '{job_id}' not found or not available for applications"
            )
        # Check if email has already applied for this job
        existing_application = db.query(Candidate).filter(
            Candidate.email_id == email,
            Candidate.associated_job_id == job_id
        ).first()
        if existing_application:
            raise HTTPException(
                status_code=400,
                detail=f"This email has already applied for job '{job_id}'. Each email can only apply once per job."
            )
        # Generate unique filename for S3 upload
        unique_filename = f"public-applications/resumes/{job_id}/{uuid.uuid4()}-{resume.filename}"
        # Upload resume to S3
        try:
            s3_client.upload_fileobj(
                resume.file,
                S3_BUCKET,
                unique_filename,
                ExtraArgs={
                    'ContentType': resume.content_type or 'application/octet-stream'
                }
            )
            resume_url = f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{unique_filename}"
        except ClientError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload resume: {str(e)}"
            )
        # Create a new candidate record (which represents the job application)
        new_candidate = Candidate(
            candidate_name=full_name.strip(),
            email_id=email,
            mobile_no=phone,
            skills_set=skills.strip(),
            resume_url=resume_url,
            resume_path=unique_filename,
            current_location=city_location.strip(),
            associated_job_id=job_id,
            application_date=date.today(),
            current_status="Application Received",
            final_status="In progress",
            created_by="public_application",
            department=job.department,
            pan_card_no=pan_card_no,
            referred_by=referred_by
        )
        db.add(new_candidate)
        db.commit()
        db.refresh(new_candidate)
        return PublicJobApplicationResponse(
            message="Application submitted successfully! We will review your application and get back to you soon.",
            candidate_id=new_candidate.candidate_id,
            job_id=job_id,
            application_date=datetime.combine(new_candidate.application_date, datetime.min.time())
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing your application: {str(e)}"
        ) 