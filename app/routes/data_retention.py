from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import ProgrammingError, OperationalError
from typing import List
from ..database import get_db
from ..models import DataRetentionSettings
from ..schemas import (
    DataRetentionSettingsCreate,
    DataRetentionSettingsUpdate,
    DataRetentionSettingsResponse
)
from datetime import datetime

router = APIRouter(prefix="/data-retention", tags=["Data Retention"])

@router.post("/", response_model=DataRetentionSettingsResponse)
def create_retention_settings(
    settings: DataRetentionSettingsCreate,
    db: Session = Depends(get_db)
):
    """Create new data retention settings"""
    # Check if settings already exist
    try:
        existing_settings = db.query(DataRetentionSettings).first()
    except (ProgrammingError, OperationalError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table 'data_retention_settings' not found. Create it using the provided SQL DDL."
        )
    if existing_settings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Data retention settings already exist. Use PUT to update."
        )
    
    db_settings = DataRetentionSettings(
        notification_retention_days=settings.notification_retention_days,
        logs_retention_days=settings.logs_retention_days,
        created_by=settings.created_by or "system"
    )
    
    db.add(db_settings)
    db.commit()
    db.refresh(db_settings)
    
    return db_settings

@router.get("/", response_model=DataRetentionSettingsResponse)
def get_retention_settings(db: Session = Depends(get_db)):
    """Get current data retention settings"""
    try:
        settings = db.query(DataRetentionSettings).first()
    except (ProgrammingError, OperationalError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table 'data_retention_settings' not found. Create it using the provided SQL DDL."
        )
    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data retention settings not found"
        )
    return settings

@router.put("/", response_model=DataRetentionSettingsResponse)
def update_retention_settings(
    settings: DataRetentionSettingsUpdate,
    db: Session = Depends(get_db)
):
    """Update existing data retention settings"""
    try:
        db_settings = db.query(DataRetentionSettings).first()
    except (ProgrammingError, OperationalError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table 'data_retention_settings' not found. Create it using the provided SQL DDL."
        )
    if not db_settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data retention settings not found. Create them first."
        )
    
    if settings.notification_retention_days is not None:
        db_settings.notification_retention_days = settings.notification_retention_days
    
    if settings.logs_retention_days is not None:
        db_settings.logs_retention_days = settings.logs_retention_days
    
    db_settings.updated_by = settings.updated_by or "system"
    db_settings.updated_on = datetime.utcnow()
    
    db.commit()
    db.refresh(db_settings)
    
    return db_settings

@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
def delete_retention_settings(db: Session = Depends(get_db)):
    """Delete data retention settings"""
    try:
        settings = db.query(DataRetentionSettings).first()
    except (ProgrammingError, OperationalError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table 'data_retention_settings' not found. Create it using the provided SQL DDL."
        )
    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data retention settings not found"
        )
    
    db.delete(settings)
    db.commit()
    
    return None
