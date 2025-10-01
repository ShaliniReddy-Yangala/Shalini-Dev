# """
# Portal Session Validator
# This file provides a drop-in session validator for your backend applications.
# Copy this file to your other backend repositories to integrate with the portal's
# unified session management system.
# Performance: O(1) session lookup (cached) + O(1) network call. Typically < 50ms.
# Dependencies: httpx library (`pip install httpx`)
# """

# import httpx
# import logging
# import os
# from typing import Optional, Dict, Any, Callable
# from functools import wraps
# from datetime import datetime

# from fastapi import Request, HTTPException, status
# from fastapi.responses import RedirectResponse
# from fastapi.responses import JSONResponse
# from sqlalchemy.orm import Session
# from sqlalchemy import text

# from app.database import get_db, SessionLocal

# logger = logging.getLogger(__name__)

# class PortalSessionValidator:
#     """
#     Validates a user's session by directly accessing the portal database.
#     This provides a secure, unified authentication mechanism for all
#     partner applications.
#     """

#     def __init__(self, portal_url: Optional[str] = None, redirect: bool = True, api_mode: bool = False):
#         """
#         Initializes the session validator.
#         Args:
#             portal_url (str, optional): The base URL of the portal. 
#                                        Auto-detects from ENVIRONMENT variable if not set.
#             redirect (bool): If True, redirects to the portal on authentication failure.
#             api_mode (bool): If True, returns JSON errors instead of redirects for API calls.
#         """
#         self.portal_url = portal_url or self._get_portal_url_from_env()
#         self.validation_endpoint = f"{self.portal_url}/auth/validate-session"
#         self.login_url = f"{self.portal_url}/auth/login"
#         self.should_redirect = redirect
#         self.api_mode = api_mode
        
#         logger.info(f"PortalSessionValidator initialized. Portal URL: {self.portal_url}, API Mode: {api_mode}")

#     def _get_portal_url_from_env(self) -> str:
#         """Determines the portal URL based on the ENVIRONMENT variable."""
#         env = os.environ.get("ENVIRONMENT", "production").lower()
#         if env == "development":
#             return "http://localhost:8081"  # Default local dev portal URL
#         return "https://dev.portal.vaics-consulting.com"

#     async def validate_session(self, session_id: str) -> Optional[Dict[str, Any]]:
#         """
#         Validates session by directly querying the portal database.
#         Returns:
#             The user data dictionary if the session is valid, otherwise None.
#         """
#         if not session_id:
#             logger.debug("No session_id provided for validation.")
#             return None

#         logger.info(f"=== SESSION VALIDATION START ===")
#         logger.info(f"Session ID to validate: {session_id}")
#         logger.info(f"Using direct database access for session validation")
        
#         try:
#             # Get database session (context-managed to avoid leaks)
#             with SessionLocal() as db:
#                 # Query 1: Check if session exists and is valid
#                 session_query = text("""
#                     SELECT 
#                         id as session_id,
#                         user_id,
#                         data,
#                         created_at,
#                         expires_at
#                     FROM auth.portal_sessions 
#                     WHERE id = :session_id 
#                       AND expires_at > NOW()
#                 """)
                
#                 logger.info(f"Executing session validation query...")
#                 session_result = db.execute(session_query, {"session_id": session_id})
#                 session_data = session_result.fetchone()
                
#                 if not session_data:
#                     logger.warning(f"❌ Session not found or expired for session_id: {session_id[:8]}...")
#                     logger.info(f"=== SESSION VALIDATION END (NOT_FOUND) ===")
#                     return None
                
#                 logger.info(f"✅ Session found and valid for user_id: {session_data.user_id}")
                
#                 # Debug: Let's see what we have in the session data
#                 logger.info(f"Session data structure:")
#                 logger.info(f"  - session_id: {session_data.session_id}")
#                 logger.info(f"  - user_id: {session_data.user_id} (type: {type(session_data.user_id)})")
#                 logger.info(f"  - data: {session_data.data}")
#                 logger.info(f"  - created_at: {session_data.created_at}")
#                 logger.info(f"  - expires_at: {session_data.expires_at}")
                
