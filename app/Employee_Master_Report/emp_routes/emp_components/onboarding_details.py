from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.Employee_Master_Report.emp_models.employee_master import EmployeeMaster, OnboardingHistory, ClientMaster
from app.Employee_Master_Report.emp_schema.employee_entry_schemas import (
    OnboardingDetailsIn,
    OnboardingDetailsOut
)

router = APIRouter(prefix="/employee-entry", tags=["Employee Entry - Onboarding Details"])


@router.post("/onboarding-details", status_code=status.HTTP_201_CREATED, response_model=OnboardingDetailsOut)
def create_onboarding_details(payload: OnboardingDetailsIn, db: Session = Depends(get_db)):
    """Create a new onboarding record for an employee"""
    
    # Check if employee exists
    employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == payload.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Check if client exists, if not create it
    client = db.query(ClientMaster).filter(ClientMaster.client_name == payload.client_name).first()
    if not client:
        # Create new client
        client = ClientMaster(
            client_name=payload.client_name,
            client_code=payload.client_name.replace(" ", "_").upper()[:20],  # Generate client code
            client_status="Active"
        )
        db.add(client)
        db.flush()  # Flush to get the client_id
    
    # Calculate duration if both dates are provided
    duration_calculated = None
    if payload.effective_start_date and payload.effective_end_date:
        if payload.effective_end_date >= payload.effective_start_date:
            days = (payload.effective_end_date - payload.effective_start_date).days + 1
            duration_calculated = f"{days} days"
    
    # Create onboarding history
    onboarding = OnboardingHistory(
        employee_id=payload.employee_id,
        client_id=client.client_id,
        effective_start_date=payload.effective_start_date,
        effective_end_date=payload.effective_end_date,
        onboarding_status=payload.onboarding_status,
        duration_calculated=duration_calculated or payload.duration_calculated,
        spoc=payload.spoc,
        onboarding_department=payload.onboarding_department,
        assigned_manager=payload.assigned_manager,
        is_current_assignment="Yes" if payload.onboarding_status == "Active" else "No",
        created_by="system",
        updated_by="system"
    )
    
    db.add(onboarding)
    db.commit()
    db.refresh(onboarding)
    
    return OnboardingDetailsOut(
        onboarding_id=onboarding.onboarding_id,
        employee_id=onboarding.employee_id,
        client_name=payload.client_name,
        effective_start_date=str(onboarding.effective_start_date),
        effective_end_date=str(onboarding.effective_end_date) if onboarding.effective_end_date else None,
        onboarding_status=onboarding.onboarding_status,
        duration_calculated=onboarding.duration_calculated,
        spoc=onboarding.spoc,
        onboarding_department=onboarding.onboarding_department,
        assigned_manager=onboarding.assigned_manager,
        message="Onboarding details added successfully"
    )


@router.get("/onboarding-details/{employee_id}", response_model=list[OnboardingDetailsOut])
def get_onboarding_details(employee_id: str, db: Session = Depends(get_db)):
    """Get all onboarding records for an employee"""
    
    # Check if employee exists
    employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    onboarding_records = db.query(OnboardingHistory).filter(
        OnboardingHistory.employee_id == employee_id
    ).all()
    
    result = []
    for onboarding in onboarding_records:
        # Get client name
        client = db.query(ClientMaster).filter(ClientMaster.client_id == onboarding.client_id).first()
        client_name = client.client_name if client else "Unknown Client"
        
        result.append(OnboardingDetailsOut(
            onboarding_id=onboarding.onboarding_id,
            employee_id=onboarding.employee_id,
            client_name=client_name,
            effective_start_date=str(onboarding.effective_start_date),
            effective_end_date=str(onboarding.effective_end_date) if onboarding.effective_end_date else None,
            onboarding_status=onboarding.onboarding_status,
            duration_calculated=onboarding.duration_calculated,
            spoc=onboarding.spoc,
            onboarding_department=onboarding.onboarding_department,
            assigned_manager=onboarding.assigned_manager,
            message="Onboarding details retrieved successfully"
        ))
    
    return result


