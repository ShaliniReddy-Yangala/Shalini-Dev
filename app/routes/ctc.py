from typing import Optional
from fastapi import APIRouter, Depends, Form, HTTPException, Query
from pydantic import EmailStr
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from datetime import datetime, date
import pytz
from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/ctc", tags=["CTC Breakup"])

@router.post("/save", response_model=schemas.CTCBreakupResponse)
def save_ctc_breakup(ctc_breakup: schemas.CTCBreakupCreate, db: Session = Depends(get_db), created_by: str = "taadmin"):
    # Check if CTC breakup already exists
    db_ctc_breakup = db.query(models.CTCBreakup).filter(
        models.CTCBreakup.candidate_id == ctc_breakup.candidate_id
    ).first()

    if db_ctc_breakup:
        # Update CTC breakup
        for key, value in ctc_breakup.dict(exclude={"candidate_id"}).items():
            setattr(db_ctc_breakup, key, value)
        db_ctc_breakup.updated_by = ctc_breakup.updated_by  
        db_ctc_breakup.updated_at = ctc_breakup.updated_at  
    else:
        # Create new CTC breakup
        db_ctc_breakup = models.CTCBreakup(**ctc_breakup.dict())
        db_ctc_breakup.created_by = ctc_breakup.updated_by 
        db_ctc_breakup.updated_by = ctc_breakup.updated_by
        db.add(db_ctc_breakup)

    # Update related fields in Candidate
    db_candidate = db.query(models.Candidate).filter(
        models.Candidate.candidate_id == ctc_breakup.candidate_id
    ).first()

    if db_candidate:
        db_candidate.offer_ctc = ctc_breakup.ctc
        db_candidate.current_designation = ctc_breakup.designation
        db_candidate.status_updated_on = date.today()
        db_candidate.updated_by = ctc_breakup.updated_by
        db_candidate.updated_at = ctc_breakup.updated_at

    db.commit()
    db.refresh(db_ctc_breakup)
    
    # Convert datetime to date for response
    response_data = {
        "id": db_ctc_breakup.id,
        "candidate_id": db_ctc_breakup.candidate_id,
        "candidate_name": db_ctc_breakup.candidate_name,
        "designation": db_ctc_breakup.designation,
        "ctc": db_ctc_breakup.ctc,
        "salary_components": db_ctc_breakup.salary_components,
        "ctc_email_status": db_ctc_breakup.ctc_email_status,
        "created_by": db_ctc_breakup.created_by,
        "updated_by": db_ctc_breakup.updated_by,
        "created_at": db_ctc_breakup.created_at.date() if db_ctc_breakup.created_at else None,
        "updated_at": db_ctc_breakup.updated_at.date() if db_ctc_breakup.updated_at else None,
    }
    
    return response_data

@router.get("/candidate/{candidate_id}", response_model=schemas.CTCBreakupResponse)
def get_ctc_breakup(candidate_id: str, db: Session = Depends(get_db)):
    db_ctc_breakup = db.query(models.CTCBreakup).filter(
        models.CTCBreakup.candidate_id == candidate_id
    ).first()

    if db_ctc_breakup:
        return db_ctc_breakup

    raise HTTPException(status_code=404, detail="CTC breakup not found for this candidate")

@router.post("/offer_status", response_model=schemas.CandidateOfferStatusResponse)
def create_or_update_offer_status(
    offer_status: schemas.CandidateOfferStatusCreate,
    db: Session = Depends(get_db)
):
    try:
        # Check if candidate exists
        candidate = db.query(models.Candidate).filter(
            models.Candidate.candidate_id == offer_status.candidate_id
        ).first()
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")

        # Check if status exists
        existing_status = db.query(models.CandidateOfferStatus).filter(
            models.CandidateOfferStatus.candidate_id == offer_status.candidate_id
        ).first()

        if existing_status:
            # Update existing status
            existing_status.offer_status = offer_status.offer_status
            existing_status.updated_at = datetime.now(pytz.UTC)
        else:
            # Create new status
            existing_status = models.CandidateOfferStatus(
                candidate_id=offer_status.candidate_id,
                offer_status=offer_status.offer_status
            )
            db.add(existing_status)

        # If the offer_status is "Accepted", update the candidate's final_status to "Offer Accepted"
        # and ensure current_status remains "ctcBreakup"
        if offer_status.offer_status == "Accepted":
            candidate.final_status = "Offer Accepted"
            candidate.current_status = "ctcBreakup"  # Ensure current_status remains "ctcBreakup"
            candidate.status_updated_on = date.today()

        db.commit()
        db.refresh(existing_status)
        return existing_status
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create/update offer status: {str(e)}")

