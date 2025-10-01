from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.Employee_Master_Report.emp_models.employee_master import EmployeeMaster
from app.Employee_Master_Report.emp_schema.employee_entry_schemas import (
    BasicDetailsIn,
    BasicDetailsOut,
    PersonalDetailsIn
)
from datetime import datetime

router = APIRouter(prefix="/employee-entry", tags=["Employee Entry - Basic Details"])


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


@router.post("/create-employee", status_code=status.HTTP_201_CREATED)
def create_employee_with_details(
    request_data: dict,
    db: Session = Depends(get_db)
):
    """Create a new employee with both personal and basic details"""
    
    # Extract data from request
    personal_data = request_data.get("personal_data", {})
    basic_data = request_data.get("basic_data", {})
    
    if not personal_data or not basic_data:
        raise HTTPException(status_code=400, detail="Both personal_data and basic_data are required")
    
    # Validate required fields
    if not personal_data.get("employee_id"):
        raise HTTPException(status_code=400, detail="employee_id is required in personal_data")
    
    if not basic_data.get("employee_id"):
        raise HTTPException(status_code=400, detail="employee_id is required in basic_data")
    
    if personal_data.get("employee_id") != basic_data.get("employee_id"):
        raise HTTPException(status_code=400, detail="employee_id must be the same in both personal_data and basic_data")
    
    # Check if employee already exists
    existing_employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == personal_data["employee_id"]).first()
    if existing_employee:
        raise HTTPException(status_code=400, detail="Employee with this ID already exists")
    
    # Check if official email already exists
    existing_email = db.query(EmployeeMaster).filter(
        EmployeeMaster.official_email_id == basic_data["official_email_id"]
    ).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Official email already exists")
    
    # Create new employee with both personal and basic details
    employee = EmployeeMaster(
        employee_id=personal_data["employee_id"],
        title=personal_data.get("title"),
        first_name=personal_data["first_name"],
        last_name=personal_data["last_name"],
        full_name=personal_data["full_name"],
        gender=personal_data["gender"],
        dob=convert_dd_mm_yyyy_to_date(personal_data.get("dob")),
        marital_status=personal_data.get("marital_status"),
        doa=convert_dd_mm_yyyy_to_date(personal_data.get("doa")),
        religion=personal_data.get("religion"),
        blood_group=personal_data.get("blood_group"),
        mobile_no=personal_data.get("mobile_no"),
        doj=convert_dd_mm_yyyy_to_date(basic_data["doj"]),
        designation=basic_data["designation"],
        department=basic_data["department"],
        manager_name=basic_data["manager_name"],
        official_no=basic_data["official_no"],
        official_email_id=basic_data["official_email_id"],
        category=basic_data["category"],
        excluded_from_payroll=basic_data.get("excluded_from_payroll", "No"),
        created_by="system",
        updated_by="system"
    )
    
    db.add(employee)
    db.commit()
    db.refresh(employee)
    
    return {
        "message": "Employee created successfully",
        "employee_id": employee.employee_id,
            "personal_details": {
                "title": employee.title,
                "first_name": employee.first_name,
                "last_name": employee.last_name,
                "full_name": employee.full_name,
                "gender": employee.gender,
                "dob": format_date_to_dd_mm_yyyy(employee.dob),
                "marital_status": employee.marital_status,
                "doa": format_date_to_dd_mm_yyyy(employee.doa),
                "religion": employee.religion,
                "blood_group": employee.blood_group,
                "mobile_no": employee.mobile_no
            },
            "basic_details": {
                "doj": format_date_to_dd_mm_yyyy(employee.doj),
                "designation": employee.designation,
                "department": employee.department,
                "manager_name": employee.manager_name,
                "official_no": employee.official_no,
                "official_email_id": employee.official_email_id,
                "category": employee.category,
                "excluded_from_payroll": employee.excluded_from_payroll
            }
    }


@router.post("/basic-details", status_code=status.HTTP_201_CREATED, response_model=BasicDetailsOut)
def create_basic_details(payload: BasicDetailsIn, db: Session = Depends(get_db)):
    """Create or update basic details for an employee"""
    
    # Check if employee exists
    employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == payload.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found. Please create employee first using personal details or basic employee creation endpoint.")
    
    # Check if official email already exists for another employee
    existing_email = db.query(EmployeeMaster).filter(
        EmployeeMaster.official_email_id == payload.official_email_id,
        EmployeeMaster.employee_id != payload.employee_id
    ).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Official email already exists for another employee")
    
    # Update basic details
    employee.doj = convert_dd_mm_yyyy_to_date(payload.doj)
    employee.designation = payload.designation
    employee.department = payload.department
    employee.manager_name = payload.manager_name
    employee.official_no = payload.official_no
    employee.official_email_id = payload.official_email_id
    employee.category = payload.category
    employee.excluded_from_payroll = payload.excluded_from_payroll
    employee.updated_by = "system"
    
    db.commit()
    db.refresh(employee)
    
    return BasicDetailsOut(
        employee_id=employee.employee_id,
        doj=format_date_to_dd_mm_yyyy(employee.doj),
        designation=employee.designation,
        department=employee.department,
        manager_name=employee.manager_name,
        official_no=employee.official_no,
        official_email_id=employee.official_email_id,
        category=employee.category,
        excluded_from_payroll=employee.excluded_from_payroll,
        message="Basic details updated successfully"
    )


@router.put("/basic-details/{employee_id}", response_model=BasicDetailsOut)
def update_basic_details(
    employee_id: str,
    payload: BasicDetailsIn,
    db: Session = Depends(get_db)
):
    """PUT variant to update basic details using path param employee_id."""
    # Ensure path and payload IDs align
    if payload.employee_id and payload.employee_id != employee_id:
        raise HTTPException(status_code=400, detail="employee_id in path and body must match")

    employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Check official email uniqueness for other employees
    existing_email = db.query(EmployeeMaster).filter(
        EmployeeMaster.official_email_id == payload.official_email_id,
        EmployeeMaster.employee_id != employee_id
    ).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Official email already exists for another employee")

    # Update fields
    employee.doj = convert_dd_mm_yyyy_to_date(payload.doj)
    employee.designation = payload.designation
    employee.department = payload.department
    employee.manager_name = payload.manager_name
    employee.official_no = payload.official_no
    employee.official_email_id = payload.official_email_id
    employee.category = payload.category
    employee.excluded_from_payroll = payload.excluded_from_payroll
    employee.updated_by = "system"

    db.commit()
    db.refresh(employee)

    return BasicDetailsOut(
        employee_id=employee.employee_id,
        doj=format_date_to_dd_mm_yyyy(employee.doj) or "",
        designation=employee.designation or "",
        department=employee.department or "",
        manager_name=employee.manager_name or "",
        official_no=employee.official_no or "",
        official_email_id=employee.official_email_id or "",
        category=employee.category or "",
        excluded_from_payroll=employee.excluded_from_payroll or "No",
        message="Basic details updated successfully"
    )

@router.get("/basic-details/{employee_id}", response_model=BasicDetailsOut)
def get_basic_details(employee_id: str, db: Session = Depends(get_db)):
    """Get basic details for an employee"""
    
    employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    return BasicDetailsOut(
        employee_id=employee.employee_id,
        doj=format_date_to_dd_mm_yyyy(employee.doj) or "",
        designation=employee.designation or "",
        department=employee.department or "",
        manager_name=employee.manager_name or "",
        official_no=employee.official_no or "",
        official_email_id=employee.official_email_id or "",
        category=employee.category or "",
        excluded_from_payroll=employee.excluded_from_payroll or "No",
        message="Basic details retrieved successfully"
    )