@router.put("/onboarding-details/{employee_id}", response_model=OnboardingDetailsOut)
def update_onboarding_by_employee_alias(employee_id: str, payload: OnboardingDetailsIn, db: Session = Depends(get_db)):
    """Alias: Update the current (or latest) onboarding record for an employee by employee_id."""
    # Ensure payload employee_id matches path when provided
    if payload.employee_id and payload.employee_id != employee_id:
        raise HTTPException(status_code=400, detail="employee_id in path and body must match")

    # Pick current assignment if present, else the most recent record
    onboarding = db.query(OnboardingHistory).filter(
        OnboardingHistory.employee_id == employee_id
    ).order_by(OnboardingHistory.is_current_assignment.desc(), OnboardingHistory.effective_start_date.desc()).first()
    if not onboarding:
        raise HTTPException(status_code=404, detail="Onboarding record not found for employee")

    # Ensure client exists (create if missing)
    client = db.query(ClientMaster).filter(ClientMaster.client_name == payload.client_name).first()
    if not client:
        client = ClientMaster(
            client_name=payload.client_name,
            client_code=payload.client_name.replace(" ", "_").upper()[:20],
            client_status="Active"
        )
        db.add(client)
        db.flush()

    # Compute duration
    duration_calculated = None
    if payload.effective_start_date and payload.effective_end_date and payload.effective_end_date >= payload.effective_start_date:
        days = (payload.effective_end_date - payload.effective_start_date).days + 1
        duration_calculated = f"{days} days"

    # Update onboarding
    onboarding.client_id = client.client_id
    onboarding.effective_start_date = payload.effective_start_date
    onboarding.effective_end_date = payload.effective_end_date
    onboarding.onboarding_status = payload.onboarding_status
    onboarding.duration_calculated = duration_calculated or payload.duration_calculated
    onboarding.spoc = payload.spoc
    onboarding.onboarding_department = payload.onboarding_department
    onboarding.assigned_manager = payload.assigned_manager
    onboarding.is_current_assignment = "Yes" if payload.onboarding_status == "Active" else "No"
    onboarding.updated_by = "system"

    db.commit()
    db.refresh(onboarding)

    # Get client name
    client_name = db.query(ClientMaster).filter(ClientMaster.client_id == onboarding.client_id).first().client_name

    return OnboardingDetailsOut(
        onboarding_id=onboarding.onboarding_id,
        employee_id=onboarding.employee_id,
        client_name=client_name,
        effective_start_date=str(onboarding.effective_start_date),
        effective_end_date=str(onboarding.effective_end_date) if onboarding.effective_end_date else None,
        onboarding_status=onboarding.onboarding_status,
        duration_calculated=onboarding.duration_calculated,
        spoc=onboarding.spoc,
        onboarding_department=onboarding.onboarding_department,
        assigned_manager=onboarding.assigned_manager,
        message="Onboarding details updated successfully"
    )

@router.put("/onboarding-details/{onboarding_id}", response_model=OnboardingDetailsOut)
def update_onboarding_details(onboarding_id: int, payload: OnboardingDetailsIn, db: Session = Depends(get_db)):
    """Update an onboarding record"""
    
    onboarding = db.query(OnboardingHistory).filter(OnboardingHistory.onboarding_id == onboarding_id).first()
    if not onboarding:
        raise HTTPException(status_code=404, detail="Onboarding record not found")
    
    # Check if client exists, if not create it
    client = db.query(ClientMaster).filter(ClientMaster.client_name == payload.client_name).first()
    if not client:
        client = ClientMaster(
            client_name=payload.client_name,
            client_code=payload.client_name.replace(" ", "_").upper()[:20],
            client_status="Active"
        )
        db.add(client)
        db.flush()
    
    # Calculate duration if both dates are provided
    duration_calculated = None
    if payload.effective_start_date and payload.effective_end_date:
        if payload.effective_end_date >= payload.effective_start_date:
            days = (payload.effective_end_date - payload.effective_start_date).days + 1
            duration_calculated = f"{days} days"
    
    # Update onboarding record
    onboarding.client_id = client.client_id
    onboarding.effective_start_date = payload.effective_start_date
    onboarding.effective_end_date = payload.effective_end_date
    onboarding.onboarding_status = payload.onboarding_status
    onboarding.duration_calculated = duration_calculated or payload.duration_calculated
    onboarding.spoc = payload.spoc
    onboarding.onboarding_department = payload.onboarding_department
    onboarding.assigned_manager = payload.assigned_manager
    onboarding.is_current_assignment = "Yes" if payload.onboarding_status == "Active" else "No"
    onboarding.updated_by = "system"
    
    db.commit()
    db.refresh(onboarding)
    
    return OnboardingDetailsOut(
        onboarding_id=onboarding.onboarding_id,
        employee_id=onboarding.employee_id,
        client_name=payload.client_name,
        effective_start_date=str(onboarding.effective_start_date),
        effective_end_date=str(onboarding.effective_end_date) if onboarding.effective_end_date else None,
        onboarding_status=onboarding.onboarding_status,
        duration_calculated=onboarding.duration_calculated,
        spoc=onboarding.spoc,
        onboarding_department=onboarding.onboarding_department,
        assigned_manager=onboarding.assigned_manager,
        message="Onboarding details updated successfully"
    )


