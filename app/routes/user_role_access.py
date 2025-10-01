from fastapi import APIRouter, status
from app.schemas import (
    UserRoleAccessResponse,
    PaginatedUserRoleAccess,
    UserAccessSummary,
    RoleAccessDetails,
    UserRoleAccessCreate,
    UserRoleAccessFilter,
    UserRoleAccessUpdate,
)
from app.database import get_db
from sqlalchemy.orm import Session
from fastapi import Depends, Request
from sqlalchemy import text
from app.models import User
from app.middleware.session_validator import get_current_user

# Re-use the existing endpoint callables from the candidates module
from app.routes.candidates import (
    create_user_role_access,
    get_all_user_role_access,
    get_user_role_access,
    get_user_role_access_by_user_id,
    update_user_role_access,
    delete_user_role_access,
    get_user_access_summary,
    get_user_access_details,
)

router = APIRouter(
    prefix="/user-role-access",
    tags=["user-role-access"],
    responses={404: {"description": "Not found"}},
)

# Wrapper functions to ensure unique callables and unique operation IDs

@router.post("", response_model=UserRoleAccessResponse, status_code=status.HTTP_201_CREATED)
async def create_user_role_access_root(
    request: Request,
    user_role_access: UserRoleAccessCreate,
    db: Session = Depends(get_db),
):
    import logging
    import traceback
    from sqlalchemy.exc import SQLAlchemyError
    
    logger = logging.getLogger(__name__)
    
    try:
        # Get the authenticated user from session validator
        user_data = get_current_user(request)
        if not user_data:
            from fastapi import HTTPException
            raise HTTPException(status_code=401, detail="Authentication required")
        
        current_user = user_data.get('email', 'taadmin')
        logger.info(f"🔍 Starting user-role-access creation for user_id: {user_role_access.user_id}")
        logger.info(f"🔍 Current authenticated user: {current_user}")
        
        # Ensure the referenced user exists in the public.users table.
        logger.info(f"🔍 Checking if user exists in public.users table...")
        public_user = db.query(User).filter(User.id == user_role_access.user_id).first()
        
        if public_user is None:
            logger.info(f"🔍 User not found in public.users, checking auth.users...")
            # Try to fetch from auth schema
            auth_query = text(
                """
                SELECT id, name, email, department_id
                FROM auth.users
                WHERE id = :uid
                """
            )
            
            try:
                auth_row = db.execute(auth_query, {"uid": user_role_access.user_id}).fetchone()
                logger.info(f"🔍 Auth query result: {auth_row}")
                
                if auth_row:
                    logger.info(f"🔍 User found in auth.users, creating shadow entry in public.users...")
                    logger.info(f"🔍 Auth user data: id={auth_row.id}, name={auth_row.name}, email={auth_row.email}, department_id={auth_row.department_id}")
                    
                    # Create a shadow entry in public.users so the rest of the code works
                    public_user = User(
                        id=auth_row.id,
                        name=auth_row.name,
                        email=auth_row.email,
                        department=auth_row.department_id,
                    )
                    
                    logger.info(f"🔍 Created User object: {public_user}")
                    logger.info(f"🔍 About to add user to database...")
                    
                    db.add(public_user)
                    logger.info(f"🔍 User added to session, about to commit...")
                    
                    db.commit()
                    logger.info(f"🔍 Commit successful, refreshing user object...")
                    
                    db.refresh(public_user)
                    logger.info(f"🔍 User object refreshed successfully")
                    
                else:
                    logger.warning(f"❌ User not found in auth.users table either")
                    # Still not found → let original logic raise 404 for consistency
                    pass
                    
            except SQLAlchemyError as db_error:
                logger.error(f"💥 DATABASE ERROR during auth query:")
                logger.error(f"💥 Error type: {type(db_error).__name__}")
                logger.error(f"💥 Error message: {str(db_error)}")
                logger.error(f"💥 Full traceback:")
                logger.error(traceback.format_exc())
                
                # Re-raise with detailed error information
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "Database error during user lookup",
                        "error_type": type(db_error).__name__,
                        "error_message": str(db_error),
                        "operation": "auth_users_query",
                        "user_id": user_role_access.user_id
                    }
                )
                
        else:
            logger.info(f"✅ User already exists in public.users table")

        logger.info(f"🔍 Proceeding to create_user_role_access function...")
        return await create_user_role_access(
            user_role_access=user_role_access,
            db=db,
            current_user=current_user,
        )
        
    except SQLAlchemyError as db_error:
        logger.error(f"💥 DATABASE ERROR in create_user_role_access_root:")
        logger.error(f"💥 Error type: {type(db_error).__name__}")
        logger.error(f"💥 Error message: {str(db_error)}")
        logger.error(f"💥 Full traceback:")
        logger.error(traceback.format_exc())
        
        # Re-raise with detailed error information
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Database error in user-role-access creation",
                "error_type": type(db_error).__name__,
                "error_message": str(db_error),
                "operation": "create_user_role_access",
                "user_id": user_role_access.user_id if hasattr(user_role_access, 'user_id') else 'unknown'
            }
        )
        
    except Exception as e:
        logger.error(f"💥 UNEXPECTED ERROR in create_user_role_access_root:")
        logger.error(f"💥 Error type: {type(e).__name__}")
        logger.error(f"💥 Error message: {str(e)}")
        logger.error(f"💥 Full traceback:")
        logger.error(traceback.format_exc())
        
        # Re-raise with detailed error information
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Unexpected error in user-role-access creation",
                "error_type": type(e).__name__,
                "error_message": str(e),
                "operation": "create_user_role_access",
                "user_id": user_role_access.user_id if hasattr(user_role_access, 'user_id') else 'unknown'
            }
        )

