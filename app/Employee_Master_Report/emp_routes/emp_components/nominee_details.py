from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.Employee_Master_Report.emp_models.employee_master import EmployeeMaster
from app.Employee_Master_Report.emp_schema.employee_entry_schemas import (
    NomineeDetailsIn,
    NomineeDetailsOut
)

router = APIRouter(prefix="/employee-entry", tags=["Employee Entry - Nominee Details"])


@router.post("/nominee-details", status_code=status.HTTP_201_CREATED, response_model=NomineeDetailsOut)
def create_nominee_details(payload: NomineeDetailsIn, db: Session = Depends(get_db)):
    """Create or update nominee details for an employee"""
    
    # Check if employee exists
    employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == payload.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Update nominee details
    employee.nominee_name = payload.nominee_name
    employee.nominee_address = payload.nominee_address
    employee.nominee_relation = payload.nominee_relation
    employee.nominee_age = payload.nominee_age
    employee.nominee_proportion = payload.nominee_proportion
    employee.updated_by = "system"
    
    db.commit()
    db.refresh(employee)
    
    return NomineeDetailsOut(
        employee_id=employee.employee_id,
        nominee_name=employee.nominee_name,
        nominee_address=employee.nominee_address,
        nominee_relation=employee.nominee_relation,
        nominee_age=employee.nominee_age,
        nominee_proportion=employee.nominee_proportion,
        message="Nominee details updated successfully"
    )


@router.get("/nominee-details/{employee_id}", response_model=NomineeDetailsOut)
def get_nominee_details(employee_id: str, db: Session = Depends(get_db)):
    """Get nominee details for an employee"""
    
    employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    return NomineeDetailsOut(
        employee_id=employee.employee_id,
        nominee_name=employee.nominee_name or "",
        nominee_address=employee.nominee_address or "",
        nominee_relation=employee.nominee_relation or "",
        nominee_age=employee.nominee_age or 0,
        nominee_proportion=employee.nominee_proportion or 0,
        message="Nominee details retrieved successfully"
    )


@router.put("/nominee-details/{employee_id}", response_model=NomineeDetailsOut)
def update_nominee_details(employee_id: str, payload: NomineeDetailsIn, db: Session = Depends(get_db)):
    """PUT variant to update nominee details using path param employee_id."""
    if payload.employee_id and payload.employee_id != employee_id:
        raise HTTPException(status_code=400, detail="employee_id in path and body must match")

    employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    employee.nominee_name = payload.nominee_name
    employee.nominee_address = payload.nominee_address
    employee.nominee_relation = payload.nominee_relation
    employee.nominee_age = payload.nominee_age
    employee.nominee_proportion = payload.nominee_proportion
    employee.updated_by = "system"

    db.commit()
    db.refresh(employee)

    return NomineeDetailsOut(
        employee_id=employee.employee_id,
        nominee_name=employee.nominee_name or "",
        nominee_address=employee.nominee_address or "",
        nominee_relation=employee.nominee_relation or "",
        nominee_age=employee.nominee_age or 0,
        nominee_proportion=employee.nominee_proportion or 0,
        message="Nominee details updated successfully"
    )