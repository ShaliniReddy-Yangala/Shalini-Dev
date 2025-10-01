from typing import Optional, Union
from decimal import Decimal
from datetime import date, datetime
from datetime import date
from pydantic import BaseModel


class CandidateOnboardOut(BaseModel):
    candidate_id: str
    candidate_name: str
    email_id: Optional[str] = None
    mobile_no: Optional[str] = None
    pan_card_no: Optional[str] = None
    resume_path: Optional[str] = None
    resume_url: Optional[str] = None
    date_of_resume_received: Optional[date] = None
    associated_job_id: Optional[str] = None
    application_date: Optional[date] = None
    skills_set: Optional[str] = None
    current_company: Optional[str] = None
    current_designation: Optional[str] = None
    department: Optional[str] = None
    years_of_exp: Optional[float] = None
    status: Optional[str] = None
    notice_period: Optional[Union[str, int]] = None
    notice_period_units: Optional[str] = None
    npd_info: Optional[str] = None
    current_fixed_ctc: Optional[float] = None
    current_variable_pay: Optional[float] = None
    expected_fixed_ctc: Optional[float] = None
    mode_of_work: Optional[str] = None
    gender: Optional[str] = None
    reason_for_job_change: Optional[str] = None
    current_address: Optional[str] = None
    current_location: Optional[str] = None
    permanent_address: Optional[str] = None
    ta_team: Optional[str] = None
    ta_comments: Optional[str] = None
    rating: Optional[str] = None

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
    hr_feedback: Optional[str] = None

    expected_ctc: Optional[Union[str, float, int, Decimal]] = None
    final_offer_ctc: Optional[Union[str, float, int, Decimal]] = None
    ctc_breakup_sent_date: Optional[date] = None
    offer_initiated_date: Optional[date] = None
    offer_status: Optional[str] = None
    offer_accepted_rejected_date: Optional[date] = None

    date_of_joining: Optional[str] = None
    current_status: Optional[str] = None
    status_updated_on: Optional[date] = None
    rejected_date: Optional[date] = None
    final_status: Optional[str] = None

    created_at: Optional[Union[date, datetime, str]] = None
    updated_at: Optional[Union[date, datetime, str]] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    linkedin_url: Optional[str] = None
    referred_by: Optional[str] = None

    class Config:
        from_attributes = True


