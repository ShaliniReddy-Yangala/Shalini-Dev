# Pydantic models for API schemas
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, Optional, List, Union
import re
from fastapi import File, UploadFile
from pydantic import BaseModel, EmailStr, Field, field_validator,validator
from dateutil.parser import parse as parse_date



class FilterOptionValues(BaseModel):
    values: list

    class Config:
        from_attributes = True

class FilterOptionsResponse(BaseModel):
    current_status: FilterOptionValues
    final_status: FilterOptionValues
    department: FilterOptionValues
    interview_status: FilterOptionValues
    open_jobs: FilterOptionValues
    ratings: FilterOptionValues
    ta_team_members: FilterOptionValues
    referred_by: FilterOptionValues
    created_by: FilterOptionValues
    updated_by: FilterOptionValues

    class Config:
        from_attributes = True

class JobCreate(BaseModel):
    job_title: str
    no_of_positions: int
    requisition_type:str
    employee_to_be_replaced: Optional[str] = None
    job_type: str
    skill_set: Optional[str] = None
    department: str
    required_experience_min: int
    required_experience_max: int
    ctc_budget_min: Optional[int] = None
    ctc_budget_max: Optional[int] = None
    target_hiring_date: Optional[str] = None
    priority: str
    office_location: Optional[str] = "Hyderabad"
    additional_notes: Optional[str] = None
    job_description: str
    mode_of_work: str
    client_name: Optional[str] = None
    head_of_department: str
    # reason_for_hiring: Optional[str] = None
    created_by: Optional[str] = None
    created_on: Optional[str] = None
    created_by: Optional[str] = None
    created_on: Optional[str] = None
    status: str = "OPEN"
    

class JobUpdate(BaseModel):
    job_title: Optional[str] = None
    no_of_positions: Optional[int] = None
    requisition_type: Optional[str] = None
    employee_to_be_replaced: Optional[str] = None
    job_type: Optional[str] = None
    skill_set: Optional[str] = None
    department: Optional[str] = None
    required_experience_min: Optional[int] = None
    required_experience_max: Optional[int] = None
    ctc_budget_min: Optional[int] = None
    ctc_budget_max: Optional[int] = None
    target_hiring_date: Optional[str] = None
    priority:Optional[str] = None
    office_location: Optional[str] = None
    additional_notes: Optional[str] = None
    job_description: Optional[str] = None
    mode_of_work: Optional[str] = None
    client_name: Optional[str] = None
    head_of_department: Optional[str] = None
    status: Optional[str] = None
    updated_by: Optional[str] = None 
    updated_on: Optional[str] = None
    updated_by: Optional[str] = None 
    updated_on: Optional[str] = None
    # reason_for_hiring: Optional[str] = None

class JobResponse(BaseModel):
    id: int
    job_id: str
    job_title: str
    no_of_positions: int
    requisition_type: str
    employee_to_be_replaced: Optional[str] = None
    job_type: str
    skill_set: Optional[str] = None
    department: str
    required_experience_min: int
    required_experience_max: int
    ctc_budget_min: Optional[int] = None
    ctc_budget_max: Optional[int] = None
    mode_of_work: str
    office_location: str
    job_description: Optional[str] = None
    target_hiring_date: Optional[str] = None
    priority: str
    client_name: Optional[str] = None
    head_of_department: str
    # date_of_request: Optional[str] = None
    status: str
    created_on: Optional[str] = None
    created_by: Optional[str] = None
    updated_on: Optional[str] = None
    updated_by: Optional[str] = None
    created_by: Optional[str] = None
    updated_on: Optional[str] = None
    updated_by: Optional[str] = None
    # reason_for_hiring: Optional[str] = None
    additional_notes: Optional[str] = None

    class Config:
        from_attributes = True 

class JobListResponse(BaseModel):
    id: int
    job_id: str
    job_title: str
    no_of_positions: int
    requisition_type: str
    employee_to_be_replaced: Optional[str] = None
    job_type: str
    primary_skills: Optional[str] = None
    secondary_skills: Optional[str] = None
    department: str
    required_experience_min: int
    required_experience_max: int
    mode_of_work: str
    office_location: str
    status: str
    created_on: Optional[str] = None
    updated_on: Optional[str] = None  # New field
    updated_by: Optional[str] = None  # New fiel
    target_hiring_date: Optional[str] = None
    priority: Optional[str] = None

    class Config:
        from_attributes = True  

############## notification ############

class NotificationBase(BaseModel):
    user_id: str
    notification_type: str
    title: str
    message: str
    link: Optional[str] = None
    job_id: Optional[str] = None
    candidate_id: Optional[str] = None

class NotificationCreate(NotificationBase):
    pass

class NotificationResponse(NotificationBase):
    id: int
    is_read: bool
    created_on: datetime
    updated_on: Optional[datetime] = None

    class Config:
        from_attributes = True 

class NotificationList(BaseModel):
    items: List[NotificationResponse]
    unread_count: int


############################## Roles and Permissions ###############################

class RoleBase(BaseModel):
    name: str  
    description: Optional[str] = None

class RoleCreate(RoleBase):
    pass

class RoleResponse(RoleBase):
    id: int

    class Config:
        from_attributes = True  

# User role schemas
class UserRoleBase(BaseModel):
    role_id: int
    department: Optional[str] = None
    job_ids: Optional[List[str]] = None
    is_unrestricted: bool = False
    duration_days: Optional[int] = None
    duration_months: Optional[int] = None
    duration_years: Optional[int] = None


class UserRoleCreate(UserRoleBase):
    user_id: Optional[int] = None
    email: Optional[str] = None


class UserRoleUpdate(BaseModel):
    role_id: Optional[int] = None
    department: Optional[str] = None
    job_ids: Optional[List[str]] = None
    is_unrestricted: Optional[bool] = None
    duration_days: Optional[int] = None
    duration_months: Optional[int] = None
    duration_years: Optional[int] = None


class UserRoleResponse(BaseModel):
    id: int
    name: str
    email: str
    department: str
    role: str  
    selectedJobs: str
    duration: str

    class Config:
        from_attributes = True 

############################ Documents upload

class UploadRequest(BaseModel):
    candidate_id: str
    document_type: str
    file_name: str
    content_type: str
    
class DocumentResponse(BaseModel):
    id: str
    documentType: str
    filename: str
    candidateId: str
    uploadedAt: datetime
    downloadUrl: str
    
class PresignedURLResponse(BaseModel):
    uploadUrl: str
    documentId: str
    documentType: str
    expiresIn: int
    
class ShareableLinkResponse(BaseModel):
    shareableLink: str
    candidateId: str
    expiresIn: int
    createdAt: datetime

##################Candidtae #####################

class OfferDetails(BaseModel):
    id: Optional[int] = None
    candidate_id: int
    job_id: Optional[int] = None
    salary: float
    start_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    status: str
    additional_benefits: Optional[List[str]] = None
    
    class Config:
        from_attributes = True  

class SalaryComponent(BaseModel):
    basic_salary: float
    house_rent_allowance: float
    special_allowance: float
    bonus: float
    conveyance: float
    gross_salary: float
    employer_provident_fund: float
    total_cost_to_company: float

class CTCBreakupCreate(BaseModel):
    candidate_id: str
    candidate_name: str
    designation: str
    ctc: float
    salary_components: dict
    ctc_email_status: Optional[str] = "not_sent"
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    

    class Config:
        from_attributes = True 

class CTCBreakupResponse(BaseModel):
    id: Optional[int] = None
    candidate_id: str
    candidate_name: str
    designation: str
    ctc: float
    salary_components: dict
    ctc_email_status: Optional[str] = "not_sent"
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_at: Optional[date] = None
    updated_at: Optional[date] = None

    # Add validators to handle datetime to date conversion
    @field_validator('created_at', 'updated_at', mode='before')
    @classmethod
    def convert_datetime_to_date(cls, v):
        if isinstance(v, datetime):
            return v.date()
        return v

    class Config:
        from_attributes = True


class CTCStatusResponse(BaseModel):
    candidate_id: str
    status: str
    
    class Config:
        from_attributes = True

class CTCStatusCreate(BaseModel):
    candidate_id: str
    status: str    
    
