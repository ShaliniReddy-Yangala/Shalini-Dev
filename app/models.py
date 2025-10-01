import uuid
from sqlalchemy import ARRAY, JSON, Boolean, Column, Float, ForeignKey, Integer, String, Date, DateTime, Enum as SQLAlchemyEnum, Table, Text, UniqueConstraint, func, Index, text
from sqlalchemy.ext.declarative import declarative_base
from enum import Enum
from datetime import date, datetime, timezone
from typing import Optional, List
from pydantic import BaseModel
from .database import Base, engine
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func
from sqlalchemy import event


# Priority enum removed and will be used as string values

# class RequisitionType(str, Enum):
#     NEWHIRE = "New Hire"
#     REPLACEMENT = "Replacement"

# class JobType(str, Enum):
#     FULLTIME = "Full Time"
#     PARTTIME = "Part Time"
#     INTERNSHIP = 'Internship'

# class ModeOfWork(str, Enum):
#     WFH = "Work From Home"
#     OFFICE = "Office"
#     HYBRID = "Hybrid"

class Status(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"

class IdCounter(Base):
    __tablename__ = 'id_counters'

    counter_name = Column(String(20), primary_key=True)
    last_value = Column(Integer, nullable=False, default=0)

# Job_requisition Table
class Job(Base):
    __tablename__ = 'job_requisitions'

    id = Column(Integer, primary_key=True)
    job_id = Column(String(20), unique=True)
    job_title = Column(String(200), nullable=False)
    no_of_positions = Column(Integer, nullable=False, default=1)
    requisition_type = Column(String, nullable=False, default="NEWHIRE")
    employee_to_be_replaced = Column(String(200))
    job_type = Column(String, nullable=False, default="FULLTIME")
    # primary_skills = Column(String(250))
    # secondary_skills = Column(String(250))
    skill_set = Column(String(250))
    department = Column(String(200), nullable=False)
    required_experience_min = Column(Integer, nullable=False)
    required_experience_max = Column(Integer, nullable=False)
    ctc_budget_min = Column(Integer)
    ctc_budget_max = Column(Integer)
    target_hiring_date = Column(Date)
    priority = Column(String(20), nullable=False)  # Changed from SQLAlchemyEnum to String
    office_location = Column(String(25), nullable=False, default="Hyderabad")
    additional_notes = Column(String(500))
    job_description = Column(Text)
    mode_of_work = Column(String, nullable=False)
    client_name = Column(String(50))
    head_of_department = Column(String(200), nullable=False)
    status = Column(String, nullable=False, default="OPEN")
    created_on = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by = Column(String(200), nullable=False, default='system')
    updated_on = Column(DateTime, nullable=True, default=None, onupdate=datetime.utcnow)
    updated_by = Column(String(200), nullable=False, default='')
    updated_by = Column(String(200), nullable=False, default='')
    # reason_for_hiring = Column(String(250))



 # Relationships
    notifications = relationship("Notification", back_populates="job")

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

        # Generate job_id if not provided
        if not self.job_id:
            from sqlalchemy.orm import Session
            with Session(engine) as session:
                job_counter = session.query(IdCounter).filter_by(counter_name='job_id').first()
                if not job_counter:
                    job_counter = IdCounter(counter_name='job_id', last_value=900000)
                    session.add(job_counter)

                # Increment the counter
                job_counter.last_value += 1
                next_id = job_counter.last_value

                # Commit to save the counter
                session.commit()

                # Format job_id as JR00xxxxxx
                self.job_id = f"JR00{next_id}"

        # Apply business rules
        self._apply_business_rules()

    def _apply_business_rules(self):
        # Default location to Hyderabad if not specified
        if not self.office_location:
            self.office_location = "Hyderabad"

        # Default job_type to Full Time if not specified
        if not self.job_type:
            self.job_type = "FULLTIME"

        # Clear employee_to_be_replaced if requisition_type is not Replacement
        if self.requisition_type != "REPLACEMENT":
            self.employee_to_be_replaced = None

        # Set date_of_request to today if not specified
        # if not self.date_of_request:
        #     self.date_of_request = datetime.now(timezone.utc).date()

################## Candidate #####################

# class OfferStatus(str, Enum):
#     ACCEPTED = "Accepted"
#     DECLINED = "Declined"
#     PENDING = "Pending"
#     SENT = "Sent"
#     NOT_INITIATED = "Not Initiated"

# class InterviewStatus(str, Enum):
#     SELECTED = "Selected"
#     REJECTED = "Rejected"
#     ON_HOLD = "On Hold"
#     SKIPPED = "Skipped"

# class CurrentStatus(str, Enum):
#     SCREENING = "SCREENING"
#     CALL = "Call"Screening, call, 
#     IN_PIPELINE = "In Pipeline"
#     SCHEDULED = "Scheduled"
#     L1_INTERVIEW = "L1 Interview"
#     L2_INTERVIEW = "L2 Interview"
#     HR_ROUND = "HR Round"
#     CTC_BREAKUP = "CTC Breakup"
#     DOCS_UPLOAD = "Docs Upload"
#     CREATE_OFFER = "Create Offer"
#     OFFER_INITIATED = "Offer Initiated"
#     OFFER_ACCEPTED = "Offer Accepted"
#     OFFER_DECLINED = "Offer Declined"
#     REJECTED = "Rejected"
#     IN_DISCUSSION = "In Discussion"
#     ONBOARDED = "Onboarded"
#     DECLINED = "DECLINED" 


# Enum for Final Status
# class FinalStatus(str, Enum):
#     IN_PROGRESS = "In progress"
#     OFFERED = "Offered"
#     OFFER_ACCEPTED = "Offer accepted"
#     REJECTED = "Rejected"
#     ONBOARDED = "Onboarded"


# Candidate Table
class Candidate(Base):
    __tablename__ = 'candidates'

    candidate_id = Column(String, primary_key=True, index=True)
    candidate_name = Column(String, nullable=False)
    email_id = Column(String, nullable=False)
    mobile_no = Column(String)
    pan_card_no = Column(String(10), nullable=True)
    resume_path = Column(Text)
    date_of_resume_received = Column(Date, default=date.today)
    associated_job_id = Column(String)
    application_date = Column(Date)
    skills_set = Column(String) 
    current_company = Column(String)
    current_designation = Column(String)
    department = Column(String(100), nullable=True)
    years_of_exp = Column(Float)
    status = Column(String)
    notice_period = Column(String)
    notice_period_units = Column(String)
    npd_info = Column(String)
    current_fixed_ctc = Column(Float)
    current_variable_pay = Column(Float)
    expected_fixed_ctc = Column(Float, nullable=True)
    mode_of_work = Column(String)
    gender = Column(String)
    reason_for_job_change = Column(String)
    current_address = Column(Text, nullable=True)
    current_location = Column(String, nullable=True)
    permanent_address = Column(Text, nullable=True)
    ta_team = Column(String)
    ta_comments = Column(Text)
    rating = Column(String)
    # L1 Interview details
    l1_interview_date = Column(Date, nullable=True)
    l1_interviewers_name = Column(String(100), nullable=True)
    l1_status = Column(String(50), nullable=True)
    l1_feedback = Column(Text, nullable=True)
    # L2 Interview details
    l2_interview_date = Column(Date, nullable=True)
    l2_interviewers_name = Column(String(100), nullable=True)
    l2_status = Column(String(50), nullable=True)
    l2_feedback = Column(Text, nullable=True)
    # HR Interview details
    hr_interview_date = Column(Date, nullable=True)
    hr_interviewer_name = Column(String(100), nullable=True)
    hr_status = Column(String(50), nullable=True)
    hr_feedback = Column(Text, nullable=True)
    # Offer related fields
    expected_ctc = Column(String(20))
    final_offer_ctc = Column(String(20))
    ctc_breakup_sent_date = Column(Date)
    offer_initiated_date = Column(Date)
    offer_status = Column(String, nullable=True)
    offer_accepted_rejected_date = Column(Date)
    expected_date_of_joining = Column(String(20), nullable=True)
    date_of_joining = Column(String(20))
    current_status = Column(String, nullable=True)
    status_updated_on = Column(Date, nullable=True)
    rejected_date = Column(Date, nullable=True)

     # New field for final status
    final_status = Column(String, nullable=True)
    
    # Discussion fields
    discussion1_date = Column(Date, nullable=True)
    discussion1_status = Column(String(50), nullable=True)
    discussion1_notes = Column(String, nullable=True)
    discussion1_done_by = Column(String(255), nullable=True)

    discussion2_date = Column(Date, nullable=True)
    discussion2_status = Column(String(50), nullable=True)
    discussion2_notes = Column(String, nullable=True)
    discussion2_done_by = Column(String(255), nullable=True)
    
    discussion3_date = Column(Date, nullable=True)
    discussion3_status = Column(String(50), nullable=True)
    discussion3_notes = Column(String, nullable=True)
    discussion3_done_by = Column(String(255), nullable=True)
    
    discussion4_date = Column(Date, nullable=True)
    discussion4_status = Column(String(50), nullable=True)
    discussion4_notes = Column(String, nullable=True)
    discussion4_done_by = Column(String(255), nullable=True)
    
    discussion5_date = Column(Date, nullable=True)
    discussion5_status = Column(String(50), nullable=True)
    discussion5_notes = Column(String, nullable=True)
    discussion5_done_by = Column(String(255), nullable=True)
    
    discussion6_date = Column(Date, nullable=True)
    discussion6_status = Column(String(50), nullable=True)
    discussion6_notes = Column(String, nullable=True)
    discussion6_done_by = Column(String(255), nullable=True)

    resume_url = Column(String(255))
    created_at = Column(Date, default=date.today)
    created_at = Column(Date, default=date.today)
    updated_at = Column(Date, nullable=True, onupdate=date.today)  # Made nullable
    created_by = Column(String(100), default='system', nullable=False)  # Changed from 'taadmin'
    updated_by = Column(String(100), nullable=True)  # Removed default, made nullable
    linkedin_url = Column(String(255), nullable=True)
    referred_by = Column(String(255), nullable=True)
# Relationships
    progress = relationship("CandidateProgress", back_populates="candidate", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="candidate", cascade="all, delete-orphan")
    ctc_breakup_details= relationship("CTCBreakup", back_populates="candidate", uselist=False)
    discussions = relationship("Discussion", back_populates="candidate", cascade="all, delete-orphan")
    ctc_status_details = relationship("CTCStatus", back_populates="candidate")
    notifications = relationship("Notification", back_populates="candidate")
    employee = relationship("Employee", back_populates="candidate", uselist=False)

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


### Pan card validation and rejected date validation
    def __setattr__(self, name, value):
        # Auto-convert PAN card to uppercase
        if name == 'pan_card_no' and value:
            value = value.upper()
        super().__setattr__(name, value)
            
# Event listener to handle rejected_date updates based on status changes
@event.listens_for(Candidate.current_status, 'set')
@event.listens_for(Candidate.final_status, 'set')
def update_rejected_date(target, value, oldvalue, initiator):
    """
    Update rejected_date when status changes to rejection-related values
    """
    if value and initiator.key in ['current_status', 'final_status']:
        rejection_statuses = [
            'Screening Rejected', 'Rejected', 'Offer Declined'
        ]
        
        # Check if the new status is a rejection status
        if value in rejection_statuses:
            target.rejected_date = date.today()
        # Check if final_status is "Rejected"
        elif initiator.key == 'final_status' and value == 'Rejected':
            target.rejected_date = date.today()
        else:
            # For other status values, clear the rejected_date
            target.rejected_date = None

@event.listens_for(Candidate, 'before_insert')
def assign_candidate_id(mapper, connection, target):
    """
    Atomically assign candidate_id within the same transaction as the insert.
    Uses an UPSERT to create the counter if missing and increments it, then
    returns the new value. If the surrounding transaction is rolled back, the
    counter increment is rolled back too, preventing gaps.
    """
    if target.candidate_id:
        return

    result = connection.execute(
        text(
            """
            INSERT INTO id_counters (counter_name, last_value)
            VALUES (:counter_name, :start_value)
            ON CONFLICT (counter_name)
            DO UPDATE SET last_value = id_counters.last_value + 1
            RETURNING last_value
            """
        ),
        {"counter_name": "candidate_id", "start_value": 800000},
    )
    next_value = result.scalar()
    target.candidate_id = f"C00{next_value}"

class CandidateProgress(Base):
    __tablename__ = "candidate_progress"
    
    id = Column(Integer, primary_key=True)
    candidate_id = Column(String, ForeignKey('candidates.candidate_id')) 
    status = Column(String, nullable=False)
    timestamp = Column(Date)

    candidate = relationship("Candidate", back_populates="progress")

############################### discussion 

class Discussion(Base):
    __tablename__ = "discussions"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(String, ForeignKey("candidates.candidate_id"))
    level = Column(Integer)
    done_by = Column(String, nullable=True)
    feedback = Column(Text, nullable=True)
    decision = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)
    created_by = Column(String(100), default="taadmin", nullable=False)
    updated_by = Column(String(100), nullable=True)  # Removed default
    
    # Relationship to candidate
    candidate = relationship("Candidate", back_populates="discussions")
    questions = relationship("DiscussionQuestion", back_populates="discussion", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('candidate_id', 'level', name='unique_candidate_discussion_level'),
    )



