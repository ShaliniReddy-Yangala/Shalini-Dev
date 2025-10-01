from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


class CreateEmployeeBasicIn(BaseModel):
    title: str = Field(..., min_length=1)
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)
    full_name: str = Field(..., min_length=1)
    doj: date
    gender: str = Field(..., min_length=1)
    employee_id: Optional[str] = None
    pan_card_no: Optional[str] = None
    aadhar_no: Optional[str] = None
    personal_email_id: Optional[str] = None


class CreateEmployeeBasicOut(BaseModel):
    title: str
    message: str
    employee_id: str
    first_name: str
    last_name: str
    full_name: str
    doj: str
    gender: str
    pan_card_no: Optional[str] = None
    aadhar_no: Optional[str] = None
    personal_email_id: Optional[str] = None


class EmployeeBasicOut(BaseModel):
    title: str
    employee_id: str
    doj: str
    first_name: str
    last_name: str
    full_name: str
    gender: str
    pan_card_no: Optional[str] = None
    aadhar_no: Optional[str] = None

