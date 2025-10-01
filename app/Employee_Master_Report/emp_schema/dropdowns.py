# from pydantic import BaseModel, Field
# from typing import Optional
# from datetime import datetime


# class CategoryIn(BaseModel):
#     type_of_category: str = Field(..., min_length=1, max_length=100)


# class CategoryOut(BaseModel):
#     id: int
#     type_of_category: str
#     created_by: Optional[str] = None
#     created_at: str
#     updated_by: Optional[str] = None
#     updated_at: str


# class EmployeeTypeIn(BaseModel):
#     type_of_employee: str = Field(..., min_length=1, max_length=100)


# class EmployeeTypeOut(BaseModel):
#     id: int
#     type_of_employee: str
#     created_by: Optional[str] = None
#     created_at: str
#     updated_by: Optional[str] = None
#     updated_at: str



from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CategoryIn(BaseModel):
    type_of_category: str = Field(..., min_length=1, max_length=100)


class CategoryOut(BaseModel):
    id: int
    type_of_category: str
    created_by: Optional[str] = None
    created_at: str
    updated_by: Optional[str] = None
    updated_at: str


class EmployeeTypeIn(BaseModel):
    type_of_employee: str = Field(..., min_length=1, max_length=100)


class EmployeeTypeOut(BaseModel):
    id: int
    type_of_employee: str
    created_by: Optional[str] = None
    created_at: str
    updated_by: Optional[str] = None
    updated_at: str


# Excluded from Payroll schemas
class ExcludedFromPayrollIn(BaseModel):
    value: str = Field(..., min_length=1, max_length=10)


class ExcludedFromPayrollOut(BaseModel):
    id: int
    value: str
    created_by: Optional[str] = None
    created_at: str
    updated_by: Optional[str] = None
    updated_at: str


# Marital Status schemas
class MaritalStatusIn(BaseModel):
    status: str = Field(..., min_length=1, max_length=20)


class MaritalStatusOut(BaseModel):
    id: int
    status: str
    created_by: Optional[str] = None
    created_at: str
    updated_by: Optional[str] = None
    updated_at: str


# Blood Group schemas
class BloodGroupIn(BaseModel):
    group: str = Field(..., min_length=1, max_length=5)


class BloodGroupOut(BaseModel):
    id: int
    group: str
    created_by: Optional[str] = None
    created_at: str
    updated_by: Optional[str] = None
    updated_at: str


# Address Type schemas
class AddressTypeIn(BaseModel):
    type: str = Field(..., min_length=1, max_length=20)


class AddressTypeOut(BaseModel):
    id: int
    type: str
    created_by: Optional[str] = None
    created_at: str
    updated_by: Optional[str] = None
    updated_at: str


# Relation Type schemas
class RelationTypeIn(BaseModel):
    type: str = Field(..., min_length=1, max_length=20)


class RelationTypeOut(BaseModel):
    id: int
    type: str
    created_by: Optional[str] = None
    created_at: str
    updated_by: Optional[str] = None
    updated_at: str


# Type of Degree schemas
class TypeOfDegreeIn(BaseModel):
    degree: str = Field(..., min_length=1, max_length=20)


class TypeOfDegreeOut(BaseModel):
    id: int
    degree: str
    created_by: Optional[str] = None
    created_at: str
    updated_by: Optional[str] = None
    updated_at: str


# Job Type schemas
class JobTypeIn(BaseModel):
    type: str = Field(..., min_length=1, max_length=20)


class JobTypeOut(BaseModel):
    id: int
    type: str
    created_by: Optional[str] = None
    created_at: str
    updated_by: Optional[str] = None
    updated_at: str


# Asset Status schemas
class AssetStatusIn(BaseModel):
    status: str = Field(..., min_length=1, max_length=20)


class AssetStatusOut(BaseModel):
    id: int
    status: str
    created_by: Optional[str] = None
    created_at: str
    updated_by: Optional[str] = None
    updated_at: str


# Title schemas
class TitleIn(BaseModel):
    title: str = Field(..., min_length=2, max_length=10)


class TitleOut(BaseModel):
    id: int
    title: str
    created_by: Optional[str] = None
    created_at: str
    updated_by: Optional[str] = None
    updated_at: str


# Gender schemas
class GenderIn(BaseModel):
    gender: str = Field(..., min_length=1, max_length=20)


class GenderOut(BaseModel):
    id: int
    gender: str
    created_by: Optional[str] = None
    created_at: str
    updated_by: Optional[str] = None
    updated_at: str


# Asset Type schemas
class AssetTypeIn(BaseModel):
    type: str = Field(..., min_length=1, max_length=50)


class AssetTypeOut(BaseModel):
    id: int
    type: str
    created_by: Optional[str] = None
    created_at: str
    updated_by: Optional[str] = None
    updated_at: str