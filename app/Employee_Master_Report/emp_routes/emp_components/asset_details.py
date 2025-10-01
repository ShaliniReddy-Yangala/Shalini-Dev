from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.Employee_Master_Report.emp_models.employee_master import EmployeeMaster, AssetHistory
from app.Employee_Master_Report.emp_schema.employee_entry_schemas import (
    AssetDetailsIn,
    AssetDetailsOut
)

router = APIRouter(prefix="/employee-entry", tags=["Employee Entry - Asset Details"])


@router.post("/asset-details", status_code=status.HTTP_201_CREATED, response_model=AssetDetailsOut)
def create_asset_details(payload: AssetDetailsIn, db: Session = Depends(get_db)):
    """Create a new asset record for an employee"""
    
    # Check if employee exists
    employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == payload.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Create asset history
    asset = AssetHistory(
        employee_id=payload.employee_id,
        asset_type=payload.asset_type,
        asset_number=payload.asset_number,
        issued_date=payload.issued_date,
        status=payload.status,
        created_by="system",
        updated_by="system"
    )
    
    db.add(asset)
    db.commit()
    db.refresh(asset)
    
    return AssetDetailsOut(
        asset_id=asset.asset_id,
        employee_id=asset.employee_id,
        asset_type=asset.asset_type,
        asset_number=asset.asset_number,
        issued_date=str(asset.issued_date),
        status=asset.status,
        message="Asset details added successfully"
    )


@router.get("/asset-details/{employee_id}", response_model=list[AssetDetailsOut])
def get_asset_details(employee_id: str, db: Session = Depends(get_db)):
    """Get all asset records for an employee"""
    
    # Check if employee exists
    employee = db.query(EmployeeMaster).filter(EmployeeMaster.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    asset_records = db.query(AssetHistory).filter(
        AssetHistory.employee_id == employee_id
    ).all()
    
    result = []
    for asset in asset_records:
        result.append(AssetDetailsOut(
            asset_id=asset.asset_id,
            employee_id=asset.employee_id,
            asset_type=asset.asset_type,
            asset_number=asset.asset_number,
            issued_date=str(asset.issued_date) if asset.issued_date else "",
            status=asset.status,
            message="Asset details retrieved successfully"
        ))
    # Fallback: only if master has meaningful asset fields (ignore default status)
    if not result and any([employee.asset_type, employee.asset_number, employee.asset_issued_date]):
        result.append(AssetDetailsOut(
            asset_id=0,
            employee_id=employee.employee_id,
            asset_type=employee.asset_type or "",
            asset_number=employee.asset_number or "",
            issued_date=str(employee.asset_issued_date) if employee.asset_issued_date else "",
            status=employee.asset_status or "Issued",
            message="Asset details retrieved successfully"
        ))

    return result


@router.put("/asset-details/{asset_id}", response_model=AssetDetailsOut)
def update_asset_details(asset_id: int, payload: AssetDetailsIn, db: Session = Depends(get_db)):
    """Update an asset record"""
    
    asset = db.query(AssetHistory).filter(AssetHistory.asset_id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset record not found")
    
    # Update asset record
    asset.asset_type = payload.asset_type
    asset.asset_number = payload.asset_number
    asset.issued_date = payload.issued_date
    asset.status = payload.status
    asset.updated_by = "system"
    
    db.commit()
    db.refresh(asset)
    
    return AssetDetailsOut(
        asset_id=asset.asset_id,
        employee_id=asset.employee_id,
        asset_type=asset.asset_type,
        asset_number=asset.asset_number,
        issued_date=str(asset.issued_date),
        status=asset.status,
        message="Asset details updated successfully"
    )


@router.delete("/asset-details/{asset_id}")
def delete_asset_details(asset_id: int, db: Session = Depends(get_db)):
    """Delete an asset record"""
    
    asset = db.query(AssetHistory).filter(AssetHistory.asset_id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset record not found")
    
    db.delete(asset)
    db.commit()
    
    return {"message": "Asset record deleted successfully"}
