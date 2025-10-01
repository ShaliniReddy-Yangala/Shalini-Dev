from sqlalchemy import Column, Integer, String, Date, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)

    asset_name = Column(String(200), nullable=False, index=True)
    asset_type = Column(String(100), nullable=False, index=True)
    asset_model = Column(String(150), nullable=True)
    category = Column(String(50), nullable=False, index=True)  # Internal, External
    company_name = Column(String(150), nullable=True)
    asset_description = Column(Text, nullable=True)
    serial_no = Column(String(150), nullable=True, index=True)
    issued_on = Column(Date, nullable=True)
    returned_on = Column(Date, nullable=True)
    asset_status = Column(String(50), nullable=False, index=True)  # In Use, Damaged, Returned, Open
    quantity = Column(Integer, default=1, nullable=False)
    notes = Column(Text, nullable=True)
    employee_id = Column(String(50), nullable=True, index=True)
    department = Column(String(100), nullable=True, index=True)
    attachment_url = Column(String(500), nullable=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50))
    updated_by = Column(String(50))


class AssetCategory(Base):
    __tablename__ = "asset_category"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50))
    updated_by = Column(String(50))


class AssetAssignment(Base):
    __tablename__ = "asset_assignments"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False, index=True)
    employee_id = Column(String(50), nullable=False, index=True)
    issued_on = Column(Date, nullable=True)
    returned_on = Column(Date, nullable=True)
    condition_on_return = Column(String(200), nullable=True)
    attachment_url = Column(String(500), nullable=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50))
    updated_by = Column(String(50))


class AssetAttachment(Base):
    __tablename__ = "asset_attachments"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False, index=True)
    file_type = Column(String(50), nullable=False)
    file_url = Column(String(500), nullable=False)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50))
    updated_by = Column(String(50))


class MaintenanceLog(Base):
    __tablename__ = "maintenance_logs"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False, index=True)
    vendor = Column(String(150), nullable=True)
    cost = Column(Integer, nullable=True)
    scheduled_date = Column(Date, nullable=True)
    completed_date = Column(Date, nullable=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50))
    updated_by = Column(String(50))


class License(Base):
    __tablename__ = "licenses"

    id = Column(Integer, primary_key=True, index=True)
    software_name = Column(String(150), nullable=False, index=True)
    license_key = Column(String(200), nullable=True, index=True)
    vendor = Column(String(150), nullable=True)
    invoice_copy = Column(String(500), nullable=True)
    assigned_to = Column(String(50), nullable=True, index=True)
    expiry_date = Column(Date, nullable=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by = Column(String(50))
    updated_by = Column(String(50))


