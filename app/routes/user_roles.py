from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Body, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.models import Role, User, UserRole
from app.schemas import RoleResponse, UserRoleCreate, UserRoleResponse, UserRoleUpdate

router = APIRouter(
    prefix="/user-roles",
    tags=["user-roles"],
    responses={404: {"description": "Not found"}},
)


# Seed default roles if they don't exist
def seed_default_roles():
    db = SessionLocal()
    try:
        # Check if roles already exist
        existing_roles_count = db.query(Role).count()
        print(f"Found {existing_roles_count} existing roles in the database")
        
        # Only seed if no roles exist
        if existing_roles_count == 0:
            print("No roles found, seeding default roles...")
            default_roles = [
                Role(
                    name="Global TA Manager",
                    description="Global TA manager has accesses to all features, functions and data in VAICS HRMS."
                ),
                Role(
                    name="TA Manager",
                    description="TA manager has permission to create/manage/screen and view jobs."
                ),
                Role(
                    name="Departmental Head",
                    description="Departmental head has permission to create/manage/screen and view candidates and jobs within their departments."
                ),
                Role(
                    name="TA Recruiter",
                    description="TA recruiter has permissions to screen, view and manage candidates. TA recruiter dose not have accesses to create new jobs."
                ),
                Role(
                    name="Departmental Representative",
                    description="Departmental representative can view/edit/manage jobs and screen candidates for a selected departmental job."
                ),
                Role(
                    name="Visitor",
                    description="Allows employees to view job, screen candidates and candidate details for a particular job for a limited time period."
                ),
                Role(
                    name="Interviewer",
                    description="Can have accesses to assigned candidates profile, screening manager and can modify interview feedback."
                )
            ]
            
            for role in default_roles:
                print(f"Adding role: {role.name}")
                db.add(role)
            
            db.commit()
            
            # Verify all roles were created
            roles = db.query(Role).all()
            print(f"Successfully seeded {len(roles)} roles")
            for role in roles:
                print(f"  - Role ID {role.id}: {role.name}")
        else:
            # Check what roles actually exist
            roles = db.query(Role).all()
            print(f"Existing roles:")
            for role in roles:
                print(f"  - Role ID {role.id}: {role.name}")
    except Exception as e:
        db.rollback()
        print(f"Error seeding default roles: {e}")
    finally:
        db.close()

# Helper to calculate expiry date
def calculate_expiry_date(days=0, months=0, years=0):
    if not any([days, months, years]):
        return None
    
    expiry = datetime.utcnow()
    if days:
        expiry += timedelta(days=days)
    if months:
        # Approximate months as 30 days
        expiry += timedelta(days=30 * months)
    if years:
        # Approximate years as 365 days
        expiry += timedelta(days=365 * years)
    return expiry

