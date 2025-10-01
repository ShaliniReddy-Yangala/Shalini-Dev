##backend/app/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError

from .database import get_db
from . import models

# Security configuration
SECRET_KEY = "your-secret-key"  # In production, use a proper secret key stored in environment variables
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

def check_user_permission(user: models.User, permission_name: str, db: Session):
    """Check if user has the specified permission through any of their roles"""
    user_roles = db.query(models.UserRole).filter(
        models.UserRole.user_id == user.id,
        models.UserRole.end_date == None  
    ).all()
    
    for user_role in user_roles:
        role = db.query(models.Role).filter(models.Role.id == user_role.role_id).first()
        if not role:
            continue
            
        for permission in role.permissions:
            if permission.name in ["view_all", "manage_all"] or permission.name == permission_name:
                return True
                
    return False

# Permission dependency for routes
def require_permission(permission_name: str):
    def permission_dependency(
        current_user: models.User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
        if not check_user_permission(current_user, permission_name, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not enough permissions. Required: {permission_name}"
            )
        return current_user
    return permission_dependency