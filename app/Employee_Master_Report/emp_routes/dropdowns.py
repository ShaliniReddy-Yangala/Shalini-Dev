# from fastapi import APIRouter, Depends, HTTPException, status
# from sqlalchemy.orm import Session
# from app.database import get_db
# from app.Employee_Master_Report.emp_models.dropdowns import Category, EmployeeType
# from app.Employee_Master_Report.emp_schema.dropdowns import (
#     CategoryIn, CategoryOut,
#     EmployeeTypeIn, EmployeeTypeOut
# )

# router = APIRouter(prefix="/employee-entry", tags=["Employee Entry - Dropdowns"])


# # Category Routes
# @router.post("/category", status_code=status.HTTP_201_CREATED, response_model=CategoryOut)
# def create_category(payload: CategoryIn, db: Session = Depends(get_db)):
#     """Create a new category"""
    
#     # Check if category already exists
#     existing_category = db.query(Category).filter(Category.type_of_category == payload.type_of_category).first()
#     if existing_category:
#         raise HTTPException(status_code=400, detail="Category already exists")
    
#     category = Category(
#         type_of_category=payload.type_of_category,
#         created_by="system",
#         updated_by="system"
#     )
    
#     db.add(category)
#     db.commit()
#     db.refresh(category)
    
#     return CategoryOut(
#         id=category.id,
#         type_of_category=category.type_of_category,
#         created_by=category.created_by,
#         created_at=str(category.created_at),
#         updated_by=category.updated_by,
#         updated_at=str(category.updated_at)
#     )


# @router.get("/categories", response_model=list[CategoryOut])
# def get_categories(db: Session = Depends(get_db)):
#     """Get all categories"""
    
#     categories = db.query(Category).order_by(Category.type_of_category.asc()).all()
    
#     result = []
#     for category in categories:
#         result.append(CategoryOut(
#             id=category.id,
#             type_of_category=category.type_of_category,
#             created_by=category.created_by,
#             created_at=str(category.created_at),
#             updated_by=category.updated_by,
#             updated_at=str(category.updated_at)
#         ))
    
#     return result


# @router.put("/category/{category_id}", response_model=CategoryOut)
# def update_category(category_id: int, payload: CategoryIn, db: Session = Depends(get_db)):
#     """Update a category"""
    
#     category = db.query(Category).filter(Category.id == category_id).first()
#     if not category:
#         raise HTTPException(status_code=404, detail="Category not found")
    
#     # Check if new type already exists for different category
#     existing_category = db.query(Category).filter(
#         Category.type_of_category == payload.type_of_category,
#         Category.id != category_id
#     ).first()
#     if existing_category:
#         raise HTTPException(status_code=400, detail="Category type already exists")
    
#     category.type_of_category = payload.type_of_category
#     category.updated_by = "system"
    
#     db.commit()
#     db.refresh(category)
    
#     return CategoryOut(
#         id=category.id,
#         type_of_category=category.type_of_category,
#         created_by=category.created_by,
#         created_at=str(category.created_at),
#         updated_by=category.updated_by,
#         updated_at=str(category.updated_at)
#     )


# @router.delete("/category/{category_id}")
# def delete_category(category_id: int, db: Session = Depends(get_db)):
#     """Delete a category"""
    
#     category = db.query(Category).filter(Category.id == category_id).first()
#     if not category:
#         raise HTTPException(status_code=404, detail="Category not found")
    
#     db.delete(category)
#     db.commit()
    
#     return {"message": "Category deleted successfully"}


# # Employee Type Routes
# @router.post("/employee-type", status_code=status.HTTP_201_CREATED, response_model=EmployeeTypeOut)
# def create_employee_type(payload: EmployeeTypeIn, db: Session = Depends(get_db)):
#     """Create a new employee type"""
    
#     # Check if employee type already exists
#     existing_type = db.query(EmployeeType).filter(EmployeeType.type_of_employee == payload.type_of_employee).first()
#     if existing_type:
#         raise HTTPException(status_code=400, detail="Employee type already exists")
    
#     employee_type = EmployeeType(
#         type_of_employee=payload.type_of_employee,
#         created_by="system",
#         updated_by="system"
#     )
    
#     db.add(employee_type)
#     db.commit()
#     db.refresh(employee_type)
    
#     return EmployeeTypeOut(
#         id=employee_type.id,
#         type_of_employee=employee_type.type_of_employee,
#         created_by=employee_type.created_by,
#         created_at=str(employee_type.created_at),
#         updated_by=employee_type.updated_by,
#         updated_at=str(employee_type.updated_at)
#     )


# @router.get("/employee-types", response_model=list[EmployeeTypeOut])
# def get_employee_types(db: Session = Depends(get_db)):
#     """Get all employee types"""
    
#     employee_types = db.query(EmployeeType).order_by(EmployeeType.type_of_employee.asc()).all()
    
#     result = []
#     for emp_type in employee_types:
#         result.append(EmployeeTypeOut(
#             id=emp_type.id,
#             type=emp_type.type,
#             created_by=emp_type.created_by,
#             created_at=str(emp_type.created_at),
#             updated_by=emp_type.updated_by,
#             updated_at=str(emp_type.updated_at)
#         ))
    
#     return result