class DiscussionQuestion(Base):
    __tablename__ = "discussion_questions"
    id = Column(Integer, primary_key=True, index=True)
    discussion_id = Column(Integer, ForeignKey("discussions.id"), nullable=True)
    round_name = Column(String)  # D1, D2, D3, D4, D5, D6
    questions_content = Column(Text, nullable=True)  # Rich text content
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)

  
    
    # Relationship back to discussion
    discussion = relationship("Discussion", back_populates="questions")
    
    __table_args__ = (
        UniqueConstraint('discussion_id', 'round_name', name='unique_discussion_round_questions'),
    )

    
########## notification ########################

# class NotificationType(str, Enum):
#     APPLICATION_REVIEW = "Application Review"
#     APPLICATION_COUNT = "Application Count"f
#     JOB_APPROVAL = "Job Approval"
#     LOGIN_ALERT = "Login Alert"
#     SYSTEM = "System"
#     INTERVIEW_SCHEDULE = "Interview Schedule"

class Notification(Base):
    __tablename__ = 'notifications'

    id = Column(Integer, primary_key=True)
    user_id = Column(String(100), nullable=False)
    notification_type = Column(String, nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(String(500), nullable=False)
    link = Column(String(200), nullable=True)
    job_id = Column(String(20), ForeignKey('job_requisitions.job_id'), nullable=True)
    candidate_id = Column(String(20), ForeignKey('candidates.candidate_id'), nullable=True)
    is_read = Column(Boolean, default=False)
    created_on = Column(DateTime, nullable=False, default=datetime.now(timezone.utc))
    updated_on = Column(DateTime(timezone=True), onupdate=func.now())
    # Relationships
    job = relationship("Job", back_populates="notifications")
    candidate = relationship("Candidate", back_populates="notifications")

################################ CTC Breakout #######################################################

class CTCBreakup(Base):
    __tablename__ = "ctc_breakups"

    id= Column(Integer, primary_key=True, index=True)
    candidate_id= Column(String, ForeignKey("candidates.candidate_id"), unique=True)
    candidate_name= Column(String)
    designation= Column(String)
    ctc= Column(Float) 
    salary_components= Column(JSON)
    ctc_email_status = Column(String, default="not_sent")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)
    created_by = Column(String(100), default="taadmin", nullable=False)
    updated_by = Column(String(100), nullable=True)  # Removed default

    candidate=relationship("Candidate", back_populates="ctc_breakup_details")