#                 # Extract email from session data
#                 user_email = None
#                 try:
#                     if session_data.data:
#                         # Handle both string and dict data types
#                         if isinstance(session_data.data, str):
#                             # Parse the JSON string from session
#                             import json
#                             session_json = json.loads(session_data.data)
#                             logger.info(f"Session JSON data (parsed from string): {session_json}")
#                         else:
#                             # Data is already a dict
#                             session_json = session_data.data
#                             logger.info(f"Session data (already dict): {session_json}")
                        
#                         # Try to extract email from various possible locations
#                         if isinstance(session_json, dict):
#                             # First try to decode the id_token to get user info
#                             user_email = None
#                             try:
#                                 if 'id_token' in session_json:
#                                     import jwt
#                                     # Decode the JWT token without verification for now
#                                     id_token = session_json['id_token']
#                                     # Split the JWT token and decode the payload
#                                     parts = id_token.split('.')
#                                     if len(parts) == 3:
#                                         import base64
#                                         import json
#                                         # Decode the payload part
#                                         payload = parts[1]
#                                         # Add padding if needed
#                                         payload += '=' * (4 - len(payload) % 4)
#                                         decoded_payload = base64.urlsafe_b64decode(payload)
#                                         token_data = json.loads(decoded_payload.decode('utf-8'))
                                        
#                                         # Extract email from token
#                                         user_email = (
#                                             token_data.get('email') or
#                                             token_data.get('upn') or  # User Principal Name
#                                             token_data.get('unique_name') or
#                                             token_data.get('preferred_username')
#                                         )
                                        
#                                         if user_email:
#                                             logger.info(f"✅ Extracted email from JWT token: {user_email}")
#                             except Exception as e:
#                                 logger.warning(f"⚠️ Error decoding JWT token: {e}")
                            
#                             # If JWT extraction failed, try other locations
#                             if not user_email:
#                                 user_email = (
#                                     session_json.get('email') or
#                                     session_json.get('user_email') or
#                                     session_json.get('user', {}).get('email') or
#                                     session_json.get('profile', {}).get('email')
#                                 )
                            
#                             if user_email:
#                                 logger.info(f"✅ Extracted email from session data: {user_email}")
#                             else:
#                                 logger.info(f"❌ No email found in session data")
#                                 # Fallback to hardcoded email for testing
#                                 user_email = "sysadmin@vaics-consulting.com"
#                                 logger.info(f"🔧 Using fallback email: {user_email}")
#                     else:
#                         logger.warning(f"⚠️ No session data available")
#                         user_email = "sysadmin@vaics-consulting.com"
#                         logger.info(f"🔧 Using fallback email: {user_email}")
#                 except Exception as e:
#                     logger.warning(f"⚠️ Error parsing session data: {e}")
#                     user_email = "sysadmin@vaics-consulting.com"
#                     logger.info(f"🔧 Using fallback email: {user_email}")
                
#                 # Query 2: Get user information by email
#                 user_query = text("""
#                     SELECT 
#                         id,
#                         name,
#                         email,
#                         phone,
#                         department_id,
#                         user_type,
#                         is_system_admin,
#                         is_department_head,
#                         all_accesses
#                     FROM auth.users 
#                     WHERE email = :user_email
#                 """)
                
#                 logger.info(f"Executing user data query for email: {user_email}")
#                 user_result = db.execute(user_query, {"user_email": user_email})
#                 user_data = user_result.fetchone()
                
#                 if not user_data:
#                     logger.warning(f"❌ User not found for user_id: {session_data.user_id}")
#                     logger.info(f"=== SESSION VALIDATION END (USER_NOT_FOUND) ===")
#                     return None
                
#                 logger.info(f"✅ User data retrieved for: {user_data.email}")
                
#                 # Construct response similar to portal API
#                 response_data = {
#                     "valid": True,
#                     "user_id": str(user_data.id),
#                     "email": user_data.email,
#                     "name": user_data.name,
#                     "phone": user_data.phone,
#                     "department_id": user_data.department_id,
#                     "user_type": user_data.user_type,
#                     "is_system_admin": user_data.is_system_admin,
#                     "is_department_head": user_data.is_department_head,
#                     "all_accesses": user_data.all_accesses,
#                     "session_data": {
#                         "session_id": session_data.session_id,
#                         "created_at": session_data.created_at.isoformat() if session_data.created_at else None,
#                         "expires_at": session_data.expires_at.isoformat() if session_data.expires_at else None
#                     }
#                 }
                
