from pydantic import BaseModel, Field, EmailStr, validator, HttpUrl
from typing import Optional, List
from datetime import date
from decimal import Decimal
import re


# Basic Details Schema
class BasicDetailsIn(BaseModel):
    employee_id: str = Field(..., min_length=1)
    doj: str = Field(..., description="Date in DD-MM-YYYY format")
    designation: str = Field(..., min_length=1)
    department: str = Field(..., min_length=1)
    manager_name: str = Field(..., min_length=1)
    official_no: str = Field(..., min_length=1)
    official_email_id: EmailStr
    category: str = Field(..., min_length=1)
    excluded_from_payroll: str = Field(default="No")
    
    @validator('doj')
    def validate_doj(cls, v):
        if not re.match(r'^\d{2}-\d{2}-\d{4}$', v):
            raise ValueError('Date must be in DD-MM-YYYY format')
        return v


class BasicDetailsOut(BaseModel):
    employee_id: str
    doj: str
    designation: str
    department: str
    manager_name: str
    official_no: str
    official_email_id: str
    category: str
    excluded_from_payroll: str
    message: str


# Personal Details Schema
class PersonalDetailsIn(BaseModel):
    employee_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)
    full_name: str = Field(..., min_length=1)
    gender: str = Field(..., min_length=1)
    dob: Optional[str] = Field(None, description="Date in DD-MM-YYYY format")
    marital_status: Optional[str] = None
    doa: Optional[str] = Field(None, description="Date in DD-MM-YYYY format")
    religion: Optional[str] = None
    blood_group: Optional[str] = None
    mobile_no: Optional[str] = None
    resume_url: Optional[HttpUrl] = None
    
    @validator('dob', 'doa')
    def validate_dates(cls, v):
        if v and not re.match(r'^\d{2}-\d{2}-\d{4}$', v):
            raise ValueError('Date must be in DD-MM-YYYY format')
        return v

    @validator('resume_url')
    def ensure_https(cls, v):
        # Require https scheme if provided
        if v and not str(v).startswith("https://"):
            raise ValueError('resume_url must use https scheme')
        return v


class PersonalDetailsOut(BaseModel):
    employee_id: str
    title: str
    first_name: str
    last_name: str
    full_name: str
    gender: str
    dob: Optional[str] = None
    marital_status: Optional[str] = None
    doa: Optional[str] = None
    religion: Optional[str] = None
    blood_group: Optional[str] = None
    mobile_no: Optional[str] = None
    resume_url: Optional[str] = None
    message: str


# Address Details Schema
class AddressDetailsIn(BaseModel):
    employee_id: str = Field(..., min_length=1)
    permanent_address: 'AddressInfo'
    temporary_address: 'AddressInfo'
    office_address: 'AddressInfo'


class AddressInfo(BaseModel):
    address_type: str
    h_no: Optional[str] = None
    street: Optional[str] = None
    street2: Optional[str] = None
    landmark: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    complete_address: Optional[str] = None


class AddressDetailsOut(BaseModel):
    employee_id: str
    permanent_address: AddressInfo
    temporary_address: AddressInfo
    office_address: AddressInfo
    message: str


# Family Members Schema
class FamilyMemberIn(BaseModel):
    employee_id: str = Field(..., min_length=1)
    relation_type: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    dob: Optional[str] = Field(None, description="Date in DD-MM-YYYY format")
    aadhar_number: Optional[str] = None
    dependant: str = Field(default="No")
    
    @validator('dob')
    def validate_dob(cls, v):
        if v and not re.match(r'^\d{2}-\d{2}-\d{4}$', v):
            raise ValueError('Date must be in DD-MM-YYYY format')
        return v


class FamilyMemberOut(BaseModel):
    family_id: int
    employee_id: str
    relation_type: str
    name: str
    dob: Optional[str] = None
    aadhar_number: Optional[str] = None
    dependant: str
    message: str