@router.put("/onboarding-details/{employee_id}", response_model=OnboardingDetailsOut)
def update_onboarding_by_employee(employee_id: str, payload: OnboardingDetailsIn, db: Session = Depends(get_db)):
    """Update the current (or latest) onboarding record for an employee by employee_id."""
    # Ensure payload employee_id matches path when provided
    if payload.employee_id and payload.employee_id != employee_id:
        raise HTTPException(status_code=400, detail="employee_id in path and body must match")

    employee = db.query(OnboardingHistory).filter(OnboardingHistory.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Pick current assignment if present, else the most recent record
    onboarding = db.query(OnboardingHistory).filter(
        OnboardingHistory.employee_id == employee_id
    ).order_by(OnboardingHistory.is_current_assignment.desc(), OnboardingHistory.effective_start_date.desc()).first()
    if not onboarding:
        raise HTTPException(status_code=404, detail="Onboarding record not found for employee")

    # Ensure client exists (create if missing)
    client = db.query(ClientMaster).filter(ClientMaster.client_name == payload.client_name).first()
    if not client:
        client = ClientMaster(
            client_name=payload.client_name,
            client_code=payload.client_name.replace(" ", "_").upper()[:20],
            client_status="Active"
        )
        db.add(client)
        db.flush()

    # Compute duration
    duration_calculated = None
    if payload.effective_start_date and payload.effective_end_date and payload.effective_end_date >= payload.effective_start_date:
        days = (payload.effective_end_date - payload.effective_start_date).days + 1
        duration_calculated = f"{days} days"

    # Update onboarding
    onboarding.client_id = client.client_id
    onboarding.effective_start_date = payload.effective_start_date
    onboarding.effective_end_date = payload.effective_end_date
    onboarding.onboarding_status = payload.onboarding_status
    onboarding.duration_calculated = duration_calculated or payload.duration_calculated
    onboarding.spoc = payload.spoc
    onboarding.onboarding_department = payload.onboarding_department
    onboarding.assigned_manager = payload.assigned_manager
    onboarding.is_current_assignment = "Yes" if payload.onboarding_status == "Active" else "No"
    onboarding.updated_by = "system"

    db.commit()
    db.refresh(onboarding)

    # Get client name
    client_name = db.query(ClientMaster).filter(ClientMaster.client_id == onboarding.client_id).first().client_name

    return OnboardingDetailsOut(
        onboarding_id=onboarding.onboarding_id,
        employee_id=onboarding.employee_id,
        client_name=client_name,
        effective_start_date=str(onboarding.effective_start_date),
        effective_end_date=str(onboarding.effective_end_date) if onboarding.effective_end_date else None,
        onboarding_status=onboarding.onboarding_status,
        duration_calculated=onboarding.duration_calculated,
        spoc=onboarding.spoc,
        onboarding_department=onboarding.onboarding_department,
        assigned_manager=onboarding.assigned_manager,
        message="Onboarding details updated successfully"
    )


@router.delete("/onboarding-details/{onboarding_id}")
def delete_onboarding_details(onboarding_id: int, db: Session = Depends(get_db)):
    """Delete an onboarding record"""
    
    onboarding = db.query(OnboardingHistory).filter(OnboardingHistory.onboarding_id == onboarding_id).first()
    if not onboarding:
        raise HTTPException(status_code=404, detail="Onboarding record not found")
    
    db.delete(onboarding)
    db.commit()
    
    return {"message": "Onboarding record deleted successfully"}
