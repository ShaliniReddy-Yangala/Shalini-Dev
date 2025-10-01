from fastapi import APIRouter, Depends, HTTPException
from .. import models, schemas
from sqlalchemy.orm import Session
from ..database import get_db
from typing import List
import re

router = APIRouter(prefix="/interview2team", tags=["Interview2Team"])

@router.post("/create_interview2_team", response_model=schemas.TAteamResponse)
def create_interview2_team(ta_team: schemas.TAteamCreate, db: Session = Depends(get_db)):
    try:
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

        # Check for duplicate weightage
        existing_team = db.query(models.SecondInterviewTeam).filter(
            models.SecondInterviewTeam.weightage == ta_team.weightage
        ).first()
        
        if existing_team:
            # Swap weightages
            existing_team.weightage = db.query(models.SecondInterviewTeam).count() + 1
            db.commit()

        # Create new team
        db_interview_team = models.SecondInterviewTeam(
            team_name=ta_team.team_name,
            team_members=ta_team.team_members,
            team_emails=ta_team.team_emails,
            department_id=ta_team.department_id,
            weightage=ta_team.weightage,
            created_by=ta_team.created_by  # Accept from frontend
        )
        db.add(db_interview_team)
        db.commit()
        db.refresh(db_interview_team)
        return db_interview_team

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating Interview 2 team: {str(e)}")

@router.get("/get_interview2_team", response_model=List[schemas.TAteamResponse])
def get_interview2_team(db: Session = Depends(get_db)):
    try:
        teams = db.query(models.SecondInterviewTeam).order_by(models.SecondInterviewTeam.weightage).all()
        return teams or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching Interview 2 teams: {str(e)}")

@router.get("/get_interview2_team/{team_id}", response_model=schemas.TAteamResponse)
def get_interview2_team_by_id(team_id: int, db: Session = Depends(get_db)):
    try:
        team = db.query(models.SecondInterviewTeam).filter(
            models.SecondInterviewTeam.id == team_id
        ).first()
        if not team:
            raise HTTPException(status_code=404, detail="Interview 2 Team not found")
        return team
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching Interview 2 team: {str(e)}")

@router.put("/update_interview2_team/{team_id}", response_model=schemas.TAteamResponse)
def update_interview2_team(team_id: int, ta_team_update: schemas.TAteamUpdate, db: Session = Depends(get_db)):
    try:
        db_team = db.query(models.SecondInterviewTeam).filter(
            models.SecondInterviewTeam.id == team_id
        ).first()
        if not db_team:
            raise HTTPException(status_code=404, detail="Interview 2 Team not found")

        if ta_team_update.team_emails:
            email_regex = r'^[^\s@]+@vaics-consulting\.com$'
            for email in ta_team_update.team_emails:
                if not email or not re.match(email_regex, email):
                    raise HTTPException(status_code=400, detail=f"Invalid email format or domain: {email}")

            if ta_team_update.team_members and len(ta_team_update.team_members) != len(ta_team_update.team_emails):
                raise HTTPException(status_code=400, detail="Number of team members and emails must match")

        if ta_team_update.weightage:
            existing_team = db.query(models.SecondInterviewTeam).filter(
                models.SecondInterviewTeam.weightage == ta_team_update.weightage,
                models.SecondInterviewTeam.id != team_id
            ).first()
            
            if existing_team:
                existing_team.weightage = db_team.weightage
                db.commit()

        update_data = ta_team_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_team, field, value if value is not None else [])
        # Remove hardcoded updated_by, accept from frontend if present
        if 'updated_by' in update_data:
            db_team.updated_by = update_data['updated_by']

        db.commit()
        db.refresh(db_team)
        return db_team
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating Interview 2 team: {str(e)}")


@router.delete("/delete_interview2_team/{team_id}")
def delete_interview2_team(team_id: int, db: Session = Depends(get_db)):
    try:
        db_team = db.query(models.SecondInterviewTeam).filter(
            models.SecondInterviewTeam.id == team_id
        ).first()
        if not db_team:
            raise HTTPException(status_code=404, detail="Interview 2 Team not found")

        db.delete(db_team)
        db.commit()
        
        # Reorder weightages
        teams = db.query(models.SecondInterviewTeam).order_by(models.SecondInterviewTeam.weightage).all()
        for i, team in enumerate(teams, 1):
            team.weightage = i
        db.commit()
        
        return {"detail": "Interview 2 Team deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting Interview 2 team: {str(e)}")