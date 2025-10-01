from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.Employee_Master_Report.emp_models.employee_master import EmployeeMaster
from app.Employee_Master_Report.emp_schema.employee_entry_schemas import (
    SalaryDetailsIn,
    SalaryDetailsOut
)

router = APIRouter(prefix="/employee-entry", tags=["Employee Entry - Salary Details"])


@router.post("/salary-details", status_code=status.HTTP_201_CREATED, response_model=SalaryDetailsOut)
def create_salary_details(payload: SalaryDetailsIn, db: Session = Depends(get_db)):
    """Create or update salary details for an employee"""
    
    # Check if employee exists
    employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == payload.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Update salary details
    employee.gross_salary_per_month = payload.gross_salary_per_month
    employee.tax_regime = payload.tax_regime
    employee.updated_by = "system"
    
    db.commit()
    db.refresh(employee)
    
    return SalaryDetailsOut(
        employee_id=employee.employee_id,
        gross_salary_per_month=employee.gross_salary_per_month,
        tax_regime=employee.tax_regime,
        message="Salary details updated successfully"
    )


@router.get("/salary-details/{employee_id}", response_model=SalaryDetailsOut)
def get_salary_details(employee_id: str, db: Session = Depends(get_db)):
    """Get salary details for an employee"""
    
    employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    return SalaryDetailsOut(
        employee_id=employee.employee_id,
        gross_salary_per_month=employee.gross_salary_per_month or 0,
        tax_regime=employee.tax_regime or "New",
        message="Salary details retrieved successfully"
    )


@router.put("/salary-details/{employee_id}", response_model=SalaryDetailsOut)
def update_salary_details(employee_id: str, payload: SalaryDetailsIn, db: Session = Depends(get_db)):
    """PUT variant to update salary details using path param employee_id."""
    if payload.employee_id and payload.employee_id != employee_id:
        raise HTTPException(status_code=400, detail="employee_id in path and body must match")

    employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    employee.gross_salary_per_month = payload.gross_salary_per_month
    employee.tax_regime = payload.tax_regime
    employee.updated_by = "system"

    db.commit()
    db.refresh(employee)

    return SalaryDetailsOut(
        employee_id=employee.employee_id,
        gross_salary_per_month=employee.gross_salary_per_month,
        tax_regime=employee.tax_regime or "New",
        message="Salary details updated successfully"
    )