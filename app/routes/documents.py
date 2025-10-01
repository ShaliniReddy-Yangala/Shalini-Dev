from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import boto3
import uuid
import os
from botocore.exceptions import ClientError

from app.models import Candidate, Document, DocumentType, DocumentStatus, ShareableLink
from app.database import get_db
from app.schemas import DocumentResponse, PresignedURLResponse, ShareableLinkResponse, UploadRequest

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
    responses={404: {"description": "Not found"}},
)

# S3 Configuration
AWS_REGION = os.getenv("AWS_REGION", "ap-south-2")
S3_BUCKET = os.getenv("S3_BUCKET", "upload-media00")
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=AWS_REGION,
    endpoint_url=f"https://s3.{AWS_REGION}.amazonaws.com"
)

@router.post("/upload/{document_type}")
async def upload_document(
    document_type: str,
    file: Optional[UploadFile] = File(None),
    files: Optional[List[UploadFile]] = File(None),
    candidate_id: str = Form(...),
    user_id: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Upload one or more documents for a specific candidate.
    Supports both single file (backward compatibility) and multiple files.
    Use 'file' for single file uploads, 'files' for multiple file uploads.
    """
    # Validate document type
    try:
        doc_type = DocumentType(document_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document type")
    
    # Check if candidate exists
    candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    # Determine which files to process
    files_to_process = []
    if files:
        files_to_process = files
    elif file:
        files_to_process = [file]
    else:
        raise HTTPException(status_code=400, detail="Either 'file' or 'files' parameter is required")
    
    uploaded_documents = []
    
    try:
        for file in files_to_process:
            # Generate a unique filename
            file_extension = os.path.splitext(file.filename)[1]
            unique_filename = f"{candidate_id}/{document_type}/{uuid.uuid4()}{file_extension}"
            
            # Upload file to S3
            s3_client.upload_fileobj(
                file.file,
                S3_BUCKET,
                unique_filename,
                ExtraArgs={
                    'ContentType': file.content_type
                }
            )
            
            # Create new document record in database
            new_document = Document(
                candidate_id=candidate_id,
                document_type=doc_type,
                original_filename=file.filename,
                s3_key=unique_filename,
                content_type=file.content_type,
                status=DocumentStatus.PENDING,
                uploaded_at=datetime.now(timezone.utc)
            )
            
            db.add(new_document)
            
            # Generate a pre-signed URL for download
            presigned_url = s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': S3_BUCKET,
                    'Key': unique_filename
                },
                ExpiresIn=3600  # 1 hour
            )
            
            uploaded_documents.append({
                "id": str(new_document.id),
                "documentType": document_type,
                "filename": file.filename,
                "candidateId": candidate_id,
                "uploadedAt": new_document.uploaded_at,
                "downloadUrl": presigned_url
            })
        
        # Update candidate status if needed (only once for all files)
        if candidate.current_status is None or candidate.current_status != "Docs Upload":
            candidate.current_status = "Docs Upload"
            candidate.status_updated_on = datetime.now(timezone.utc).date()
            
        # Update document collection date
        candidate.documents_collect_date = datetime.now(timezone.utc).date()
        
        db.commit()
        
        # Return single document for backward compatibility if only one file
        if len(uploaded_documents) == 1:
            return uploaded_documents[0]
        
        # Return array of documents for multiple files
        return {
            "documents": uploaded_documents,
            "count": len(uploaded_documents),
            "candidateId": candidate_id,
            "documentType": document_type
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    

@router.post("/generate-upload-url", response_model=PresignedURLResponse)
async def generate_document_upload_url(
    data: UploadRequest,
    db: Session = Depends(get_db)
):
    """
    Generate a presigned URL for document upload
    """
    # Validate document type
    try:
        doc_type = DocumentType(data.document_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document type")
    
    # Check if candidate exists
    candidate = db.query(Candidate).filter(Candidate.candidate_id == data.candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    # Get file extension and check if it's allowed
    file_extension = os.path.splitext(data.file_name)[1].lower().lstrip('.')
    
    # Define allowed extensions
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}
    
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}")
    
    # Generate a unique filename
    unique_filename = f"{data.candidate_id}/{data.document_type}/{uuid.uuid4()}.{file_extension}"
    
    try:
        # Generate presigned URL for the client to upload directly
        presigned_url = s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": S3_BUCKET,
                "Key": unique_filename,
                "ContentType": data.content_type,
            },
            ExpiresIn=3600  # 1 hour
        )
        
        return {
            "uploadUrl": presigned_url,
            "documentId": unique_filename,
            "documentType": data.document_type,
            "expiresIn": 3600
        }
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate upload URL: {str(e)}")

@router.post("/confirm-upload/{document_id}")
async def confirm_document_upload(
    document_id: str,  
    user_id: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Confirm a document upload and update candidate status
    """
    # Extract candidate_id from document_id
    parts = document_id.split('/')
    if len(parts) < 2:
        raise HTTPException(status_code=400, detail="Invalid document ID format")
    
    candidate_id = parts[0]
    document_type = parts[1] if len(parts) > 1 else "unknown"
    
    # Check if the file exists in S3
    try:
        file_info = s3_client.head_object(Bucket=S3_BUCKET, Key=document_id)
    except ClientError:
        raise HTTPException(status_code=404, detail="Document not found in storage")
    
    # Get candidate
    candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    # Create document record
    try:
        doc_type = DocumentType(document_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document type")
    
    # Create new document in database
    new_document = Document(
        candidate_id=candidate_id,
        document_type=doc_type,
        original_filename=document_id.split('/')[-1],
        s3_key=document_id,
        content_type=file_info.get('ContentType', 'application/octet-stream'),
        status=DocumentStatus.PENDING,
        uploaded_at=datetime.now(timezone.utc)
    )
    
    db.add(new_document)
    
    # Update candidate status if needed
    if candidate.current_status is None or candidate.current_status != "Docs Upload":
        candidate.current_status = "Docs Upload"
        candidate.status_updated_on = datetime.now(timezone.utc).date()
        
    # Update document collection date
    candidate.documents_collect_date = datetime.now(timezone.utc).date()
    
    db.commit()
    
    # Generate a pre-signed URL for download
    download_url = s3_client.generate_presigned_url(
        'get_object',
        Params={
            'Bucket': S3_BUCKET,
            'Key': document_id
        },
        ExpiresIn=3600  # 1 hour
    )
    
    return {
        "message": "Document upload confirmed and candidate status updated",
        "id": str(new_document.id),
        "documentType": document_type,
        "candidateId": candidate_id,
        "uploadedAt": new_document.uploaded_at,
        "downloadUrl": download_url
    }

@router.get("/{candidate_id}", response_model=List[DocumentResponse])
async def get_candidate_documents(
    candidate_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all documents for a specific candidate.
    """
    # Check if candidate exists
    candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    # Get documents from database
    documents = db.query(Document).filter(Document.candidate_id == candidate_id).all()
    
    result = []
    for doc in documents:
        # Generate download URL
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': S3_BUCKET,
                'Key': doc.s3_key
            },
            ExpiresIn=3600  # 1 hour
        )
        
        result.append({
            "id": str(doc.id),
            "documentType": doc.document_type.value,
            "filename": doc.original_filename,
            "candidateId": doc.candidate_id,
            "uploadedAt": doc.uploaded_at,
            "downloadUrl": presigned_url
        })
    
    return result

@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a specific document.
    """
    # Get document by ID
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        # Delete from S3
        s3_client.delete_object(
            Bucket=S3_BUCKET,
            Key=document.s3_key
        )
        
        # Delete document record
        db.delete(document)
        db.commit()
        
        return {"message": "Document deleted successfully"}
    except ClientError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

@router.post("/shareable-link/{candidate_id}", response_model=ShareableLinkResponse)
async def create_shareable_link(
    candidate_id: str,
    user_id: str = Form(...),
    expiration: int = Form(7*24*60*60),  # Default to 7 days in seconds
    db: Session = Depends(get_db)
):
    """
    Create a shareable link for all documents of a candidate.
    """
    # Check if candidate exists
    candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    try:
        # Generate a unique token
        token = str(uuid.uuid4())
        
        # Calculate expiration date
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expiration)
        
        # Create new shareable link record
        new_link = ShareableLink(
            token=token,
            candidate_id=candidate_id,
            created_by=user_id,
            created_at=datetime.now(timezone.utc),
            expires_at=expires_at,
            is_active=True
        )
        
        db.add(new_link)
        
        # Build URL for frontend to access
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        shareable_url = f"{frontend_url}/shared-documents/{candidate_id}/{token}"
        
        db.commit()
        
        return {
            "shareableLink": shareable_url,
            "candidateId": candidate_id,
            "expiresIn": expiration,
            "createdAt": new_link.created_at
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to generate shareable link: {str(e)}")

@router.get("/shared/{candidate_id}/{token}", response_model=List[DocumentResponse])
async def access_shared_documents(
    candidate_id: str,
    token: str,
    db: Session = Depends(get_db)
):
    """
    Access documents through a shared link.
    """
    # Validate token
    link = db.query(ShareableLink).filter(
        ShareableLink.candidate_id == candidate_id,
        ShareableLink.token == token,
        ShareableLink.is_active == True,
        ShareableLink.expires_at > datetime.now(timezone.utc)
    ).first()
    
    if not link:
        raise HTTPException(status_code=403, detail="Invalid or expired link")
    
    # Return the documents for the candidate
    return await get_candidate_documents(candidate_id, db)

@router.post("/verify/{document_id}")
async def verify_document(
    document_id: str,
    status: DocumentStatus = Form(DocumentStatus.VERIFIED),
    notes: Optional[str] = Form(None),
    user_id: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Verify a specific document.
    """
    # Get document
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Update document status
    document.status = status
    document.verification_notes = notes
    document.verified_at = datetime.now(timezone.utc)
    document.verified_by = user_id
    document.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    
    return {"message": f"Document status updated to {status.value}"}

@router.post("/verify-all/{candidate_id}")
async def verify_all_documents(
    candidate_id: str,
    user_id: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Mark all documents as verified for a candidate and update status.
    """
    candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    # Get all pending documents
    documents = db.query(Document).filter(
        Document.candidate_id == candidate_id,
        Document.status == DocumentStatus.PENDING
    ).all()
    
    # Update all documents
    now = datetime.now(timezone.utc)
    for doc in documents:
        doc.status = DocumentStatus.VERIFIED
        doc.verified_at = now
        doc.verified_by = user_id
        doc.updated_at = now
    
    # Update candidate status to move to the next stage
    if candidate.current_status == "Docs Upload":
       candidate.current_status = "Create Offer"
       candidate.status_updated_on = datetime.now(timezone.utc).date()
    
    db.commit()
    
    return {"message": "All documents verified and candidate status updated"}

@router.get("/generate-download-url/{document_id}")
async def generate_download_url(
    document_id: str,
    db: Session = Depends(get_db)
):
    """
    Generate a pre-signed URL for downloading a document
    """
    # Get document
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        # Generate a pre-signed URL for download (skip head_object check to avoid permission issues)
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': S3_BUCKET,
                'Key': document.s3_key
            },
            ExpiresIn=3600  # 1 hour
        )
        
        return {"downloadUrl": presigned_url}
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchKey':
            raise HTTPException(status_code=404, detail="Document not found in storage")
        elif error_code == 'AccessDenied':
            raise HTTPException(status_code=403, detail="Access denied to document storage")
        else:
            raise HTTPException(status_code=500, detail=f"Failed to generate download URL: {error_code}")