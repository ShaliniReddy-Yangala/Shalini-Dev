# backend/app/main.py - Updated to include document routes and localhost for dev CORS
from fastapi import Depends, FastAPI, Request
import uvicorn
from app.database import Base, engine
from fastapi.middleware.cors import CORSMiddleware
from app.middleware.session_validator import PortalSessionValidator, get_current_user
from app.config import ENVIRONMENT

from app.routes.jobs import router as jobs_route
from app.routes.candidates import router as candidates_route
from app.routes.TAteam import router as TAteam_route
from app.routes.notifications import router as notifications_route
from app.routes.ctc import router as ctc_route
from app.routes.demand import router as demand_route
from app.routes.upload import router as upload_route
from app.routes.user_roles import router as user_roles_route, seed_default_roles
from app.routes.documents import router as documents_route
from app.routes.dashboard import router as dashboard_route
from app.routes.skills import router as skills_route
from app.routes.interview1 import router as interview_route
from app.routes.interview2 import router as interview2_route
from app.routes.hr_team import router as hrteam_route
from app.routes.discussionstatus import router as discussionstatus_route
from app.routes.stats_filter import router as stats_filter_route
from app.routes.ta_team_stats import router as ta_team_stats_route
from app.routes.candidates_analytics import router as candidates_analytics_route
from app.routes.excel_upload import router as excel_upload_route
from app.routes.auth_users import router as auth_users_route
from app.routes.user_role_access import router as user_role_access_router
from app.routes.public_jobs import router as public_jobs_router
from app.routes.referred_by import router as referred_by_router
from app.routes.realtime_access_revoke import router as realtime_access_router
from app.routes.internal_logs import router as internal_logs_router
from app.routes.data_retention import router as data_retention_router
from app.routes.filter_options import router as filter_options_router
from app.routes.interviewer_candidates import router as interviewer_candidates_router



#Employee Master Report
from app.Employee_Master_Report.emp_routes.emp_components.candidates_to_onboard import router as candidates_to_onboard_router
from app.Employee_Master_Report.emp_routes.create_employee_basic import router as create_employee_basic_router
from app.Employee_Master_Report.emp_routes.emp_components.basic_details import router as basic_details_router
from app.Employee_Master_Report.emp_routes.emp_components.personal_details import router as personal_details_router
from app.Employee_Master_Report.emp_routes.emp_components.address_details import router as address_details_router
from app.Employee_Master_Report.emp_routes.emp_components.family_details import router as family_details_router
from app.Employee_Master_Report.emp_routes.emp_components.education_details import router as education_details_router
from app.Employee_Master_Report.emp_routes.emp_components.experience_details import router as experience_details_router
from app.Employee_Master_Report.emp_routes.emp_components.contract_details import router as contract_details_router
from app.Employee_Master_Report.emp_routes.emp_components.bank_details import router as bank_details_router
from app.Employee_Master_Report.emp_routes.emp_components.communication_details import router as communication_details_router
from app.Employee_Master_Report.emp_routes.emp_components.nominee_details import router as nominee_details_router
from app.Employee_Master_Report.emp_routes.emp_components.salary_details import router as salary_details_router
from app.Employee_Master_Report.emp_routes.emp_components.emergency_contact_details import router as emergency_contact_router
from app.Employee_Master_Report.emp_routes.emp_components.onboarding_details import router as onboarding_details_router
from app.Employee_Master_Report.emp_routes.emp_components.asset_details import router as asset_details_router
from app.Employee_Master_Report.emp_routes.emp_components.health_insurance_details import router as health_insurance_router
from app.Employee_Master_Report.emp_routes.dropdowns import router as dropdowns_router
from app.Employee_Master_Report.emp_routes.bulk_upload import router as bulk_upload_router
from app.Employee_Master_Report.emp_routes.excel_template import router as excel_template_router


#Assert Application
from app.Assert_Application.assert_route import router as assets_router
from app.Assert_Application.assert_dropdown import router_categories as assets_categories_router








import boto3
from app.routes.email_service import email_router
from app.config import AWS_REGION, S3_BUCKET
from app.database import get_db
from app.models import Candidate, FinalStatusDB  # Add FinalStatusDB import
from sqlalchemy.orm import Session
from app import schemas
from typing import List