@router.post("/roles/seed", status_code=201)
def force_seed_roles(db: Session = Depends(get_db)):
    """Force seed all default roles (use with caution)"""
    try:
        # Get existing roles
        existing_roles = db.query(Role).all()
        existing_role_names = {role.name for role in existing_roles}
        
        # Define all default roles
        default_roles = [
            Role(
                name="Global TA Manager",
                description="Global TA manager has accesses to all features, functions and data in VAICS HRMS."
            ),
            Role(
                name="TA Manager",
                description="TA manager has permission to create/manage/screen and view jobs."
            ),
            Role(
                name="Departmental Head",
                description="Departmental head has permission to create/manage/screen and view candidates and jobs within their departments."
            ),
            Role(
                name="TA Recruiter",
                description="TA recruiter has permissions to screen, view and manage candidates. TA recruiter dose not have accesses to create new jobs."
            ),
            Role(
                name="Departmental Representative",
                description="Departmental representative can view/edit/manage jobs and screen candidates for a selected departmental job."
            ),
            Role(
                name="Visitor",
                description="Allows employees to view job, screen candidates and candidate details for a particular job for a limited time period."
            ),
            Role(
                name="Interviewer",
                description="Can have accesses to assigned candidates profile, screening manager and can modify interview feedback."
            )
        ]
        
        # Add only roles that don't already exist
        added_roles = []
        for role in default_roles:
            if role.name not in existing_role_names:
                db.add(role)
                added_roles.append(role.name)
        
        db.commit()
        
        # Get all roles after seeding
        all_roles = db.query(Role).all()
        role_data = [{"id": role.id, "name": role.name} for role in all_roles]
        
        return {
            "message": f"Added {len(added_roles)} new roles",
            "added_roles": added_roles,
            "all_roles": role_data
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error seeding roles: {str(e)}")


# API Endpoints
@router.get("/roles/", response_model=List[RoleResponse])
def get_roles(db: Session = Depends(get_db)):
    """Get all available roles"""
    # Simplified query just focusing on the Role table
    roles = db.query(Role).all()
    return roles


@router.get("/", response_model=List[UserRoleResponse])
def get_user_roles(db: Session = Depends(get_db)):
    """Get all user roles with formatted response for frontend"""
    # Get all user roles
    user_roles_query = db.query(UserRole, User, Role).join(
        User, UserRole.user_id == User.id
    ).join(
        Role, UserRole.role_id == Role.id
    ).all()
    
    result = []
    for ur, user, role in user_roles_query:
        # Format jobs
        jobs_str = "All"
        if ur.job_ids:
            if len(ur.job_ids) == 1:
                jobs_str = ur.job_ids[0]
            elif ur.department and ("Departmental Head" in role.name or "Departmental Representative" in role.name):
                jobs_str = "All departmental jobs"
            elif len(ur.job_ids) > 1:
                jobs_str = f"Multiple ({len(ur.job_ids)})"
        
        # Format duration
        if ur.is_unrestricted:
            duration_str = "Unrestricted"
        elif ur.expiry_date:
            days_remaining = (ur.expiry_date - datetime.utcnow()).days
            if days_remaining <= 0:
                duration_str = "Expired"
            elif days_remaining <= 7:
                duration_str = f"{days_remaining} days remaining"
            elif ur.duration_years:
                duration_str = f"{ur.duration_years} years"
            elif ur.duration_months:
                duration_str = f"{ur.duration_months} months"
            else:
                duration_str = f"{ur.duration_days} days"
        else:
            duration_str = "Unlimited"
        
        result.append(UserRoleResponse(
            id=ur.id,
            name=user.name,
            email=user.email,
            department=ur.department or user.department or "General",
            role=role.name,
            selectedJobs=jobs_str,
            duration=duration_str
        ))
    
    return result


@router.post("/", response_model=UserRoleResponse)
def create_user_role(
    user_role: UserRoleCreate,
    db: Session = Depends(get_db)
):
    """Create a new user role assignment with improved error handling"""
    try:
        # Debug info
        print(f"Attempting to create user role with role_id: {user_role.role_id}")
        
        # Verify role exists
        role = db.query(Role).filter(Role.id == user_role.role_id).first()
        if not role:
            # Check if any roles exist in database
            roles_count = db.query(Role).count()
            if roles_count == 0:
                # No roles exist, try to seed them
                seed_default_roles()
                # Try again
                role = db.query(Role).filter(Role.id == user_role.role_id).first()
                if not role:
                    # Still no role, return detailed error
                    available_roles = db.query(Role).all()
                    role_ids = [r.id for r in available_roles]
                    raise HTTPException(
                        status_code=404, 
                        detail=f"Role with ID {user_role.role_id} not found. Available role IDs: {role_ids}"
                    )
            else:
                # Roles exist but the requested one doesn't
                available_roles = db.query(Role).all()
                role_ids = [r.id for r in available_roles]
                raise HTTPException(
                    status_code=404, 
                    detail=f"Role with ID {user_role.role_id} not found. Available role IDs: {role_ids}"
                )
        
        user = None
        # Handle either user_id or email
        if user_role.user_id:
            user = db.query(User).filter(User.id == user_role.user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail=f"User with ID {user_role.user_id} not found")
        elif user_role.email:
            user = db.query(User).filter(User.email == user_role.email).first()
            if not user:
                # If user doesn't exist, create a new user
                name = user_role.email.split('@')[0].replace('.', ' ').title()
                user = User(
                    name=name,
                    email=user_role.email,
                    department=user_role.department
                )
                db.add(user)
                db.flush()  
        else:
            raise HTTPException(status_code=400, detail="Either user_id or email must be provided")
        
        # Calculate expiry date if not unrestricted
        expiry_date = None
        if not user_role.is_unrestricted:
            expiry_date = calculate_expiry_date(
                days=user_role.duration_days,
                months=user_role.duration_months,
                years=user_role.duration_years
            )
        
        # Create the user role
        new_user_role = UserRole(
            user_id=user.id,
            role_id=role.id,
            department=user_role.department,
            job_ids=user_role.job_ids,
            is_unrestricted=user_role.is_unrestricted,
            duration_days=user_role.duration_days,
            duration_months=user_role.duration_months,
            duration_years=user_role.duration_years,
            expiry_date=expiry_date
        )
        
        db.add(new_user_role)
        db.commit()
        db.refresh(new_user_role)
        
        # Format response
        jobs_str = "All"
        if new_user_role.job_ids:
            if len(new_user_role.job_ids) == 1:
                jobs_str = new_user_role.job_ids[0]
            elif new_user_role.department and ("Departmental Head" in role.name or "Departmental Representative" in role.name):
                jobs_str = "All departmental jobs"
            elif len(new_user_role.job_ids) > 1:
                jobs_str = f"Multiple ({len(new_user_role.job_ids)})"
        
        # Format duration
        if new_user_role.is_unrestricted:
            duration_str = "Unrestricted"
        elif new_user_role.expiry_date:
            days_remaining = (new_user_role.expiry_date - datetime.utcnow()).days
            if new_user_role.duration_years:
                duration_str = f"{new_user_role.duration_years} years"
            elif new_user_role.duration_months:
                duration_str = f"{new_user_role.duration_months} months"
            else:
                duration_str = f"{new_user_role.duration_days} days"
        else:
            duration_str = "Unlimited"
        
        return UserRoleResponse(
            id=new_user_role.id,
            name=user.name,
            email=user.email,
            department=new_user_role.department or user.department or "General",
            role=role.name,
            selectedJobs=jobs_str,
            duration=duration_str
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        print(f"Error creating user role: {e}")
        # Roll back the transaction
        db.rollback()
        # Return a generic error
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    

@router.put("/{user_role_id}", response_model=UserRoleResponse)
def update_user_role(
    user_role_id: int = Path(..., title="The ID of the user role to update"),
    update_data: UserRoleUpdate = Body(...),
    db: Session = Depends(get_db)
):
    """Update an existing user role with improved error handling"""
    try:
        # Find user role by ID
        user_role = db.query(UserRole).filter(UserRole.id == user_role_id).first()
        if not user_role:
            raise HTTPException(status_code=404, detail=f"User role with ID {user_role_id} not found")
        
        # Get user information
        user = db.query(User).filter(User.id == user_role.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail=f"User with ID {user_role.user_id} not found")
        
        # Get current role information
        current_role = db.query(Role).filter(Role.id == user_role.role_id).first()
        if not current_role:
            # Current role doesn't exist, let's check available roles
            available_roles = db.query(Role).all()
            if not available_roles:
                # No roles exist, seed them
                seed_default_roles()
                available_roles = db.query(Role).all()
            
            role_ids = [r.id for r in available_roles]
            
            # If roles exist but current one doesn't, assign the first available role
            if available_roles:
                current_role = available_roles[0]
                user_role.role_id = current_role.id
                print(f"Warning: Assigned role ID {current_role.id} since role ID {user_role.role_id} not found")
            else:
                raise HTTPException(
                    status_code=404, 
                    detail=f"No roles found in the database. Please add roles before updating user roles."
                )
        
        # Update role if provided
        role = current_role  
        if update_data.role_id is not None:
            new_role = db.query(Role).filter(Role.id == update_data.role_id).first()
            if not new_role:
                # Get available roles
                available_roles = db.query(Role).all()
                role_ids = [r.id for r in available_roles]
                raise HTTPException(
                    status_code=404, 
                    detail=f"Role with ID {update_data.role_id} not found. Available role IDs: {role_ids}"
                )
            user_role.role_id = update_data.role_id
            role = new_role
        
        # Update other fields if provided
        if update_data.department is not None:
            user_role.department = update_data.department
        
        if update_data.job_ids is not None:
            user_role.job_ids = update_data.job_ids
        
        if update_data.is_unrestricted is not None:
            user_role.is_unrestricted = update_data.is_unrestricted
            
            # If unrestricted is now True, clear duration fields
            if update_data.is_unrestricted:
                user_role.duration_days = None
                user_role.duration_months = None
                user_role.duration_years = None
                user_role.expiry_date = None
        
        # Update duration if provided and not unrestricted
        if not user_role.is_unrestricted:
            duration_updated = False
            
            if update_data.duration_days is not None:
                user_role.duration_days = update_data.duration_days
                duration_updated = True
            
            if update_data.duration_months is not None:
                user_role.duration_months = update_data.duration_months
                duration_updated = True
            
            if update_data.duration_years is not None:
                user_role.duration_years = update_data.duration_years
                duration_updated = True
            
            # Recalculate expiry date if any duration field was updated
            if duration_updated:
                user_role.expiry_date = calculate_expiry_date(
                    days=user_role.duration_days or 0,
                    months=user_role.duration_months or 0,
                    years=user_role.duration_years or 0
                )
        
        db.commit()
        db.refresh(user_role)
        
        # Format response
        jobs_str = "All"
        if user_role.job_ids:
            if len(user_role.job_ids) == 1:
                jobs_str = user_role.job_ids[0]
            elif user_role.department and ("Departmental Head" in role.name or "Departmental Representative" in role.name):
                jobs_str = "All departmental jobs"
            elif len(user_role.job_ids) > 1:
                jobs_str = f"Multiple ({len(user_role.job_ids)})"
        
        # Format duration
        if user_role.is_unrestricted:
            duration_str = "Unrestricted"
        elif user_role.expiry_date:
            days_remaining = (user_role.expiry_date - datetime.utcnow()).days
            if days_remaining <= 0:
                duration_str = "Expired"
            elif days_remaining <= 7:
                duration_str = f"{days_remaining} days remaining"
            elif user_role.duration_years:
                duration_str = f"{user_role.duration_years} years"
            elif user_role.duration_months:
                duration_str = f"{user_role.duration_months} months"
            else:
                duration_str = f"{user_role.duration_days} days"
        else:
            duration_str = "Unlimited"
        
        return UserRoleResponse(
            id=user_role.id,
            name=user.name,
            email=user.email,
            department=user_role.department or user.department or "General",
            role=role.name,
            selectedJobs=jobs_str,
            duration=duration_str
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        print(f"Error updating user role: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.delete("/{user_role_id}", status_code=204)
async def delete_user_role(
    user_role_id: int = Path(..., title="The ID of the user role to delete"),
    db: Session = Depends(get_db),
    current_user: str = "taadmin"
):
    """Delete a user role assignment with real-time notification"""
    logger.info(f"DELETE /user-roles/{user_role_id} called by {current_user}")
    
    from app.routes.realtime_access_revoke import revoke_user_role, AccessRevocationPayload
    
    logger.info(f"Calling revoke_user_role for user_role_id: {user_role_id}")
    
    # Use the real-time revocation function
    result = await revoke_user_role(
        user_role_id=user_role_id,
        revoked_by=current_user,
        revocation_reason="User role deleted by admin",
        db=db
    )
    
    logger.info(f"Revoke result - success: {result.success}, message: {result.message}, event_published: {result.event_published}")
    
    if result.success:
        return {"message": result.message, "event_published": result.event_published}
    else:
        logger.error(f"Failed to revoke user role for user_role_id: {user_role_id}")
        raise HTTPException(status_code=500, detail="Failed to revoke user role")


# --- Start of commented out UserRoleAccess routes (moved to app/routes/candidates.py) ---
# @router.get("/user-role-access", response_model=List[UserRoleAccessResponse])
# def get_user_role_access(db: Session = Depends(get_db)):
#     """Get all user role access"""
#     user_role_access = db.query(UserRoleAccess).all()
#     return user_role_access

# @router.post("/user-role-access", response_model=UserRoleAccessResponse)
# def create_user_role_access(user_role_access: UserRoleAccessCreate, db: Session = Depends(get_db)):
#     """Create a new user role access"""
#     db_user_role_access = UserRoleAccess(**user_role_access.dict())
#     db.add(db_user_role_access)
#     db.commit()
#     db.refresh(db_user_role_access)
#     return db_user_role_access

# @router.put("/user-role-access/{user_role_access_id}", response_model=UserRoleAccessResponse)
# def update_user_role_access(user_role_access_id: int, user_role_access: UserRoleAccessUpdate, db: Session = Depends(get_db)):
#     """Update an existing user role access"""
#     db_user_role_access = db.query(UserRoleAccess).filter(UserRoleAccess.id == user_role_access_id).first()
#     if not db_user_role_access:
#         raise HTTPException(status_code=404, detail="User role access not found")
    
#     for key, value in user_role_access.dict().items():
#         setattr(db_user_role_access, key, value)
        
#     db.commit()
#     db.refresh(db_user_role_access)
#     return db_user_role_access

# @router.delete("/user-role-access/{user_role_access_id}", status_code=204)
# def delete_user_role_access(user_role_access_id: int, db: Session = Depends(get_db)):
#     """Delete a user role access"""
#     db_user_role_access = db.query(UserRoleAccess).filter(UserRoleAccess.id == user_role_access_id).first()
#     if not db_user_role_access:
#         raise HTTPException(status_code=404, detail="User role access not found")
    
#     db.delete(db_user_role_access)
#     db.commit()
    
#     return None

# @router.get("/user-access-summary", response_model=List[UserAccessSummary])
# def get_user_access_summary(db: Session = Depends(get_db)):
#     """Get a summary of user access roles"""
#     user_roles = db.query(UserRole).all()
    
#     summary = []
#     for ur in user_roles:
#         user = db.query(User).filter(User.id == ur.user_id).first()
#         role = db.query(Role).filter(Role.id == ur.role_id).first()
        
#         if user and role:
#             summary.append(UserAccessSummary(
#                 id=ur.id,
#                 name=user.name,
#                 email=user.email,
#                 department=ur.department or user.department,
#                 role=role.name,
#                 access_level="All Jobs" if not ur.job_ids else f"Jobs: {', '.join(ur.job_ids)}",
#                 duration="Unrestricted" if ur.is_unrestricted else f"Expires on {ur.expiry_date.strftime('%Y-%m-%d') if ur.expiry_date else 'N/A'}"
#             ))
            
#     return summary

# @router.get("/role-access-details/{role_id}", response_model=RoleAccessDetails)
# def get_role_access_details(role_id: int, db: Session = Depends(get_db)):
#     """Get detailed access permissions for a specific role"""
#     role = db.query(Role).filter(Role.id == role_id).first()
#     if not role:
#         raise HTTPException(status_code=404, detail="Role not found")
    
#     access_rights = db.query(UserRoleAccess).filter(UserRoleAccess.role_id == role_id).all()
    
#     return RoleAccessDetails(
#         role_id=role.id,
#         role_name=role.name,
#         access_rights=[
#             PageAccessResponse(
#                 id=ar.id,
#                 page_name=ar.page_name,
#                 can_view=ar.can_view,
#                 can_edit=ar.can_edit,
#                 can_delete=ar.can_delete
#             ) for ar in access_rights
#         ]
#     )

# @router.post("/role-access-details", status_code=201)
# def set_role_access_details(access_details: RoleAccessDetails, db: Session = Depends(get_db)):
#     """Set or update access permissions for a role"""
#     role = db.query(Role).filter(Role.id == access_details.role_id).first()
#     if not role:
#         raise HTTPException(status_code=404, detail="Role not found")
    
#     # Clear existing access rights for this role
#     db.query(UserRoleAccess).filter(UserRoleAccess.role_id == access_details.role_id).delete()
    
#     # Add new access rights
#     for ar_data in access_details.access_rights:
#         new_ar = UserRoleAccess(
#             role_id=access_details.role_id,
#             page_name=ar_data.page_name,
#             can_view=ar_data.can_view,
#             can_edit=ar.can_edit,
#             can_delete=ar.can_delete
#         )
#         db.add(new_ar)
        
#     db.commit()
    
#     return {"message": f"Access rights for role '{role.name}' updated successfully"}

# @router.get("/page-access", response_model=List[PageAccessResponse])
# def get_page_access(db: Session = Depends(get_db)):
#     """Get all page access settings"""
#     page_access = db.query(PageAccess).all()
#     return page_access

# @router.post("/page-access", response_model=PageAccessResponse)
# def create_page_access(page_access: PageAccessCreate, db: Session = Depends(get_db)):
#     """Create a new page access setting"""
#     db_page_access = PageAccess(**page_access.dict())
#     db.add(db_page_access)
#     db.commit()
#     db.refresh(db_page_access)
#     return db_page_access

# @router.get("/subpage-access", response_model=List[SubpageAccessResponse])
# def get_subpage_access(db: Session = Depends(get_db)):
#     """Get all subpage access settings"""
#     subpage_access = db.query(SubpageAccess).all()
#     return subpage_access

# @router.post("/subpage-access", response_model=SubpageAccessResponse)
# def create_subpage_access(subpage_access: SubpageAccessCreate, db: Session = Depends(get_db)):
#     """Create a new subpage access setting"""
#     db_subpage_access = SubpageAccess(**subpage_access.dict())
#     db.add(db_subpage_access)
#     db.commit()
#     db.refresh(db_subpage_access)
#     return db_subpage_access

# @router.get("/section-access", response_model=List[SectionAccessResponse])
# def get_section_access(db: Session = Depends(get_db)):
#     """Get all section access settings"""
#     section_access = db.query(SectionAccess).all()
#     return section_access

# @router.post("/section-access", response_model=SectionAccessResponse)
# def create_section_access(section_access: SectionAccessCreate, db: Session = Depends(get_db)):
#     """Create a new section access setting"""
#     db_section_access = SectionAccess(**section_access.dict())
#     db.add(db_section_access)
#     db.commit()
#     db.refresh(db_section_access)
#     return db_section_access

# @router.get("/user-role-access/paginated", response_model=PaginatedUserRoleAccess)
# def get_paginated_user_role_access(
#     page: int = 1,
#     items_per_page: int = 10,
#     filters: UserRoleAccessFilter = Depends(),
#     db: Session = Depends(get_db)
# ):
#     """Get paginated user role access with filtering"""
#     query = db.query(UserRoleAccess)
    
#     if filters.role_id:
#         query = query.filter(UserRoleAccess.role_id == filters.role_id)
#     if filters.page_name:
#         query = query.filter(UserRoleAccess.page_name.ilike(f"%{filters.page_name}%"))
    
#     total = query.count()
#     items = query.offset((page - 1) * items_per_page).limit(items_per_page).all()
    
#     return {
#         "items": items,
#         "total": total,
#         "page": page,
#         "items_per_page": items_per_page
#     }
# --- End of commented out UserRoleAccess routes ---