# PAN Card validation function
def validate_pan_card(pan_card: str) -> bool:
    """
    Validate PAN card format: 5 letters, 4 digits, 1 letter (e.g., ABCDE1234F)
    """
    if not pan_card:
        return True  # Optional field
    
    pan_pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$'
    return bool(re.match(pan_pattern, pan_card.upper()))

class CandidateBase(BaseModel):
    candidate_name: str
    email_id: str
    mobile_no: Optional[str] = None
    pan_card_no: Optional[str] = Field(None, max_length=10)
    linkedin_url: Optional[str] = None
    associated_job_id: Optional[str] = None
    skills_set: Union[List[str], str] = []  
    resume_path: Optional[str] = None
    resume_url: Optional[str] = None
    application_date: datetime = None
    date_of_resume_received: Optional[date] = None
    status: Optional[str] = None  
    current_status: Optional[str] = None
    final_status: Optional[str] = None
    department : Optional[str] = None
    gender : Optional[str] = None
    referred_by: Optional[str] = None  # <-- Added field
    # L1 interview fields
    l1_interview_date: Optional[date] = None
    l1_interviewers_name: Optional[str] = None
    l1_status: Optional[str] = None
    l1_feedback: Optional[str] = None
    # L2 interview fields
    l2_interview_date: Optional[date] = None
    l2_interviewers_name: Optional[str] = None
    l2_status: Optional[str] = None
    l2_feedback: Optional[str] = None
    # HR interview fields
    hr_interview_date: Optional[date] = None
    hr_interviewer_name: Optional[str] = None
    hr_status: Optional[str] = None
    hr_feedback: Optional[str] = None
    # Offer details
    offer_ctc: Optional[float] = None
    offer_date: Optional[date] = None
    offer_status: Optional[ str] = None
    date_of_joining: Optional[date] = None
    # Additional fields
    current_designation: Optional[str] = None
    current_company: Optional[str] = None
    current_fixed_ctc: Optional[float] = None
    current_variable_ctc: Optional[float] = None
    years_of_exp: Optional[float] = None
    mode_of_work: Optional[str] = None
    expected_fixed_ctc: Optional[float] = None
    npd_info: Optional[str] = None
    notice_period: Optional[int] = None
    status_updated_on: Optional[date] = None
    job: Optional[JobResponse] = None
    rating: Optional[str] = None
    current_location: Optional[str] = None
    current_address: Optional[str] = None
    permanent_address: Optional[str] = None
    created_by: Optional[str] = "system"


    @field_validator('skills_set', mode='before')
    @classmethod
    def parse_skills_set(cls, value):
        if isinstance(value, str) and value:
            # Handle curly braces format: {skill, skill 2} -> skill, skill 2
            if value.startswith('{') and value.endswith('}'):
                # Remove curly braces and process as comma-separated string
                value = value[1:-1].strip()
            return [skill.strip() for skill in value.split(',') if skill.strip()]
        elif isinstance(value, list):
            return value
        return []

    @field_validator('current_status', mode='before')
    @classmethod
    def parse_current_status(cls, value):
        if value is None:
            return "Screening"  
        return str(value)

    @field_validator('final_status', mode='before')
    @classmethod
    def parse_final_status(cls, value):
        if value is None:
                return "IN_PROGRESS"
        return str(value)

    @field_validator('offer_status', mode='before')
    @classmethod
    def parse_offer_status(cls, value):
        if value is None:
            return None
        return str(value)

    class Config:
        from_attributes = True  

class CandidateCreate(BaseModel):
    candidate_name: str
    email_id: str
    mobile_no: Optional[str] = None
    pan_card_no: Optional[str] = Field(None, max_length=10)
    associated_job_id: Optional[str] = None
    skills_set: Optional[List[str]] = None
    resume_path: Optional[str] = None
    resume_url: Optional[str] = None
    application_date: datetime = None
    date_of_resume_received: Optional[date] = None
    status: Optional[str] = None
    current_status: Optional[str] = None
    final_status: Optional[str] = None
    rating: Optional[str] = None
    linkedin_url: Optional[str] = None
    department : Optional[str] = None
    gender : Optional[str] = None
    referred_by: Optional[str] = None  # <-- Added field
    expected_date_of_joining: Optional[str] = None
    
    # Other optional fields
    current_designation: Optional[str] = None
    current_company: Optional[str] = None
    current_fixed_ctc: Optional[float] = None
    current_variable_ctc: Optional[float] = None
    years_of_exp: Optional[float] = None
    mode_of_work: Optional[str] = None
    expected_ctc: Optional[float] = None
    notice_period: Optional[int] = None

    additional_info: Optional[str] = None
    current_fixed_ctc: Optional[float] = None
    current_variable_pay: Optional[float] = None
    expected_fixed_ctc: Optional[float] = None
    mode_of_work: Optional[str] = None
    reason_for_change: Optional[str] = None
    ta_team: Optional[str] = None
    ta_comments: Optional[str] = None
    l1_interview_date: Optional[date] = None
    l1_interviewers_name: Optional[str] = None
    l1_status: Optional[str] = None
    l1_feedback: Optional[str] = None
    l2_interview_date: Optional[date] = None
    l2_interviewers_name: Optional[str] = None
    l2_status: Optional[str] = None
    l2_feedback: Optional[str] = None
    hr_interview_date: Optional[date] = None
    hr_interviewer_name: Optional[str] = None
    hr_status: Optional[str] = None
    offer_ctc: Optional[float] = None
    hr_feedback: Optional[str] = None
    offered_designation: Optional[str] = None
    reason_for_change: Optional[str] = None
    current_location: Optional[str] = None
    current_address: Optional[str] = None
    permanent_address: Optional[str] = None
    date_of_joining: Optional[str] = None
    created_by: Optional[str] = "system"
    
 
    class Config:
        from_attributes = True 
@validator('pan_card_no')
def validate_pan_format(cls, v):
        if v and not validate_pan_card(v):
            raise ValueError('Invalid PAN card format. Must be in format: ABCDE1234F')
        return v.upper() if v else v
class CandidateResponse(CandidateBase):
    candidate_id: str
    pan_card_no: Optional[str] = None
    reason_for_job_change: Optional[str] = None
    ta_team: Optional[str] = None
    ta_team_member: Optional[str] = None
    ta_comments:Optional[str]=None
    current_address: Optional[str] = None
    permanent_address: Optional[str] = None
    current_location: Optional[str] = None
    date_of_joining : Optional[str]=None
    application_date: Optional[datetime] = None
    final_status: Optional[str] = None
    department: Optional[str] = None
    current_status: Optional[str] = None
    current_variable_pay: Optional[float] = None
    npd_info: Optional[str] = None
    updated_by: Optional[str] = "taadmin"
    created_by: Optional[str] = "taadmin"
    updated_at: Optional[datetime] = None
    created_at: Optional[datetime] = None 
    rejected_date: Optional[datetime] = None
    final_offer_ctc: Optional[float] = None
    referred_by: Optional[str] = None  # <-- Added field

    
    
    
    
    class Config:
        from_attributes = True
        allow_population_by_field_name = True
        

class CandidateFilter(BaseModel):
    page: int = 1
    items_per_page: int = 10
    search: Optional[str] = None
    job_filter: Optional[str] = None
    rating_filter: Optional[str] = None
    status_filter: Optional[str] = None  # For interview_progress_status
    current_status_filter: Optional[str] = None
    final_status_filter: Optional[str] = None
    skill_filter: Optional[str] = None
    ctc_filter: Optional[str] = None
    experience_filter: Optional[str] = None
    department_filter: Optional[str] = None
    ta_team_filter: Optional[str] = None
    notice_period_filter: Optional[str] = None
    sort_key: Optional[str] = None
    sort_order: Optional[str] = "asc"        


class PaginatedCandidateResponse(BaseModel):
    total: int
    page: int
    items_per_page: int
    items: List[CandidateResponse]
    role: Optional[str] = None
    explanation: Optional[str] = None


@validator('pan_card_no')
def validate_pan_format(cls, v):
        if v and not validate_pan_card(v):
            raise ValueError('Invalid PAN card format. Must be in format: ABCDE1234F')
        return v.upper() if v else v