# @router.put("/employee-type/{employee_type_id}", response_model=EmployeeTypeOut)
# def update_employee_type(employee_type_id: int, payload: EmployeeTypeIn, db: Session = Depends(get_db)):
#     """Update an employee type"""
    
#     employee_type = db.query(EmployeeType).filter(EmployeeType.id == employee_type_id).first()
#     if not employee_type:
#         raise HTTPException(status_code=404, detail="Employee type not found")
    
#     # Check if new type already exists for different employee type
#     existing_type = db.query(EmployeeType).filter(
#         EmployeeType.type_of_employee == payload.type_of_employee,
#         EmployeeType.id != employee_type_id
#     ).first()
#     if existing_type:
#         raise HTTPException(status_code=400, detail="Employee type already exists")
    
#     employee_type.type_of_employee = payload.type_of_employee
#     employee_type.updated_by = "system"
    
#     db.commit()
#     db.refresh(employee_type)
    
#     return EmployeeTypeOut(
#         id=employee_type.id,
#         type_of_employee=employee_type.type_of_employee,
#         created_by=employee_type.created_by,
#         created_at=str(employee_type.created_at),
#         updated_by=employee_type.updated_by,
#         updated_at=str(employee_type.updated_at)
#     )


# @router.delete("/employee-type/{employee_type_id}")
# def delete_employee_type(employee_type_id: int, db: Session = Depends(get_db)):
#     """Delete an employee type"""
    
#     employee_type = db.query(EmployeeType).filter(EmployeeType.id == employee_type_id).first()
#     if not employee_type:
#         raise HTTPException(status_code=404, detail="Employee type not found")
    
#     db.delete(employee_type)
#     db.commit()
    
#     return {"message": "Employee type deleted successfully"}






from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.Employee_Master_Report.emp_models.dropdowns import (
    Category, EmployeeType, ExcludedFromPayroll, MaritalStatus, BloodGroup,
    AddressType, RelationType, TypeOfDegree, JobType, AssetStatus, Title, Gender, AssetType
)
from app.Employee_Master_Report.emp_schema.dropdowns import (
    CategoryIn, CategoryOut,
    EmployeeTypeIn, EmployeeTypeOut,
    ExcludedFromPayrollIn, ExcludedFromPayrollOut,
    MaritalStatusIn, MaritalStatusOut,
    BloodGroupIn, BloodGroupOut,
    AddressTypeIn, AddressTypeOut,
    RelationTypeIn, RelationTypeOut,
    TypeOfDegreeIn, TypeOfDegreeOut,
    JobTypeIn, JobTypeOut,
    AssetStatusIn, AssetStatusOut,
    TitleIn, TitleOut,
    GenderIn, GenderOut,
    AssetTypeIn, AssetTypeOut
)

router = APIRouter(prefix="/employee-entry", tags=["Employee Entry - Dropdowns"])
# Title Routes
@router.post("/title", status_code=status.HTTP_201_CREATED, response_model=TitleOut)
def create_title(payload: TitleIn, db: Session = Depends(get_db)):
    existing = db.query(Title).filter(Title.title == payload.title).first()
    if existing:
        raise HTTPException(status_code=400, detail="Title already exists")
    item = Title(title=payload.title, created_by="system", updated_by="system")
    db.add(item); db.commit(); db.refresh(item)
    return TitleOut(id=item.id, title=item.title, created_by=item.created_by, created_at=str(item.created_at), updated_by=item.updated_by, updated_at=str(item.updated_at))


@router.get("/titles", response_model=list[TitleOut])
def get_titles(db: Session = Depends(get_db)):
    rows = db.query(Title).order_by(Title.title.asc()).all()
    return [TitleOut(id=r.id, title=r.title, created_by=r.created_by, created_at=str(r.created_at), updated_by=r.updated_by, updated_at=str(r.updated_at)) for r in rows]


