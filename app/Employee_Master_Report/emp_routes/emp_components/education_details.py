from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.Employee_Master_Report.emp_models.employee_master import EmployeeMaster, EducationHistory
from app.Employee_Master_Report.emp_schema.employee_entry_schemas import (
    EducationDetailsIn,
    EducationDetailsOut
)

router = APIRouter(prefix="/employee-entry", tags=["Employee Entry - Education Details"])


@router.post("/education-details", status_code=status.HTTP_201_CREATED, response_model=EducationDetailsOut)
def create_education_details(payload: EducationDetailsIn, db: Session = Depends(get_db)):
    """Create a new education record for an employee"""
    
    # Check if employee exists
    employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == payload.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Create education history
    education = EducationHistory(
        employee_id=payload.employee_id,
        type_of_degree=payload.type_of_degree,
        course_name=payload.course_name,
        completed_in_month_year=payload.completed_in_month_year,
        school_college_name=payload.school_college_name,
        affiliated_university=payload.affiliated_university,
        certificate_url=(str(payload.certificate_url) if payload.certificate_url else None),
        created_by="system",
        updated_by="system"
    )
    
    db.add(education)
    db.commit()
    db.refresh(education)
    
    return EducationDetailsOut(
        education_id=education.education_id,
        employee_id=education.employee_id,
        type_of_degree=education.type_of_degree,
        course_name=education.course_name,
        completed_in_month_year=education.completed_in_month_year,
        school_college_name=education.school_college_name,
        affiliated_university=education.affiliated_university,
        certificate_url=education.certificate_url,
        message="Education details added successfully"
    )


@router.get("/education-details/{employee_id}", response_model=list[EducationDetailsOut])
def get_education_details(employee_id: str, db: Session = Depends(get_db)):
    """Get all education records for an employee"""
    
    # Check if employee exists
    employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    education_records = db.query(EducationHistory).filter(
        EducationHistory.employee_id == employee_id
    ).order_by(EducationHistory.completed_in_month_year.desc()).all()
    
    result = []
    for education in education_records:
        result.append(EducationDetailsOut(
            education_id=education.education_id,
            employee_id=education.employee_id,
            type_of_degree=education.type_of_degree,
            course_name=education.course_name,
            completed_in_month_year=education.completed_in_month_year,
            school_college_name=education.school_college_name,
            affiliated_university=education.affiliated_university,
            certificate_url=education.certificate_url,
            message="Education details retrieved successfully"
        ))
    
    return result


@router.put("/education-details/{education_id}", response_model=EducationDetailsOut)
def update_education_details(education_id: int, payload: EducationDetailsIn, db: Session = Depends(get_db)):
    """Update an education record"""
    
    education = db.query(EducationHistory).filter(EducationHistory.education_id == education_id).first()
    if not education:
        raise HTTPException(status_code=404, detail="Education record not found")
    
    # Update education record
    education.type_of_degree = payload.type_of_degree
    education.course_name = payload.course_name
    education.completed_in_month_year = payload.completed_in_month_year
    education.school_college_name = payload.school_college_name
    education.affiliated_university = payload.affiliated_university
    education.certificate_url = (str(payload.certificate_url) if payload.certificate_url else None)
    education.updated_by = "system"
    
    db.commit()
    db.refresh(education)
    
    return EducationDetailsOut(
        education_id=education.education_id,
        employee_id=education.employee_id,
        type_of_degree=education.type_of_degree,
        course_name=education.course_name,
        completed_in_month_year=education.completed_in_month_year,
        school_college_name=education.school_college_name,
        affiliated_university=education.affiliated_university,
        certificate_url=education.certificate_url,
        message="Education details updated successfully"
    )


@router.delete("/education-details/{education_id}")
def delete_education_details(education_id: int, db: Session = Depends(get_db)):
    """Delete an education record"""
    
    education = db.query(EducationHistory).filter(EducationHistory.education_id == education_id).first()
    if not education:
        raise HTTPException(status_code=404, detail="Education record not found")
    
    db.delete(education)
    db.commit()
    
    return {"message": "Education record deleted successfully"}
