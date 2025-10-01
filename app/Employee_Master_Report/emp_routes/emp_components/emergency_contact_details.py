from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.Employee_Master_Report.emp_models.employee_master import EmployeeMaster
from app.Employee_Master_Report.emp_schema.employee_entry_schemas import (
    EmergencyContactIn,
    EmergencyContactOut
)

router = APIRouter(prefix="/employee-entry", tags=["Employee Entry - Emergency Contact Details"])


@router.post("/emergency-contact-details", status_code=status.HTTP_201_CREATED, response_model=EmergencyContactOut)
def create_emergency_contact_details(payload: EmergencyContactIn, db: Session = Depends(get_db)):
    """Create or update emergency contact details for an employee"""
    
    # Check if employee exists
    employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == payload.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Update emergency contact details
    employee.emergency_contact_name = payload.emergency_contact_name
    employee.emergency_contact_relation = payload.emergency_contact_relation
    employee.emergency_contact_no = payload.emergency_contact_no
    employee.updated_by = "system"
    
    db.commit()
    db.refresh(employee)
    
    return EmergencyContactOut(
        employee_id=employee.employee_id,
        emergency_contact_name=employee.emergency_contact_name,
        emergency_contact_relation=employee.emergency_contact_relation,
        emergency_contact_no=employee.emergency_contact_no,
        message="Emergency contact details updated successfully"
    )


@router.get("/emergency-contact-details/{employee_id}", response_model=EmergencyContactOut)
def get_emergency_contact_details(employee_id: str, db: Session = Depends(get_db)):
    """Get emergency contact details for an employee"""
    
    employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    return EmergencyContactOut(
        employee_id=employee.employee_id,
        emergency_contact_name=employee.emergency_contact_name or "",
        emergency_contact_relation=employee.emergency_contact_relation or "",
        emergency_contact_no=employee.emergency_contact_no or "",
        message="Emergency contact details retrieved successfully"
    )