class CTCStatus(Base):
    __tablename__ = "ctc_status"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, index=True)
    candidate_id = Column(String, ForeignKey("candidates.candidate_id"), nullable=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, onupdate=datetime.now(timezone.utc))

    # Relationships
    candidate = relationship("Candidate", back_populates="ctc_status_details")


##############################USer roles
class Role(Base):
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)  
    description = Column(String)
    
    # Relationship to UserRole 
    user_roles = relationship("UserRole", back_populates="role")

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    department = Column(String, nullable=True, index=True)
    
    # Relationship to UserRole
    user_roles = relationship("UserRole", back_populates="user")
    
    __table_args__ = (
        Index('idx_users_email_lower', func.lower(email)),
        Index('idx_users_name_email', 'name', 'email'),
    )

class UserRole(Base):
    __tablename__ = "user_roles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    role_id = Column(Integer, ForeignKey("roles.id"))
    role_template_id = Column(Integer, ForeignKey("role_templates.id"), nullable=True)  # New field
    department = Column(String, nullable=True)
    job_ids = Column(ARRAY(String), nullable=True)
    is_unrestricted = Column(Boolean, default=False)
    duration_days = Column(Integer, nullable=True)
    duration_months = Column(Integer, nullable=True)
    duration_years = Column(Integer, nullable=True)
    expiry_date = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="user_roles")
    role = relationship("Role", back_populates="user_roles")
    role_template = relationship("RoleTemplate", back_populates="user_roles")  # New relationship