@router.get("/offer_status/{candidate_id}", response_model=schemas.CandidateOfferStatusResponse)
def get_offer_status(
    candidate_id: str,
    db: Session = Depends(get_db)
):
    try:
        # Check if candidate exists
        candidate = db.query(models.Candidate).filter(
            models.Candidate.candidate_id == candidate_id
        ).first()
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")

        # Get offer status
        status = db.query(models.CandidateOfferStatus).filter(
            models.CandidateOfferStatus.candidate_id == candidate_id
        ).first()
        if not status:
            raise HTTPException(status_code=404, detail="Offer status not found for this candidate")
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve offer status: {str(e)}")

@router.put("/offer_status/{candidate_id}", response_model=schemas.CandidateOfferStatusResponse)
def update_offer_status(
    candidate_id: str,
    offer_status_update: schemas.CandidateOfferStatusUpdate,
    db: Session = Depends(get_db)
):
    try:
        # Check if candidate exists
        candidate = db.query(models.Candidate).filter(
            models.Candidate.candidate_id == candidate_id
        ).first()
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")

        # Check if offer status exists
        existing_status = db.query(models.CandidateOfferStatus).filter(
            models.CandidateOfferStatus.candidate_id == candidate_id
        ).first()

        if existing_status:
            # Update existing status
            existing_status.offer_status = offer_status_update.offer_status
            existing_status.updated_by = offer_status_update.updated_by  # From frontend
            existing_status.updated_at = offer_status_update.updated_at  # From frontend
        else:
            # Create new status
            existing_status = models.CandidateOfferStatus(
                candidate_id=candidate_id,
                offer_status=offer_status_update.offer_status,
                created_by=offer_status_update.updated_by,  
                updated_by=offer_status_update.updated_by,
                updated_at=offer_status_update.updated_at
            )
            db.add(existing_status)
            
        candidate.updated_by = offer_status_update.updated_by
        candidate.updated_at = offer_status_update.updated_at

        db.commit()
        db.refresh(existing_status)
        return existing_status
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update or create offer status: {str(e)}")
    



    
@router.post("/subscriptions", response_model=schemas.SubscriptionResponse)
async def create_subscription(subscription: schemas.SubscriptionCreate, db: Session = Depends(get_db)):
    """Create a new email subscription entry"""
    # Check if combination already exists
    existing = db.query(models.CandidateEmailSubscription).filter(
        models.CandidateEmailSubscription.email == subscription.email,
        models.CandidateEmailSubscription.job_id == subscription.job_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Subscription for this email and job ID already exists")
    
    db_subscription = models.CandidateEmailSubscription(**subscription.dict())
    db.add(db_subscription)
    db.commit()
    db.refresh(db_subscription)
    return db_subscription

@router.get("/subscriptions", response_model=schemas.PaginatedResponse)
async def get_subscriptions(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    email_filter: Optional[str] = Query(None, description="Filter by email"),
    job_id_filter: Optional[str] = Query(None, description="Filter by job ID"),
    subscription_status: Optional[bool] = Query(None, description="Filter by subscription status"),
    db: Session = Depends(get_db)
):
    """Get paginated list of subscriptions with optional filters"""
    query = db.query(models.CandidateEmailSubscription)
    
    # Apply filters
    if email_filter:
        query = query.filter(models.CandidateEmailSubscription.email.ilike(f"%{email_filter}%"))
    if job_id_filter:
        query = query.filter(models.CandidateEmailSubscription.job_id.ilike(f"%{job_id_filter}%"))
    if subscription_status is not None:
        query = query.filter(models.CandidateEmailSubscription.subscription_status == subscription_status)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * per_page
    items = query.offset(offset).limit(per_page).all()
    
    total_pages = (total + per_page - 1) // per_page
    
    return schemas.PaginatedResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )

@router.put("/subscriptions/{subscription_id}", response_model=schemas.SubscriptionResponse)
async def update_subscription_status(
    subscription_id: int,
    subscription_update: schemas.SubscriptionUpdate,
    db: Session = Depends(get_db)
):
    """Update subscription status for a specific candidate"""
    db_subscription = db.query(models.CandidateEmailSubscription).filter(
        models.CandidateEmailSubscription.id == subscription_id
    ).first()
    
    if not db_subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    db_subscription.subscription_status = subscription_update.subscription_status
    db.commit()
    db.refresh(db_subscription)
    return db_subscription

@router.get("/subscriptions/{subscription_id}", response_model=schemas.SubscriptionResponse)
async def get_subscription(subscription_id: int, db: Session = Depends(get_db)):
    """Get a specific subscription by ID"""
    db_subscription = db.query(models.CandidateEmailSubscription).filter(
        models.CandidateEmailSubscription.id == subscription_id
    ).first()
    
    if not db_subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    return db_subscription

@router.delete("/subscriptions/{subscription_id}")
async def delete_subscription(subscription_id: int, db: Session = Depends(get_db)):
    """Delete a subscription (for taadmin purposes)"""
    db_subscription = db.query(models.CandidateEmailSubscription).filter(
        models.CandidateEmailSubscription.id == subscription_id
    ).first()
    
    if not db_subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    db.delete(db_subscription)
    db.commit()
    return {"message": "Subscription deleted successfully"}

# Unsubscribe endpoints (for AWS compliance)
@router.get("/unsubscribe/{subscription_id}")
async def unsubscribe_get(subscription_id: int, db: Session = Depends(get_db)):
    """Handle unsubscribe via GET request (for email links)"""
    db_subscription = db.query(models.CandidateEmailSubscription).filter(
        models.CandidateEmailSubscription.id == subscription_id
    ).first()
    
    if not db_subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    db_subscription.subscription_status = False
    db.commit()
    
    return {"message": "Successfully unsubscribed", "email": db_subscription.email}

@router.post("/unsubscribe")
async def unsubscribe_post(
    email: EmailStr = Form(...),
    job_id: str = Form(...),
    db: Session = Depends(get_db)
):
    """Handle unsubscribe via POST request"""
    db_subscription = db.query(models.CandidateEmailSubscription).filter(
        models.CandidateEmailSubscription.email == email,
        models.CandidateEmailSubscription.job_id == job_id
    ).first()
    
    if not db_subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    db_subscription.subscription_status = False
    db.commit()
    
    return {"message": "Successfully unsubscribed"}

@router.post("/update_email_status/{candidate_id}")
def update_ctc_email_status(candidate_id: str, db: Session = Depends(get_db)):
    try:
        # Fetch the CTC breakup entry
        db_ctc_breakup = db.query(models.CTCBreakup).filter(
            models.CTCBreakup.candidate_id == candidate_id
        ).first()

        if not db_ctc_breakup:
            raise HTTPException(status_code=404, detail="CTC breakup not found for this candidate")

        # Update ctc_email_status to "sent"
        db_ctc_breakup.ctc_email_status = "sent"

        # Update the candidate's current_status to "ctcBreakup" and final_status to "Offered"
        db_candidate = db.query(models.Candidate).filter(
            models.Candidate.candidate_id == candidate_id
        ).first()

        if not db_candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")

        db_candidate.current_status = "ctcBreakup"
        db_candidate.final_status = "Offered"
        db_candidate.status_updated_on = date.today()

        db.commit()
        db.refresh(db_ctc_breakup)
        return {"status": "success", "message": "CTC email status and candidate status updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update CTC email status: {str(e)}")