class CandidateUpdate(BaseModel):
    candidate_name: Optional[str] = None
    email_id: Optional[str] = None
    mobile_no: Optional[str] = None
    pan_card_no: Optional[str] = Field(None, max_length=10)
    associated_job_id: Optional[str] = None
    skills_set: Optional[List[str]] = None
    current_designation: Optional[str] = None
    current_company: Optional[str] = None
    application_date: Optional[date] = None
    date_of_resume_received: Optional[date] = None
    current_fixed_ctc: Optional[float] = None
    current_variable_pay: Optional[float] = None
    years_of_exp: Optional[float] = None
    mode_of_work: Optional[str] = None
    gender : Optional[str] = None
    expected_ctc: Optional[float] = None
    expected_fixed_ctc:Optional[float] =None
    notice_period: Optional[int] = None
    notice_period_units: Optional[str] = None
    npd_info: Optional[str] = None
    status: Optional[str] = None
    current_status: Optional[str] = None
    final_status: Optional[str] = None
    reason_for_job_change: Optional[str] = None
    ta_team: Optional[str] = None
    ta_comments: Optional[str] = None
    rating: Optional[str] = None
    linkedin_url: Optional[str] = None
    current_address: Optional[str] = None
    permanent_address: Optional[str] = None
    current_location: Optional[str] = None
    department: Optional[str] = None
    date_of_joining: Optional[date] = None
    rejected_date: Optional[datetime] = None
    referred_by: Optional[str] = None  # <-- Added field
    updated_by: str  # Required field from frontend
    updated_at: datetime  # Required field from frontend
    class Config:
        from_attributes = True

class StatusUpdate(BaseModel):
    status: str


class ProgressUpdate(BaseModel):

    new_status: str


class InterviewUpdate(BaseModel):
    interview_date: Optional[date] = None
    interviewer_name: Optional[str] = None
    status: Optional[str] = None
    feedback: Optional[str] = None
    final_offer_ctc: Optional[float] = None
    updated_by: str  # Required field from frontend
    updated_at: datetime  # Required field from frontend

class CandidateListItem(BaseModel):
    candidate_id: str
    candidate_name: str
    position: Optional[str] = None
    location: Optional[str] = None
    company: Optional[str] = None
    rating: Optional[str] = None
    applied: Optional[date] = None
    job_title: Optional[str]

class CandidateRatingUpdate(BaseModel):
    rating: str
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None

###################Discussion Question

class DiscussionQuestionBase(BaseModel):
    questions_content: Optional[str] = None

class DiscussionQuestionCreate(DiscussionQuestionBase):
    pass

class DiscussionQuestionUpdate(DiscussionQuestionBase):
    pass

class DiscussionQuestionResponse(DiscussionQuestionBase):
    id: int
    discussion_id: Optional[int] = None
    round_name: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class DiscussionBase(BaseModel):
    done_by: Optional[str] = None  
    feedback: Optional[str] = None
    decision: Optional[str] = None
    updated_by: str  # From frontend
    updated_at: datetime  # From frontend (UTC datetime)
    
    @validator("done_by", pre=True)
    def validate_done_by(cls, value):
        if value is None:
            return value
        if not isinstance(value, str):
            raise ValueError("done_by must be a string")
        # Allow formats like "Name (Team Name)"
        if not value.strip():  # Ensure it's not an empty string
            raise ValueError("done_by cannot be empty")
        return value


class DiscussionCreate(DiscussionBase):
    pass


class DiscussionResponse(DiscussionBase):
    id: int
    candidate_id: str
    level: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = "taadmin"
    questions: Dict[str, DiscussionQuestionResponse] = {}

    class Config:
        from_attributes = True  


class DiscussionSavePayload(BaseModel):
    candidateId: str
    discussions: Dict[str, DiscussionCreate]


class CandidateDiscussionResponse(BaseModel):
    candidateId: str
    discussions: Dict[str, DiscussionResponse]
    
    

class RejectOfferRequest(BaseModel):
    rejection_reason: Optional[str] = None


class ExcelUploadResponse(BaseModel):
    job_id: str
    message: str

class ExcelUploadStatusResponse(BaseModel):
    status: str
    total: Optional[int] = None
    successful: Optional[int] = None
    failed: Optional[int] = None
    errors: Optional[List[Dict[str, str]]] = None
    message: Optional[str] = None
    error: Optional[str] = None

class CandidateBulkCreateResponse(BaseModel):
    success_count: int
    failed_count: int
    failed_items: List[Dict]


class CandidateSingleEntry(BaseModel):
    candidate_name: str
    email_id: Optional[str] = None
    mobile_no: Optional[str] = None
    pan_card_no: Optional[str] = Field(None, max_length=10)
    date_of_resume_received: Optional[str] = None
    associated_job_id: Optional[str] = None
    application_date: Optional[datetime] = None
    linkedin_url: Optional[str] = None
    skills_set: Optional[Union[str, List[str]]] = None  # Accept string or list
    current_company: Optional[str] = None
    department: Optional[str] = None
    current_designation: Optional[str] = None
    years_of_exp: Optional[float] = None
    current_status: Optional[str] = None
    final_status: Optional[str] = None
    gender : Optional[str] = None
    notice_period: Optional[Union[int, str]] = None
    notice_period_unit: Optional[str] = None
    ctc: Optional[str] = None
    current_location: Optional[str] = None
    current_address: Optional[str] = None
    permanent_address: Optional[str] = None
    npd_info: Optional[str] = None
    current_fixed_ctc: Optional[float] = None
    current_variable_pay: Optional[float] = None
    expected_fixed_ctc: Optional[float] = None
    mode_of_work: Optional[str] = None
    reason_for_job_change: Optional[str] = None
    ta_team: Optional[str] = None
    ta_comments: Optional[str] = None
    l1_interview_date: Optional[str] = None
    l1_interviewers_name: Optional[str] = None
    l1_status: Optional[str] = None
    l1_feedback: Optional[str] = None
    l2_interview_date: Optional[str] = None
    l2_interviewers_name: Optional[str] = None
    l2_status: Optional[str] = None
    l2_feedback: Optional[str] = None
    hr_interview_date: Optional[str] = None
    hr_interviewer_name: Optional[str] = None
    hr_status: Optional[str] = None
    final_offer_ctc: Optional[float] = None
    hr_feedback: Optional[str] = None
    designation: Optional[str] = None
    resume_url: Optional[str] = None
    offer_letter: Optional[str] = None
    discussion1_date: Optional[str] = None
    discussion1_notes: Optional[str] = None
    discussion1_done_by: Optional[str] = None
    discussion2_date: Optional[str] = None
    discussion2_notes: Optional[str] = None
    discussion2_done_by: Optional[str] = None
    discussion3_date: Optional[str] = None
    discussion3_notes: Optional[str] = None
    discussion3_done_by: Optional[str] = None
    discussion4_date: Optional[str] = None
    discussion4_notes: Optional[str] = None
    discussion4_done_by: Optional[str] = None
    discussion5_date: Optional[str] = None
    discussion5_notes: Optional[str] = None
    discussion5_done_by: Optional[str] = None
    discussion6_date: Optional[str] = None
    discussion6_notes: Optional[str] = None
    discussion6_done_by: Optional[str] = None
    expected_date_of_joining: Optional[str] = None
    created_by: Optional[str] =None
    created_at: Optional[datetime] = None
    ctc_breakup_status: Optional[str] = None
    ctc_offer_status: Optional[str] = None

    @validator("skills_set", pre=True)
    def convert_skills_set(cls, value):
        if isinstance(value, list):
            return ", ".join(value) if value else None
        elif isinstance(value, str) and value:
            # Handle curly braces format: {skill, skill 2} -> skill, skill 2
            if value.startswith('{') and value.endswith('}'):
                # Remove curly braces and process as comma-separated string
                value = value[1:-1].strip()
                # Clean up and return as comma-separated string
                skills = [skill.strip() for skill in value.split(",") if skill.strip()]
                return ", ".join(skills) if skills else None
        return value

    class Config:
        from_attributes = True

class FinalStatusUpdate(BaseModel):
    final_status: str


    class Config:
        from_attributes = True  
############################# DASH BOARD ##############

class JobStatistics(BaseModel):
    totalJobs: int
    openJobs: int
    closedJobs: int
    ta1CreatedJobs: int
    ta2CreatedJobs: int
    
class JobTrendEntry(BaseModel):
    month: str
    jobs: int

class JobTrend(BaseModel):
    monthlyJobTrend: List[JobTrendEntry]

class JobTypeDistribution(BaseModel):
    type: str
    count: int

