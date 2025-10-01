from datetime import date, datetime, timedelta, timezone
from enum import Enum
from io import BytesIO
import os
import re
import random
import string
import pandas as pd
from typing import Annotated, Any, Dict, List, Optional , Union
import uuid
import asyncio
import threading
from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, Form, HTTPException, Path, Query, UploadFile, status
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import Float, and_, func, cast, TEXT, or_, exists, case
from botocore.exceptions import ClientError
import boto3
import logging
from fastapi.responses import FileResponse
import tempfile

from app import schemas
from app import models
from app.database import get_db
from app.models import Candidate, CandidateProgress, DiscussionQuestion,  FinalStatusDB, InterviewStatusDB, Discussion, OfferStatusDB, RatingDB, StatusDB ,Job ,OfferLetterStatus,Employee,GenderDB, User, UserRoleAccess, RoleTemplate, Document
from app.schemas import (
    CandidateResponse, 
    CandidateCreate,
    CandidateSingleEntry, 
    CandidateUpdate,
    CurrentStatusModel,
    DiscussionQuestionCreate,
    DiscussionQuestionResponse,
    DiscussionQuestionUpdate,
    FinalStatusModel,
    FinalStatusUpdate,
    InterviewStatusModel,
    OfferStatusCreate,
    OfferStatusModel,
    OfferStatusUpdate,
    RatingModel,
    RejectOfferRequest, 
    StatusUpdate, 
    ProgressUpdate, 
    InterviewUpdate,
    CandidateListItem,
    CandidateRatingUpdate,
    PaginatedCandidateResponse,
    DiscussionSavePayload,
    DiscussionResponse,
    CandidateDiscussionResponse,
    DiscussionCreate,
    ExcelUploadStatusResponse,
    OfferLetterStatusCreate,
    OfferLetterStatusUpdate,
    OfferLetterStatusResponse,
    CandidateExcelUpload,
    EmployeeCreate,
    EmployeeUpdate,
    EmployeeResponse,
    GenderResponse,
    GenderCreate,
    GenderUpdate,
    RoleTemplateResponse,
    RoleTemplateCreate,
    RoleTemplateUpdate,
    UserRoleAccessResponse,
    UserRoleAccessCreate,
    UserRoleAccessUpdate,
    UserAccessSummary,
    RoleAccessDetails,
    PageAccessResponse,
    PageAccessCreate,
    SubpageAccessResponse,
    SubpageAccessCreate,
    SectionAccessResponse,
    SectionAccessCreate,
    PaginatedUserRoleAccess,
    UserRoleAccessFilter
)
from .. import schemas, database, models

logger = logging.getLogger(__name__)  # Creates a logger for the current module
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# AWS Config
AWS_REGION = os.getenv("AWS_REGION", "ap-south-2")
S3_BUCKET = os.getenv("S3_BUCKET", "upload-media00")
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=AWS_REGION,
    endpoint_url=f"https://s3.{AWS_REGION}.amazonaws.com"
)

print("AWS_REGION", AWS_REGION, os.getenv('AWS_ACCESS_KEY_ID'), os.getenv('AWS_SECRET_ACCESS_KEY'))
# Allowed file types and max size
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

router = APIRouter(
    prefix="/candidates",
    tags=["candidates"],
    responses={404: {"description": "Not found"}},
)

class PaginatedCandidateResponse(BaseModel):
    items: List[dict]
    total: int
    page: int
    items_per_page: int

class ResumeUploadRequest(BaseModel):
    file_name: str
    content_type: str

class CandidateFilter(BaseModel):
    search: Optional[str] = None
    job_filter: Optional[str] = None
    status_filter: Optional[str] = None
    skill_filter: Optional[str] = None
    ctc_filter: Optional[str] = None
    experience_filter: Optional[str] = None
    rating_filter: Optional[str] = None
    sort_key: Optional[str] = None
    sort_order: str = "asc"
    page: int = Query(1, ge=1)
    items_per_page: int = Query(10, ge=1, le=100)

class OfferDetailsUpdate(BaseModel):
    offer_ctc: Optional[float] = None
    offer_date: Optional[date] = None
    offer_status: Optional[str] = None
    joining_date: Optional[date] = None

def get_file_extension(filename):
    return os.path.splitext(filename)[1][1:].lower()

@router.post("/resume-upload-url", status_code=201)
def generate_resume_upload_url(data: ResumeUploadRequest):
    """Generate a presigned URL for resume upload"""
    # Validate file type
    extension = get_file_extension(data.file_name)
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Generate unique filename to prevent overwriting
    unique_filename = f"resumes/{uuid.uuid4()}-{data.file_name}"
    
    try:
        print(f"Generating presigned URL for {unique_filename}", S3_BUCKET, data.content_type)
        url = s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": S3_BUCKET,
                "Key": unique_filename,
                "ContentType": data.content_type,
            },
            ExpiresIn=3600  # 1 hour
        )
        # Generate the download URL that will be stored in the database
        resume_url = f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{unique_filename}"
        print(url, resume_url, "check url")
        return {
            "upload_url": url,
            "resume_url": resume_url,
            "file_key": unique_filename
        }
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=CandidateResponse)
async def create_candidate_form(
    name: str = Form(...),
    email: str = Form(...),
    contact: str = Form(...),
    associatedJobId: Optional[str] = Form(None),
    skills: str = Form(...),
    resumeUrl: str = Form(...),  
    resumeKey: str = Form(...), 
    db: Session = Depends(get_db)
):
    """Create candidate using form data with uploaded resume"""
    try:
        # Automatically assign department based on associated job
        department = get_department_from_job_id(associatedJobId, db) if associatedJobId else None
        
        db_candidate = Candidate(
            candidate_name=name,
            email_id=email,
            mobile_no=contact,
            associated_job_id=associatedJobId,
            skills_set=skills,
            resume_path=resumeKey, 
            resume_url=resumeUrl,   
            application_date=date.today(),
            date_of_resume_received=date.today(),
            status="Pending Review",  
            current_status="Screening",
            department=department , # Automatically assign department
            created_by=candidate_data.created_by,
            expected_date_of_joining=None
       
        )
        db.add(db_candidate)
        db.commit()
        db.refresh(db_candidate)
        
        # Add initial progress
        db_progress = CandidateProgress(candidate_id=db_candidate.candidate_id, status="Application Received")
        db.add(db_progress)
        db.commit()
        
        return db_candidate
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating candidate: {str(e)}")



def validate_pan_card(pan_card: str) -> bool:
    """Validate PAN card format: 5 letters, 4 digits, 1 letter"""
    if not pan_card:
        return True  # Optional field
    pan_pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$'
    return bool(re.match(pan_pattern, pan_card.upper()))

def should_set_rejected_date(current_status: str = None, final_status: str = None) -> bool:
    """Check if rejected_date should be set based on status values"""
    rejection_statuses = ['Screening Rejected', 'Rejected', 'Offer Declined']
    return (
        (current_status and current_status in rejection_statuses) or 
        (final_status and final_status == 'Rejected')
    )


@router.post("/create", response_model=CandidateResponse)
def create_candidate_json(candidate: CandidateCreate, db: Session = Depends(get_db)):
    """Create candidate using JSON payload"""
    try:
        # Convert skills list to comma-separated string if skills_set is provided
        skills_str = ", ".join(candidate.skills_set) if candidate.skills_set else None
        
        candidate_dict = candidate.model_dump()
        if "skills_set" in candidate_dict:
            candidate_dict["skills_set"] = skills_str
      
      # Handle PAN card validation and formatting
        if candidate_dict.get("pan_card_no"):
            pan_card = candidate_dict["pan_card_no"].replace(" ", "").upper()
            if not validate_pan_card(pan_card):
                raise HTTPException(
                    status_code=400, 
                    detail="Invalid PAN card format. Expected format: ABCDE1234F"
                )
            candidate_dict["pan_card_no"] = pan_card


        field_mapping = {
            "current_variable_ctc": "current_variable_pay",  
            "reason_for_change": "reason_for_job_change",    
            "additional_info_npd": "npd_info",              
             "ta_team": "ta_team",
             "ta_comments": "ta_comments",
             "linkedin_url": "linkedin_url",
            "current_address": "current_address",   
            "permanent_address": "permanent_address",
            "current_location":"current_location" ,
            "final_status": "final_status",
            "department": "department",
            "gender":"gender"
        }
        
        # Apply field mapping
        for frontend_field, db_field in field_mapping.items():
            if frontend_field in candidate_dict:
                candidate_dict[db_field] = candidate_dict.pop(frontend_field)

         # Handle rejected_date logic for new candidates
        current_status = candidate_dict.get("status") or candidate_dict.get("current_status")
        final_status = candidate_dict.get("final_status")
        
        if should_set_rejected_date(current_status, final_status):
            candidate_dict["rejected_date"] = date.today()
        else:
            candidate_dict["rejected_date"] = None

        # Automatically assign department based on associated job if not already provided
        if not candidate_dict.get("department") and candidate_dict.get("associated_job_id"):
            candidate_dict["department"] = get_department_from_job_id(candidate_dict["associated_job_id"], db)
 
        candidate_dict["created_by"] = candidate_data.created_by
        

        db_candidate = Candidate(**candidate_dict)
        db.add(db_candidate)
        db.commit()
        db.refresh(db_candidate)
        
        # Add initial progress
        db_progress = CandidateProgress(candidate_id=db_candidate.candidate_id, status="Application Received")
        db.add(db_progress)
        db.commit()
        
        return db_candidate
    except Exception as e:
        db.rollback()
    ##Add detailed exception information for debugging
        import traceback
        error_details = traceback.format_exc()
        print(f"Error creating candidate: {str(e)}\n{error_details}")
        raise HTTPException(status_code=500, detail=f"Error creating candidate: {str(e)}")

@router.put("/update/{candidate_id}", response_model=CandidateResponse)
def update_candidate(candidate_id: str, update_data: CandidateUpdate, db: Session = Depends(get_db)):
    try:
        # Fetch the candidate from the database
        db_candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
        if not db_candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")

        # Convert update_data to dictionary, excluding unset fields
        update_dict = update_data.model_dump(exclude_unset=True)
        print(f"Received update payload: {update_dict}")

        # Handle PAN card validation and formatting
        if "pan_card_no" in update_dict:
            pan_card = update_dict["pan_card_no"]
            if pan_card:
                pan_card = pan_card.replace(" ", "").upper()
                if not validate_pan_card(pan_card):
                    raise HTTPException(
                        status_code=400, 
                        detail="Invalid PAN card format. Expected format: ABCDE1234F"
                    )
                update_dict["pan_card_no"] = pan_card
                print(f"Validated and formatted PAN card: {pan_card}")
            else:
                update_dict["pan_card_no"] = None

        # Handle skills_set if present
        if "skills_set" in update_dict:
            update_dict["skills_set"] = ", ".join(update_dict["skills_set"]) if update_dict["skills_set"] else None
            print(f"Processed skills_set: {update_dict['skills_set']}")

        # Map frontend fields to database fields
        field_mapping = {
            "reason_for_change": "reason_for_job_change",
            "additional_info_npd": "additional_info_npd",
            "ta_team": "ta_team",
            "ta_comments": "ta_comments",
            "linkedin_url": "linkedin_url",
            "current_address": "current_address",
            "permanent_address": "permanent_address",
            "current_location": "current_location",
            "final_status": "final_status",
            "department": "department",
            "notice_period": "notice_period",
            "notice_period_units": "notice_period_units",
            "current_fixed_ctc": "current_fixed_ctc",
            "expected_fixed_ctc": "expected_fixed_ctc",  # Ensure mapping is present
            "mode_of_work": "mode_of_work",
            "current_variable_pay": "current_variable_pay",
            "gender":"gender"
        }

        # Transform frontend field names to database field names
        for frontend_field, db_field in field_mapping.items():
            if frontend_field in update_dict:
                update_dict[db_field] = update_dict.pop(frontend_field)
                print(f"Mapped {frontend_field} to {db_field} with value: {update_dict[db_field]}")

        # Explicitly handle expected_fixed_ctc to prevent null
        if "expected_fixed_ctc" in update_dict:
            value = update_dict["expected_fixed_ctc"]
            print(f"Processing expected_fixed_ctc: Raw value = {value}, Type = {type(value)}")
            if value is not None:
                try:
                    # Convert to float and ensure it's a valid number
                    update_dict["expected_fixed_ctc"] = float(value)
                    if update_dict["expected_fixed_ctc"] < 0:
                        raise ValueError("expected_fixed_ctc cannot be negative")
                    print(f"Converted expected_fixed_ctc to: {update_dict['expected_fixed_ctc']}")
                except (ValueError, TypeError) as e:
                    print(f"Invalid expected_fixed_ctc value: {value}, Error: {str(e)}")
                    update_dict["expected_fixed_ctc"] = None  # Set to None only if conversion fails
            else:
                print("expected_fixed_ctc is explicitly set to None in payload")
        else:
            print("expected_fixed_ctc not included in update payload")

     # Handle rejected_date logic based on status changes
        current_status_changed = "current_status" in update_dict
        final_status_changed = "final_status" in update_dict
        
        if current_status_changed or final_status_changed:
            # Get the new status values (use existing values if not being updated)
            new_current_status = update_dict.get("current_status", db_candidate.current_status)
            new_final_status = update_dict.get("final_status", db_candidate.final_status)
            
            # Set rejected_date based on new status values
            if should_set_rejected_date(new_current_status, new_final_status):
                update_dict["rejected_date"] = date.today()
                print(f"Setting rejected_date to today due to status: current={new_current_status}, final={new_final_status}")
            else:
                update_dict["rejected_date"] = None
                print(f"Clearing rejected_date due to status: current={new_current_status}, final={new_final_status}")
            
            # Update status_updated_on when status changes
            if current_status_changed:
                update_dict["status_updated_on"] = date.today()

        # Set metadata
        update_dict["updated_by"] = update_dict.get("updated_by", "taadmin")
        update_dict["updated_at"] = datetime.utcnow()

        # Apply updates to the database model
        for key, value in update_dict.items():
            if hasattr(db_candidate, key):
                print(f"Setting {key} to {value} (Type: {type(value)})")
                setattr(db_candidate, key, value)
            else:
                print(f"Warning: Field '{key}' not found in Candidate model")

        # Log the state before committing
        print(f"Pre-commit candidate state: {db_candidate.__dict__}")

        # Commit changes to the database
        db.commit()
        db.refresh(db_candidate)

        # Log the final state after commit
        print(f"Post-commit candidate state: {db_candidate.__dict__}")
        return db_candidate

    except Exception as e:
        db.rollback()
        print(f"Error updating candidate: {str(e)}")
        raise HTTPException(status_code=422, detail=f"Error updating candidate: {str(e)}")

@router.get("/resume/{file_key}")
def get_resume_access_url(file_key: str):
    """Generate a temporary URL to access the resume"""
    try:
        url = s3_client.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": S3_BUCKET,
                "Key": file_key
            },
            ExpiresIn=3600  # 1 hour
        )
        return {"access_url": url}
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=PaginatedCandidateResponse)
def read_candidates(filters: CandidateFilter = Depends(), db: Session = Depends(get_db)):
    """Get paginated list of candidates with optional filtering"""
    query = db.query(Candidate)
    

    # Apply filters - with improved matching logic
    if filters.search:
        search_term = f"%{filters.search.lower()}%"
        query = query.filter(func.lower(Candidate.candidate_name).like(search_term))

    if filters.job_filter:
        # Filter by associated_job_id for exact job matching
        query = query.filter(Candidate.associated_job_id == filters.job_filter)

    if filters.status_filter:
        # Case-insensitive comparison for status
        status_term = f"%{filters.status_filter.lower()}%"
        query = query.filter(func.lower(Candidate.status).like(status_term))

    from sqlalchemy import or_

    if filters.skill_filter:
        skills = [skill.strip().lower() for skill in filters.skill_filter.split(",")]
        skill_conditions = [
            func.lower(cast(Candidate.skills_set, TEXT)).like(f"%{skill}%")
            for skill in skills
        ]
        query = query.filter(or_(*skill_conditions))

    if filters.ctc_filter:
        try:
            if "+" in filters.ctc_filter:
                min_ctc = float(filters.ctc_filter.replace("+", ""))
                query = query.filter(Candidate.current_fixed_ctc >= min_ctc)
            elif "-" in filters.ctc_filter:
                min_ctc, max_ctc = map(float, filters.ctc_filter.split("-"))
                query = query.filter(Candidate.current_fixed_ctc >= min_ctc, Candidate.current_fixed_ctc <= max_ctc)
        except ValueError:
            # Log the error instead of raising exception
            print(f"Invalid CTC filter format: {filters.ctc_filter}")
            # Continue with query without applying this filter

    if filters.experience_filter:
        try:
            if "+" in filters.experience_filter:
                min_exp = float(filters.experience_filter.replace("+", ""))
                query = query.filter(Candidate.years_of_exp >= min_exp)
            elif "-" in filters.experience_filter:
                min_exp, max_exp = map(float, filters.experience_filter.split("-"))
                query = query.filter(Candidate.years_of_exp >= min_exp, Candidate.years_of_exp <= max_exp)
        except ValueError:
            # Log the error instead of raising exception
            print(f"Invalid experience filter format: {filters.experience_filter}")
            # Continue with query without applying this filter

    if filters.rating_filter:
        # Case-insensitive matching for rating
        rating_term = f"%{filters.rating_filter.lower()}%"
        query = query.filter(func.lower(Candidate.rating).like(rating_term))

    # Add debug output to check the SQL query
    print(str(query.statement.compile(compile_kwargs={"literal_binds": True})))

    # Apply sorting
    if filters.sort_key:
        sort_column = getattr(Candidate, filters.sort_key, None)
        if sort_column is not None:
            if filters.sort_order and filters.sort_order.lower() == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())

    # Count total and paginate
    total = query.count()
    items = query.offset((filters.page - 1) * filters.items_per_page).limit(filters.items_per_page).all()

    # Process candidates
    processed_candidates = []
    for candidate in items:
        candidate_dict = {column.name: getattr(candidate, column.name) for column in candidate.__table__.columns}
         # Instead of accessing candidate.job.job_title, use the associated_job_id if needed
        candidate_dict["job_title"] = candidate_dict.get("associated_job_id", "Not specified")
        
        # Ensure skills_set is processed as a list
        if candidate_dict.get("skills_set"):
            candidate_dict["skills_set"] = [skill.strip() for skill in candidate_dict["skills_set"].split(",")]
        else:
            candidate_dict["skills_set"] = []
                # Ensure linkedin_url is included (will be None if not present)
        if "linkedin_url" not in candidate_dict:
            candidate_dict["linkedin_url"] = None
        # Set defaults for string fields
        for field in ["status", "current_status"]:
            if candidate_dict.get(field) is None:
                candidate_dict[field] = "Not specified" if field == "status" else "Screening"

        # Set default dates
        for date_field in ["application_date", "date_of_resume_received"]:
            if candidate_dict.get(date_field) is None:
                candidate_dict[date_field] = date.today()
        
         # Add created_by and updated_by
        candidate_dict["created_by"] = candidate.created_by or "taadmin"
        candidate_dict["updated_by"] = candidate.updated_by or None  # Or use "taadmin" if you want to show it


        processed_candidates.append(candidate_dict)

    return {
        "total": total, 
        "page": filters.page,
         "items_per_page": filters.items_per_page,
        "items": processed_candidates
          }


@router.get("/list", response_model=List[dict])  
def get_all_candidates(db: Session = Depends(get_db)):
    """
    Retrieves a list of candidates with complete details including all interview stages, 
    offer information, and other candidate data.
    """
    candidates = db.query(Candidate).all()
    # Process each candidate to ensure proper data formatting
    processed_candidates = []
    for candidate in candidates:
        # Convert model to dict
        candidate_dict = {column.name: getattr(candidate, column.name) for column in candidate.__table__.columns}
        # Instead of accessing candidate.job.job_title, use the associated_job_id if needed
        candidate_dict["job_title"] = candidate_dict.get("associated_job_id", "Not specified")
        print(candidate_dict)
        # Format skills_set as list (if it exists and is not None)
        if candidate_dict.get("skills_set"):
            candidate_dict["skills_set"] = [skill.strip() for skill in candidate_dict["skills_set"].split(",")]
        else:
            candidate_dict["skills_set"] = []
          # Ensure linkedin_url is included (will be None if not present)
        if "linkedin_url" not in candidate_dict:
            candidate_dict["linkedin_url"] = None



        # Handle PAN card field - ensure it's included and properly formatted
        if "pan_card_no" not in candidate_dict:
            candidate_dict["pan_card_no"] = None
        elif candidate_dict["pan_card_no"]:
            # Ensure PAN card is in uppercase (defensive programming)
            candidate_dict["pan_card_no"] = candidate_dict["pan_card_no"].upper()
        
        # Handle rejected_date field - ensure it's included
        if "rejected_date" not in candidate_dict:
            candidate_dict["rejected_date"] = None
        # Convert date to string format if it exists (for JSON serialization)
        elif candidate_dict["rejected_date"]:
            candidate_dict["rejected_date"] = candidate_dict["rejected_date"].isoformat()
        
        
        # Handle enum values safely - convert to string representation
        if "current_status" in candidate_dict and candidate_dict["current_status"] is not None:
            candidate_dict["current_status"] = str(candidate_dict["current_status"])
        
        # Handle any other enum fields if present
        if "offer_status" in candidate_dict and candidate_dict["offer_status"] is not None:
            candidate_dict["offer_status"] = str(candidate_dict["offer_status"])
        # Add created_by and updated_by explicitly
        candidate_dict["created_by"] = candidate.created_by or "taadmin"
        candidate_dict["updated_by"] = candidate.updated_by or "taadmin"


        # Add a helper field to indicate if candidate was rejected (for frontend convenience)
        candidate_dict["is_rejected"] = candidate_dict["rejected_date"] is not None
        
        # Add PAN card validation status (for frontend validation feedback)
        candidate_dict["pan_card_valid"] = bool(
            candidate_dict.get("pan_card_no") and 
            len(candidate_dict["pan_card_no"]) == 10 and
            candidate_dict["pan_card_no"].isalnum()
        ) if candidate_dict.get("pan_card_no") else None


        processed_candidates.append(candidate_dict)
        
    return processed_candidates


@router.get("/ids-names")
def get_candidates_ids_and_names(
    db: Session = Depends(get_db),
    search: Optional[str] = Query(None, description="Filter by candidate name, email, or ID (partial match)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Number of candidates per page")
):
    """
    Get paginated candidate IDs and names, with optional search by name, email, or ID.
    """
    try:
        query = db.query(Candidate.candidate_id, Candidate.candidate_name)
        # Add search filter if provided
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Candidate.candidate_name.ilike(search_term),
                    Candidate.email_id.ilike(search_term),
                    Candidate.candidate_id.ilike(search_term)
                )
            )
        total = query.count()
        # Pagination
        offset = (page - 1) * limit
        query = query.order_by(Candidate.candidate_name).offset(offset).limit(limit)
        candidates = query.all()
        items = [
            {"candidate_id": candidate.candidate_id, "candidate_name": candidate.candidate_name}
            for candidate in candidates
        ]
        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching candidates: {str(e)}")


#################################### candidate table

