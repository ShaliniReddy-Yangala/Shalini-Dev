from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from .assert_model import AssetCategory
from .assert_schema import AssetCategoryCreate, AssetCategoryOut


router_categories = APIRouter(prefix="/categories", tags=["Assets - Categories"])


@router_categories.post("/", response_model=AssetCategoryOut, status_code=status.HTTP_201_CREATED)
@router_categories.post("", response_model=AssetCategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(payload: AssetCategoryCreate, db: Session = Depends(get_db)):
    existing = db.query(AssetCategory).filter(AssetCategory.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists")
    item = AssetCategory(name=payload.name)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router_categories.get("/", response_model=List[AssetCategoryOut])
@router_categories.get("", response_model=List[AssetCategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.query(AssetCategory).order_by(AssetCategory.name.asc()).all()


@router_categories.put("/{category_id}", response_model=AssetCategoryOut)
def update_category(category_id: int, payload: AssetCategoryCreate, db: Session = Depends(get_db)):
    item = db.query(AssetCategory).filter(AssetCategory.id == category_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Category not found")
    # enforce unique name
    if payload.name != item.name:
        exists = db.query(AssetCategory).filter(AssetCategory.name == payload.name).first()
        if exists:
            raise HTTPException(status_code=400, detail="Category already exists")
    item.name = payload.name
    db.commit(); db.refresh(item)
    return item


@router_categories.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    item = db.query(AssetCategory).filter(AssetCategory.id == category_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Category not found")
    db.delete(item); db.commit()
    return None