class JobTypeDistributionList(BaseModel):
    jobTypes: List[JobTypeDistribution]

class PriorityDistribution(BaseModel):
    priority: str 
    count: int

class PriorityDistributionList(BaseModel):
    priorityDistribution: List[PriorityDistribution]

class CandidateStatistics(BaseModel):
    screening: int
    scheduled: int
    onboarding: int
    discussions: int
    onboarded: int

class PipelineFlowEntry(BaseModel):
    stage: str
    count: int

class PipelineFlow(BaseModel):
    pipelineFlow: List[PipelineFlowEntry]

class SkillEntry(BaseModel):
    skill: str
    count: int

class SkillsList(BaseModel):
    candidatesBySkill: List[SkillEntry]

class MonthlyHireEntry(BaseModel):
    month: str
    hires: int

class MonthlyHires(BaseModel):
    monthlyHires: List[MonthlyHireEntry]

class TAPerformanceEntry(BaseModel):
    month: str
    sourced: int
    hired: int

class TAPerformance(BaseModel):
    monthlyPerformance: List[TAPerformanceEntry]

class TAMetrics(BaseModel):
    jobsCreated: int
    candidatesSourced: int
    candidatesInScreening: int
    offersReleased: int
    candidatesOnboarded: int
    monthlyPerformance: List[TAPerformanceEntry]

class TAMetricsAll(BaseModel):
    ta1: TAMetrics
    ta2: TAMetrics

class DashboardOverview(BaseModel):
    avgDaysToHire: float
    newApplications: int
    interviewsScheduledToday: int
    offerAcceptanceRate: float
    candidatesInFinalStage: int

###############################Department

# class DepartmentNameEnum(str, Enum):
#     APPLICATION_DEVELOPMENT = "Application Development"
#     DATA_SCIENCE = "Data Science"
#     HR_OPERATIONS = "HR Operations"

class DepartmentBase(BaseModel):
    """Base class for department schemas."""
    name: str
    department_head: str


class DepartmentCreate(DepartmentBase):
    """Class for creating a new department."""
    created_by: Optional[str] = None
    updated_by: Optional[str] = None


class DepartmentUpdate(DepartmentBase):
    """Class for creating a new department."""
    name: Optional[str] = None
    department_head: Optional[str] = None
    updated_by: Optional[str] = None

    class Config:
        from_attributes = True  


