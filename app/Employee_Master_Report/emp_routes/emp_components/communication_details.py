from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.Employee_Master_Report.emp_models.employee_master import EmployeeMaster
from app.Employee_Master_Report.emp_schema.employee_entry_schemas import (
    CommunicationDetailsIn,
    CommunicationDetailsOut
)
from datetime import datetime

router = APIRouter(prefix="/employee-entry", tags=["Employee Entry - Communication Details"])


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


@router.post("/communication-details", status_code=status.HTTP_201_CREATED, response_model=CommunicationDetailsOut)
def create_communication_details(payload: CommunicationDetailsIn, db: Session = Depends(get_db)):
    """Create or update communication details for an employee"""
    
    # Check if employee exists
    employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == payload.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Validate PAN format if provided (ABCDE1234F)
    if payload.pan_card_no:
        pan_val = payload.pan_card_no.strip().upper()
        import re as _re
        if not _re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", pan_val):
            raise HTTPException(status_code=400, detail="Invalid PAN format. Expected: AAAAA9999A")
        payload.pan_card_no = pan_val
    
    # Validate Aadhar if provided: keep digits; must be 12 digits
    if payload.aadhar_no:
        digits = "".join(ch for ch in str(payload.aadhar_no) if ch.isdigit())
        if len(digits) != 12:
            raise HTTPException(status_code=400, detail="Aadhar must be 12 digits")
        payload.aadhar_no = digits
    
    # Check for duplicate PAN if provided
    if payload.pan_card_no:
        existing_pan = db.query(EmployeeMaster).filter(
            EmployeeMaster.pan_card_no == payload.pan_card_no.upper(),
            EmployeeMaster.employee_id != payload.employee_id
        ).first()
        if existing_pan:
            raise HTTPException(status_code=400, detail="PAN already exists for another employee")
    
    # Check for duplicate Aadhar if provided
    if payload.aadhar_no:
        existing_aadhar = db.query(EmployeeMaster).filter(
            EmployeeMaster.aadhar_no == payload.aadhar_no,
            EmployeeMaster.employee_id != payload.employee_id
        ).first()
        if existing_aadhar:
            raise HTTPException(status_code=400, detail="Aadhar already exists for another employee")
    
    # Update communication details
    employee.pan_card_no = payload.pan_card_no.upper() if payload.pan_card_no else None
    employee.aadhar_no = payload.aadhar_no
    employee.name_as_per_aadhar = payload.name_as_per_aadhar
    employee.passport_no = payload.passport_no
    employee.issued_date = convert_dd_mm_yyyy_to_date(payload.issued_date)
    employee.expiry_date = convert_dd_mm_yyyy_to_date(payload.expiry_date)
    employee.personal_email_id = payload.personal_email_id
    employee.mobile_no_comm = payload.mobile_no_comm
    employee.current_uan_no = payload.current_uan_no
    employee.updated_by = "system"
    
    db.commit()
    db.refresh(employee)
    
    return CommunicationDetailsOut(
        employee_id=employee.employee_id,
        pan_card_no=employee.pan_card_no,
        aadhar_no=employee.aadhar_no,
        name_as_per_aadhar=employee.name_as_per_aadhar,
        passport_no=employee.passport_no,
        issued_date=str(employee.issued_date) if employee.issued_date else None,
        expiry_date=format_date_to_dd_mm_yyyy(employee.expiry_date),
        personal_email_id=employee.personal_email_id,
        mobile_no_comm=employee.mobile_no_comm,
        current_uan_no=employee.current_uan_no,
        message="Communication details updated successfully"
    )


@router.get("/communication-details/{employee_id}", response_model=CommunicationDetailsOut)
def get_communication_details(employee_id: str, db: Session = Depends(get_db)):
    """Get communication details for an employee"""
    
    employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    return CommunicationDetailsOut(
        employee_id=employee.employee_id,
        pan_card_no=employee.pan_card_no,
        aadhar_no=employee.aadhar_no,
        name_as_per_aadhar=employee.name_as_per_aadhar,
        passport_no=employee.passport_no,
        issued_date=str(employee.issued_date) if employee.issued_date else None,
        expiry_date=format_date_to_dd_mm_yyyy(employee.expiry_date),
        personal_email_id=employee.personal_email_id,
        mobile_no_comm=employee.mobile_no_comm,
        current_uan_no=employee.current_uan_no,
        message="Communication details retrieved successfully"
    )


@router.put("/communication-details/{employee_id}", response_model=CommunicationDetailsOut)
def update_communication_details(employee_id: str, payload: CommunicationDetailsIn, db: Session = Depends(get_db)):
    """PUT variant to update communication details using path param employee_id."""
    if payload.employee_id and payload.employee_id != employee_id:
        raise HTTPException(status_code=400, detail="employee_id in path and body must match")

    employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Duplicate checks
    if payload.pan_card_no:
        pan_val = payload.pan_card_no.strip().upper()
        import re as _re
        if not _re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", pan_val):
            raise HTTPException(status_code=400, detail="Invalid PAN format. Expected: AAAAA9999A")
        existing_pan = db.query(EmployeeMaster).filter(
            EmployeeMaster.pan_card_no == pan_val,
            EmployeeMaster.employee_id != employee_id
        ).first()
        if existing_pan:
            raise HTTPException(status_code=400, detail="PAN already exists for another employee")
        payload.pan_card_no = pan_val
    if payload.aadhar_no:
        digits = "".join(ch for ch in str(payload.aadhar_no) if ch.isdigit())
        if len(digits) != 12:
            raise HTTPException(status_code=400, detail="Aadhar must be 12 digits")
        existing_aadhar = db.query(EmployeeMaster).filter(
            EmployeeMaster.aadhar_no == digits,
            EmployeeMaster.employee_id != employee_id
        ).first()
        if existing_aadhar:
            raise HTTPException(status_code=400, detail="Aadhar already exists for another employee")
        payload.aadhar_no = digits

    employee.pan_card_no = payload.pan_card_no.upper() if payload.pan_card_no else None
    employee.aadhar_no = payload.aadhar_no
    employee.name_as_per_aadhar = payload.name_as_per_aadhar
    employee.passport_no = payload.passport_no
    employee.issued_date = convert_dd_mm_yyyy_to_date(payload.issued_date)
    employee.expiry_date = convert_dd_mm_yyyy_to_date(payload.expiry_date)
    employee.personal_email_id = payload.personal_email_id
    employee.mobile_no_comm = payload.mobile_no_comm
    employee.current_uan_no = payload.current_uan_no
    employee.updated_by = "system"

    db.commit()
    db.refresh(employee)

    return CommunicationDetailsOut(
        employee_id=employee.employee_id,
        pan_card_no=employee.pan_card_no,
        aadhar_no=employee.aadhar_no,
        name_as_per_aadhar=employee.name_as_per_aadhar,
        passport_no=employee.passport_no,
        issued_date=str(employee.issued_date) if employee.issued_date else None,
        expiry_date=format_date_to_dd_mm_yyyy(employee.expiry_date),
        personal_email_id=employee.personal_email_id,
        mobile_no_comm=employee.mobile_no_comm,
        current_uan_no=employee.current_uan_no,
        message="Communication details updated successfully"
    )