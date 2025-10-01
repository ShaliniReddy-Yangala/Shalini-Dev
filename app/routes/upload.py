from contextlib import asynccontextmanager
import os
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from botocore.exceptions import ClientError
from .. import models, schemas, database
import boto3

# AWS Config - Use environment variables with fallbacks
AWS_REGION = os.getenv("AWS_REGION", "ap-south-2")
S3_BUCKET = os.getenv("S3_BUCKET", "upload-media00")

# Initialize S3 client without explicit endpoint_url to let boto3 handle region correctly
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=AWS_REGION,
    endpoint_url=f"https://s3.{AWS_REGION}.amazonaws.com"
)

class UploadRequest(BaseModel):
    file_name: str
    content_type: str

# Allowed file types and max size
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

router = APIRouter(prefix="/upload", tags=["upload"])

@router.post("/generate-presigned-url", status_code=201)
def generate_presigned_url(data: UploadRequest):
    print(f"Generating presigned URL in region {AWS_REGION} for bucket {S3_BUCKET}")
    try:
        url = s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": S3_BUCKET,
                "Key": data.file_name,
                "ContentType": data.content_type,
            },
            ExpiresIn=3600  # 1 hour
        )
        print(f"Generated URL: {url}")
        return {"url": url}
    except ClientError as e:
        print(f"Error generating presigned URL: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# App initialization with startup event
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create required S3 bucket if it doesn't exist
    try:
        print(f"Checking if bucket {S3_BUCKET} exists in region {AWS_REGION}")
        s3_client.head_bucket(Bucket=S3_BUCKET)
        print(f"Bucket {S3_BUCKET} exists")
    except ClientError as e:
        print(f"Bucket {S3_BUCKET} does not exist, creating it")
        try:
            # Create bucket with consistent region
            s3_client.create_bucket(
                Bucket=S3_BUCKET,
                CreateBucketConfiguration={"LocationConstraint": AWS_REGION}
            )
            print(f"Bucket {S3_BUCKET} created in {AWS_REGION}")
            
            # Set bucket CORS policy
            cors_config = {
                "CORSRules": [
                    {
                        "AllowedHeaders": ["*"],
                        "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
                        "AllowedOrigins": ["*"],
                        "MaxAgeSeconds": 3000
                    }
                ]
            }
            s3_client.put_bucket_cors(Bucket=S3_BUCKET, CORSConfiguration=cors_config)
            print("CORS configuration set for bucket")
        except ClientError as create_error:
            print(f"Failed to create bucket: {str(create_error)}")
    
    yield
