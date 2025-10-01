from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.Employee_Master_Report.emp_models.employee_master import EmployeeMaster
from app.Employee_Master_Report.emp_schema.employee_entry_schemas import (
    ContractDetailsIn,
    ContractDetailsOut
)

router = APIRouter(prefix="/employee-entry", tags=["Employee Entry - Contract Details"])


@router.post("/contract-details", status_code=status.HTTP_201_CREATED, response_model=ContractDetailsOut)
def create_contract_details(payload: ContractDetailsIn, db: Session = Depends(get_db)):
    """Create or update contract details for an employee"""
    
    # Check if employee exists
    employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == payload.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Update contract details
    employee.job_type = payload.job_type
    employee.contract_end_date = payload.contract_end_date
    employee.probation_end_date = payload.probation_end_date
    employee.updated_by = "system"
    
    db.commit()
    db.refresh(employee)
    
    return ContractDetailsOut(
        employee_id=employee.employee_id,
        job_type=employee.job_type,
        contract_end_date=str(employee.contract_end_date) if employee.contract_end_date else None,
        probation_end_date=str(employee.probation_end_date) if employee.probation_end_date else None,
        message="Contract details updated successfully"
    )


@router.get("/contract-details/{employee_id}", response_model=ContractDetailsOut)
def get_contract_details(employee_id: str, db: Session = Depends(get_db)):
    """Get contract details for an employee"""
    
    employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    return ContractDetailsOut(
        employee_id=employee.employee_id,
        job_type=employee.job_type or "",
        contract_end_date=str(employee.contract_end_date) if employee.contract_end_date else None,
        probation_end_date=str(employee.probation_end_date) if employee.probation_end_date else None,
        message="Contract details retrieved successfully"
    )


@router.put("/contract-details/{employee_id}", response_model=ContractDetailsOut)
def update_contract_details(employee_id: str, payload: ContractDetailsIn, db: Session = Depends(get_db)):
    """PUT variant to update contract details using path param employee_id."""
    if payload.employee_id and payload.employee_id != employee_id:
        raise HTTPException(status_code=400, detail="employee_id in path and body must match")

    employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    employee.job_type = payload.job_type
    employee.contract_end_date = payload.contract_end_date
    employee.probation_end_date = payload.probation_end_date
    employee.updated_by = "system"

    db.commit()
    db.refresh(employee)

    return ContractDetailsOut(
        employee_id=employee.employee_id,
        job_type=employee.job_type or "",
        contract_end_date=str(employee.contract_end_date) if employee.contract_end_date else None,
        probation_end_date=str(employee.probation_end_date) if employee.probation_end_date else None,
        message="Contract details updated successfully"
    )