class DepartmentRead(DepartmentBase):
    """Class for reading department data."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime]=None
    created_by: str
    updated_by: Optional[str] = None

    class Config:
        from_attributes = True  


class JobBase(BaseModel):
    """Base class for job schemas"""
    title: str
    description: str
    department_id: int


class JobTitleCreate(JobBase):
    """Class for creating a new job."""
    created_by: Optional[str] = None
    pass


class JobTitleUpdate(JobBase):
    """Class for creating a new job."""
    title: Optional[str] = None
    description: Optional[str] = None
    department_id: Optional[int] = None
    updated_by: Optional[str] = None


class JobRead(JobBase):
    """Base class for job schemas"""
    id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    created_by: str
    updated_by: str

    class Config:
        from_attributes = True  
    
########## Department with Jobs (Optional - for nested responses) ##############

class DepartmentWithJobs(DepartmentRead):
    jobs: List[JobRead] = []

########## Job with Department (Optional - for nested responses) ##############

class JobWithDepartment(JobRead):
    department: DepartmentRead


# Updated Pydantic Schemas
class JobSkillCreate(BaseModel):
    primary_skills: Optional[str] = None
    secondary_primary_skillss: Optional[str] = None
    secondary_skills: Optional[str] = None
    therapeutic_area: Optional[str] = None
    job_id: int
    created_by: Optional[str] = "taadmin"


class JobSkillUpdate(BaseModel):
    primary_skills: Optional[str] = None
    secondary_skills: Optional[str] = None
    therapeutic_area: Optional[str] = None
    job_id: Optional[int] = None
    updated_by: Optional[str] = "taadmin"

class JobSkillRead(BaseModel):
    id: int
    primary_skills: Optional[str]  # Allow None
    secondary_skills: Optional[str]  # Allow None
    therapeutic_area: Optional[str] = None
    job_id: int
    job_title: str
    created_at: Optional[str]
    updated_at: Optional[str]
    created_by: str
    updated_by: str

    class Config: 
        orm_mode = True  # For SQLAlchemy ORM compatibility
        from_attributes = True  # For Pydantic v2 compatibility

# class ClientNameEnum(str, Enum):
#     SIRO = "SIRO"
#     GSK = "GSK"

class JobSkillReadWithSkillSet(BaseModel):
    """Schema for job skills with dynamically combined skill_set"""
    id: int
    primary_skills: str
    secondary_skills: Optional[str] = None
    skill_set: Optional[str] = None  # Dynamically combined: primary + secondary
    job_id: int
    job_title: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    created_by: str
    updated_by: str
    
    class Config:
        from_attributes = True

class JobSkillSetOnly(BaseModel):
    """Schema for just the skill_set field (for job requisition table)"""
    job_id: int
    skill_set: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    error: Optional[str] = None

class BulkJobSkillSets(BaseModel):
    """Schema for bulk skill_set operations"""
    job_ids: List[int]
    created_by: Optional[str] = None
    updated_by: Optional[str] = None



    
class ClientBase(BaseModel):
    name: str


class ClientCreate(ClientBase):
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    pass


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None


class ClientRead(ClientBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: str
    updated_by: Optional[str] = None

    class Config:
        orm_mode = True


class TAteamBase(BaseModel):
    team_name: str
    team_members: List[str]
    team_emails: List[EmailStr] = Field(default=[])
    department_id: int
    weightage: int

    @validator('team_emails')
    def validate_emails(cls, emails):
        for email in emails:
            if not email.endswith('@vaics-consulting.com'):
                raise ValueError(f"Invalid email domain: {email}. Only vaics-consulting.com emails are allowed.")
        return emails

class TAteamCreate(TAteamBase):
    created_by: Optional[str] = None
    pass

class TAteamUpdate(BaseModel):
    team_name: Optional[str] = None
    team_members: Optional[List[str]] = None
    team_emails: Optional[List[EmailStr]] = None
    department_id: Optional[int] = None
    weightage: Optional[int] = None
    updated_by: Optional[str] = None

    @validator('team_emails', always=True)
    def validate_emails(cls, emails):
        if emails is None:
            return emails
        for email in emails:
            if not email.endswith('@vaics-consulting.com'):
                raise ValueError(f"Invalid email domain: {email}. Only vaics-consulting.com emails are allowed.")
        return emails

class TAteamResponse(TAteamBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None

    class Config:
        from_attributes = True
############ Mode of work ####################

class CurrentStatusCreate(BaseModel):
    status: str
    final_status_id: Optional[int] = None
    weight: int
    created_by: Optional[str] = None
    updated_by: Optional[str] = None

    @field_validator("weight")
    def validate_weight(cls, value):
        if value is None:
            raise ValueError("Weight cannot be null")
        if not isinstance(value, int):
            raise ValueError("Weight must be an integer")
        if value < 0:
            raise ValueError("Weight must be a non-negative integer")
        return value

class CurrentStatusModel(BaseModel):
    id: int
    status: str
    final_status_id: Optional[int] = None
    final_status: Optional[str] = None
    weight: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    
    class Config:
        from_attributes = True 

class ModeOfWorkModel(BaseModel):
    id: Optional[int] = None
    mode: str
    weight: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    
    
    @field_validator("weight")
    def validate_weight(cls, value):
        if value is None:
            raise ValueError("Weight cannot be null")
        if not isinstance(value, int):
            raise ValueError("Weight must be an integer")
        if value < 0:
            raise ValueError("Weight must be a non-negative integer")
        return value
    
    class Config:
        from_attributes = True
        validate_by_name = True  

class JobTypeCreate(BaseModel):
    job_type: str
    weight: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    
    
    @field_validator("weight")
    def validate_weight(cls, value):
        if value is None:
            raise ValueError("Weight cannot be null")
        if not isinstance(value, int):
            raise ValueError("Weight must be an integer")
        if value < 0:
            raise ValueError("Weight must be a non-negative integer")
        return value

class JobTypeModel(BaseModel):
    id: int
    job_type: str
    weight: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    
    class Config:
        from_attributes = True
        validate_by_name = True  


class RequisitionTypeModel(BaseModel):
    id: Optional[int] = None
    requisition_type: str
    weight: Optional[int] = None 
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    
    @field_validator("weight")
    def validate_weight(cls, value):
        if value < 0:
            raise ValueError("Weight must be a non-negative integer")
        return value

    class Config:
        from_attributes = True
    class Config:
        from_attributes = True  

class PriorityCreate(BaseModel):
    priority: str
    weight: int
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None


class PriorityModel(BaseModel):
    id: Optional[int] = None
    priority: str
    weight: Optional[int] = None 
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None

    @field_validator("weight")
    def validate_weight(cls, value):
        if value is not None:
            if not isinstance(value, int):
                # Try to convert to int
                try:
                    value = int(value)
                except (ValueError, TypeError):
                    raise ValueError("Weight must be an integer")
        return value

    class Config:
        from_attributes = True 

class DiscussionStatusModel(BaseModel):
    id: Optional[int] = None
    status: str
    weight: Optional[int] = None 
    hex_code: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    
    @field_validator("weight")
    def validate_weight(cls, value):
        if value is not None:
            if not isinstance(value, int):
                # Try to convert to int
                try:
                    value = int(value)
                except (ValueError, TypeError):
                    raise ValueError("Weight must be an integer")
        return value

    class Config:
        from_attributes = True

class FinalStatusCreate(BaseModel):
    status: str
    weight: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    
    @field_validator("weight")
    def validate_weight(cls, value):
        if value is None:
            raise ValueError("Weight cannot be null")
        if not isinstance(value, int):
            raise ValueError("Weight must be an integer")
        if value < 0:
            raise ValueError("Weight must be a non-negative integer")
        return value
    
class FinalStatusModel(BaseModel):
    id: int
    status: str
    weight: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
   
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    
    class Config:
        from_attributes = True
        validate_by_name = True 



# Model for creation
class OfferStatusCreate(BaseModel):
    status: str
    created_by: Optional[str] = None

# Model for update
class OfferStatusUpdate(BaseModel):
    status: str
    updated_by: Optional[str] = None
    
# Model for response
class OfferStatusModel(BaseModel):
    id: Optional[int] = None
    status: str
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class InterviewStatusCreate(BaseModel):
    status: str
    weight: int
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    
    @field_validator("weight")
    def validate_weight(cls, value):
        if value is None:
            raise ValueError("Weight cannot be null")
        if not isinstance(value, int):
            raise ValueError("Weight must be an integer")
        if value < 0:
            raise ValueError("Weight must be a non-negative integer")
        return value

class InterviewStatusModel(BaseModel):
    id: Optional[int] = None
    status: str
    weight: Optional[int] = None  # Make weight nullable temporarily
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    
    class Config:
        from_attributes = True
    
class RatingModel(BaseModel):
    id: int | None = None
    rating: str
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True  

class JobListMinimal(BaseModel):
    id: int
    title: str
    department_id: int
    created_at: datetime
    created_by: str
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        
class JobRead(BaseModel):
    id: int
    title: str
    description: str
    department_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True                

class CandidateOfferStatusCreate(BaseModel):
    candidate_id: str
    offer_status: str

class CandidateOfferStatusResponse(BaseModel):
    candidate_id: str
    offer_status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    created_by: Optional[str] = "taadmin"
    updated_by: Optional[str] = "taadmin"

    class Config:
        from_attributes = True
        
class CandidateOfferStatusUpdate(BaseModel):
    offer_status: str
    updated_by: Optional[str] = None

    class Config:
        from_attributes = True  
        
class OfferLetterStatusBase(BaseModel):
    candidate_id: str
    offer_letter_status: str
    offer_letter_date: Optional[date] = None

class OfferLetterStatusCreate(OfferLetterStatusBase):
    created_by: Optional[str] = None
    

class OfferLetterStatusUpdate(BaseModel):
    offer_letter_status: Optional[str] = None
    offer_letter_date: Optional[date] = None
    updated_by: Optional[str] = None
    created_by: Optional[str] = None


class OfferLetterStatusResponse(OfferLetterStatusBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = "taadmin"
    created_by: Optional[str] = "taadmin"

    class Config:
        from_attributes = True      



class SubscriptionBase(BaseModel):
    email: EmailStr
    job_id: str
    subscription_status: bool = True

class SubscriptionCreate(SubscriptionBase):
    pass

class SubscriptionUpdate(BaseModel):
    subscription_status: bool

class SubscriptionResponse(SubscriptionBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
       from_attributes = True 

class PaginatedResponse(BaseModel):
    items: List[SubscriptionResponse]
    total: int
    page: int
    per_page: int
    total_pages: int

class JobSkillBase(BaseModel):
    primary_skills: str
    secondary_skills: Optional[str] = None
    therapeutic_area: Optional[str] = None
    job_id: int

class JobSkillCreate(JobSkillBase):
    created_by: Optional[str] = None
    pass

class JobSkillUpdate(BaseModel):
    primary_skills: Optional[str] = None
    secondary_skills: Optional[str] = None
    therapeutic_area: Optional[str] = None
    job_id: Optional[int] = None
    updated_by: Optional[str] = None

class JobSkillRead(JobSkillBase):
    id: int
    job_title: Optional[str] = None
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    updated_by: Optional[str] = None
    created_by: Optional[str] = None

    class Config:
        from_attributes = True

# New schemas for comprehensive skills endpoint
class SkillItem(BaseModel):
    skill: str
    count: int = 1
    
class SkillSource(BaseModel):
    job_id: Optional[str] = None
    job_title: Optional[str] = None
    candidate_id: Optional[str] = None
    candidate_name: Optional[str] = None
    source_type: str  # 'job_requisition', 'job_skills', 'candidate'

class SkillDetail(BaseModel):
    skill: str
    total_count: int
    sources: List[SkillSource]

class AllSkillsResponse(BaseModel):
    primary_skills: List[SkillDetail]
    secondary_skills: List[SkillDetail]
    candidate_skills: List[SkillDetail]
    unique_skills: List[str]
    total_skills_count: int    
    
    
class TATeamBase(BaseModel):
    team_name: str
    team_members: List[str]
    team_emails: List[str]
    weight: int

    @validator('team_emails')
    def validate_emails(cls, emails):
        for email in emails:
            if not email.endswith('@vaics-consulting.com'):
                raise ValueError(f"Invalid email domain: {email}. Only vaics-consulting.com emails are allowed.")
        return emails

class TATeamCreate(TATeamBase):
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    pass

class TATeamUpdate(BaseModel):
    team_name: Optional[str] = None
    team_members: Optional[List[str]] = None
    team_emails: Optional[List[str]] = None
    weight: Optional[int] = None
    updated_by: Optional[str] = None

    @validator('team_emails', always=True)
    def validate_emails(cls, emails):
        if emails is None:
            return emails
        for email in emails:
            if not email.endswith('@vaics-consulting.com'):
                raise ValueError(f"Invalid email domain: {email}. Only vaics-consulting.com emails are allowed.")
        return emails

class TATeamResponse(TATeamBase):
    id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    created_by: Optional[str] = None
    updated_by: Optional[str] = None

    class Config:
        from_attributes = True
        

class HRTeamBase(BaseModel):
    team_name: str = "HR Team"  # Default value
    team_members: List[str]
    team_emails: List[str]

    @validator('team_emails')
    def validate_emails(cls, emails):
        for email in emails:
            if not email.endswith('@vaics-consulting.com'):
                raise ValueError(f"Invalid email domain: {email}. Only vaics-consulting.com emails are allowed.")
        return emails

class HRTeamCreate(HRTeamBase):
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None

class HRTeamUpdate(BaseModel):
    team_name: Optional[str] = None
    team_members: Optional[List[str]] = None
    team_emails: Optional[List[str]] = None
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None

    @validator('team_emails', always=True)
    def validate_emails(cls, emails):
        if emails is None:
            return emails
        for email in emails:
            if not email.endswith('@vaics-consulting.com'):
                raise ValueError(f"Invalid email domain: {email}. Only vaics-consulting.com emails are allowed.")
        return emails

class HRTeamResponse(HRTeamBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None


    class Config:
        from_attributes = True

# Rest of the schemas remain unchanged (omitted for brevity)

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Union, List
from datetime import datetime

class CandidateExcelUpload(BaseModel):
    candidate_name: str = Field(..., alias="candidate_name")
    email_id: EmailStr = Field(..., alias="email_id")
    mobile_no: str = Field(..., alias="mobile_no")
    pan_card_no: Optional[str] = Field(None, max_length=10)
    date_of_resume_received: Optional[str] = Field(None, alias="date_of_resume_received")
    department: Optional[str] = Field(None, alias="department")
    associated_job_id: Optional[str] = Field(None, alias="associated_job_id")
    application_date: Optional[str] = Field(None, alias="application_date")
    skills_set: Optional[Union[str, List[str]]] = Field(None, alias="skills_set")
    current_company: Optional[str] = Field(None, alias="current_company")
    current_designation: Optional[str] = Field(None, alias="current_designation")
    gender : Optional[str] = Field(None, alias="gender")
    years_of_exp: Optional[float] = None
    current_status: Optional[str] = Field(None, alias="current_status")
    final_status: Optional[str] = Field(None, alias="final_status")
    notice_period: Optional[int] = Field(None, alias="notice_period")
    notice_period_unit: Optional[str] = Field(None, alias="time_unit")
    current_location: Optional[str] = Field(None, alias="current_location")
    additional_information_npd: Optional[str] = Field(None, alias="additional_information_npd")
    current_fixed_ctc: Optional[float] 
    current_variable_pay: Optional[float] 
    expected_fixed_ctc: Optional[float] 
    mode_of_work: Optional[str] = Field(None, alias="mode_of_work")
    reason_for_job_change: Optional[str] = Field(None, alias="reason_for_job_change")
    ta_team: Optional[str] = Field(None, alias="ta_team")
    ta_comments: Optional[str] = Field(None, alias="ta_comments")
    linkedin_url: Optional[str] = Field(None, alias="linkedin_url")
    l1_interview_date: Optional[str] = None
    l1_interviewer_name: Optional[str] = Field(None, alias="l1_interviewer_name")
    l1_status: Optional[str] = Field(None, alias="l1_status")
    l1_feedback: Optional[str] = Field(None, alias="l1_feedback")
    l2_interview_date: Optional[str] = None
    l2_interviewer_name: Optional[str] = Field(None, alias="l2_interviewer_name")
    l2_status: Optional[str] = Field(None, alias="l2_status")
    l2_feedback: Optional[str] = Field(None, alias="l2_feedback")
    hr_interview_date: Optional[str] = None
    hr_interviewer_name: Optional[str] = Field(None, alias="hr_interviewer_name")
    hr_status: Optional[str] = Field(None, alias="hr_status")
    hr_feedback: Optional[str] = Field(None, alias="hr_feedback")
    finalized_ctc: Optional[float] = Field(None, alias="Finalized CTC (In INR)")
    designation: Optional[str] = Field(None, alias="designation")
    offered_ctc: Optional[str] = Field(None, alias="Offered CTC (in INR)")
    ctc_breakup_status: Optional[str] = Field(None, alias="ctc_breakup_status")
    current_address: Optional[str] = Field(None, alias="current_address")
    permanent_address: Optional[str] = Field(None, alias="permanent_address")
    expected_date_of_joining: Optional[str] = Field(None, alias="expected_date_of_joining")
    date_of_joining: Optional[str] = Field(None, alias="date_of_joining")
    offer_status: Optional[str] = Field(None, alias="offer_status")
    discussion1_status: Optional[str] = Field(None, alias="discussion1_status")
    discussion1_done_by: Optional[str] = Field(None, alias="discussion1_done_by")
    discussion1_notes: Optional[str] = Field(None, alias="discussion1_notes")
    discussion1_date: Optional[str] = Field(None, alias="discussion1_date")
    discussion2_status: Optional[str] = Field(None, alias="discussion2_status")
    discussion2_done_by: Optional[str] = Field(None, alias="discussion2_done_by")
    discussion2_notes: Optional[str] = Field(None, alias="discussion2_notes")
    discussion2_date: Optional[str] = Field(None, alias="discussion2_date")
    discussion3_status: Optional[str] = Field(None, alias="discussion3_status")
    discussion3_done_by: Optional[str] = Field(None, alias="discussion3_done_by")
    discussion3_notes: Optional[str] = Field(None, alias="discussion3_notes")
    discussion3_date: Optional[str] = Field(None, alias="discussion3_date")
    discussion4_status: Optional[str] = Field(None, alias="discussion4_status")
    discussion4_done_by: Optional[str] = Field(None, alias="discussion4_done_by")
    discussion4_notes: Optional[str] = Field(None, alias="discussion4_notes")
    discussion4_date: Optional[str] = Field(None, alias="discussion4_date")
    discussion5_status: Optional[str] = Field(None, alias="discussion5_status")
    discussion5_done_by: Optional[str] = Field(None, alias="discussion5_done_by")
    discussion5_notes: Optional[str] = Field(None, alias="discussion5_notes")
    discussion5_date: Optional[str] = Field(None, alias="discussion5_date")
    discussion6_status: Optional[str] = Field(None, alias="discussion6_status")
    discussion6_done_by: Optional[str] = Field(None, alias="discussion6_done_by")
    discussion6_notes: Optional[str] = Field(None, alias="discussion6_notes")
    discussion6_date: Optional[str] = Field(None, alias="discussion6_date")
    created_by: Optional[str] = Field(None, alias="created_by")
    updated_by: Optional[str] = Field(None, alias="updated_by")

    @validator("mobile_no", pre=True)
    def clean_mobile_number(cls, value):
        if value:
            # Remove any non-digit characters and take the last 10 digits
            cleaned = ''.join(filter(str.isdigit, str(value)))
            if len(cleaned) < 10:
                raise ValueError("Mobile number must contain at least 10 digits")
            return cleaned[-10:]
        return value

    class Config:
        validate_by_name = True
        from_attributes = True


    @validator("skills_set", pre=True)
    def convert_skills_set(cls, value):
        if isinstance(value, str) and value:
             # Handle curly braces format: {skill, skill 2} -> skill, skill 2
            if value.startswith('{') and value.endswith('}'):
                # Remove curly braces and process as comma-separated string
                value = value[1:-1].strip()
            
            # Split by comma and clean up each skill
            return [skill.strip() for skill in value.split(",") if skill.strip()]
        elif isinstance(value, list):
            return [skill.strip() for skill in value if skill.strip()]
        return []



    @validator("current_status", pre=True)
    def set_default_current_status(cls, value):
        return value if value else "Screening"

    @validator("date_of_resume_received", "l1_interview_date", "l2_interview_date", "hr_interview_date", "expected_date_of_joining", pre=True)
    def format_date(cls, value):
        if not value:
            return None
        if isinstance(value, str) and value.strip():
            try:
                parsed = parse_date(value)
                if parsed and not isinstance(parsed, str):
                    return parsed.strftime("%Y-%m-%d")
            except:
                return None
        return value

    class Config:
        from_attributes = True
        allow_population_by_field_name = True

class EmployeeBase(BaseModel):
    employee_no: str
    date_of_joining: datetime
    comments: Optional[str] = None

class EmployeeCreate(EmployeeBase):
  
    pass

class EmployeeUpdate(EmployeeBase):
    employee_no: Optional[str] = None
    date_of_joining: Optional[datetime] = None
    updated_by: Optional[str] = "taadmin"
    updated_at: datetime
    updated_at: datetime

class EmployeeResponse(EmployeeBase):
    id: int
    candidate_id: str
    updated_by: Optional[str] = "taadmin"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True        

class GenderBase(BaseModel):
    gender: str
    updated_by: Optional[str] = None
    created_by: Optional[str] = None

class GenderCreate(GenderBase):
    
    pass
   
    
class GenderUpdate(GenderBase):
    updated_by: Optional[str] = None
    pass

class GenderResponse(GenderBase):
        id: int
        gender: str
        created_at: datetime
        updated_at: Optional[datetime]
        created_by: str
        updated_by: Optional[str]
        
        class Config:
          from_attributes = True

class JobTitleMinimal(BaseModel):
    id: int
    job_title: str

    class Config:
        from_attributes = True        

class DemandSupplyMetrics(BaseModel):
    demand: int
    supply: int
    in_process: int
    gap: int

class DepartmentDemandSupply(DemandSupplyMetrics):
    department: str

class JobDemandSupply(DemandSupplyMetrics):
    job_id: str
    job_title: str
    department: Optional[str] = None
    status: Optional[str] = None

class OnboardedCandidate(BaseModel):
    candidate_id: str
    candidate_name: str
    job_id: Optional[str] = None
    job_title: Optional[str] = None
    date_of_joining: Optional[date] = None
    department: Optional[str] = None
    designation: Optional[str] = None

    @field_validator('date_of_joining', mode='before')
    @classmethod
    def parse_date_of_joining(cls, value):
        if value is None:
            return None
        if isinstance(value, str) and value.strip():
            try:
                # Handle DD-MM-YYYY format
                if '-' in value and len(value.split('-')[0]) == 2:
                    parsed = parse_date(value, dayfirst=True)
                else:
                    parsed = parse_date(value)
                if parsed and not isinstance(parsed, str):
                    return parsed.date()
            except:
                return None
        elif isinstance(value, date):
            return value
        return value

    class Config:
        from_attributes = True

class TATeamStats(BaseModel):
    team_id: int
    team_name: str
    candidate_count: int


class TATeamOverview(BaseModel):
    total_ta_teams: int
    total_ta_members: int
    team_stats: List[TATeamStats]

class TATeamCandidateDetails(BaseModel):
    candidate_id: str
    candidate_name: str
    department: Optional[str] = None
    status: Optional[str] = None

class TATeamInterviewRoundStats(BaseModel):
    round_name: str
    count: int

class PaginatedTeamCandidates(BaseModel):
    total: int
    page: int
    items_per_page: int
    items: List[TATeamCandidateDetails]

class TATeamDetailedStatsResponse(BaseModel):
    team_id: int
    team_name: str
    total_candidates: int
    interview_round_stats: List[TATeamInterviewRoundStats]
    candidates: PaginatedTeamCandidates
    filter_applied: dict

class TATeamDetailsFilter(BaseModel):
    page: int = 1
    items_per_page: int = 10
    search: Optional[str] = None

class PaginatedTATeamDetails(BaseModel):
    total: int
    page: int
    items_per_page: int
    team_stats: TATeamDetailedStatsResponse

# New schemas for candidate stage details analytics
class CandidateStageDetail(BaseModel):
    candidate_id: str
    candidate_name: str
    associated_job_id: Optional[str] = None
    job_title: Optional[str] = None
    department: Optional[str] = None
    current_status: Optional[str] = None
    
    class Config:
        from_attributes = True

class CandidateStageDetailFilter(BaseModel):
    page: int = 1
    items_per_page: int = 10
    search: Optional[str] = None
    status: str  # Required parameter for the specific status to filter by

class PaginatedCandidateStageDetails(BaseModel):
    total: int
    page: int
    items_per_page: int
    status: str
    items: List[CandidateStageDetail]
    filter_applied: dict

# New schemas for department breakdown APIs
class DepartmentBreakdownItem(BaseModel):
    department: str
    count: int

    class Config:
        from_attributes = True

class DepartmentBreakdownResponse(BaseModel):
    breakdown: List[DepartmentBreakdownItem]
    total: int

    class Config:
        from_attributes = True

# New schemas for demand supply department breakdown APIs with percentage
class DemandSupplyDepartmentBreakdownItem(BaseModel):
    department: str
    count: int
    percentage: float

    class Config:
        from_attributes = True

class DemandSupplyDepartmentBreakdownResponse(BaseModel):
    total: int
    departments: int
    breakdown: List[DemandSupplyDepartmentBreakdownItem]

    class Config:
        from_attributes = True

# New schema for TA team individual breakdown with team name
class TATeamDepartmentBreakdownResponse(BaseModel):
    total: int
    departments: int
    team_name: str
    breakdown: List[DemandSupplyDepartmentBreakdownItem]

    class Config:
        from_attributes = True

# New schema for candidate stage department breakdown with stage name
class CandidateStageDepartmentBreakdownResponse(BaseModel):
    total: int
    departments: int
    stage_name: str
    breakdown: List[DemandSupplyDepartmentBreakdownItem]
    
    class Config:
        from_attributes = True

################## ROLE BASED ACCESS CONTROL SCHEMAS ##################

class PageAccessBase(BaseModel):
    page_name: str
    can_view: bool = False
    can_edit: bool = False

class PageAccessCreate(PageAccessBase):
    pass

class PageAccessUpdate(BaseModel):
    page_name: Optional[str] = None
    can_view: Optional[bool] = None
    can_edit: Optional[bool] = None

class PageAccessResponse(PageAccessBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    
    class Config:
        from_attributes = True

class SubpageAccessBase(BaseModel):
    subpage_name: str
    can_view: bool = False
    can_edit: bool = False

class SubpageAccessCreate(SubpageAccessBase):
    pass

class SubpageAccessUpdate(BaseModel):
    subpage_name: Optional[str] = None
    can_view: Optional[bool] = None
    can_edit: Optional[bool] = None

class SubpageAccessResponse(SubpageAccessBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    
    class Config:
        from_attributes = True

class SectionAccessBase(BaseModel):
    section_name: str
    can_view: bool = False
    can_edit: bool = False

class SectionAccessCreate(SectionAccessBase):
    pass

class SectionAccessUpdate(BaseModel):
    section_name: Optional[str] = None
    can_view: Optional[bool] = None
    can_edit: Optional[bool] = None

class SectionAccessResponse(SectionAccessBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    
    class Config:
        from_attributes = True

class RoleTemplateBase(BaseModel):
    role_name: str
    description: Optional[str] = None
    is_super_admin: bool = False
    duration_days: Optional[int] = None
    duration_months: Optional[int] = None
    duration_years: Optional[int] = None

class RoleTemplateCreate(RoleTemplateBase):
    pass

class RoleTemplateUpdate(BaseModel):
    role_name: Optional[str] = None
    description: Optional[str] = None
    is_super_admin: Optional[bool] = None
    duration_days: Optional[int] = None
    duration_months: Optional[int] = None
    duration_years: Optional[int] = None

class RoleTemplateResponse(RoleTemplateBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    
    class Config:
        from_attributes = True

class UserRoleAccessBase(BaseModel):
    user_id: int
    role_template_id: Optional[int] = None
    role_name: str
    is_super_admin: Optional[bool] = False
    email: Optional[str] = None  # Email field for direct lookups
    duration_days: Optional[int] = None
    duration_months: Optional[int] = None
    duration_years: Optional[int] = None
    expiry_date: Optional[datetime] = None
    page_access: Optional[dict] = None  # {"page_name": {"can_view": true, "can_edit": false}}
    subpage_access: Optional[dict] = None  # {"subpage_name": {"can_view": true, "can_edit": false}}
    section_access: Optional[dict] = None  # {"section_name": {"can_view": true, "can_edit": false}}
    allowed_job_ids: Optional[List[str]] = None
    allowed_department_ids: Optional[List[int]] = None
    allowed_candidate_ids: Optional[List[str]] = None
    is_unrestricted: bool = False

class UserRoleAccessCreate(UserRoleAccessBase):
    created_by: Optional[str] = None

class UserRoleAccessUpdate(BaseModel):
    role_template_id: Optional[int] = None
    role_name: Optional[str] = None
    is_super_admin: Optional[bool] = None
    email: Optional[str] = None  # Email field for direct lookups
    duration_days: Optional[int] = None
    duration_months: Optional[int] = None
    duration_years: Optional[int] = None
    expiry_date: Optional[datetime] = None
    page_access: Optional[dict] = None
    subpage_access: Optional[dict] = None
    section_access: Optional[dict] = None
    allowed_job_ids: Optional[List[str]] = None
    allowed_department_ids: Optional[List[int]] = None
    allowed_candidate_ids: Optional[List[str]] = None
    is_unrestricted: Optional[bool] = None

class UserRoleAccessResponse(UserRoleAccessBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    
    class Config:
        from_attributes = True

class UserAccessSummary(BaseModel):
    """Summary of user's access permissions"""
    user_id: int
    role_name: str
    is_super_admin: Optional[bool]
    expiry_date: Optional[datetime] = None
    total_pages: int
    total_subpages: int
    total_sections: int
    allowed_jobs_count: int
    allowed_departments_count: int
    allowed_candidates_count: int
    is_unrestricted: bool
    
    class Config:
        from_attributes = True