@router.get("/alldetails", response_model=PaginatedCandidateResponse)
def get_all_candidates_details(
    db: Session = Depends(get_db),
    page: int = 1,
    items_per_page: int = 6,
    search: Optional[str] = None,
    rating_filter: Optional[str] = None,
    status_filter: Optional[str] = None,  # For interview_progress_status
    current_status_filter: Optional[str] = None,  # New parameter for current_status
    final_status_filter: Optional[str] = None,  # New parameter for final_status
    skill_filter: Optional[str] = None,  # Legacy parameter for backward compatibility
    skills_filter: Optional[str] = None,  # New parameter matching frontend requirements
    ctc_filter: Optional[str] = None,
    experience_filter: Optional[str] = None,
    sort_key: Optional[str] = None,
    sort_order: Optional[str] = "asc",
    associated_job_id: Optional[str] = None,
    department: Optional[str] = None,
    ta_team: Optional[str] = None,
    ta_team_member: Optional[str] = None,
    notice_period_filter: Optional[str] = None,
    referred_by: Optional[str] = None,  # <-- Add this line
    # New audit filters
    updated_by: Optional[str] = Query(None, alias="update_by"),
    created_by: Optional[str] = None,
    updated_at: Optional[str] = None,  # Accept single date or comma-separated range: DD-MM-YYYY[,DD-MM-YYYY]
    created_at: Optional[str] = None   # Accept single date or comma-separated range: DD-MM-YYYY[,DD-MM-YYYY]
):
    try:
        print(f"Received parameters: page={page}, items_per_page={items_per_page}, "
              f"search={search}, rating_filter={rating_filter}, status_filter={status_filter}, "
              f"current_status_filter={current_status_filter}, final_status_filter={final_status_filter}, "
              f"skill_filter={skill_filter}, skills_filter={skills_filter}, ctc_filter={ctc_filter}, experience_filter={experience_filter}, "
              f"sort_key={sort_key}, sort_order={sort_order}, associated_job_id={associated_job_id}, "
              f"department={department}, ta_team={ta_team}, ta_team_member={ta_team_member}, "
              f"updated_by={updated_by}, created_by={created_by}, updated_at={updated_at}, created_at={created_at}")

        # Base query
        query = db.query(Candidate)

        # Apply filters
        if search:
           query = query.filter(
           or_(
            Candidate.candidate_name.ilike(f"%{search}%"),
            Candidate.email_id.ilike(f"%{search}%"),
            Candidate.mobile_no.ilike(f"%{search}%"),
            Candidate.candidate_id.ilike(f"%{search}%")  # Add candidate_id to search
        )
    )

        if associated_job_id:
            print(f"Filtering by associated_job_id: {associated_job_id}")
            if associated_job_id == "null":
                query = query.filter(Candidate.associated_job_id.is_(None))
            else:
                query = query.filter(
                or_(
                    Candidate.associated_job_id == associated_job_id,  # Exact match for single job
                    Candidate.associated_job_id.like(f"{associated_job_id},%"),  # Job ID at start
                    Candidate.associated_job_id.like(f"%,{associated_job_id},%"),  # Job ID in middle
                    Candidate.associated_job_id.like(f"%,{associated_job_id}")  # Job ID at end
                )
            )

        if rating_filter and rating_filter != "all":
            query = query.filter(func.lower(Candidate.rating) == rating_filter.lower())

        # Interview Status Filter (maps to interview_progress_status)
        if status_filter and status_filter != "all":
            status_mapping = {
                "not started": "Not Started",
                "l1 interview": "L1 Interview",
                "l2 interview": "L2 Interview",
                "hr round": "HR Round",
                "offer stage": "Offer Stage",
                "joined": "Joined",
                "rejected": "Rejected",
                "declined": "Offer Declined"
            }
            db_status = status_mapping.get(status_filter.lower())
            if db_status:
                query = query.filter(Candidate.interview_progress_status == db_status)
            else:
                print(f"Invalid status_filter: {status_filter}, expected one of {list(status_mapping.keys())}")

        # Current Status Filter
        if current_status_filter and current_status_filter != "all":
            status_mapping = {
                "screening": "Screening",
                "yet to call": "Yet to Call",
                "in pipeline": "In Pipeline",
                "scheduled": "Scheduled",
                "l1 interview": "L1 Interview",
                "l2 interview": "L2 Interview",
                "hr round": "HR Round",
                "docs upload": "Docs Upload",
                "ctc breakup": "CTC Breakup",
                "create offer": "Create Offer",
                "offer initiated": "Offer Initiated",
                "offer accepted": "Offer Accepted",
                "offer declined": "Offer Declined",
                "rejected": "Rejected",
                "in discussion": "In Discussion",
                "onboarded": "Onboarded"
            }
            db_status = status_mapping.get(current_status_filter.lower())
            if db_status:
                query = query.filter(Candidate.current_status == db_status)
            else:
                print(f"Invalid current_status_filter: {current_status_filter}, expected one of {list(status_mapping.keys())}")

        # Final Status Filter
        if final_status_filter and final_status_filter != "all":
            query = query.filter(func.lower(Candidate.final_status) == final_status_filter.lower())

        # Skills filtering - support both skill_filter (legacy) and skills_filter (new)
        # Use skills_filter if provided, otherwise fallback to skill_filter for backward compatibility
        active_skills_filter = skills_filter if skills_filter is not None else skill_filter
        
        if active_skills_filter and active_skills_filter != "all":
            skill_list = [skill.strip().lower() for skill in active_skills_filter.split(",") if skill.strip()]
            if skill_list:  # Only apply filter if we have actual skills after splitting and stripping
                # Create a filter condition for each skill using case-insensitive partial matching
                skill_filters = [func.lower(Candidate.skills_set).ilike(f"%{skill}%") for skill in skill_list]
                # Combine with OR operator (candidates match if they have ANY of the specified skills)
                query = query.filter(or_(*skill_filters))

        if ctc_filter and ctc_filter != "all":
            total_ctc = (Candidate.current_fixed_ctc + Candidate.current_variable_pay).cast(Float)
            if ctc_filter.endswith("+"):
                min_ctc = float(ctc_filter.rstrip("+")) * 100000
                query = query.filter(total_ctc >= min_ctc)
            else:
                min_ctc, max_ctc = map(float, ctc_filter.split("-"))
                query = query.filter(total_ctc.between(min_ctc * 100000, max_ctc * 100000))

        if experience_filter and experience_filter != "all":
            if experience_filter == "fresher":
                query = query.filter(Candidate.years_of_exp == 0)
            elif experience_filter.endswith("+"):
                min_exp = float(experience_filter.rstrip("+"))
                query = query.filter(Candidate.years_of_exp >= min_exp)
            else:
                min_exp, max_exp = map(float, experience_filter.split("-"))
                query = query.filter(Candidate.years_of_exp.between(min_exp, max_exp))

        if department and department != "all":
            query = query.filter(func.lower(Candidate.department) == department.lower())

        if ta_team and ta_team != "all":
            query = query.filter(func.lower(Candidate.ta_team) == ta_team.lower())

        if ta_team_member and ta_team_member != "all":
            query = query.filter(Candidate.ta_team_member == ta_team_member)
            
        if notice_period_filter and notice_period_filter != "all":
            if notice_period_filter.endswith("+"):
                min_period = int(notice_period_filter.rstrip("+"))
                query = query.filter(Candidate.notice_period >= min_period)
            else:
                min_period, max_period = map(int, notice_period_filter.split("-"))
                query = query.filter(Candidate.notice_period.between(min_period, max_period))    

        # Add filter for referred_by
        if referred_by:
            query = query.filter(Candidate.referred_by.ilike(f"%{referred_by}%"))

        # New: Filter by updated_by email (case-insensitive exact match)
        if updated_by:
            query = query.filter(func.lower(Candidate.updated_by) == updated_by.lower())

        # New: Filter by created_by email (case-insensitive exact match)
        if created_by:
            query = query.filter(func.lower(Candidate.created_by) == created_by.lower())

        # Helper to parse single date string in DD-MM-YYYY or YYYY-MM-DD
        def _parse_date_str(date_str: str) -> date:
            try:
                return datetime.strptime(date_str.strip(), '%d-%m-%Y').date()
            except ValueError:
                return datetime.strptime(date_str.strip(), '%Y-%m-%d').date()

        # New: Filter by updated_at (single date or comma-separated range)
        if updated_at:
            try:
                if ',' in updated_at:
                    start_str, end_str = [part.strip() for part in updated_at.split(',', 1)]
                else:
                    start_str, end_str = updated_at.strip(), updated_at.strip()
                start_date = _parse_date_str(start_str)
                end_date = _parse_date_str(end_str)
                end_date_plus_one = end_date + timedelta(days=1)
                query = query.filter(Candidate.updated_at >= start_date)
                query = query.filter(Candidate.updated_at < end_date_plus_one)
            except ValueError:
                raise HTTPException(status_code=400, detail='Invalid updated_at format. Use DD-MM-YYYY or DD-MM-YYYY,DD-MM-YYYY')

        # New: Filter by created_at (single date or comma-separated range)
        if created_at:
            try:
                if ',' in created_at:
                    start_str, end_str = [part.strip() for part in created_at.split(',', 1)]
                else:
                    start_str, end_str = created_at.strip(), created_at.strip()
                start_date = _parse_date_str(start_str)
                end_date = _parse_date_str(end_str)
                end_date_plus_one = end_date + timedelta(days=1)
                query = query.filter(Candidate.created_at >= start_date)
                query = query.filter(Candidate.created_at < end_date_plus_one)
            except ValueError:
                raise HTTPException(status_code=400, detail='Invalid created_at format. Use DD-MM-YYYY or DD-MM-YYYY,DD-MM-YYYY')

        # Apply sorting (independent of filters)
        if sort_key and sort_key != "all" and sort_key.strip():
            print(f"Applying sorting: sort_key={sort_key}, sort_order={sort_order}")

            # Computed/related columns
            total_ctc_expr = (
                func.coalesce(Candidate.current_fixed_ctc, 0) + func.coalesce(Candidate.current_variable_pay, 0)
            )
            docs_exists = exists().where(Document.candidate_id == Candidate.candidate_id).correlate(Candidate)
            docs_flag = case((docs_exists, 1), else_=0)

            # Choose column/expression
            sort_expr = None
            join_employee = False

            if sort_key == "candidate_id":
                sort_expr = Candidate.candidate_id
            elif sort_key == "candidate_name":
                sort_expr = Candidate.candidate_name
            elif sort_key in ("contact_no", "mobile_no"):
                sort_expr = Candidate.mobile_no
            elif sort_key in ("email", "email_id"):
                sort_expr = Candidate.email_id
            elif sort_key in ("pan", "pan_card_no"):
                sort_expr = Candidate.pan_card_no
            elif sort_key == "gender":
                sort_expr = Candidate.gender
            elif sort_key in ("current_location", "location"):
                sort_expr = Candidate.current_location
            elif sort_key in ("skills", "skills_set"):
                sort_expr = Candidate.skills_set
            elif sort_key in ("associated_job_id", "applied_for"):
                sort_expr = Candidate.associated_job_id
            elif sort_key in ("application_date", "applied_date"):
                sort_expr = Candidate.application_date
            elif sort_key == "department":
                sort_expr = Candidate.department
            elif sort_key == "date_of_resume_received":
                sort_expr = Candidate.date_of_resume_received
            elif sort_key in ("years_of_exp", "experience"):
                sort_expr = Candidate.years_of_exp
            elif sort_key == "current_designation":
                sort_expr = Candidate.current_designation
            elif sort_key == "current_company":
                sort_expr = Candidate.current_company
            elif sort_key in ("current_fixed_ctc", "fixed_ctc"):
                sort_expr = Candidate.current_fixed_ctc
            elif sort_key in ("current_variable_pay", "variable_ctc"):
                sort_expr = Candidate.current_variable_pay
            elif sort_key in ("current_total_ctc", "total_ctc"):
                sort_expr = total_ctc_expr
            elif sort_key in ("expected_ctc", "expected_fixed_ctc"):
                sort_expr = Candidate.expected_fixed_ctc
            elif sort_key == "notice_period":
                # Try numeric ordering if possible
                sort_expr = cast(Candidate.notice_period, Float)
            elif sort_key in ("mode_of_work", "work_mode"):
                sort_expr = Candidate.mode_of_work
            elif sort_key == "l1_interview_date":
                sort_expr = Candidate.l1_interview_date
            elif sort_key == "l1_interview_status" or sort_key == "l1_status":
                sort_expr = Candidate.l1_status
            elif sort_key == "l2_interview_date":
                sort_expr = Candidate.l2_interview_date
            elif sort_key == "l2_interview_status" or sort_key == "l2_status":
                sort_expr = Candidate.l2_status
            elif sort_key == "hr_interview_date":
                sort_expr = Candidate.hr_interview_date
            elif sort_key == "hr_interview_status" or sort_key == "hr_status":
                sort_expr = Candidate.hr_status
            elif sort_key == "offer_status":
                sort_expr = Candidate.offer_status
            elif sort_key in ("documents_status", "documents"):
                sort_expr = docs_flag
            elif sort_key == "current_status":
                sort_expr = Candidate.current_status
            elif sort_key == "final_status":
                sort_expr = Candidate.final_status
            elif sort_key == "created_by":
                sort_expr = Candidate.created_by
            elif sort_key == "updated_by":
                sort_expr = Candidate.updated_by
            elif sort_key == "created_at":
                sort_expr = Candidate.created_at
            elif sort_key == "updated_at":
                sort_expr = Candidate.updated_at
            elif sort_key in ("employee_id", "employee_no"):
                join_employee = True
                sort_expr = Employee.employee_no
            elif sort_key == "date_of_joining":
                join_employee = True
                sort_expr = Employee.date_of_joining
            elif sort_key == "referred_by":
                sort_expr = Candidate.referred_by

            if join_employee:
                query = query.outerjoin(Employee, Employee.candidate_id == Candidate.candidate_id)

            if sort_expr is not None:
                if (sort_order or "asc").lower() == "desc":
                    query = query.order_by(sort_expr.desc().nulls_last())
                else:
                    query = query.order_by(sort_expr.asc().nulls_last())
            else:
                print(f"Invalid sort_key: {sort_key}, skipping sorting")

        print(f"Generated SQL Query: {str(query)}")

        total = query.count()
        print(f"Total candidates before pagination: {total}")
        
        # Debug: Check if we have any candidates with this job_id at all
        if associated_job_id:
            # Check both exact match and comma-separated values
            all_candidates_with_job = db.query(Candidate).filter(
                or_(
                    Candidate.associated_job_id == associated_job_id,
                    Candidate.associated_job_id.like(f"{associated_job_id},%"),
                    Candidate.associated_job_id.like(f"%,{associated_job_id},%"),
                    Candidate.associated_job_id.like(f"%,{associated_job_id}")
                )
            ).all()
            print(f"Debug: Found {len(all_candidates_with_job)} candidates with associated_job_id containing {associated_job_id}")
            for candidate in all_candidates_with_job:
                print(f"  - Candidate ID: {candidate.candidate_id}, Name: {candidate.candidate_name}, Job ID: {candidate.associated_job_id}")

        candidates = query.offset((page - 1) * items_per_page).limit(items_per_page).all()
        print(f"Retrieved candidates: {len(candidates)}")

        if not candidates:
            print("No candidates found, returning empty response.")
            return {
                "items": [],
                "total": total,
                "page": page,
                "items_per_page": items_per_page
            }

        result = []
        for db_candidate in candidates:
            interview_progress = "Not Started"
            if db_candidate.status:
                status_mapping = {
                    "L1_INTERVIEW": "L1 Interview",
                    "L2_INTERVIEW": "L2 Interview",
                    "HR_ROUND": "HR Round",
                    "OFFER_INITIATED": "Offer Stage",
                    "ONBOARDED": "Joined",
                    "REJECTED": "Rejected",
                    "OFFER_DECLINED": "Declined"
                }
                interview_progress = status_mapping.get(db_candidate.status, db_candidate.status)

            documents_status = "⚠️ Pending"
            if hasattr(db_candidate, 'documents_verified') and db_candidate.documents_verified:
                documents_status = "✅ Submitted"

            joining_status = "Pending"
            if db_candidate.status == "ONBOARDED":
                joining_status = "Onboarded"
            elif db_candidate.status == "OFFER_DECLINED":
                joining_status = "Declined"

            offer_status = "Not Initiated"
            if db_candidate.offer_status:
                if db_candidate.offer_status == "SENT":
                    offer_status = "In Progress"
                elif db_candidate.offer_status == "ACCEPTED":
                    offer_status = "Selected"
                elif db_candidate.offer_status == "DECLINED":
                    offer_status = "Rejected"

            notice_period_display = getattr(db_candidate, 'notice_period', None)
            notice_period_unit = getattr(db_candidate, 'notice_period_unit', 'Days')
            if notice_period_display is not None:
                notice_period_display = f"{notice_period_display} {notice_period_unit}"

            rating = getattr(db_candidate, 'rating', None)

            job_title = None
            associated_job_id = getattr(db_candidate, 'associated_job_id', None)
            if hasattr(db_candidate, 'job') and db_candidate.job:
                job_title = db_candidate.job.job_title

                        # Handle PAN card field - ensure it's properly formatted
            pan_card_no = getattr(db_candidate, 'pan_card_no', None)
            if pan_card_no:
                pan_card_no = pan_card_no.upper()  # Ensure PAN card is in uppercase
            # Handle rejected_date field and convert to ISO format if exists
            rejected_date = getattr(db_candidate, 'rejected_date', None)
            if rejected_date:
                rejected_date = rejected_date.isoformat()

            candidate_data = {
                "candidate_id": db_candidate.candidate_id,
                "candidate_name": getattr(db_candidate, 'candidate_name', None),
                "email_id": getattr(db_candidate, 'email_id', None),
                "mobile_no": getattr(db_candidate, 'mobile_no', None),
                "linkedin_url": getattr(db_candidate, 'linkedin_url', None),
                "applied_position": job_title,
                "associated_job_id": associated_job_id,
                "status": getattr(db_candidate, 'status', None) or "Screening",
                "current_status": getattr(db_candidate, 'current_status', None) or "Screening",
                "final_status": getattr(db_candidate, 'final_status', None),
                "years_of_exp": getattr(db_candidate, 'years_of_exp', None),
                "current_designation": getattr(db_candidate, 'current_designation', None),
                "current_company": getattr(db_candidate, 'current_company', None),
                "current_fixed_ctc": getattr(db_candidate, 'current_fixed_ctc', None),
                "current_variable_pay": getattr(db_candidate, 'current_variable_pay', None),
                "expected_fixed_ctc": getattr(db_candidate, 'expected_fixed_ctc', None),
                "expected_ctc": getattr(db_candidate, 'expected_ctc', None),
                "offer_ctc": getattr(db_candidate, 'offer_ctc', None),
                "ctc": getattr(db_candidate, 'ctc', None),
                "current_location": getattr(db_candidate, 'current_location', None),
                "current_address": getattr(db_candidate, 'current_address', None),
                "permanent_address": getattr(db_candidate, 'permanent_address', None),
                "notice_period": notice_period_display,
                "notice_period_unit": notice_period_unit,
                "mode_of_work": getattr(db_candidate, 'mode_of_work', None),
                "work_mode_preference": getattr(db_candidate, 'work_mode_preference', None),
                "reason_for_change": getattr(db_candidate, 'reason_for_change', None),
                "interview_progress_status": interview_progress,
                "offer_status": offer_status,
                "documents_status": documents_status,
                "joining_status": joining_status,
                "rating": rating,
                "date_of_resume_received": getattr(db_candidate, 'date_of_resume_received', None),
                "application_date": getattr(db_candidate, 'application_date', None),
                "date_of_joining": getattr(db_candidate, 'date_of_joining', None),
                "l1_interview_date": getattr(db_candidate, 'l1_interview_date', None),
                "l1_interviewers_name": getattr(db_candidate, 'l1_interviewers_name', None),
                "l1_status": getattr(db_candidate, 'l1_status', None),
                "l2_interview_date": getattr(db_candidate, 'l2_interview_date', None),
                "l2_interviewers_name": getattr(db_candidate, 'l2_interviewers_name', None),
                "l2_status": getattr(db_candidate, 'l2_status', None),
                "hr_interview_date": getattr(db_candidate, 'hr_interview_date', None),
                "hr_interviewer_name": getattr(db_candidate, 'hr_interviewer_name', None),
                "hr_status": getattr(db_candidate, 'hr_status', None),
                "additional_info": getattr(db_candidate, 'additional_info', None),
                "resume_url": getattr(db_candidate, 'resume_url', None),
                "offered_designation": getattr(db_candidate, 'offered_designation', None),
                "skills_set": getattr(db_candidate, 'skills_set', []),
                "department": getattr(db_candidate, 'department', None),
                "ta_team": getattr(db_candidate, 'ta_team', None),
                "ta_team_member": getattr(db_candidate, 'ta_team_member', None),
                "created_by": getattr(db_candidate, 'created_by', None),
                "updated_by": getattr(db_candidate, 'updated_by', None),
                "created_at": getattr(db_candidate, 'created_at', None),
                "updated_at": getattr(db_candidate, 'updated_at', None),
                "gender": getattr(db_candidate, 'gender', None),
        
                "pan_card_no": pan_card_no,
                "rejected_date": rejected_date,
                # Add helper fields for frontend convenience
                "is_rejected": rejected_date is not None,
                "pan_card_valid": bool(
                    pan_card_no and 
                    len(pan_card_no) == 10 and
                    pan_card_no.isalnum()
                ) if pan_card_no else None,
                "referred_by": getattr(db_candidate, 'referred_by', None),
            }

            

            for i in range(1, 7):
                candidate_data[f"discussion{i}_date"] = getattr(db_candidate, f"discussion{i}_date", None)
                candidate_data[f"discussion{i}_done_by"] = getattr(db_candidate, f"discussion{i}_done_by", None)
                candidate_data[f"discussion{i}_notes"] = getattr(db_candidate, f"discussion{i}_notes", None)

            result.append(candidate_data)

        print(f"Returning {len(result)} candidates.")
        return {
            "items": result,
            "total": total,
            "page": page,
            "items_per_page": items_per_page
        }

    except Exception as e:
        print(f"Error in get_all_candidates_details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving candidates: {str(e)}"
        )
        
        

        

