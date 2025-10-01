from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.sql import func
from app.database import Base


class Category(Base):
    __tablename__ = "category"

    id = Column(Integer, primary_key=True, index=True)
    # Map ORM attribute to DB column 'type' to match existing schema
    type_of_category = Column('type', String(100), nullable=False, unique=True)
    created_by = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())
    updated_by = Column(String(50))
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class EmployeeType(Base):
    __tablename__ = "employee_type"

    id = Column(Integer, primary_key=True, index=True)
    # Map ORM attribute to DB column 'type' to match existing schema
    type_of_employee = Column('type', String(100), nullable=False, unique=True)
    created_by = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())
    updated_by = Column(String(50))
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ExcludedFromPayroll(Base):
    __tablename__ = "excluded_from_payroll"

    id = Column(Integer, primary_key=True, index=True)
    value = Column(String(10), nullable=False, unique=True)
    created_by = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())
    updated_by = Column(String(50))
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class MaritalStatus(Base):
    __tablename__ = "marital_status"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String(20), nullable=False, unique=True)
    created_by = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())
    updated_by = Column(String(50))
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class BloodGroup(Base):
    __tablename__ = "blood_group"

    id = Column(Integer, primary_key=True, index=True)
    group = Column(String(5), nullable=False, unique=True)
    created_by = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())
    updated_by = Column(String(50))
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class AddressType(Base):
    __tablename__ = "address_type"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(20), nullable=False, unique=True)
    created_by = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())
    updated_by = Column(String(50))
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class RelationType(Base):
    __tablename__ = "relation_type"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(20), nullable=False, unique=True)
    created_by = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())
    updated_by = Column(String(50))
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class TypeOfDegree(Base):
    __tablename__ = "type_of_degree"

    id = Column(Integer, primary_key=True, index=True)
    degree = Column(String(20), nullable=False, unique=True)
    created_by = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())
    updated_by = Column(String(50))
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class JobType(Base):
    __tablename__ = "job_type"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(20), nullable=False, unique=True)
    created_by = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())
    updated_by = Column(String(50))
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class AssetStatus(Base):
    __tablename__ = "asset_status"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String(20), nullable=False, unique=True)
    created_by = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())
    updated_by = Column(String(50))
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Title(Base):
    __tablename__ = "title_master"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(10), nullable=False, unique=True)
    created_by = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())
    updated_by = Column(String(50))
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Gender(Base):
    __tablename__ = "gender_master"

    id = Column(Integer, primary_key=True, index=True)
    gender = Column(String(20), nullable=False, unique=True)
    created_by = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())
    updated_by = Column(String(50))
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class AssetType(Base):
    __tablename__ = "asset_type"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(50), nullable=False, unique=True)
    created_by = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())
    updated_by = Column(String(50))
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())