class RoleAccessDetails(BaseModel):
    """Detailed access permissions for a user"""
    user_id: int
    role_name: str
    is_super_admin: Optional[bool]
    expiry_date: Optional[datetime] = None
    page_access: List[PageAccessResponse]
    subpage_access: List[SubpageAccessResponse]
    section_access: List[SectionAccessResponse]
    allowed_job_ids: List[str]
    allowed_department_ids: List[int]
    allowed_candidate_ids: List[str]
    is_unrestricted: bool
    
    class Config:
        from_attributes = True

class PaginatedUserRoleAccess(BaseModel):
    """Paginated response for user role access"""
    items: List[UserRoleAccessResponse]
    total: int
    page: int
    items_per_page: int
    
    class Config:
        from_attributes = True

class UserRoleAccessFilter(BaseModel):
    """Filter for user role access queries"""
    page: int = 1
    items_per_page: int = 10
    search: Optional[str] = None
    is_super_admin: Optional[bool] = None
    role_template_id: Optional[int] = None
    user_id: Optional[int] = None

################## AUTH USER SCHEMAS ##################

class AuthUserResponse(BaseModel):
    """Response schema for auth users"""
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    department_id: Optional[int] = None
    is_system_admin: bool
    is_department_head: bool
    
    class Config:
        from_attributes = True