@router.get("/details", response_model=PaginatedCandidateResponse)
def get_all_candidates_details(
    db: Session = Depends(get_db),
    page: int = 1,
    items_per_page: int = 6,
    search: Optional[str] = None,
    job_filter: Optional[str] = None,
    rating_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    skill_filter: Optional[str] = None,
    ctc_filter: Optional[str] = None,
    experience_filter: Optional[str] = None,
    sort_key: Optional[str] = None,
    sort_order: Optional[str] = "desc"
):
    """
    Get all candidates with specific fields, supporting pagination, filtering, and sorting.
    """
    try:
        # Base query
        query = db.query(Candidate)

        # Apply filters
        if search:
            query = query.filter(
                Candidate.candidate_name.ilike(f"%{search}%") |
                Candidate.email_id.ilike(f"%{search}%#pragma: no cover") |
                Candidate.mobile_no.ilike(f"%{search}%")
            )

        if job_filter:
            query = query.filter(Candidate.current_designation == job_filter)

        if rating_filter:
            query = query.filter(Candidate.rating == rating_filter)

        if status_filter:
            query = query.filter(Candidate.current_status == status_filter)

        if skill_filter:
            query = query.filter(Candidate.skills_set.ilike(f"%{skill_filter}%"))

        if ctc_filter:
            if ctc_filter == "15+":
                query = query.filter(
                    (Candidate.current_fixed_ctc >= 1500000) &
                    (Candidate.current_fixed_ctc.isnot(None))
                )
            else:
                min_ctc, max_ctc = map(int, ctc_filter.split("-"))
                query = query.filter(
                    (Candidate.current_fixed_ctc.between(min_ctc * 100000, max_ctc * 100000)) &
                    (Candidate.current_fixed_ctc.isnot(None))
                )

        if experience_filter:
            if experience_filter == "5+":
                query = query.filter(
                    (func.coalesce(Candidate.years_of_exp, 0) >= 5)
                )
            else:
                min_exp, max_exp = map(int, experience_filter.split("-"))
                query = query.filter(
                    func.coalesce(Candidate.years_of_exp, 0).between(min_exp, max_exp)
                )

        # Apply sorting
        if sort_key:
            if sort_key == "candidate_name":
                query = query.order_by(
                    Candidate.candidate_name.asc() if sort_order == "asc" else Candidate.candidate_name.desc()
                )
            elif sort_key == "status":
                query = query.order_by(
                    Candidate.current_status.asc() if sort_order == "asc" else Candidate.current_status.desc()
                )
            elif sort_key == "current_designation":
                query = query.order_by(
                    Candidate.current_designation.asc() if sort_order == "asc" else Candidate.current_designation.desc()
                )
            elif sort_key == "date_of_resume_received":
                query = query.order_by(
                    Candidate.date_of_resume_received.asc().nullslast() if sort_order == "asc" else Candidate.date_of_resume_received.desc().nullslast()
                )
        else:
            # Default sorting by date_of_resume_received in descending order
            query = query.order_by(Candidate.date_of_resume_received.desc().nullslast())

        # Get total count for pagination
        total = query.count()

        # Apply pagination
        candidates = query.offset((page - 1) * items_per_page).limit(items_per_page).all()

        if not candidates:
            return {
                "items": [],
                "total": total,
                "page": page,
                "items_per_page": items_per_page
            }

        result = []
        for db_candidate in candidates:
            # Normalize current_fixed_ctc
            current_fixed_ctc = getattr(db_candidate, 'current_fixed_ctc', None)
            if current_fixed_ctc is not None:
                # If CTC is likely in lakhs (e.g., < 100000), convert to rupees
                if 0 < current_fixed_ctc < 100000:
                    current_fixed_ctc = current_fixed_ctc * 100000
                # Set invalid CTC (e.g., 0) to None
                if current_fixed_ctc < 1000:
                    current_fixed_ctc = None

            # Normalize skills_set
            skills_set = getattr(db_candidate, 'skills_set', None)
            if skills_set == "[object Object]" or not skills_set:
                skills_set = ""

            # Determine interview progress status
            interview_progress = "Not Started"
            if db_candidate.current_status:
                status_mapping = {
                    "L1 Interview": "L1 Interview",
                    "L2 Interview": "L2 Interview",
                    "HR Round": "HR Round",
                    "Offer Initiated": "Offer Stage",
                    "Onboarded": "Joined",
                    "Rejected": "Rejected",
                    "Offer Declined": "Declined",
                    "SCREENING": "Screening",
                    "CTC_BREAKUP": "CTC Breakup"
                }
                interview_progress = status_mapping.get(db_candidate.current_status, db_candidate.current_status)

            # Determine documents status
            documents_status = "⚠️ Pending"
            if hasattr(db_candidate, 'documents_verified') and db_candidate.documents_verified:
                documents_status = "✅ Submitted"

            # Determine joining status
            joining_status = "Pending"
            if db_candidate.current_status == "Onboarded":
                joining_status = "Onboarded"
            elif db_candidate.current_status == "Offer Declined":
                joining_status = "Declined"

            # Determine offer status
            offer_status = getattr(db_candidate, 'offer_status', "Not Initiated") or "Not Initiated"

            # Format notice period with unit
            notice_period_display = getattr(db_candidate, 'notice_period', None)
            notice_period_unit = getattr(db_candidate, 'notice_period_unit', 'Days')
            if notice_period_display is not None:
                notice_period_display = f"{notice_period_display} {notice_period_unit}"

            # Get candidate rating
            rating = getattr(db_candidate, 'rating', None)
            
            # Get job information
            job_title = None
            associated_job_id = getattr(db_candidate, 'associated_job_id', None)
            if hasattr(db_candidate, 'job') and db_candidate.job:
                job_title = db_candidate.job.job_title

            department = None
            if hasattr(db_candidate, 'department'):
                department = db_candidate.department

                        # Handle PAN card field - ensure it's properly formatted
            pan_card_no = getattr(db_candidate, 'pan_card_no', None)
            if pan_card_no:
                pan_card_no = pan_card_no.upper()  # Ensure PAN card is in uppercase
            
            # Handle rejected_date field and convert to ISO format if exists
            rejected_date = getattr(db_candidate, 'rejected_date', None)
            if rejected_date:
                rejected_date = rejected_date.isoformat()
            
            # Collect candidate data
            candidate_data = {
                "candidate_id": db_candidate.candidate_id,
                "candidate_name": getattr(db_candidate, 'candidate_name', None),
                "email_id": getattr(db_candidate, 'email_id', None),
                "mobile_no": getattr(db_candidate, 'mobile_no', None),
                "linkedin_url": getattr(db_candidate, 'linkedin_url', None),
                "applied_position": job_title,
                "associated_job_id": associated_job_id,
                "status": getattr(db_candidate, 'status', None) or str(db_candidate.current_status),
                "final_status": getattr(db_candidate, 'final_status', None),
                "years_of_exp": getattr(db_candidate, 'years_of_exp', None),
                "current_designation": getattr(db_candidate, 'current_designation', None),
                "current_company": getattr(db_candidate, 'current_company', None),
                "current_fixed_ctc": current_fixed_ctc,
                "current_variable_pay": getattr(db_candidate, 'current_variable_pay', None),
                "expected_fixed_ctc": getattr(db_candidate, 'expected_fixed_ctc', None),
                "expected_ctc": getattr(db_candidate, 'expected_ctc', None),
                "offer_ctc": getattr(db_candidate, 'offer_ctc', None),
                "ctc": getattr(db_candidate, 'ctc', None),
                "current_location": getattr(db_candidate, 'current_location', None),
                "current_address": getattr(db_candidate, 'current_address', None),
                "permanent_address": getattr(db_candidate, 'permanent_address', None),
                "notice_period": notice_period_display,
                "notice_period_unit": notice_period_unit,
                "mode_of_work": getattr(db_candidate, 'mode_of_work', None),
                "work_mode_preference": getattr(db_candidate, 'work_mode_preference', None),
                "reason_for_change": getattr(db_candidate, 'reason_for_change', None),
                "interview_progress_status": interview_progress,
                "offer_status": offer_status,
                "documents_status": documents_status,
                "joining_status": joining_status,
                "rating": rating,
                "department": department,
                "date_of_resume_received": getattr(db_candidate, 'date_of_resume_received', None),
                "application_date": getattr(db_candidate, 'application_date', None),
                "date_of_joining": getattr(db_candidate, 'date_of_joining', None),
                "l1_interview_date": getattr(db_candidate, 'l1_interview_date', None),
                "l1_interviewers_name": getattr(db_candidate, 'l1_interviewers_name', None),
                "l1_status": getattr(db_candidate, 'l1_status', None),
                "l2_interview_date": getattr(db_candidate, 'l2_interview_date', None),
                "l2_interviewers_name": getattr(db_candidate, 'l2_interviewers_name', None),
                "l2_status": getattr(db_candidate, 'l2_status', None),
                "hr_interview_date": getattr(db_candidate, 'hr_interview_date', None),
                "hr_interviewer_name": getattr(db_candidate, 'hr_interviewer_name', None),
                "hr_status": getattr(db_candidate, 'hr_status', None),
                "additional_info": getattr(db_candidate, 'additional_info', None),
                "resume_url": getattr(db_candidate, 'resume_url', None),
                "offered_designation": getattr(db_candidate, 'offered_designation', None),
                "skills_set": skills_set,
                "gender": getattr(db_candidate, 'gender', None),
                "pan_card_no": pan_card_no,
                "rejected_date": rejected_date,
                # Add helper fields for frontend convenience
                "is_rejected": rejected_date is not None,
                "pan_card_valid": bool(
                    pan_card_no and 
                    len(pan_card_no) == 10 and
                    pan_card_no.isalnum()
                ) if pan_card_no else None,
                "referred_by": getattr(db_candidate, 'referred_by', None),
            }

            # Discussion 1-6 fields
            for i in range(1, 7):
                candidate_data[f"discussion{i}_date"] = getattr(db_candidate, f"discussion{i}_date", None)
                candidate_data[f"discussion{i}_done_by"] = getattr(db_candidate, f"discussion{i}_done_by", None)
                candidate_data[f"discussion{i}_notes"] = getattr(db_candidate, f"discussion{i}_notes", None)

            result.append(candidate_data)

        return {
            "items": result,
            "total": total,
            "page": page,
            "items_per_page": items_per_page
        }
        
    except Exception as e:
        print(f"Error in get_all_candidates_details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving candidates: {str(e)}"
        )

@router.put("/update-rating/{candidate_id}", response_model=dict)
def update_candidate_rating(
    candidate_id: str,  
    rating_data: dict = Body(..., example={"rating": "Good"}),
    db: Session = Depends(get_db)
):
    """
    Update a candidate's rating.
    """
    try:
        rating = rating_data.get("rating")
        valid_ratings = ["Excellent", "Good", "Average", "Poor"]
        if rating is not None and rating not in valid_ratings:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Rating must be one of: {', '.join(valid_ratings)}"
            )
        
        db_candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
        if not db_candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate with ID {candidate_id} not found"
            )
        
        # Update the rating
        db_candidate.rating = rating
        db.commit()
        
        return {
            "status": "success",
            "message": f"Rating updated for candidate {db_candidate.candidate_name}",
            "candidate_id": candidate_id,
            "rating": rating
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in update_candidate_rating: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating candidate rating: {str(e)}"
        )

@router.get("/basic-info", response_model=List[dict])  
def get_candidates_basic_info(
    limit: int = Query(30, ge=1, le=100, description="Number of candidates to return (max 100)"),
    search: Optional[str] = Query(None, description="Search by candidate name, email, or ID"),
    db: Session = Depends(get_db)
):
    """
    Get basic candidate information: ID, name, department and associated job IDs with pagination and search
    """
    # Start with base query
    query = db.query(Candidate)
    
    # Apply search filter if provided
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Candidate.candidate_name.ilike(search_term),
                Candidate.email_id.ilike(search_term),
                Candidate.candidate_id.ilike(search_term)
            )
        )
    
    # Apply limit and execute query
    candidates = query.limit(limit).all()
    
    # Process each candidate to return only ID, name, department and associated job IDs
    processed_candidates = []
    for candidate in candidates:
        # Handle associated job IDs - split by comma if multiple, return as list
        associated_job_ids = []
        if candidate.associated_job_id:
            # Split by comma and clean up any whitespace
            associated_job_ids = [job_id.strip() for job_id in candidate.associated_job_id.split(',') if job_id.strip()]
        
        basic_info = {
            "id": candidate.candidate_id,
            "name": candidate.candidate_name,
            "department": getattr(candidate, 'department', None),
            "associated_job_ids": associated_job_ids
        }
        processed_candidates.append(basic_info)
        
    return processed_candidates

@router.get("/basic-info/not-applied", response_model=List[dict])  
def get_candidates_basic_info_not_applied(
    limit: int = Query(30, ge=1, le=100, description="Number of candidates to return (max 100)"),
    search: Optional[str] = Query(None, description="Search by candidate name, email, or ID"),
    db: Session = Depends(get_db)
):
    """
    Get basic information for candidates who have not applied for any job
    """
    # Start with base query for candidates who haven't applied for any job
    query = db.query(Candidate).filter(
        or_(
            Candidate.associated_job_id == None,
            Candidate.associated_job_id == "",
            Candidate.associated_job_id.ilike("")
        )
    )
    
    # Apply search filter if provided
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Candidate.candidate_name.ilike(search_term),
                Candidate.email_id.ilike(search_term),
                Candidate.candidate_id.ilike(search_term)
            )
        )
    
    # Apply limit and execute query
    candidates = query.limit(limit).all()
    
    # Process each candidate to return only ID, name, and department
    processed_candidates = []
    for candidate in candidates:
        basic_info = {
            "id": candidate.candidate_id,
            "name": candidate.candidate_name,
            "department": getattr(candidate, 'department', None)
        }
        processed_candidates.append(basic_info)
        
    return processed_candidates

# New endpoint to fetch candidate ID by email - Ultra-optimized version
@router.get("/by-email", response_model=dict)
def get_user_access_by_email(email: str = Query(..., description="User email to search"), db: Session = Depends(get_db)):
    """Get user access data by email with ultra-optimized single query"""
    from app.models import User, UserRoleAccess
    from sqlalchemy import func, or_
    
    # Normalize email for consistent lookups
    email_lower = email.lower().strip()
    
    # Ultra-optimized single query with LEFT JOIN and minimal field selection
    result = db.query(
        User.id.label('user_id'),
        User.name.label('user_name'),
        User.department.label('user_department'),
        UserRoleAccess.id.label('access_id'),
        UserRoleAccess.role_template_id,
        UserRoleAccess.role_name,
        UserRoleAccess.is_super_admin,
        UserRoleAccess.duration_days,
        UserRoleAccess.duration_months,
        UserRoleAccess.duration_years,
        UserRoleAccess.expiry_date,
        UserRoleAccess.page_access,
        UserRoleAccess.subpage_access,
        UserRoleAccess.section_access,
        UserRoleAccess.allowed_job_ids,
        UserRoleAccess.allowed_department_ids,
        UserRoleAccess.allowed_candidate_ids,
        UserRoleAccess.is_unrestricted,
        UserRoleAccess.created_at,
        UserRoleAccess.updated_at,
        UserRoleAccess.created_by,
        UserRoleAccess.updated_by
    ).outerjoin(
        UserRoleAccess, 
        or_(
            func.lower(UserRoleAccess.email) == email_lower,
            UserRoleAccess.user_id == User.id
        )
    ).filter(
        func.lower(User.email) == email_lower
    ).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Determine user type (l1, l2, hr) based on team membership
    user_type = None
    try:
        from app.models import InterviewTeam, SecondInterviewTeam, HRTeam
        email_key = email_lower

        teams1 = db.query(InterviewTeam).all()
        in_l1 = any(
            (member_email or "").strip().lower() == email_key
            for team in teams1
            for member_email in (team.team_emails or [])
        )

        teams2 = db.query(SecondInterviewTeam).all()
        in_l2 = any(
            (member_email or "").strip().lower() == email_key
            for team in teams2
            for member_email in (team.team_emails or [])
        )

        hrteams = db.query(HRTeam).all()
        in_hr = any(
            (member_email or "").strip().lower() == email_key
            for team in hrteams
            for member_email in (team.team_emails or [])
        )

        if in_hr:
            user_type = "hr"
        elif in_l2:
            user_type = "l2"
        elif in_l1:
            user_type = "l1"
    except Exception:
        # If any error occurs in role detection, leave user_type as None
        user_type = None

    # Return optimized response with null safety
    return {
        "user_id": result.user_id,
        "user_name": result.user_name,
        "user_department": result.user_department,
        "role_template_id": result.role_template_id,
        "role_name": result.role_name,
        "is_super_admin": bool(result.is_super_admin) if result.is_super_admin is not None else False,
        "duration_days": result.duration_days,
        "duration_months": result.duration_months,
        "duration_years": result.duration_years,
        "expiry_date": result.expiry_date,
        "page_access": result.page_access,
        "subpage_access": result.subpage_access,
        "section_access": result.section_access,
        "allowed_job_ids": result.allowed_job_ids,
        "allowed_department_ids": result.allowed_department_ids,
        "allowed_candidate_ids": result.allowed_candidate_ids,
        "is_unrestricted": bool(result.is_unrestricted) if result.is_unrestricted is not None else False,
        "id": result.access_id,
        "created_at": result.created_at,
        "updated_at": result.updated_at,
        "created_by": result.created_by,
        "updated_by": result.updated_by,
        # Additional fields appended at the end (does not alter existing fields)
        "user_type": user_type
    }

@router.post("/check-contact-exists", response_model=dict)
def check_contact_exists(
    contact_data: dict = Body(..., example={"email": "user@example.com", "phone": "1234567890"}),
    db: Session = Depends(get_db)
):
    """
    Check if an email or phone number has already been used to apply.
    Highly optimized endpoint that uses exists() query for minimal database load.
    
    Request body: {"email": "user@example.com", "phone": "1234567890"} (both optional)
    Response: {"emailHasApplied": true/false, "phoneHasApplied": true/false}
    """
    try:
        # Extract email and phone from request body
        email = contact_data.get("email")
        phone = contact_data.get("phone")
        
        # At least one contact method should be provided
        if not email and not phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one of email or phone is required"
            )
        
        response = {}
        
        # Check email if provided
        if email:
            if not isinstance(email, str):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email must be a string"
                )
            
            # Trim whitespace and convert to lowercase for consistent checking
            email = email.strip().lower()
            
            # Basic email format validation (simple check)
            if not email or "@" not in email or len(email) < 5:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid email format"
                )
            
            # Highly optimized exists() query for email
            email_exists = db.query(
                db.query(Candidate).filter(
                    func.lower(Candidate.email_id) == email
                ).exists()
            ).scalar()
            
            response["emailHasApplied"] = bool(email_exists)
        
        # Check phone if provided
        if phone:
            if not isinstance(phone, str):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Phone must be a string"
                )
            
            # Trim whitespace and remove common phone formatting
            phone = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "").replace("+", "")
            
            # Basic phone validation (simple check)
            if not phone or len(phone) < 10:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid phone format"
                )
            
            # Highly optimized exists() query for phone
            phone_exists = db.query(
                db.query(Candidate).filter(
                    func.replace(
                        func.replace(
                            func.replace(
                                func.replace(
                                    func.replace(Candidate.mobile_no, " ", ""), 
                                    "-", ""
                                ), 
                                "(", ""
                            ), 
                            ")", ""
                        ), 
                        "+", ""
                    ) == phone
                ).exists()
            ).scalar()
            
            response["phoneHasApplied"] = bool(phone_exists)
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Log unexpected errors but don't expose internal details
        print(f"Error checking contact existence: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while checking contact information"
        )

@router.post("/check-contact-exists/bulk", response_model=dict)
def check_contact_exists_bulk(
    contact_data_list: List[dict] = Body(..., example=[
        {"email": "user1@example.com", "phone": "1234567890"},
        {"email": "user2@example.com", "phone": "0987654321"}
    ]),
    db: Session = Depends(get_db)
):
    """
    Bulk check if emails or phone numbers have already been used to apply.
    Highly optimized endpoint that processes multiple contact checks in a single request.
    
    Request body: [{"email": "user@example.com", "phone": "1234567890"}, ...] (both optional per item)
    Response: {"results": [{"emailHasApplied": true/false, "phoneHasApplied": true/false}, ...]}
    """
    try:
        # Validate input
        if not contact_data_list or not isinstance(contact_data_list, list):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Request body must be a non-empty array of contact objects"
            )
        
        if len(contact_data_list) > 100:  # Reasonable limit for bulk operations
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 100 contact checks allowed per request"
            )
        
        results = []
        
        # Process each contact data item
        for i, contact_data in enumerate(contact_data_list):
            try:
                # Extract email and phone from current item
                email = contact_data.get("email")
                phone = contact_data.get("phone")
                
                # At least one contact method should be provided
                if not email and not phone:
                    results.append({
                        "error": f"Item {i+1}: At least one of email or phone is required"
                    })
                    continue
                
                response = {}
                
                # Check email if provided
                if email:
                    if not isinstance(email, str):
                        results.append({
                            "error": f"Item {i+1}: Email must be a string"
                        })
                        continue
                    
                    # Trim whitespace and convert to lowercase for consistent checking
                    email = email.strip().lower()
                    
                    # Basic email format validation (simple check)
                    if not email or "@" not in email or len(email) < 5:
                        results.append({
                            "error": f"Item {i+1}: Invalid email format"
                        })
                        continue
                    
                    # Highly optimized exists() query for email
                    email_exists = db.query(
                        db.query(Candidate).filter(
                            func.lower(Candidate.email_id) == email
                        ).exists()
                    ).scalar()
                    
                    response["emailHasApplied"] = bool(email_exists)
                
                # Check phone if provided
                if phone:
                    if not isinstance(phone, str):
                        results.append({
                            "error": f"Item {i+1}: Phone must be a string"
                        })
                        continue
                    
                    # Trim whitespace and remove common phone formatting
                    phone = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "").replace("+", "")
                    
                    # Basic phone validation (simple check)
                    if not phone or len(phone) < 10:
                        results.append({
                            "error": f"Item {i+1}: Invalid phone format"
                        })
                        continue
                    
                    # Highly optimized exists() query for phone
                    phone_exists = db.query(
                        db.query(Candidate).filter(
                            func.replace(
                                func.replace(
                                    func.replace(
                                        func.replace(
                                            func.replace(Candidate.mobile_no, " ", ""), 
                                            "-", ""
                                        ), 
                                        "(", ""
                                    ), 
                                    ")", ""
                                ), 
                                "+", ""
                            ) == phone
                        ).exists()
                    ).scalar()
                    
                    response["phoneHasApplied"] = bool(phone_exists)
                
                results.append(response)
                
            except Exception as e:
                # Handle individual item errors without failing the entire request
                results.append({
                    "error": f"Item {i+1}: {str(e)}"
                })
                continue
        
        return {"results": results}
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Log unexpected errors but don't expose internal details
        print(f"Error checking bulk contact existence: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while checking bulk contact information"
        )

# ===== USER ROLE ACCESS ROUTES =====
# These routes must be placed BEFORE the dynamic /{candidate_id} route to avoid conflicts

@router.get("/user-role-access", response_model=PaginatedUserRoleAccess)
async def get_all_user_role_access(
    filters: UserRoleAccessFilter = Depends(),
    db: Session = Depends(get_db)
):
    """Get all user role access with pagination and filtering - Optimized version"""
    
    # Start with base query - always join with User for consistent performance
    query = db.query(models.UserRoleAccess).join(
        models.User, models.UserRoleAccess.user_id == models.User.id
    )
    
    # Apply filters
    if filters.search:
        search_term = f"%{filters.search}%"
        query = query.filter(
            or_(
                models.UserRoleAccess.role_name.ilike(search_term),
                models.User.name.ilike(search_term),
                models.User.email.ilike(search_term)
            )
        )
    
    if filters.is_super_admin is not None:
        query = query.filter(models.UserRoleAccess.is_super_admin == filters.is_super_admin)
    
    if filters.role_template_id:
        query = query.filter(models.UserRoleAccess.role_template_id == filters.role_template_id)
    
    if filters.user_id:
        query = query.filter(models.UserRoleAccess.user_id == filters.user_id)
    
    # Optimize count query by using subquery
    count_query = query.subquery()
    total = db.query(count_query).count()
    
    # Apply pagination with optimized ordering
    offset = (filters.page - 1) * filters.items_per_page
    user_role_access_list = query.order_by(
        models.UserRoleAccess.created_at.desc()
    ).offset(offset).limit(filters.items_per_page).all()
    
    return {
        "items": user_role_access_list,
        "total": total,
        "page": filters.page,
        "items_per_page": filters.items_per_page
    }

@router.get("/{candidate_id}", response_model=CandidateResponse)
def read_candidate(candidate_id: str, db: Session = Depends(get_db)):
    db_candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    if db_candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    # Convert None to a default datetime if needed
    candidate_data = db_candidate.__dict__
    if candidate_data.get('updated_at') is None:
        candidate_data['updated_at'] = candidate_data.get('created_at') or datetime.now()
    
    return candidate_data

@router.put("/{candidate_id}", response_model=CandidateResponse)
def update_candidate(candidate_id: str, candidate_update: CandidateUpdate, db: Session = Depends(get_db)):
    """Update candidate information"""
    db_candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    if db_candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    update_data = candidate_update.dict(exclude_unset=True)

    if "skills_set" in update_data and update_data["skills_set"] is not None:
        update_data["skills_set"] = ", ".join(update_data["skills_set"])

    for key, value in update_data.items():
        setattr(db_candidate, key, value)

    db.commit()
    db.refresh(db_candidate)
    return db_candidate
    
@router.patch("/{candidate_id}/rating")
def update_candidate_rating(candidate_id: str, rating_update: CandidateRatingUpdate, db: Session = Depends(get_db)):
    db_candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    if db_candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    db_candidate.rating = rating_update.rating
    db_candidate.updated_by = rating_update.updated_by or "taadmin"
    db_candidate.updated_at = datetime.utcnow()  # Set updated_at to current timestamp
    db.commit()
    db.refresh(db_candidate)
    return {"message": f"Rating updated for candidate {candidate_id}"}

@router.put("/{candidate_id}/status")
def update_candidate_status(candidate_id: str, status_update: StatusUpdate, db: Session = Depends(get_db)):
    """Update candidate status"""
    db_candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    if db_candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    db_candidate.status = status_update.status
    db.commit()
    db.refresh(db_candidate)
    return {"message": f"Status updated for candidate {candidate_id} to {status_update.status}"}

class FinalStatusUpdate(BaseModel):
    final_status: str

@router.put("/{candidate_id}/final-status")
def update_candidate_final_status(candidate_id: str, final_status_update: FinalStatusUpdate, db: Session = Depends(get_db)):
    """Update candidate final status"""
    logger.info(f"Received request to update final_status for candidate {candidate_id} to {final_status_update.final_status}")

    # Validate final_status against the database
    allowed_statuses_from_db = [status.status for status in db.query(models.FinalStatusDB).all()]
    if final_status_update.final_status not in allowed_statuses_from_db:
        logger.error(f"Invalid final_status: {final_status_update.final_status}. Allowed values from DB: {allowed_statuses_from_db}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid final_status. Must be one of {allowed_statuses_from_db}"
        )

    db_candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    if db_candidate is None:
        logger.error(f"Candidate {candidate_id} not found")
        raise HTTPException(status_code=404, detail="Candidate not found")
   
    # Update the final status
    try:
        db_candidate.final_status = final_status_update.final_status
        db_candidate.updated_at = date.today()

    # Handle rejected_date based on final_status
        if final_status_update.final_status == "Rejected":
            db_candidate.rejected_date = date.today()
            logger.info(f"Set rejected_date to {date.today()} for candidate {candidate_id}")
        else:
            db_candidate.rejected_date = None
            logger.info(f"Cleared rejected_date for candidate {candidate_id}")

        db.commit()
        db.refresh(db_candidate)
        logger.info(f"Successfully updated final_status for candidate {candidate_id} to {db_candidate.final_status}")
    except Exception as e:
        logger.error(f"Failed to update final_status for candidate {candidate_id}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update final_status: {str(e)}")

    return {
        "message": f"Final status updated for candidate {candidate_id} to {final_status_update.final_status}",
        "candidate_id": candidate_id,
        "final_status": db_candidate.final_status
    }

