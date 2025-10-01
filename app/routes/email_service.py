# app/routes/email_service.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, EmailStr
import boto3
import os
from typing import Optional, List
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders


email_router = APIRouter(prefix="/api/email", tags=["Email"])

class EmailRequest(BaseModel):
    recipient: EmailStr  # Ensures valid email format
    subject: str
    body: str
    cc: Optional[List[EmailStr]] = None  # Optional CC recipients
    bcc: Optional[List[EmailStr]] = None  # Optional BCC recipients
    attachments: Optional[List[dict]] = None  # Optional attachments with filename and content

class AttachmentInfo(BaseModel):
    filename: str
    content: str  # Base64 encoded content
    content_type: str = "application/octet-stream"

class EmailService:
    def __init__(self):
        # Hardcoded region (ensure it matches your SES configuration)
        self.aws_region = "ap-south-1"  # SES-supported region
        
        # Environment variables
        self.sender_email = os.getenv("SENDER_EMAIL", "hr@vaics-consulting.com")  # Verified domain email
        self.client = boto3.client(
            'ses',
            region_name=self.aws_region,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID1"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY1")
        )

    def send_email(
        self, 
        recipient: str, 
        subject: str, 
        body: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[dict]] = None
    ):
        """Send email via Amazon SES with optional attachments"""
        destination = {'ToAddresses': [recipient]}
        
        if cc:
            destination['CcAddresses'] = cc
        if bcc:
            destination['BccAddresses'] = bcc

        try:
            if attachments:
                # Send email with attachments using raw email
                return self._send_email_with_attachments(
                    destination, subject, body, attachments
                )
            else:
                # Send email without attachments using simple email
                return self._send_simple_email(destination, subject, body)
                
        except self.client.exceptions.MessageRejected as e:
            return {'status': 'error', 'message': f"Message rejected: {str(e)}"}
        except self.client.exceptions.AccountSendingPausedException:
            return {'status': 'error', 'message': "SES sending disabled for account"}
        except Exception as e:
            return {'status': 'error', 'message': f"SES API error: {str(e)}"}

    def _send_simple_email(self, destination, subject, body):
        """Send email without attachments"""
        response = self.client.send_email(
            Source=f"VAICS HR Team <{self.sender_email}>",
            Destination=destination,
            Message={
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                'Body': {
                    'Html': {'Data': body, 'Charset': 'UTF-8'},
                    'Text': {'Data': body, 'Charset': 'UTF-8'},
                }
            }
        )
        return {
            'status': 'success',
            'message_id': response['MessageId'],
            'recipient': destination['ToAddresses'][0]
        }

    def _send_email_with_attachments(self, destination, subject, body, attachments):
        """Send email with attachments using raw email"""
        # Create multipart message
        msg = MIMEMultipart()
        msg['From'] = f"VAICS HR Team <{self.sender_email}>"
        msg['To'] = ', '.join(destination['ToAddresses'])
        if 'CcAddresses' in destination:
            msg['Cc'] = ', '.join(destination['CcAddresses'])
        if 'BccAddresses' in destination:
            msg['Bcc'] = ', '.join(destination['BccAddresses'])
        msg['Subject'] = subject

        # Add body
        msg.attach(MIMEText(body, 'html'))

        # Add attachments
        for attachment in attachments:
            try:
                # Decode base64 content
                file_content = base64.b64decode(attachment['content'])
                
                # Create attachment part
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(file_content)
                encoders.encode_base64(part)
                
                # Set filename - quoted to handle spaces and special characters
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{attachment["filename"]}"'
                )
                
                msg.attach(part)
            except Exception as e:
                return {'status': 'error', 'message': f"Attachment processing error: {str(e)}"}

        # Send raw email
        response = self.client.send_raw_email(
            Source=self.sender_email,
            Destinations=destination['ToAddresses'],
            RawMessage={'Data': msg.as_string()}
        )
        
        return {
            'status': 'success',
            'message_id': response['MessageId'],
            'recipient': destination['ToAddresses'][0]
        }

@email_router.post("/send")
async def send_email(request: EmailRequest):
    service = EmailService()
    result = service.send_email(
        recipient=request.recipient,
        subject=request.subject,
        body=request.body,
        cc=request.cc,
        bcc=request.bcc,
        attachments=request.attachments
    )
    
    if result['status'] == 'error':
        raise HTTPException(
            status_code=400, 
            detail={
                "error": "EmailFailed",
                "message": result['message']
            }
        )
    return {
        "status": "success",
        "data": {
            "message_id": result['message_id'],
            "recipient": result['recipient']
        }
    }

@email_router.post("/send-with-file-attachments")
async def send_email_with_file_attachments(
    recipient: str = Form(...),
    subject: str = Form(...),
    body: str = Form(...),
    cc: Optional[str] = Form(None),
    bcc: Optional[str] = Form(None),
    attachments: List[UploadFile] = File([])
):
    """Send email with file attachments using form data"""
    service = EmailService()
    
    # Process attachments
    attachment_list = []
    for attachment in attachments:
        try:
            content = base64.b64encode(attachment.file.read()).decode('utf-8')
            attachment_list.append({
                'filename': attachment.filename,
                'content': content,
                'content_type': attachment.content_type or 'application/octet-stream'
            })
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "AttachmentProcessingFailed",
                    "message": f"Failed to process attachment {attachment.filename}: {str(e)}"
                }
            )
    
    # Process CC and BCC
    cc_list = cc.split(',') if cc else None
    bcc_list = bcc.split(',') if bcc else None
    
    result = service.send_email(
        recipient=recipient,
        subject=subject,
        body=body,
        cc=cc_list,
        bcc=bcc_list,
        attachments=attachment_list if attachment_list else None
    )
    
    if result['status'] == 'error':
        raise HTTPException(
            status_code=400, 
            detail={
                "error": "EmailFailed",
                "message": result['message']
            }
        )
    return {
        "status": "success",
        "data": {
            "message_id": result['message_id'],
            "recipient": result['recipient'],
            "attachments_count": len(attachment_list)
        }
    }




