from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field, HttpUrl


class AssetCreate(BaseModel):
    asset_name: str = Field(..., min_length=1)
    asset_type: str = Field(..., description="Laptop, Head Phones, Mouse, Keyboard, etc")
    asset_model: Optional[str] = None
    category: str = Field(..., description="Internal or External (from AssetCategory)")
    company_name: Optional[str] = None
    asset_description: Optional[str] = None
    serial_no: Optional[str] = None
    issued_on: Optional[date] = None
    returned_on: Optional[date] = None
    asset_status: str = Field(..., description="In Use, Damaged, Returned, Open")
    quantity: int = 1
    notes: Optional[str] = None
    employee_id: Optional[str] = None
    department: Optional[str] = None
    attachment_url: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AssetOut(BaseModel):
    id: int
    asset_name: str
    asset_type: str
    asset_model: Optional[str]
    category: str
    company_name: Optional[str]
    asset_description: Optional[str]
    serial_no: Optional[str]
    issued_on: Optional[date]
    returned_on: Optional[date]
    asset_status: str
    quantity: int
    notes: Optional[str]
    employee_id: Optional[str]
    department: Optional[str]
    attachment_url: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    created_by: Optional[str]
    updated_by: Optional[str]


class AssetFilters(BaseModel):
    search: Optional[str] = None
    employee_id: Optional[str] = None
    asset_type: Optional[str] = None
    asset_status: Optional[str] = None


class AssetUpdate(BaseModel):
    asset_name: Optional[str] = None
    asset_type: Optional[str] = None
    asset_model: Optional[str] = None
    category: Optional[str] = None
    company_name: Optional[str] = None
    asset_description: Optional[str] = None
    serial_no: Optional[str] = None
    issued_on: Optional[date] = None
    returned_on: Optional[date] = None
    asset_status: Optional[str] = None
    quantity: Optional[int] = None
    notes: Optional[str] = None
    employee_id: Optional[str] = None
    department: Optional[str] = None
    attachment_url: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AssetUploadRequest(BaseModel):
    file_name: str
    content_type: str


class AssetPresignedResponse(BaseModel):
    upload_url: str
    object_url: str
    file_key: str


class AssetCategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class AssetCategoryOut(BaseModel):
    id: int
    name: str



class AssetAssignRequest(BaseModel):
    employee_id: str = Field(..., min_length=1)
    issued_on: Optional[date] = None
    attachment_url: Optional[str] = None


class AssetUnassignRequest(BaseModel):
    returned_on: Optional[date] = None
    condition_on_return: Optional[str] = None
    attachment_url: Optional[str] = None


class AssetAssignmentOut(BaseModel):
    id: int
    asset_id: int
    employee_id: str
    issued_on: Optional[date]
    returned_on: Optional[date]
    condition_on_return: Optional[str]
    attachment_url: Optional[str]


class AssetAttachmentCreate(BaseModel):
    file_type: str
    file_url: str
    created_by: Optional[str] = None


class AssetAttachmentOut(BaseModel):
    id: int
    asset_id: int
    file_type: str
    file_url: str
    created_at: datetime
    updated_at: Optional[datetime]
    created_by: Optional[str]
    updated_by: Optional[str]


class AssetBulkRow(BaseModel):
    asset_name: str
    asset_type: str
    asset_model: Optional[str] = None
    category: str
    company_name: Optional[str] = None
    asset_description: Optional[str] = None
    serial_no: Optional[str] = None
    asset_status: str
    quantity: int = 1
    notes: Optional[str] = None
    employee_id: Optional[str] = None
    department: Optional[str] = None
    attachment_url: Optional[str] = None


class AssetBulkImportRequest(BaseModel):
    items: List[AssetBulkRow]



# Historical data response models
class MaintenanceLogOut(BaseModel):
    id: int
    asset_id: int
    vendor: Optional[str]
    cost: Optional[int]
    scheduled_date: Optional[date]
    completed_date: Optional[date]
    created_at: datetime
    updated_at: Optional[datetime]
    created_by: Optional[str]
    updated_by: Optional[str]


class AssetHistoryOut(BaseModel):
    assignments: List[AssetAssignmentOut]
    maintenance_logs: List[MaintenanceLogOut]