####################################### Documents uplload 

class DocumentType(str, Enum):
    AADHAR = "aadhar"
    PAN = "pan"
    PHOTO = "photo"
    EDUCATION = "education"
    PAYSLIPS = "payslips"
    BANK_STATEMENT = "bankStatement"
    FORM16 = "form16"
    OFFER_LETTER = "offerLetter"
    HIKE_LETTER = "hikeLetter"
    UAN = "uan"
    RESIGNATION = "resignation"

class DocumentStatus(str, Enum):
    PENDING = "Pending"
    VERIFIED = "Verified"
    REJECTED = "Rejected"

class Document(Base):
    __tablename__ = 'documents'

    id = Column(Integer, primary_key=True)
    candidate_id = Column(String, ForeignKey('candidates.candidate_id'), nullable=False)
    document_type = Column(SQLAlchemyEnum(DocumentType), nullable=False)
    original_filename = Column(String(200), nullable=False)
    s3_key = Column(String(500), nullable=False)
    content_type = Column(String(100))
    status = Column(String, default=DocumentStatus.PENDING)
    verification_notes = Column(String(500))
    uploaded_at = Column(DateTime, nullable=False, default=datetime.now(timezone.utc))
    verified_at = Column(DateTime, nullable=True)
    verified_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)
    

    # Relationships
    candidate = relationship("Candidate", back_populates="documents")

