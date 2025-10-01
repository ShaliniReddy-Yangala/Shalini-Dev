from sqlalchemy import Column, String, Integer, Date, DateTime, Text, Numeric, ForeignKey, DECIMAL
from sqlalchemy.sql import func
from app.database import Base
from sqlalchemy.orm import relationship


class EmployeeMaster(Base):
    __tablename__ = "employee_master"

    # A: Personal Details
    employee_id = Column(String(50), primary_key=True)
    title = Column(String(10))
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    full_name = Column(String(100))
    gender = Column(String(10))
    dob = Column(Date)
    marital_status = Column(String(20))
    doa = Column(Date)
    religion = Column(String(50))
    blood_group = Column(String(10))
    vaics_format_resume = Column(Text)
    mobile_no = Column(String(15))
    # B: Basic Details

    doj = Column(Date, nullable=True)
    designation = Column(String(100))
    department = Column(String(100))
    manager_name = Column(String(100))
    official_no = Column(String(50))
    official_email_id = Column(String(100), unique=True)
    category = Column(String(50))
    excluded_from_payroll = Column(String(10), default="No")



    # C: Address Details (single-row fields retained for quick reference)
    address_type = Column(String(50))
    h_no = Column(String(20))
    street = Column(String(100))
    street2 = Column(String(100))
    landmark = Column(String(100))
    city = Column(String(50))
    state = Column(String(50))
    postal_code = Column(String(10))
    complete_address = Column(Text)

    # D: Family Members Details (single-row fields retained)
    relation_type = Column(String(50))
    family_member_name = Column(String(100))
    family_member_dob = Column(Date)
    aadhar_number = Column(String(12))
    dependant = Column(String(10))

    # E: Education Details (single-row fields retained)
    type_of_degree = Column(String(50))
    course_name = Column(String(100))
    completed_in_month_year = Column(String(50))
    school_college_name = Column(String(150))
    affiliated_university = Column(String(150))

    # F: Previous Experience Details (single-row fields retained)
    company_name = Column(String(150))
    prev_designation = Column(String(100))
    prev_department = Column(String(100))
    office_email_id = Column(String(100))
    uan_no = Column(String(50))
    start_date = Column(Date)
    end_date = Column(Date)

    # G: Contract Details
    job_type = Column(String(50))
    contract_end_date = Column(Date)
    probation_end_date = Column(Date)

    # H: Bank Details
    bank_name = Column(String(100))
    account_no = Column(String(30))
    ifsc_code = Column(String(11))
    type_of_account = Column(String(20))
    branch = Column(String(100))

    # I: Communication Details
    pan_card_no = Column(String(10), unique=True)
    aadhar_no = Column(String(12), unique=True)
    name_as_per_aadhar = Column(String(100))
    passport_no = Column(String(20))
    issued_date = Column(Date)
    expiry_date = Column(Date)
    personal_email_id = Column(String(100))
    mobile_no_comm = Column(String(15))
    current_uan_no = Column(String(20))

    # J: Nominee Details
    nominee_name = Column(String(100))
    nominee_address = Column(Text)
    nominee_relation = Column(String(50))
    nominee_age = Column(Integer)
    nominee_proportion = Column(Numeric(5, 2), default=100.00)

    # K: Salary Details
    gross_salary_per_month = Column(Numeric(12, 2))
    tax_regime = Column(String(10), default="New")

    # L: Emergency Contact Details
    emergency_contact_name = Column(String(100))
    emergency_contact_relation = Column(String(50))
    emergency_contact_no = Column(String(15))

    # Current Client reference
    current_client_id = Column(Integer, ForeignKey("client_master.client_id", ondelete="SET NULL"), nullable=True)

    # N: Asset Details (single-row fields retained)
    asset_type = Column(String(50))
    asset_number = Column(String(50))
    asset_issued_date = Column(Date)
    asset_status = Column(String(20), default="Issued")

    # O: Health Insurance Details
    policy_no = Column(String(50))
    commencement_date = Column(Date)
    end_date = Column(Date)
    amount = Column(Numeric(12, 2))
    covered_members = Column(Integer, default=1)
    duration = Column(String(20))
    insurer_name = Column(String(100))

    # P: Reference Details
    pf_no = Column(String(50))
    company_address = Column(Text)
    reference_details_1 = Column(String(200))
    reference_details_2 = Column(String(200))

    # Additional Fields
    employment_status = Column(String(20), default="Active")
    termination_date = Column(Date)
    remarks = Column(Text)

    # Audit Fields
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50))
    updated_by = Column(String(50))

    # Relationships
    current_client = relationship("ClientMaster", back_populates="employees")
    family_members = relationship("FamilyMember", back_populates="employee", cascade="all, delete-orphan")
    education_history = relationship("EducationHistory", back_populates="employee", cascade="all, delete-orphan")
    experience_history = relationship("ExperienceHistory", back_populates="employee", cascade="all, delete-orphan")
    asset_history = relationship("AssetHistory", back_populates="employee", cascade="all, delete-orphan")
    address_history = relationship("AddressHistory", back_populates="employee", cascade="all, delete-orphan")
    onboarding_history = relationship("OnboardingHistory", back_populates="employee", cascade="all, delete-orphan")