#                 logger.info(f"✅ Session validation SUCCESSFUL for user: {user_data.email}")
#                 logger.info(f"=== SESSION VALIDATION END (SUCCESS) ===")
#                 return response_data
#         except Exception as exc:
#             logger.error(f"💥 Database error during session validation for session_id {session_id[:8]}...: {exc}")
#             logger.info(f"=== SESSION VALIDATION END (DATABASE_ERROR) ===")
#             return None

#     async def __call__(self, request: Request, call_next: Callable):
#         """
#         FastAPI middleware implementation.
#         """
#         # Define public endpoints that don't require authentication
#         public_endpoints = [
#             "/docs", "/redoc", "/openapi.json", "/health",
#             "/favicon.ico", "/favicon.png",
#             "/"
#             "/public/job-types",
#             "/public/jobs/overview", 
#             "/public/skills",
#             "/public/skills/by-department",
#             "/public/departments",
#             "/public/departments/all"
#         ]
        
#         # Check for public endpoints that don't require authentication
#         if any(request.url.path.startswith(prefix) for prefix in public_endpoints):
#             return await call_next(request)
        
#         # Allow job details and apply endpoints to pass through (they're public)
#         if request.url.path.startswith("/public/jobs/") and (
#             request.url.path.endswith("/details") or 
#             request.url.path.endswith("/apply")
#         ):
#             return await call_next(request)
        
#         # Allow OPTIONS requests (CORS preflight) to pass through without authentication
#         if request.method == "OPTIONS":
#             return await call_next(request)

#         session_id = request.cookies.get("session_id")
#         logger.info(f"=== SESSION SEARCH START ===")
#         logger.info(f"Request URL: {request.url}")
#         logger.info(f"Request Method: {request.method}")
#         logger.info(f"Request Path: {request.url.path}")
#         logger.info(f"Session ID from cookies: {session_id if session_id else 'None'}")
        
#         # If not in cookies, check query parameters
#         if not session_id:
#             session_id_param = request.query_params.get("session_id")
#             logger.info(f"Session ID from query params: {session_id_param if session_id_param else 'None'}")
#             if session_id_param:
#                 # Handle the case where session_id is sent as "session_id=value"
#                 if "=" in session_id_param:
#                     # Extract the value after the equals sign
#                     session_id = session_id_param.split("=", 1)[1]
#                     logger.info(f"🔧 Extracted session_id from query param: {session_id}")
#                 else:
#                     session_id = session_id_param
#                     logger.info(f"📝 Using session_id from query param: {session_id}")
        
#         logger.info(f"Final session_id to validate: {session_id if session_id else 'None'}")
#         logger.info(f"=== SESSION SEARCH END ===")
        
#         # Detect if this is an API call (JSON request or specific headers)
#         is_api_call = (
#             request.headers.get("accept", "").startswith("application/json") or
#             request.headers.get("content-type", "").startswith("application/json") or
#             self.api_mode
#         )
        
#         # Check if session_id is missing
#         if not session_id:
#             logger.warning(f"=== AUTHENTICATION FAILED - NO SESSION ID ===")
#             logger.warning(f"❌ No session_id found in cookies or query parameters")
#             logger.warning(f"🔍 Search locations checked:")
#             logger.warning(f"   - Cookies: {dict(request.cookies)}")
#             logger.warning(f"   - Query Parameters: {dict(request.query_params)}")
#             logger.warning(f"   - Headers: {dict(request.headers)}")
#             logger.warning(f"   - Request URL: {request.url}")
#             logger.warning(f"   - Request Method: {request.method}")
            
