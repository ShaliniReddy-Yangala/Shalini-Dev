from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.Employee_Master_Report.emp_models.employee_master import EmployeeMaster
from app.Employee_Master_Report.emp_schema.employee_entry_schemas import (
    HealthInsuranceIn,
    HealthInsuranceOut
)
from datetime import datetime

router = APIRouter(prefix="/employee-entry", tags=["Employee Entry - Health Insurance Details"])


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


@router.post("/health-insurance-details", status_code=status.HTTP_201_CREATED, response_model=HealthInsuranceOut)
def create_health_insurance_details(payload: HealthInsuranceIn, db: Session = Depends(get_db)):
    """Create or update health insurance details for an employee"""
    
    # Check if employee exists
    employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == payload.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Update health insurance details
    employee.policy_no = payload.policy_no
    employee.commencement_date = convert_dd_mm_yyyy_to_date(payload.commencement_date)
    employee.end_date = convert_dd_mm_yyyy_to_date(payload.end_date)
    employee.amount = payload.amount
    employee.covered_members = payload.covered_members
    employee.duration = payload.duration
    employee.insurer_name = payload.insurer_name
    employee.updated_by = "system"
    
    db.commit()
    db.refresh(employee)
    
    return HealthInsuranceOut(
        employee_id=employee.employee_id,
        policy_no=employee.policy_no,
        commencement_date=format_date_to_dd_mm_yyyy(employee.commencement_date),
        end_date=format_date_to_dd_mm_yyyy(employee.end_date),
        amount=employee.amount,
        covered_members=employee.covered_members,
        duration=employee.duration,
        insurer_name=employee.insurer_name,
        message="Health insurance details updated successfully"
    )


@router.get("/health-insurance-details/{employee_id}", response_model=HealthInsuranceOut)
def get_health_insurance_details(employee_id: str, db: Session = Depends(get_db)):
    """Get health insurance details for an employee"""
    
    employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    return HealthInsuranceOut(
        employee_id=employee.employee_id,
        policy_no=employee.policy_no or "",
        commencement_date=format_date_to_dd_mm_yyyy(employee.commencement_date) or "",
        end_date=format_date_to_dd_mm_yyyy(employee.end_date),
        amount=employee.amount,
        covered_members=employee.covered_members or 1,
        duration=employee.duration,
        insurer_name=employee.insurer_name or "",
        message="Health insurance details retrieved successfully"
    )


@router.put("/health-insurance-details/{employee_id}", response_model=HealthInsuranceOut)
def update_health_insurance_details(employee_id: str, payload: HealthInsuranceIn, db: Session = Depends(get_db)):
    """PUT variant to update health insurance details using path param employee_id."""
    if payload.employee_id and payload.employee_id != employee_id:
        raise HTTPException(status_code=400, detail="employee_id in path and body must match")

    employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    employee.policy_no = payload.policy_no
    employee.commencement_date = convert_dd_mm_yyyy_to_date(payload.commencement_date)
    employee.end_date = convert_dd_mm_yyyy_to_date(payload.end_date)
    employee.amount = payload.amount
    employee.covered_members = payload.covered_members
    employee.duration = payload.duration
    employee.insurer_name = payload.insurer_name
    employee.updated_by = "system"

    db.commit()
    db.refresh(employee)

    return HealthInsuranceOut(
        employee_id=employee.employee_id,
        policy_no=employee.policy_no or "",
        commencement_date=format_date_to_dd_mm_yyyy(employee.commencement_date) or "",
        end_date=format_date_to_dd_mm_yyyy(employee.end_date),
        amount=employee.amount,
        covered_members=employee.covered_members or 1,
        duration=employee.duration,
        insurer_name=employee.insurer_name or "",
        message="Health insurance details updated successfully"
    )