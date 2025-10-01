from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db
from app.schemas import AuthUserResponse, AuthUserListResponse

router = APIRouter(
    prefix="/auth-users",
    tags=["auth-users"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=AuthUserListResponse)
def get_all_auth_users(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    search: str = Query(None, description="Search by name or email")
):
    """
    Get all users from auth.users table with optional pagination and search.
    
    This endpoint queries the auth schema directly to get user information
    including id, name, email, phone, department_id, is_system_admin, and is_department_head.
    """
    try:
        # Build the base query
        base_query = """
            SELECT id, name, email, phone, department_id, is_system_admin, is_department_head
            FROM auth.users
        """
        
        # Add search condition if provided
        where_clause = ""
        params = {}
        if search:
            where_clause = " WHERE LOWER(name) LIKE LOWER(:search) OR LOWER(email) LIKE LOWER(:search)"
            params['search'] = f"%{search}%"
        
        # Get total count
        count_query = f"SELECT COUNT(*) as total FROM auth.users{where_clause}"
        count_result = db.execute(text(count_query), params).fetchone()
        total = count_result.total if count_result else 0
        
        # Get paginated results
        data_query = f"""
            {base_query}{where_clause}
            ORDER BY name
            LIMIT :limit OFFSET :skip
        """
        params.update({'limit': limit, 'skip': skip})
        
        result = db.execute(text(data_query), params)
        
        # Convert to response format
        users = []
        for row in result:
            user = AuthUserResponse(
                id=row.id,
                name=row.name,
                email=row.email,
                phone=row.phone,
                department_id=row.department_id,
                is_system_admin=row.is_system_admin,
                is_department_head=row.is_department_head
            )
            users.append(user)
        
        return AuthUserListResponse(users=users, total=total)
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error fetching users from auth schema: {str(e)}"
        )


@router.get("/all", response_model=List[AuthUserResponse])
def get_all_auth_users_simple(db: Session = Depends(get_db)):
    """
    Get all users from auth.users table without pagination (for simple use cases).
    
    This endpoint queries the auth schema directly to get user information
    including id, name, email, phone, department_id, is_system_admin, and is_department_head.
    """
    try:
        query = """
            SELECT id, name, email, phone, department_id, is_system_admin, is_department_head
            FROM auth.users
            ORDER BY name
        """
        
        result = db.execute(text(query))
        
        # Convert to response format
        users = []
        for row in result:
            user = AuthUserResponse(
                id=row.id,
                name=row.name,
                email=row.email,
                phone=row.phone,
                department_id=row.department_id,
                is_system_admin=row.is_system_admin,
                is_department_head=row.is_department_head
            )
            users.append(user)
        
        return users
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error fetching users from auth schema: {str(e)}"
        )


@router.get("/{user_id}", response_model=AuthUserResponse)
def get_auth_user_by_id(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific user from auth.users table by ID.
    """
    try:
        query = """
            SELECT id, name, email, phone, department_id, is_system_admin, is_department_head
            FROM auth.users
            WHERE id = :user_id
        """
        
        result = db.execute(text(query), {'user_id': user_id}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="User not found")
        
        return AuthUserResponse(
            id=result.id,
            name=result.name,
            email=result.email,
            phone=result.phone,
            department_id=result.department_id,
            is_system_admin=result.is_system_admin,
            is_department_head=result.is_department_head
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error fetching user from auth schema: {str(e)}"
        )


@router.get("/by-email/{email}", response_model=AuthUserResponse)
def get_auth_user_by_email(
    email: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific user from auth.users table by email.
    """
    try:
        query = """
            SELECT id, name, email, phone, department_id, is_system_admin, is_department_head
            FROM auth.users
            WHERE LOWER(email) = LOWER(:email)
        """
        
        result = db.execute(text(query), {'email': email}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="User not found")
        
        return AuthUserResponse(
            id=result.id,
            name=result.name,
            email=result.email,
            phone=result.phone,
            department_id=result.department_id,
            is_system_admin=result.is_system_admin,
            is_department_head=result.is_department_head
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error fetching user from auth schema: {str(e)}"
        )


@router.get("/getid/{email}")
def get_user_id_by_email(
    email: str,
    db: Session = Depends(get_db)
):
    """
    Get user ID from auth.users table by email.
    Returns only the user ID associated with the given email.
    """
    try:
        query = """
            SELECT id
            FROM auth.users
            WHERE LOWER(email) = LOWER(:email)
        """
        
        result = db.execute(text(query), {'email': email}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {"user_id": result.id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error fetching user ID from auth schema: {str(e)}"
        ) 