print(f"Using AWS_REGION: {AWS_REGION} and S3_BUCKET: {S3_BUCKET}")
print("Environment variables loaded from OS environment")

app = FastAPI()

# Initialize Portal Session Validator Middleware
session_validator = PortalSessionValidator(api_mode=True)

# CORS middleware with comprehensive localhost dev support
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://dev.hrms.vaics-consulting.com",
        "https://hrms.vaics-consulting.com",
        "https://dev.portal.vaics-consulting.com",
        "https://portal.vaics-consulting.com",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
        "https://vaics-consulting.com",
        # # Add wildcard for development (remove in production)
        # "*"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

# Add Portal Session Validator Middleware
app.middleware("http")(session_validator)

# Create database tables
Base.metadata.create_all(bind=engine)

# Include all routers
app.include_router(jobs_route)
app.include_router(candidates_route)
app.include_router(TAteam_route)
app.include_router(notifications_route)
app.include_router(ctc_route)
app.include_router(demand_route)
app.include_router(upload_route)
app.include_router(user_roles_route)
app.include_router(documents_route)
app.include_router(dashboard_route)
app.include_router(skills_route)
app.include_router(email_router)
app.include_router(interview_route)
app.include_router(interview2_route)
app.include_router(hrteam_route)
app.include_router(discussionstatus_route)
app.include_router(stats_filter_route)
app.include_router(ta_team_stats_route)
app.include_router(candidates_analytics_route)
app.include_router(excel_upload_route)
app.include_router(auth_users_route)
app.include_router(user_role_access_router)
app.include_router(public_jobs_router)
app.include_router(referred_by_router)
app.include_router(realtime_access_router)
app.include_router(internal_logs_router)
app.include_router(data_retention_router)
app.include_router(filter_options_router)
app.include_router(interviewer_candidates_router)


#Employee Master Report
app.include_router(candidates_to_onboard_router)
app.include_router(create_employee_basic_router)
app.include_router(basic_details_router)
app.include_router(personal_details_router)
app.include_router(address_details_router)
app.include_router(family_details_router)
app.include_router(education_details_router)
app.include_router(experience_details_router)
app.include_router(contract_details_router)
app.include_router(bank_details_router)
app.include_router(communication_details_router)
app.include_router(nominee_details_router)
app.include_router(salary_details_router)
app.include_router(emergency_contact_router)
app.include_router(onboarding_details_router)
app.include_router(asset_details_router)
app.include_router(health_insurance_router)
app.include_router(dropdowns_router)
app.include_router(bulk_upload_router)
app.include_router(excel_template_router)



#Assert Application
app.include_router(assets_categories_router, prefix="/assets")
app.include_router(assets_router)




# Add lightweight user role access endpoint without candidates prefix
@app.get("/user-role-access-lite", response_model=List[schemas.UserRoleAccessLiteResponse])
async def get_all_users_role_access_lite(db: Session = Depends(get_db)):
    """Lightweight user role access info for all users - table fill"""
    from app.models import User, UserRoleAccess
    
    # Get all users with their role access
    users_with_access = db.query(User, UserRoleAccess).join(
        UserRoleAccess, User.id == UserRoleAccess.user_id
    ).all()
    
    result = []
    for user, access in users_with_access:
        result.append({
            "user_id": access.id,  # Changed from access.user_id to access.id (access_id)
            "role_template_id": access.role_template_id,
            "role_name": access.role_name,
            "is_super_admin": access.is_super_admin,
            "expiry_date": access.expiry_date,
            "allowed_job_ids": access.allowed_job_ids,
            "allowed_department_ids": access.allowed_department_ids,
            "allowed_candidate_ids": access.allowed_candidate_ids,
            "is_unrestricted": access.is_unrestricted,
            "user_name": user.name,
            "user_email": user.email
        })
    
    return result

# Seed default roles on startup
@app.on_event("startup")
def startup_event():
    seed_default_roles()
    print("Default roles seeded successfully!")



@app.get("/referred-by-list", response_model=list)
def get_referred_by_list_root(db: Session = Depends(get_db)):
    """
    Returns a list of unique non-null values for the referred_by field from all candidates, sorted alphabetically.
    """
    referred_by_values = db.query(Candidate.referred_by).distinct().all()
    # Flatten and filter out None/empty values
    unique_values = []
    for val in referred_by_values:
        # Extract the actual value from the row object
        actual_val = val[0]  # SQLAlchemy returns a Row object, access first element
        # Only add non-null, non-empty values
        if actual_val is not None and str(actual_val).strip():
            unique_values.append(actual_val)
    
    return sorted(unique_values)

