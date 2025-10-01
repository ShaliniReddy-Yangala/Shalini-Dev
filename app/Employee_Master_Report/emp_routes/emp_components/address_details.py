from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.Employee_Master_Report.emp_models.employee_master import EmployeeMaster, AddressHistory
from app.Employee_Master_Report.emp_schema.employee_entry_schemas import (
    AddressDetailsIn,
    AddressDetailsOut,
    AddressInfo
)

router = APIRouter(prefix="/employee-entry", tags=["Employee Entry - Address Details"])


@router.post("/address-details", status_code=status.HTTP_201_CREATED, response_model=AddressDetailsOut)
def create_address_details(payload: AddressDetailsIn, db: Session = Depends(get_db)):
    """Create or update address details for an employee"""
    
    # Check if employee exists
    employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == payload.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Update main address fields (for quick reference)
    employee.address_type = "Permanent"
    employee.h_no = payload.permanent_address.h_no
    employee.street = payload.permanent_address.street
    employee.street2 = payload.permanent_address.street2
    employee.landmark = payload.permanent_address.landmark
    employee.city = payload.permanent_address.city
    employee.state = payload.permanent_address.state
    employee.postal_code = payload.permanent_address.postal_code
    employee.complete_address = payload.permanent_address.complete_address
    employee.updated_by = "system"
    
    # Create address history entries
    addresses = [
        (payload.permanent_address, "Permanent"),
        (payload.temporary_address, "Temporary"),
        (payload.office_address, "Office")
    ]
    
    for address, address_type in addresses:
        # Check if address history already exists for this type
        existing_address = db.query(AddressHistory).filter(
            AddressHistory.employee_id == payload.employee_id,
            AddressHistory.address_type == address_type
        ).first()
        
        if existing_address:
            # Update existing address
            existing_address.h_no = address.h_no
            existing_address.street = address.street
            existing_address.street2 = address.street2
            existing_address.landmark = address.landmark
            existing_address.city = address.city
            existing_address.state = address.state
            existing_address.postal_code = address.postal_code
            existing_address.complete_address = address.complete_address
            existing_address.updated_by = "system"
        else:
            # Create new address history
            new_address = AddressHistory(
                employee_id=payload.employee_id,
                address_type=address_type,
                h_no=address.h_no,
                street=address.street,
                street2=address.street2,
                landmark=address.landmark,
                city=address.city,
                state=address.state,
                postal_code=address.postal_code,
                complete_address=address.complete_address,
                created_by="system",
                updated_by="system"
            )
            db.add(new_address)
    
    db.commit()
    
    return AddressDetailsOut(
        employee_id=payload.employee_id,
        permanent_address=payload.permanent_address,
        temporary_address=payload.temporary_address,
        office_address=payload.office_address,
        message="Address details updated successfully"
    )


@router.get("/address-details/{employee_id}", response_model=AddressDetailsOut)
def get_address_details(employee_id: str, db: Session = Depends(get_db)):
    """Get address details for an employee"""
    
    employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get address history
    address_history = db.query(AddressHistory).filter(
        AddressHistory.employee_id == employee_id
    ).all()
    
    # Initialize with defaults
    permanent_address = AddressInfo(address_type="Permanent")
    temporary_address = AddressInfo(address_type="Temporary")
    office_address = AddressInfo(address_type="Office")
    
    # Fill in from address history
    for addr in address_history:
        if addr.address_type == "Temporary":
            temporary_address = AddressInfo(
                address_type=addr.address_type,
                h_no=addr.h_no,
                street=addr.street,
                street2=addr.street2,
                landmark=addr.landmark,
                city=addr.city,
                state=addr.state,
                postal_code=addr.postal_code,
                complete_address=addr.complete_address
            )
        elif addr.address_type == "Office":
            office_address = AddressInfo(
                address_type=addr.address_type,
                h_no=addr.h_no,
                street=addr.street,
                street2=addr.street2,
                landmark=addr.landmark,
                city=addr.city,
                state=addr.state,
                postal_code=addr.postal_code,
                complete_address=addr.complete_address
            )
        elif addr.address_type == "Permanent":
            permanent_address = AddressInfo(
                address_type=addr.address_type,
                h_no=addr.h_no,
                street=addr.street,
                street2=addr.street2,
                landmark=addr.landmark,
                city=addr.city,
                state=addr.state,
                postal_code=addr.postal_code,
                complete_address=addr.complete_address
            )

    # If no permanent record in history, fall back to master quick-reference
    if permanent_address and not any([
        permanent_address.h_no, permanent_address.street, permanent_address.street2,
        permanent_address.landmark, permanent_address.city, permanent_address.state,
        permanent_address.postal_code, permanent_address.complete_address
    ]):
        permanent_address = AddressInfo(
            address_type="Permanent",
            h_no=employee.h_no,
            street=employee.street,
            street2=employee.street2,
            landmark=employee.landmark,
            city=employee.city,
            state=employee.state,
            postal_code=employee.postal_code,
            complete_address=employee.complete_address
        )
    
    return AddressDetailsOut(
        employee_id=employee_id,
        permanent_address=permanent_address,
        temporary_address=temporary_address,
        office_address=office_address,
        message="Address details retrieved successfully"
    )


@router.put("/address-details/{employee_id}", response_model=AddressDetailsOut)
def update_address_details(employee_id: str, payload: AddressDetailsIn, db: Session = Depends(get_db)):
    """Update address details for an employee"""
    
    # Check if employee exists
    employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Update main address fields (for quick reference)
    employee.address_type = "Permanent"
    employee.h_no = payload.permanent_address.h_no
    employee.street = payload.permanent_address.street
    employee.street2 = payload.permanent_address.street2
    employee.landmark = payload.permanent_address.landmark
    employee.city = payload.permanent_address.city
    employee.state = payload.permanent_address.state
    employee.postal_code = payload.permanent_address.postal_code
    employee.complete_address = payload.permanent_address.complete_address
    employee.updated_by = "system"
    
    # Create or update address history entries
    addresses = [
        (payload.permanent_address, "Permanent"),
        (payload.temporary_address, "Temporary"),
        (payload.office_address, "Office")
    ]
    
    for address, address_type in addresses:
        # Check if address history already exists for this type
        existing_address = db.query(AddressHistory).filter(
            AddressHistory.employee_id == employee_id,
            AddressHistory.address_type == address_type
        ).first()
        
        if existing_address:
            # Update existing address
            existing_address.h_no = address.h_no
            existing_address.street = address.street
            existing_address.street2 = address.street2
            existing_address.landmark = address.landmark
            existing_address.city = address.city
            existing_address.state = address.state
            existing_address.postal_code = address.postal_code
            existing_address.complete_address = address.complete_address
            existing_address.updated_by = "system"
        else:
            # Create new address history
            new_address = AddressHistory(
                employee_id=employee_id,
                address_type=address_type,
                h_no=address.h_no,
                street=address.street,
                street2=address.street2,
                landmark=address.landmark,
                city=address.city,
                state=address.state,
                postal_code=address.postal_code,
                complete_address=address.complete_address,
                created_by="system",
                updated_by="system"
            )
            db.add(new_address)
    
    db.commit()
    
    return AddressDetailsOut(
        employee_id=employee_id,
        permanent_address=payload.permanent_address,
        temporary_address=payload.temporary_address,
        office_address=payload.office_address,
        message="Address details updated successfully"
    )
 