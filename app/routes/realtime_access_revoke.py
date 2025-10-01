"""
Real-time Access Revocation System

This module handles real-time access revocation notifications using Supabase broadcasting.
When a user's access/permission is revoked by an admin, it publishes a message to 
Supabase's access_control broadcast channel with ACCESS_REVOKED event type.

Environment Variables Required:
- SUPABASE_URL: Your Supabase project URL
- SUPABASE_ANON_KEY: Your Supabase anonymous key
- SUPABASE_SERVICE_ROLE_KEY: Your Supabase service role key (for server-side operations)

Frontend Integration:
The frontend should listen to the 'access_control' channel for 'ACCESS_REVOKED' events
and check if the current session belongs to the revoked user.
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from pydantic import BaseModel
import httpx
import json

from app.database import get_db
from app import models

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/realtime-access",
    tags=["realtime-access-revoke"],
    responses={404: {"description": "Not found"}},
)

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Validate required environment variables
if not all([SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY]):
    logger.warning(
        "Supabase environment variables not configured. "
        "Real-time access revocation will not work. "
        "Please set SUPABASE_URL, SUPABASE_ANON_KEY, and SUPABASE_SERVICE_ROLE_KEY"
    )


class AccessRevocationPayload(BaseModel):
    """Payload for access revocation events"""
    user_id: int
    revoked_by: str
    revocation_reason: Optional[str] = None
    revoked_at: datetime
    access_type: str = "user_role_access"  # Can be: user_role_access, user_role, etc.


class AccessRevocationResponse(BaseModel):
    """Response for access revocation operations"""
    success: bool
    message: str
    user_id: int
    event_published: bool
    database_updated: bool


async def publish_access_revocation_event(
    user_id: int, 
    revoked_by: str, 
    revocation_reason: Optional[str] = None,
    access_type: str = "user_role_access"
) -> bool:
    """
    Publish access revocation event to Supabase broadcast channel
    
    Args:
        user_id: ID of the user whose access was revoked
        revoked_by: Username/ID of the admin who revoked access
        revocation_reason: Optional reason for revocation
        access_type: Type of access that was revoked
        
    Returns:
        bool: True if event was published successfully, False otherwise
    """
    logger.info(f"Attempting to publish access revocation event for user_id: {user_id}, access_type: {access_type}")
    
    if not all([SUPABASE_URL, SUPABASE_ANON_KEY]):
        logger.error("Supabase configuration missing. Cannot publish access revocation event.")
        return False
    
    try:
        # Prepare the event payload
        event_payload = {
            "event_type": "ACCESS_REVOKED",
            "payload": {
                "user_id": user_id,
                "revoked_by": revoked_by,
                "revocation_reason": revocation_reason,
                "revoked_at": datetime.now(timezone.utc).isoformat(),
                "access_type": access_type
            }
        }
        
        logger.info(f"Prepared event payload: {json.dumps(event_payload, indent=2)}")
        
        # Publish to Supabase broadcast channel
        async with httpx.AsyncClient() as client:
            logger.info(f"Making POST request to {SUPABASE_URL}/rest/v1/rpc/pg_notify")
            response = await client.post(
                f"{SUPABASE_URL}/rest/v1/rpc/pg_notify",
                headers={
                    "apikey": SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal"
                },
                json={
                    "channel": "access_control",
                    "payload": json.dumps(event_payload)
                },
                timeout=10.0
            )
            
            logger.info(f"Supabase response status: {response.status_code}")
            logger.info(f"Supabase response text: {response.text}")
            
            if response.status_code == 200:
                logger.info(f"Access revocation event published successfully for user {user_id}")
                return True
            else:
                logger.error(f"Failed to publish access revocation event: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"Error publishing access revocation event: {str(e)}")
        return False


async def revoke_user_role_access(
    access_id: int,
    revoked_by: str,
    revocation_reason: Optional[str] = None,
    db: Session = None
) -> AccessRevocationResponse:
    """
    Revoke user role access and publish real-time notification
    
    Args:
        access_id: ID of the user role access to revoke
        revoked_by: Username/ID of the admin who revoked access
        revocation_reason: Optional reason for revocation
        db: Database session
        
    Returns:
        AccessRevocationResponse: Result of the revocation operation
    """
    if not db:
        raise HTTPException(status_code=500, detail="Database session required")
    
    logger.info(f"Starting user role access revocation for access_id: {access_id}, revoked_by: {revoked_by}")
    
    try:
        # Find the user role access record
        user_role_access = db.query(models.UserRoleAccess).filter(
            models.UserRoleAccess.id == access_id
        ).first()
        
        if not user_role_access:
            logger.error(f"User role access not found for access_id: {access_id}")
            raise HTTPException(
                status_code=404, 
                detail="User role access not found"
            )
        
        user_id = user_role_access.user_id
        email = user_role_access.email
        logger.info(f"Found user role access record - user_id: {user_id}, role_name: {user_role_access.role_name}, email: {email}")
        
        # Find the user record from users table
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            logger.warning(f"User not found in users table for user_id: {user_id}")
        else:
            logger.info(f"Found user record - user_id: {user.id}, name: {user.name}, email: {user.email}")
        
        # Delete user role access record
        logger.info(f"Deleting user role access record with id: {access_id}")
        db.delete(user_role_access)
        
        # Delete user from users table if found
        if user:
            logger.info(f"Deleting user record with id: {user.id} for email: {user.email}")
            db.delete(user)
        
        # Commit database changes
        db.commit()
        logger.info(f"Successfully deleted user role access record and user record with id: {access_id}")
        
        # Publish real-time event
        logger.info(f"Publishing real-time access revocation event for user_id: {user_id}")
        event_published = await publish_access_revocation_event(
            user_id=user_id,
            revoked_by=revoked_by,
            revocation_reason=revocation_reason,
            access_type="user_role_access"
        )
        
        logger.info(f"Real-time event published: {event_published}")
        
        return AccessRevocationResponse(
            success=True,
            message="User role access revoked and user deleted successfully",
            user_id=user_id,
            event_published=event_published,
            database_updated=True
        )
        
    except HTTPException:
        logger.error(f"HTTPException during user role access revocation for access_id: {access_id}")
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error revoking user role access for access_id {access_id}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {str(e)}"
        )


async def revoke_user_role_access_by_email(
    email: str,
    revoked_by: str,
    revocation_reason: Optional[str] = None,
    db: Session = None
) -> AccessRevocationResponse:
    """
    Revoke user role access by email and delete user from both tables with real-time notification
    
    Args:
        email: Email of the user whose role access should be revoked
        revoked_by: Username/ID of the admin who revoked access
        revocation_reason: Optional reason for revocation
        db: Database session
        
    Returns:
        AccessRevocationResponse: Result of the revocation operation
    """
    if not db:
        raise HTTPException(status_code=500, detail="Database session required")
    
    logger.info(f"Starting user role access revocation and user deletion for email: {email}, revoked_by: {revoked_by}")
    
    try:
        # Test database connection
        try:
            db.execute(text("SELECT 1"))
            logger.info("✅ Database connection test successful")
            
            # Check current database
            try:
                db_name = db.execute(text("SELECT current_database()")).fetchone()[0]
                logger.info(f"Connected to database: {db_name}")
            except Exception as db_name_e:
                logger.warning(f"Could not get database name: {db_name_e}")
                
        except Exception as db_test_e:
            logger.error(f"❌ Database connection test failed: {db_test_e}")
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        # URL decode the email if it contains encoded characters
        import urllib.parse
        decoded_email = urllib.parse.unquote(email)
        if decoded_email != email:
            logger.info(f"URL decoded email from '{email}' to '{decoded_email}'")
            email = decoded_email
        
        # Find the user role access record by email
        logger.info(f"Searching for UserRoleAccess record with email: {email}")
        
        # Debug: Check what tables exist
        try:
            # Try to get table info
            table_names = [table.name for table in db.get_bind().table_names()]
            logger.info(f"Available tables in database: {table_names}")
            
            # Check if our expected tables exist
            expected_tables = ['users', 'user_role_access']
            for table in expected_tables:
                if table in table_names:
                    logger.info(f"✅ Table '{table}' exists")
                else:
                    logger.warning(f"❌ Table '{table}' NOT found")
            
            # Check for common table name variations
            possible_user_tables = ['user', 'Users', 'User', 'USERS']
            possible_role_tables = ['userroleaccess', 'UserRoleAccess', 'USER_ROLE_ACCESS', 'user_role_accesses']
            
            for table in possible_user_tables:
                if table in table_names:
                    logger.info(f"⚠️  Found possible user table: '{table}' (expected 'users')")
                    
            for table in possible_role_tables:
                if table in table_names:
                    logger.info(f"⚠️  Found possible role table: '{table}' (expected 'user_role_access')")
            
            # Check table schemas
            try:
                if 'users' in table_names:
                    user_columns = db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'users'")).fetchall()
                    logger.info(f"Users table columns: {[col[0] for col in user_columns]}")
                    
                if 'user_role_access' in table_names:
                    role_columns = db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'user_role_access'")).fetchall()
                    logger.info(f"UserRoleAccess table columns: {[col[0] for col in role_columns]}")
                    
            except Exception as schema_e:
                logger.warning(f"Could not inspect table schemas: {schema_e}")
                    
        except Exception as e:
            logger.warning(f"Could not get table names: {e}")
        
        # Try case-insensitive search first
        user_role_access = db.query(models.UserRoleAccess).filter(
            func.lower(models.UserRoleAccess.email) == func.lower(email)
        ).first()
        
        if not user_role_access:
            # Try exact match
            user_role_access = db.query(models.UserRoleAccess).filter(
                models.UserRoleAccess.email == email
            ).first()
        
        if user_role_access:
            logger.info(f"✅ Found UserRoleAccess record - ID: {user_role_access.id}, user_id: {user_role_access.user_id}")
        else:
            logger.info(f"❌ No UserRoleAccess record found for email: {email}")
            
            # Debug: Check if there are any records in the table
            try:
                total_records = db.query(models.UserRoleAccess).count()
                logger.info(f"Total records in UserRoleAccess table: {total_records}")
                
                # Check a few sample records
                sample_records = db.query(models.UserRoleAccess).limit(5).all()
                for record in sample_records:
                    logger.info(f"Sample record - ID: {record.id}, email: {record.email}, user_id: {record.user_id}")
                
                # Try raw SQL to see what's actually in the table
                try:
                    raw_result = db.execute(text("SELECT id, email, user_id FROM user_role_access LIMIT 5"))
                    raw_records = raw_result.fetchall()
                    logger.info(f"Raw SQL query results:")
                    for record in raw_records:
                        logger.info(f"  Raw record: {record}")
                        
                    # Also check for the specific email we're looking for
                    search_result = db.execute(
                        text("SELECT id, email, user_id FROM user_role_access WHERE email ILIKE :email"), 
                        {"email": f"%{email}%"}
                    )
                    search_records = search_result.fetchall()
                    if search_records:
                        logger.info(f"Found {len(search_records)} records containing '{email}':")
                        for record in search_records:
                            logger.info(f"  Matching record: {record}")
                    else:
                        logger.info(f"No records found containing '{email}'")
                        
                except Exception as sql_e:
                    logger.warning(f"Raw SQL query failed: {sql_e}")
                    
            except Exception as e:
                logger.warning(f"Could not query UserRoleAccess table: {e}")
        
        # Find the user record from users table first
        logger.info(f"Searching for User record with email: {email}")
        
        # Try case-insensitive search first
        user = db.query(models.User).filter(
            func.lower(models.User.email) == func.lower(email)
        ).first()
        
        if not user:
            # Try exact match
            user = db.query(models.User).filter(
                models.User.email == email
            ).first()
        
        if user:
            logger.info(f"✅ Found User record - ID: {user.id}, name: {user.name}")
        else:
            logger.info(f"❌ No User record found for email: {email}")
            
            # Debug: Check users table with raw SQL
            try:
                raw_result = db.execute(text("SELECT id, name, email FROM users LIMIT 5"))
                raw_records = raw_result.fetchall()
                logger.info(f"Raw SQL query results from users table:")
                for record in raw_records:
                    logger.info(f"  Raw user record: {record}")
                    
                # Also check for the specific email we're looking for
                search_result = db.execute(
                    text("SELECT id, name, email FROM users WHERE email ILIKE :email"), 
                    {"email": f"%{email}%"}
                )
                search_records = search_result.fetchall()
                if search_records:
                    logger.info(f"Found {len(search_records)} user records containing '{email}':")
                    for record in search_records:
                        logger.info(f"  Matching user record: {record}")
                else:
                    logger.info(f"No user records found containing '{email}'")
                    
            except Exception as sql_e:
                logger.warning(f"Raw SQL query on users table failed: {sql_e}")
        
        if not user_role_access and not user:
            logger.error(f"Neither user role access nor user record found for email: {email}")
            raise HTTPException(
                status_code=404, 
                detail={
                    "error": "User not found",
                    "email": email,
                    "message": "No user record or role access record found for this email address"
                }
            )
        
        # If no user role access record exists but user exists, just delete the user
        if not user_role_access and user:
            logger.info(f"No user role access record found, but user exists. Deleting user only for email: {email}")
            
            # First, check if there are any orphaned user_role_access records that might reference this user
            try:
                orphaned_records = db.query(models.UserRoleAccess).filter(
                    models.UserRoleAccess.user_id == user.id
                ).all()
                
                if orphaned_records:
                    logger.info(f"Found {len(orphaned_records)} orphaned user_role_access records for user_id {user.id}, deleting them first")
                    for orphaned_record in orphaned_records:
                        db.delete(orphaned_record)
                        logger.info(f"Deleted orphaned user_role_access record ID: {orphaned_record.id}")
                
                # Also check for any records with null user_id that might cause issues
                null_user_records = db.query(models.UserRoleAccess).filter(
                    models.UserRoleAccess.user_id.is_(None)
                ).all()
                
                if null_user_records:
                    logger.info(f"Found {len(null_user_records)} user_role_access records with null user_id, cleaning them up")
                    for null_record in null_user_records:
                        db.delete(null_record)
                        logger.info(f"Deleted null user_id record ID: {null_record.id}")
                
            except Exception as cleanup_e:
                logger.warning(f"Could not clean up orphaned records: {cleanup_e}")
            
            # Now delete the user
            db.delete(user)
            db.commit()
            logger.info(f"Successfully deleted user record for email: {email}")
            
            # Try to publish a simplified event for user deletion
            try:
                event_published = await publish_access_revocation_event(
                    user_id=user.id,
                    revoked_by=revoked_by,
                    revocation_reason=revocation_reason or "User deleted (no role access record)",
                    access_type="user_deletion_only"
                )
                logger.info(f"User deletion event published: {event_published}")
            except Exception as e:
                logger.warning(f"Failed to publish user deletion event: {str(e)}")
                event_published = False
            
            return AccessRevocationResponse(
                success=True,
                message="User deleted successfully (no role access record found)",
                user_id=user.id,
                event_published=event_published,
                database_updated=True
            )
        
        user_id = user_role_access.user_id
        access_id = user_role_access.id
        logger.info(f"Found user role access record - user_id: {user_id}, access_id: {access_id}, role_name: {user_role_access.role_name}")
        
        # Find the user record from users table (we already found it above, but let's use the existing one)
        if not user:
            user = db.query(models.User).filter(models.User.email == email).first()
            if not user:
                logger.warning(f"User not found in users table for email: {email}")
            else:
                logger.info(f"Found user record - user_id: {user.id}, name: {user.name}")
        
        # Delete user role access record
        logger.info(f"Deleting user role access record with id: {access_id} for email: {email}")
        db.delete(user_role_access)
        
        # Delete user from users table if found
        if user:
            logger.info(f"Deleting user record with id: {user.id} for email: {email}")
            
            # Check for any other orphaned user_role_access records for this user
            try:
                other_orphaned_records = db.query(models.UserRoleAccess).filter(
                    models.UserRoleAccess.user_id == user.id,
                    models.UserRoleAccess.id != access_id  # Exclude the one we already deleted
                ).all()
                
                if other_orphaned_records:
                    logger.info(f"Found {len(other_orphaned_records)} additional orphaned user_role_access records for user_id {user.id}, deleting them")
                    for orphaned_record in other_orphaned_records:
                        db.delete(orphaned_record)
                        logger.info(f"Deleted additional orphaned record ID: {orphaned_record.id}")
                        
            except Exception as cleanup_e:
                logger.warning(f"Could not clean up additional orphaned records: {cleanup_e}")
            
            db.delete(user)
        
        # Commit database changes
        db.commit()
        logger.info(f"Successfully deleted user role access record and user record for email: {email}")
        
        # Publish real-time event
        logger.info(f"Publishing real-time access revocation event for user_id: {user_id}")
        event_published = await publish_access_revocation_event(
            user_id=user_id,
            revoked_by=revoked_by,
            revocation_reason=revocation_reason,
            access_type="user_role_access"
        )
        
        logger.info(f"Real-time event published: {event_published}")
        
        return AccessRevocationResponse(
            success=True,
            message="User role access revoked and user deleted successfully by email",
            user_id=user_id,
            event_published=event_published,
            database_updated=True
        )
        
    except HTTPException:
        logger.error(f"HTTPException during user role access revocation for email: {email}")
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error revoking user role access for email {email}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {str(e)}"
        )


async def revoke_multiple_user_role_access_by_email(
    emails: list[str],
    revoked_by: str,
    revocation_reason: Optional[str] = None,
    db: Session = None
) -> Dict[str, Any]:
    """
    Revoke user role access for multiple users by email and delete users from both tables with real-time notification
    
    Args:
        emails: List of emails of users whose role access should be revoked
        revoked_by: Username/ID of the admin who revoked access
        revocation_reason: Optional reason for revocation
        db: Database session
        
    Returns:
        Dict containing results of the bulk revocation operation
    """
    if not db:
        raise HTTPException(status_code=500, detail="Database session required")
    
    if not emails:
        raise HTTPException(status_code=400, detail="At least one email is required")
    
    logger.info(f"Starting bulk user role access revocation for {len(emails)} emails, revoked_by: {revoked_by}")
    
    results = {
        "success": True,
        "total_emails": len(emails),
        "successful_deletions": 0,
        "failed_deletions": 0,
        "errors": [],
        "event_published_count": 0
    }
    
    try:
        for email in emails:
            email = email.strip()  # Remove any whitespace
            if not email:  # Skip empty emails
                continue
                
            try:
                logger.info(f"Processing email: {email}")
                
                # Find the user role access record by email
                logger.info(f"Searching for UserRoleAccess record with email: {email}")
                
                # Try case-insensitive search first
                user_role_access = db.query(models.UserRoleAccess).filter(
                    func.lower(models.UserRoleAccess.email) == func.lower(email)
                ).first()
                
                if not user_role_access:
                    # Try exact match
                    user_role_access = db.query(models.UserRoleAccess).filter(
                        models.UserRoleAccess.email == email
                    ).first()
                
                if user_role_access:
                    logger.info(f"✅ Found UserRoleAccess record - ID: {user_role_access.id}, user_id: {user_role_access.user_id}")
                else:
                    logger.info(f"❌ No UserRoleAccess record found for email: {email}")
                
                # Find the user record from users table
                logger.info(f"Searching for User record with email: {email}")
                
                # Try case-insensitive search first
                user = db.query(models.User).filter(
                    func.lower(models.User.email) == func.lower(email)
                ).first()
                
                if not user:
                    # Try exact match
                    user = db.query(models.User).filter(
                        models.User.email == email
                    ).first()
                
                if user:
                    logger.info(f"✅ Found User record - ID: {user.id}, name: {user.name}")
                else:
                    logger.info(f"❌ No User record found for email: {email}")
                
                if not user_role_access and not user:
                    logger.warning(f"Neither user role access nor user record found for email: {email}")
                    results["errors"].append({
                        "email": email,
                        "error": "User not found"
                    })
                    results["failed_deletions"] += 1
                    continue
                
                # If no user role access record exists but user exists, just delete the user
                if not user_role_access and user:
                    logger.info(f"No user role access record found, but user exists. Deleting user only for email: {email}")
                    
                    # First, check if there are any orphaned user_role_access records that might reference this user
                    try:
                        orphaned_records = db.query(models.UserRoleAccess).filter(
                            models.UserRoleAccess.user_id == user.id
                        ).all()
                        
                        if orphaned_records:
                            logger.info(f"Found {len(orphaned_records)} orphaned user_role_access records for user_id {user.id}, deleting them first")
                            for orphaned_record in orphaned_records:
                                db.delete(orphaned_record)
                                logger.info(f"Deleted orphaned user_role_access record ID: {orphaned_record.id}")
                        
                        # Also check for any records with null user_id that might cause issues
                        null_user_records = db.query(models.UserRoleAccess).filter(
                            models.UserRoleAccess.user_id.is_(None)
                        ).all()
                        
                        if null_user_records:
                            logger.info(f"Found {len(null_user_records)} user_role_access records with null user_id, cleaning them up")
                            for null_record in null_user_records:
                                db.delete(null_record)
                                logger.info(f"Deleted null user_id record ID: {null_record.id}")
                        
                    except Exception as cleanup_e:
                        logger.warning(f"Could not clean up orphaned records: {cleanup_e}")
                    
                    # Now delete the user
                    db.delete(user)
                    results["successful_deletions"] += 1
                    logger.info(f"Successfully processed email (user only): {email}")
                    continue
                
                user_id = user_role_access.user_id
                access_id = user_role_access.id
                logger.info(f"Found user role access record - user_id: {user_id}, access_id: {access_id}, role_name: {user_role_access.role_name}")
                
                # User record was already found above, just log if it exists
                if not user:
                    logger.warning(f"User not found in users table for email: {email}")
                else:
                    logger.info(f"Found user record - user_id: {user.id}, name: {user.name}")
                
                # Delete user role access record
                logger.info(f"Deleting user role access record with id: {access_id} for email: {email}")
                db.delete(user_role_access)
                
                # Delete user from users table if found
                if user:
                    logger.info(f"Deleting user record with id: {user.id} for email: {email}")
                    db.delete(user)
                
                # Publish real-time event
                logger.info(f"Publishing real-time access revocation event for user_id: {user_id}")
                event_published = await publish_access_revocation_event(
                    user_id=user_id,
                    revoked_by=revoked_by,
                    revocation_reason=revocation_reason,
                    access_type="user_role_access"
                )
                
                if event_published:
                    results["event_published_count"] += 1
                
                results["successful_deletions"] += 1
                logger.info(f"Successfully processed email: {email}")
                
            except Exception as e:
                logger.error(f"Error processing email {email}: {str(e)}")
                results["errors"].append({
                    "email": email,
                    "error": str(e)
                })
                results["failed_deletions"] += 1
                # Continue with other emails instead of failing completely
        
        # Commit all database changes at once
        if results["successful_deletions"] > 0:
            db.commit()
            logger.info(f"Committed {results['successful_deletions']} successful deletions to database")
        
        # Update overall success status
        if results["failed_deletions"] > 0:
            results["success"] = False
            logger.warning(f"Bulk deletion completed with {results['failed_deletions']} failures")
        else:
            logger.info("Bulk deletion completed successfully for all emails")
        
        return results
        
    except Exception as e:
        db.rollback()
        logger.error(f"Critical error during bulk user role access revocation: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Critical error during bulk deletion: {str(e)}"
        )


async def revoke_user_role(
    user_role_id: int,
    revoked_by: str,
    revocation_reason: Optional[str] = None,
    db: Session = None
) -> AccessRevocationResponse:
    """
    Revoke user role and publish real-time notification
    
    Args:
        user_role_id: ID of the user role to revoke
        revoked_by: Username/ID of the admin who revoked access
        revocation_reason: Optional reason for revocation
        db: Database session
        
    Returns:
        AccessRevocationResponse: Result of the revocation operation
    """
    if not db:
        raise HTTPException(status_code=500, detail="Database session required")
    
    logger.info(f"Starting user role revocation for user_role_id: {user_role_id}, revoked_by: {revoked_by}")
    
    try:
        # Find the user role record
        user_role = db.query(models.UserRole).filter(
            models.UserRole.id == user_role_id
        ).first()
        
        if not user_role:
            logger.error(f"User role not found for user_role_id: {user_role_id}")
            raise HTTPException(
                status_code=404, 
                detail="User role not found"
            )
        
        user_id = user_role.user_id
        logger.info(f"Found user role record - user_id: {user_id}, role_id: {user_role.role_id}")
        
        # Delete the user role (this is the existing behavior)
        logger.info(f"Deleting user role record with id: {user_role_id}")
        db.delete(user_role)
        db.commit()
        logger.info(f"Successfully deleted user role record with id: {user_role_id}")
        
        # Publish real-time event
        logger.info(f"Publishing real-time access revocation event for user_id: {user_id}")
        event_published = await publish_access_revocation_event(
            user_id=user_id,
            revoked_by=revoked_by,
            revocation_reason=revocation_reason,
            access_type="user_role"
        )
        
        logger.info(f"Real-time event published: {event_published}")
        
        return AccessRevocationResponse(
            success=True,
            message="User role revoked successfully",
            user_id=user_id,
            event_published=event_published,
            database_updated=True
        )
        
    except HTTPException:
        logger.error(f"HTTPException during user role revocation for user_role_id: {user_role_id}")
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error revoking user role for user_role_id {user_role_id}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/revoke-user-role-access/{access_id}", response_model=AccessRevocationResponse)
async def revoke_user_role_access_endpoint(
    access_id: int,
    revocation_data: AccessRevocationPayload,
    db: Session = Depends(get_db)
):
    """
    Revoke user role access with real-time notification
    
    This endpoint revokes a user's role access and publishes a real-time event
    to the frontend so it can immediately check if the current session belongs
    to the revoked user.
    """
    return await revoke_user_role_access(
        access_id=access_id,
        revoked_by=revocation_data.revoked_by,
        revocation_reason=revocation_data.revocation_reason,
        db=db
    )


@router.post("/revoke-user-role/{user_role_id}", response_model=AccessRevocationResponse)
async def revoke_user_role_endpoint(
    user_role_id: int,
    revocation_data: AccessRevocationPayload,
    db: Session = Depends(get_db)
):
    """
    Revoke user role with real-time notification
    
    This endpoint revokes a user's role and publishes a real-time event
    to the frontend so it can immediately check if the current session belongs
    to the revoked user.
    """
    return await revoke_user_role(
        user_role_id=user_role_id,
        revoked_by=revocation_data.revoked_by,
        revocation_reason=revocation_data.revocation_reason,
        db=db
    )


@router.get("/health", response_model=Dict[str, Any])
async def health_check():
    """
    Health check endpoint for real-time access revocation system
    
    Returns:
        Dict containing system status and configuration
    """
    supabase_configured = all([
        SUPABASE_URL, 
        SUPABASE_ANON_KEY, 
        SUPABASE_SERVICE_ROLE_KEY
    ])
    
    return {
        "status": "healthy",
        "supabase_configured": supabase_configured,
        "supabase_url": SUPABASE_URL if SUPABASE_URL else None,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/debug/user-role-access/{access_id}", response_model=Dict[str, Any])
async def debug_user_role_access(
    access_id: int = Path(..., gt=0),
    db: Session = Depends(get_db)
):
    """
    Debug endpoint to check the state of a user role access record
    
    Returns:
        Dict containing the record details or error information
    """
    logger.info(f"Debug request for user role access id: {access_id}")
    
    try:
        user_role_access = db.query(models.UserRoleAccess).filter(
            models.UserRoleAccess.id == access_id
        ).first()
        
        if user_role_access:
            return {
                "found": True,
                "id": user_role_access.id,
                "user_id": user_role_access.user_id,
                "role_name": user_role_access.role_name,
                "is_active": user_role_access.is_active,
                "created_at": user_role_access.created_at.isoformat() if user_role_access.created_at else None,
                "updated_at": user_role_access.updated_at.isoformat() if user_role_access.updated_at else None,
                "created_by": user_role_access.created_by,
                "updated_by": user_role_access.updated_by
            }
        else:
            return {
                "found": False,
                "access_id": access_id,
                "message": "User role access record not found"
            }
            
    except Exception as e:
        logger.error(f"Error in debug endpoint: {str(e)}")
        return {
            "found": False,
            "error": str(e),
            "access_id": access_id
        }


# Export functions for use in other modules
__all__ = [
    "revoke_user_role_access",
    "revoke_user_role", 
    "publish_access_revocation_event",
    "AccessRevocationPayload",
    "AccessRevocationResponse"
]


@router.get("/config-check", response_model=Dict[str, Any])
async def check_supabase_config():
    """
    Check if Supabase configuration is properly loaded
    
    Returns:
        Dict containing configuration status and details
    """
    logger.info("Checking Supabase configuration...")
    
    config_status = {
        "supabase_url": SUPABASE_URL,
        "supabase_anon_key": SUPABASE_ANON_KEY[:20] + "..." if SUPABASE_ANON_KEY else None,
        "supabase_service_role_key": SUPABASE_SERVICE_ROLE_KEY[:20] + "..." if SUPABASE_SERVICE_ROLE_KEY else None,
        "all_configured": all([SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY]),
        "url_valid": bool(SUPABASE_URL and SUPABASE_URL.startswith("https://")),
        "anon_key_valid": bool(SUPABASE_ANON_KEY and SUPABASE_ANON_KEY.startswith("eyJ")),
        "service_key_valid": bool(SUPABASE_SERVICE_ROLE_KEY and SUPABASE_SERVICE_ROLE_KEY.startswith("eyJ"))
    }
    
    logger.info(f"Configuration check result: {config_status}")
    return config_status 