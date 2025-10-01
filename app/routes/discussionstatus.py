from fastapi import APIRouter, Body, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from datetime import datetime
import logging

from app.models import DiscussionStatusDB
from app import schemas, database

router = APIRouter(prefix="/discussionstatus", tags=["discussionstatus"])
logger = logging.getLogger(__name__)

@router.get("/all", response_model=List[schemas.DiscussionStatusModel])
async def get_all_discussion_statuses(db: Session = Depends(database.get_db)):
    """Get all discussion statuses sorted by weight in ascending order"""
    discussion_statuses = db.query(DiscussionStatusDB).order_by(DiscussionStatusDB.weight.asc()).all()
    
    # Handle null weight values to avoid validation errors
    result = []
    for status_item in discussion_statuses:
        result.append({
            "id": status_item.id,
            "status": status_item.status,
            "weight": status_item.weight if status_item.weight is not None else 0,
            "hex_code": status_item.hex_code
        })
    
    return result

@router.get("/{status_id}", response_model=schemas.DiscussionStatusModel)
async def get_discussion_status(status_id: int = Path(..., gt=0), db: Session = Depends(database.get_db)):
    """Get a specific discussion status by ID"""
    discussion_status = db.query(DiscussionStatusDB).filter(DiscussionStatusDB.id == status_id).first()
    if not discussion_status:
        raise HTTPException(status_code=404, detail="Discussion status not found")
    return discussion_status

@router.post("/", response_model=schemas.DiscussionStatusModel, status_code=status.HTTP_201_CREATED)
async def create_discussion_status(status_model: schemas.DiscussionStatusModel = Body(...), db: Session = Depends(database.get_db)):
    """Create a new discussion status"""
    # Check for duplicate status
    existing_status = db.query(DiscussionStatusDB).filter(DiscussionStatusDB.status == status_model.status).first()
    if existing_status:
        raise HTTPException(status_code=400, detail="Discussion status already exists")

    # Check for duplicate weight
    existing_weight = db.query(DiscussionStatusDB).filter(DiscussionStatusDB.weight == status_model.weight).first()
    if existing_weight:
        raise HTTPException(status_code=400, detail="Weight already assigned to another discussion status")

    new_status = DiscussionStatusDB(
        status=status_model.status,
        weight=status_model.weight,
        hex_code=status_model.hex_code,
        created_by=status_model.created_by  # Accept from frontend
    )
    db.add(new_status)
    db.commit()
    db.refresh(new_status)
    return new_status

@router.put("/{status_id}", response_model=schemas.DiscussionStatusModel)
async def update_discussion_status(
    status_id: int = Path(..., gt=0),
    status_model: schemas.DiscussionStatusModel = Body(...),
    db: Session = Depends(database.get_db)
):
    """Update an existing discussion status with weight swapping"""
    try:
        discussion_status = db.query(DiscussionStatusDB).filter(DiscussionStatusDB.id == status_id).first()
        if not discussion_status:
            logger.warning(f"Discussion status ID {status_id} not found")
            raise HTTPException(status_code=404, detail="Discussion status not found")

        # Check for duplicate status (excluding current status)
        duplicate_status = db.query(DiscussionStatusDB).filter(
            DiscussionStatusDB.status == status_model.status,
            DiscussionStatusDB.id != status_id
        ).first()
        if duplicate_status:
            logger.warning(f"Discussion status {status_model.status} already exists")
            raise HTTPException(status_code=400, detail="Discussion status already exists")

        # Check if another status has the desired weight
        duplicate_weight = db.query(DiscussionStatusDB).filter(
            DiscussionStatusDB.weight == status_model.weight,
            DiscussionStatusDB.id != status_id
        ).first()

        # Start a transaction
        try:
            if duplicate_weight:
                # Swap weights: assign current status's weight to the other status
                duplicate_weight.weight = discussion_status.weight
                duplicate_weight.updated_at = datetime.utcnow()
                duplicate_weight.updated_by = status_model.updated_by  # Accept from frontend
                logger.info(f"Swapping weight: setting weight {discussion_status.weight} for discussion status ID {duplicate_weight.id}")

            # Update the current status
            discussion_status.status = status_model.status
            discussion_status.weight = status_model.weight
            discussion_status.hex_code = status_model.hex_code
            discussion_status.updated_at = datetime.utcnow()
            discussion_status.updated_by = status_model.updated_by  # Accept from frontend

            db.commit()
            db.refresh(discussion_status)
            if duplicate_weight:
                db.refresh(duplicate_weight)

            logger.info(f"Updated discussion status ID {status_id} with weight {discussion_status.weight}")
            if duplicate_weight:
                logger.info(f"Swapped weight with discussion status ID {duplicate_weight.id}, new weight {duplicate_weight.weight}")

            return discussion_status
        except Exception as e:
            db.rollback()
            logger.error(f"Error during weight swap for discussion status ID {status_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error updating discussion status: {str(e)}"
            )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating discussion status {status_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error updating discussion status: {str(e)}"
        )

@router.delete("/{status_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_discussion_status(status_id: int = Path(..., gt=0), db: Session = Depends(database.get_db)):
    """Delete a discussion status"""
    discussion_status = db.query(DiscussionStatusDB).filter(DiscussionStatusDB.id == status_id).first()
    if not discussion_status:
        raise HTTPException(status_code=404, detail="Discussion status not found")

    db.delete(discussion_status)
    db.commit()
    return None 