@router.get("", response_model=PaginatedUserRoleAccess)
async def get_all_user_role_access_root(
    filters: UserRoleAccessFilter = Depends(),
    db: Session = Depends(get_db),
):
    return await get_all_user_role_access(filters=filters, db=db)

@router.get("/{access_id}", response_model=UserRoleAccessResponse)
async def get_user_role_access_root(
    access_id: int,
    db: Session = Depends(get_db),
):
    return await get_user_role_access(access_id=access_id, db=db)

@router.get("/user/{user_id}", response_model=UserRoleAccessResponse)
async def get_user_role_access_by_user_id_root(
    user_id: int,
    db: Session = Depends(get_db),
):
    return await get_user_role_access_by_user_id(user_id=user_id, db=db)

@router.put("/{access_id}", response_model=UserRoleAccessResponse)
async def update_user_role_access_root(
    request: Request,
    access_id: int,
    user_role_access: UserRoleAccessUpdate,
    db: Session = Depends(get_db),
):
    import logging
    import traceback
    from sqlalchemy.exc import SQLAlchemyError
    
    logger = logging.getLogger(__name__)
    
    try:
        # Get the authenticated user from session validator
        user_data = get_current_user(request)
        if not user_data:
            from fastapi import HTTPException
            raise HTTPException(status_code=401, detail="Authentication required")
        
        current_user = user_data.get('email', 'taadmin')
        logger.info(f"🔍 Starting user-role-access update for access_id: {access_id}")
        logger.info(f"🔍 Current authenticated user: {current_user}")
        
        return await update_user_role_access(
            access_id=access_id,
            user_role_access=user_role_access,
            db=db,
            current_user=current_user,
        )
        
    except SQLAlchemyError as db_error:
        logger.error(f"💥 DATABASE ERROR in update_user_role_access_root:")
        logger.error(f"💥 Error type: {type(db_error).__name__}")
        logger.error(f"💥 Error message: {str(db_error)}")
        logger.error(f"💥 Full traceback:")
        logger.error(traceback.format_exc())
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Database error in user-role-access update",
                "error_type": type(db_error).__name__,
                "error_message": str(db_error),
                "operation": "update_user_role_access",
                "access_id": access_id
            }
        )
        
    except Exception as e:
        logger.error(f"💥 UNEXPECTED ERROR in update_user_role_access_root:")
        logger.error(f"💥 Error type: {type(e).__name__}")
        logger.error(f"💥 Error message: {str(e)}")
        logger.error(f"💥 Full traceback:")
        logger.error(traceback.format_exc())
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Unexpected error in user-role-access update",
                "error_type": type(e).__name__,
                "error_message": str(e),
                "operation": "update_user_role_access",
                "access_id": access_id
            }
        )

