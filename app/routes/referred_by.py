from fastapi import APIRouter, Depends, HTTPException, status, Body, Path
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.database import get_db
from app.models import ReferredByDB
from app.schemas import ReferredByCreate, ReferredByUpdate, ReferredByResponse

router = APIRouter(prefix="/referred-by", tags=["referred_by"])

@router.get("/", response_model=List[ReferredByResponse])
def list_referred_by(db: Session = Depends(get_db)):
    return db.query(ReferredByDB).order_by(ReferredByDB.referred_by.asc()).all()

@router.post("/", response_model=ReferredByResponse, status_code=status.HTTP_201_CREATED)
def create_referred_by(payload: ReferredByCreate, db: Session = Depends(get_db)):
    # Check for duplicate
    if db.query(ReferredByDB).filter(ReferredByDB.referred_by == payload.referred_by).first():
        raise HTTPException(status_code=400, detail="Referred by value already exists.")
    obj = ReferredByDB(
        referred_by=payload.referred_by,
        created_by=payload.created_by,
        updated_by=payload.created_by
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.put("/{referred_by_id}", response_model=ReferredByResponse)
def update_referred_by(
    referred_by_id: int = Path(..., gt=0),
    payload: ReferredByUpdate = Body(...),
    db: Session = Depends(get_db)
):
    obj = db.query(ReferredByDB).filter(ReferredByDB.id == referred_by_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Referred by entry not found.")
    if payload.referred_by:
        # Check for duplicate name
        if db.query(ReferredByDB).filter(ReferredByDB.referred_by == payload.referred_by, ReferredByDB.id != referred_by_id).first():
            raise HTTPException(status_code=400, detail="Referred by value already exists.")
        obj.referred_by = payload.referred_by
    obj.updated_by = payload.updated_by
    obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj

@router.delete("/{referred_by_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_referred_by(referred_by_id: int = Path(..., gt=0), db: Session = Depends(get_db)):
    obj = db.query(ReferredByDB).filter(ReferredByDB.id == referred_by_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Referred by entry not found.")
    db.delete(obj)
    db.commit()
    return None 