class ShareableLink(Base):
    __tablename__ = 'shareable_links'

    id = Column(Integer, primary_key=True)
    token = Column(String(100), nullable=False, unique=True)
    candidate_id = Column(String, ForeignKey('candidates.candidate_id'), nullable=False)
    created_by = Column(String(100), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)

    # Relationships
    candidate = relationship("Candidate")


############## DASH BOARD ##################
class TimePeriod(str, Enum):
    LAST_7_DAYS = "last-7-days"
    LAST_30_DAYS = "last-30-days"
    THIS_MONTH = "this-month"
    PAST_WEEK = "past-week"
    LAST_90_DAYS = "last-90-days"
    PAST_MONTH = "past-month"
    LAST_QUARTER = "last-quarter"
    THIS_YEAR = "this-year"
    PAST_YEAR = "past-year"
    CUSTOM = "custom"

# class DepartmentNameEnum(str, Enum):
#     APPLICATION_DEVELOPMENT = "Application Development"
#     DATA_SCIENCE = "Data Science"
#     HR_OPERATIONS = "HR Operations"

########## Department wise data ##############
class Department(Base):
    __tablename__ = "departments"

    id                = Column(Integer, primary_key=True, index=True)
    name              = Column(String(200), unique=True, index=True, nullable=False)
    department_head   = Column(String(200), nullable=False)
    created_at        = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at        = Column(DateTime, nullable=True, onupdate=datetime.now(timezone.utc))
    created_by        = Column(String(100), default="system", nullable=False)
    updated_by        = Column(String(100), nullable=True)  # Removed default, made nullable
    
    # Relationships
    jobs = relationship("Jobs", back_populates="department", cascade="all, delete-orphan")
    


############# Job ###############

class Jobs(Base):
    __tablename__ = "jobs"  # Fixed double underscore syntax
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="CASCADE"))
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.now(timezone.utc))
    created_by = Column(String(100), default="system", nullable=False)
    updated_by = Column(String(100), nullable=True)  # Removed default, made nullable
    
    # Relationships
    department = relationship("Department", back_populates="jobs")
    skills = relationship("JobSkills", back_populates="job", cascade="all, delete-orphan")



############ Job Skills ###############

class JobSkills(Base):
    __tablename__ = "job_skills"
    
    id = Column(Integer, primary_key=True, index=True)
    primary_skills = Column(String(200), nullable=False)  # Store primary skills as a comma-separated string
    secondary_skills = Column(String(200), nullable=True)  # Secondary skills can be optional
    therapeutic_area = Column(String(200), nullable=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"))
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.now(timezone.utc))
    created_by = Column(String(100), default="taadmin", nullable=False)
    updated_by = Column(String(100), nullable=True)  # Removed default, made nullable
    
    job = relationship("Jobs", back_populates="skills")



############ Client ###############
# class ClientNameEnum(str, Enum):
#     SIRO = "SIRO"
#     GSK = "GSK"


class Client(Base):
    __tablename__ = "clients"

    id          = Column(Integer, primary_key=True, index=True)
    name              = Column(String(200), unique=True, index=True, nullable=False)
    created_at  = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at  = Column(DateTime, nullable=True, onupdate=datetime.now(timezone.utc))
    created_by  = Column(String(100), default="system", nullable=False)
    updated_by  = Column(String(100), nullable=True)  # Removed default, made nullable