@router.delete("/{access_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_role_access_root(
    request: Request,
    access_id: int,
    db: Session = Depends(get_db),
):
    import logging
    import traceback
    from sqlalchemy.exc import SQLAlchemyError
    
    logger = logging.getLogger(__name__)
    
    try:
        # Get the authenticated user from session validator
        user_data = get_current_user(request)
        if not user_data:
            from fastapi import HTTPException
            raise HTTPException(status_code=401, detail="Authentication required")
        
        current_user = user_data.get('email', 'taadmin')
        logger.info(f"🔍 Starting user-role-access deletion for access_id: {access_id}")
        logger.info(f"🔍 Current authenticated user: {current_user}")
        
        return await delete_user_role_access(access_id=access_id, db=db, current_user=current_user)
        
    except SQLAlchemyError as db_error:
        logger.error(f"💥 DATABASE ERROR in delete_user_role_access_root:")
        logger.error(f"💥 Error type: {type(db_error).__name__}")
        logger.error(f"💥 Error message: {str(db_error)}")
        logger.error(f"💥 Full traceback:")
        logger.error(traceback.format_exc())
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Database error in user-role-access deletion",
                "error_type": type(db_error).__name__,
                "error_message": str(db_error),
                "operation": "delete_user_role_access",
                "access_id": access_id
            }
        )
        
    except Exception as e:
        logger.error(f"💥 UNEXPECTED ERROR in delete_user_role_access_root:")
        logger.error(f"💥 Error type: {type(e).__name__}")
        logger.error(f"💥 Error message: {str(e)}")
        logger.error(f"💥 Full traceback:")
        logger.error(traceback.format_exc())
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Unexpected error in user-role-access deletion",
                "error_type": type(e).__name__,
                "error_message": str(e),
                "operation": "delete_user_role_access",
                "access_id": access_id
            }
        )

@router.delete("/by-email/{email}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_role_access_by_email_root(
    request: Request,
    email: str,
    db: Session = Depends(get_db),
):
    """Delete user role access and user from both tables by email with real-time notification"""
    import logging
    import traceback
    from sqlalchemy.exc import SQLAlchemyError
    from fastapi import HTTPException
    
    logger = logging.getLogger(__name__)
    
    try:
        # Get the authenticated user from session validator
        user_data = get_current_user(request)
        if not user_data:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        current_user = user_data.get('email', 'taadmin')
        logger.info(f"🔍 Starting user-role-access deletion by email: {email}")
        logger.info(f"🔍 Current authenticated user: {current_user}")
        
        from app.routes.realtime_access_revoke import revoke_user_role_access_by_email
        
        return await revoke_user_role_access_by_email(
            email=email,
            revoked_by=current_user,
            revocation_reason="Access revoked by admin",
            db=db
        )
        
    except HTTPException as http_error:
        # Re-raise HTTPException without wrapping it in a 500 error
        logger.info(f"HTTPException in delete_user_role_access_by_email_root: {http_error.status_code} - {http_error.detail}")
        raise
        
    except SQLAlchemyError as db_error:
        logger.error(f"💥 DATABASE ERROR in delete_user_role_access_by_email_root:")
        logger.error(f"💥 Error type: {type(db_error).__name__}")
        logger.error(f"💥 Error message: {str(db_error)}")
        logger.error(f"💥 Full traceback:")
        logger.error(traceback.format_exc())
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Database error in user-role-access deletion by email",
                "error_type": type(db_error).__name__,
                "error_message": str(db_error),
                "operation": "delete_user_role_access_by_email",
                "email": email
            }
        )
        
    except Exception as e:
        logger.error(f"💥 UNEXPECTED ERROR in delete_user_role_access_by_email_root:")
        logger.error(f"💥 Error type: {type(e).__name__}")
        logger.error(f"💥 Error message: {str(e)}")
        logger.error(f"💥 Full traceback:")
        logger.error(traceback.format_exc())
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Unexpected error in user-role-access deletion by email",
                "error_type": type(e).__name__,
                "error_message": str(e),
                "operation": "delete_user_role_access_by_email",
                "email": email
            }
        )