# Education Details Schema
class EducationDetailsIn(BaseModel):
    employee_id: str = Field(..., min_length=1)
    type_of_degree: str = Field(..., min_length=1)
    course_name: str = Field(..., min_length=1)
    completed_in_month_year: Optional[str] = None
    school_college_name: str = Field(..., min_length=1)
    affiliated_university: Optional[str] = None
    certificate_url: Optional[HttpUrl] = None


class EducationDetailsOut(BaseModel):
    education_id: int
    employee_id: str
    type_of_degree: str
    course_name: str
    completed_in_month_year: Optional[str] = None
    school_college_name: str
    affiliated_university: Optional[str] = None
    certificate_url: Optional[str] = None
    message: str


# Previous Experience Schema
class ExperienceDetailsIn(BaseModel):
    employee_id: str = Field(..., min_length=1)
    company_name: str = Field(..., min_length=1)
    designation: str = Field(..., min_length=1)
    department: Optional[str] = None
    office_email_id: Optional[EmailStr] = None
    uan_no: Optional[str] = None
    start_date: str = Field(..., description="Date in DD-MM-YYYY format")
    end_date: Optional[str] = Field(None, description="Date in DD-MM-YYYY format")
    pf_no: Optional[str] = None
    company_address: Optional[str] = None
    reference_details_1: Optional[str] = None
    reference_details_2: Optional[str] = None
    
    @validator('start_date', 'end_date')
    def validate_dates(cls, v):
        if v and not re.match(r'^\d{2}-\d{2}-\d{4}$', v):
            raise ValueError('Date must be in DD-MM-YYYY format')
        return v


class ExperienceDetailsOut(BaseModel):
    experience_id: int
    employee_id: str
    company_name: str
    designation: str
    department: Optional[str] = None
    office_email_id: Optional[str] = None
    uan_no: Optional[str] = None
    start_date: str
    end_date: Optional[str] = None
    pf_no: Optional[str] = None
    company_address: Optional[str] = None
    reference_details_1: Optional[str] = None
    reference_details_2: Optional[str] = None
    message: str


# Contract Details Schema
class ContractDetailsIn(BaseModel):
    employee_id: str = Field(..., min_length=1)
    job_type: str = Field(..., min_length=1)
    contract_end_date: Optional[date] = None
    probation_end_date: Optional[date] = None


class ContractDetailsOut(BaseModel):
    employee_id: str
    job_type: str
    contract_end_date: Optional[str] = None
    probation_end_date: Optional[str] = None
    message: str


# Bank Details Schema
class BankDetailsIn(BaseModel):
    employee_id: str = Field(..., min_length=1)
    bank_name: str = Field(..., min_length=1)
    account_no: str = Field(..., min_length=1)
    ifsc_code: str = Field(..., min_length=1)
    type_of_account: str = Field(..., min_length=1)
    branch: str = Field(..., min_length=1)


class BankDetailsOut(BaseModel):
    employee_id: str
    bank_name: str
    account_no: str
    ifsc_code: str
    type_of_account: str
    branch: str
    message: str


# Communication Details Schema
class CommunicationDetailsIn(BaseModel):
    employee_id: str = Field(..., min_length=1)
    pan_card_no: Optional[str] = None
    aadhar_no: Optional[str] = None
    name_as_per_aadhar: Optional[str] = None
    passport_no: Optional[str] = None
    issued_date: Optional[str] = Field(None, description="Date in DD-MM-YYYY format")
    expiry_date: Optional[str] = Field(None, description="Date in DD-MM-YYYY format")
    personal_email_id: Optional[EmailStr] = None
    mobile_no_comm: Optional[str] = None
    current_uan_no: Optional[str] = None
    
    @validator('issued_date', 'expiry_date')
    def validate_dates(cls, v):
        if v and not re.match(r'^\d{2}-\d{2}-\d{4}$', v):
            raise ValueError('Date must be in DD-MM-YYYY format')
        return v


class CommunicationDetailsOut(BaseModel):
    employee_id: str
    pan_card_no: Optional[str] = None
    aadhar_no: Optional[str] = None
    name_as_per_aadhar: Optional[str] = None
    passport_no: Optional[str] = None
    issued_date: Optional[str] = None
    expiry_date: Optional[str] = None
    personal_email_id: Optional[str] = None
    mobile_no_comm: Optional[str] = None
    current_uan_no: Optional[str] = None
    message: str