@router.get("/by-final-status/{final_status}")
def get_candidates_by_final_status(final_status: str, db: Session = Depends(get_db)):
    """Get candidates by final status"""
    candidates = db.query(Candidate).filter(Candidate.final_status == final_status).all()
    
    if not candidates:
        return {"candidates": [], "count": 0}
    
    result = []
    for candidate in candidates:
        result.append({
            "candidate_id": candidate.candidate_id,
            "candidate_name": getattr(candidate, 'candidate_name', None),
            "email_id": getattr(candidate, 'email_id', None),
            "status": getattr(candidate, 'status', None),
            "final_status": getattr(candidate, 'final_status', None),
            "l1_status": getattr(candidate, 'l1_status', None),
            "l2_status": getattr(candidate, 'l2_status', None),
            "hr_status": getattr(candidate, 'hr_status', None),
            "expected_ctc": getattr(candidate, 'expected_ctc', None),
            "final_offer_ctc": getattr(candidate, 'final_offer_ctc', None),
            "date_of_joining": getattr(candidate, 'date_of_joining', None),
            "offer_status": getattr(candidate, 'offer_status', None),
            "resume_url": getattr(candidate, 'resume_url', None),
            "linkedin_url": getattr(candidate, 'linkedin_url', None),
            "ta_team": getattr(candidate, 'ta_team', None),
            "ta_comments": getattr(candidate, 'ta_comments', None),
            "rating": getattr(candidate, 'rating', None),
            "application_date": getattr(candidate, 'application_date', None),
            "created_by": getattr(candidate, 'created_by', "taadmin"),
            "updated_by": getattr(candidate, 'updated_by', "taadmin"),
            "created_at": getattr(candidate, 'created_at', None),
            "updated_at": getattr(candidate, 'updated_at', None),
            "department":getattr(candidate, 'department', None),
            "gender" : getattr(candidate, 'gender', None),
            "rejected_date": getattr(candidate, 'rejected_date', None),
          
            ###If we need we can add remaining filed also
        })
    
    return {"candidates": result, "count": len(result)}

@router.put("/{candidate_id}/progress")
def update_candidate_progress(candidate_id: str, progress_update: ProgressUpdate, db: Session = Depends(get_db)):
    """Update candidate progress status"""
    db_candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    if db_candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    # Store the status as-is without converting to enum format
    db_candidate.current_status = progress_update.new_status
    db_candidate.status_updated_on = date.today()
    
    # Add progress entry with the original status value
    progress_entry = CandidateProgress(candidate_id=candidate_id, status=progress_update.new_status)
    db.add(progress_entry)
    db.commit()
    db.refresh(db_candidate)
    
    return {"message": f"Progress updated for candidate {candidate_id} to {progress_update.new_status}"}
########################### Interview levels ######################

@router.put("/{candidate_id}/interview/{level}")
def update_candidate_interview(candidate_id: str, level: str, interview_data: InterviewUpdate, db: Session = Depends(get_db)):
    """Update candidate interview information for a specific level (L1, L2, HR)"""
    db_candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    if db_candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    try:
        level = level.lower()
        update_successful = False
        
        if level == "l1":
            # Update L1 interview fields
            if interview_data.interview_date is not None:
                db_candidate.l1_interview_date = interview_data.interview_date
                update_successful = True
                
            if interview_data.interviewer_name is not None:
                db_candidate.l1_interviewers_name = interview_data.interviewer_name
                update_successful = True
                
            if interview_data.status is not None:
                db_candidate.l1_status = interview_data.status
                update_successful = True
                
            if interview_data.feedback is not None:
                db_candidate.l1_feedback = interview_data.feedback
                update_successful = True
                
        elif level == "l2":
            # Update L2 interview fields
            if interview_data.interview_date is not None:
                db_candidate.l2_interview_date = interview_data.interview_date
                update_successful = True
                
            if interview_data.interviewer_name is not None:
                db_candidate.l2_interviewers_name = interview_data.interviewer_name
                update_successful = True
                
            if interview_data.status is not None:
                db_candidate.l2_status = interview_data.status
                update_successful = True
                
            if interview_data.feedback is not None:
                db_candidate.l2_feedback = interview_data.feedback
                update_successful = True
                
        elif level == "hr":
            # Update HR interview fields
            if interview_data.interview_date is not None:
                db_candidate.hr_interview_date = interview_data.interview_date
                update_successful = True
                
            if interview_data.interviewer_name is not None:
                db_candidate.hr_interviewer_name = interview_data.interviewer_name
                update_successful = True
                
            if interview_data.status is not None:
                db_candidate.hr_status = interview_data.status
                update_successful = True
                
            if interview_data.feedback is not None:
                db_candidate.hr_feedback = interview_data.feedback
                update_successful = True
            
            if interview_data.final_offer_ctc is not None:
                db_candidate.final_offer_ctc = interview_data.final_offer_ctc
                update_successful = True    
                
        else:
            raise HTTPException(status_code=400, detail="Invalid interview level. Must be 'l1', 'l2', or 'hr'")

        if update_successful:
            # Update candidate progress if status changed
            if interview_data.status is not None:
                # Add a new progress entry
                progress_status = f"{level.upper()} Interview: {interview_data.status}"
                db_progress = CandidateProgress(
                    candidate_id=candidate_id, 
                    status=progress_status,
                    timestamp=date.today(),
                   
                )
                db.add(db_progress)
                
                # Update current status based on the interview level and result
            if interview_data.status.lower() in ["pass", "passed", "accepted", "success", "successful"]:
                if level == "l1":
                    db_candidate.current_status = "L2 Interview"
                elif level == "l2":
                    db_candidate.current_status = "HR Round"
                elif level == "hr":
                    db_candidate.current_status = "Offer Initiated"
            elif interview_data.status.lower() in ["fail", "failed", "rejected", "reject"]:
                db_candidate.current_status = "Rejected"

                db_candidate.status_updated_on = date.today()
                
            db_candidate.updated_by = interview_data.updated_by
            db_candidate.updated_at = interview_data.updated_at    

            db.commit()
            db.refresh(db_candidate)
            
            # Create response data
            response_data = {
                "message": f"{level.upper()} interview updated for candidate {candidate_id}",
                "updated_fields": []
            }
            
            if interview_data.interview_date is not None:
                response_data["updated_fields"].append("interview_date")
            if interview_data.interviewer_name is not None:
                response_data["updated_fields"].append("interviewer_name")
            if interview_data.status is not None:
                response_data["updated_fields"].append("status")
            if interview_data.feedback is not None:
                response_data["updated_fields"].append("feedback")
                
            return response_data
        else:
            return {"message": "No fields were updated"}
            
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating interview: {str(e)}")

##################### Offer ###################

@router.put("/{candidate_id}/offer", response_model=CandidateResponse)
def update_candidate_offer(candidate_id: str, offer_details: OfferDetailsUpdate, db: Session = Depends(get_db)):
    """Update candidate offer details"""
    db_candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    if not db_candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    update_data = offer_details.dict(exclude_unset=True)
    allowed_offer_statuses = ["Not Initiated", "Pending", "Sent", "Accepted", "Declined"]
    
    # Validate offer_status
    if "offer_status" in update_data and update_data["offer_status"]:
        status_value = update_data["offer_status"].strip().capitalize()
        if status_value not in allowed_offer_statuses:
            raise HTTPException(status_code=400, detail="Invalid offer status")
        update_data["offer_status"] = status_value
        
        # Sync current_status and final_status
        if status_value == "Accepted":
            update_data["current_status"] = "OFFER_ACCEPTED"
            update_data["final_status"] = "offer_accepted"
            
            # Update offer_letter_status
            offer_letter = db.query(OfferLetterStatus).filter(OfferLetterStatus.candidate_id == candidate_id).first()
            if offer_letter:
                offer_letter.offer_letter_status = "Offer Accepted"
                offer_letter.updated_by = "taadmin"  # Add updated_by
                offer_letter.updated_at = datetime.now()
            else:
                new_offer_letter = OfferLetterStatus(
                    candidate_id=candidate_id,
                    offer_letter_status="Offer Accepted",
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    created_by=offer_details.created_by or "taadmin",  # Use frontend or fallback
                    updated_by="taadmin"   # Add updated_by
                )
                db.add(new_offer_letter)
                
        elif status_value == "Declined":
            update_data["current_status"] = "DECLINED"
            update_data["final_status"] = "rejected"
    
    # Add audit fields to update data
    update_data["updated_by"] = "taadmin"
    update_data["updated_at"] = datetime.now()
    
    # Set created_by if this is a new record (though unlikely in an update)
    if not hasattr(db_candidate, 'created_by') or db_candidate.created_by is None:
        update_data["created_by"] = "taadmin"
        update_data["created_at"] = datetime.now()
    
    # Update candidate fields
    for key, value in update_data.items():
        setattr(db_candidate, key, value)
    
    db.commit()
    db.refresh(db_candidate)
    return db_candidate





@router.post("/offer_letter_status/{candidate_id}", response_model=OfferLetterStatusResponse)
def create_or_update_offer_letter_status(
    candidate_id: str,
    status_data: OfferLetterStatusCreate,
    db: Session = Depends(get_db)
):
    """Create or update offer letter status"""
    db_candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    if not db_candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    db_offer_letter = db.query(OfferLetterStatus).filter(OfferLetterStatus.candidate_id == candidate_id).first()
    if db_offer_letter:
        db_offer_letter.offer_letter_status = status_data.offer_letter_status
        db_offer_letter.updated_at = date.today()
        db_offer_letter.updated_by = status_data.created_by or "taadmin"  # Add updated_by field
    else:
        db_offer_letter = OfferLetterStatus(
            candidate_id=candidate_id,
            offer_letter_status=status_data.offer_letter_status,
            created_at=date.today(),
            updated_at=date.today(),
            created_by=status_data.created_by or "taadmin",  # Add created_by field
            
        )
        db.add(db_offer_letter)

    # Update candidate statuses
    if status_data.offer_letter_status == "Offered":
        db_candidate.current_status = "OFFER_INITIATED"
        db_candidate.final_status = "offered"
        db_candidate.offer_status = "Sent"

    db.commit()
    db.refresh(db_offer_letter)
    db.refresh(db_candidate)
    return db_offer_letter



@router.put("/{candidate_id}/reject-offer", response_model=CandidateResponse)
def reject_candidate_offer(candidate_id: str, rejection_data: RejectOfferRequest = None, db: Session = Depends(get_db)):
    """Reject the offer for a candidate."""
    db_candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    if not db_candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    current_offer_status = db_candidate.offer_status or "Not Initiated"
    allowed_statuses = ["Sent", "Pending", "Not Initiated"]

    if current_offer_status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reject offer. Current offer status is {current_offer_status}"
        )

    db_candidate.offer_status = "Declined"
    db_candidate.current_status = "DECLINED"
    db_candidate.final_status = "rejected"
    db_candidate.offer_accepted_rejected_date = date.today()

    # Update offer_letter_status
    offer_letter = db.query(OfferLetterStatus).filter(OfferLetterStatus.candidate_id == candidate_id).first()
    if offer_letter:
        offer_letter.offer_letter_status = "Declined"
        offer_letter.updated_at = date.today()
        offer_letter.updated_by = "taadmin"  # Add updated_by field
    else:
        new_offer_letter = OfferLetterStatus(
            candidate_id=candidate_id,
            offer_letter_status="Declined",
            created_at=date.today(),
            updated_at=date.today(),
            created_by="taadmin",  # Add created_by field
           
        )
        db.add(new_offer_letter)

    if rejection_data and rejection_data.rejection_reason:
        db_candidate.rejection_reason = rejection_data.rejection_reason

    db.commit()
    db.refresh(db_candidate)
    return db_candidate


@router.get("/offer_letter_status/{candidate_id}", response_model=OfferLetterStatusResponse)
def get_offer_letter_status(candidate_id: str, db: Session = Depends(get_db)):
    """Fetch offer letter status for a candidate"""
    db_offer_letter = db.query(OfferLetterStatus).filter(OfferLetterStatus.candidate_id == candidate_id).first()
    if not db_offer_letter:
        raise HTTPException(status_code=404, detail="Offer letter status not found")
    return db_offer_letter

####################### Discussions ##############################

