from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models import InternalLog
from app import schemas
from app.middleware.session_validator import get_current_user

router = APIRouter(prefix="/internal-logs", tags=["Internal Logs"])

@router.post("/", response_model=schemas.InternalLogResponse)
async def create_internal_log(
    log_data: schemas.InternalLogCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new internal log entry
    """
    # Validate action_type
    valid_action_types = ["Create", "Update", "Delete"]
    if log_data.action_type not in valid_action_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid action_type. Must be one of: {valid_action_types}"
        )
    
    # Create the log entry
    db_log = InternalLog(
        page=log_data.page,
        sub_page=log_data.sub_page,
        action=log_data.action,
        action_type=log_data.action_type,
        performed_by=log_data.performed_by,
        description=log_data.description,
        related_value=log_data.related_value,
        job_id=log_data.job_id,
        candidate_id=log_data.candidate_id
    )
    
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    
    return db_log

@router.get("/", response_model=schemas.PaginatedInternalLogResponse)
async def get_internal_logs(
    page: int = Query(1, ge=1),
    items_per_page: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    page_filter: Optional[str] = Query(None),
    action_type_filter: Optional[str] = Query(None),
    performed_by_filter: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    sort_key: str = Query("timestamp"),
    sort_order: str = Query("desc"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get paginated internal logs with filtering and sorting
    """
    # Build query
    query = db.query(InternalLog)
    
    # Apply filters
    filters = []
    
    if search:
        search_filter = or_(
            InternalLog.page.ilike(f"%{search}%"),
            InternalLog.sub_page.ilike(f"%{search}%"),
            InternalLog.action.ilike(f"%{search}%"),
            InternalLog.description.ilike(f"%{search}%"),
            InternalLog.performed_by.ilike(f"%{search}%")
        )
        filters.append(search_filter)
    
    if page_filter:
        filters.append(InternalLog.page == page_filter)
    
    if action_type_filter:
        filters.append(InternalLog.action_type == action_type_filter)
    
    if performed_by_filter:
        filters.append(InternalLog.performed_by == performed_by_filter)
    
    if start_date:
        filters.append(InternalLog.timestamp >= start_date)
    
    if end_date:
        # Add one day to include the end date
        end_date_plus_one = end_date + timedelta(days=1)
        filters.append(InternalLog.timestamp < end_date_plus_one)
    
    if filters:
        query = query.filter(and_(*filters))
    
    # Get total count
    total = query.count()
    
    # Apply sorting
    if sort_key == "timestamp":
        sort_column = InternalLog.timestamp
    elif sort_key == "page":
        sort_column = InternalLog.page
    elif sort_key == "action":
        sort_column = InternalLog.action
    elif sort_key == "action_type":
        sort_column = InternalLog.action_type
    elif sort_key == "performed_by":
        sort_column = InternalLog.performed_by
    else:
        sort_column = InternalLog.timestamp
    
    if sort_order.lower() == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))
    
    # Apply pagination
    offset = (page - 1) * items_per_page
    logs = query.offset(offset).limit(items_per_page).all()
    
    return schemas.PaginatedInternalLogResponse(
        total=total,
        page=page,
        items_per_page=items_per_page,
        items=logs
    )

@router.get("/{log_id}", response_model=schemas.InternalLogResponse)
async def get_internal_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific internal log entry by ID
    """
    log = db.query(InternalLog).filter(InternalLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Internal log not found")
    
    return log

@router.put("/{log_id}", response_model=schemas.InternalLogResponse)
async def update_internal_log(
    log_id: int,
    log_data: schemas.InternalLogUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update an internal log entry
    """
    log = db.query(InternalLog).filter(InternalLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Internal log not found")
    
    # Update fields if provided
    update_data = log_data.dict(exclude_unset=True)
    
    # Validate action_type if provided
    if "action_type" in update_data:
        valid_action_types = ["Create", "Update", "Delete"]
        if update_data["action_type"] not in valid_action_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid action_type. Must be one of: {valid_action_types}"
            )
    
    for field, value in update_data.items():
        setattr(log, field, value)
    
    log.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(log)
    
    return log

@router.delete("/{log_id}")
async def delete_internal_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete an internal log entry
    """
    log = db.query(InternalLog).filter(InternalLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Internal log not found")
    
    db.delete(log)
    db.commit()
    
    return {"message": "Internal log deleted successfully"}

@router.get("/stats/summary")
async def get_internal_logs_summary(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get summary statistics for internal logs
    """
    total_logs = db.query(InternalLog).count()
    
    # Get counts by action type
    action_type_counts = db.query(
        InternalLog.action_type,
        db.func.count(InternalLog.id).label('count')
    ).group_by(InternalLog.action_type).all()
    
    # Get counts by page
    page_counts = db.query(
        InternalLog.page,
        db.func.count(InternalLog.id).label('count')
    ).group_by(InternalLog.page).order_by(desc('count')).limit(10).all()
    
    # Get recent activity (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_logs = db.query(InternalLog).filter(
        InternalLog.timestamp >= seven_days_ago
    ).count()
    
    return {
        "total_logs": total_logs,
        "action_type_breakdown": [
            {"action_type": item.action_type, "count": item.count}
            for item in action_type_counts
        ],
        "top_pages": [
            {"page": item.page, "count": item.count}
            for item in page_counts
        ],
        "recent_activity_7_days": recent_logs
    }