# Nominee Details Schema
class NomineeDetailsIn(BaseModel):
    employee_id: str = Field(..., min_length=1)
    nominee_name: str = Field(..., min_length=1)
    nominee_address: str = Field(..., min_length=1)
    nominee_relation: str = Field(..., min_length=1)
    nominee_age: int = Field(..., ge=0, le=120)
    nominee_proportion: Decimal = Field(..., ge=0, le=100)


class NomineeDetailsOut(BaseModel):
    employee_id: str
    nominee_name: str
    nominee_address: str
    nominee_relation: str
    nominee_age: int
    nominee_proportion: Decimal
    message: str


# Salary Details Schema
class SalaryDetailsIn(BaseModel):
    employee_id: str = Field(..., min_length=1)
    gross_salary_per_month: Decimal = Field(..., gt=0)
    tax_regime: str = Field(default="New")


class SalaryDetailsOut(BaseModel):
    employee_id: str
    gross_salary_per_month: Decimal
    tax_regime: str
    message: str


# Emergency Contact Schema
class EmergencyContactIn(BaseModel):
    employee_id: str = Field(..., min_length=1)
    emergency_contact_name: str = Field(..., min_length=1)
    emergency_contact_relation: str = Field(..., min_length=1)
    emergency_contact_no: str = Field(..., min_length=1)


class EmergencyContactOut(BaseModel):
    employee_id: str
    emergency_contact_name: str
    emergency_contact_relation: str
    emergency_contact_no: str
    message: str


# Onboarding Details Schema
class OnboardingDetailsIn(BaseModel):
    employee_id: str = Field(..., min_length=1)
    client_name: str = Field(..., min_length=1)
    effective_start_date: date
    effective_end_date: Optional[date] = None
    onboarding_status: str = Field(..., min_length=1)
    duration_calculated: Optional[str] = None
    spoc: str = Field(..., min_length=1)
    onboarding_department: str = Field(..., min_length=1)
    assigned_manager: str = Field(..., min_length=1)


class OnboardingDetailsOut(BaseModel):
    onboarding_id: int
    employee_id: str
    client_name: str
    effective_start_date: str
    effective_end_date: Optional[str] = None
    onboarding_status: str
    duration_calculated: Optional[str] = None
    spoc: str
    onboarding_department: str
    assigned_manager: str
    message: str


# Asset Details Schema
class AssetDetailsIn(BaseModel):
    employee_id: str = Field(..., min_length=1)
    asset_type: str = Field(..., min_length=1)
    asset_number: str = Field(..., min_length=1)
    issued_date: date
    status: str = Field(default="Issued")


class AssetDetailsOut(BaseModel):
    asset_id: int
    employee_id: str
    asset_type: str
    asset_number: str
    issued_date: str
    status: str
    message: str


# Health Insurance Schema
class HealthInsuranceIn(BaseModel):
    employee_id: str = Field(..., min_length=1)
    policy_no: str = Field(..., min_length=1)
    commencement_date: str = Field(..., description="Date in DD-MM-YYYY format")
    end_date: Optional[str] = Field(None, description="Date in DD-MM-YYYY format")
    amount: Optional[Decimal] = None
    covered_members: int = Field(default=1, ge=1)
    duration: Optional[str] = None
    insurer_name: str = Field(..., min_length=1)
    
    @validator('commencement_date', 'end_date')
    def validate_dates(cls, v):
        if v and not re.match(r'^\d{2}-\d{2}-\d{4}$', v):
            raise ValueError('Date must be in DD-MM-YYYY format')
        return v


class HealthInsuranceOut(BaseModel):
    employee_id: str
    policy_no: str
    commencement_date: str
    end_date: Optional[str] = None
    amount: Optional[Decimal] = None
    covered_members: int
    duration: Optional[str] = None
    insurer_name: str
    message: str


# Update forward references
AddressDetailsIn.model_rebuild()