@router.put("/discussions/{candidate_id}", response_model=CandidateDiscussionResponse)
def update_discussions(
    candidate_id: str, 
    payload: DiscussionSavePayload, 
    db: Session = Depends(get_db)
):
    """Update candidate discussions"""
    try:
        discussions_data = payload.discussions

        logger.debug(f"Updating discussions for candidate {candidate_id}")
        logger.debug(f"Discussion data: {discussions_data}")

        # Check if candidate exists
        db_candidate = db.query(Candidate).filter(
            Candidate.candidate_id == candidate_id
        ).first()
        if not db_candidate:
            logger.error(f"Candidate {candidate_id} not found")
            raise HTTPException(status_code=404, detail="Candidate not found")

        for level, discussion_create in discussions_data.items():
            try:
                level_int = int(level)
                db_discussion = db.query(Discussion).filter(
                    Discussion.candidate_id == candidate_id,
                    Discussion.level == level_int
                ).first()

                discussion_data = discussion_create.model_dump(exclude_unset=True)
                
                # Remove notes if present (handled separately)
                if 'notes' in discussion_data:
                    del discussion_data['notes']
                
                # Set updated_at from frontend
                if 'updated_at' not in discussion_data:
                    raise HTTPException(
                        status_code=422,
                        detail="updated_at is required in payload"
                    )
                
                # Set updated_by from frontend
                if 'updated_by' not in discussion_data:
                    raise HTTPException(
                        status_code=422,
                        detail="updated_by is required in payload"
                    )

                if db_discussion:
                    # Update existing discussion
                    for key, value in discussion_data.items():
                        setattr(db_discussion, key, value)
                else:
                    # Create new discussion with frontend-provided values
                    db_discussion = Discussion(
                        candidate_id=candidate_id,
                        level=level_int,
                        **discussion_data
                    )
                    db.add(db_discussion)

                # Also update the candidate's audit fields
                db_candidate.updated_by = discussion_data['updated_by']
                db_candidate.updated_at = discussion_data['updated_at']

                # Mirror fields into candidates table for backward-compatible GET
                if 'done_by' in discussion_data:
                    setattr(db_candidate, f"discussion{level_int}_done_by", discussion_data['done_by'])
                if 'feedback' in discussion_data:
                    setattr(db_candidate, f"discussion{level_int}_notes", discussion_data['feedback'])
                if 'decision' in discussion_data:
                    setattr(db_candidate, f"discussion{level_int}_status", discussion_data['decision'])
                # Set per-round date using updated_at if provided
                round_dt = discussion_data.get('updated_at')
                if round_dt:
                    try:
                        setattr(db_candidate, f"discussion{level_int}_date", round_dt.date())
                    except Exception:
                        setattr(db_candidate, f"discussion{level_int}_date", None)

            except ValueError as ve:
                logger.error(f"Invalid level format: {level}. Error: {str(ve)}")
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid level format: {level}"
                )
            except Exception as e:
                logger.error(f"Error processing discussion level {level}: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Error processing discussion level {level}: {str(e)}"
                )

        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Database commit failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update discussions: {str(e)}"
            )

        # Prepare response
        updated_discussions = db.query(Discussion).filter(
            Discussion.candidate_id == candidate_id
        ).all()

        response_discussions = {}
        for discussion in updated_discussions:
            # Transform questions
            questions_dict = {}
            for question in discussion.questions:
                questions_dict[question.round_name] = DiscussionQuestionResponse.model_validate(question)

            # Create response object
            discussion_dict = {
                "id": discussion.id,
                "candidate_id": discussion.candidate_id,
                "level": discussion.level,
                "decision": discussion.decision,
                "feedback": discussion.feedback,
                "done_by": discussion.done_by,
                "created_at": discussion.created_at,
                "updated_at": discussion.updated_at,
                "updated_by": discussion.updated_by,
            }
            
            discussion_response = DiscussionResponse.model_validate(discussion_dict)
            discussion_response.questions = questions_dict
            response_discussions[str(discussion.level)] = discussion_response

        return CandidateDiscussionResponse(
            candidateId=candidate_id,
            discussions=response_discussions
        )

    except ValidationError as ve:
        logger.error(f"Validation error: {str(ve)}")
        raise HTTPException(
            status_code=422,
            detail=str(ve)
        )
    except Exception as e:
        logger.error(f"Unexpected error in update_discussions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
# NEW ROUTES FOR DISCUSSION QUESTIONS


# Individual round routes for writing questions

@router.post("/discussions/questions/{round_name}", response_model=DiscussionQuestionResponse)
def save_discussion_questions(
    round_name: str, 
    payload: DiscussionQuestionCreate, 
    db: Session = Depends(get_db)
):
    """Save questions for a specific discussion round (D1-D6)"""
    try:
        # Validate round name
        valid_rounds = ['D1', 'D2', 'D3', 'D4', 'D5', 'D6']
        if round_name not in valid_rounds:
            raise HTTPException(status_code=400, detail=f"Invalid round name. Must be one of: {valid_rounds}")

        logger.debug(f"Saving questions for round {round_name}")

        # Check if questions already exist for this round
        db_question = db.query(DiscussionQuestion).filter(
            DiscussionQuestion.round_name == round_name
        ).first()

        question_data = payload.model_dump(exclude_unset=True)
        question_data["updated_at"] = datetime.now()

        if db_question:
            # Update existing questions
            for key, value in question_data.items():
                setattr(db_question, key, value)
        else:
            # Create new questions
            db_question = DiscussionQuestion(
                round_name=round_name,
                **question_data
            )
            db.add(db_question)

        db.commit()
        return DiscussionQuestionResponse.model_validate(db_question)

    except Exception as e:
        db.rollback()
        logger.error(f"Error saving questions for round {round_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save questions: {str(e)}")

@router.get("/discussions/questions/{round_name}", response_model=DiscussionQuestionResponse)
def get_discussion_questions(round_name: str, db: Session = Depends(get_db)):
    """Get questions for a specific discussion round (D1-D6)"""
    try:
        # Validate round name
        valid_rounds = ['D1', 'D2', 'D3', 'D4', 'D5', 'D6']
        if round_name not in valid_rounds:
            raise HTTPException(status_code=400, detail=f"Invalid round name. Must be one of: {valid_rounds}")

        logger.debug(f"Getting questions for round {round_name}")

        # Get questions for this round
        db_question = db.query(DiscussionQuestion).filter(
            DiscussionQuestion.round_name == round_name
        ).first()

        if not db_question:
            raise HTTPException(status_code=404, detail=f"Questions not found for round {round_name}")

        return DiscussionQuestionResponse.model_validate(db_question)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting questions for round {round_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get questions: {str(e)}")

@router.put("/discussions/questions/{round_name}", response_model=DiscussionQuestionResponse)
def update_discussion_questions(
    round_name: str, 
    payload: DiscussionQuestionUpdate, 
    db: Session = Depends(get_db)
):
    """Update questions for a specific discussion round (D1-D6)"""
    try:
        # Validate round name
        valid_rounds = ['D1', 'D2', 'D3', 'D4', 'D5', 'D6']
        if round_name not in valid_rounds:
            raise HTTPException(status_code=400, detail=f"Invalid round name. Must be one of: {valid_rounds}")

        logger.debug(f"Updating questions for round {round_name}")

        # Get questions for this round
        db_question = db.query(DiscussionQuestion).filter(
            DiscussionQuestion.round_name == round_name
        ).first()

        if not db_question:
            raise HTTPException(status_code=404, detail=f"Questions not found for round {round_name}")

        # Update questions
        question_data = payload.model_dump(exclude_unset=True)
        question_data["updated_at"] = datetime.now()

        for key, value in question_data.items():
            setattr(db_question, key, value)

        db.commit()
        return DiscussionQuestionResponse.model_validate(db_question)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating questions for round {round_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update questions: {str(e)}")

@router.get("/discussions/questions", response_model=Dict[str, DiscussionQuestionResponse])
def get_all_discussion_questions(db: Session = Depends(get_db)):
    """Get all questions across all discussion rounds"""
    try:
        logger.debug("Getting all questions")

        # Get all discussion questions directly
        questions = db.query(DiscussionQuestion).all()

        result = {}
        for question in questions:
            result[question.round_name] = DiscussionQuestionResponse.model_validate(question)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting all questions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get questions: {str(e)}")

@router.delete("/discussions/questions/{round_name}")
def delete_discussion_questions(round_name: str, db: Session = Depends(get_db)):
    """Delete questions for a specific discussion round (D1-D6)"""
    try:
        # Validate round name
        valid_rounds = ['D1', 'D2', 'D3', 'D4', 'D5', 'D6']
        if round_name not in valid_rounds:
            raise HTTPException(status_code=400, detail=f"Invalid round name. Must be one of: {valid_rounds}")

        logger.debug(f"Deleting questions for round {round_name}")

        # Get and delete questions for this round
        db_question = db.query(DiscussionQuestion).filter(
            DiscussionQuestion.round_name == round_name
        ).first()

        if not db_question:
            raise HTTPException(status_code=404, detail=f"Questions not found for round {round_name}")

        db.delete(db_question)
        db.commit()

        return {"message": f"Questions for round {round_name} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting questions for round {round_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete questions: {str(e)}")

@router.get("/discussions/{candidate_id}", response_model=Dict[str, DiscussionResponse])
def get_discussions(candidate_id: str, db: Session = Depends(get_db)):
    """Get discussions for a candidate from candidates table (backward compatible response)."""
    try:
        logger.debug(f"Getting discussions for candidate {candidate_id}")

        db_candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
        if not db_candidate:
            logger.info(f"Candidate {candidate_id} not found, returning empty dict")
            return {}

        result: Dict[str, DiscussionResponse] = {}
        for level in range(1, 7):
            notes = getattr(db_candidate, f"discussion{level}_notes", None)
            done_by = getattr(db_candidate, f"discussion{level}_done_by", None)
            disc_date = getattr(db_candidate, f"discussion{level}_date", None)
            status_val = getattr(db_candidate, f"discussion{level}_status", None)

            # Only include levels that have any data
            if not any([notes, done_by, disc_date]):
                continue

            discussion_dict = {
                "id": level,  # synthetic id for compatibility
                "candidate_id": db_candidate.candidate_id,
                "level": level,
                "decision": status_val,
                "feedback": notes,
                "done_by": done_by,
                "created_at": disc_date,
                "updated_at": getattr(db_candidate, "updated_at", None),
                "updated_by": getattr(db_candidate, "updated_by", None),
            }

            discussion_response = DiscussionResponse.model_validate(discussion_dict)
            discussion_response.questions = {}
            result[str(level)] = discussion_response

        return result

    except Exception as e:
        logger.error(f"Error getting discussions for candidate {candidate_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get discussions: {str(e)}")
    
@router.post("/discussions/{candidate_id}", response_model=CandidateDiscussionResponse)
def create_discussions(candidate_id: str, payload: DiscussionSavePayload, db: Session = Depends(get_db)):
    """Create or set discussions for a candidate by updating candidates table (backward compatible response)."""
    try:
        discussions_data = payload.discussions

        logger.debug(f"Creating discussions for candidate {candidate_id}")
        logger.debug(f"Discussion data: {discussions_data}")

        db_candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
        if not db_candidate:
            logger.error(f"Candidate {candidate_id} not found")
            raise HTTPException(status_code=404, detail="Candidate not found")

        for level, discussion_create in discussions_data.items():
            try:
                level_int = int(level)
                if not (1 <= level_int <= 6):
                    raise HTTPException(status_code=400, detail=f"Invalid level: {level}. Must be between 1 and 6.")

                discussion_data = discussion_create.model_dump(exclude_unset=True)

                # Map to candidate fields
                if "done_by" in discussion_data:
                    setattr(db_candidate, f"discussion{level_int}_done_by", discussion_data["done_by"])
                if "feedback" in discussion_data:
                    setattr(db_candidate, f"discussion{level_int}_notes", discussion_data["feedback"])
                if "decision" in discussion_data:
                    setattr(db_candidate, f"discussion{level_int}_status", discussion_data["decision"])
                # Save date per round if provided via updated_at
                round_date = discussion_data.get("updated_at")
                if round_date:
                    try:
                        setattr(db_candidate, f"discussion{level_int}_date", round_date.date())
                    except Exception:
                        setattr(db_candidate, f"discussion{level_int}_date", None)

                # Update audit on candidate
                if "updated_by" in discussion_data:
                    db_candidate.updated_by = discussion_data["updated_by"]
                if "updated_at" in discussion_data:
                    db_candidate.updated_at = discussion_data["updated_at"]

            except ValueError as ve:
                logger.error(f"Invalid level format: {level}. Error: {str(ve)}")
                raise HTTPException(status_code=400, detail=f"Invalid level format: {level}")
            except Exception as e:
                logger.error(f"Error processing discussion level {level}: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Error processing discussion level {level}: {str(e)}")

        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Database commit failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to create discussions: {str(e)}")

        # Build response from candidate data
        response_discussions: Dict[str, DiscussionResponse] = {}
        for level in range(1, 7):
            notes = getattr(db_candidate, f"discussion{level}_notes", None)
            done_by = getattr(db_candidate, f"discussion{level}_done_by", None)
            disc_date = getattr(db_candidate, f"discussion{level}_date", None)
            status_val = getattr(db_candidate, f"discussion{level}_status", None)
            if not any([notes, done_by, disc_date]):
                continue
            discussion_dict = {
                "id": level,
                "candidate_id": db_candidate.candidate_id,
                "level": level,
                "decision": status_val,
                "feedback": notes,
                "done_by": done_by,
                "created_at": disc_date,
                "updated_at": getattr(db_candidate, "updated_at", None),
                "updated_by": getattr(db_candidate, "updated_by", None),
            }
            discussion_response = DiscussionResponse.model_validate(discussion_dict)
            discussion_response.questions = {}
            response_discussions[str(level)] = discussion_response

        return CandidateDiscussionResponse(
            candidateId=candidate_id,
            discussions=response_discussions
        )

    except ValidationError as ve:
        logger.error(f"Validation error: {str(ve)}")
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        logger.error(f"Unexpected error in create_discussions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")    

@router.put("/discussions/{candidate_id}", response_model=CandidateDiscussionResponse)
def update_discussions(candidate_id: str, payload: DiscussionSavePayload, db: Session = Depends(get_db)):
    """Update candidate discussions by writing to candidates table (backward compatible response)."""
    try:
        discussions_data = payload.discussions

        logger.debug(f"Updating discussions for candidate {candidate_id}")
        logger.debug(f"Discussion data: {discussions_data}")

        db_candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
        if not db_candidate:
            logger.error(f"Candidate {candidate_id} not found")
            raise HTTPException(status_code=404, detail="Candidate not found")

        for level, discussion_create in discussions_data.items():
            try:
                level_int = int(level)
                if not (1 <= level_int <= 6):
                    raise HTTPException(status_code=400, detail=f"Invalid level: {level}. Must be between 1 and 6.")

                discussion_data = discussion_create.model_dump(exclude_unset=True)
                # Map to candidate fields
                if "done_by" in discussion_data:
                    setattr(db_candidate, f"discussion{level_int}_done_by", discussion_data["done_by"])
                if "feedback" in discussion_data:
                    setattr(db_candidate, f"discussion{level_int}_notes", discussion_data["feedback"])
                if "decision" in discussion_data:
                    setattr(db_candidate, f"discussion{level_int}_status", discussion_data["decision"])
                # Update per-round date from updated_at if provided
                round_date = discussion_data.get("updated_at")
                if round_date:
                    try:
                        setattr(db_candidate, f"discussion{level_int}_date", round_date.date())
                    except Exception:
                        setattr(db_candidate, f"discussion{level_int}_date", None)

                # Update audit on candidate
                if "updated_by" in discussion_data:
                    db_candidate.updated_by = discussion_data["updated_by"]
                if "updated_at" in discussion_data:
                    db_candidate.updated_at = discussion_data["updated_at"]

            except ValueError as ve:
                logger.error(f"Invalid level format: {level}. Error: {str(ve)}")
                raise HTTPException(status_code=400, detail=f"Invalid level format: {level}")
            except Exception as e:
                logger.error(f"Error processing discussion level {level}: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Error processing discussion level {level}: {str(e)}")

        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Database commit failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to update discussions: {str(e)}")

        # Build response from candidate data
        response_discussions: Dict[str, DiscussionResponse] = {}
        for level in range(1, 7):
            notes = getattr(db_candidate, f"discussion{level}_notes", None)
            done_by = getattr(db_candidate, f"discussion{level}_done_by", None)
            disc_date = getattr(db_candidate, f"discussion{level}_date", None)
            status_val = getattr(db_candidate, f"discussion{level}_status", None)
            if not any([notes, done_by, disc_date, status_val]):
                continue
            discussion_dict = {
                "id": level,
                "candidate_id": db_candidate.candidate_id,
                "level": level,
                "decision": status_val,
                "feedback": notes,
                "done_by": done_by,
                "created_at": disc_date,
                "updated_at": getattr(db_candidate, "updated_at", None),
                "updated_by": getattr(db_candidate, "updated_by", None),
            }
            discussion_response = DiscussionResponse.model_validate(discussion_dict)
            discussion_response.questions = {}
            response_discussions[str(level)] = discussion_response

        return CandidateDiscussionResponse(
            candidateId=candidate_id,
            discussions=response_discussions
        )

    except ValidationError as ve:
        logger.error(f"Validation error: {str(ve)}")
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        logger.error(f"Unexpected error in update_discussions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
#################### EXCEL UPLOAD #####################

# Global job tracking system for bulk operations
bulk_jobs = {}
job_lock = threading.Lock()

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class BulkJobResult(BaseModel):
    job_id: str
    status: JobStatus
    created_count: int = 0
    error_count: int = 0
    errors: List[str] = []
    message: str = ""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

def process_bulk_candidates_background(job_id: str, candidates_data: List[dict]):
    """Background task to process bulk candidate creation"""
    try:
        with job_lock:
            bulk_jobs[job_id] = BulkJobResult(
                job_id=job_id,
                status=JobStatus.PROCESSING,
                started_at=datetime.now()
            )
        
        # Get a new database session for background task
        from app.database import SessionLocal
        db = SessionLocal()
        
        try:
            created_candidates = []
            errors = []
            email_map = {}
            mobile_map = {}
            pan_map = {}

            # Pre-validation phase
            for index, candidate_data in enumerate(candidates_data):
                email = candidate_data.get("email_id", "").strip().lower() if candidate_data.get("email_id") else ""
                mobile = re.sub(r'[\s\-\+\(\)]', '', candidate_data.get("mobile_no", ""))[-10:] if candidate_data.get("mobile_no") else ""
                pan_card_no = candidate_data.get("pan_card_no", "").strip().upper() if candidate_data.get("pan_card_no") else ""

                if email:
                    if email in email_map:
                        errors.append(
                            f"Duplicate email {email} found at row {index + 1} (previously at row {email_map[email] + 1})."
                        )
                    else:
                        email_map[email] = index

                if mobile:
                    if mobile in mobile_map:
                        errors.append(
                            f"Duplicate mobile number {mobile} found at row {index + 1} (previously at row {mobile_map[mobile] + 1})."
                        )
                    else:
                        mobile_map[mobile] = index

                if pan_card_no:
                    pan_pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$'
                    if not re.match(pan_pattern, pan_card_no):
                        errors.append(f"Invalid PAN card format at row {index + 1}: {pan_card_no}")

            # If validation errors, update job status
            if errors:
                with job_lock:
                    bulk_jobs[job_id].status = JobStatus.FAILED
                    bulk_jobs[job_id].errors = errors
                    bulk_jobs[job_id].completed_at = datetime.now()
                    bulk_jobs[job_id].message = f"Validation failed with {len(errors)} errors"
                return

            # Process candidates in batches for better performance
            batch_size = 50
            for batch_start in range(0, len(candidates_data), batch_size):
                batch_end = min(batch_start + batch_size, len(candidates_data))
                batch_candidates = candidates_data[batch_start:batch_end]
                
                for index, candidate_data in enumerate(batch_candidates):
                    try:
                        # Check for existing candidate by email
                        existing_candidate = (
                            db.query(Candidate)
                            .filter(Candidate.email_id == candidate_data.get("email_id"))
                            .first()
                        )
                        if existing_candidate:
                            errors.append(
                                f"Candidate at row {batch_start + index + 1}: Email {candidate_data.get('email_id')} already exists in database."
                            )
                            continue

                        # Check for existing candidate by PAN card if provided
                        if candidate_data.get("pan_card_no"):
                            existing_pan = (
                                db.query(Candidate)
                                .filter(Candidate.pan_card_no == candidate_data.get("pan_card_no").strip().upper())
                                .first()
                            )
                            if existing_pan:
                                errors.append(
                                    f"Candidate at row {batch_start + index + 1}: PAN card number {candidate_data.get('pan_card_no')} already exists in database."
                                )
                                continue

                        # Create candidate object with correct field mappings
                        candidate = Candidate(
                            candidate_name=candidate_data.get("candidate_name"),
                            email_id=candidate_data.get("email_id"),
                            mobile_no=candidate_data.get("mobile_no"),
                            pan_card_no=candidate_data.get("pan_card_no", "").strip().upper() if candidate_data.get("pan_card_no") else None,
                            department=candidate_data.get("department"),
                            associated_job_id=candidate_data.get("associated_job_id"),
                            skills_set=candidate_data.get("skills_set"),
                            date_of_resume_received=candidate_data.get("date_of_resume_received"),
                            current_company=candidate_data.get("current_company"),
                            current_designation=candidate_data.get("current_designation"),
                            years_of_exp=candidate_data.get("years_of_experience"),
                            current_status=candidate_data.get("current_status") or "Screening",
                            final_status=candidate_data.get("final_status"),
                            notice_period=candidate_data.get("notice_period"),
                            notice_period_unit=candidate_data.get("notice_period_unit"),
                            npd_info=candidate_data.get("additional_information_npd"),
                            current_fixed_ctc=candidate_data.get("current_fixed_ctc"),
                            current_variable_pay=candidate_data.get("current_variable_pay"),
                            expected_fixed_ctc=candidate_data.get("expected_fixed_ctc"),
                            expected_date_of_joining=candidate_data.get("expected_date_of_joining"),
                            mode_of_work=candidate_data.get("mode_of_work"),
                            reason_for_job_change=candidate_data.get("reason_for_job_change"),
                            ta_team=candidate_data.get("ta_team"),
                            ta_comments=candidate_data.get("ta_comments"),
                            linkedin_url=candidate_data.get("linkedin_url"),
                            l1_interview_date=candidate_data.get("l1_interview_date"),
                            l1_interviewers_name=candidate_data.get("l1_interviewer_name"),
                            l1_status=candidate_data.get("l1_status"),
                            l1_feedback=candidate_data.get("l1_feedback"),
                            l2_interview_date=candidate_data.get("l2_interview_date"),
                            l2_interviewers_name=candidate_data.get("l2_interviewer_name"),
                            l2_status=candidate_data.get("l2_status"),
                            l2_feedback=candidate_data.get("l2_feedback"),
                            hr_interview_date=candidate_data.get("hr_interview_date"),
                            hr_interviewer_name=candidate_data.get("hr_interviewer_name"),
                            hr_status=candidate_data.get("hr_status"),
                            hr_feedback=candidate_data.get("hr_feedback"),
                            final_offer_ctc=candidate_data.get("finalized_ctc"),
                            designation=candidate_data.get("designation"),
                            expected_ctc=candidate_data.get("offered_ctc") if candidate_data.get("offered_ctc") else str(candidate_data.get("finalized_ctc")) if candidate_data.get("finalized_ctc") else None,
                            current_address=candidate_data.get("current_address"),
                            permanent_address=candidate_data.get("permanent_address"),
                            date_of_joining=candidate_data.get("expected_date_of_joining"),
                            current_location=candidate_data.get("current_location"),
                            offer_status=candidate_data.get("offer_status"),
                            discussion1_status=candidate_data.get("discussion1_status"),
                            discussion1_done_by=candidate_data.get("discussion1_done_by"),
                            discussion1_notes=candidate_data.get("discussion1_notes"),
                            discussion1_date=candidate_data.get("discussion1_date"),
                            discussion2_status=candidate_data.get("discussion2_status"),
                            discussion2_done_by=candidate_data.get("discussion2_done_by"),
                            discussion2_notes=candidate_data.get("discussion2_notes"),
                            discussion2_date=candidate_data.get("discussion2_date"),
                            discussion3_status=candidate_data.get("discussion3_status"),
                            discussion3_done_by=candidate_data.get("discussion3_done_by"),
                            discussion3_notes=candidate_data.get("discussion3_notes"),
                            discussion3_date=candidate_data.get("discussion3_date"),
                            discussion4_status=candidate_data.get("discussion4_status"),
                            discussion4_done_by=candidate_data.get("discussion4_done_by"),
                            discussion4_notes=candidate_data.get("discussion4_notes"),
                            discussion4_date=candidate_data.get("discussion4_date"),
                            discussion5_status=candidate_data.get("discussion5_status"),
                            discussion5_done_by=candidate_data.get("discussion5_done_by"),
                            discussion5_notes=candidate_data.get("discussion5_notes"),
                            discussion5_date=candidate_data.get("discussion5_date"),
                            discussion6_status=candidate_data.get("discussion6_status"),
                            discussion6_done_by=candidate_data.get("discussion6_done_by"),
                            discussion6_notes=candidate_data.get("discussion6_notes"),
                            discussion6_date=candidate_data.get("discussion6_date"),
                            application_date=candidate_data.get("application_date"),
                            created_at=datetime.utcnow(),
                            created_by=candidate_data.get("created_by") or "taadmin",
                            updated_by="",
                            updated_at=None,
                            gender=candidate_data.get("gender")
                        )
                        
                        db.add(candidate)
                        db.flush()
                        db.refresh(candidate)
                        
                        # Handle ctc_breakup_status: Update candidate_offer_statuses table
                        if candidate_data.get('ctc_breakup_status'):
                            from app.models import CandidateOfferStatus
                            
                            # Check if offer status already exists for this candidate
                            offer_status = db.query(CandidateOfferStatus).filter_by(candidate_id=candidate.candidate_id).first()
                            
                            if offer_status:
                                # Update existing record
                                offer_status.offer_status = candidate_data.get('ctc_breakup_status')
                                offer_status.updated_by = candidate_data.get('created_by', 'taadmin')
                                offer_status.updated_at = datetime.now(timezone.utc)
                            else:
                                # Create new record
                                offer_status = CandidateOfferStatus(
                                    candidate_id=candidate.candidate_id,
                                    offer_status=candidate_data.get('ctc_breakup_status'),
                                    created_by=candidate_data.get('created_by', 'taadmin'),
                                    updated_by=candidate_data.get('created_by', 'taadmin'),
                                    created_at=datetime.now(timezone.utc),
                                    updated_at=datetime.now(timezone.utc)
                                )
                                db.add(offer_status)
                            
                            db.commit()
                        
                        created_candidates.append(candidate)
                        
                    except Exception as e:
                        errors.append(f"Candidate at row {batch_start + index + 1}: {str(e)}")
                        db.rollback()
                        continue

            # Update job status
            with job_lock:
                bulk_jobs[job_id].status = JobStatus.COMPLETED
                bulk_jobs[job_id].created_count = len(created_candidates)
                bulk_jobs[job_id].error_count = len(errors)
                bulk_jobs[job_id].errors = errors
                bulk_jobs[job_id].completed_at = datetime.now()
                bulk_jobs[job_id].message = f"Successfully created {len(created_candidates)} candidates"
                
        finally:
            db.close()
            
    except Exception as e:
        with job_lock:
            bulk_jobs[job_id].status = JobStatus.FAILED
            bulk_jobs[job_id].completed_at = datetime.now()
            bulk_jobs[job_id].message = f"Background processing failed: {str(e)}"

class JoinTransactionMode(str, Enum):
    BULK_UPLOAD = "bulk_upload"
    SINGLE_CREATE = "single_create"

@router.post("/bulk-create-from-excel", status_code=status.HTTP_202_ACCEPTED)
async def bulk_create_candidates_from_excel(
    candidates: List[CandidateExcelUpload], 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    if not candidates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No candidate data provided.",
        )

    # Generate unique job ID
    job_id = str(uuid.uuid4())
    
    # Convert Pydantic models to dictionaries for background processing
    candidates_data = [candidate.dict() for candidate in candidates]
    
    # Initialize job status
    with job_lock:
        bulk_jobs[job_id] = BulkJobResult(
            job_id=job_id,
            status=JobStatus.PENDING,
            started_at=datetime.now()
        )
    
    # Start background task
    background_tasks.add_task(process_bulk_candidates_background, job_id, candidates_data)
    
    return {
        "message": f"Bulk candidate creation started. Processing {len(candidates)} candidates.",
        "job_id": job_id,
        "status": "pending",
        "check_status_url": f"/candidates/bulk-job-status/{job_id}"
    }

@router.get("/bulk-job-status/{job_id}", response_model=BulkJobResult)
async def get_bulk_job_status(job_id: str):
    """Get the status of a bulk candidate creation job"""
    with job_lock:
        if job_id not in bulk_jobs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        return bulk_jobs[job_id]

####################Candidate single entry ##############################
@router.post("/create-single-entry", status_code=201, response_model=CandidateResponse)
def create_single_candidate_entry(
    candidate_data: CandidateSingleEntry,
    db: Session = Depends(get_db)
):
    """
    Create a single candidate entry with all possible details.
    
    Mandatory fields:
    - candidate_name
    - email_id
    - mobile_no
    - skills_set
    - resume_url (handled separately via resume upload endpoint)
    - current_location
    """
    try:
        # Validate required fields
        if not all([
            candidate_data.candidate_name,
            candidate_data.email_id,
            candidate_data.mobile_no,
            candidate_data.skills_set,
            candidate_data.current_location
        ]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required fields. Name, email, mobile, skills, and current location are mandatory."
            )

        # Validate mobile number format (10 digits)
        if candidate_data.mobile_no and len(candidate_data.mobile_no) != 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mobile number must be exactly 10 digits"
            )
        # Validate PAN card format if provided
        if candidate_data.pan_card_no:
            pan_pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$'
            pan_card_upper = candidate_data.pan_card_no.strip().upper()
            if not re.match(pan_pattern, pan_card_upper):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid PAN card format. Expected format: XXXXX9999X (5 letters, 4 digits, 1 letter)"
                )
 
        # Check if candidate with same email already exists
        existing_candidate_email = db.query(Candidate).filter(
            Candidate.email_id == candidate_data.email_id
        ).first()
        if existing_candidate_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Candidate with email {candidate_data.email_id} already exists"
            )

        # Check if candidate with same mobile number already exists
        existing_candidate_mobile = db.query(Candidate).filter(
            Candidate.mobile_no == candidate_data.mobile_no
        ).first()
        if existing_candidate_mobile:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Candidate with mobile number {candidate_data.mobile_no} already exists"
            )

        # Check if candidate with same PAN card already exists (if PAN is provided)
        if candidate_data.pan_card_no:
            pan_card_upper = candidate_data.pan_card_no.strip().upper()
            existing_candidate_pan = db.query(Candidate).filter(
                Candidate.pan_card_no == pan_card_upper
            ).first()
            if existing_candidate_pan:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Candidate with PAN card number {pan_card_upper} already exists"
                )


       
        # Convert skills list to comma-separated string if it's a list
        if isinstance(candidate_data.skills_set, list):
            skills_str = ", ".join([skill.strip() for skill in candidate_data.skills_set if skill.strip()])
        else:
            skills_str = candidate_data.skills_set

        # Check if associated job exists if provided
        associated_job = None
        if candidate_data.associated_job_id:
            associated_job = db.query(Job).filter(
                Job.job_id == candidate_data.associated_job_id 
            ).first()
            if not associated_job:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Associated job with ID {candidate_data.associated_job_id} not found"
                )

        # Create the candidate record
        db_candidate = Candidate(
            candidate_name=candidate_data.candidate_name,
            email_id=candidate_data.email_id,
            mobile_no=candidate_data.mobile_no,
            pan_card_no=candidate_data.pan_card_no.strip().upper() if candidate_data.pan_card_no else None,
            linkedin_url=candidate_data.linkedin_url,
            associated_job_id=associated_job.job_id if associated_job else None,
            skills_set=skills_str,
            resume_url=candidate_data.resume_url,
            resume_key=candidate_data.resume_key if hasattr(candidate_data, 'resume_key') else None,
            application_date=candidate_data.application_date,
            date_of_resume_received=candidate_data.date_of_resume_received,
            current_status=candidate_data.current_status or "screening",
            final_status=candidate_data.final_status or "in_progress",
            department=candidate_data.department,
            current_company=candidate_data.current_company,
            current_designation=candidate_data.current_designation,
            years_of_exp=candidate_data.years_of_exp,
            notice_period=candidate_data.notice_period,
            notice_period_unit=candidate_data.notice_period_unit or "days",
            npd_info=candidate_data.npd_info,
            current_fixed_ctc=candidate_data.current_fixed_ctc,
            current_variable_pay=candidate_data.current_variable_pay,
            expected_fixed_ctc=candidate_data.expected_fixed_ctc,
            mode_of_work=candidate_data.mode_of_work,
            reason_for_job_change=candidate_data.reason_for_job_change,
            ta_team=candidate_data.ta_team,
            ta_comments=candidate_data.ta_comments,
            current_location=candidate_data.current_location,
            expected_date_of_joining=candidate_data.expected_date_of_joining,
            l1_interview_date=candidate_data.l1_interview_date,
            l1_interviewers_name=candidate_data.l1_interviewers_name,
            l1_status=candidate_data.l1_status,
            l1_feedback=candidate_data.l1_feedback,
            l2_interview_date=candidate_data.l2_interview_date,
            l2_interviewers_name=candidate_data.l2_interviewers_name,
            l2_status=candidate_data.l2_status,
            l2_feedback=candidate_data.l2_feedback,
            hr_interview_date=candidate_data.hr_interview_date,
            hr_interviewer_name=candidate_data.hr_interviewer_name,
            hr_status=candidate_data.hr_status,
            hr_feedback=candidate_data.hr_feedback,
            final_offer_ctc=candidate_data.final_offer_ctc,
            designation=candidate_data.designation,
            ctc=candidate_data.ctc,
            current_address=candidate_data.current_address,
            permanent_address=candidate_data.permanent_address,
            date_of_joining=candidate_data.expected_date_of_joining,
            offer_letter=candidate_data.offer_letter,
            created_by=candidate_data.created_by or "taadmin",
            updated_by=getattr(candidate_data, 'updated_by', None),
            gender =candidate_data.gender,
            updated_at=getattr(candidate_data, 'updated_at', None),
            ctc_breakup_status=candidate_data.ctc_breakup_status,
        )

        db.add(db_candidate)
        db.commit()
        db.refresh(db_candidate)

        # Handle ctc_breakup_status: fast upsert into CandidateOfferStatus.offer_status using ON CONFLICT
        if getattr(candidate_data, 'ctc_breakup_status', None):
            from sqlalchemy.dialects.postgresql import insert
            from app.models import CandidateOfferStatus
            stmt = insert(CandidateOfferStatus).values(
                candidate_id=db_candidate.candidate_id,
                offer_status=candidate_data.ctc_breakup_status,
                created_by=getattr(candidate_data, 'created_by', 'taadmin'),
                updated_by=getattr(candidate_data, 'updated_by', None),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            ).on_conflict_do_update(
                index_elements=['candidate_id'],
                set_={
                    'offer_status': candidate_data.ctc_breakup_status,
                    'updated_by': getattr(candidate_data, 'updated_by', None),
                    'updated_at': datetime.now(timezone.utc)
                }
            )
            db.execute(stmt)
            db.commit()

        # Add CTC breakup status if provided (write to candidate_offer_statuses table)
        if getattr(candidate_data, 'ctc_breakup_status', None):
            from app.models import CandidateOfferStatus
            offer_status = db.query(CandidateOfferStatus).filter_by(candidate_id=db_candidate.candidate_id).first()
            if offer_status:
                offer_status.offer_status = candidate_data.ctc_breakup_status
                offer_status.updated_by = getattr(candidate_data, 'updated_by', 'taadmin')
                offer_status.updated_at = datetime.now(timezone.utc)
            else:
                offer_status = CandidateOfferStatus(
                    candidate_id=db_candidate.candidate_id,
                    offer_status=candidate_data.ctc_breakup_status,
                    created_by=getattr(candidate_data, 'created_by', 'taadmin'),
                    updated_by=getattr(candidate_data, 'updated_by', 'taadmin'),
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                db.add(offer_status)
            db.commit()

        # Add or update CandidateOfferStatus if ctc_offer_status is provided
        if getattr(candidate_data, 'ctc_offer_status', None):
            from app.models import CandidateOfferStatus
            offer_status = db.query(CandidateOfferStatus).filter_by(candidate_id=db_candidate.candidate_id).first()
            if offer_status:
                offer_status.offer_status = candidate_data.ctc_offer_status
                offer_status.updated_by = getattr(candidate_data, 'updated_by', 'taadmin')
            else:
                offer_status = CandidateOfferStatus(
                    candidate_id=db_candidate.candidate_id,
                    offer_status=candidate_data.ctc_offer_status,
                    created_by=getattr(candidate_data, 'created_by', 'taadmin'),
                    updated_by=getattr(candidate_data, 'updated_by', 'taadmin')
                )
                db.add(offer_status)
            db.commit()

        return db_candidate

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating candidate: {str(e)}"
        )