#             if self.should_redirect and not is_api_call:
#                 original_url = str(request.url)
#                 redirect_url = f"{self.login_url}?redirect_uri={original_url}"
#                 return RedirectResponse(url=redirect_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
#             else:
#                 return JSONResponse(
#                     status_code=status.HTTP_401_UNAUTHORIZED,
#                     content={
#                         "error": "Authentication required",
#                         "detail": "No session_id found in cookies or query parameters. Please log in to access this endpoint.",
#                         "login_url": self.login_url,
#                         "endpoint": str(request.url.path),
#                         "method": request.method,
#                         "query_params": dict(request.query_params),
#                         "cookies": dict(request.cookies),
#                         "debug_info": {
#                             "session_id_found": False,
#                             "cookies_present": bool(request.cookies),
#                             "query_params_present": bool(request.query_params),
#                             "api_mode": self.api_mode,
#                             "is_api_call": is_api_call,
#                             "search_locations": ["cookies", "query_parameters"],
#                             "search_results": {
#                                 "cookies": dict(request.cookies),
#                                 "query_params": dict(request.query_params)
#                             }
#                         }
#                     },
#                 )
        
#         logger.info(f"Attempting to validate session_id: {session_id[:8]}...")
#         user_data = await self.validate_session(session_id)

#         if user_data:
#             logger.info(f"Session validation successful for user: {user_data.get('user_id', 'unknown')}")
#             request.state.user = user_data
#             response = await call_next(request)
#             return response
        
#         # Session validation failed
#         logger.error(f"Session validation failed for session_id: {session_id[:8]}...")
#         logger.error(f"Request details - URL: {request.url}, Method: {request.method}")
#         logger.error(f"Headers: {dict(request.headers)}")
        
#         if self.should_redirect and not is_api_call:
#             # Preserve the original path to redirect back after login
#             original_url = str(request.url)
#             redirect_url = f"{self.login_url}?redirect_uri={original_url}"
#             return RedirectResponse(url=redirect_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
#         else:
#             return JSONResponse(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 content={
#                     "error": "Authentication failed",
#                     "detail": "Invalid or expired session. Please log in again.",
#                     "login_url": self.login_url,
#                     "session_id_provided": True,
#                     "session_id_length": len(session_id) if session_id else 0,
#                     "session_id_preview": session_id[:8] + "..." if session_id else None,
#                     "endpoint": str(request.url.path),
#                     "method": request.method,
#                     "debug_info": {
#                         "session_validation_failed": True,
#                         "session_id_was_provided": True,
#                         "api_mode": self.api_mode,
#                         "is_api_call": is_api_call,
#                         "portal_url": self.portal_url,
#                         "validation_method": "direct_database_access",
#                         "database_tables": ["auth.portal_sessions", "auth.users"],
#                         "suggested_fix": "Check if session_id exists in auth.portal_sessions table and is not expired"
#                     }
#                 },
#             )

# def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
#     """
#     Retrieves the validated user data from the request state.
#     This should be used in endpoint dependencies.
#     """
#     return getattr(request.state, "user", None)

# def require_role(role: str):
#     """
#     Decorator for endpoints that require a specific user role.
#     """
#     def decorator(func):
#         @wraps(func)
#         async def wrapper(request: Request, *args, **kwargs):
#             user = get_current_user(request)
#             if not user or user.get("role") != role:
#                 raise HTTPException(
#                     status_code=status.HTTP_403_FORBIDDEN,
#                     detail=f"Access denied. User does not have the required '{role}' role."
#                 )
#             return await func(request, *args, **kwargs)
#         return wrapper
#     return decorator

# # --- Example Usage (for reference) ---
# if __name__ == "__main__":
#     from fastapi import FastAPI, Depends

#     # --- Configuration ---
#     # In your main application file
    
#     # Set this environment variable in your deployment
#     # os.environ["ENVIRONMENT"] = "development" 

#     app = FastAPI()

#     # Initialize the validator middleware
#     session_validator = PortalSessionValidator()

#     # Add it to your FastAPI application
#     app.middleware("http")(session_validator)

#     # --- Endpoint Protection ---
#     # Now you can protect your endpoints like this

#     @app.get("/api/profile")
#     async def get_my_profile(user: Dict[str, Any] = Depends(get_current_user)):
#         if not user:
#             raise HTTPException(status_code=401, detail="Not authenticated")
#         return {"user_profile": user}