class AuthUserListResponse(BaseModel):
    """Response schema for paginated auth users list"""
    users: List[AuthUserResponse]
    total: int

    class Config:
        from_attributes = True

# Public Jobs Overview Schemas
class PublicJobOverviewItem(BaseModel):
    """Schema for individual job item in public jobs overview"""
    job_id: str
    job_title: str
    job_type: str
    posting_date: datetime
    skills: Optional[str] = None
    department: str  # Added department field

    class Config:
        from_attributes = True

class PublicJobsOverviewResponse(BaseModel):
    """Response schema for public jobs overview with pagination"""
    jobs: List[PublicJobOverviewItem]
    total: int
    page: int
    limit: int
    total_pages: int

    class Config:
        from_attributes = True

# Public Job Details Schema
class PublicJobDetailsResponse(BaseModel):
    """Schema for detailed public job information"""
    posted_on: Optional[datetime] = None  # When the job was posted
    title: str  # Job title
    summary: Optional[str] = None  # Job description/summary
    job_type: str  # Type of job (full-time, part-time, etc.)
    department: str  # Department name
    experience_required: str  # Experience range (e.g., "2-5 years")
    mode_of_work: str  # Work mode (remote, onsite, hybrid)
    no_of_positions: int  # Number of open positions
    must_have_skills: Optional[str] = None  # Required skills

    class Config:
        from_attributes = True