@router.delete("/by-emails/{emails}", status_code=status.HTTP_200_OK)
async def delete_multiple_user_role_access_by_email_root(
    request: Request,
    emails: str,
    db: Session = Depends(get_db),
):
    """Delete multiple user role accesses and users from both tables by comma-separated emails with real-time notification"""
    import logging
    import traceback
    from sqlalchemy.exc import SQLAlchemyError
    from fastapi import HTTPException
    
    logger = logging.getLogger(__name__)
    
    try:
        # Get the authenticated user from session validator
        user_data = get_current_user(request)
        if not user_data:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        current_user = user_data.get('email', 'taadmin')
        
        # URL decode the emails string first, then parse comma-separated emails
        import urllib.parse
        decoded_emails = urllib.parse.unquote(emails)
        logger.info(f"URL decoded emails from '{emails}' to '{decoded_emails}'")
        
        # Parse comma-separated emails
        email_list = [email.strip() for email in decoded_emails.split(',') if email.strip()]
        
        if not email_list:
            raise HTTPException(status_code=400, detail="At least one valid email is required")
        
        logger.info(f"🔍 Starting bulk user-role-access deletion for {len(email_list)} emails: {email_list}")
        logger.info(f"🔍 Current authenticated user: {current_user}")
        
        from app.routes.realtime_access_revoke import revoke_multiple_user_role_access_by_email
        
        result = await revoke_multiple_user_role_access_by_email(
            emails=email_list,
            revoked_by=current_user,
            revocation_reason="Access revoked by admin",
            db=db
        )
        
        return result
        
    except HTTPException as http_error:
        # Re-raise HTTPException without wrapping it in a 500 error
        logger.info(f"HTTPException in delete_multiple_user_role_access_by_email_root: {http_error.status_code} - {http_error.detail}")
        raise
        
    except SQLAlchemyError as db_error:
        logger.error(f"💥 DATABASE ERROR in delete_multiple_user_role_access_by_email_root:")
        logger.error(f"💥 Error type: {type(db_error).__name__}")
        logger.error(f"💥 Error message: {str(db_error)}")
        logger.error(f"💥 Full traceback:")
        logger.error(traceback.format_exc())
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Database error in bulk user-role-access deletion by emails",
                "error_type": type(db_error).__name__,
                "error_message": str(db_error),
                "operation": "delete_multiple_user_role_access_by_email",
                "emails": emails
            }
        )
        
    except Exception as e:
        logger.error(f"💥 UNEXPECTED ERROR in delete_multiple_user_role_access_by_email_root:")
        logger.error(f"💥 Error type: {type(e).__name__}")
        logger.error(f"💥 Error message: {str(e)}")
        logger.error(f"💥 Full traceback:")
        logger.error(traceback.format_exc())
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Unexpected error in bulk user-role-access deletion by emails",
                "error_type": type(e).__name__,
                "error_message": str(e),
                "operation": "delete_multiple_user_role_access_by_email",
                "emails": emails
            }
        )

@router.get("/{access_id}/summary", response_model=UserAccessSummary)
async def get_user_access_summary_root(
    access_id: int,
    db: Session = Depends(get_db),
):
    return await get_user_access_summary(access_id=access_id, db=db)

@router.get("/{access_id}/details", response_model=RoleAccessDetails)
async def get_user_access_details_root(
    access_id: int,
    db: Session = Depends(get_db),
):
    return await get_user_access_details(access_id=access_id, db=db) 