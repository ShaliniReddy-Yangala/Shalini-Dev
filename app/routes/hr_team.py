from fastapi import APIRouter, Depends, HTTPException
from .. import models, schemas
from sqlalchemy.orm import Session
from ..database import get_db
from typing import List
import re
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hrteam", tags=["HRTeam"])

@router.post("/create_hr_team", response_model=schemas.HRTeamResponse)
def create_hr_team(hr_team: schemas.HRTeamCreate, db: Session = Depends(get_db)):
    try:
        # Log the incoming request body
        logger.info(f"Incoming request body: {hr_team.dict()}")

        # Validate inputs
        if not hr_team.team_members:
            raise HTTPException(status_code=400, detail="Team members cannot be empty")

        if len(hr_team.team_members) != len(hr_team.team_emails):
            raise HTTPException(status_code=400, detail="Number of team members and emails must match")

        # Validate email formats and domain
        email_regex = r'^[^\s@]+@vaics-consulting\.com$'
        for email in hr_team.team_emails:
            if not email or not re.match(email_regex, email):
                raise HTTPException(status_code=400, detail=f"Invalid email format or domain: {email}")

        # Create new HR team group
        db_hr_team = models.HRTeam(
            team_name=hr_team.team_name,
            team_members=hr_team.team_members,
            team_emails=hr_team.team_emails,
            created_by=hr_team.created_by,
            created_at=hr_team.created_at
            # updated_by and updated_at are not set to ensure they remain None
        )
        db.add(db_hr_team)
        db.commit()
        db.refresh(db_hr_team)
        return db_hr_team

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating HR team: {str(e)}")

@router.get("/get_hr_team", response_model=List[schemas.HRTeamResponse])
def get_hr_team(db: Session = Depends(get_db)):
    try:
        hr_teams = db.query(models.HRTeam).all()
        return hr_teams or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching HR teams: {str(e)}")

@router.get("/get_hr_team/{team_id}", response_model=schemas.HRTeamResponse)
def get_hr_team_by_id(team_id: int, db: Session = Depends(get_db)):
    try:
        hr_team = db.query(models.HRTeam).filter(
            models.HRTeam.id == team_id
        ).first()
        if not hr_team:
            raise HTTPException(status_code=404, detail="HR Team not found")
        return hr_team
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching HR team: {str(e)}")

@router.put("/update_hr_team/{team_id}", response_model=schemas.HRTeamResponse)
def update_hr_team(team_id: int, hr_team_update: schemas.HRTeamUpdate, db: Session = Depends(get_db)):
    try:
        db_hr_team = db.query(models.HRTeam).filter(
            models.HRTeam.id == team_id
        ).first()
        if not db_hr_team:
            raise HTTPException(status_code=404, detail="HR Team not found")

        if hr_team_update.team_emails:
            email_regex = r'^[^\s@]+@vaics-consulting\.com$'
            for email in hr_team_update.team_emails:
                if not email or not re.match(email_regex, email):
                    logger.warning(f"Validation failed for email: {email}")
                    raise HTTPException(status_code=400, detail=f"Invalid email format or domain: {email}")

            if hr_team_update.team_members and len(hr_team_update.team_members) != len(hr_team_update.team_emails):
                raise HTTPException(status_code=400, detail="Number of team members and emails must match")

        # Update with the provided data
        update_data = hr_team_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field in ['team_members', 'team_emails'] and value is None:
                continue  # Skip setting None for array fields
            setattr(db_hr_team, field, value)

        db.commit()
        db.refresh(db_hr_team)
        return db_hr_team
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating HR team: {str(e)}")

@router.delete("/delete_hr_team/{team_id}")
def delete_hr_team(team_id: int, db: Session = Depends(get_db)):
    try:
        db_hr_team = db.query(models.HRTeam).filter(
            models.HRTeam.id == team_id
        ).first()
        if not db_hr_team:
            raise HTTPException(status_code=404, detail="HR Team not found")

        db.delete(db_hr_team)
        db.commit()
        return {"detail": "HR Team deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting HR team: {str(e)}")