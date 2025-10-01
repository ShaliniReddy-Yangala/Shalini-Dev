import logging
from fastapi import APIRouter, Depends, HTTPException, Response, Body, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime, timezone

from .. import models, schemas
from ..database import get_db

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
    responses={404: {"description": "Not found"}},
)


@router.post("/", response_model=schemas.NotificationResponse, status_code=status.HTTP_201_CREATED)
def create_notification(notification: schemas.NotificationCreate, db: Session = Depends(get_db)):
    """
    Create a new notification
    """
    try:
        # Check if job_id is provided and if it exists in job_requisitions table
        if notification.job_id:
            job = db.query(models.Job).filter(models.Job.job_id == notification.job_id).first()
            if not job:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail=f"Job ID {notification.job_id} does not exist in job_requisitions table"
                )
        
        # Check if candidate_id is provided and if it exists in candidates table
        if notification.candidate_id:
            candidate = db.query(models.Candidate).filter(models.Candidate.candidate_id == notification.candidate_id).first()
            if not candidate:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail=f"Candidate ID {notification.candidate_id} does not exist in candidates table"
                )
                
        db_notification = models.Notification(
            user_id=notification.user_id,
            notification_type=notification.notification_type,
            title=notification.title,
            message=notification.message,
            link=notification.link,
            job_id=notification.job_id,
            candidate_id=notification.candidate_id,
            is_read=False,
        )
        db.add(db_notification)
        db.commit()
        db.refresh(db_notification)
        return db_notification
        
    except Exception as e:
        logger.error(f"Error creating notification: {str(e)}")
        db.rollback()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}"
        )


@router.get("/user/{user_id}", response_model=schemas.NotificationList)
def get_user_notifications(
    user_id: str, 
    limit: int = 20, 
    skip: int = 0, 
    include_read: bool = False,
    db: Session = Depends(get_db)
):
    """
    Get notifications for a specific user
    """
    query = db.query(models.Notification).filter(models.Notification.user_id == user_id)
    
    if not include_read:
        query = query.filter(models.Notification.is_read == False)
    
    # Get total unread count
    unread_count = db.query(models.Notification).filter(
        models.Notification.user_id == user_id,
        models.Notification.is_read == False
    ).count()
    
    # Get notifications with pagination
    notifications = query.order_by(desc(models.Notification.created_on)).offset(skip).limit(limit).all()
    
    return {
        "items": notifications,
        "unread_count": unread_count
    }