class TATeam(Base):
    __tablename__ = "ta_team"

    id = Column(Integer, primary_key=True, index=True)
    team_name = Column(String(200), nullable=False, index=True)
    team_members = Column(ARRAY(String(100)), nullable=False)
    team_emails = Column(ARRAY(String(100)), nullable=False, server_default='{}')  # Match SQL default
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.now(timezone.utc))
    created_by = Column(String(100), nullable=False)  # Removed default
    updated_by = Column(String(100), nullable=True)  # Removed default, made nullable



class StatusDB(Base):
    __tablename__ = "statuses"
    
    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, nullable=False)
    final_status_id = Column(Integer, ForeignKey("final_statuses.id"), nullable=True)
    weight = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    created_by = Column(String(100), default="system", nullable=False)
    updated_by = Column(String(100), nullable=True)  # Removed default, made nullable


    # Add relationship
    final_status = relationship("FinalStatusDB")
    

class ModeDB(Base):
    __tablename__ = "modes"
    
    id = Column(Integer, primary_key=True, index=True)
    mode = Column(String, nullable=False)
    weight = Column(Integer, nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)
    created_by = Column(String(100), nullable=False)  # Removed default
    updated_by = Column(String(100), nullable=True)  # No default



class JobTypeDB(Base):
    __tablename__ = "job_types"
    id = Column(Integer, primary_key=True, index=True)
    job_type = Column(String, unique=True, nullable=False)
    weight = Column(Integer, nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    created_by = Column(String(100), default="system", nullable=False)
    updated_by = Column(String(100), nullable=True)  # Removed default, made nullable


class RequisitionTypeDB(Base):
    __tablename__ = "requisition_types"
    id = Column(Integer, primary_key=True, index=True)
    requisition_type = Column(String, unique=True, nullable=False)
    weight = Column(Integer, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)
    created_by = Column(String(100), default="system", nullable=False)
    updated_by = Column(String(100), nullable=True)  # Removed default, made nullable


class PriorityDB(Base):
    __tablename__ = "priorities"
    id = Column(Integer, primary_key=True, index=True)
    priority = Column(String(20), unique=True, nullable=False)  # Changed from SQLAlchemyEnum to String
    weight = Column(Integer, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    created_by = Column(String(100), default="system", nullable=False)
    updated_by = Column(String(100), nullable=True)  # Removed default, made nullable



class FinalStatusDB(Base):
    __tablename__ = "final_statuses"
    
    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, nullable=False)
    weight = Column(Integer, nullable=False, unique=True)  # Added weight column
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    created_by = Column(String(100), default="system", nullable=False)
    updated_by = Column(String(100), nullable=True)  # Removed default, made nullable

class OfferStatusDB(Base):
    __tablename__ = "offer_statuses"
    
    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)  # No default, only onupdate
    created_by = Column(String(100), default="taadmin", nullable=False)
    updated_by = Column(String(100), nullable=True)

class InterviewStatusDB(Base):
    __tablename__ = "interview_statuses"
    
    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, nullable=False)
    weight = Column(Integer, nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)
    created_by = Column(String(100), nullable=False)  # Removed default
    updated_by = Column(String(100), nullable=True)  # Removed default

class RatingDB(Base):
    __tablename__ = "rating"

    id = Column(Integer,primary_key=True, index=True)
    rating = Column(String,nullable=False)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_by = Column(String, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_by = Column(String, nullable=True)
    updated_at = Column(DateTime, nullable=True)


class CandidateOfferStatus(Base):
    __tablename__ = "candidate_offer_statuses"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(String, ForeignKey("candidates.candidate_id"), nullable=False, index=True)
    offer_status = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, onupdate=datetime.now(timezone.utc))
    created_by = Column(String(100), default="taadmin", nullable=False)
    updated_by = Column(String(100), nullable=True)  # Removed default

    # Relationship
    candidate = relationship("Candidate", backref="offer_statuses")    
    
class OfferLetterStatus(Base):
    __tablename__ = "offer_letter_status"
    
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(String, ForeignKey("candidates.candidate_id"), index=True)
    offer_letter_status = Column(String, nullable=False)
    offer_letter_date = Column(Date, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now()) 
    created_by = Column(String(100), default="taadmin", nullable=False)
    updated_by = Column(String(100), nullable=True)  # Removed default


