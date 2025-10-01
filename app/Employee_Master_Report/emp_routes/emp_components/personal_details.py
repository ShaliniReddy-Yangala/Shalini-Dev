from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.Employee_Master_Report.emp_models.employee_master import EmployeeMaster
from app.Employee_Master_Report.emp_schema.employee_entry_schemas import (
    PersonalDetailsIn,
    PersonalDetailsOut
)
from datetime import datetime
import base64

router = APIRouter(prefix="/employee-entry", tags=["Employee Entry - Personal Details"])


def convert_dd_mm_yyyy_to_date(date_str):
    """Convert DD-MM-YYYY string to date object"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%d-%m-%Y").date()
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid date format. Use DD-MM-YYYY format. Received: {date_str}")


def format_date_to_dd_mm_yyyy(date_obj):
    """Convert date object to DD-MM-YYYY string"""
    if not date_obj:
        return None
    return date_obj.strftime("%d-%m-%Y")


@router.post("/personal-details", status_code=status.HTTP_201_CREATED, response_model=PersonalDetailsOut)
def create_personal_details(payload: PersonalDetailsIn, db: Session = Depends(get_db)):
    """Create or update personal details for an employee"""
    
    # Check if employee exists
    employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == payload.employee_id).first()
    
    if not employee:
        # Create new employee if doesn't exist
        employee = EmployeeMaster(
            employee_id=payload.employee_id,
            title=payload.title,
            first_name=payload.first_name,
            last_name=payload.last_name,
            full_name=payload.full_name,
            gender=payload.gender,
            dob=convert_dd_mm_yyyy_to_date(payload.dob),
            marital_status=payload.marital_status,
            doa=convert_dd_mm_yyyy_to_date(payload.doa),
            religion=payload.religion,
            blood_group=payload.blood_group,
            vaics_format_resume=(str(payload.resume_url) if payload.resume_url else None),
            mobile_no=payload.mobile_no,
            created_by="system",
            updated_by="system"
        )
        db.add(employee)
        message = "Employee created successfully"
    else:
        # Update personal details
        employee.title = payload.title
        employee.first_name = payload.first_name
        employee.last_name = payload.last_name
        employee.full_name = payload.full_name
        employee.gender = payload.gender
        employee.dob = convert_dd_mm_yyyy_to_date(payload.dob)
        employee.marital_status = payload.marital_status
        employee.doa = convert_dd_mm_yyyy_to_date(payload.doa)
        employee.religion = payload.religion
        employee.blood_group = payload.blood_group
        employee.vaics_format_resume = (str(payload.resume_url) if payload.resume_url else None)
        employee.mobile_no = payload.mobile_no
        employee.updated_by = "system"
        message = "Personal details updated successfully"
    
    db.commit()
    db.refresh(employee)
    
    return PersonalDetailsOut(
        employee_id=employee.employee_id,
        title=employee.title,
        first_name=employee.first_name,
        last_name=employee.last_name,
        full_name=employee.full_name,
        gender=employee.gender,
        dob=format_date_to_dd_mm_yyyy(employee.dob),
        marital_status=employee.marital_status,
        doa=format_date_to_dd_mm_yyyy(employee.doa),
        religion=employee.religion,
        blood_group=employee.blood_group,
        resume_url=employee.vaics_format_resume,
        mobile_no=employee.mobile_no,
        message=message
    )


@router.get("/personal-details/{employee_id}", response_model=PersonalDetailsOut)
def get_personal_details(employee_id: str, db: Session = Depends(get_db)):
    """Get personal details for an employee"""
    
    employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    return PersonalDetailsOut(
        employee_id=employee.employee_id,
        title=employee.title or "",
        first_name=employee.first_name or "",
        last_name=employee.last_name or "",
        full_name=employee.full_name or "",
        gender=employee.gender or "",
        dob=format_date_to_dd_mm_yyyy(employee.dob),
        marital_status=employee.marital_status,
        doa=format_date_to_dd_mm_yyyy(employee.doa),
        religion=employee.religion,
        blood_group=employee.blood_group,
        resume_url=employee.vaics_format_resume,
        mobile_no=employee.mobile_no,
        message="Personal details retrieved successfully"
    )


@router.put("/personal-details/{employee_id}", response_model=PersonalDetailsOut)
def update_personal_details(employee_id: str, payload: PersonalDetailsIn, db: Session = Depends(get_db)):
    """PUT variant to update personal details using path param employee_id."""
    if payload.employee_id and payload.employee_id != employee_id:
        raise HTTPException(status_code=400, detail="employee_id in path and body must match")

    employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    employee.title = payload.title
    employee.first_name = payload.first_name
    employee.last_name = payload.last_name
    employee.full_name = payload.full_name
    employee.gender = payload.gender
    employee.dob = convert_dd_mm_yyyy_to_date(payload.dob)
    employee.marital_status = payload.marital_status
    employee.doa = convert_dd_mm_yyyy_to_date(payload.doa)
    employee.religion = payload.religion
    employee.blood_group = payload.blood_group
    employee.vaics_format_resume = (str(payload.resume_url) if payload.resume_url else None)
    employee.mobile_no = payload.mobile_no
    employee.updated_by = "system"

    db.commit()
    db.refresh(employee)

    return PersonalDetailsOut(
        employee_id=employee.employee_id,
        title=employee.title or "",
        first_name=employee.first_name or "",
        last_name=employee.last_name or "",
        full_name=employee.full_name or "",
        gender=employee.gender or "",
        dob=format_date_to_dd_mm_yyyy(employee.dob),
        marital_status=employee.marital_status,
        doa=format_date_to_dd_mm_yyyy(employee.doa),
        religion=employee.religion,
        blood_group=employee.blood_group,
        resume_url=employee.vaics_format_resume,
        mobile_no=employee.mobile_no,
        message="Personal details updated successfully"
    )