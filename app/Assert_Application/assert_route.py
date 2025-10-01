from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Response
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.database import get_db
from .assert_model import Asset, AssetAssignment, AssetAttachment, MaintenanceLog
from .assert_schema import (
    AssetCreate,
    AssetOut,
    AssetUpdate,
    AssetAssignRequest,
    AssetUnassignRequest,
    AssetAssignmentOut,
    AssetAttachmentCreate,
    AssetAttachmentOut,
    AssetBulkImportRequest,
)
from app.Employee_Master_Report.emp_models.dropdowns import AssetType, AssetStatus
from app.routes.email_service import EmailService
import os
import boto3
from botocore.exceptions import ClientError
from app.config import AWS_REGION, S3_BUCKET
from .assert_schema import AssetUploadRequest, AssetPresignedResponse, AssetHistoryOut, AssetAssignmentOut
import json


router = APIRouter(prefix="/assets", tags=["Assets"])

## Asset Routes
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=AssetOut)
def create_asset(payload: AssetCreate, db: Session = Depends(get_db)):
    # Validate type and status against dropdown masters
    if payload.asset_type:
        exists_type = db.query(AssetType).filter(AssetType.type == payload.asset_type).first()
        if not exists_type:
            raise HTTPException(status_code=400, detail="Invalid asset_type")
    if payload.asset_status:
        exists_status = db.query(AssetStatus).filter(AssetStatus.status == payload.asset_status).first()
        if not exists_status:
            raise HTTPException(status_code=400, detail="Invalid asset_status")

    # Note: Category validation should be done via separate categories endpoint
    item = Asset(
        asset_name=payload.asset_name,
        asset_type=payload.asset_type,
        asset_model=payload.asset_model,
        category=payload.category,
        company_name=payload.company_name,
        asset_description=payload.asset_description,
        serial_no=payload.serial_no,
        issued_on=payload.issued_on,
        returned_on=payload.returned_on,
        asset_status=payload.asset_status,
        quantity=payload.quantity,
        notes=payload.notes,
        employee_id=payload.employee_id,
        department=payload.department,
        attachment_url=payload.attachment_url,
        created_by=payload.created_by,
        updated_by=payload.updated_by,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("", response_model=List[AssetOut])
@router.get("/", response_model=List[AssetOut])
def list_assets(
    response: Response,
    db: Session = Depends(get_db),
    search: Optional[str] = Query(None, description="Search across name, model, serial, company"),
    employee_id: Optional[str] = None,
    asset_type: Optional[str] = None,
    asset_status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = db.query(Asset)

    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                Asset.asset_name.ilike(like),
                Asset.asset_model.ilike(like),
                Asset.serial_no.ilike(like),
                Asset.company_name.ilike(like),
                Asset.asset_description.ilike(like),
            )
        )

    if employee_id:
        query = query.filter(Asset.employee_id == employee_id)
    if asset_type:
        query = query.filter(Asset.asset_type == asset_type)
    if asset_status:
        query = query.filter(Asset.asset_status == asset_status)

    # Total count before pagination
    total_count = query.count()

    # Apply ordering and pagination
    items = (
        query
        .order_by(Asset.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # Pagination headers for frontend
    response.headers["X-Total-Count"] = str(total_count)
    response.headers["X-Page"] = str(page)
    response.headers["X-Page-Size"] = str(page_size)

    return items


# Convenience: generate presigned URL for asset attachments
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=AWS_REGION,
    endpoint_url=f"https://s3.{AWS_REGION}.amazonaws.com"
)


@router.post("/upload-url", response_model=AssetPresignedResponse, status_code=status.HTTP_201_CREATED)
def generate_asset_upload_url(data: AssetUploadRequest):
    file_key = data.file_name if '/' in data.file_name else f"assets/{data.file_name}"
    try:
        url = s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": S3_BUCKET,
                "Key": file_key,
                "ContentType": data.content_type,
            },
            ExpiresIn=3600
        )
        object_url = f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{file_key}"
        return AssetPresignedResponse(upload_url=url, object_url=object_url, file_key=file_key)
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{asset_id}", response_model=AssetOut)
def get_asset(asset_id: int, db: Session = Depends(get_db)):
    item = db.query(Asset).filter(Asset.id == asset_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Asset not found")
    return item


# Assignment history for an asset
@router.get("/{asset_id}/assignments", response_model=List[AssetAssignmentOut])
def get_asset_assignments(
    asset_id: int,
    active_only: Optional[bool] = False,
    db: Session = Depends(get_db),
):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    query = db.query(AssetAssignment).filter(AssetAssignment.asset_id == asset_id)
    if active_only:
        query = query.filter(AssetAssignment.returned_on == None)
    return query.order_by(AssetAssignment.issued_on.desc(), AssetAssignment.id.desc()).all()


# Combined historical data for an asset
@router.get("/{asset_id}/history", response_model=AssetHistoryOut)
def get_asset_history(
    asset_id: int,
    db: Session = Depends(get_db),
):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    assignments = (
        db.query(AssetAssignment)
        .filter(AssetAssignment.asset_id == asset_id)
        .order_by(AssetAssignment.issued_on.desc(), AssetAssignment.id.desc())
        .all()
    )

    maintenance_logs = (
        db.query(MaintenanceLog)
        .filter(MaintenanceLog.asset_id == asset_id)
        .order_by(MaintenanceLog.created_at.desc(), MaintenanceLog.id.desc())
        .all()
    )

    return AssetHistoryOut(assignments=assignments, maintenance_logs=maintenance_logs)

@router.put("/{asset_id}", response_model=AssetOut)
def update_asset(asset_id: int, payload: AssetUpdate, db: Session = Depends(get_db)):
    item = db.query(Asset).filter(Asset.id == asset_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Optional validations
    if payload.asset_type:
        if not db.query(AssetType).filter(AssetType.type == payload.asset_type).first():
            raise HTTPException(status_code=400, detail="Invalid asset_type")
    if payload.asset_status:
        if not db.query(AssetStatus).filter(AssetStatus.status == payload.asset_status).first():
            raise HTTPException(status_code=400, detail="Invalid asset_status")

    update_data = payload.model_dump(exclude_unset=True)
    
    # Auto-set status to "In Use" when employee_id is assigned
    if payload.employee_id and not payload.asset_status:
        update_data['asset_status'] = 'In Use'
    
    # Auto-set status to "In Stock" when asset is returned (returned_on provided)
    if payload.returned_on and not payload.asset_status:
        update_data['asset_status'] = 'In Stock'
        # Clear employee_id when returned
        if not payload.employee_id:
            update_data['employee_id'] = None
    
    for field, value in update_data.items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(asset_id: int, db: Session = Depends(get_db)):
    item = db.query(Asset).filter(Asset.id == asset_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Asset not found")
    db.delete(item)
    db.commit()
    return None


# Assign asset to employee
@router.post("/{asset_id}/assign", response_model=AssetAssignmentOut, status_code=status.HTTP_201_CREATED)
def assign_asset(asset_id: int, payload: AssetAssignRequest, db: Session = Depends(get_db)):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    assignment = AssetAssignment(
        asset_id=asset_id,
        employee_id=payload.employee_id,
        issued_on=payload.issued_on,
        attachment_url=payload.attachment_url,
    )
    db.add(assignment)
    # optional: update asset_status / employee_id
    asset.employee_id = payload.employee_id
    asset.asset_status = asset.asset_status or "In Use"
    db.commit(); db.refresh(assignment)

    # Notification (best-effort; non-blocking failure handling)
    try:
        service = EmailService()
        subject = f"Asset Assigned: {asset.asset_name}"
        body = (
            f"<p>Asset <strong>{asset.asset_name}</strong> (Serial: {asset.serial_no or 'N/A'}) has been assigned to employee"
            f" <strong>{payload.employee_id}</strong> on {payload.issued_on or 'today'}.</p>"
        )
        service.send_email(recipient=service.sender_email, subject=subject, body=body)
    except Exception:
        pass
    return assignment


# Unassign/return asset
@router.post("/{asset_id}/unassign", response_model=AssetAssignmentOut)
def unassign_asset(asset_id: int, payload: AssetUnassignRequest, db: Session = Depends(get_db)):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Find the latest open assignment
    assignment = (
        db.query(AssetAssignment)
        .filter(AssetAssignment.asset_id == asset_id, AssetAssignment.returned_on == None)
        .order_by(AssetAssignment.issued_on.desc())
        .first()
    )
    if not assignment:
        raise HTTPException(status_code=400, detail="No active assignment found")

    assignment.returned_on = payload.returned_on
    assignment.condition_on_return = payload.condition_on_return
    if payload.attachment_url:
        assignment.attachment_url = payload.attachment_url

    # optional: clear on asset and set status to "In Stock"
    asset.employee_id = None
    asset.asset_status = "In Stock"
    db.commit(); db.refresh(assignment)

    # Notification (best-effort)
    try:
        service = EmailService()
        subject = f"Asset Returned: {asset.asset_name}"
        body = (
            f"<p>Asset <strong>{asset.asset_name}</strong> (Serial: {asset.serial_no or 'N/A'}) was returned on"
            f" {payload.returned_on or 'today'}. Condition: {payload.condition_on_return or 'N/A'}.</p>"
        )
        service.send_email(recipient=service.sender_email, subject=subject, body=body)
    except Exception:
        pass
    return assignment


# Bulk import
@router.post("/import", status_code=status.HTTP_201_CREATED, response_model=List[AssetOut])
async def bulk_import_assets(request: Request, db: Session = Depends(get_db)):
    """
    Bulk import assets.

    Accepts either:
    - application/json with body: {"items": [...]} or just an array [...]
    - multipart/form-data with a field 'items' containing the JSON string above

    Any unknown fields in items are ignored. Supports optional 'issued_on' and 'returned_on'.
    Files should be uploaded separately via the presign flow; any files in the multipart
    payload are ignored by this endpoint.
    """
    # Parse incoming payload flexibly
    try:
        content_type = request.headers.get("content-type", "")
        data = None
        if "multipart/form-data" in content_type:
            form = await request.form()
            raw_items = form.get("items")
            if not raw_items:
                raise HTTPException(status_code=422, detail="'items' field is required in form-data")
            try:
                data = json.loads(raw_items)
            except Exception:
                raise HTTPException(status_code=422, detail="'items' must be valid JSON")
        else:
            # attempt to parse JSON body
            try:
                data = await request.json()
            except Exception:
                raise HTTPException(status_code=422, detail="Request body must be JSON with 'items'")

        # Normalize to items list
        if isinstance(data, list):
            items_list = data
        elif isinstance(data, dict) and "items" in data:
            items_list = data.get("items")
        else:
            raise HTTPException(status_code=422, detail="Body must be { 'items': [...] } or an array of items")

        if not isinstance(items_list, list) or len(items_list) == 0:
            raise HTTPException(status_code=422, detail="'items' must be a non-empty array")

        created_items: List[Asset] = []
        # Allowed keys to set on Asset model
        allowed_keys = {
            "asset_name",
            "asset_type",
            "asset_model",
            "category",
            "company_name",
            "asset_description",
            "serial_no",
            "issued_on",
            "returned_on",
            "asset_status",
            "quantity",
            "notes",
            "employee_id",
            "department",
            "attachment_url",
        }

        for idx, row in enumerate(items_list):
            if not isinstance(row, dict):
                raise HTTPException(status_code=422, detail=f"items[{idx}] must be an object")

            # Required fields
            required_fields = ["asset_name", "asset_type", "category", "asset_status"]
            for f in required_fields:
                if not row.get(f):
                    raise HTTPException(status_code=422, detail=f"items[{idx}].{f} is required")

            # Default quantity
            if "quantity" not in row or row.get("quantity") in (None, ""):
                row["quantity"] = 1

            # Validate type and status against dropdown masters (same as create endpoint)
            if row.get("asset_type"):
                if not db.query(AssetType).filter(AssetType.type == row["asset_type"]).first():
                    raise HTTPException(status_code=400, detail=f"Invalid asset_type at items[{idx}]")
            if row.get("asset_status"):
                if not db.query(AssetStatus).filter(AssetStatus.status == row["asset_status"]).first():
                    raise HTTPException(status_code=400, detail=f"Invalid asset_status at items[{idx}]")

            # Build the Asset entity using only allowed keys
            filtered_data = {k: row.get(k) for k in allowed_keys if k in row}
            item = Asset(**filtered_data)
            db.add(item)
            created_items.append(item)

        db.commit()
        for item in created_items:
            db.refresh(item)
        return created_items
    except HTTPException:
        # Re-raise HTTPException as-is
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Add attachment record after upload
@router.post("/{asset_id}/attachments", response_model=AssetAttachmentOut, status_code=status.HTTP_201_CREATED)
def add_asset_attachment(asset_id: int, payload: AssetAttachmentCreate, db: Session = Depends(get_db)):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    att = AssetAttachment(
        asset_id=asset_id,
        file_type=payload.file_type,
        file_url=payload.file_url,
        created_by=payload.created_by,
    )
    db.add(att); 
    db.commit(); 
    db.refresh(att)
    return att


__all__ = [
    "router",
]



