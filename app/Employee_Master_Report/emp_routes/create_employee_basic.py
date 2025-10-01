from fastapi import APIRouter, Depends, HTTPException, status, Query
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Integer

from app.database import get_db
from app.Employee_Master_Report.emp_models.employee_master import EmployeeMaster
from app.Employee_Master_Report.emp_schema.employee_basic import (
    CreateEmployeeBasicIn,
    CreateEmployeeBasicOut,
    EmployeeBasicOut,
)


router = APIRouter(prefix="/employee-master", tags=["Employee Master Report"])


def _generate_employee_id(db: Session) -> str:
    SERIES_START = 759000
    SERIES_END = 759999

    # Get current max in the series
    max_id_row = (
        db.query(func.max(cast(EmployeeMaster.employee_id, Integer)))
        .filter(EmployeeMaster.employee_id >= str(SERIES_START))
        .filter(EmployeeMaster.employee_id <= str(SERIES_END))
        .one()
    )

    current_max = max_id_row[0] or (SERIES_START - 1)
    next_id = current_max + 1
    if next_id > SERIES_END:
        raise HTTPException(status_code=400, detail="Employee ID series exhausted (759000-759999)")
    return f"{next_id:06d}"


@router.post("/create-basic", status_code=status.HTTP_201_CREATED, response_model=CreateEmployeeBasicOut)
def create_employee_basic(payload: CreateEmployeeBasicIn, db: Session = Depends(get_db)):
    # Optional uniqueness checks if PAN/Aadhar provided
    if payload.pan_card_no:
        exists_pan = (
            db.query(EmployeeMaster)
            .filter(EmployeeMaster.pan_card_no == payload.pan_card_no)
            .first()
        )
        if exists_pan:
            raise HTTPException(status_code=400, detail="Employee with this PAN already exists")

    if payload.aadhar_no:
        exists_aadhar = (
            db.query(EmployeeMaster)
            .filter(EmployeeMaster.aadhar_no == payload.aadhar_no)
            .first()
        )
        if exists_aadhar:
            raise HTTPException(status_code=400, detail="Employee with this Aadhar already exists")

    # Use provided employee_id or generate one
    employee_id = payload.employee_id or _generate_employee_id(db)

    # Ensure no duplicate employee_id
    exists_emp = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == employee_id).first()
    if exists_emp:
        raise HTTPException(status_code=400, detail="Employee ID already exists. Provide a different one.")

    employee = EmployeeMaster(
        title=payload.title,
        employee_id=employee_id,
        doj=payload.doj,
        first_name=payload.first_name,
        last_name=payload.last_name,
        full_name=payload.full_name,
        gender=payload.gender,
        pan_card_no=(payload.pan_card_no.upper() if payload.pan_card_no else None),
        aadhar_no=payload.aadhar_no,
        personal_email_id=payload.personal_email_id,
        created_by="system",
        updated_by="system",
    )

    db.add(employee)
    db.commit()
    db.refresh(employee)

    # Send welcome email with link if personal email is provided
    try:
        if payload.personal_email_id:
            from app.routes.email_service import EmailService
            service = EmailService()
            link = f"http://localhost:5173/employee/employee-entry?employee_id={employee.employee_id}"
            subject = "Welcome to VAICS - Complete Your Employee Entry"
            body = f"""
            <p>Dear {employee.first_name},</p>
            <p>Welcome! Please complete your employee entry using the link below:</p>
            <p><a href=\"{link}\">Complete Employee Entry</a></p>
            <p>Employee ID: <strong>{employee.employee_id}</strong></p>
            <p>Regards,<br/>HR Team</p>
            """
            service.send_email(recipient=payload.personal_email_id, subject=subject, body=body)
    except Exception:
        # Do not fail creation if email sending fails
        pass

    return CreateEmployeeBasicOut(
        message="Employee created successfully",
        employee_id=employee.employee_id,
        first_name=employee.first_name,
        last_name=employee.last_name,
        full_name=employee.full_name,
        doj=employee.doj.strftime("%d-%m-%Y") if isinstance(employee.doj, (date, datetime)) else employee.doj,
        gender=employee.gender,
        pan_card_no=employee.pan_card_no,
        aadhar_no=employee.aadhar_no,
        personal_email_id=employee.personal_email_id,
        title=employee.title,
    )


@router.get("/emp-basic")
def list_basic_employees(
    db: Session = Depends(get_db),
    first_name: str | None = Query(default=None),
    last_name: str | None = Query(default=None),
    full_name: str | None = Query(default=None),
    employee_id: str | None = Query(default=None),
    status: str | None = Query(default=None, description="Active | InActive | SelectAll"),
    joining_month: int | None = Query(default=None, ge=1, le=12),
    joining_year: int | None = Query(default=None, ge=1900, le=3000),
    blood_group: str | None = Query(default=None),
):
    query = db.query(EmployeeMaster)

    if first_name:
        query = query.filter(EmployeeMaster.first_name.ilike(f"%{first_name}%"))
    if last_name:
        query = query.filter(EmployeeMaster.last_name.ilike(f"%{last_name}%"))
    if full_name:
        query = query.filter(EmployeeMaster.full_name.ilike(f"%{full_name}%"))
    if employee_id:
        query = query.filter(EmployeeMaster.employee_id.ilike(f"%{employee_id}%"))

    # Employment status filter
    if status and status.lower() != "selectall":
        normalized = "Inactive" if status.lower() in ("inactive", "inactive", "inActive".lower()) else "Active"
        query = query.filter(EmployeeMaster.employment_status.ilike(normalized))

    # Joining month/year filters
    if joining_month is not None:
        query = query.filter(func.extract('month', EmployeeMaster.doj) == joining_month)
    if joining_year is not None:
        query = query.filter(func.extract('year', EmployeeMaster.doj) == joining_year)

    if blood_group:
        query = query.filter(EmployeeMaster.blood_group.ilike(blood_group))

    rows = query.order_by(EmployeeMaster.employee_id.asc()).all()

    # Serialize full EmployeeMaster rows with all columns
    from datetime import date as _date, datetime as _datetime
    from decimal import Decimal as _Decimal

    def format_value(val):
        if isinstance(val, (_date, _datetime)):
            try:
                return val.strftime("%d-%m-%Y")
            except Exception:
                return str(val)
        if isinstance(val, _Decimal):
            return float(val)
        return val

    # Columns to exclude from the response
    excluded_fields = {
        "address_type", "h_no", "street", "street2", "landmark", "city", "state", "postal_code", "complete_address",
        "relation_type", "family_member_name", "family_member_dob", "aadhar_number", "dependant",
        "type_of_degree", "course_name", "completed_in_month_year", "school_college_name", "affiliated_university",
        "company_name", "prev_designation", "prev_department", "office_email_id", "uan_no", "start_date", "end_date",
        "current_client_id", "asset_type", "asset_number", "asset_issued_date", "asset_status",
    }

    full_list: list[dict] = []
    for e in rows:
        row: dict = {}
        for col in e.__table__.columns:
            if col.name in excluded_fields:
                continue
            row[col.name] = format_value(getattr(e, col.name))
        full_list.append(row)

    return full_list


