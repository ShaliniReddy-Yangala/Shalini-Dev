from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from app.database import get_db
from app.Employee_Master_Report.emp_models.employee_master import (
    EmployeeMaster,
    FamilyMember,
    EducationHistory,
    ExperienceHistory,
    AssetHistory,
    AddressHistory,
    OnboardingHistory,
    ClientMaster,
)
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List
import re

router = APIRouter(prefix="/employee-entry", tags=["Employee Entry - Bulk Upload"])


def parse_date_ddmmyyyy(value: Any):
    if value in (None, "", float("nan")):
        return None
    if isinstance(value, datetime):
        return value.date()
    try:
        return datetime.strptime(str(value).strip(), "%d-%m-%Y").date()
    except Exception:
        return None


def to_digits(value: Any, max_len: int | None = None) -> str | None:
    """Coerce excel cell into digits-only string, drop trailing .0 from numeric cells,
    and optionally cap length to max_len. Returns None for empty values."""
    if value in (None, "", float("nan")):
        return None
    s = str(value).strip()
    # Remove all non-digits
    s = re.sub(r"\D", "", s)
    if not s:
        return None
    if max_len is not None:
        s = s[:max_len]
    return s


@router.post("/bulk-upload", status_code=status.HTTP_200_OK)
async def bulk_upload_employees(
    file: UploadFile = File(...), 
    upload_type: str = "create",
    db: Session = Depends(get_db)
):
    try:
        content = await file.read()
        xls = pd.ExcelFile(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid Excel file: {str(e)}")

    errors: List[Dict[str, Any]] = []
    created: List[str] = []

    try:
        employee_df = pd.read_excel(xls, sheet_name="Employee Details")
    except Exception:
        raise HTTPException(status_code=400, detail="Missing 'Employee Details' sheet in template")

    # Optional multi-row sheets
    address_df = None
    family_df = None
    education_df = None
    experience_df = None
    emergency_df = None
    nominee_df = None
    onboarding_df = None
    asset_df = None
    try:
        address_df = pd.read_excel(xls, sheet_name="Address Details")
    except Exception:
        address_df = None
    try:
        family_df = pd.read_excel(xls, sheet_name="Family Members")
    except Exception:
        family_df = None
    try:
        education_df = pd.read_excel(xls, sheet_name="Education Details")
    except Exception:
        education_df = None
    try:
        experience_df = pd.read_excel(xls, sheet_name="Experience Details")
    except Exception:
        experience_df = None
    try:
        emergency_df = pd.read_excel(xls, sheet_name="Emergency Contacts")
    except Exception:
        emergency_df = None
    try:
        nominee_df = pd.read_excel(xls, sheet_name="Nominee Details")
    except Exception:
        nominee_df = None
    try:
        onboarding_df = pd.read_excel(xls, sheet_name="Onboarding Details")
    except Exception:
        onboarding_df = None
    try:
        asset_df = pd.read_excel(xls, sheet_name="Asset Details")
    except Exception:
        asset_df = None

    # Normalize columns
    def norm(col: str) -> str:
        return (col or "").strip().lower()

    employee_cols = {norm(c): c for c in employee_df.columns}

    # Expected column keys
    col_employee_id = employee_cols.get("employee id")
    col_doj = employee_cols.get("doj (dd-mm-yyyy)")
    col_designation = employee_cols.get("designation")
    col_department = employee_cols.get("department")
    col_manager = employee_cols.get("manager name")
    col_off_no = employee_cols.get("official contact number")
    col_off_email = employee_cols.get("official email id")
    col_category = employee_cols.get("category")
    col_excluded = employee_cols.get("excluded from payroll")

    p_title = employee_cols.get("title (mr./mrs./ms./miss)") or employee_cols.get("title")
    p_first = employee_cols.get("first name")
    p_last = employee_cols.get("last name")
    p_full = employee_cols.get("full name (auto-generated)") or employee_cols.get("full name")
    p_gender = employee_cols.get("gender")
    p_dob = employee_cols.get("dob (dd-mm-yyyy)")
    p_marital = employee_cols.get("marital status")
    p_doa = employee_cols.get("doa (dd-mm-yyyy)")
    p_religion = employee_cols.get("religion")
    p_blood = employee_cols.get("blood group")
    p_mobile_col = employee_cols.get("mobile no")

    c_pan = (employee_cols.get("pan card no") or employee_cols.get("pan"))
    c_aadhar = (employee_cols.get("aadhar no") or employee_cols.get("aadhar"))
    c_personal_email_col = employee_cols.get("personal email id")
    c_passport_no = employee_cols.get("passport no")
    c_passport_issue = employee_cols.get("passport issued date (dd-mm-yyyy)")
    c_passport_exp = employee_cols.get("passport expiry date (dd-mm-yyyy)")
    c_name_as_aadhar = employee_cols.get("name as per aadhar")
    c_current_uan = employee_cols.get("current uan no")

    k_bank_name = employee_cols.get("bank name")
    k_account_no = employee_cols.get("account no")
    k_ifsc = employee_cols.get("ifsc code")
    k_type_ac = employee_cols.get("type of account")
    k_branch = employee_cols.get("branch")

    ct_job_type = employee_cols.get("job type")
    ct_contract_end = employee_cols.get("contract end date (dd-mm-yyyy)")
    ct_probation_end = employee_cols.get("probation end date (dd-mm-yyyy)")

    s_gross = employee_cols.get("gross salary per month")
    s_tax = employee_cols.get("tax regime")

    h_policy_no = employee_cols.get("policy no")
    h_commence = employee_cols.get("commencement date (dd-mm-yyyy)")
    h_end = employee_cols.get("end date (dd-mm-yyyy)")
    h_amount = employee_cols.get("amount")
    h_members = employee_cols.get("covered members")
    h_duration = employee_cols.get("duration")
    h_insurer = employee_cols.get("insurer name")

    # Collect duplicates within file
    in_file_emp_ids = set()
    in_file_emails = set()  # all emails (official + personal)
    in_file_contacts = set()  # all contact numbers (official + personal)
    in_file_pan = set()
    in_file_aadhar = set()

    for idx, row in employee_df.iterrows():
        row_num = idx + 2  # header is row 1
        employee_id = str(row[col_employee_id]).strip() if col_employee_id and pd.notna(row.get(col_employee_id)) else None
        doj_str = row.get(col_doj) if col_doj else None
        doj = parse_date_ddmmyyyy(doj_str)
        designation = str(row[col_designation]).strip() if col_designation and pd.notna(row.get(col_designation)) else None
        department = str(row[col_department]).strip() if col_department and pd.notna(row.get(col_department)) else None
        manager_name = str(row[col_manager]).strip() if col_manager and pd.notna(row.get(col_manager)) else None
        official_no = str(row[col_off_no]).strip() if col_off_no and pd.notna(row.get(col_off_no)) else None
        official_email_id = str(row[col_off_email]).strip() if col_off_email and pd.notna(row.get(col_off_email)) else None
        category = str(row[col_category]).strip() if col_category and pd.notna(row.get(col_category)) else None
        excluded_from_payroll = str(row[col_excluded]).strip() if col_excluded and pd.notna(row.get(col_excluded)) else None

        # Pull consolidated info from current row
        title = str(row.get(p_title)).strip() if p_title and pd.notna(row.get(p_title)) else None
        first_name = str(row.get(p_first)).strip() if p_first and pd.notna(row.get(p_first)) else None
        last_name = str(row.get(p_last)).strip() if p_last and pd.notna(row.get(p_last)) else None
        full_name = str(row.get(p_full)).strip() if p_full and pd.notna(row.get(p_full)) else None
        gender = str(row.get(p_gender)).strip() if p_gender and pd.notna(row.get(p_gender)) else None
        dob = parse_date_ddmmyyyy(row.get(p_dob)) if p_dob else None
        marital_status = str(row.get(p_marital)).strip() if p_marital and pd.notna(row.get(p_marital)) else None
        doa = parse_date_ddmmyyyy(row.get(p_doa)) if p_doa else None
        religion = str(row.get(p_religion)).strip() if p_religion and pd.notna(row.get(p_religion)) else None
        blood_group = str(row.get(p_blood)).strip() if p_blood and pd.notna(row.get(p_blood)) else None
        personal_mobile = str(row.get(p_mobile_col)).strip() if p_mobile_col and pd.notna(row.get(p_mobile_col)) else None

        pan_card_no = str(row.get(c_pan)).strip().upper() if c_pan and pd.notna(row.get(c_pan)) else None
        aadhar_no = str(row.get(c_aadhar)).strip() if c_aadhar and pd.notna(row.get(c_aadhar)) else None
        personal_email_id = str(row.get(c_personal_email_col)).strip() if c_personal_email_col and pd.notna(row.get(c_personal_email_col)) else None
        passport_no = str(row.get(c_passport_no)).strip() if c_passport_no and pd.notna(row.get(c_passport_no)) else None
        issued_date = parse_date_ddmmyyyy(row.get(c_passport_issue)) if c_passport_issue else None
        expiry_date = parse_date_ddmmyyyy(row.get(c_passport_exp)) if c_passport_exp else None
        name_as_per_aadhar = str(row.get(c_name_as_aadhar)).strip() if c_name_as_aadhar and pd.notna(row.get(c_name_as_aadhar)) else None
        current_uan_no = str(row.get(c_current_uan)).strip() if c_current_uan and pd.notna(row.get(c_current_uan)) else None

        bank_name = str(row.get(k_bank_name)).strip() if k_bank_name and pd.notna(row.get(k_bank_name)) else None
        account_no = str(row.get(k_account_no)).strip() if k_account_no and pd.notna(row.get(k_account_no)) else None
        ifsc_code = str(row.get(k_ifsc)).strip() if k_ifsc and pd.notna(row.get(k_ifsc)) else None
        type_of_account = str(row.get(k_type_ac)).strip() if k_type_ac and pd.notna(row.get(k_type_ac)) else None
        branch = str(row.get(k_branch)).strip() if k_branch and pd.notna(row.get(k_branch)) else None

        job_type = str(row.get(ct_job_type)).strip() if ct_job_type and pd.notna(row.get(ct_job_type)) else None
        contract_end_date = parse_date_ddmmyyyy(row.get(ct_contract_end)) if ct_contract_end else None
        probation_end_date = parse_date_ddmmyyyy(row.get(ct_probation_end)) if ct_probation_end else None

        try:
            gross_salary_per_month = float(row.get(s_gross)) if s_gross and pd.notna(row.get(s_gross)) else None
        except Exception:
            gross_salary_per_month = None
        tax_regime = str(row.get(s_tax)).strip() if s_tax and pd.notna(row.get(s_tax)) else None

        policy_no = str(row.get(h_policy_no)).strip() if h_policy_no and pd.notna(row.get(h_policy_no)) else None
        commencement_date = parse_date_ddmmyyyy(row.get(h_commence)) if h_commence else None
        end_date = parse_date_ddmmyyyy(row.get(h_end)) if h_end else None
        try:
            amount = float(row.get(h_amount)) if h_amount and pd.notna(row.get(h_amount)) else None
        except Exception:
            amount = None
        try:
            covered_members = int(row.get(h_members)) if h_members and pd.notna(row.get(h_members)) else None
        except Exception:
            covered_members = None
        duration = str(row.get(h_duration)).strip() if h_duration and pd.notna(row.get(h_duration)) else None
        insurer_name = str(row.get(h_insurer)).strip() if h_insurer and pd.notna(row.get(h_insurer)) else None

        # Normalize digit-only fields and apply length caps compatible with DB schema
        # Many Excel numeric cells come as '1234567890.0' -> keep only digits
        official_no_clean = to_digits(official_no, max_len=12)
        personal_mobile_clean = to_digits(personal_mobile, max_len=12)
        aadhar_no_clean = to_digits(aadhar_no, max_len=12)

        # Build row errors
        row_errors = []
        if not employee_id:
            row_errors.append("Employee ID is required")
        if not doj:
            row_errors.append("DOJ must be in DD-MM-YYYY format")
        if not first_name:
            row_errors.append("First Name is required")
        if not last_name:
            row_errors.append("Last Name is required")
        if not official_email_id:
            row_errors.append("Official Email ID is required")

        # In-file duplicates
        if employee_id:
            if employee_id in in_file_emp_ids:
                row_errors.append("Duplicate Employee ID in file")
            in_file_emp_ids.add(employee_id)
        # Emails (official + personal) unique within file
        for email_val, label in ((official_email_id, "Official Email"), (personal_email_id, "Personal Email")):
            if email_val:
                ekey = email_val.lower()
                if ekey in in_file_emails:
                    row_errors.append(f"Duplicate {label} in file")
                in_file_emails.add(ekey)
        if pan_card_no:
            if pan_card_no in in_file_pan:
                row_errors.append("Duplicate PAN in file")
            in_file_pan.add(pan_card_no)
        if aadhar_no:
            if aadhar_no in in_file_aadhar:
                row_errors.append("Duplicate Aadhar in file")
            in_file_aadhar.add(aadhar_no)
        # Contacts (official + personal + comm)
        for num_val, label in ((official_no_clean, "Official Contact"), (personal_mobile_clean, "Personal Mobile")):
            if num_val:
                nkey = num_val
                if nkey in in_file_contacts:
                    row_errors.append(f"Duplicate {label} in file")
                in_file_contacts.add(nkey)

        # DB duplicates - only check for create mode
        if upload_type == "create":
            if employee_id and db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == employee_id).first():
                row_errors.append("Employee ID already exists")
            if official_email_id and db.query(EmployeeMaster).filter(
                (EmployeeMaster.official_email_id.ilike(official_email_id)) | (EmployeeMaster.personal_email_id.ilike(official_email_id))
            ).first():
                row_errors.append("Official Email already exists")
            if personal_email_id and db.query(EmployeeMaster).filter(
                (EmployeeMaster.personal_email_id.ilike(personal_email_id)) | (EmployeeMaster.official_email_id.ilike(personal_email_id))
            ).first():
                row_errors.append("Personal Email already exists")
            if pan_card_no and db.query(EmployeeMaster).filter(EmployeeMaster.pan_card_no == pan_card_no).first():
                row_errors.append("PAN already exists")
            if aadhar_no_clean and db.query(EmployeeMaster).filter(EmployeeMaster.aadhar_no == aadhar_no_clean).first():
                row_errors.append("Aadhar already exists")
            # Contact numbers unique across all employee contact fields
            def contact_exists(num: str) -> bool:
                if not num:
                    return False
                return db.query(EmployeeMaster).filter(
                    (EmployeeMaster.official_no == num) | (EmployeeMaster.mobile_no == num) | (EmployeeMaster.mobile_no_comm == num)
                ).first() is not None
            if contact_exists(official_no_clean):
                row_errors.append("Official Contact already exists")
            if contact_exists(personal_mobile_clean):
                row_errors.append("Personal Mobile already exists")
        elif upload_type == "update":
            # For update mode, check if employee exists
            if employee_id and not db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == employee_id).first():
                row_errors.append("Employee ID not found - cannot update non-existent employee")

        if row_errors:
            errors.append({
                "row": row_num,
                "employee_id": employee_id,
                "errors": row_errors
            })
            continue

        # Create or update employee
        if upload_type == "create":
            # Create new employee
            employee = EmployeeMaster(
                employee_id=employee_id,
                doj=doj,
                designation=designation,
                department=department,
                manager_name=manager_name,
                official_no=official_no_clean,
                official_email_id=official_email_id,
                category=category,
                excluded_from_payroll=excluded_from_payroll,
                title=title,
                first_name=first_name,
                last_name=last_name,
                full_name=full_name or f"{first_name} {last_name}".strip(),
                gender=gender,
                dob=dob,
                marital_status=marital_status,
                doa=doa,
                religion=religion,
                blood_group=blood_group,
                pan_card_no=pan_card_no,
                aadhar_no=aadhar_no_clean,
                name_as_per_aadhar=name_as_per_aadhar,
                passport_no=passport_no,
                issued_date=issued_date,
                expiry_date=expiry_date,
                personal_email_id=personal_email_id,
                mobile_no=personal_mobile_clean,
                mobile_no_comm=personal_mobile_clean,  # fallback to same mobile if separate comm not provided
                current_uan_no=current_uan_no,
                # Bank
                bank_name=bank_name,
                account_no=account_no,
                ifsc_code=ifsc_code,
                type_of_account=type_of_account,
                branch=branch,
                # Contract
                job_type=job_type,
                contract_end_date=contract_end_date,
                probation_end_date=probation_end_date,
                # Salary
                gross_salary_per_month=gross_salary_per_month,
                tax_regime=tax_regime,
                # Health Insurance
                policy_no=policy_no,
                commencement_date=commencement_date,
                end_date=end_date,
                amount=amount,
                covered_members=covered_members,
                duration=duration,
                insurer_name=insurer_name,
                created_by="system",
                updated_by="system",
            )
            db.add(employee)
            created.append(employee_id)
        elif upload_type == "update":
            # Update existing employee
            employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == employee_id).first()
            if employee:
                # Update all fields
                employee.doj = doj if doj else employee.doj
                employee.designation = designation if designation else employee.designation
                employee.department = department if department else employee.department
                employee.manager_name = manager_name if manager_name else employee.manager_name
                employee.official_no = official_no_clean if official_no_clean else employee.official_no
                employee.official_email_id = official_email_id if official_email_id else employee.official_email_id
                employee.category = category if category else employee.category
                employee.excluded_from_payroll = excluded_from_payroll if excluded_from_payroll else employee.excluded_from_payroll
                employee.title = title if title else employee.title
                employee.first_name = first_name if first_name else employee.first_name
                employee.last_name = last_name if last_name else employee.last_name
                employee.full_name = full_name or f"{first_name} {last_name}".strip() if first_name and last_name else employee.full_name
                employee.gender = gender if gender else employee.gender
                employee.dob = dob if dob else employee.dob
                employee.marital_status = marital_status if marital_status else employee.marital_status
                employee.doa = doa if doa else employee.doa
                employee.religion = religion if religion else employee.religion
                employee.blood_group = blood_group if blood_group else employee.blood_group
                employee.pan_card_no = pan_card_no if pan_card_no else employee.pan_card_no
                employee.aadhar_no = aadhar_no_clean if aadhar_no_clean else employee.aadhar_no
                employee.name_as_per_aadhar = name_as_per_aadhar if name_as_per_aadhar else employee.name_as_per_aadhar
                employee.passport_no = passport_no if passport_no else employee.passport_no
                employee.issued_date = issued_date if issued_date else employee.issued_date
                employee.expiry_date = expiry_date if expiry_date else employee.expiry_date
                employee.personal_email_id = personal_email_id if personal_email_id else employee.personal_email_id
                employee.mobile_no = personal_mobile_clean if personal_mobile_clean else employee.mobile_no
                employee.mobile_no_comm = personal_mobile_clean if personal_mobile_clean else employee.mobile_no_comm
                employee.current_uan_no = current_uan_no if current_uan_no else employee.current_uan_no
                # Bank
                employee.bank_name = bank_name if bank_name else employee.bank_name
                employee.account_no = account_no if account_no else employee.account_no
                employee.ifsc_code = ifsc_code if ifsc_code else employee.ifsc_code
                employee.type_of_account = type_of_account if type_of_account else employee.type_of_account
                employee.branch = branch if branch else employee.branch
                # Contract
                employee.job_type = job_type if job_type else employee.job_type
                employee.contract_end_date = contract_end_date if contract_end_date else employee.contract_end_date
                employee.probation_end_date = probation_end_date if probation_end_date else employee.probation_end_date
                # Salary
                employee.gross_salary_per_month = gross_salary_per_month if gross_salary_per_month is not None else employee.gross_salary_per_month
                employee.tax_regime = tax_regime if tax_regime else employee.tax_regime
                # Health Insurance
                employee.policy_no = policy_no if policy_no else employee.policy_no
                employee.commencement_date = commencement_date if commencement_date else employee.commencement_date
                employee.end_date = end_date if end_date else employee.end_date
                employee.amount = amount if amount is not None else employee.amount
                employee.covered_members = covered_members if covered_members is not None else employee.covered_members
                employee.duration = duration if duration else employee.duration
                employee.insurer_name = insurer_name if insurer_name else employee.insurer_name
                employee.updated_by = "system"
                created.append(employee_id)

    # If any errors while creating masters, rollback and report
    if errors:
        db.rollback()
        return JSONResponse(status_code=400, content={"message": "Validation errors", "errors": errors})

    # Commit masters first
    db.commit()

    # Helper to safely get string from row by header
    def sval(r: pd.Series, header: str) -> str:
        return str(r.get(header)).strip() if header and pd.notna(r.get(header)) else None

    # Address History
    if address_df is not None and len(address_df) > 0:
        a_cols = {norm(c): c for c in address_df.columns}
        a_emp = a_cols.get("employee id")
        a_type = a_cols.get("address type")
        a_hno = a_cols.get("h.no")
        a_street = a_cols.get("street")
        a_street2 = a_cols.get("street2")
        a_landmark = a_cols.get("landmark")
        a_city = a_cols.get("city")
        a_state = a_cols.get("state")
        a_postal = a_cols.get("postal code")
        a_complete = a_cols.get("complete address (auto-generated)") or a_cols.get("complete address")
        # In update mode, remove existing address rows for listed employees to avoid duplicates
        if upload_type == "update" and a_emp:
            emp_ids_in_sheet: set[str] = set()
            for _, r in address_df.iterrows():
                emp_val = sval(r, a_emp)
                if emp_val:
                    emp_ids_in_sheet.add(emp_val)
            if emp_ids_in_sheet:
                db.query(AddressHistory).filter(AddressHistory.employee_id.in_(list(emp_ids_in_sheet))).delete(synchronize_session=False)
        for _, r in address_df.iterrows():
            emp_id = sval(r, a_emp)
            if not emp_id:
                continue
            addr_type_val = sval(r, a_type)
            
            if upload_type == "create":
                # Create new address history
                db.add(AddressHistory(
                    employee_id=emp_id,
                    address_type=addr_type_val,
                    h_no=sval(r, a_hno),
                    street=sval(r, a_street),
                    street2=sval(r, a_street2),
                    landmark=sval(r, a_landmark),
                    city=sval(r, a_city),
                    state=sval(r, a_state),
                    postal_code=sval(r, a_postal),
                    complete_address=sval(r, a_complete),
                    created_by="system",
                    updated_by="system",
                ))
            elif upload_type == "update":
                # Update existing address history or create if not exists
                existing_address = db.query(AddressHistory).filter(
                    AddressHistory.employee_id == emp_id,
                    AddressHistory.address_type == addr_type_val
                ).first()
                
                if existing_address:
                    # Update existing
                    existing_address.h_no = sval(r, a_hno)
                    existing_address.street = sval(r, a_street)
                    existing_address.street2 = sval(r, a_street2)
                    existing_address.landmark = sval(r, a_landmark)
                    existing_address.city = sval(r, a_city)
                    existing_address.state = sval(r, a_state)
                    existing_address.postal_code = sval(r, a_postal)
                    existing_address.complete_address = sval(r, a_complete)
                    existing_address.updated_by = "system"
                else:
                    # Create new if doesn't exist
                    db.add(AddressHistory(
                        employee_id=emp_id,
                        address_type=addr_type_val,
                        h_no=sval(r, a_hno),
                        street=sval(r, a_street),
                        street2=sval(r, a_street2),
                        landmark=sval(r, a_landmark),
                        city=sval(r, a_city),
                        state=sval(r, a_state),
                        postal_code=sval(r, a_postal),
                        complete_address=sval(r, a_complete),
                        created_by="system",
                        updated_by="system",
                    ))
            # If Permanent, also update quick-reference fields on master for GET endpoint
            if (addr_type_val or "").strip().lower() == "permanent":
                db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == emp_id).update({
                    EmployeeMaster.address_type: addr_type_val,
                    EmployeeMaster.h_no: sval(r, a_hno),
                    EmployeeMaster.street: sval(r, a_street),
                    EmployeeMaster.street2: sval(r, a_street2),
                    EmployeeMaster.landmark: sval(r, a_landmark),
                    EmployeeMaster.city: sval(r, a_city),
                    EmployeeMaster.state: sval(r, a_state),
                    EmployeeMaster.postal_code: sval(r, a_postal),
                    EmployeeMaster.complete_address: sval(r, a_complete),
                }, synchronize_session=False)

    # Family Members
    if family_df is not None and len(family_df) > 0:
        f_cols = {norm(c): c for c in family_df.columns}
        f_emp = f_cols.get("employee id")
        f_rel = f_cols.get("relation type")
        f_name = f_cols.get("name")
        f_dob = f_cols.get("dob (dd-mm-yyyy)")
        f_aadhar = f_cols.get("aadhar number")
        f_dep = f_cols.get("dependant (yes/no)")
        # For update, clear existing family rows for employees in sheet
        if upload_type == "update" and f_emp:
            emp_ids_in_sheet: set[str] = set()
            for _, r in family_df.iterrows():
                emp_val = sval(r, f_emp)
                if emp_val:
                    emp_ids_in_sheet.add(emp_val)
            if emp_ids_in_sheet:
                db.query(FamilyMember).filter(FamilyMember.employee_id.in_(list(emp_ids_in_sheet))).delete(synchronize_session=False)
        for _, r in family_df.iterrows():
            emp_id = sval(r, f_emp)
            if not emp_id:
                continue
            db.add(FamilyMember(
                employee_id=emp_id,
                relation_type=sval(r, f_rel),
                name=sval(r, f_name),
                dob=parse_date_ddmmyyyy(r.get(f_dob)) if f_dob else None,
                aadhar_number=sval(r, f_aadhar),
                dependant=sval(r, f_dep) or "No",
                created_by="system",
                updated_by="system",
            ))

    # Education History
    if education_df is not None and len(education_df) > 0:
        e_cols = {norm(c): c for c in education_df.columns}
        e_emp = e_cols.get("employee id")
        e_type = e_cols.get("type of degree")
        e_course = e_cols.get("course name")
        e_month = e_cols.get("completed month (1-12)")
        e_year = e_cols.get("completed year")
        e_school = e_cols.get("school/college name")
        e_univ = e_cols.get("affiliated from university")
        # For update, clear existing education rows for employees in sheet
        if upload_type == "update" and e_emp:
            emp_ids_in_sheet: set[str] = set()
            for _, r in education_df.iterrows():
                emp_val = sval(r, e_emp)
                if emp_val:
                    emp_ids_in_sheet.add(emp_val)
            if emp_ids_in_sheet:
                db.query(EducationHistory).filter(EducationHistory.employee_id.in_(list(emp_ids_in_sheet))).delete(synchronize_session=False)
        for _, r in education_df.iterrows():
            emp_id = sval(r, e_emp)
            if not emp_id:
                continue
            month = sval(r, e_month)
            year = sval(r, e_year)
            completed_in_month_year = f"{month}-{year}" if month or year else None
            db.add(EducationHistory(
                employee_id=emp_id,
                type_of_degree=sval(r, e_type),
                course_name=sval(r, e_course),
                school_college_name=sval(r, e_school),
                affiliated_university=sval(r, e_univ),
                completed_in_month_year=completed_in_month_year,
                created_by="system",
                updated_by="system",
            ))

    # Experience History and mapping some fields back to master
    pf_by_emp: Dict[str, Dict[str, Any]] = {}
    if experience_df is not None and len(experience_df) > 0:
        x_cols = {norm(c): c for c in experience_df.columns}
        x_emp = x_cols.get("employee id")
        x_company = x_cols.get("company name")
        x_start = x_cols.get("start date (dd-mm-yyyy)")
        x_end = x_cols.get("end date (dd-mm-yyyy)")
        x_desig = x_cols.get("designation")
        x_dept = x_cols.get("department")
        x_off_email = x_cols.get("office email id")
        x_uan = x_cols.get("uan no")
        x_pf = x_cols.get("pf no")
        x_addr = x_cols.get("company address")
        x_ref1 = x_cols.get("reference details -1")
        x_ref2 = x_cols.get("reference details -2")
        # For update, clear existing experience rows for employees in sheet
        if upload_type == "update" and x_emp:
            emp_ids_in_sheet: set[str] = set()
            for _, r in experience_df.iterrows():
                emp_val = sval(r, x_emp)
                if emp_val:
                    emp_ids_in_sheet.add(emp_val)
            if emp_ids_in_sheet:
                db.query(ExperienceHistory).filter(ExperienceHistory.employee_id.in_(list(emp_ids_in_sheet))).delete(synchronize_session=False)
        for _, r in experience_df.iterrows():
            emp_id = sval(r, x_emp)
            if not emp_id:
                continue
            db.add(ExperienceHistory(
                employee_id=emp_id,
                company_name=sval(r, x_company),
                start_date=parse_date_ddmmyyyy(r.get(x_start)) if x_start else None,
                end_date=parse_date_ddmmyyyy(r.get(x_end)) if x_end else None,
                designation=sval(r, x_desig),
                department=sval(r, x_dept),
                office_email_id=sval(r, x_off_email),
                uan_no=sval(r, x_uan),
                created_by="system",
                updated_by="system",
            ))
            # Stash PF/company address/reference to update master from first seen row
            if emp_id not in pf_by_emp:
                pf_by_emp[emp_id] = {
                    "pf_no": sval(r, x_pf),
                    "company_address": sval(r, x_addr),
                    "reference_details_1": sval(r, x_ref1),
                    "reference_details_2": sval(r, x_ref2),
                }
    # Apply stashed PF and references to master
    if pf_by_emp:
        for emp_id, vals in pf_by_emp.items():
            db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == emp_id).update({
                EmployeeMaster.pf_no: vals.get("pf_no"),
                EmployeeMaster.company_address: vals.get("company_address"),
                EmployeeMaster.reference_details_1: vals.get("reference_details_1"),
                EmployeeMaster.reference_details_2: vals.get("reference_details_2"),
            })

    # Emergency contacts -> set first contact into master
    if emergency_df is not None and len(emergency_df) > 0:
        em_cols = {norm(c): c for c in emergency_df.columns}
        em_emp = em_cols.get("employee id")
        em_name = em_cols.get("contact name")
        em_rel = em_cols.get("relation")
        em_num = em_cols.get("contact number")
        seen: set = set()
        for _, r in emergency_df.iterrows():
            emp_id = sval(r, em_emp)
            if not emp_id or emp_id in seen:
                continue
            seen.add(emp_id)
            db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == emp_id).update({
                EmployeeMaster.emergency_contact_name: sval(r, em_name),
                EmployeeMaster.emergency_contact_relation: sval(r, em_rel),
                EmployeeMaster.emergency_contact_no: sval(r, em_num),
            })

    # Nominee details -> master
    if nominee_df is not None and len(nominee_df) > 0:
        n_cols = {norm(c): c for c in nominee_df.columns}
        n_name = n_cols.get("nominee name")
        n_addr = n_cols.get("address")
        n_rel = n_cols.get("relation")
        n_age = n_cols.get("age")
        n_prop = n_cols.get("proportion")
        # Single row for now; apply to all created employees if values provided
        n0 = nominee_df.iloc[0]
        try:
            nominee_age_val = int(n0.get(n_age)) if n_age and pd.notna(n0.get(n_age)) else None
        except Exception:
            nominee_age_val = None
        try:
            nominee_prop_val = float(n0.get(n_prop)) if n_prop and pd.notna(n0.get(n_prop)) else None
        except Exception:
            nominee_prop_val = None
        db.query(EmployeeMaster).filter(EmployeeMaster.employee_id.in_(created)).update({
            EmployeeMaster.nominee_name: sval(n0, n_name),
            EmployeeMaster.nominee_address: sval(n0, n_addr),
            EmployeeMaster.nominee_relation: sval(n0, n_rel),
            EmployeeMaster.nominee_age: nominee_age_val,
            EmployeeMaster.nominee_proportion: nominee_prop_val,
        }, synchronize_session=False)

    # Onboarding Details -> OnboardingHistory
    if onboarding_df is not None and len(onboarding_df) > 0:
        o_cols = {norm(c): c for c in onboarding_df.columns}
        o_client_name = o_cols.get("client name")
        o_start = o_cols.get("effective start date (dd-mm-yyyy)")
        o_end = o_cols.get("effective end date (dd-mm-yyyy)")
        o_status = o_cols.get("current onboarding status (active/withdrawn/on bench)")
        o_duration = o_cols.get("duration (auto-calculated)")
        o_spoc = o_cols.get("spoc")
        o_dept = o_cols.get("department")
        o_manager = o_cols.get("manager")
        # We need employee_id association; assume one row per employee by order matching created list
        # If Employee ID column exists, prefer that
        o_emp_col = o_cols.get("employee id")
        # For update, clear existing onboarding rows for employees in sheet
        if upload_type == "update" and o_emp_col:
            emp_ids_in_sheet: set[str] = set()
            for _, r in onboarding_df.iterrows():
                emp_val = sval(r, o_emp_col)
                if emp_val:
                    emp_ids_in_sheet.add(emp_val)
            if emp_ids_in_sheet:
                db.query(OnboardingHistory).filter(OnboardingHistory.employee_id.in_(list(emp_ids_in_sheet))).delete(synchronize_session=False)
        for idx2, r in onboarding_df.iterrows():
            if o_emp_col:
                emp_id = sval(r, o_emp_col)
            else:
                emp_id = created[idx2] if idx2 < len(created) else None
            if not emp_id:
                continue
            client_name = sval(r, o_client_name)
            client_id = None
            if client_name:
                client = db.query(ClientMaster).filter(ClientMaster.client_name.ilike(client_name)).first()
                if client:
                    client_id = client.client_id
            if not client_id and client_name:
                # create client in ClientMaster if missing
                new_client = ClientMaster(client_name=client_name)
                db.add(new_client)
                db.flush()  # assign id
                client_id = new_client.client_id
            if not client_id:
                continue  # skip if still not available
            db.add(OnboardingHistory(
                employee_id=emp_id,
                client_id=client_id,
                effective_start_date=parse_date_ddmmyyyy(r.get(o_start)) if o_start else None,
                effective_end_date=parse_date_ddmmyyyy(r.get(o_end)) if o_end else None,
                onboarding_status=(sval(r, o_status) or "Active"),
                duration_calculated=sval(r, o_duration),
                spoc=sval(r, o_spoc),
                onboarding_department=sval(r, o_dept),
                assigned_manager=sval(r, o_manager),
                is_current_assignment="Yes",
                created_by="system",
                updated_by="system",
            ))

    # Asset Details -> AssetHistory (single row per file; apply per employee if Employee ID column provided)
    if asset_df is not None and len(asset_df) > 0:
        as_cols = {norm(c): c for c in asset_df.columns}
        as_emp = as_cols.get("employee id")
        as_type = as_cols.get("asset type")
        as_num = as_cols.get("asset number")
        as_issue = as_cols.get("issued date (dd-mm-yyyy)")
        as_status = as_cols.get("status")
        # For update, clear existing asset rows for employees in sheet
        if upload_type == "update" and as_emp:
            emp_ids_in_sheet: set[str] = set()
            for _, r in asset_df.iterrows():
                emp_val = sval(r, as_emp)
                if emp_val:
                    emp_ids_in_sheet.add(emp_val)
            if emp_ids_in_sheet:
                db.query(AssetHistory).filter(AssetHistory.employee_id.in_(list(emp_ids_in_sheet))).delete(synchronize_session=False)
        for _, r in asset_df.iterrows():
            emp_id = sval(r, as_emp) if as_emp else None
            if not emp_id:
                continue
            db.add(AssetHistory(
                employee_id=emp_id,
                asset_type=sval(r, as_type),
                asset_number=sval(r, as_num),
                issued_date=parse_date_ddmmyyyy(r.get(as_issue)) if as_issue else None,
                status=sval(r, as_status) or "Issued",
                created_by="system",
                updated_by="system",
            ))

    db.commit()
    operation = "Updated" if upload_type == "update" else "Created"
    return {"message": f"{operation} {len(created)} employees with related details", "created": created, "operation": upload_type}



@router.put("/bulk-upload", status_code=status.HTTP_200_OK)
async def bulk_upload_employees_put(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Alias to support PUT semantics for updates
    return await bulk_upload_employees(file=file, upload_type="update", db=db)

