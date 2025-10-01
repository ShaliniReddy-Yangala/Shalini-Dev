from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.Employee_Master_Report.emp_models.employee_master import EmployeeMaster, FamilyMember
from app.Employee_Master_Report.emp_schema.employee_entry_schemas import (
    FamilyMemberIn,
    FamilyMemberOut
)
from datetime import datetime

router = APIRouter(prefix="/employee-entry", tags=["Employee Entry - Family Details"])


def convert_dd_mm_yyyy_to_date(date_str):
    """Convert DD-MM-YYYY string to date object"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%d-%m-%Y").date()
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid date format. Use DD-MM-YYYY format. Received: {date_str}")


def format_date_to_dd_mm_yyyy(date_obj):
    """Convert date object to DD-MM-YYYY string"""
    if not date_obj:
        return None
    return date_obj.strftime("%d-%m-%Y")


@router.post("/family-member", status_code=status.HTTP_201_CREATED, response_model=FamilyMemberOut)
def create_family_member(payload: FamilyMemberIn, db: Session = Depends(get_db)):
    """Create a new family member for an employee"""
    
    # Check if employee exists
    employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == payload.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Create family member
    family_member = FamilyMember(
        employee_id=payload.employee_id,
        relation_type=payload.relation_type,
        name=payload.name,
        dob=convert_dd_mm_yyyy_to_date(payload.dob),
        aadhar_number=payload.aadhar_number,
        dependant=payload.dependant,
        created_by="system",
        updated_by="system"
    )
    
    db.add(family_member)
    db.commit()
    db.refresh(family_member)
    
    return FamilyMemberOut(
        family_id=family_member.family_id,
        employee_id=family_member.employee_id,
        relation_type=family_member.relation_type,
        name=family_member.name,
        dob=format_date_to_dd_mm_yyyy(family_member.dob),
        aadhar_number=family_member.aadhar_number,
        dependant=family_member.dependant,
        message="Family member added successfully"
    )


@router.get("/family-members/{employee_id}", response_model=list[FamilyMemberOut])
def get_family_members(employee_id: str, db: Session = Depends(get_db)):
    """Get all family members for an employee"""
    
    # Check if employee exists
    employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    family_members = db.query(FamilyMember).filter(
        FamilyMember.employee_id == employee_id
    ).all()
    
    result = []
    for member in family_members:
        result.append(FamilyMemberOut(
            family_id=member.family_id,
            employee_id=member.employee_id,
            relation_type=member.relation_type,
            name=member.name,
            dob=format_date_to_dd_mm_yyyy(member.dob),
            aadhar_number=member.aadhar_number,
            dependant=member.dependant,
            message="Family member retrieved successfully"
        ))
    
    return result


@router.put("/family-member/{family_id}", response_model=FamilyMemberOut)
def update_family_member(family_id: int, payload: FamilyMemberIn, db: Session = Depends(get_db)):
    """Update a family member"""
    
    family_member = db.query(FamilyMember).filter(FamilyMember.family_id == family_id).first()
    if not family_member:
        raise HTTPException(status_code=404, detail="Family member not found")
    
    # Update family member
    family_member.relation_type = payload.relation_type
    family_member.name = payload.name
    family_member.dob = convert_dd_mm_yyyy_to_date(payload.dob)
    family_member.aadhar_number = payload.aadhar_number
    family_member.dependant = payload.dependant
    family_member.updated_by = "system"
    
    db.commit()
    db.refresh(family_member)
    
    return FamilyMemberOut(
        family_id=family_member.family_id,
        employee_id=family_member.employee_id,
        relation_type=family_member.relation_type,
        name=family_member.name,
        dob=format_date_to_dd_mm_yyyy(family_member.dob),
        aadhar_number=family_member.aadhar_number,
        dependant=family_member.dependant,
        message="Family member updated successfully"
    )


@router.delete("/family-member/{family_id}")
def delete_family_member(family_id: int, db: Session = Depends(get_db)):
    """Delete a family member"""
    
    family_member = db.query(FamilyMember).filter(FamilyMember.family_id == family_id).first()
    if not family_member:
        raise HTTPException(status_code=404, detail="Family member not found")
    
    db.delete(family_member)
    db.commit()
    
    return {"message": "Family member deleted successfully"}