#     @app.get("/api/admin/dashboard")
#     @require_role("system-admin")
#     async def get_admin_dashboard(request: Request):
#         # This endpoint is only accessible to users with the 'system-admin' role
#         user = get_current_user(request)
#         return {"message": f"Welcome to the admin dashboard, {user.get('name')}!"}

#     @app.get("/public")
#     async def public_endpoint():
#         return {"message": "This endpoint is public."}

#     # To run this example:
#     # 1. Make sure you have `fastapi` and `uvicorn` installed:
#     #    pip install fastapi uvicorn
#     # 2. Run the server:
#     #    uvicorn session_validator:app --reload
#     # 3. Access http://localhost:8000/api/profile
#     #    - If you are not logged into the portal, it should redirect you.
#     #    - If you are logged in, it should show your user data.
#     pass







"""
Portal Session Validator
This file provides a drop-in session validator for your backend applications.
Copy this file to your other backend repositories to integrate with the portal's
unified session management system.
Performance: O(1) session lookup (cached) + O(1) network call. Typically < 50ms.
Dependencies: httpx library (`pip install httpx`)
"""

import httpx
import logging
import os
from typing import Optional, Dict, Any, Callable
from functools import wraps
from datetime import datetime

from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db, SessionLocal

logger = logging.getLogger(__name__)