############## APPLY FUNCTIONALITY ######################
@router.post("/apply", response_model=dict, status_code=status.HTTP_201_CREATED)
async def apply_to_job(
    background_tasks: BackgroundTasks,
    job_id: str = Form(...),
    candidate_name: Optional[str] = Form(None),
    email_id: Optional[str] = Form(None),
    mobile_no: Optional[str] = Form(None),
    skills_set: Optional[str] = Form(None),
    resume_url: Optional[str] = Form(None),
    resume_path: Optional[str] = Form(None),
    linkedin_url: Optional[str] = Form(None),
    current_location: Optional[str] = Form(None),
    use_existing_candidate: bool = Form(False),
    candidate_id: Optional[str] = Form(None),
    replace_previous_application: bool = Form(False),
    created_by: Optional[str] = Form("tateam"),
    created_at: Optional[str] = Form(None),
    updated_by: Optional[str] = Form(None),
    updated_at: Optional[str] = Form(None),
    applied_date: Optional[str] = Form(None),
    final_status: Optional[str] = Form(None),  # <-- Added this line
    db: Session = Depends(get_db)
):
    """
    Endpoint to apply for a job. 
    Handles single application per job with option to replace previous application.
    """
    try:
        # Parse and validate created_at if provided
        created_at_datetime = None
        if created_at:
            try:
                created_at_datetime = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid created_at format. Expected ISO format (e.g., '2025-06-19T07:47:00.000Z').")

        # Check if job exists
        job = db.query(models.Job).filter(models.Job.job_id == job_id).first()
        if not job or job.status != models.Status.OPEN:
            raise HTTPException(status_code=400, detail="Invalid or closed job")

        # Handle existing candidate
        if use_existing_candidate and candidate_id:
            candidate = db.query(models.Candidate).filter(
                models.Candidate.candidate_id == candidate_id
            ).first()
            if not candidate:
                raise HTTPException(status_code=404, detail="Candidate not found")

            # Check if candidate has already applied to jobs
            if candidate.associated_job_id:
                existing_job_ids = candidate.associated_job_id.split(',')
                
                # If already applied to this specific job, return error
                if job_id in existing_job_ids:
                    raise HTTPException(status_code=400, detail="Already applied for this job")
                
                # If candidate has previous applications and no confirmation to replace
                if len(existing_job_ids) >= 1 and not replace_previous_application:
                    # Get previous job details for the response
                    previous_jobs = db.query(models.Job).filter(
                        models.Job.job_id.in_(existing_job_ids)
                    ).all()
                    
                    previous_job_details = [
                        {
                            "job_id": job.job_id,
                            "title": getattr(job, 'title', 'Unknown'),
                            "company": getattr(job, 'company', 'Unknown')
                        } for job in previous_jobs
                    ]
                    
                    return {
                        "status": "confirmation_required",
                        "message": "Candidate has already applied to other job(s). Do you want to replace the previous application(s)?",
                        "previous_applications": previous_job_details,
                        "current_job_id": job_id,
                        "candidate_id": candidate_id,
                        "action_required": "Set 'replace_previous_application=true' to confirm replacement"
                    }
                
                # If confirmation is given, replace previous applications
                if replace_previous_application:
                    candidate.associated_job_id = job_id
                else:
                    # Add to existing applications
                    candidate.associated_job_id = f"{candidate.associated_job_id},{job_id}"
            else:
                # First application for this candidate
                candidate.associated_job_id = job_id

            # Update department if not already assigned
            if not candidate.department:
                candidate.department = get_department_from_job_id(job_id, db)

            # Merge existing skills with new skills
            existing_skills = candidate.skills_set.split(",") if candidate.skills_set else []
            new_skills = skills_set.split(",") if skills_set else []
            all_skills = list(set(existing_skills + new_skills))  # Remove duplicates and merge
            candidate.skills_set = ",".join(all_skills) if all_skills else None

            # Update LinkedIn URL if provided
            if linkedin_url:
                candidate.linkedin_url = linkedin_url

            # Update other fields if provided
            if current_location:
                candidate.current_location = current_location

            # Update candidate_name, email_id, mobile_no if provided
            if candidate_name:
                candidate.candidate_name = candidate_name
            if email_id:
                candidate.email_id = email_id
            if mobile_no:
                candidate.mobile_no = mobile_no

            # Update resume if provided
            if resume_url and resume_path:
                candidate.resume_url = resume_url
                candidate.resume_path = resume_path

            # Update created_by and created_at if provided
            candidate.created_by = created_by
            if created_at_datetime:
                candidate.created_at = created_at_datetime

            # Update updated_by and updated_at if provided
            if updated_by:
                candidate.updated_by = updated_by
            if updated_at:
                try:
                    candidate.updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid updated_at format. Expected ISO format (e.g., '2025-06-19T07:47:00.000Z').")

            # Update applied_date if provided
            if applied_date:
                try:
                    candidate.application_date = datetime.fromisoformat(applied_date.replace("Z", "+00:00")).date()
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid applied_date format. Expected ISO format (e.g., '2025-06-19T07:47:00.000Z').")

            # Update final_status if provided
            if final_status is not None:
                candidate.final_status = final_status

            db.commit()
            return {
                "message": "Application submitted successfully",
                "candidate_id": candidate.candidate_id,
                "job_id": job_id,
                "action": "replaced_previous" if replace_previous_application else "added_new"
            }

        # Handle new candidate
        if not use_existing_candidate:
            if not candidate_name or not email_id or not mobile_no or not resume_url or not resume_path:
                raise HTTPException(
                    status_code=400, 
                    detail="Missing required fields for new application (including resume URL and path)"
                )

            # Automatically assign department based on job
            department = get_department_from_job_id(job_id, db)
            
            new_candidate = models.Candidate(
                candidate_name=candidate_name,
                email_id=email_id,
                mobile_no=mobile_no,
                skills_set=skills_set,
                associated_job_id=job_id,
                resume_url=resume_url,
                resume_path=resume_path,
                linkedin_url=linkedin_url,
                current_location=current_location,
                department=department,
                created_by=created_by,  # Set created_by
                created_at=created_at_datetime or datetime.utcnow(),  # Use provided created_at or current time
                application_date=datetime.fromisoformat(applied_date.replace("Z", "+00:00")).date() if applied_date else date.today(),  # Set application_date
                final_status=final_status,  # <-- Added this line
                expected_date_of_joining=None,
            )
            
            db.add(new_candidate)
            db.commit()
            db.refresh(new_candidate)
            
            return {
                "message": "Application submitted successfully",
                "candidate_id": new_candidate.candidate_id,
                "job_id": job_id
            }

    except HTTPException as e:
        raise e
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))




@router.get("/excel-template")
def get_excel_template():
    """
    Generate and download an example Excel template for candidate upload.
    """
    try:
        # Create a sample dataframe with all the columns
        columns = [
            'Candidate ID', 'Candidate Name', 'Email ID', 'Mobile No.','PAN Card Number', 
            'Associated with (Job ID)', 'Date of Resume Received', 'Skill Set',
            'Notice Period', 'Notice Period Unit', 'Additional Information of NPD',
            'Years of Experience', 'Mode of Work', 'gender','Current Location',
            'Current Designation', 'Current Company', 'Reason for Job Change',
            'Current Fixed CTC', 'Current Variable Pay', 'Expected Fixed CTC',
            'TA Team', 'L1 Interview Date', 'L1 Interviewer Name', 'L1 Status',
            'L1 Interview Feedback', 'L2 Interview Date', 'L2 Interviewer Name',
            'L2 Status', 'L2 Interview Feedback', 'HR Interview Date',
            'HR Interviewer Name', 'HR Status', 'HR Interview Feedback',
            'Current Status', 'Status', 'CTC Breakup Status', 'Current Address', 'Permanent Address'
        ]
        
        # Create sample data with one row of example values
        # sample_data = [[
        #     "", "John Doe", "john.doe@example.com", "1234567890",
        #     "JOB123", date.today().strftime("%Y-%m-%d"), "Python, React, SQL",
        #     "30", "Days", "Can join earlier if needed",
        #     "5", "Remote", "New York",
        #     "Senior Developer", "ABC Corp", "Career Growth",
        #     "100000", "20000", "150000",
        #     "Engineering", "", "", "",
        #     "", "", "", 
        #     "", "", "",
        #     "", "", "",
        #     "SCREENING", "New Application", "123 Main St", "123 Main St"
        # ]]
        
        # Create a dataframe and write to a temporary Excel file
        df = pd.DataFrame(columns=columns)
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            temp_filename = tmp.name
            # Use ExcelWriter to format the date column
            with pd.ExcelWriter(temp_filename, engine='xlsxwriter', datetime_format='DD-MM-YYYY') as writer:
                df.to_excel(writer, index=False)
        
        # Return the file as a downloadable response
        return FileResponse(
            path=temp_filename,
            filename="candidate_upload_template.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating template: {str(e)}")


######################### Current Status ##############################

@router.get("/current_status/all", response_model=List[schemas.CurrentStatusModel])
async def get_all_statuses(db: Session = Depends(database.get_db)):
    """Get all current statuses sorted by weight in ascending order."""
    try:
        db_statuses = db.query(models.StatusDB).order_by(models.StatusDB.weight.asc()).all()
        logger.info(f"Fetched {len(db_statuses)} statuses from database")
        
        statuses = []
        for s in db_statuses:
            if s.weight is None:
                logger.warning(f"Status ID {s.id} has NULL weight, setting to 0")
                s.weight = 0  # Temporary fallback, should be fixed in DB
                db.commit()
            statuses.append({
                "id": s.id,
                "status": s.status,
                "final_status_id": s.final_status_id,
                "final_status": s.final_status.status if s.final_status else None,
                "weight": s.weight,
                "created_by": s.created_by,
                "updated_by": s.updated_by,
                "created_at": s.created_at,
                "updated_at": s.updated_at
            })
        
        if not statuses:
            logger.info("No statuses found in the database.")
            return []
        
        return statuses

    except Exception as e:
        logger.error(f"Error fetching current statuses: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving statuses: {str(e)}"
        )

@router.get("/current_status/next_weight", response_model=int)
async def get_next_weight(db: Session = Depends(database.get_db)):
    """Get the next available weight for a current status."""
    try:
        max_weight = db.query(func.max(models.StatusDB.weight)).scalar()
        next_weight = (max_weight or -1) + 1
        logger.info(f"Suggested next weight: {next_weight}")
        return next_weight
    except Exception as e:
        logger.error(f"Error fetching next weight: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching next weight"
        )

@router.get("/current_status/{status_id}", response_model=schemas.CurrentStatusModel)
async def get_status(status_id: int = Path(..., gt=0), db: Session = Depends(database.get_db)):
    """Get a specific status by ID"""
    try:
        db_status = db.query(models.StatusDB).filter(models.StatusDB.id == status_id).first()
        if db_status is None:
            logger.warning(f"Status with ID {status_id} not found")
            raise HTTPException(status_code=404, detail="Not found")
        
        if db_status.weight is None:
            logger.warning(f"Status ID {status_id} has NULL weight, setting to 0")
            db_status.weight = 0
            db.commit()
        
        response_data = {
            "id": db_status.id,
            "status": db_status.status,
            "final_status_id": db_status.final_status_id,
            "final_status": db_status.final_status.status if db_status.final_status else None,
            "weight": db_status.weight,
            "created_by": db_status.created_by,
            "updated_by": db_status.updated_by,
            "created_at": db_status.created_at,
            "updated_at": db_status.updated_at
        }
        logger.info(f"Fetched status with ID {status_id}")
        return response_data
    except Exception as e:
        logger.error(f"Error fetching status {status_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving status: {str(e)}"
        )

@router.post("/current_status", response_model=schemas.CurrentStatusModel, status_code=status.HTTP_201_CREATED)
async def create_status(status_model: schemas.CurrentStatusCreate = Body(...), db: Session = Depends(database.get_db)):
    """Create a new current status"""
    try:
        # Validate final_status_id if provided
        if status_model.final_status_id:
            final_status = db.query(models.FinalStatusDB).filter(models.FinalStatusDB.id == status_model.final_status_id).first()
            if not final_status:
                logger.warning(f"Final status ID {status_model.final_status_id} not found")
                raise HTTPException(status_code=404, detail="Final status not found")
        
        # Check for duplicate status
        existing_status = db.query(models.StatusDB).filter(models.StatusDB.status == status_model.status).first()
        if existing_status:
            logger.warning(f"Status {status_model.status} already exists")
            raise HTTPException(status_code=400, detail="Status already exists")
        
        # Check for duplicate weight
        existing_weight = db.query(models.StatusDB).filter(models.StatusDB.weight == status_model.weight).first()
        if existing_weight:
            logger.warning(f"Weight {status_model.weight} already assigned")
            raise HTTPException(status_code=400, detail="Weight already assigned")

        db_status = models.StatusDB(
            status=status_model.status,
            final_status_id=status_model.final_status_id,
            weight=status_model.weight,
            created_by=getattr(status_model, 'created_by', 'system'),
            updated_by=getattr(status_model, 'updated_by', 'system')
        )
        db.add(db_status)
        db.commit()
        db.refresh(db_status)
        
        logger.info(f"Created status {db_status.status} with weight {db_status.weight} by {db_status.created_by}")
        
        response_data = {
            "id": db_status.id,
            "status": db_status.status,
            "final_status_id": db_status.final_status_id,
            "final_status": db_status.final_status.status if db_status.final_status else None,
            "weight": db_status.weight,
            "created_by": db_status.created_by,
            "updated_by": db_status.updated_by,
            "created_at": db_status.created_at,
            "updated_at": db_status.updated_at
        }
        return response_data
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error creating status: {str(e)}"
        )

