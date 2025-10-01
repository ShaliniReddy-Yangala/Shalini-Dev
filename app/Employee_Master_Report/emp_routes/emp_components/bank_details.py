from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.Employee_Master_Report.emp_models.employee_master import EmployeeMaster
from app.Employee_Master_Report.emp_schema.employee_entry_schemas import (
    BankDetailsIn,
    BankDetailsOut
)

router = APIRouter(prefix="/employee-entry", tags=["Employee Entry - Bank Details"])


@router.post("/bank-details", status_code=status.HTTP_201_CREATED, response_model=BankDetailsOut)
def create_bank_details(payload: BankDetailsIn, db: Session = Depends(get_db)):
    """Create or update bank details for an employee"""
    
    # Check if employee exists
    employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == payload.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Update bank details
    employee.bank_name = payload.bank_name
    employee.account_no = payload.account_no
    employee.ifsc_code = payload.ifsc_code
    employee.type_of_account = payload.type_of_account
    employee.branch = payload.branch
    employee.updated_by = "system"
    
    db.commit()
    db.refresh(employee)
    
    return BankDetailsOut(
        employee_id=employee.employee_id,
        bank_name=employee.bank_name,
        account_no=employee.account_no,
        ifsc_code=employee.ifsc_code,
        type_of_account=employee.type_of_account,
        branch=employee.branch,
        message="Bank details updated successfully"
    )


@router.get("/bank-details/{employee_id}", response_model=BankDetailsOut)
def get_bank_details(employee_id: str, db: Session = Depends(get_db)):
    """Get bank details for an employee"""
    
    employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    return BankDetailsOut(
        employee_id=employee.employee_id,
        bank_name=employee.bank_name or "",
        account_no=employee.account_no or "",
        ifsc_code=employee.ifsc_code or "",
        type_of_account=employee.type_of_account or "",
        branch=employee.branch or "",
        message="Bank details retrieved successfully"
    )


@router.put("/bank-details/{employee_id}", response_model=BankDetailsOut)
def update_bank_details(employee_id: str, payload: BankDetailsIn, db: Session = Depends(get_db)):
    """PUT variant to update bank details using path param employee_id."""
    if payload.employee_id and payload.employee_id != employee_id:
        raise HTTPException(status_code=400, detail="employee_id in path and body must match")

    employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    employee.bank_name = payload.bank_name
    employee.account_no = payload.account_no
    employee.ifsc_code = payload.ifsc_code
    employee.type_of_account = payload.type_of_account
    employee.branch = payload.branch
    employee.updated_by = "system"

    db.commit()
    db.refresh(employee)

    return BankDetailsOut(
        employee_id=employee.employee_id,
        bank_name=employee.bank_name or "",
        account_no=employee.account_no or "",
        ifsc_code=employee.ifsc_code or "",
        type_of_account=employee.type_of_account or "",
        branch=employee.branch or "",
        message="Bank details updated successfully"
    )