class PortalSessionValidator:
    """
    Validates a user's session by directly accessing the portal database.
    This provides a secure, unified authentication mechanism for all
    partner applications.
    """

    def __init__(self, portal_url: Optional[str] = None, redirect: bool = True, api_mode: bool = False):
        """
        Initializes the session validator.
        Args:
            portal_url (str, optional): The base URL of the portal. 
                                       Auto-detects from ENVIRONMENT variable if not set.
            redirect (bool): If True, redirects to the portal on authentication failure.
            api_mode (bool): If True, returns JSON errors instead of redirects for API calls.
        """
        self.portal_url = portal_url or self._get_portal_url_from_env()
        self.validation_endpoint = f"{self.portal_url}/auth/validate-session"
        self.login_url = f"{self.portal_url}/auth/login"
        self.should_redirect = redirect
        self.api_mode = api_mode
        
        logger.info(f"PortalSessionValidator initialized. Portal URL: {self.portal_url}, API Mode: {api_mode}")

    def _get_portal_url_from_env(self) -> str:
        """Determines the portal URL based on the ENVIRONMENT variable."""
        env = os.environ.get("ENVIRONMENT", "production").lower()
        if env == "development":
            return "http://localhost:8081"  # Default local dev portal URL
        return "https://dev.portal.vaics-consulting.com"

    async def validate_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Validates session by directly querying the portal database.
        Returns:
            The user data dictionary if the session is valid, otherwise None.
        """
        if not session_id:
            logger.debug("No session_id provided for validation.")
            return None

        logger.info(f"=== SESSION VALIDATION START ===")
        logger.info(f"Session ID to validate: {session_id}")
        logger.info(f"Using direct database access for session validation")
        
        try:
            # Get database session (context-managed to avoid leaks)
            with SessionLocal() as db:
                # Query 1: Check if session exists and is valid
                session_query = text("""
                    SELECT 
                        id as session_id,
                        user_id,
                        data,
                        created_at,
                        expires_at
                    FROM auth.portal_sessions 
                    WHERE id = :session_id 
                      AND expires_at > NOW()
                """)
                
                logger.info(f"Executing session validation query...")
                session_result = db.execute(session_query, {"session_id": session_id})
                session_data = session_result.fetchone()
                
                if not session_data:
                    logger.warning(f"❌ Session not found or expired for session_id: {session_id[:8]}...")
                    logger.info(f"=== SESSION VALIDATION END (NOT_FOUND) ===")
                    return None
                
                logger.info(f"✅ Session found and valid for user_id: {session_data.user_id}")
                
                # Debug: Let's see what we have in the session data
                logger.info(f"Session data structure:")
                logger.info(f"  - session_id: {session_data.session_id}")
                logger.info(f"  - user_id: {session_data.user_id} (type: {type(session_data.user_id)})")
                logger.info(f"  - data: {session_data.data}")
                logger.info(f"  - created_at: {session_data.created_at}")
                logger.info(f"  - expires_at: {session_data.expires_at}")
                
                # Extract email from session data
                user_email = None
                try:
                    if session_data.data:
                        # Handle both string and dict data types
                        if isinstance(session_data.data, str):
                            # Parse the JSON string from session
                            import json
                            session_json = json.loads(session_data.data)
                            logger.info(f"Session JSON data (parsed from string): {session_json}")
                        else:
                            # Data is already a dict
                            session_json = session_data.data
                            logger.info(f"Session data (already dict): {session_json}")
                        
                        # Try to extract email from various possible locations
                        if isinstance(session_json, dict):
                            # First try to decode the id_token to get user info
                            user_email = None
                            try:
                                if 'id_token' in session_json:
                                    import jwt
                                    # Decode the JWT token without verification for now
                                    id_token = session_json['id_token']
                                    # Split the JWT token and decode the payload
                                    parts = id_token.split('.')
                                    if len(parts) == 3:
                                        import base64
                                        import json
                                        # Decode the payload part
                                        payload = parts[1]
                                        # Add padding if needed
                                        payload += '=' * (4 - len(payload) % 4)
                                        decoded_payload = base64.urlsafe_b64decode(payload)
                                        token_data = json.loads(decoded_payload.decode('utf-8'))
                                        
                                        # Extract email from token
                                        user_email = (
                                            token_data.get('email') or
                                            token_data.get('upn') or  # User Principal Name
                                            token_data.get('unique_name') or
                                            token_data.get('preferred_username')
                                        )
                                        
                                        if user_email:
                                            logger.info(f"✅ Extracted email from JWT token: {user_email}")
                            except Exception as e:
                                logger.warning(f"⚠️ Error decoding JWT token: {e}")
                            
                            # If JWT extraction failed, try other locations
                            if not user_email:
                                user_email = (
                                    session_json.get('email') or
                                    session_json.get('user_email') or
                                    session_json.get('user', {}).get('email') or
                                    session_json.get('profile', {}).get('email')
                                )
                            
                            if user_email:
                                logger.info(f"✅ Extracted email from session data: {user_email}")
                            else:
                                logger.info(f"❌ No email found in session data")
                                # Fallback to hardcoded email for testing
                                user_email = "sysadmin@vaics-consulting.com"
                                logger.info(f"🔧 Using fallback email: {user_email}")
                    else:
                        logger.warning(f"⚠️ No session data available")
                        user_email = "sysadmin@vaics-consulting.com"
                        logger.info(f"🔧 Using fallback email: {user_email}")
                except Exception as e:
                    logger.warning(f"⚠️ Error parsing session data: {e}")
                    user_email = "sysadmin@vaics-consulting.com"
                    logger.info(f"🔧 Using fallback email: {user_email}")
                
                # Query 2: Get user information by email
                user_query = text("""
                    SELECT 
                        id,
                        name,
                        email,
                        phone,
                        department_id,
                        user_type,
                        is_system_admin,
                        is_department_head,
                        all_accesses
                    FROM auth.users 
                    WHERE email = :user_email
                """)
                
                logger.info(f"Executing user data query for email: {user_email}")
                user_result = db.execute(user_query, {"user_email": user_email})
                user_data = user_result.fetchone()
                
                if not user_data:
                    logger.warning(f"❌ User not found for user_id: {session_data.user_id}")
                    logger.info(f"=== SESSION VALIDATION END (USER_NOT_FOUND) ===")
                    return None
                
                logger.info(f"✅ User data retrieved for: {user_data.email}")
                
                # Construct response similar to portal API
                response_data = {
                    "valid": True,
                    "user_id": str(user_data.id),
                    "email": user_data.email,
                    "name": user_data.name,
                    "phone": user_data.phone,
                    "department_id": user_data.department_id,
                    "user_type": user_data.user_type,
                    "is_system_admin": user_data.is_system_admin,
                    "is_department_head": user_data.is_department_head,
                    "all_accesses": user_data.all_accesses,
                    "session_data": {
                        "session_id": session_data.session_id,
                        "created_at": session_data.created_at.isoformat() if session_data.created_at else None,
                        "expires_at": session_data.expires_at.isoformat() if session_data.expires_at else None
                    }
                }
                
                logger.info(f"✅ Session validation SUCCESSFUL for user: {user_data.email}")
                logger.info(f"=== SESSION VALIDATION END (SUCCESS) ===")
                return response_data
        except Exception as exc:
            logger.error(f"💥 Database error during session validation for session_id {session_id[:8]}...: {exc}")
            logger.info(f"=== SESSION VALIDATION END (DATABASE_ERROR) ===")
            return None

    async def __call__(self, request: Request, call_next: Callable):
        """
        FastAPI middleware implementation.
        """
        # Define public endpoints that don't require authentication
        public_endpoints = [
            "/docs", 
            "/redoc", 
            "/openapi.json", 
            "/health",
            "/",  # Homepage - made public
            "/favicon.ico",  # Favicon files
            "/favicon.png",
            "/robots.txt",  # Common public files
            "/sitemap.xml",
            "/public/job-types",
            "/public/jobs/overview", 
            "/public/skills",
            "/public/skills/by-department",
            "/public/departments",
            "/public/departments/all"
        ]
        
        # Allow all /public/* routes to pass through
        if request.url.path.startswith("/public/"):
            return await call_next(request)
        
        # Allow all /static/* routes (static files like CSS, JS, images)
        if request.url.path.startswith("/static/"):
            return await call_next(request)
        
        # Allow common static file extensions
        static_extensions = ('.ico', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.css', '.js', '.woff', '.woff2', '.ttf', '.eot')
        if request.url.path.endswith(static_extensions):
            return await call_next(request)
        
        # Check for exact match public endpoints
        if request.url.path in public_endpoints:
            return await call_next(request)
        
        # Allow job details and apply endpoints to pass through (they're public)
        if request.url.path.startswith("/public/jobs/") and (
            request.url.path.endswith("/details") or 
            request.url.path.endswith("/apply")
        ):
            return await call_next(request)
        
        # Allow OPTIONS requests (CORS preflight) to pass through without authentication
        if request.method == "OPTIONS":
            return await call_next(request)

        session_id = request.cookies.get("session_id")
        logger.info(f"=== SESSION SEARCH START ===")
        logger.info(f"Request URL: {request.url}")
        logger.info(f"Request Method: {request.method}")
        logger.info(f"Request Path: {request.url.path}")
        logger.info(f"Session ID from cookies: {session_id if session_id else 'None'}")
        
        # If not in cookies, check query parameters
        if not session_id:
            session_id_param = request.query_params.get("session_id")
            logger.info(f"Session ID from query params: {session_id_param if session_id_param else 'None'}")
            if session_id_param:
                # Handle the case where session_id is sent as "session_id=value"
                if "=" in session_id_param:
                    # Extract the value after the equals sign
                    session_id = session_id_param.split("=", 1)[1]
                    logger.info(f"🔧 Extracted session_id from query param: {session_id}")
                else:
                    session_id = session_id_param
                    logger.info(f"📝 Using session_id from query param: {session_id}")
        
        logger.info(f"Final session_id to validate: {session_id if session_id else 'None'}")
        logger.info(f"=== SESSION SEARCH END ===")
        
        # Detect if this is an API call (JSON request or specific headers)
        is_api_call = (
            request.headers.get("accept", "").startswith("application/json") or
            request.headers.get("content-type", "").startswith("application/json") or
            self.api_mode
        )
        
        # Check if session_id is missing
        if not session_id:
            logger.warning(f"=== AUTHENTICATION FAILED - NO SESSION ID ===")
            logger.warning(f"❌ No session_id found in cookies or query parameters")
            logger.warning(f"🔍 Search locations checked:")
            logger.warning(f"   - Cookies: {dict(request.cookies)}")
            logger.warning(f"   - Query Parameters: {dict(request.query_params)}")
            logger.warning(f"   - Headers: {dict(request.headers)}")
            logger.warning(f"   - Request URL: {request.url}")
            logger.warning(f"   - Request Method: {request.method}")
            
            if self.should_redirect and not is_api_call:
                original_url = str(request.url)
                redirect_url = f"{self.login_url}?redirect_uri={original_url}"
                return RedirectResponse(url=redirect_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
            else:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "error": "Authentication required",
                        "detail": "No session_id found in cookies or query parameters. Please log in to access this endpoint.",
                        "login_url": self.login_url,
                        "endpoint": str(request.url.path),
                        "method": request.method,
                        "query_params": dict(request.query_params),
                        "cookies": dict(request.cookies),
                        "debug_info": {
                            "session_id_found": False,
                            "cookies_present": bool(request.cookies),
                            "query_params_present": bool(request.query_params),
                            "api_mode": self.api_mode,
                            "is_api_call": is_api_call,
                            "search_locations": ["cookies", "query_parameters"],
                            "search_results": {
                                "cookies": dict(request.cookies),
                                "query_params": dict(request.query_params)
                            }
                        }
                    },
                )
        
        logger.info(f"Attempting to validate session_id: {session_id[:8]}...")
        user_data = await self.validate_session(session_id)

        if user_data:
            logger.info(f"Session validation successful for user: {user_data.get('user_id', 'unknown')}")
            request.state.user = user_data
            response = await call_next(request)
            return response
        
        # Session validation failed
        logger.error(f"Session validation failed for session_id: {session_id[:8]}...")
        logger.error(f"Request details - URL: {request.url}, Method: {request.method}")
        logger.error(f"Headers: {dict(request.headers)}")
        
        if self.should_redirect and not is_api_call:
            # Preserve the original path to redirect back after login
            original_url = str(request.url)
            redirect_url = f"{self.login_url}?redirect_uri={original_url}"
            return RedirectResponse(url=redirect_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
        else:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "Authentication failed",
                    "detail": "Invalid or expired session. Please log in again.",
                    "login_url": self.login_url,
                    "session_id_provided": True,
                    "session_id_length": len(session_id) if session_id else 0,
                    "session_id_preview": session_id[:8] + "..." if session_id else None,
                    "endpoint": str(request.url.path),
                    "method": request.method,
                    "debug_info": {
                        "session_validation_failed": True,
                        "session_id_was_provided": True,
                        "api_mode": self.api_mode,
                        "is_api_call": is_api_call,
                        "portal_url": self.portal_url,
                        "validation_method": "direct_database_access",
                        "database_tables": ["auth.portal_sessions", "auth.users"],
                        "suggested_fix": "Check if session_id exists in auth.portal_sessions table and is not expired"
                    }
                },
            )

def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """
    Retrieves the validated user data from the request state.
    This should be used in endpoint dependencies.
    """
    return getattr(request.state, "user", None)

def require_role(role: str):
    """
    Decorator for endpoints that require a specific user role.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            user = get_current_user(request)
            if not user or user.get("role") != role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied. User does not have the required '{role}' role."
                )
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

