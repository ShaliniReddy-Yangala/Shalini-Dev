from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.Employee_Master_Report.emp_models.employee_master import EmployeeMaster, ExperienceHistory
from app.Employee_Master_Report.emp_schema.employee_entry_schemas import (
    ExperienceDetailsIn,
    ExperienceDetailsOut
)
from datetime import datetime

router = APIRouter(prefix="/employee-entry", tags=["Employee Entry - Experience Details"])


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


@router.post("/experience-details", status_code=status.HTTP_201_CREATED, response_model=ExperienceDetailsOut)
def create_experience_details(payload: ExperienceDetailsIn, db: Session = Depends(get_db)):
    """Create a new experience record for an employee"""
    
    # Check if employee exists
    employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == payload.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Create experience history
    experience = ExperienceHistory(
        employee_id=payload.employee_id,
        company_name=payload.company_name,
        designation=payload.designation,
        department=payload.department,
        office_email_id=payload.office_email_id,
        uan_no=payload.uan_no,
        start_date=convert_dd_mm_yyyy_to_date(payload.start_date),
        end_date=convert_dd_mm_yyyy_to_date(payload.end_date),
        created_by="system",
        updated_by="system"
    )
    
    db.add(experience)
    db.commit()
    db.refresh(experience)
    
    return ExperienceDetailsOut(
        experience_id=experience.experience_id,
        employee_id=experience.employee_id,
        company_name=experience.company_name,
        designation=experience.designation,
        department=experience.department,
        office_email_id=experience.office_email_id,
        uan_no=experience.uan_no,
        start_date=format_date_to_dd_mm_yyyy(experience.start_date),
        end_date=format_date_to_dd_mm_yyyy(experience.end_date),
        pf_no=payload.pf_no,
        company_address=payload.company_address,
        reference_details_1=payload.reference_details_1,
        reference_details_2=payload.reference_details_2,
        message="Experience details added successfully"
    )


@router.get("/experience-details/{employee_id}", response_model=list[ExperienceDetailsOut])
def get_experience_details(employee_id: str, db: Session = Depends(get_db)):
    """Get all experience records for an employee"""
    
    # Check if employee exists
    employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    experience_records = db.query(ExperienceHistory).filter(
        ExperienceHistory.employee_id == employee_id
    ).order_by(ExperienceHistory.start_date.desc()).all()
    
    result = []
    for experience in experience_records:
        result.append(ExperienceDetailsOut(
            experience_id=experience.experience_id,
            employee_id=experience.employee_id,
            company_name=experience.company_name,
            designation=experience.designation,
            department=experience.department,
            office_email_id=experience.office_email_id,
            uan_no=experience.uan_no,
            start_date=format_date_to_dd_mm_yyyy(experience.start_date),
            end_date=format_date_to_dd_mm_yyyy(experience.end_date),
            pf_no=employee.pf_no,
            company_address=employee.company_address,
            reference_details_1=employee.reference_details_1,
            reference_details_2=employee.reference_details_2,
            message="Experience details retrieved successfully"
        ))
    
    return result


@router.put("/experience-details/{experience_id}", response_model=ExperienceDetailsOut)
def update_experience_details(experience_id: int, payload: ExperienceDetailsIn, db: Session = Depends(get_db)):
    """Update an experience record"""
    
    experience = db.query(ExperienceHistory).filter(ExperienceHistory.experience_id == experience_id).first()
    if not experience:
        raise HTTPException(status_code=404, detail="Experience record not found")
    
    # Update experience record
    experience.company_name = payload.company_name
    experience.designation = payload.designation
    experience.department = payload.department
    experience.office_email_id = payload.office_email_id
    experience.uan_no = payload.uan_no
    experience.start_date = convert_dd_mm_yyyy_to_date(payload.start_date)
    experience.end_date = convert_dd_mm_yyyy_to_date(payload.end_date)
    experience.updated_by = "system"
    
    # Update employee master with additional fields
    employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == payload.employee_id).first()
    if employee:
        employee.pf_no = payload.pf_no
        employee.company_address = payload.company_address
        employee.reference_details_1 = payload.reference_details_1
        employee.reference_details_2 = payload.reference_details_2
        employee.updated_by = "system"
    
    db.commit()
    db.refresh(experience)
    
    return ExperienceDetailsOut(
        experience_id=experience.experience_id,
        employee_id=experience.employee_id,
        company_name=experience.company_name,
        designation=experience.designation,
        department=experience.department,
        office_email_id=experience.office_email_id,
        uan_no=experience.uan_no,
        start_date=format_date_to_dd_mm_yyyy(experience.start_date),
        end_date=format_date_to_dd_mm_yyyy(experience.end_date),
        pf_no=payload.pf_no,
        company_address=payload.company_address,
        reference_details_1=payload.reference_details_1,
        reference_details_2=payload.reference_details_2,
        message="Experience details updated successfully"
    )


@router.delete("/experience-details/{experience_id}")
def delete_experience_details(experience_id: int, db: Session = Depends(get_db)):
    """Delete an experience record"""
    
    experience = db.query(ExperienceHistory).filter(ExperienceHistory.experience_id == experience_id).first()
    if not experience:
        raise HTTPException(status_code=404, detail="Experience record not found")
    
    db.delete(experience)
    db.commit()
    
    return {"message": "Experience record deleted successfully"}