@router.put("/current_status/{status_id}", response_model=schemas.CurrentStatusModel)
async def update_status(
    status_model: schemas.CurrentStatusCreate = Body(...),
    status_id: int = Path(..., gt=0),
    db: Session = Depends(database.get_db)
):
    """Update an existing current status with weight swapping"""
    try:
        db_status = db.query(models.StatusDB).filter(models.StatusDB.id == status_id).first()
        if not db_status:
            logger.warning(f"Status with ID {status_id} not found")
            raise HTTPException(status_code=404, detail="Not found")
        
        # Validate final_status_id if provided
        if status_model.final_status_id:
            final_status = db.query(models.FinalStatusDB).filter(models.FinalStatusDB.id == status_model.final_status_id).first()
            if not final_status:
                logger.warning(f"Final status ID {status_model.final_status_id} not found")
                raise HTTPException(status_code=404, detail="Final status not found")
        
        # Check for duplicate status (excluding current status)
        existing_status = db.query(models.StatusDB).filter(
            models.StatusDB.status == status_model.status,
            models.StatusDB.id != status_id
        ).first()
        if existing_status:
            logger.warning(f"Status {status_model.status} already exists")
            raise HTTPException(status_code=400, detail="Status already exists")
        
        # Check if another status has the desired weight
        existing_weight_status = db.query(models.StatusDB).filter(
            models.StatusDB.weight == status_model.weight,
            models.StatusDB.id != status_id
        ).first()
        
        # Start a transaction
        try:
            if existing_weight_status:
                # Swap weights: assign current status's weight to the other status
                existing_weight_status.weight = db_status.weight
                existing_weight_status.updated_by = getattr(status_model, 'updated_by', None)
                existing_weight_status.updated_at = datetime.utcnow()
            
            # Update the current status
            db_status.status = status_model.status
            db_status.final_status_id = status_model.final_status_id
            db_status.weight = status_model.weight
            db_status.updated_by = getattr(status_model, 'updated_by', None)
            db_status.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(db_status)
            if existing_weight_status:
                db.refresh(existing_weight_status)
                
            logger.info(f"Updated status ID {status_id} with weight {db_status.weight} by {db_status.updated_by}")
            if existing_weight_status:
                logger.info(f"Swapped weight with status ID {existing_weight_status.id}, new weight {existing_weight_status.weight}")
            
            return {
                "id": db_status.id,
                "status": db_status.status,
                "final_status_id": db_status.final_status_id,
                "final_status": db_status.final_status.status if db_status.final_status else None,
                "weight": db_status.weight,
                "created_by": db_status.created_by,
                "updated_by": db_status.updated_by,
                "created_at": db_status.created_at,
                "updated_at": db_status.updated_at
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Error during weight swap for status ID {status_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error updating status: {str(e)}"
            )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating status {status_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error updating status: {str(e)}"
        )

@router.delete("/current_status/{status_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_status(status_id: int = Path(..., gt=0), db: Session = Depends(database.get_db)):
    """Delete a current status by ID"""
    try:
        db_status = db.query(models.StatusDB).filter(models.StatusDB.id == status_id).first()
        if not db_status:
            logger.warning(f"Status with ID {status_id} not found")
            raise HTTPException(status_code=404, detail="Not found")
        
        db.delete(db_status)
        db.commit()
        logger.info(f"Deleted status ID {status_id}")
        return None
    except Exception as e:
        logger.error(f"Error deleting status {status_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error deleting status: {str(e)}"
        )

# ----- Final Status Operations -----

@router.get("/final_status/all", response_model=List[schemas.FinalStatusModel])
async def get_all_final_statuses(db: Session = Depends(database.get_db)):
    """Get all final statuses sorted by weight in ascending order"""
    try:
        db_statuses = db.query(models.FinalStatusDB).order_by(models.FinalStatusDB.weight.asc()).all()
        logger.info(f"Fetched {len(db_statuses)} final statuses from database")
        
        statuses = []
        for s in db_statuses:
            if s.weight is None:
                logger.warning(f"Final status ID {s.id} has NULL weight, setting to 0")
                s.weight = 0  # Temporary fallback
                db.commit()
            statuses.append({
                "id": s.id,
                "status": s.status,
                "weight": s.weight,
                "created_at": s.created_at,
                "updated_at": s.updated_at,
                "created_by": getattr(s, 'created_by', 'taadmin'),
                "updated_by": getattr(s, 'updated_by', 'taadmin')
         
            })
        
        if not statuses:
            logger.info("No final statuses found in the database.")
            return []
        
        return statuses
    except Exception as e:
        logger.error(f"Error fetching final statuses: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving final statuses: {str(e)}"
        )

@router.get("/final_status/all", response_model=List[schemas.FinalStatusModel])
async def get_all_final_statuses(db: Session = Depends(database.get_db)):
    """Get all final statuses sorted by weight in ascending order"""
    try:
        db_statuses = db.query(models.FinalStatusDB).order_by(models.FinalStatusDB.weight.asc()).all()
        logger.info(f"Fetched {len(db_statuses)} final statuses from database")
        
        statuses = []
        for s in db_statuses:
            if s.weight is None:
                logger.warning(f"Final status ID {s.id} has NULL weight, setting to 0")
                s.weight = 0  # Temporary fallback
                db.commit()
            statuses.append({
                "id": s.id,
                "status": s.status,
                "weight": s.weight,
                "created_at": s.created_at,
                "updated_at": s.updated_at,
                "created_by": getattr(s, 'created_by', 'taadmin'),
                "updated_by": getattr(s, 'updated_by', 'taadmin')
                
            })
        
        if not statuses:
            logger.info("No final statuses found in the database.")
            return []
        
        return statuses
    except Exception as e:
        logger.error(f"Error fetching final statuses: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving final statuses: {str(e)}"
        )

@router.post("/final_status", response_model=schemas.FinalStatusModel, status_code=status.HTTP_201_CREATED)
async def create_final_status(
    status_model: schemas.FinalStatusCreate = Body(...), 
    db: Session = Depends(database.get_db),
    current_user: str = "taadmin"
):
    """Create a new final status"""
    try:
        # Check for duplicate status
        existing_status = db.query(models.FinalStatusDB).filter(
            models.FinalStatusDB.status == status_model.status
        ).first()
        if existing_status:
            logger.warning(f"Status {status_model.status} already exists")
            raise HTTPException(status_code=400, detail="Status already exists")
        
        # Check for duplicate weight
        existing_weight = db.query(models.FinalStatusDB).filter(
            models.FinalStatusDB.weight == status_model.weight
        ).first()
        if existing_weight:
            logger.warning(f"Weight {status_model.weight} already assigned")
            raise HTTPException(status_code=400, detail="Weight already assigned")
        
        db_status = models.FinalStatusDB(
            status=status_model.status,
            weight=status_model.weight,
            created_at=status_model.created_at or datetime.utcnow(),
            created_by=status_model.created_by or current_user,
                )
        db.add(db_status)
        db.commit()
        db.refresh(db_status)
        
        logger.info(f"Created final status {db_status.status} with weight {db_status.weight} by {db_status.created_by}")
        
        return {
            "id": db_status.id,
            "status": db_status.status,
            "weight": db_status.weight,
            "created_at": db_status.created_at,
            "updated_at": db_status.updated_at,
            "created_by": db_status.created_by,
            "updated_by": db_status.updated_by
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating final status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error creating final status: {str(e)}"
        )

@router.put("/final_status/{status_id}", response_model=schemas.FinalStatusModel)
async def update_final_status(
    status_model: schemas.FinalStatusCreate = Body(...),
    status_id: int = Path(..., gt=0),
    db: Session = Depends(database.get_db),
    current_user: str = "taadmin"
):
    """Update an existing final status with weight swapping"""
    try:
        db_status = db.query(models.FinalStatusDB).filter(models.FinalStatusDB.id == status_id).first()
        if db_status is None:
            logger.warning(f"Final status with ID {status_id} not found")
            raise HTTPException(status_code=404, detail="Final status not found")
        
        # Check for duplicate status (excluding current status)
        existing_status = db.query(models.FinalStatusDB).filter(
            models.FinalStatusDB.status == status_model.status,
            models.FinalStatusDB.id != status_id
        ).first()
        if existing_status:
            logger.warning(f"Status {status_model.status} already exists")
            raise HTTPException(status_code=400, detail="Status already exists")
        
        # Check if another status has the desired weight
        existing_weight_status = db.query(models.FinalStatusDB).filter(
            models.FinalStatusDB.weight == status_model.weight,
            models.FinalStatusDB.id != status_id
        ).first()
        
        # Start a transaction
        try:
            if existing_weight_status:
                # Swap weights: assign current status's weight to the other status
                existing_weight_status.weight = db_status.weight
                existing_weight_status.updated_by = status_model.updated_by or current_user
                existing_weight_status.updated_at = status_model.updated_at or datetime.utcnow()
                logger.info(f"Swapping weight: setting weight {db_status.weight} for status ID {existing_weight_status.id}")
            
            # Update the current status
            db_status.status = status_model.status
            db_status.weight = status_model.weight
            db_status.updated_by = status_model.updated_by or current_user
            db_status.updated_at = status_model.updated_at or datetime.utcnow()

            db.commit()
            db.refresh(db_status)
            if existing_weight_status:
                db.refresh(existing_weight_status)
                
            logger.info(f"Updated final status ID {status_id} with weight {db_status.weight} by {db_status.updated_by}")
            if existing_weight_status:
                logger.info(f"Swapped weight with status ID {existing_weight_status.id}, new weight {existing_weight_status.weight}")
            
            return {
                "id": db_status.id,
                "status": db_status.status,
                "weight": db_status.weight,
                "created_at": db_status.created_at,
                "updated_at": db_status.updated_at,
                "created_by": getattr(db_status, 'created_by', 'taadmin'),
                "updated_by": db_status.updated_by
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Error during weight swap for status ID {status_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error updating final status: {str(e)}"
            )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating final status {status_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error updating final status: {str(e)}"
        )

@router.delete("/final_status/{status_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_final_status(status_id: int = Path(..., gt=0), db: Session = Depends(database.get_db),current_user: str = "taadmin"):
    """Delete a final status"""
    try:
        db_status = db.query(models.FinalStatusDB).filter(models.FinalStatusDB.id == status_id).first()
        if db_status is None:
            logger.warning(f"Final status with ID {status_id} not found")
            raise HTTPException(status_code=404, detail="Final status not found")
        
        # Check if linked to any current statuses
        linked_statuses = db.query(models.StatusDB).filter(models.StatusDB.final_status_id == status_id).first()
        if linked_statuses:
            logger.warning(f"Final status ID {status_id} is linked to current statuses")
            raise HTTPException(status_code=400, detail="Cannot delete final status linked to current statuses")
        
        db.delete(db_status)
        db.commit()
        logger.info(f"Deleted final status ID {status_id}")
        return None
    except Exception as e:
        logger.error(f"Error deleting final status {status_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error deleting final status: {str(e)}"
        )

@router.get("/final_status/next_weight", response_model=int)
async def get_next_weight(db: Session = Depends(database.get_db)):
    """Get the next available weight for a final status."""
    try:
        max_weight = db.query(func.max(models.FinalStatusDB.weight)).scalar()
        next_weight = (max_weight or -1) + 1
        logger.info(f"Suggested next weight: {next_weight}")
        return next_weight
    except Exception as e:
        logger.error(f"Error fetching next weight: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching next weight"
        )
    
# ----- Offer Status Operations ----- ##
@router.get("/offer_status/all", response_model=List[OfferStatusModel])
async def get_all_offer_statuses(db: Session = Depends(get_db)):
    """Get all offer statuses"""
    return db.query(OfferStatusDB).all()

@router.get("/offer_status/{status_id}", response_model=OfferStatusModel)
async def get_offer_status(
    status_id: int = Path(..., gt=0), 
    db: Session = Depends(get_db)
):
    """Get a specific offer status by ID"""
    db_status = db.query(OfferStatusDB).filter(OfferStatusDB.id == status_id).first()
    if db_status is None:
        raise HTTPException(status_code=404, detail="Offer status not found")
    return db_status

@router.post("/offer_status", response_model=OfferStatusModel, status_code=status.HTTP_201_CREATED)
async def create_offer_status(
    status_model: OfferStatusCreate = Body(...),
    db: Session = Depends(get_db)
):
    """Create a new offer status"""
    # Check if status already exists
    existing_status = db.query(OfferStatusDB).filter(
        OfferStatusDB.status == status_model.status
    ).first()
    if existing_status:
        raise HTTPException(
            status_code=400, 
            detail=f"Offer status '{status_model.status}' already exists"
        )
    db_status = OfferStatusDB(
        status=status_model.status,
        created_by=status_model.created_by if status_model.created_by else "taadmin",
        updated_by=status_model.updated_by if hasattr(status_model, 'updated_by') and status_model.updated_by else None
    )
    db.add(db_status)
    db.commit()
    db.refresh(db_status)
    return db_status

@router.put("/offer_status/{status_id}", response_model=OfferStatusModel)
async def update_offer_status(
    status_id: int = Path(..., gt=0),
    status_model: OfferStatusUpdate = Body(...),
    db: Session = Depends(get_db)
):
    """Update an existing offer status"""
    db_status = db.query(OfferStatusDB).filter(OfferStatusDB.id == status_id).first()
    if db_status is None:
        raise HTTPException(status_code=404, detail="Offer status not found")
    # Check if the new status name already exists (excluding current record)
    existing_status = db.query(OfferStatusDB).filter(
        OfferStatusDB.status == status_model.status,
        OfferStatusDB.id != status_id
    ).first()
    if existing_status:
        raise HTTPException(
            status_code=400, 
            detail=f"Offer status '{status_model.status}' already exists"
        )
    # Update fields
    db_status.status = status_model.status
    db_status.updated_by = status_model.updated_by if status_model.updated_by else "taadmin"
    db.commit()
    db.refresh(db_status)
    return db_status

@router.delete("/offer_status/{status_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_offer_status(
    status_id: int = Path(..., gt=0), 
    db: Session = Depends(get_db)
):
    """Delete an offer status"""
    db_status = db.query(OfferStatusDB).filter(OfferStatusDB.id == status_id).first()
    if db_status is None:
        raise HTTPException(status_code=404, detail="Offer status not found")
    
   
    
    db.delete(db_status)
    db.commit()
    return None

# ----- Interview Status Operations ----- #
@router.get("/interview_status/all", response_model=List[schemas.InterviewStatusModel])
async def get_all_interview_statuses(db: Session = Depends(get_db)):
    """Get all interview statuses sorted by weight"""
    return db.query(models.InterviewStatusDB).order_by(models.InterviewStatusDB.weight.asc()).all()

@router.get("/interview_status/{status_id}", response_model=schemas.InterviewStatusModel)
async def get_interview_status(status_id: int = Path(..., gt=0), db: Session = Depends(get_db)):
    """Get a specific interview status by ID"""
    db_status = db.query(models.InterviewStatusDB).filter(models.InterviewStatusDB.id == status_id).first()
    if db_status is None:
        raise HTTPException(status_code=404, detail="Interview status not found")
    return db_status

@router.post("/interview_status", response_model=schemas.InterviewStatusModel)
async def create_interview_status(
    status_data: schemas.InterviewStatusCreate = Body(...),
    db: Session = Depends(get_db)
):
    """Create a new interview status"""
    # Check if status already exists (case-insensitive)
    existing_status = db.query(models.InterviewStatusDB).filter(
        models.InterviewStatusDB.status.ilike(status_data.status.strip())
    ).first()
    if existing_status:
        raise HTTPException(status_code=400, detail="Interview status already exists")

    # Check if weight is already taken
    existing_weight = db.query(models.InterviewStatusDB).filter(
        models.InterviewStatusDB.weight == status_data.weight
    ).first()
    if existing_weight:
        raise HTTPException(status_code=400, detail="Serial Number is already assigned to another status")

    # Create new status with created_by from frontend
    db_status = models.InterviewStatusDB(
        status=status_data.status.strip(), 
        weight=status_data.weight,
        created_by=status_data.created_by or "taadmin",
        updated_by=status_data.updated_by
    )
    try:
        db.add(db_status)
        db.commit()
        db.refresh(db_status)
    except IntegrityError as e:
        db.rollback()
        print("DB ERROR (POST /interview_status):", e)
        raise HTTPException(status_code=400, detail=f"DB error: {str(e)}")
    return db_status

@router.put("/interview_status/{status_id}", response_model=schemas.InterviewStatusModel)
async def update_interview_status(
    status_data: schemas.InterviewStatusModel = Body(...),
    status_id: int = Path(..., gt=0),
    db: Session = Depends(get_db)
):
    """Update an existing interview status"""
    db_status = db.query(models.InterviewStatusDB).filter(models.InterviewStatusDB.id == status_id).first()
    if db_status is None:
        raise HTTPException(status_code=404, detail="Interview status not found")
    
    # Check if status already exists (case-insensitive, excluding current status)
    existing_status = db.query(models.InterviewStatusDB).filter(
        models.InterviewStatusDB.status.ilike(status_data.status.strip()),
        models.InterviewStatusDB.id != status_id
    ).first()
    if existing_status:
        raise HTTPException(status_code=400, detail="Interview status already exists")

    # Handle weight swapping
    if status_data.weight != db_status.weight:
        existing_weight = db.query(models.InterviewStatusDB).filter(
            models.InterviewStatusDB.weight == status_data.weight
        ).first()
        if existing_weight:
            # Swap weights and update updated_by for the swapped record
            existing_weight.weight = db_status.weight
            existing_weight.updated_by = getattr(status_data, 'updated_by', None)
            db.commit()

    # Update the status, weight, and updated_by field
    db_status.status = status_data.status.strip()
    db_status.weight = status_data.weight
    db_status.updated_by = getattr(status_data, 'updated_by', None)
    
    try:
        db.commit()
        db.refresh(db_status)
    except IntegrityError as e:
        db.rollback()
        print("DB ERROR (PUT /interview_status):", e)
        raise HTTPException(status_code=400, detail=f"DB error: {str(e)}")
    return db_status

@router.delete("/interview_status/{status_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_interview_status(status_id: int = Path(..., gt=0), db: Session = Depends(get_db)):
    """Delete an interview status"""
    db_status = db.query(models.InterviewStatusDB).filter(models.InterviewStatusDB.id == status_id).first()
    if db_status is None:
        raise HTTPException(status_code=404, detail="Interview status not found")
    
    db.delete(db_status)
    db.commit()
    return None
# ---------------- Rating ------------ #

@router.get("/rating/all", response_model=List[RatingModel])
async def get_all_ratings(db: Session = Depends(get_db)):
    """Get all rating values"""
    return db.query(RatingDB).all()

@router.get("/rating/{rating_id}", response_model=RatingModel)
async def get_rating(rating_id: int = Path(..., gt=0), db: Session = Depends(get_db)):
    """Get a specific rating by ID"""
    db_rating = db.query(RatingDB).filter(RatingDB.id == rating_id).first()
    if db_rating is None:
        raise HTTPException(status_code=404, detail="Rating not found")
    return db_rating

@router.post("/rating", response_model=RatingModel, status_code=status.HTTP_201_CREATED)
async def create_rating(rating_model: RatingModel = Body(...), db: Session = Depends(get_db)):
    """Create a new rating"""
    db_rating = RatingDB(
        rating=rating_model.rating,
        created_by=rating_model.created_by,
        created_at=rating_model.created_at
        # updated_by and updated_at are not set here to ensure they are blank
    )
    db_rating = RatingDB(
        rating=rating_model.rating,
        created_by=rating_model.created_by,
        created_at=rating_model.created_at
        # updated_by and updated_at are not set here to ensure they are blank
    )
    db.add(db_rating)
    db.commit()
    db.refresh(db_rating)
    return db_rating

@router.put("/rating/{rating_id}", response_model=RatingModel)
async def update_rating(
    rating_model: RatingModel = Body(...),
    rating_id: int = Path(..., gt=0),
    db: Session = Depends(get_db)
):
    """Update an existing rating"""
    db_rating = db.query(RatingDB).filter(RatingDB.id == rating_id).first()
    if db_rating is None:
        raise HTTPException(status_code=404, detail="Rating not found")

    db_rating.rating = rating_model.rating
    db_rating.updated_by = rating_model.updated_by
    db_rating.updated_at = rating_model.updated_at
    db_rating.updated_by = rating_model.updated_by
    db_rating.updated_at = rating_model.updated_at
    db.commit()
    db.refresh(db_rating)
    return db_rating

@router.delete("/rating/{rating_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rating(rating_id: int = Path(..., gt=0), db: Session = Depends(get_db)):
    """Delete a rating"""
    db_rating = db.query(RatingDB).filter(RatingDB.id == rating_id).first()
    if db_rating is None:
        raise HTTPException(status_code=404, detail="Rating not found")

    db.delete(db_rating)
    db.commit()
    return None


# ----- Offer Letter Status Operations ----- #

# ----- Offer Letter Status Operations ----- #

@router.post("/offer-letter-status", response_model=OfferLetterStatusResponse)
def create_offer_letter_status(
    offer_status: OfferLetterStatusCreate,
    db: Session = Depends(get_db)
):
    """Create offer letter status for a candidate"""
    try:
        # Check if candidate exists
        candidate = db.query(Candidate).filter(Candidate.candidate_id == offer_status.candidate_id).first()
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")
        
        # Check if offer letter status already exists for this candidate
        existing_status = db.query(models.OfferLetterStatus).filter(
            models.OfferLetterStatus.candidate_id == offer_status.candidate_id
        ).first()
        if existing_status:
            raise HTTPException(status_code=400, detail="Offer letter status already exists for this candidate")
        
        # Create the offer status with default created_by and updated_by
        offer_data = offer_status.model_dump()
        offer_data['created_by'] = offer_data.get('created_by') or 'taadmin'
        offer_data['created_at'] = datetime.now()
       
        
        db_offer_status = models.OfferLetterStatus(**offer_data)
        db.add(db_offer_status)
        db.commit()
        db.refresh(db_offer_status)
        return db_offer_status
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating offer letter status: {str(e)}")


@router.put("/offer-letter-status/{candidate_id}", response_model=OfferLetterStatusResponse)
def update_offer_letter_status(
    candidate_id: str,
    update_data: OfferLetterStatusUpdate,
    db: Session = Depends(get_db)
):
    """Update or create offer letter status for a candidate (upsert)"""
    try:
        db_offer_status = db.query(models.OfferLetterStatus).filter(
            models.OfferLetterStatus.candidate_id == candidate_id
        ).first()
        
        update_dict = update_data.model_dump(exclude_unset=True)
        
        if db_offer_status:
            # Update existing record
            update_dict['updated_by'] = update_data.updated_by or 'taadmin'
            update_dict['updated_at'] = datetime.now()
        
            for key, value in update_dict.items():
                setattr(db_offer_status, key, value)
        else:
            # Create new record
            if 'offer_letter_status' not in update_dict:
                 raise HTTPException(status_code=422, detail="offer_letter_status is required to create an offer letter status.")
            
            creation_data = update_dict
            creation_data['candidate_id'] = candidate_id
            creation_data['created_by'] = update_data.created_by or 'taadmin'
            if 'updated_by' in creation_data:
                del creation_data['updated_by'] # Not needed for creation

            db_offer_status = models.OfferLetterStatus(**creation_data)
            db.add(db_offer_status)

        db.commit()
        db.refresh(db_offer_status)
        return db_offer_status
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=f"Error updating or creating offer letter status: {str(e)}")


@router.get("/offer-letter-status/{candidate_id}", response_model=OfferLetterStatusResponse)
def get_offer_letter_status(
    candidate_id: str,
    db: Session = Depends(get_db)
):
    """Get offer letter status for a candidate"""
    try:
        db_offer_status = db.query(models.OfferLetterStatus).filter(
            models.OfferLetterStatus.candidate_id == candidate_id
        ).first()
        if not db_offer_status:
            raise HTTPException(status_code=404, detail="Offer letter status not found for this candidate")
        return db_offer_status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving offer letter status: {str(e)}")

    

@router.post("/{candidate_id}/resume-upload-url", status_code=201)
def generate_candidate_resume_upload_url(
    candidate_id: str,
    data: ResumeUploadRequest,
    db: Session = Depends(get_db)
):
    """
    Generate a presigned URL for uploading a resume for a specific candidate and update their resume_url and resume_path.
    
    Parameters:
    - candidate_id: The ID of the candidate whose resume is being uploaded
    - data: ResumeUploadRequest containing file_name and content_type
    """
    # Check if candidate exists
    db_candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    if not db_candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Validate file type
    extension = get_file_extension(data.file_name)
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Generate unique filename to prevent overwriting
    unique_filename = f"resumes/{uuid.uuid4()}-{data.file_name}"

    try:
        # Generate presigned URL for S3 upload
        url = s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": S3_BUCKET,
                "Key": unique_filename,
                "ContentType": data.content_type,
            },
            ExpiresIn=3600  # 1 hour
        )
        # Generate the download URL that will be stored in the database
        resume_url = f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{unique_filename}"

        # Update candidate's resume_url and resume_path; preserve resume received date
        db_candidate.resume_url = resume_url
        db_candidate.resume_path = unique_filename
        # Do NOT auto-set date_of_resume_received here
        db.commit()
        db.refresh(db_candidate)

        return {
            "upload_url": url,
            "resume_url": resume_url,
            "file_key": unique_filename,
            "candidate_id": candidate_id,
            "message": f"Resume upload URL generated and candidate {candidate_id} updated successfully"
        }
    except ClientError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error generating upload URL: {str(e)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating candidate resume: {str(e)}")    
    
    
@router.delete("/{candidate_id}/resume")
async def delete_resume(candidate_id: str, db: Session = Depends(get_db)):
    # Fetch candidate from database
    candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    # Check if there's a resume to delete (either resume_path or resume_url)
    has_resume_path = candidate.resume_path and candidate.resume_path != "null" and candidate.resume_path.strip() != ""
    has_resume_url = candidate.resume_url and candidate.resume_url != "null" and candidate.resume_url.strip() != ""
    
    if not has_resume_path and not has_resume_url:
        # If no resume exists, just clear the fields and return success
        candidate.resume_path = None
        candidate.resume_url = None
        db.commit()
        db.refresh(candidate)
        return {"message": "Resume fields cleared successfully"}
    
    try:
        # Delete file from S3 only if resume_path exists
        if has_resume_path:
            s3_client.delete_object(Bucket=S3_BUCKET, Key=candidate.resume_path)
        
        # Update candidate in database
        candidate.resume_path = None
        candidate.resume_url = None
        db.commit()
        db.refresh(candidate)
        
        return {"message": "Resume deleted successfully"}
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete resume from S3: {str(e)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete resume: {str(e)}")  
    


@router.put("/update-offer-status")
def update_offer_status(
    candidate_id: int = Query(..., description="Candidate ID"),
    status: str = Query(..., description="New offer status (Accepted/Rejected)"),
    db: Session = Depends(get_db)
):
    valid_status = {"Accepted", "Rejected"}

    if status not in valid_status:
        raise HTTPException(status_code=400, detail="Invalid status. Must be 'Accepted' or 'Rejected'.")

    candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()

    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    candidate.offer_status = status
    # Add updated_by and updated_at fields
    candidate.updated_by = 'taadmin'
    candidate.updated_at = datetime.now()
    
    db.commit()

    return {"message": f"Offer status updated to '{status}' for candidate ID {candidate_id}"}


@router.put("/update-departments", response_model=dict)
def update_candidate_departments(db: Session = Depends(get_db)):
    """
    Update departments for existing candidates based on their associated job IDs.
    This endpoint will update all candidates who have associated_job_id but no department assigned.
    """
    try:
        # Find candidates who have associated_job_id but no department
        candidates_without_dept = db.query(Candidate).filter(
            and_(
                Candidate.associated_job_id.isnot(None),
                Candidate.associated_job_id != "",
                or_(
                    Candidate.department.is_(None),
                    Candidate.department == ""
                )
            )
        ).all()

        updated_count = 0
        errors = []

        for candidate in candidates_without_dept:
            try:
                department = get_department_from_job_id(candidate.associated_job_id, db)
                if department:
                    candidate.department = department
                    # Add updated_by and updated_at fields
                    candidate.updated_by = 'taadmin'
                    candidate.updated_at = datetime.now()
                    updated_count += 1
                    print(f"Updated candidate {candidate.candidate_id} with department: {department}")
                else:
                    errors.append(f"No department found for candidate {candidate.candidate_id} with job_id {candidate.associated_job_id}")
            except Exception as e:
                errors.append(f"Error updating candidate {candidate.candidate_id}: {str(e)}")

        if updated_count > 0:
            db.commit()

        response = {
            "message": f"Successfully updated {updated_count} candidates with departments",
            "updated_count": updated_count,
            "total_candidates_without_dept": len(candidates_without_dept)
        }

        if errors:
            response["errors"] = errors

        return response

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating candidate departments: {str(e)}"
        )

@router.get("/{candidate_id}/department", response_model=dict)
def get_candidate_department_info(candidate_id: str, db: Session = Depends(get_db)):
    """
    Get department information for a specific candidate and suggest department if missing.
    """
    try:
        candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")

        response = {
            "candidate_id": candidate_id,
            "candidate_name": candidate.candidate_name,
            "current_department": candidate.department,
            "associated_job_id": candidate.associated_job_id
        }

        # If no department but has job_id, suggest department
        if not candidate.department and candidate.associated_job_id:
            suggested_dept = get_department_from_job_id(candidate.associated_job_id, db)
            response["suggested_department"] = suggested_dept
            response["suggestion_message"] = f"Based on job ID {candidate.associated_job_id}, suggested department is: {suggested_dept}"

        return response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving candidate department info: {str(e)}"
        )


def get_department_from_job_id(job_id: str, db: Session) -> Optional[str]:
    """
    Get department name from job_id by querying the Job model.
    Handles both single job_id and comma-separated job_ids by taking the first one.
    """
    if not job_id:
        return None
    
    # Handle comma-separated job IDs - take the first one
    first_job_id = job_id.split(',')[0].strip()
    
    try:
        job = db.query(Job).filter(Job.job_id == first_job_id).first()
        if job and job.department:
            return job.department
    except Exception as e:
        print(f"Error fetching department for job_id {first_job_id}: {str(e)}")
    
    return None

@router.get("/applications-received/{job_id}")
def check_applications_received(job_id: str, db: Session = Depends(get_db)):
    """
    Check if any candidates have applied to a specific job.
    Returns applicationReceived: true/false
    """
    try:
        # Check if any candidate exists with this job_id in their associated_job_id
        candidate_exists = db.query(Candidate).filter(
            or_(
                Candidate.associated_job_id == job_id,  # Exact match for single job
                Candidate.associated_job_id.like(f"{job_id},%"),  # Job ID at start
                Candidate.associated_job_id.like(f"%,{job_id},%"),  # Job ID in middle
                Candidate.associated_job_id.like(f"%,{job_id}")  # Job ID at end
            )
        ).first()
        
        return {"applicationReceived": candidate_exists is not None}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                          detail=f"Error checking applications: {str(e)}"
          )
        
########Employeee API Endpoints##########

@router.get("/employees/{candidate_id}", response_model=Optional[EmployeeResponse])
def get_employee(candidate_id: str, db: Session = Depends(get_db)):
    """Get onboarding details for a candidate"""
    try:
        logger.debug(f"Getting onboarding details for candidate {candidate_id}")

        db_employee = db.query(Employee).filter(Employee.candidate_id == candidate_id).first()
        if not db_employee:
            logger.info(f"No onboarding details found for candidate {candidate_id}")
            return None

        return db_employee

    except Exception as e:
        logger.error(f"Error getting onboarding details for candidate {candidate_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get onboarding details: {str(e)}")

@router.post("/employees/{candidate_id}", response_model=EmployeeResponse)
def create_employee(candidate_id: str, employee: EmployeeCreate, db: Session = Depends(get_db)):
    """Create onboarding details for a candidate"""
    try:
        logger.debug(f"Creating onboarding details for candidate {candidate_id}")

        # Check if candidate exists
        db_candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
        if not db_candidate:
            logger.error(f"Candidate {candidate_id} not found")
            raise HTTPException(status_code=404, detail="Candidate not found")

        # Check if employee record already exists
        db_employee = db.query(Employee).filter(Employee.candidate_id == candidate_id).first()
        if db_employee:
            logger.error(f"Onboarding details already exist for candidate {candidate_id}")
            raise HTTPException(status_code=400, detail="Onboarding details already exist. Use PUT to update.")

        # Create new employee record with audit fields
        db_employee = Employee(
            candidate_id=candidate_id,
            employee_no=employee.employee_no,
            date_of_joining=employee.date_of_joining,
            comments=employee.comments,
            created_by="taadmin",
            created_at=datetime.utcnow()
          
        )
        db.add(db_employee)
        db.commit()
        db.refresh(db_employee)

        return db_employee

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating onboarding details for candidate {candidate_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create onboarding details: {str(e)}")

@router.put("/employees/{candidate_id}", response_model=EmployeeResponse)
def update_employee(candidate_id: str, employee_update: EmployeeUpdate, db: Session = Depends(get_db)):
    """Update onboarding details for a candidate"""
    try:
        logger.debug(f"Updating onboarding details for candidate {candidate_id}")

        # Check if employee record exists
        db_employee = db.query(Employee).filter(Employee.candidate_id == candidate_id).first()
        if not db_employee:
            logger.error(f"Onboarding details not found for candidate {candidate_id}")
            raise HTTPException(status_code=404, detail="Onboarding details not found. Use POST to create.")

        # Update fields
        update_data = employee_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_employee, key, value)


        db.commit()
        db.refresh(db_employee)

        # Prepare response
        response_data = {
            "id": db_employee.id,
            "candidate_id": db_employee.candidate_id,
            "employee_no": db_employee.employee_no,
            "date_of_joining": db_employee.date_of_joining,
            "comments": db_employee.comments,
            "created_at": db_employee.created_at,
            "updated_at": db_employee.updated_at,
            "updated_by": db_employee.updated_by,
        }

        return EmployeeResponse(**response_data)

    except ValidationError as ve:
        db.rollback()
        logger.error(f"Validation error for candidate {candidate_id}: {str(ve)}")
        raise HTTPException(status_code=422, detail=str(ve))
        # Prepare response
        response_data = {
            "id": db_employee.id,
            "candidate_id": db_employee.candidate_id,
            "employee_no": db_employee.employee_no,
            "date_of_joining": db_employee.date_of_joining,
            "comments": db_employee.comments,
            "created_at": db_employee.created_at,
            "updated_at": db_employee.updated_at,
            "updated_by": db_employee.updated_by,
        }

        return EmployeeResponse(**response_data)

    except ValidationError as ve:
        db.rollback()
        logger.error(f"Validation error for candidate {candidate_id}: {str(ve)}")
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating onboarding details for candidate {candidate_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update onboarding details: {str(e)}")        
        
###### Gender API ######


@router.get("/gender/all", response_model=List[GenderResponse])
async def get_all_genders(db: Session = Depends(get_db)):
    """Get all gender values in alphabetical order"""
    return db.query(GenderDB).order_by(GenderDB.gender.asc()).all()


@router.get("/gender/{gender_id}", response_model=GenderResponse)
async def get_gender(gender_id: int = Path(..., gt=0), db: Session = Depends(get_db)):
    """Get a specific gender by ID"""
    db_gender = db.query(GenderDB).filter(GenderDB.id == gender_id).first()
    if db_gender is None:
        raise HTTPException(status_code=404, detail="Gender not found")
    return db_gender


@router.post("/gendercreate", response_model=GenderResponse, status_code=status.HTTP_201_CREATED)
async def create_gender(gender_model: GenderCreate = Body(...), db: Session = Depends(get_db)):
    """Create a new gender"""
    # Check if gender already exists (case-insensitive)
    existing_gender = db.query(GenderDB).filter(GenderDB.gender.ilike(gender_model.gender)).first()
    if existing_gender:
        raise HTTPException(status_code=400, detail="Gender already exists")
    
    # Create new gender with audit fields
    db_gender = GenderDB(
        gender=gender_model.gender,
        created_by=gender_model.created_by or "taadmin",  # Use frontend or fallback
        created_at=datetime.utcnow()
      
    )
    db.add(db_gender)
    db.commit()
    db.refresh(db_gender)
    return db_gender


@router.put("/gender/{gender_id}", response_model=GenderResponse)
async def update_gender(
    gender_model: GenderCreate = Body(...),
    gender_id: int = Path(..., gt=0),
    db: Session = Depends(get_db)
):
    """Update an existing gender"""
    db_gender = db.query(GenderDB).filter(GenderDB.id == gender_id).first()
    if db_gender is None:
        raise HTTPException(status_code=404, detail="Gender not found")

    # Check for duplicate gender (case-insensitive)
    existing_gender = db.query(GenderDB).filter(
        GenderDB.gender.ilike(gender_model.gender),
        GenderDB.id != gender_id
    ).first()
    if existing_gender:
        raise HTTPException(status_code=400, detail="Gender already exists")

    # Update values
    db_gender.gender = gender_model.gender
    db_gender.updated_by = gender_model.updated_by or "taadmin"
    db_gender.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(db_gender)
    return db_gender



@router.delete("/gender/{gender_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_gender(gender_id: int = Path(..., gt=0), db: Session = Depends(get_db)):
    gender = db.query(models.GenderDB).filter(models.GenderDB.id == gender_id).first()
    if not gender:
        raise HTTPException(status_code=404, detail="Gender not found")
    
    db.delete(gender)
    db.commit()
    return {"message": "Gender deleted successfully"}

################## ROLE BASED ACCESS CONTROL APIs ##################

# Role Template APIs
@router.post("/role-templates", response_model=RoleTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_role_template(
    role_template: RoleTemplateCreate,
    db: Session = Depends(get_db),
    current_user: str = "taadmin"
):
    """Create a new role template"""
    # Check if role name already exists
    existing_template = db.query(models.RoleTemplate).filter(
        models.RoleTemplate.role_name == role_template.role_name
    ).first()
    
    if existing_template:
        raise HTTPException(status_code=400, detail="Role template with this name already exists")
    
    db_role_template = models.RoleTemplate(
        **role_template.dict(),
        created_by=role_template.created_by or current_user or "taadmin"
    )
    db.add(db_role_template)
    db.commit()
    db.refresh(db_role_template)
    return db_role_template

@router.get("/role-templates", response_model=List[RoleTemplateResponse])
async def get_all_role_templates(db: Session = Depends(get_db)):
    """Get all role templates"""
    role_templates = db.query(models.RoleTemplate).all()
    return role_templates

@router.get("/role-templates/{template_id}", response_model=RoleTemplateResponse)
async def get_role_template(template_id: int = Path(..., gt=0), db: Session = Depends(get_db)):
    """Get a specific role template"""
    role_template = db.query(models.RoleTemplate).filter(
        models.RoleTemplate.id == template_id
    ).first()
    
    if not role_template:
        raise HTTPException(status_code=404, detail="Role template not found")
    
    return role_template

@router.put("/role-templates/{template_id}", response_model=RoleTemplateResponse)
async def update_role_template(
    template_id: int = Path(..., gt=0),
    role_template: RoleTemplateUpdate = Body(...),
    db: Session = Depends(get_db),
    current_user: str = "taadmin"
):
    """Update a role template"""
    db_role_template = db.query(models.RoleTemplate).filter(
        models.RoleTemplate.id == template_id
    ).first()
    
    if not db_role_template:
        raise HTTPException(status_code=404, detail="Role template not found")
    
    # Check if new role name conflicts with existing ones
    if role_template.role_name and role_template.role_name != db_role_template.role_name:
        existing_template = db.query(models.RoleTemplate).filter(
            models.RoleTemplate.role_name == role_template.role_name
        ).first()
        
        if existing_template:
            raise HTTPException(status_code=400, detail="Role template with this name already exists")
    
    # Update fields
    update_data = role_template.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_role_template, field, value)
    
    db_role_template.updated_by = current_user
    db_role_template.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(db_role_template)
    return db_role_template

@router.delete("/role-templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role_template(
    template_id: int = Path(..., gt=0),
    db: Session = Depends(get_db)
):
    """Delete a role template"""
    role_template = db.query(models.RoleTemplate).filter(
        models.RoleTemplate.id == template_id
    ).first()
    
    if not role_template:
        raise HTTPException(status_code=404, detail="Role template not found")
    
    # Check if template is being used
    users_with_template = db.query(models.UserRoleAccess).filter(
        models.UserRoleAccess.role_template_id == template_id
    ).first()
    
    if users_with_template:
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete template as it is being used by users"
        )
    
    db.delete(role_template)
    db.commit()
    return {"message": "Role template deleted successfully"}

# User Role Access APIs
@router.post("/user-role-access", response_model=UserRoleAccessResponse, status_code=status.HTTP_201_CREATED)
async def create_user_role_access(
    user_role_access: UserRoleAccessCreate,
    db: Session = Depends(get_db),
    current_user: str = "taadmin"
):
    """Create user role access (Step 4 - Final API call)"""
    try:
        logger.info(f"Creating user role access for user_id: {user_role_access.user_id}")
        logger.info(f"Request payload: {user_role_access.dict()}")
        
        # Check if user exists
        user = db.query(models.User).filter(models.User.id == user_role_access.user_id).first()
        if not user:
            logger.error(f"User not found with ID: {user_role_access.user_id}")
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if user already has role access
        existing_access = db.query(models.UserRoleAccess).filter(
            models.UserRoleAccess.user_id == user_role_access.user_id
        ).first()
        
        if existing_access:
            logger.error(f"User {user_role_access.user_id} already has role access")
            raise HTTPException(status_code=400, detail="User already has role access")
        
        # Calculate expiry date if duration is provided
        expiry_date = None
        if any([user_role_access.duration_days, user_role_access.duration_months, user_role_access.duration_years]):
            current_date = datetime.now(timezone.utc)
            if user_role_access.duration_years:
                current_date += timedelta(days=user_role_access.duration_years * 365)
            if user_role_access.duration_months:
                current_date += timedelta(days=user_role_access.duration_months * 30)
            if user_role_access.duration_days:
                current_date += timedelta(days=user_role_access.duration_days)
            expiry_date = current_date
        
        # Create user role access (avoid duplicate expiry_date key)
        payload_dict = user_role_access.dict(exclude={"expiry_date"})
        # Set created_by in payload_dict to avoid duplicate parameter
        payload_dict["created_by"] = user_role_access.created_by or current_user or "taadmin"
        # Remove permissions field if it exists (it's not part of the UserRoleAccess model)
        if "permissions" in payload_dict:
            del payload_dict["permissions"]
        
        # Ensure JSON fields are properly handled
        if "page_access" in payload_dict and payload_dict["page_access"] is None:
            payload_dict["page_access"] = {}
        if "subpage_access" in payload_dict and payload_dict["subpage_access"] is None:
            payload_dict["subpage_access"] = {}
        if "section_access" in payload_dict and payload_dict["section_access"] is None:
            payload_dict["section_access"] = {}
        
        logger.info(f"Creating UserRoleAccess with payload: {payload_dict}")
        logger.info(f"Expiry date: {expiry_date}")
        
        # Create the UserRoleAccess object with explicit field handling
        db_user_role_access = models.UserRoleAccess(
            user_id=payload_dict["user_id"],
            role_name=payload_dict["role_name"],
            is_super_admin=payload_dict.get("is_super_admin", False),
            duration_days=payload_dict.get("duration_days"),
            duration_months=payload_dict.get("duration_months"),
            duration_years=payload_dict.get("duration_years"),
            page_access=payload_dict.get("page_access", {}),
            subpage_access=payload_dict.get("subpage_access", {}),
            section_access=payload_dict.get("section_access", {}),
            allowed_job_ids=payload_dict.get("allowed_job_ids"),
            allowed_department_ids=payload_dict.get("allowed_department_ids"),
            allowed_candidate_ids=payload_dict.get("allowed_candidate_ids"),
            is_unrestricted=payload_dict.get("is_unrestricted", False),
            created_by=payload_dict["created_by"],
            expiry_date=expiry_date
        )
        
        logger.info("Adding to database...")
        db.add(db_user_role_access)
        
        logger.info("Committing to database...")
        db.commit()
        
        logger.info("Refreshing object...")
        db.refresh(db_user_role_access)
        
        logger.info(f"Successfully created user role access with ID: {db_user_role_access.id}")
        return db_user_role_access
        
    except Exception as e:
        logger.error(f"Error creating user role access: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error details: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        
        # Rollback the transaction
        db.rollback()
        
        # Re-raise the exception with more details
        raise HTTPException(
            status_code=500, 
            detail=f"Database error: {str(e)}"
        )

@router.get("/user-role-access/{access_id}", response_model=UserRoleAccessResponse)
async def get_user_role_access(access_id: int = Path(..., gt=0), db: Session = Depends(get_db)):
    """Get specific user role access by access ID (primary key)"""
    # Use primary key for faster query
    user_role_access = db.query(models.UserRoleAccess).filter(
        models.UserRoleAccess.id == access_id
    ).first()
    
    if not user_role_access:
        raise HTTPException(status_code=404, detail="User role access not found")
    
    return user_role_access

@router.get("/user-role-access/user/{user_id}", response_model=UserRoleAccessResponse)
async def get_user_role_access_by_user_id(user_id: int = Path(..., gt=0), db: Session = Depends(get_db)):
    """Get user role access by user ID with optimized query"""
    # Use join to get user information in a single query
    user_role_access = db.query(models.UserRoleAccess).join(
        models.User, models.UserRoleAccess.user_id == models.User.id
    ).filter(
        models.UserRoleAccess.user_id == user_id
    ).first()
    
    if not user_role_access:
        raise HTTPException(status_code=404, detail="User role access not found")
    
    return user_role_access

@router.put("/user-role-access/{access_id}", response_model=UserRoleAccessResponse)
async def update_user_role_access(
    access_id: int = Path(..., gt=0),
    user_role_access: UserRoleAccessUpdate = Body(...),
    db: Session = Depends(get_db),
    current_user: str = "taadmin"
):
    """Update user role access"""
    db_user_role_access = db.query(models.UserRoleAccess).filter(
        models.UserRoleAccess.id == access_id
    ).first()
    
    if not db_user_role_access:
        raise HTTPException(status_code=404, detail="User role access not found")
    
    # Calculate new expiry date if duration is updated
    if any([user_role_access.duration_days, user_role_access.duration_months, user_role_access.duration_years]):
        current_date = datetime.now(timezone.utc)
        if user_role_access.duration_years:
            current_date += timedelta(days=user_role_access.duration_years * 365)
        if user_role_access.duration_months:
            current_date += timedelta(days=user_role_access.duration_months * 30)
        if user_role_access.duration_days:
            current_date += timedelta(days=user_role_access.duration_days)
        user_role_access.expiry_date = current_date
    
    # Update fields
    update_data = user_role_access.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_user_role_access, field, value)
    
    db_user_role_access.updated_by = current_user
    db_user_role_access.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(db_user_role_access)
    return db_user_role_access

@router.delete("/user-role-access/{access_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_role_access(
    access_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    current_user: str = "taadmin"
):
    """Delete user role access with real-time notification"""
    logger.info(f"DELETE /user-role-access/{access_id} called by {current_user}")
    
    from app.routes.realtime_access_revoke import revoke_user_role_access, AccessRevocationPayload
    
    # Create revocation payload
    revocation_data = AccessRevocationPayload(
        user_id=0,  # Will be set by the revoke function
        revoked_by=current_user,
        revocation_reason="Access revoked by admin",
        revoked_at=datetime.now(timezone.utc),
        access_type="user_role_access"
    )
    
    logger.info(f"Calling revoke_user_role_access for access_id: {access_id}")
    
    # Use the real-time revocation function
    result = await revoke_user_role_access(
        access_id=access_id,
        revoked_by=current_user,
        revocation_reason="Access revoked by admin",
        db=db
    )
    
    logger.info(f"Revoke result - success: {result.success}, message: {result.message}, event_published: {result.event_published}")
    
    if result.success:
        return {"message": result.message, "event_published": result.event_published}
    else:
        logger.error(f"Failed to revoke access for access_id: {access_id}")
        raise HTTPException(status_code=500, detail="Failed to revoke access")

@router.get("/user-role-access/{access_id}/summary", response_model=UserAccessSummary)
async def get_user_access_summary(access_id: int = Path(..., gt=0), db: Session = Depends(get_db)):
    """Get summary of user's access permissions"""
    user_role_access = db.query(models.UserRoleAccess).filter(
        models.UserRoleAccess.id == access_id
    ).first()
    
    if not user_role_access:
        raise HTTPException(status_code=404, detail="User role access not found")
    
    # Calculate counts
    total_pages = len(user_role_access.page_access) if user_role_access.page_access else 0
    total_subpages = len(user_role_access.subpage_access) if user_role_access.subpage_access else 0
    total_sections = len(user_role_access.section_access) if user_role_access.section_access else 0
    allowed_jobs_count = len(user_role_access.allowed_job_ids) if user_role_access.allowed_job_ids else 0
    allowed_departments_count = len(user_role_access.allowed_department_ids) if user_role_access.allowed_department_ids else 0
    allowed_candidates_count = len(user_role_access.allowed_candidate_ids) if user_role_access.allowed_candidate_ids else 0
    
    return {
        "user_id": user_role_access.user_id,
        "role_name": user_role_access.role_name,
        "is_super_admin": user_role_access.is_super_admin,
        "expiry_date": user_role_access.expiry_date,
        "total_pages": total_pages,
        "total_subpages": total_subpages,
        "total_sections": total_sections,
        "allowed_jobs_count": allowed_jobs_count,
        "allowed_departments_count": allowed_departments_count,
        "allowed_candidates_count": allowed_candidates_count,
        "is_unrestricted": user_role_access.is_unrestricted
    }

@router.get("/user-role-access/{access_id}/details", response_model=RoleAccessDetails)
async def get_user_access_details(access_id: int = Path(..., gt=0), db: Session = Depends(get_db)):
    """Get detailed access permissions for a user"""
    user_role_access = db.query(models.UserRoleAccess).filter(
        models.UserRoleAccess.id == access_id
    ).first()
    
    if not user_role_access:
        raise HTTPException(status_code=404, detail="User role access not found")
    
    # Convert JSON data to response objects
    page_access_list = []
    if user_role_access.page_access:
        for page_name, permissions in user_role_access.page_access.items():
            page_access_list.append({
                "id": 0,  # Placeholder since this is from JSON
                "page_name": page_name,
                "can_view": permissions.get("can_view", False),
                "can_edit": permissions.get("can_edit", False),
                "created_at": None,
                "updated_at": None,
                "created_by": None,
                "updated_by": None
            })
    
    subpage_access_list = []
    if user_role_access.subpage_access:
        for subpage_name, permissions in user_role_access.subpage_access.items():
            subpage_access_list.append({
                "id": 0,  # Placeholder since this is from JSON
                "subpage_name": subpage_name,
                "can_view": permissions.get("can_view", False),
                "can_edit": permissions.get("can_edit", False),
                "created_at": None,
                "updated_at": None,
                "created_by": None,
                "updated_by": None
            })
    
    section_access_list = []
    if user_role_access.section_access:
        for section_name, permissions in user_role_access.section_access.items():
            section_access_list.append({
                "id": 0,  # Placeholder since this is from JSON
                "section_name": section_name,
                "can_view": permissions.get("can_view", False),
                "can_edit": permissions.get("can_edit", False),
                "created_at": None,
                "updated_at": None,
                "created_by": None,
                "updated_by": None
            })
    
    return {
        "user_id": user_role_access.user_id,
        "role_name": user_role_access.role_name,
        "is_super_admin": user_role_access.is_super_admin,
        "expiry_date": user_role_access.expiry_date,
        "page_access": page_access_list,
        "subpage_access": subpage_access_list,
        "section_access": section_access_list,
        "allowed_job_ids": user_role_access.allowed_job_ids or [],
        "allowed_department_ids": user_role_access.allowed_department_ids or [],
        "allowed_candidate_ids": user_role_access.allowed_candidate_ids or [],
        "is_unrestricted": user_role_access.is_unrestricted
    }

# Page Access APIs
@router.post("/page-access", response_model=PageAccessResponse, status_code=status.HTTP_201_CREATED)
async def create_page_access(
    page_access: PageAccessCreate,
    db: Session = Depends(get_db),
    current_user: str = "taadmin"
):
    """Create page access permission"""
    db_page_access = models.PageAccess(
        **page_access.dict(),
        created_by=page_access.created_by or current_user or "taadmin"
    )
    db.add(db_page_access)
    db.commit()
    db.refresh(db_page_access)
    return db_page_access

@router.get("/page-access", response_model=List[PageAccessResponse])
async def get_all_page_access(db: Session = Depends(get_db)):
    """Get all page access permissions"""
    page_access_list = db.query(models.PageAccess).all()
    return page_access_list

# Subpage Access APIs
@router.post("/subpage-access", response_model=SubpageAccessResponse, status_code=status.HTTP_201_CREATED)
async def create_subpage_access(
    subpage_access: SubpageAccessCreate,
    db: Session = Depends(get_db),
    current_user: str = "taadmin"
):
    """Create subpage access permission"""
    db_subpage_access = models.SubpageAccess(
        **subpage_access.dict(),
        created_by=subpage_access.created_by or current_user or "taadmin"
    )
    db.add(db_subpage_access)
    db.commit()
    db.refresh(db_subpage_access)
    return db_subpage_access

@router.get("/subpage-access", response_model=List[SubpageAccessResponse])
async def get_all_subpage_access(db: Session = Depends(get_db)):
    """Get all subpage access permissions"""
    subpage_access_list = db.query(models.SubpageAccess).all()
    return subpage_access_list

# Section Access APIs
@router.post("/section-access", response_model=SectionAccessResponse, status_code=status.HTTP_201_CREATED)
async def create_section_access(
    section_access: SectionAccessCreate,
    db: Session = Depends(get_db),
    current_user: str = "taadmin"
):
    """Create section access permission"""
    db_section_access = models.SectionAccess(
        **section_access.dict(),
        created_by=section_access.created_by or current_user or "taadmin"
    )
    db.add(db_section_access)
    db.commit()
    db.refresh(db_section_access)
    return db_section_access

@router.get("/section-access", response_model=List[SectionAccessResponse])
async def get_all_section_access(db: Session = Depends(get_db)):
    """Get all section access permissions"""
    section_access_list = db.query(models.SectionAccess).all()
    return section_access_list

# Utility APIs for frontend
@router.get("/available-pages", response_model=List[str])
async def get_available_pages():
    """Get list of available pages in the system"""
    return [
        "dashboard",
        "candidates",
        "jobs",
        "departments",
        "reports",
        "settings",
        "user-management",
        "role-management"
    ]

@router.get("/available-subpages", response_model=List[str])
async def get_available_subpages():
    """Get list of available subpages in the system"""
    return [
        "candidate-list",
        "candidate-details",
        "candidate-create",
        "candidate-edit",
        "job-list",
        "job-details",
        "job-create",
        "job-edit",
        "department-list",
        "department-details",
        "user-list",
        "user-details",
        "role-list",
        "role-details"
    ]

@router.get("/available-sections", response_model=List[str])
async def get_available_sections():
    """Get list of available sections in the system"""
    return [
        "personal-info",
        "contact-info",
        "work-experience",
        "education",
        "skills",
        "interviews",
        "offer-details",
        "documents",
        "notes",
        "timeline"
    ]

@router.get("/referred-by-list", response_model=list)
def get_referred_by_list(db: Session = Depends(get_db)):
    """
    Returns a list of unique non-null values for the referred_by field from all candidates, sorted alphabetically.
    """
    referred_by_values = db.query(Candidate.referred_by).distinct().all()
    # Flatten and filter out None/empty values
    unique_values = []
    for val in referred_by_values:
        # Extract the actual value from the row object
        actual_val = val[0]  # SQLAlchemy returns a Row object, access first element
        # Only add non-null, non-empty values
        if actual_val is not None and str(actual_val).strip():
            unique_values.append(actual_val)
    
    return sorted(unique_values)

@router.delete("/user-role-access/{access_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_role_access(
    access_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    current_user: str = "taadmin"
):
    """Delete user role access with real-time notification"""
    logger.info(f"DELETE /user-role-access/{access_id} called by {current_user}")
    
    from app.routes.realtime_access_revoke import revoke_user_role_access, AccessRevocationPayload
    
    # Create revocation payload
    revocation_data = AccessRevocationPayload(
        user_id=0,  # Will be set by the revoke function
        revoked_by=current_user,
        revocation_reason="Access revoked by admin",
        revoked_at=datetime.now(timezone.utc),
        access_type="user_role_access"
    )
    
    logger.info(f"Calling revoke_user_role_access for access_id: {access_id}")
    
    try:
        # Use the real-time revocation function
        result = await revoke_user_role_access(
            access_id=access_id,
            revoked_by=current_user,
            revocation_reason="Access revoked by admin",
            db=db
        )
        
        logger.info(f"Revoke result - success: {result.success}, message: {result.message}, event_published: {result.event_published}")
        
        if result.success:
            return {"message": result.message, "event_published": result.event_published}
        else:
            logger.error(f"Failed to revoke access for access_id: {access_id}")
            raise HTTPException(status_code=500, detail="Failed to revoke access")
            
    except HTTPException as http_error:
        # Re-raise HTTPException without wrapping it in a 500 error
        logger.info(f"HTTPException in delete_user_role_access: {http_error.status_code} - {http_error.detail}")
        raise

@router.delete("/user-role-access/by-email/{email}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_role_access_by_email(
    email: str = Path(..., description="Email of the user whose role access should be deleted"),
    db: Session = Depends(get_db),
    current_user: str = "taadmin"
):
    """Delete user role access and user from both tables by email with real-time notification"""
    logger.info(f"DELETE /user-role-access/by-email/{email} called by {current_user}")
    
    from app.routes.realtime_access_revoke import revoke_user_role_access_by_email
    
    try:
        # Use the real-time revocation function for email-based deletion
        result = await revoke_user_role_access_by_email(
            email=email,
            revoked_by=current_user,
            revocation_reason="Access revoked by admin",
            db=db
        )
        
        logger.info(f"Revoke result - success: {result.success}, message: {result.message}, event_published: {result.event_published}")
        
        if result.success:
            return {"message": result.message, "event_published": result.event_published}
        else:
            logger.error(f"Failed to revoke access for email: {email}")
            raise HTTPException(status_code=500, detail="Failed to revoke access")
            
    except HTTPException as http_error:
        # Re-raise HTTPException without wrapping it in a 500 error
        logger.info(f"HTTPException in delete_user_role_access_by_email: {http_error.status_code} - {http_error.detail}")
        raise

@router.delete("/user-role-access/by-emails/{emails}", status_code=status.HTTP_200_OK)
async def delete_multiple_user_role_access_by_email(
    emails: str = Path(..., description="Comma-separated emails of users whose role access should be deleted"),
    db: Session = Depends(get_db),
    current_user: str = "taadmin"
):
    """Delete multiple user role accesses and users from both tables by comma-separated emails with real-time notification"""
    logger.info(f"DELETE /user-role-access/by-emails/{emails} called by {current_user}")
    
    # Parse comma-separated emails
    email_list = [email.strip() for email in emails.split(',') if email.strip()]
    
    if not email_list:
        raise HTTPException(status_code=400, detail="At least one valid email is required")
    
    logger.info(f"Processing {len(email_list)} emails: {email_list}")
    
    from app.routes.realtime_access_revoke import revoke_multiple_user_role_access_by_email
    
    try:
        # Use the real-time revocation function for bulk email-based deletion
        result = await revoke_multiple_user_role_access_by_email(
            emails=email_list,
            revoked_by=current_user,
            revocation_reason="Access revoked by admin",
            db=db
        )
        
        logger.info(f"Bulk revoke result - success: {result['success']}, successful: {result['successful_deletions']}, failed: {result['failed_deletions']}")
        
        return result
        
    except HTTPException as http_error:
        # Re-raise HTTPException without wrapping it in a 500 error
        logger.info(f"HTTPException in delete_multiple_user_role_access_by_email: {http_error.status_code} - {http_error.detail}")
        raise