@router.put("/{notification_id}/mark-read", response_model=schemas.NotificationResponse)
def mark_notification_read(notification_id: int, db: Session = Depends(get_db)):
    """
    Mark a notification as read
    """
    notification = db.query(models.Notification).filter(models.Notification.id == notification_id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification

@router.put("/user/{user_id}/mark-all-read", status_code=status.HTTP_200_OK)
def mark_all_notifications_read(user_id: str, db: Session = Depends(get_db)):
    """
    Mark all notifications for a user as read
    """
    db.query(models.Notification).filter(
        models.Notification.user_id == user_id,
        models.Notification.is_read == False
    ).update({"is_read": True})
    
    db.commit()
    return {"message": "All notifications marked as read"}

@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(notification_id: int, db: Session = Depends(get_db)):
    """
    Delete a notification
    """
    notification = db.query(models.Notification).filter(models.Notification.id == notification_id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    db.delete(notification)
    db.commit()
    return {"message": "Notification deleted successfully"}

@router.get("/pending-reviews", response_model=List[schemas.NotificationResponse])
def get_pending_review_notifications(user_id: str, db: Session = Depends(get_db)):
    """
    Get notifications for applications that need review
    """
    notifications = db.query(models.Notification).filter(
        models.Notification.user_id == user_id,
        models.Notification.notification_type == "APPLICATION_REVIEW", 
        models.Notification.is_read == False
    ).order_by(desc(models.Notification.created_on)).all()
    
    return notifications

@router.get("/application-counts", response_model=List[schemas.NotificationResponse])
def get_application_count_notifications(user_id: str, db: Session = Depends(get_db)):
    """
    Get notifications about application counts
    """
    notifications = db.query(models.Notification).filter(
        models.Notification.user_id == user_id,
        models.Notification.notification_type == "APPLICATION_COUNT",
        models.Notification.is_read == False
    ).order_by(desc(models.Notification.created_on)).all()
    
    return notifications

@router.get("/job-approvals", response_model=List[schemas.NotificationResponse])
def get_job_approval_notifications(user_id: str, db: Session = Depends(get_db)):
    """
    Get notifications about job approvals
    """
    notifications = db.query(models.Notification).filter(
        models.Notification.user_id == user_id,
        models.Notification.notification_type == "JOB_APPROVAL",       
        models.Notification.is_read == False
    ).order_by(desc(models.Notification.created_on)).all()
    
    return notifications

@router.get("/login-alerts", response_model=List[schemas.NotificationResponse])
def get_login_alert_notifications(user_id: str, db: Session = Depends(get_db)):
    """
    Get notifications about new device logins
    """
    notifications = db.query(models.Notification).filter(
        models.Notification.user_id == user_id,
        models.Notification.notification_type == "LOGIN_ALERT",
        models.Notification.is_read == False
    ).order_by(desc(models.Notification.created_on)).all()
    
    return notifications

@router.post("/login-alert", status_code=status.HTTP_201_CREATED)
def create_login_notification(
    user_id: str = Body(...),
    device_info: str = Body(...),
    db: Session = Depends(get_db)
):
    """
    Create a new login notification
    """
    notification = models.Notification(
        user_id=user_id,
        notification_type=models.NotificationType.LOGIN_ALERT,
        title="You logged into a new device",
        message=f"A new login was detected from {device_info}",
        is_read=False
    )
    
    db.add(notification)
    db.commit()
    
    return {"message": "Login notification created successfully"}


# New endpoints for interview scheduling notifications
@router.get("/interview-schedules", response_model=List[schemas.NotificationResponse])
def get_interview_schedule_notifications(user_id: str, db: Session = Depends(get_db)):
    """
    Get notifications about scheduled interviews (L1, L2, HR, discussion rounds)
    """
    notifications = db.query(models.Notification).filter(
        models.Notification.user_id == user_id,
        models.Notification.notification_type == "INTERVIEW_SCHEDULE",
        models.Notification.is_read == False
    ).order_by(desc(models.Notification.created_on)).all()
    
    return notifications

@router.post("/interview-schedule", status_code=status.HTTP_201_CREATED)
def create_interview_schedule_notification(
    user_id: str = Body(...),
    interview_type: str = Body(...),  # "L1", "L2", "HR", "DISCUSSION"
    candidate_id: str = Body(...),
    job_id: Optional[str] = Body(None),
    interview_date: datetime = Body(...),
    interview_details: str = Body(...),
    db: Session = Depends(get_db)
):
    """
    Create a new interview schedule notification
    
    Parameters:
    - user_id: ID of the user to notify
    - interview_type: Type of interview (L1, L2, HR, DISCUSSION)
    - candidate_id: ID of the candidate being interviewed
    - job_id: Optional ID of the job position
    - interview_date: Date and time of the scheduled interview
    - interview_details: Additional details about the interview
    """
    # Format the date in a user-friendly way
    formatted_date = interview_date.strftime("%A, %B %d, %Y at %I:%M %p")
    
    # Create appropriate title and message based on interview type
    title = f"{interview_type} Interview Scheduled"
    message = f"An {interview_type} interview has been scheduled for {formatted_date}. {interview_details}"
    
    # Create a link to the interview detail page
    link = f"/interviews/{candidate_id}"
    
    notification = models.Notification(
        user_id=user_id,
        notification_type="INTERVIEW_SCHEDULE",
        title=title,
        message=message,
        link=link,
        candidate_id=candidate_id,
        job_id=job_id,
        is_read=False
    )
    
    db.add(notification)
    db.commit()
    db.refresh(notification)
    
    return notification