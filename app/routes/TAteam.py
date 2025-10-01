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

router = APIRouter(prefix="/TAteam", tags=["TAteam"])

@router.post("/create_ta_team", response_model=schemas.TATeamResponse)
def create_ta_team(ta_team: schemas.TATeamCreate, db: Session = Depends(get_db)):
    try:
        # Log the incoming request body
        logger.info(f"Incoming request body: {ta_team.dict()}")

        # Validate inputs
        if not ta_team.team_members:
            raise HTTPException(status_code=400, detail="Team members cannot be empty")

        if len(ta_team.team_members) != len(ta_team.team_emails):
            raise HTTPException(status_code=400, detail="Number of team members and emails must match")

        # Validate email formats and domain
        email_regex = r'^[^\s@]+@vaics-consulting\.com$'
        for email in ta_team.team_emails:
            if not email or not re.match(email_regex, email):
                raise HTTPException(status_code=400, detail=f"Invalid email format or domain: {email}")
        
        # Handle weight conflicts by shifting existing teams
        existing_team_with_weight = db.query(models.TalentAcquisitionTeam).filter(
            models.TalentAcquisitionTeam.weight == ta_team.weight
        ).first()
        
        if existing_team_with_weight:
            # Find the next available weight by getting the maximum weight and adding 1
            max_weight = db.query(models.TalentAcquisitionTeam).order_by(models.TalentAcquisitionTeam.weight.desc()).first()
            next_available_weight = (max_weight.weight + 1) if max_weight else 1
            
            # Move the existing team to the next available weight
            existing_team_with_weight.weight = next_available_weight
            db.commit()
            
            logger.info(f"Weight conflict resolved: Existing team {existing_team_with_weight.id} moved from weight {ta_team.weight} to weight {next_available_weight}")
        
        # Prepare data for creation
        # Use created_by from frontend if provided, else default
        created_by = getattr(ta_team, 'created_by', None) or "taadmin"
        # Use updated_at from frontend if provided, else None
        updated_at = getattr(ta_team, 'updated_at', None)
        # Create the team
        db_ta_team = models.TalentAcquisitionTeam(
            team_name=ta_team.team_name,
            team_members=ta_team.team_members,
            team_emails=ta_team.team_emails,
            weight=ta_team.weight,
            created_by=created_by,
            updated_at=updated_at
        )
        db.add(db_ta_team)
        db.commit()
        db.refresh(db_ta_team)
        return db_ta_team

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating TA team: {str(e)}")

@router.get("/get_ta_team", response_model=List[schemas.TATeamResponse])
def get_ta_team(db: Session = Depends(get_db)):
    try:
        ta_teams = db.query(models.TalentAcquisitionTeam).order_by(models.TalentAcquisitionTeam.weight).all()
        return ta_teams or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching TA teams: {str(e)}")

@router.get("/get_ta_team/{team_id}", response_model=schemas.TATeamResponse)
def get_ta_team_by_id(team_id: int, db: Session = Depends(get_db)):
    try:
        ta_team = db.query(models.TalentAcquisitionTeam).filter(
            models.TalentAcquisitionTeam.id == team_id
        ).first()
        if not ta_team:
            raise HTTPException(status_code=404, detail="TA Team not found")
        return ta_team
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching TA team: {str(e)}")

@router.put("/update_ta_team/{team_id}", response_model=schemas.TATeamResponse)
def update_ta_team(team_id: int, ta_team_update: schemas.TATeamUpdate, db: Session = Depends(get_db)):
    try:
        db_ta_team = db.query(models.TalentAcquisitionTeam).filter(
            models.TalentAcquisitionTeam.id == team_id
        ).first()
        if not db_ta_team:
            raise HTTPException(status_code=404, detail="TA Team not found")

        if ta_team_update.team_emails:
            email_regex = r'^[^\s@]+@vaics-consulting\.com$'
            for email in ta_team_update.team_emails:
                if not email or not re.match(email_regex, email):
                    raise HTTPException(status_code=400, detail=f"Invalid email format or domain: {email}")

            if ta_team_update.team_members and len(ta_team_update.team_members) != len(ta_team_update.team_emails):
                raise HTTPException(status_code=400, detail="Number of team members and emails must match")

        # Prepare update data
        update_data = ta_team_update.model_dump(exclude_unset=True)
        
        # Handle weight swapping if weight is being updated
        if ta_team_update.weight is not None:
            existing_team_with_weight = db.query(models.TalentAcquisitionTeam).filter(
                models.TalentAcquisitionTeam.weight == ta_team_update.weight,
                models.TalentAcquisitionTeam.id != team_id
            ).first()
            
            if existing_team_with_weight:
                # Get the current weight of the team being updated
                current_team_weight = db_ta_team.weight
                
                # Swap the weights
                existing_team_with_weight.weight = current_team_weight
                db_ta_team.weight = ta_team_update.weight
                
                # Log the swap for debugging
                logger.info(f"Weight swap performed: Team {team_id} now has weight {ta_team_update.weight}, Team {existing_team_with_weight.id} now has weight {current_team_weight}")
                
                # Commit the swap
                db.commit()
                db.refresh(db_ta_team)
                db.refresh(existing_team_with_weight)
                
                # Remove weight from update_data since we've already handled it
            if 'weight' in update_data:
                del update_data['weight']  # Prevents weight from being updated
        # Use updated_by from frontend if provided, else default
        if 'updated_by' not in update_data or not update_data['updated_by']:
            update_data['updated_by'] = "taadmin"

        # Apply updates
        for field, value in update_data.items():
            setattr(db_ta_team, field, value if value is not None else [])

            
        db.commit()
        db.refresh(db_ta_team)
        return db_ta_team
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating TA team: {str(e)}")

@router.delete("/delete_ta_team/{team_id}")
def delete_ta_team(team_id: int, db: Session = Depends(get_db)):
    try:
        db_ta_team = db.query(models.TalentAcquisitionTeam).filter(
            models.TalentAcquisitionTeam.id == team_id
        ).first()
        if not db_ta_team:
            raise HTTPException(status_code=404, detail="TA Team not found")

        db.delete(db_ta_team)
        db.commit()
        return {"detail": "TA Team deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting TA team: {str(e)}")