@router.put("/title/{title_id}", response_model=TitleOut)
def update_title(title_id: int, payload: TitleIn, db: Session = Depends(get_db)):
    item = db.query(Title).filter(Title.id == title_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Title not found")
    existing = db.query(Title).filter(Title.title == payload.title, Title.id != title_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Title already exists")
    item.title = payload.title; item.updated_by = "system"; db.commit(); db.refresh(item)
    return TitleOut(id=item.id, title=item.title, created_by=item.created_by, created_at=str(item.created_at), updated_by=item.updated_by, updated_at=str(item.updated_at))


@router.delete("/title/{title_id}")
def delete_title(title_id: int, db: Session = Depends(get_db)):
    item = db.query(Title).filter(Title.id == title_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Title not found")
    db.delete(item); db.commit()
    return {"message": "Title deleted successfully"}


# Gender Routes
@router.post("/gender", status_code=status.HTTP_201_CREATED, response_model=GenderOut)
def create_gender(payload: GenderIn, db: Session = Depends(get_db)):
    existing = db.query(Gender).filter(Gender.gender == payload.gender).first()
    if existing:
        raise HTTPException(status_code=400, detail="Gender already exists")
    item = Gender(gender=payload.gender, created_by="system", updated_by="system")
    db.add(item); db.commit(); db.refresh(item)
    return GenderOut(id=item.id, gender=item.gender, created_by=item.created_by, created_at=str(item.created_at), updated_by=item.updated_by, updated_at=str(item.updated_at))


@router.get("/genders", response_model=list[GenderOut])
def get_genders(db: Session = Depends(get_db)):
    rows = db.query(Gender).order_by(Gender.gender.asc()).all()
    return [GenderOut(id=r.id, gender=r.gender, created_by=r.created_by, created_at=str(r.created_at), updated_by=r.updated_by, updated_at=str(r.updated_at)) for r in rows]


@router.put("/gender/{gender_id}", response_model=GenderOut)
def update_gender(gender_id: int, payload: GenderIn, db: Session = Depends(get_db)):
    item = db.query(Gender).filter(Gender.id == gender_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Gender not found")
    existing = db.query(Gender).filter(Gender.gender == payload.gender, Gender.id != gender_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Gender already exists")
    item.gender = payload.gender; item.updated_by = "system"; db.commit(); db.refresh(item)
    return GenderOut(id=item.id, gender=item.gender, created_by=item.created_by, created_at=str(item.created_at), updated_by=item.updated_by, updated_at=str(item.updated_at))


@router.delete("/gender/{gender_id}")
def delete_gender(gender_id: int, db: Session = Depends(get_db)):
    item = db.query(Gender).filter(Gender.id == gender_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Gender not found")
    db.delete(item); db.commit()
    return {"message": "Gender deleted successfully"}


# Asset Type Routes
@router.post("/asset-type", status_code=status.HTTP_201_CREATED, response_model=AssetTypeOut)
def create_asset_type(payload: AssetTypeIn, db: Session = Depends(get_db)):
    existing = db.query(AssetType).filter(AssetType.type == payload.type).first()
    if existing:
        raise HTTPException(status_code=400, detail="Asset type already exists")
    item = AssetType(type=payload.type, created_by="system", updated_by="system")
    db.add(item); db.commit(); db.refresh(item)
    return AssetTypeOut(id=item.id, type=item.type, created_by=item.created_by, created_at=str(item.created_at), updated_by=item.updated_by, updated_at=str(item.updated_at))


@router.get("/asset-type", response_model=list[AssetTypeOut])
def get_asset_type(db: Session = Depends(get_db)):
    rows = db.query(AssetType).order_by(AssetType.type.asc()).all()
    return [AssetTypeOut(id=r.id, type=r.type, created_by=r.created_by, created_at=str(r.created_at), updated_by=r.updated_by, updated_at=str(r.updated_at)) for r in rows]


@router.put("/asset-type/{asset_type_id}", response_model=AssetTypeOut)
def update_asset_type(asset_type_id: int, payload: AssetTypeIn, db: Session = Depends(get_db)):
    item = db.query(AssetType).filter(AssetType.id == asset_type_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Asset type not found")
    existing = db.query(AssetType).filter(AssetType.type == payload.type, AssetType.id != asset_type_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Asset type already exists")
    item.type = payload.type; item.updated_by = "system"; db.commit(); db.refresh(item)
    return AssetTypeOut(id=item.id, type=item.type, created_by=item.created_by, created_at=str(item.created_at), updated_by=item.updated_by, updated_at=str(item.updated_at))


@router.delete("/asset-type/{asset_type_id}")
def delete_asset_type(asset_type_id: int, db: Session = Depends(get_db)):
    item = db.query(AssetType).filter(AssetType.id == asset_type_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Asset type not found")
    db.delete(item); db.commit()
    return {"message": "Asset type deleted successfully"}


# Category Routes
@router.post("/category", status_code=status.HTTP_201_CREATED, response_model=CategoryOut)
def create_category(payload: CategoryIn, db: Session = Depends(get_db)):
    """Create a new category"""
    
    # Check if category already exists
    existing_category = db.query(Category).filter(Category.type_of_category == payload.type_of_category).first()
    if existing_category:
        raise HTTPException(status_code=400, detail="Category already exists")
    
    category = Category(
        type_of_category=payload.type_of_category,
        created_by="system",
        updated_by="system"
    )
    
    db.add(category)
    db.commit()
    db.refresh(category)
    
    return CategoryOut(
        id=category.id,
        type_of_category=category.type_of_category,
        created_by=category.created_by,
        created_at=str(category.created_at),
        updated_by=category.updated_by,
        updated_at=str(category.updated_at)
    )


@router.get("/categories", response_model=list[CategoryOut])
def get_categories(db: Session = Depends(get_db)):
    """Get all categories"""
    
    categories = db.query(Category).order_by(Category.type_of_category.asc()).all()
    
    result = []
    for category in categories:
        result.append(CategoryOut(
            id=category.id,
            type_of_category=category.type_of_category,
            created_by=category.created_by,
            created_at=str(category.created_at),
            updated_by=category.updated_by,
            updated_at=str(category.updated_at)
        ))
    
    return result


@router.put("/category/{category_id}", response_model=CategoryOut)
def update_category(category_id: int, payload: CategoryIn, db: Session = Depends(get_db)):
    """Update a category"""
    
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Check if new type already exists for different category
    existing_category = db.query(Category).filter(
        Category.type_of_category == payload.type_of_category,
        Category.id != category_id
    ).first()
    if existing_category:
        raise HTTPException(status_code=400, detail="Category type already exists")
    
    category.type_of_category = payload.type_of_category
    category.updated_by = "system"
    
    db.commit()
    db.refresh(category)
    
    return CategoryOut(
        id=category.id,
        type_of_category=category.type_of_category,
        created_by=category.created_by,
        created_at=str(category.created_at),
        updated_by=category.updated_by,
        updated_at=str(category.updated_at)
    )


@router.delete("/category/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db)):
    """Delete a category"""
    
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    db.delete(category)
    db.commit()
    
    return {"message": "Category deleted successfully"}


# Employee Type Routes
@router.post("/employee-type", status_code=status.HTTP_201_CREATED, response_model=EmployeeTypeOut)
def create_employee_type(payload: EmployeeTypeIn, db: Session = Depends(get_db)):
    """Create a new employee type"""
    
    # Check if employee type already exists
    existing_type = db.query(EmployeeType).filter(EmployeeType.type_of_employee == payload.type_of_employee).first()
    if existing_type:
        raise HTTPException(status_code=400, detail="Employee type already exists")
    
    employee_type = EmployeeType(
        type_of_employee=payload.type_of_employee,
        created_by="system",
        updated_by="system"
    )
    
    db.add(employee_type)
    db.commit()
    db.refresh(employee_type)
    
    return EmployeeTypeOut(
        id=employee_type.id,
        type_of_employee=employee_type.type_of_employee,
        created_by=employee_type.created_by,
        created_at=str(employee_type.created_at),
        updated_by=employee_type.updated_by,
        updated_at=str(employee_type.updated_at)
    )


@router.get("/employee-types", response_model=list[EmployeeTypeOut])
def get_employee_types(db: Session = Depends(get_db)):
    """Get all employee types"""
    
    employee_types = db.query(EmployeeType).order_by(EmployeeType.type_of_employee.asc()).all()
    
    result = []
    for emp_type in employee_types:
        result.append(EmployeeTypeOut(
            id=emp_type.id,
            type_of_employee=emp_type.type_of_employee,
            created_by=emp_type.created_by,
            created_at=str(emp_type.created_at),
            updated_by=emp_type.updated_by,
            updated_at=str(emp_type.updated_at)
        ))
    
    return result


@router.put("/employee-type/{employee_type_id}", response_model=EmployeeTypeOut)
def update_employee_type(employee_type_id: int, payload: EmployeeTypeIn, db: Session = Depends(get_db)):
    """Update an employee type"""
    
    employee_type = db.query(EmployeeType).filter(EmployeeType.id == employee_type_id).first()
    if not employee_type:
        raise HTTPException(status_code=404, detail="Employee type not found")
    
    # Check if new type already exists for different employee type
    existing_type = db.query(EmployeeType).filter(
        EmployeeType.type_of_employee == payload.type_of_employee,
        EmployeeType.id != employee_type_id
    ).first()
    if existing_type:
        raise HTTPException(status_code=400, detail="Employee type already exists")
    
    employee_type.type_of_employee = payload.type_of_employee
    employee_type.updated_by = "system"
    
    db.commit()
    db.refresh(employee_type)
    
    return EmployeeTypeOut(
        id=employee_type.id,
        type_of_employee=employee_type.type_of_employee,
        created_by=employee_type.created_by,
        created_at=str(employee_type.created_at),
        updated_by=employee_type.updated_by,
        updated_at=str(employee_type.updated_at)
    )


@router.delete("/employee-type/{employee_type_id}")
def delete_employee_type(employee_type_id: int, db: Session = Depends(get_db)):
    """Delete an employee type"""
    
    employee_type = db.query(EmployeeType).filter(EmployeeType.id == employee_type_id).first()
    if not employee_type:
        raise HTTPException(status_code=404, detail="Employee type not found")
    
    db.delete(employee_type)
    db.commit()
    
    return {"message": "Employee type deleted successfully"}


# Excluded from Payroll Routes
@router.post("/excluded-from-payroll", status_code=status.HTTP_201_CREATED, response_model=ExcludedFromPayrollOut)
def create_excluded_from_payroll(payload: ExcludedFromPayrollIn, db: Session = Depends(get_db)):
    """Create a new excluded from payroll value"""
    
    existing = db.query(ExcludedFromPayroll).filter(ExcludedFromPayroll.value == payload.value).first()
    if existing:
        raise HTTPException(status_code=400, detail="Value already exists")
    
    item = ExcludedFromPayroll(
        value=payload.value,
        created_by="system",
        updated_by="system"
    )
    
    db.add(item)
    db.commit()
    db.refresh(item)
    
    return ExcludedFromPayrollOut(
        id=item.id,
        value=item.value,
        created_by=item.created_by,
        created_at=str(item.created_at),
        updated_by=item.updated_by,
        updated_at=str(item.updated_at)
    )


@router.get("/excluded-from-payroll", response_model=list[ExcludedFromPayrollOut])
def get_excluded_from_payroll(db: Session = Depends(get_db)):
    """Get all excluded from payroll values"""
    
    items = db.query(ExcludedFromPayroll).order_by(ExcludedFromPayroll.value.asc()).all()
    
    result = []
    for item in items:
        result.append(ExcludedFromPayrollOut(
            id=item.id,
            value=item.value,
            created_by=item.created_by,
            created_at=str(item.created_at),
            updated_by=item.updated_by,
            updated_at=str(item.updated_at)
        ))
    
    return result


@router.put("/excluded-from-payroll/{item_id}", response_model=ExcludedFromPayrollOut)
def update_excluded_from_payroll(item_id: int, payload: ExcludedFromPayrollIn, db: Session = Depends(get_db)):
    """Update an excluded-from-payroll value"""
    item = db.query(ExcludedFromPayroll).filter(ExcludedFromPayroll.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Excluded from payroll not found")

    # Ensure no duplicate value
    existing = db.query(ExcludedFromPayroll).filter(
        ExcludedFromPayroll.value == payload.value,
        ExcludedFromPayroll.id != item_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Value already exists")

    item.value = payload.value
    item.updated_by = "system"
    db.commit()
    db.refresh(item)

    return ExcludedFromPayrollOut(
        id=item.id,
        value=item.value,
        created_by=item.created_by,
        created_at=str(item.created_at),
        updated_by=item.updated_by,
        updated_at=str(item.updated_at)
    )


@router.delete("/excluded-from-payroll/{item_id}")
def delete_excluded_from_payroll(item_id: int, db: Session = Depends(get_db)):
    """Delete an excluded-from-payroll value"""
    item = db.query(ExcludedFromPayroll).filter(ExcludedFromPayroll.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Excluded from payroll not found")

    db.delete(item)
    db.commit()

    return {"message": "Excluded from payroll deleted successfully"}

# Marital Status Routes
@router.post("/marital-status", status_code=status.HTTP_201_CREATED, response_model=MaritalStatusOut)
def create_marital_status(payload: MaritalStatusIn, db: Session = Depends(get_db)):
    """Create a new marital status"""
    
    existing = db.query(MaritalStatus).filter(MaritalStatus.status == payload.status).first()
    if existing:
        raise HTTPException(status_code=400, detail="Status already exists")
    
    item = MaritalStatus(
        status=payload.status,
        created_by="system",
        updated_by="system"
    )
    
    db.add(item)
    db.commit()
    db.refresh(item)
    
    return MaritalStatusOut(
        id=item.id,
        status=item.status,
        created_by=item.created_by,
        created_at=str(item.created_at),
        updated_by=item.updated_by,
        updated_at=str(item.updated_at)
    )


@router.get("/marital-status", response_model=list[MaritalStatusOut])
def get_marital_status(db: Session = Depends(get_db)):
    """Get all marital status values"""
    
    items = db.query(MaritalStatus).order_by(MaritalStatus.status.asc()).all()
    
    result = []
    for item in items:
        result.append(MaritalStatusOut(
            id=item.id,
            status=item.status,
            created_by=item.created_by,
            created_at=str(item.created_at),
            updated_by=item.updated_by,
            updated_at=str(item.updated_at)
        ))
    
    return result


@router.put("/marital-status/{item_id}", response_model=MaritalStatusOut)
def update_marital_status(item_id: int, payload: MaritalStatusIn, db: Session = Depends(get_db)):
    item = db.query(MaritalStatus).filter(MaritalStatus.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Marital status not found")
    existing = db.query(MaritalStatus).filter(MaritalStatus.status == payload.status, MaritalStatus.id != item_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Status already exists")
    item.status = payload.status
    item.updated_by = "system"
    db.commit(); db.refresh(item)
    return MaritalStatusOut(id=item.id, status=item.status, created_by=item.created_by, created_at=str(item.created_at), updated_by=item.updated_by, updated_at=str(item.updated_at))


@router.delete("/marital-status/{item_id}")
def delete_marital_status(item_id: int, db: Session = Depends(get_db)):
    item = db.query(MaritalStatus).filter(MaritalStatus.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Marital status not found")
    db.delete(item); db.commit()
    return {"message": "Marital status deleted successfully"}


# Blood Group Routes
@router.post("/blood-group", status_code=status.HTTP_201_CREATED, response_model=BloodGroupOut)
def create_blood_group(payload: BloodGroupIn, db: Session = Depends(get_db)):
    """Create a new blood group"""
    
    existing = db.query(BloodGroup).filter(BloodGroup.group == payload.group).first()
    if existing:
        raise HTTPException(status_code=400, detail="Blood group already exists")
    
    item = BloodGroup(
        group=payload.group,
        created_by="system",
        updated_by="system"
    )
    
    db.add(item)
    db.commit()
    db.refresh(item)
    
    return BloodGroupOut(
        id=item.id,
        group=item.group,
        created_by=item.created_by,
        created_at=str(item.created_at),
        updated_by=item.updated_by,
        updated_at=str(item.updated_at)
    )


@router.get("/blood-group", response_model=list[BloodGroupOut])
def get_blood_group(db: Session = Depends(get_db)):
    """Get all blood group values"""
    
    items = db.query(BloodGroup).order_by(BloodGroup.group.asc()).all()
    
    result = []
    for item in items:
        result.append(BloodGroupOut(
            id=item.id,
            group=item.group,
            created_by=item.created_by,
            created_at=str(item.created_at),
            updated_by=item.updated_by,
            updated_at=str(item.updated_at)
        ))
    
    return result


@router.put("/blood-group/{item_id}", response_model=BloodGroupOut)
def update_blood_group(item_id: int, payload: BloodGroupIn, db: Session = Depends(get_db)):
    item = db.query(BloodGroup).filter(BloodGroup.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Blood group not found")
    existing = db.query(BloodGroup).filter(BloodGroup.group == payload.group, BloodGroup.id != item_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Blood group already exists")
    item.group = payload.group
    item.updated_by = "system"
    db.commit(); db.refresh(item)
    return BloodGroupOut(id=item.id, group=item.group, created_by=item.created_by, created_at=str(item.created_at), updated_by=item.updated_by, updated_at=str(item.updated_at))


@router.delete("/blood-group/{item_id}")
def delete_blood_group(item_id: int, db: Session = Depends(get_db)):
    item = db.query(BloodGroup).filter(BloodGroup.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Blood group not found")
    db.delete(item); db.commit()
    return {"message": "Blood group deleted successfully"}


# Address Type Routes
@router.post("/address-type", status_code=status.HTTP_201_CREATED, response_model=AddressTypeOut)
def create_address_type(payload: AddressTypeIn, db: Session = Depends(get_db)):
    """Create a new address type"""
    
    existing = db.query(AddressType).filter(AddressType.type == payload.type).first()
    if existing:
        raise HTTPException(status_code=400, detail="Address type already exists")
    
    item = AddressType(
        type=payload.type,
        created_by="system",
        updated_by="system"
    )
    
    db.add(item)
    db.commit()
    db.refresh(item)
    
    return AddressTypeOut(
        id=item.id,
        type=item.type,
        created_by=item.created_by,
        created_at=str(item.created_at),
        updated_by=item.updated_by,
        updated_at=str(item.updated_at)
    )


@router.get("/address-type", response_model=list[AddressTypeOut])
def get_address_type(db: Session = Depends(get_db)):
    """Get all address type values"""
    
    items = db.query(AddressType).order_by(AddressType.type.asc()).all()
    
    result = []
    for item in items:
        result.append(AddressTypeOut(
            id=item.id,
            type=item.type,
            created_by=item.created_by,
            created_at=str(item.created_at),
            updated_by=item.updated_by,
            updated_at=str(item.updated_at)
        ))
    
    return result


@router.put("/address-type/{item_id}", response_model=AddressTypeOut)
def update_address_type(item_id: int, payload: AddressTypeIn, db: Session = Depends(get_db)):
    item = db.query(AddressType).filter(AddressType.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Address type not found")
    existing = db.query(AddressType).filter(AddressType.type == payload.type, AddressType.id != item_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Address type already exists")
    item.type = payload.type
    item.updated_by = "system"
    db.commit(); db.refresh(item)
    return AddressTypeOut(id=item.id, type=item.type, created_by=item.created_by, created_at=str(item.created_at), updated_by=item.updated_by, updated_at=str(item.updated_at))


@router.delete("/address-type/{item_id}")
def delete_address_type(item_id: int, db: Session = Depends(get_db)):
    item = db.query(AddressType).filter(AddressType.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Address type not found")
    db.delete(item); db.commit()
    return {"message": "Address type deleted successfully"}


# Relation Type Routes
@router.post("/relation-type", status_code=status.HTTP_201_CREATED, response_model=RelationTypeOut)
def create_relation_type(payload: RelationTypeIn, db: Session = Depends(get_db)):
    """Create a new relation type"""
    
    existing = db.query(RelationType).filter(RelationType.type == payload.type).first()
    if existing:
        raise HTTPException(status_code=400, detail="Relation type already exists")
    
    item = RelationType(
        type=payload.type,
        created_by="system",
        updated_by="system"
    )
    
    db.add(item)
    db.commit()
    db.refresh(item)
    
    return RelationTypeOut(
        id=item.id,
        type=item.type,
        created_by=item.created_by,
        created_at=str(item.created_at),
        updated_by=item.updated_by,
        updated_at=str(item.updated_at)
    )


@router.get("/relation-type", response_model=list[RelationTypeOut])
def get_relation_type(db: Session = Depends(get_db)):
    """Get all relation type values"""
    
    items = db.query(RelationType).order_by(RelationType.type.asc()).all()
    
    result = []
    for item in items:
        result.append(RelationTypeOut(
            id=item.id,
            type=item.type,
            created_by=item.created_by,
            created_at=str(item.created_at),
            updated_by=item.updated_by,
            updated_at=str(item.updated_at)
        ))
    
    return result


@router.put("/relation-type/{item_id}", response_model=RelationTypeOut)
def update_relation_type(item_id: int, payload: RelationTypeIn, db: Session = Depends(get_db)):
    item = db.query(RelationType).filter(RelationType.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Relation type not found")
    existing = db.query(RelationType).filter(RelationType.type == payload.type, RelationType.id != item_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Relation type already exists")
    item.type = payload.type
    item.updated_by = "system"
    db.commit(); db.refresh(item)
    return RelationTypeOut(id=item.id, type=item.type, created_by=item.created_by, created_at=str(item.created_at), updated_by=item.updated_by, updated_at=str(item.updated_at))


@router.delete("/relation-type/{item_id}")
def delete_relation_type(item_id: int, db: Session = Depends(get_db)):
    item = db.query(RelationType).filter(RelationType.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Relation type not found")
    db.delete(item); db.commit()
    return {"message": "Relation type deleted successfully"}


# Type of Degree Routes
@router.post("/type-of-degree", status_code=status.HTTP_201_CREATED, response_model=TypeOfDegreeOut)
def create_type_of_degree(payload: TypeOfDegreeIn, db: Session = Depends(get_db)):
    """Create a new type of degree"""
    
    existing = db.query(TypeOfDegree).filter(TypeOfDegree.degree == payload.degree).first()
    if existing:
        raise HTTPException(status_code=400, detail="Degree type already exists")
    
    item = TypeOfDegree(
        degree=payload.degree,
        created_by="system",
        updated_by="system"
    )
    
    db.add(item)
    db.commit()
    db.refresh(item)
    
    return TypeOfDegreeOut(
        id=item.id,
        degree=item.degree,
        created_by=item.created_by,
        created_at=str(item.created_at),
        updated_by=item.updated_by,
        updated_at=str(item.updated_at)
    )


@router.get("/type-of-degree", response_model=list[TypeOfDegreeOut])
def get_type_of_degree(db: Session = Depends(get_db)):
    """Get all type of degree values"""
    
    items = db.query(TypeOfDegree).order_by(TypeOfDegree.degree.asc()).all()
    
    result = []
    for item in items:
        result.append(TypeOfDegreeOut(
            id=item.id,
            degree=item.degree,
            created_by=item.created_by,
            created_at=str(item.created_at),
            updated_by=item.updated_by,
            updated_at=str(item.updated_at)
        ))
    
    return result


@router.put("/type-of-degree/{item_id}", response_model=TypeOfDegreeOut)
def update_type_of_degree(item_id: int, payload: TypeOfDegreeIn, db: Session = Depends(get_db)):
    item = db.query(TypeOfDegree).filter(TypeOfDegree.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Degree type not found")
    existing = db.query(TypeOfDegree).filter(TypeOfDegree.degree == payload.degree, TypeOfDegree.id != item_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Degree type already exists")
    item.degree = payload.degree
    item.updated_by = "system"
    db.commit(); db.refresh(item)
    return TypeOfDegreeOut(id=item.id, degree=item.degree, created_by=item.created_by, created_at=str(item.created_at), updated_by=item.updated_by, updated_at=str(item.updated_at))


@router.delete("/type-of-degree/{item_id}")
def delete_type_of_degree(item_id: int, db: Session = Depends(get_db)):
    item = db.query(TypeOfDegree).filter(TypeOfDegree.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Degree type not found")
    db.delete(item); db.commit()
    return {"message": "Degree type deleted successfully"}


# Job Type Routes
@router.post("/job-type", status_code=status.HTTP_201_CREATED, response_model=JobTypeOut)
def create_job_type(payload: JobTypeIn, db: Session = Depends(get_db)):
    """Create a new job type"""
    
    existing = db.query(JobType).filter(JobType.type == payload.type).first()
    if existing:
        raise HTTPException(status_code=400, detail="Job type already exists")
    
    item = JobType(
        type=payload.type,
        created_by="system",
        updated_by="system"
    )
    
    db.add(item)
    db.commit()
    db.refresh(item)
    
    return JobTypeOut(
        id=item.id,
        type=item.type,
        created_by=item.created_by,
        created_at=str(item.created_at),
        updated_by=item.updated_by,
        updated_at=str(item.updated_at)
    )


@router.get("/job-type", response_model=list[JobTypeOut])
def get_job_type(db: Session = Depends(get_db)):
    """Get all job type values"""
    
    items = db.query(JobType).order_by(JobType.type.asc()).all()
    
    result = []
    for item in items:
        result.append(JobTypeOut(
            id=item.id,
            type=item.type,
            created_by=item.created_by,
            created_at=str(item.created_at),
            updated_by=item.updated_by,
            updated_at=str(item.updated_at)
        ))
    
    return result


@router.put("/job-type/{item_id}", response_model=JobTypeOut)
def update_job_type(item_id: int, payload: JobTypeIn, db: Session = Depends(get_db)):
    item = db.query(JobType).filter(JobType.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Job type not found")
    existing = db.query(JobType).filter(JobType.type == payload.type, JobType.id != item_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Job type already exists")
    item.type = payload.type
    item.updated_by = "system"
    db.commit(); db.refresh(item)
    return JobTypeOut(id=item.id, type=item.type, created_by=item.created_by, created_at=str(item.created_at), updated_by=item.updated_by, updated_at=str(item.updated_at))


@router.delete("/job-type/{item_id}")
def delete_job_type(item_id: int, db: Session = Depends(get_db)):
    item = db.query(JobType).filter(JobType.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Job type not found")
    db.delete(item); db.commit()
    return {"message": "Job type deleted successfully"}


# Asset Status Routes
@router.post("/asset-status", status_code=status.HTTP_201_CREATED, response_model=AssetStatusOut)
def create_asset_status(payload: AssetStatusIn, db: Session = Depends(get_db)):
    """Create a new asset status"""
    
    existing = db.query(AssetStatus).filter(AssetStatus.status == payload.status).first()
    if existing:
        raise HTTPException(status_code=400, detail="Asset status already exists")
    
    item = AssetStatus(
        status=payload.status,
        created_by="system",
        updated_by="system"
    )
    
    db.add(item)
    db.commit()
    db.refresh(item)
    
    return AssetStatusOut(
        id=item.id,
        status=item.status,
        created_by=item.created_by,
        created_at=str(item.created_at),
        updated_by=item.updated_by,
        updated_at=str(item.updated_at)
    )


@router.get("/asset-status", response_model=list[AssetStatusOut])
def get_asset_status(db: Session = Depends(get_db)):
    """Get all asset status values"""
    
    items = db.query(AssetStatus).order_by(AssetStatus.status.asc()).all()
    
    result = []
    for item in items:
        result.append(AssetStatusOut(
            id=item.id,
            status=item.status,
            created_by=item.created_by,
            created_at=str(item.created_at),
            updated_by=item.updated_by,
            updated_at=str(item.updated_at)
        ))
    
    return result


@router.put("/asset-status/{item_id}", response_model=AssetStatusOut)
def update_asset_status(item_id: int, payload: AssetStatusIn, db: Session = Depends(get_db)):
    item = db.query(AssetStatus).filter(AssetStatus.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Asset status not found")
    existing = db.query(AssetStatus).filter(AssetStatus.status == payload.status, AssetStatus.id != item_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Asset status already exists")
    item.status = payload.status
    item.updated_by = "system"
    db.commit(); db.refresh(item)
    return AssetStatusOut(id=item.id, status=item.status, created_by=item.created_by, created_at=str(item.created_at), updated_by=item.updated_by, updated_at=str(item.updated_at))


@router.delete("/asset-status/{item_id}")
def delete_asset_status(item_id: int, db: Session = Depends(get_db)):
    item = db.query(AssetStatus).filter(AssetStatus.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Asset status not found")
    db.delete(item); db.commit()
    return {"message": "Asset status deleted successfully"}


# Seed default values
@router.post("/seed-defaults")
def seed_default_values(db: Session = Depends(get_db)):
    """Seed default dropdown values"""
    
    # Seed Excluded from Payroll
    excluded_values = ["Yes", "No"]
    for value in excluded_values:
        if not db.query(ExcludedFromPayroll).filter(ExcludedFromPayroll.value == value).first():
            db.add(ExcludedFromPayroll(value=value, created_by="system", updated_by="system"))
    
    # Seed Marital Status
    marital_statuses = ["Single", "Married", "Divorced", "Widowed", "Other"]
    for status in marital_statuses:
        if not db.query(MaritalStatus).filter(MaritalStatus.status == status).first():
            db.add(MaritalStatus(status=status, created_by="system", updated_by="system"))
    
    # Seed Blood Groups
    blood_groups = ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"]
    for group in blood_groups:
        if not db.query(BloodGroup).filter(BloodGroup.group == group).first():
            db.add(BloodGroup(group=group, created_by="system", updated_by="system"))
    
    # Seed Address Types
    address_types = ["Permanent", "Temporary", "Office"]
    for addr_type in address_types:
        if not db.query(AddressType).filter(AddressType.type == addr_type).first():
            db.add(AddressType(type=addr_type, created_by="system", updated_by="system"))
    
    # Seed Relation Types
    relation_types = ["Spouse", "Father", "Mother", "Son", "Daughter", "Brother", "Sister", "Other"]
    for rel_type in relation_types:
        if not db.query(RelationType).filter(RelationType.type == rel_type).first():
            db.add(RelationType(type=rel_type, created_by="system", updated_by="system"))
    
    # Seed Type of Degrees
    degree_types = ["SSC", "Inter", "Diploma", "Grad", "PG", "PhD", "Other"]
    for degree in degree_types:
        if not db.query(TypeOfDegree).filter(TypeOfDegree.degree == degree).first():
            db.add(TypeOfDegree(degree=degree, created_by="system", updated_by="system"))
    
    # Seed Job Types
    job_types = ["Intern", "Consultant", "Contract", "Permanent", "Part-time", "Freelance"]
    for job_type in job_types:
        if not db.query(JobType).filter(JobType.type == job_type).first():
            db.add(JobType(type=job_type, created_by="system", updated_by="system"))
    
    # Seed Asset Status
    asset_statuses = ["Active", "Inactive", "In Use", "In Stock", "Lost", "Damaged", "Returned", "Under Repair", "Open"]
    for status in asset_statuses:
        if not db.query(AssetStatus).filter(AssetStatus.status == status).first():
            db.add(AssetStatus(status=status, created_by="system", updated_by="system"))
    
    # Seed Titles
    titles = ["Mr.", "Mrs.", "Ms.", "Miss"]
    for t in titles:
        if not db.query(Title).filter(Title.title == t).first():
            db.add(Title(title=t, created_by="system", updated_by="system"))

    # Seed Asset Types
    asset_types = ["Laptop", "ID Card", "Head Phone", "Mobile", "Monitor"]
    for at in asset_types:
        if not db.query(AssetType).filter(AssetType.type == at).first():
            db.add(AssetType(type=at, created_by="system", updated_by="system"))
    
    db.commit()
    
    return {"message": "Default dropdown values seeded successfully"}