class FamilyMember(Base):
    __tablename__ = "family_members"

    family_id = Column(Integer, primary_key=True)
    employee_id = Column(String(50), ForeignKey("employee_master.employee_id"), nullable=False)
    relation_type = Column(String(50), nullable=False)
    name = Column(String(100), nullable=False)
    dob = Column(Date)
    aadhar_number = Column(String(12))
    dependant = Column(String(10), default="No")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50))
    updated_by = Column(String(50))

    # Relationship back to employee
    employee = relationship("EmployeeMaster", back_populates="family_members")


class EducationHistory(Base):
    __tablename__ = "education_history"

    education_id = Column(Integer, primary_key=True)
    employee_id = Column(String(50), ForeignKey("employee_master.employee_id"), nullable=False)
    type_of_degree = Column(String(50), nullable=False)
    course_name = Column(String(100), nullable=False)
    school_college_name = Column(String(150), nullable=False)
    affiliated_university = Column(String(150))
    certificate_url = Column(Text)
    completed_in_month_year = Column(String(50))
    percentage_cgpa = Column(String(10))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50))
    updated_by = Column(String(50))

    # Relationship back to employee
    employee = relationship("EmployeeMaster", back_populates="education_history")


class ExperienceHistory(Base):
    __tablename__ = "experience_history"

    experience_id = Column(Integer, primary_key=True)
    employee_id = Column(String(50), ForeignKey("employee_master.employee_id"), nullable=False)
    company_name = Column(String(150), nullable=False)
    designation = Column(String(100), nullable=False)
    department = Column(String(100))
    office_email_id = Column(String(100))
    uan_no = Column(String(50))
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50))
    updated_by = Column(String(50))

    # Relationship back to employee
    employee = relationship("EmployeeMaster", back_populates="experience_history")


class AssetHistory(Base):
    __tablename__ = "asset_history"

    asset_id = Column(Integer, primary_key=True)
    employee_id = Column(String(50), ForeignKey("employee_master.employee_id"), nullable=False)
    asset_type = Column(String(50), nullable=False)
    asset_number = Column(String(50), nullable=False)
    issued_date = Column(Date, nullable=False)
    return_date = Column(Date)
    status = Column(String(20), default="Issued")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50))
    updated_by = Column(String(50))

    # Relationship back to employee
    employee = relationship("EmployeeMaster", back_populates="asset_history")


class AddressHistory(Base):
    __tablename__ = "address_history"

    address_id = Column(Integer, primary_key=True)
    employee_id = Column(String(50), ForeignKey("employee_master.employee_id"), nullable=False)
    address_type = Column(String(50), nullable=False)
    h_no = Column(String(20))
    street = Column(String(100))
    street2 = Column(String(100))
    landmark = Column(String(100))
    city = Column(String(50))
    state = Column(String(50))
    postal_code = Column(String(10))
    complete_address = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50))
    updated_by = Column(String(50))

    # Relationship back to employee
    employee = relationship("EmployeeMaster", back_populates="address_history")


class ClientMaster(Base):
    __tablename__ = "client_master"

    client_id = Column(Integer, primary_key=True)
    client_name = Column(String(150), nullable=False)
    client_code = Column(String(20), unique=True)
    client_address = Column(Text)
    client_contact_person = Column(String(100))
    client_email = Column(String(100))
    client_phone = Column(String(15))
    client_status = Column(String(20), default="Active")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    employees = relationship("EmployeeMaster", back_populates="current_client")
    onboarding_history = relationship("OnboardingHistory", back_populates="client")


class OnboardingHistory(Base):
    __tablename__ = "onboarding_history"

    onboarding_id = Column(Integer, primary_key=True)
    employee_id = Column(String(50), ForeignKey("employee_master.employee_id", ondelete="CASCADE"), nullable=False)
    client_id = Column(Integer, ForeignKey("client_master.client_id", ondelete="RESTRICT"), nullable=False)

    # M: Onboarding Details
    effective_start_date = Column(Date, nullable=False)
    effective_end_date = Column(Date)
    onboarding_status = Column(String(30), nullable=False)
    duration_calculated = Column(String(50))
    spoc = Column(String(100))
    onboarding_department = Column(String(100))
    assigned_manager = Column(String(100))
    notification_email_triggered = Column(String(10), default="No")

    # Additional onboarding specific fields
    project_name = Column(String(150))
    role_in_project = Column(String(100))
    billing_rate = Column(Numeric(10, 2))
    currency = Column(String(10), default="INR")
    work_location = Column(String(100))
    reporting_manager = Column(String(100))

    # Onboarding process tracking
    onboarding_checklist_completed = Column(String(10), default="No")
    client_training_completed = Column(String(10), default="No")
    access_provided = Column(String(10), default="No")

    # Contract specific to this onboarding
    contract_start_date = Column(Date)
    contract_end_date = Column(Date)
    contract_type = Column(String(50))

    # Financial details for this assignment
    monthly_billing_amount = Column(Numeric(12, 2))
    total_contract_value = Column(Numeric(12, 2))

    # Status tracking
    is_current_assignment = Column(String(10), default="No")
    exit_date = Column(Date)
    exit_reason = Column(String(200))

    # Audit fields
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50))
    updated_by = Column(String(50))

    # Relationships
    employee = relationship("EmployeeMaster", back_populates="onboarding_history")
    client = relationship("ClientMaster", back_populates="onboarding_history")