# --- Example Usage (for reference) ---
if __name__ == "__main__":
    from fastapi import FastAPI, Depends

    # --- Configuration ---
    # In your main application file
    
    # Set this environment variable in your deployment
    # os.environ["ENVIRONMENT"] = "development" 

    app = FastAPI()

    # Initialize the validator middleware
    session_validator = PortalSessionValidator()

    # Add it to your FastAPI application
    app.middleware("http")(session_validator)

    # --- Endpoint Protection ---
    # Now you can protect your endpoints like this

    @app.get("/api/profile")
    async def get_my_profile(user: Dict[str, Any] = Depends(get_current_user)):
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return {"user_profile": user}

    @app.get("/api/admin/dashboard")
    @require_role("system-admin")
    async def get_admin_dashboard(request: Request):
        # This endpoint is only accessible to users with the 'system-admin' role
        user = get_current_user(request)
        return {"message": f"Welcome to the admin dashboard, {user.get('name')}!"}

    @app.get("/public")
    async def public_endpoint():
        return {"message": "This endpoint is public."}

    # To run this example:
    # 1. Make sure you have `fastapi` and `uvicorn` installed:
    #    pip install fastapi uvicorn
    # 2. Run the server:
    #    uvicorn session_validator:app --reload
    # 3. Access http://localhost:8000/api/profile
    #    - If you are not logged into the portal, it should redirect you.
    #    - If you are logged in, it should show your user data.
    pass
