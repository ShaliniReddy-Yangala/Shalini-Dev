# 🛡️ Portal Session Validator - Integration Guide

## 📋 **Overview**

This guide provides instructions for integrating your backend applications with the portal's **unified session management system**. By using the `session_validator.py` module, you can enable secure, centralized authentication with minimal effort. This approach replaces the previous JWT-based system.

### **Key Benefits:**
- ✅ **Unified Authentication**: A single session is shared across the portal and all partner applications.
- 🔒 **Centralized Security**: The portal manages all session lifecycle events, including creation, validation, and revocation.
- 🚀 **Simplified Integration**: Just drop the `session_validator.py` file into your project and add the middleware.
- 🔄 **Real-time Validation**: Sessions are validated in real-time against the portal, ensuring immediate response to changes in user status or permissions.

---

## 🔧 **Requirements**

### **Dependencies:**
- `httpx` library (`pip install httpx`)
- Your backend framework (FastAPI is used in examples)

### **Configuration Requirements:**
- **Portal URL**: Your application must be able to communicate with the portal's validation endpoint.
- **Environment Variable**: Set `ENVIRONMENT=development` for local development to ensure the validator points to the correct portal URL.
- **Cookie Access**: Your application must be able to read the `session_id` cookie, which is set by the portal.

---

## 📁 **Installation**

### **Step 1: Copy Validator File**
1. Copy `session_validator.py` to your backend repository.
2. Place it in a suitable location, such as a `middleware` or `auth` directory.

### **Step 2: Install Dependencies**
```bash
pip install httpx
```

### **Step 3: Configure Environment**
For local development, set the `ENVIRONMENT` variable. This tells the validator to use the local portal URL (`http://localhost:8081`).

```bash
# For development
export ENVIRONMENT=development

# For production, no variable is needed, as it defaults to the production portal URL
# You can also set it explicitly:
export ENVIRONMENT=production
```

---

## 🚀 **Integration Example (FastAPI)**

### **1. Add Middleware to Your Application**
In your main application file (e.g., `main.py`), import and initialize the `PortalSessionValidator`.

```python
from fastapi import FastAPI
from SSO_Common_Files_Docs.session_validator import PortalSessionValidator # Adjust the import path

app = FastAPI()

# Initialize the session validator middleware
session_validator = PortalSessionValidator()

# Add the middleware to your FastAPI application
app.middleware("http")(session_validator)

@app.get("/")
def read_root():
    return {"message": "Welcome to the application!"}
```

**File Structure:**
```
YOUR-BACKEND/
└── app/
    ├── routes/
    ├── main.py
    └── session_validator.py   <--- 📥 Paste here!
```

### **2. Protect Your Endpoints**
Use the `get_current_user` dependency to protect your routes and access user information.

```python
from fastapi import Depends, HTTPException
from SSO_Common_Files_Docs.session_validator import get_current_user # Adjust the import path
from typing import Dict, Any

@app.get("/api/my-profile")
async def get_my_profile(user: Dict[str, Any] = Depends(get_current_user)):
    """
    This endpoint is protected. 
    It will only be accessible if the user has a valid session.
    """
    if not user:
        # This part is technically not needed if the middleware handles redirection,
        # but it's good practice for clarity and for non-redirect cases.
        raise HTTPException(status_code=401, detail="Authentication required")
        
    return {"user_profile": user}

@app.get("/public-data")
async def get_public_data():
    """
    This endpoint is not explicitly protected and can be accessed by anyone.
    However, the middleware will still run.
    """
    return {"info": "This is public data."}
```

---

## 🔄 **Authentication Flow**

### **Successful Authentication:**
1.  **User Logs In**: The user logs into the main portal, which creates a session and sets a `session_id` cookie on the `vaics-consulting.com` domain.
2.  **User Accesses Partner App**: When the user navigates to your application, the browser automatically sends the `session_id` cookie with the request.
3.  **Middleware Validates Session**: The `PortalSessionValidator` middleware intercepts the request, extracts the `session_id`, and sends a request to the portal's `/auth/validate-session` endpoint.
4.  **Portal Responds**: The portal checks if the session is valid and returns the user's data (ID, email, role, etc.).
5.  **Access Granted**: The middleware receives the valid response, attaches the user data to the request state (`request.state.user`), and allows the request to proceed to your route handler.

### **Failed Authentication:**
1.  **No Session or Invalid Session**: If the user is not logged in, or the session is expired or invalid, the `session_id` cookie will be missing or incorrect.
2.  **Validation Fails**: The portal's validation endpoint returns an "invalid" response.
3.  **Redirect to Login**: The middleware intercepts the failed validation and automatically redirects the user to the portal's login page.
4.  **Return to App**: After successful login, the portal will redirect the user back to the original URL of your application.

---

## 🧪 **Testing Your Integration**

### **Step 1: Test Without a Valid Session**
1.  Ensure you are logged out of the portal.
2.  Navigate directly to a protected endpoint in your application (e.g., `http://localhost:8000/api/my-profile`).
3.  You should be automatically redirected to the portal's login page.

### **Step 2: Test With a Valid Session**
1.  Log into the portal.
2.  Navigate to a protected endpoint in your application.
3.  You should be able to access the endpoint successfully, and it should return the correct data.

### **Step 3: Test User Data Access**
Create a test endpoint to verify that the user data is being correctly passed to your application.

```python
from fastapi import Depends
from SSO_Common_Files_Docs.session_validator import get_current_user # Adjust path
from typing import Dict, Any

@app.get("/test-user-info")
async def test_user_info(user: Dict[str, Any] = Depends(get_current_user)):
    if not user:
        return {"authenticated": False, "user_info": None}
    
    return {
        "authenticated": True,
        "user_info": {
            "user_id": user.get("user_id"),
            "email": user.get("email"),
            "role": user.get("role"),
        }
    }
```

---

## 🚨 **Troubleshooting**

- **"Connection Refused" or "Timeout" errors**: Ensure the portal backend is running and accessible from your application's environment. Check firewall rules if applicable.
- **Endless Redirects**: Verify that the `portal_url` configured in the validator is correct. Also, ensure the `session_id` cookie is being correctly set by the portal and sent by the browser.
- **"401 Unauthorized"**: This means authentication failed. Use your browser's developer tools to check if the `session_id` cookie is present in the request headers.

For more detailed debugging, you can enable debug logging for the validator:
```python
import logging
logging.getLogger('session_validator').setLevel(logging.DEBUG)
```