class CandidateEmailSubscription(Base):
    __tablename__ = "candidate_email_subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, index=True)
    job_id = Column(String(100), nullable=False, index=True)
    subscription_status = Column(Boolean, nullable=False, default=True)

    
class SecondInterviewTeam(Base):
    __tablename__ = "second_interview_teams"
    id = Column(Integer, primary_key=True, index=True)
    team_name = Column(String, nullable=False)
    team_members = Column(ARRAY(String), nullable=False)
    team_emails = Column(ARRAY(String), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    weightage = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)
    created_by = Column(String(100), default="taadmin", nullable=False)
    updated_by = Column(String(100), nullable=True)  # Removed default


class HRTeam(Base):
    __tablename__ = "hr_teams"
    id = Column(Integer, primary_key=True, index=True)
    team_name = Column(String, nullable=False, default="HR Team")  # Added team_name
    team_members = Column(ARRAY(String), nullable=False)
    team_emails = Column(ARRAY(String), nullable=False)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_by = Column(String, nullable=True)
    updated_at = Column(DateTime, nullable=True)
   
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_by = Column(String, nullable=True)
    updated_at = Column(DateTime, nullable=True)
   
    

class InterviewTeam(Base):
    __tablename__ = "interview_teams"
    id = Column(Integer, primary_key=True, index=True)
    team_name = Column(String, nullable=False)
    team_members = Column(ARRAY(String), nullable=False)
    team_emails = Column(ARRAY(String), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    weightage = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime,   nullable=True,onupdate=datetime.utcnow)  
    created_by = Column(String(100), default="taadmin", nullable=False)
    updated_by = Column(String(100), nullable=True)  # Removed default
    
class TalentAcquisitionTeam(Base):
    __tablename__ = "talent_acquisition_teams"
    id = Column(Integer, primary_key=True, index=True)
    team_name = Column(String, nullable=False)
    team_members = Column(ARRAY(String), nullable=False)
    team_emails = Column(ARRAY(String), nullable=False)
    weight = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)
    created_by = Column(String(100), default="taadmin", nullable=False)
    updated_by = Column(String(100), nullable=True)  # Removed default
    

class DiscussionStatusDB(Base):
    __tablename__ = "discussion_statuses"
    id = Column(Integer, primary_key=True, index=True)
    status = Column(String(50), unique=True, nullable=False)
    weight = Column(Integer, unique=True, nullable=False)
    hex_code = Column(String(7), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime,  nullable=True,onupdate=datetime.utcnow)
    created_by = Column(String(100), default="taadmin", nullable=False)
    updated_by = Column(String(100), nullable=True)  # Removed default
    

class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(String, ForeignKey("candidates.candidate_id"), nullable=False, index=True)
    employee_no = Column(String, nullable=False)
    date_of_joining = Column(DateTime, nullable=False)
    comments = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100), default="taadmin", nullable=False)
    updated_by = Column(String(100), nullable=True)  # Removed default
    candidate = relationship("Candidate", back_populates="employee")
    
class GenderDB(Base):
    __tablename__ = "genders"

    id = Column(Integer, primary_key=True, index=True)
    gender = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)   
    created_by = Column(String(100), default="taadmin", nullable=False)
    updated_by = Column(String(100), nullable=True)  # Removed default and made nullable

################## ROLE BASED ACCESS CONTROL ##################

class RoleTemplate(Base):
    """Template for roles that can be saved and reused"""
    __tablename__ = "role_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    role_name = Column(String(200), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    is_super_admin = Column(Boolean, default=False)
    duration_days = Column(Integer, nullable=True)
    duration_months = Column(Integer, nullable=True)
    duration_years = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.now(timezone.utc))
    created_by = Column(String(100), default="taadmin", nullable=False)
    updated_by = Column(String(100), nullable=True)
    
    # Relationships
    user_roles = relationship("UserRole", back_populates="role_template")
    user_role_access = relationship("UserRoleAccess", back_populates="role_template")

class PageAccess(Base):
    """Access permissions for pages"""
    __tablename__ = "page_access"
    
    id = Column(Integer, primary_key=True, index=True)
    page_name = Column(String(100), nullable=False)
    can_view = Column(Boolean, default=False)
    can_edit = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.now(timezone.utc))
    created_by = Column(String(100), default="taadmin", nullable=False)
    updated_by = Column(String(100), nullable=True)