@app.get("/final_status_first")
def get_first_final_status_root(db: Session = Depends(get_db)):
    """Return the first final status value (status string) from FinalStatusDB."""
    first_status = db.query(FinalStatusDB).order_by(FinalStatusDB.id.asc()).first()
    if first_status:
        return {"final_status": first_status.status}
    return {"final_status": None}

from sqlalchemy import text

@app.get("/debug/database")
def debug_database(db: Session = Depends(get_db)):
    """Debug endpoint to check database connection and basic queries."""
    try:
        # Test basic database connection
        result = db.execute(text("SELECT 1 as test")).fetchone()
        
        # Test if tables exist
        tables_result = db.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")).fetchall()
        tables = [row[0] for row in tables_result] if tables_result else []
        
        # Test a simple query on candidates table
        candidates_count = db.query(Candidate).count()
        
        return {
            "database_connection": "success",
            "test_query": result[0] if result else None,
            "available_tables": tables,
            "candidates_count": candidates_count,
            "database_url": str(db.bind.url) if hasattr(db, 'bind') else "unknown"
        }
    except Exception as e:
        return {
            "database_connection": "failed",
            "error": str(e),
            "database_url": str(db.bind.url) if hasattr(db, 'bind') else "unknown"
        }

@app.get("/debug/data-test")
def debug_data_test(db: Session = Depends(get_db)):
    """Debug endpoint to test actual data queries and see what's happening."""
    try:
        # Test raw SQL count
        raw_count = db.execute(text("SELECT COUNT(*) FROM candidates")).fetchone()[0]
        
        # Test ORM count
        orm_count = db.query(Candidate).count()
        
        # Test getting first few candidates
        first_candidates = db.query(Candidate).limit(3).all()
        candidates_data = []
        for candidate in first_candidates:
            candidates_data.append({
                "id": candidate.id,
                "name": candidate.name,
                "email": candidate.email,
                "phone": candidate.phone
            })
        
        # Test jobs table
        jobs_count = db.execute(text("SELECT COUNT(*) FROM jobs")).fetchone()[0]
        
        # Test departments table
        departments_count = db.execute(text("SELECT COUNT(*) FROM departments")).fetchone()[0]
        
        return {
            "raw_sql_candidates_count": raw_count,
            "orm_candidates_count": orm_count,
            "first_3_candidates": candidates_data,
            "jobs_count": jobs_count,
            "departments_count": departments_count,
            "candidates_table_exists": "candidates" in [table[0] for table in db.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")).fetchall()]
        }
    except Exception as e:
        return {
            "error": str(e),
            "error_type": type(e).__name__
        }

# SSO Test Endpoints
@app.get("/sso/test")
async def test_sso_authentication(request: Request):
    """Test endpoint to verify SSO authentication is working."""
    user = get_current_user(request)
    return {
        "authenticated": user is not None,
        "user_email": user.get('email') if user else None,
        "user_role": user.get('role') if user else None,
        "message": "SSO authentication test endpoint"
    }

@app.get("/sso/user-info")
async def get_user_info(request: Request):
    """Get detailed user information from SSO."""
    user = get_current_user(request)
    if not user:
        return {"error": "User not authenticated"}
    
    return {
        "user_id": user.get('user_id'),
        "email": user.get('email'),
        "name": user.get('name'),
        "role": user.get('role'),
    }

@app.get("/sso/health")
async def sso_health_check():
    """Health check endpoint that doesn't require authentication."""
    return {
        "status": "healthy",
        "sso_enabled": True,
        "environment": ENVIRONMENT,
        "portal_url": session_validator.portal_url
    }

@app.get("/auth/callback")
async def auth_callback():
    """Callback endpoint for portal authentication (excluded from SSO middleware)."""
    return {
        "message": "Auth callback endpoint",
        "status": "ready"
    }

@app.get("/health")
async def health_check():
    """Simple health check endpoint that doesn't require authentication."""
    return {
        "status": "healthy",
        "message": "HRMS Backend is running successfully",
        "environment": ENVIRONMENT,
        "version": "1.0.0"
    }



if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
    