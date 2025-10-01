##backend/app/middleware/permission_middleware.py
from fastapi import Request, HTTPException
from sqlalchemy.orm import Session
from typing import List
import json

from ..database import SessionLocal
from .. import models

async def permission_middleware(request: Request, call_next):
    """
    Middleware to check permissions based on route path and method.
    This is an additional layer of security beyond the route-level dependencies.
    """
    # Format: {path_pattern: {method: [required_permissions]}}
    route_permissions = {
        "/roles": {
            "GET": ["view_all"],
            "POST": ["manage_all"],
            "PUT": ["manage_all"],
            "DELETE": ["manage_all"]
        },
        "/user-roles": {
            "GET": ["view_all"],
            "POST": ["manage_all"],
            "PUT": ["manage_all"],
            "DELETE": ["manage_all"]
        },
        "/jobs": {
            "GET": ["view_job"],
            "POST": ["create_job"],
            "PUT": ["manage_job"],
            "DELETE": ["manage_job"]
        },
        "/candidates": {
            "GET": ["view_candidate"],
            "POST": ["create_candidate"],
            "PUT": ["manage_candidate"],
            "DELETE": ["manage_candidate"]
        }
    }
    
    # Skip permission check for authentication routes
    if request.url.path in ["/login", "/token", "/health", "/"]:
        return await call_next(request)
    
    # Check if authorization header exists
    if "Authorization" not in request.headers:
        return await call_next(request)
    
    # Extract token
    auth_header = request.headers.get("Authorization")
    if not auth_header.startswith("Bearer "):
        return await call_next(request)
    
    token = auth_header.split(" ")[1]
    
    from ..dependencies import get_current_user
    
    try:
        db = SessionLocal()
        user = get_current_user(token, db)
        
        # Find matching route pattern
        required_permissions = None
        for route_pattern, methods in route_permissions.items():
            if route_pattern in request.url.path:
                if request.method in methods:
                    required_permissions = methods[request.method]
                    break
        
        # If no matching pattern or no required permissions, allow access
        if not required_permissions:
            return await call_next(request)
        
        # Check user permissions
        has_permission = False
        for permission_name in required_permissions:
            from ..dependencies import check_user_permission
            if check_user_permission(user, permission_name, db):
                has_permission = True
                break
            
            # Special case: if user needs department-specific permission
            if "_department" in permission_name:
                # Extract department from request
                try:
                    body = await request.json()
                    department = body.get("department")
                    
                    # Check if user has role in this department
                    user_roles = db.query(models.UserRole).filter(
                        models.UserRole.user_id == user.id,
                        models.UserRole.department == department,
                        models.UserRole.end_date == None
                    ).all()
                    
                    if user_roles:
                        has_permission = True
                        break
                except:
                    pass
        
        if not has_permission:
            return JSONResponse(
                status_code=403,
                content={"detail": "Not enough permissions"}
            )
            
    except Exception as e:
        # Log the error
        print(f"Permission middleware error: {str(e)}")
    finally:
        db.close()


    
    # Continue processing the request
    return await call_next(request)

# JSON Response class for middleware
from starlette.responses import JSONResponse