# =============================================================================
# PUBLIC JOB APPLICATION SCHEMAS
# =============================================================================
# The /public/jobs/{job_id}/apply endpoint uses multipart/form-data with file upload:
# - full_name: str = Form(...)
# - phone: str = Form(...) 
# - email: str = Form(...)
# - skills: str = Form(...)
# - city_location: str = Form(...)
# - resume: UploadFile = File(...) - accepts PDF, DOC, DOCX files
# =============================================================================

# Note: PublicJobApplicationCreate is no longer used as the endpoint now uses Form data with file upload
# Keeping it for reference, but the actual endpoint uses:
# - full_name: str = Form(...)
# - phone: str = Form(...)  
# - email: str = Form(...)
# - skills: str = Form(...)
# - city_location: str = Form(...)
# - resume: UploadFile = File(...)

class PublicJobApplicationCreate(BaseModel):
    """
    Schema for public job application submission (JSON-based - DEPRECATED)
    
    Note: The actual /public/jobs/{job_id}/apply endpoint now uses Form data with file upload.
    This schema is kept for reference only.
    """
    full_name: str = Field(..., min_length=1, max_length=200, description="Full name of the applicant")
    phone: str = Field(..., min_length=10, max_length=15, description="Phone number of the applicant")
    email: EmailStr = Field(..., description="Email address of the applicant")
    skills: str = Field(..., min_length=1, max_length=500, description="Skills of the applicant")
    resume_url: str = Field(..., description="URL of the uploaded resume")
    city_location: str = Field(..., min_length=1, max_length=100, description="City/Location of the applicant")
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        # Remove any non-digit characters for validation
        digits_only = ''.join(filter(str.isdigit, v))
        if len(digits_only) < 10:
            raise ValueError('Phone number must contain at least 10 digits')
        return v
    
    @field_validator('full_name')
    @classmethod
    def validate_full_name(cls, v):
        if not v.strip():
            raise ValueError('Full name cannot be empty or only whitespace')
        return v.strip()
    
    @field_validator('skills')
    @classmethod
    def validate_skills(cls, v):
        if not v.strip():
            raise ValueError('Skills cannot be empty or only whitespace')
        return v.strip()
        
    @field_validator('city_location')
    @classmethod
    def validate_city_location(cls, v):
        if not v.strip():
            raise ValueError('City/Location cannot be empty or only whitespace')
            # Handle curly braces format: {skill, skill 2} -> skill, skill 2
        if v.startswith('{') and v.endswith('}'):
            # Remove curly braces and process as comma-separated string
            v = v[1:-1].strip()
        return v.strip()

class PublicJobApplicationResponse(BaseModel):
    """Response schema for public job application submission"""
    message: str
    candidate_id: str
    job_id: str
    application_date: datetime
    
    class Config:
        from_attributes = True

class ReferredByBase(BaseModel):
    referred_by: str

class ReferredByCreate(ReferredByBase):
    created_by: str

class ReferredByUpdate(BaseModel):
    referred_by: Optional[str] = None
    updated_by: str

class ReferredByResponse(ReferredByBase):
    id: int
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: Optional[str] = None
    
    class Config:
        from_attributes = True

class UserRoleAccessLiteResponse(BaseModel):
    """Lightweight response for user role access with user info"""
    user_id: int
    role_template_id: Optional[int] = None
    role_name: str
    is_super_admin: bool
    expiry_date: Optional[datetime] = None
    allowed_job_ids: Optional[List[str]] = None
    allowed_department_ids: Optional[List[int]] = None
    allowed_candidate_ids: Optional[List[str]] = None
    is_unrestricted: bool
    user_name: str
    user_email: str
    
    class Config:
        from_attributes = True

class InternalLogBase(BaseModel):
    page: str
    sub_page: Optional[str] = None
    action: str
    action_type: str  # Create, Update, Delete
    performed_by: str
    description: Optional[str] = None
    job_id: Optional[str] = None
    candidate_id: Optional[str] = None
    related_value: Optional[str] = None

class InternalLogCreate(InternalLogBase):
    pass

class InternalLogUpdate(BaseModel):
    page: Optional[str] = None
    sub_page: Optional[str] = None
    action: Optional[str] = None
    action_type: Optional[str] = None
    performed_by: Optional[str] = None
    description: Optional[str] = None
    job_id: Optional[str] = None
    candidate_id: Optional[str] = None
    related_value: Optional[str] = None

class InternalLogResponse(InternalLogBase):
    id: int
    timestamp: datetime
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class InternalLogFilter(BaseModel):
    page: int = 1
    items_per_page: int = 50
    search: Optional[str] = None
    page_filter: Optional[str] = None
    action_type_filter: Optional[str] = None
    performed_by_filter: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    sort_key: Optional[str] = "timestamp"
    sort_order: Optional[str] = "desc"

class PaginatedInternalLogResponse(BaseModel):
    total: int
    page: int
    items_per_page: int
    items: List[InternalLogResponse]

    class Config:
        from_attributes = True

class DataRetentionSettingsCreate(BaseModel):
    notification_retention_days: int = Field(..., ge=1, le=3650)  # 1 day to 10 years
    logs_retention_days: int = Field(..., ge=1, le=3650)  # 1 day to 10 years
    created_by: Optional[str] = None

class DataRetentionSettingsUpdate(BaseModel):
    notification_retention_days: Optional[int] = Field(None, ge=1, le=3650)
    logs_retention_days: Optional[int] = Field(None, ge=1, le=3650)
    updated_by: Optional[str] = None

class DataRetentionSettingsResponse(BaseModel):
    id: int
    notification_retention_days: int
    logs_retention_days: int
    created_by: str
    created_on: datetime
    updated_by: str
    updated_on: Optional[datetime] = None

    class Config:
        from_attributes = True