class SubpageAccess(Base):
    """Access permissions for subpages"""
    __tablename__ = "subpage_access"
    
    id = Column(Integer, primary_key=True, index=True)
    subpage_name = Column(String(100), nullable=False)
    can_view = Column(Boolean, default=False)
    can_edit = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.now(timezone.utc))
    created_by = Column(String(100), default="taadmin", nullable=False)
    updated_by = Column(String(100), nullable=True)

class SectionAccess(Base):
    """Access permissions for sections"""
    __tablename__ = "section_access"
    
    id = Column(Integer, primary_key=True, index=True)
    section_name = Column(String(100), nullable=False)
    can_view = Column(Boolean, default=False)
    can_edit = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.now(timezone.utc))
    created_by = Column(String(100), default="taadmin", nullable=False)
    updated_by = Column(String(100), nullable=True)

class UserRoleAccess(Base):
    """Main table for user role-based access control"""
    __tablename__ = "user_role_access"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role_template_id = Column(Integer, ForeignKey("role_templates.id"), nullable=True, index=True)
    role_name = Column(String(200), nullable=False)  # Custom role name for this user
    is_super_admin = Column(Boolean, default=False, index=True)
    
    # Email field for direct lookups
    email = Column(String(255), nullable=True, index=True)
    
    # Duration fields
    duration_days = Column(Integer, nullable=True)
    duration_months = Column(Integer, nullable=True)
    duration_years = Column(Integer, nullable=True)
    expiry_date = Column(DateTime, nullable=True, index=True)
    
    # Access permissions (stored as JSON for flexibility)
    page_access = Column(JSON, nullable=True)  # {"page_name": {"can_view": true, "can_edit": false}}
    subpage_access = Column(JSON, nullable=True)  # {"subpage_name": {"can_view": true, "can_edit": false}}
    section_access = Column(JSON, nullable=True)  # {"section_name": {"can_view": true, "can_edit": false}}
    
    # Job and department restrictions
    allowed_job_ids = Column(ARRAY(String), nullable=True)
    allowed_department_ids = Column(ARRAY(Integer), nullable=True)
    allowed_candidate_ids = Column(ARRAY(String), nullable=True)
    is_unrestricted = Column(Boolean, default=False, index=True)
    
    # Status and timestamps
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.now(timezone.utc))
    created_by = Column(String(100), default="taadmin", nullable=False)
    updated_by = Column(String(100), nullable=True)
    
    # Relationships
    user = relationship("User", backref="role_access")
    role_template = relationship("RoleTemplate", back_populates="user_role_access")
    
    __table_args__ = (
        Index('idx_user_role_access_email_lower', func.lower(email)),
        Index('idx_user_role_access_user_email', 'user_id', 'email'),
        Index('idx_user_role_access_email_role', 'email', 'role_name'),
    )

class ReferredByDB(Base):
    __tablename__ = "referred_by"

    id = Column(Integer, primary_key=True, index=True)
    referred_by = Column(String(255), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String(100), nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    updated_by = Column(String(100), nullable=True)

class InternalLog(Base):
    __tablename__ = "internal_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    page = Column(String(100), nullable=False)
    sub_page = Column(String(100), nullable=True)
    action = Column(String(200), nullable=False)
    action_type = Column(String(20), nullable=False)  # Create, Update, Delete
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    performed_by = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    related_value = Column(Text, nullable=True)
    # Optional associations
    job_id = Column(String(20), nullable=True)
    candidate_id = Column(String(20), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_internal_logs_timestamp', 'timestamp'),
        Index('idx_internal_logs_performed_by', 'performed_by'),
        Index('idx_internal_logs_action_type', 'action_type'),
        Index('idx_internal_logs_page', 'page'),
        Index('idx_internal_logs_job_id', 'job_id'),
        Index('idx_internal_logs_candidate_id', 'candidate_id'),
    )

class DataRetentionSettings(Base):
    __tablename__ = 'data_retention_settings'

    id = Column(Integer, primary_key=True)
    notification_retention_days = Column(Integer, nullable=False, default=30)
    logs_retention_days = Column(Integer, nullable=False, default=90)
    created_by = Column(String(200), nullable=False, default='system')
    created_on = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_by = Column(String(200), nullable=False, default='system')
    updated_on = Column(DateTime, nullable=True, default=None, onupdate=datetime.utcnow)

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)