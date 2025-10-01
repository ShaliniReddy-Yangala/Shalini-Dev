from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_, desc, asc, false
from typing import Optional, List
from datetime import datetime, date, timedelta
from pydantic import BaseModel

from app.database import get_db
from app.models import Candidate, InterviewStatusDB, InterviewTeam, SecondInterviewTeam, HRTeam
from app.schemas import PaginatedCandidateResponse

router = APIRouter(prefix="/candidates/interviewer", tags=["interviewer-candidates"])


class InterviewUpdateRequest(BaseModel):
    l1_interview_date: Optional[str] = None
    l1_interviewers_name: Optional[str] = None
    l1_status: Optional[str] = None
    l1_feedback: Optional[str] = None
    l2_interview_date: Optional[str] = None
    l2_interviewers_name: Optional[str] = None
    l2_status: Optional[str] = None
    l2_feedback: Optional[str] = None
    hr_interview_date: Optional[str] = None
    hr_interviewer_name: Optional[str] = None
    hr_status: Optional[str] = None
    hr_feedback: Optional[str] = None


@router.get("/alldetails", response_model=PaginatedCandidateResponse)
def get_interviewer_candidates_details(
    db: Session = Depends(get_db),
    page: int = 1,
    items_per_page: int = 6,
    search: Optional[str] = None,
    sort_key: Optional[str] = None,
    sort_order: Optional[str] = "asc",
    interviewer_email: Optional[str] = None,
    # General status filters
    current_status: Optional[str] = None,
    final_status: Optional[str] = None,
    # Stage state filters
    l1_state: Optional[str] = None,  # pending | done | all
    l2_state: Optional[str] = None,  # pending | done | all
    hr_state: Optional[str] = None,  # pending | done | all
    # L1 Interview filters
    l1_date: Optional[str] = None,  # Single date or range: DD-MM-YYYY or DD-MM-YYYY,DD-MM-YYYY
    l1_status: Optional[str] = None,
    # L2 Interview filters
    l2_date: Optional[str] = None,  # Single date or range: DD-MM-YYYY or DD-MM-YYYY,DD-MM-YYYY
    l2_status: Optional[str] = None,
    # HR Interview filters
    hr_date: Optional[str] = None,  # Single date or range: DD-MM-YYYY or DD-MM-YYYY,DD-MM-YYYY
    hr_status: Optional[str] = None,
    # Include job & salary details
    include_job_salary_details: bool = False,
):
    """
    Get candidate details for interviewers with specific filtering and sorting.
    Returns only essential candidate information needed for interview process.
    """
    try:
        print(f"Received parameters: page={page}, items_per_page={items_per_page}, "
              f"search={search}, sort_key={sort_key}, sort_order={sort_order}, "
              f"interviewer_email={interviewer_email}, "
              f"current_status={current_status}, final_status={final_status}, "
              f"l1_state={l1_state}, l2_state={l2_state}, hr_state={hr_state}, "
              f"l1_date={l1_date}, l1_status={l1_status}, l2_date={l2_date}, l2_status={l2_status}, "
              f"hr_date={hr_date}, hr_status={hr_status}, include_job_salary_details={include_job_salary_details}")

        # Base query
        query = db.query(Candidate)

        interviewer_role = None
        explanation_parts = []

        # Apply search filter
        if search:
            query = query.filter(
                or_(
                    Candidate.candidate_name.ilike(f"%{search}%"),
                    Candidate.email_id.ilike(f"%{search}%"),
                    Candidate.mobile_no.ilike(f"%{search}%"),
                    Candidate.candidate_id.ilike(f"%{search}%")
                )
            )

        # Current status filter (case-insensitive)
        if current_status and current_status != "all":
            query = query.filter(func.lower(Candidate.current_status) == current_status.lower())

        # Final status filter (case-insensitive)
        if final_status and final_status != "all":
            query = query.filter(func.lower(Candidate.final_status) == final_status.lower())

        # Interviewer email-based access filter (email-only; ignore team table alignment)
        if interviewer_email and interviewer_email.strip():
            email_key = interviewer_email.strip().lower()
            token = email_key.split("@", 1)[0]

            def build_token_clause(column, token_val: str):
                col_clean = func.replace(func.lower(column), " ", "")
                t = token_val
                return or_(
                    col_clean == t,
                    col_clean.like(func.concat(t, ",%")),
                    col_clean.like(func.concat("%,", t, ",%")),
                    col_clean.like(func.concat("%,", t)),
                )

            query = query.filter(
                or_(
                    build_token_clause(Candidate.l1_interviewers_name, token),
                    build_token_clause(Candidate.l2_interviewers_name, token),
                    build_token_clause(Candidate.hr_interviewer_name, token),
                )
            )

            explanation_parts.append(
                f"access: email-only; interviewer_email={email_key}; token={token}"
            )

        # Stage state filtering (pending/done) with defaults
        if not any([l1_state, l2_state, hr_state]):
            l1_state, l2_state, hr_state = "pending", "done", "pending"

        # Load unified interview status list (case-insensitive set)
        interview_status_values = [s[0] for s in db.query(InterviewStatusDB.status).all() if s[0]]
        interview_status_lower = set([s.lower() for s in interview_status_values])

        def apply_state_filter(column, state_value):
            if not state_value or state_value == "all":
                return None
            sv = state_value.lower()
            if sv == "done":
                # status present and in unified list
                return and_(
                    column.isnot(None),
                    func.trim(column) != "",
                    func.lower(column).in_(interview_status_lower)
                )
            if sv == "pending":
                # status null/empty or not in unified list
                return or_(
                    column.is_(None),
                    func.trim(column) == "",
                    func.lower(column).notin_(interview_status_lower)
                )
            return None

        l1_state_clause = apply_state_filter(Candidate.l1_status, l1_state)
        l2_state_clause = apply_state_filter(Candidate.l2_status, l2_state)
        hr_state_clause = apply_state_filter(Candidate.hr_status, hr_state)

        # Apply stage clauses (AND combination)
        for clause in [l1_state_clause, l2_state_clause, hr_state_clause]:
            if clause is not None:
                query = query.filter(clause)

        # Stage filter explanation
        explanation_parts.append(
            f"stage_states: l1={l1_state or 'default'}, l2={l2_state or 'default'}, hr={hr_state or 'default'}"
        )

        # Helper function to parse date string in DD-MM-YYYY format
        def _parse_date_str(date_str: str) -> date:
            try:
                return datetime.strptime(date_str.strip(), '%d-%m-%Y').date()
            except ValueError:
                raise HTTPException(status_code=400, detail=f'Invalid date format: {date_str}. Use DD-MM-YYYY format.')

        # L1 Interview date filtering
        if l1_date:
            try:
                if ',' in l1_date:
                    start_str, end_str = [part.strip() for part in l1_date.split(',', 1)]
                    start_date = _parse_date_str(start_str)
                    end_date = _parse_date_str(end_str)
                    end_date_plus_one = end_date + timedelta(days=1)
                    query = query.filter(
                        and_(
                            Candidate.l1_interview_date >= start_date,
                            Candidate.l1_interview_date < end_date_plus_one
                        )
                    )
                else:
                    single_date = _parse_date_str(l1_date)
                    query = query.filter(Candidate.l1_interview_date == single_date)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

        # L1 Interview status filtering
        if l1_status and l1_status != "all":
            query = query.filter(func.lower(Candidate.l1_status) == l1_status.lower())

        # L2 Interview date filtering
        if l2_date:
            try:
                if ',' in l2_date:
                    start_str, end_str = [part.strip() for part in l2_date.split(',', 1)]
                    start_date = _parse_date_str(start_str)
                    end_date = _parse_date_str(end_str)
                    end_date_plus_one = end_date + timedelta(days=1)
                    query = query.filter(
                        and_(
                            Candidate.l2_interview_date >= start_date,
                            Candidate.l2_interview_date < end_date_plus_one
                        )
                    )
                else:
                    single_date = _parse_date_str(l2_date)
                    query = query.filter(Candidate.l2_interview_date == single_date)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

        # L2 Interview status filtering
        if l2_status and l2_status != "all":
            query = query.filter(func.lower(Candidate.l2_status) == l2_status.lower())

        # HR Interview date filtering
        if hr_date:
            try:
                if ',' in hr_date:
                    start_str, end_str = [part.strip() for part in hr_date.split(',', 1)]
                    start_date = _parse_date_str(start_str)
                    end_date = _parse_date_str(end_str)
                    end_date_plus_one = end_date + timedelta(days=1)
                    query = query.filter(
                        and_(
                            Candidate.hr_interview_date >= start_date,
                            Candidate.hr_interview_date < end_date_plus_one
                        )
                    )
                else:
                    single_date = _parse_date_str(hr_date)
                    query = query.filter(Candidate.hr_interview_date == single_date)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

        # HR Interview status filtering
        if hr_status and hr_status != "all":
            query = query.filter(func.lower(Candidate.hr_status) == hr_status.lower())

        # Apply sorting
        if sort_key and sort_key != "all" and sort_key.strip():
            print(f"Applying sorting: sort_key={sort_key}, sort_order={sort_order}")

            sort_expr = None

            if sort_key == "candidate_id":
                sort_expr = Candidate.candidate_id
            elif sort_key == "candidate_name":
                sort_expr = Candidate.candidate_name
            elif sort_key == "gender":
                sort_expr = Candidate.gender
            elif sort_key in ("email", "email_id"):
                sort_expr = Candidate.email_id
            elif sort_key in ("phone", "mobile_no"):
                sort_expr = Candidate.mobile_no
            elif sort_key in ("associated_job_id", "job_id"):
                sort_expr = Candidate.associated_job_id
            elif sort_key == "l1_status":
                sort_expr = Candidate.l1_status
            elif sort_key == "l2_status":
                sort_expr = Candidate.l2_status
            elif sort_key == "l1_date":
                sort_expr = Candidate.l1_interview_date
            elif sort_key == "l2_date":
                sort_expr = Candidate.l2_interview_date
            elif sort_key == "hr_status":
                sort_expr = Candidate.hr_status
            elif sort_key == "hr_date":
                sort_expr = Candidate.hr_interview_date

            if sort_expr is not None:
                if (sort_order or "asc").lower() == "desc":
                    query = query.order_by(sort_expr.desc().nulls_last())
                else:
                    query = query.order_by(sort_expr.asc().nulls_last())
            else:
                print(f"Invalid sort_key: {sort_key}, skipping sorting")

            explanation_parts.append(f"sorting: key={sort_key}, order={(sort_order or 'asc').lower()}")

        print(f"Generated SQL Query: {str(query)}")

        # Get total count for pagination
        total = query.count()
        print(f"Total candidates before pagination: {total}")

        # Apply pagination
        candidates = query.offset((page - 1) * items_per_page).limit(items_per_page).all()
        print(f"Retrieved candidates: {len(candidates)}")

        if not candidates:
            print("No candidates found, returning empty response.")
            return {
                "items": [],
                "total": total,
                "page": page,
                "items_per_page": items_per_page
            }

        # Build response with only required fields
        result = []
        for db_candidate in candidates:
            candidate_data = {
                # Basic Details
                "candidate_id": db_candidate.candidate_id,
                "candidate_name": db_candidate.candidate_name,
                "gender": db_candidate.gender,
                "email_id": db_candidate.email_id,
                "mobile_no": db_candidate.mobile_no,
                "pan_card_no": db_candidate.pan_card_no,
                "resume_path": db_candidate.resume_path,
                "date_of_resume_received": db_candidate.date_of_resume_received,
                "department": db_candidate.department,
                "associated_job_id": db_candidate.associated_job_id,
                "current_location": db_candidate.current_location,
                "application_date": db_candidate.application_date,
                "skills_set": db_candidate.skills_set,
                "current_company": db_candidate.current_company,
                "current_designation": db_candidate.current_designation,
                "years_of_exp": db_candidate.years_of_exp,
                "current_status": db_candidate.current_status,
                "final_status": db_candidate.final_status,
                "linkedin_url": db_candidate.linkedin_url,
                
                # L1 Interview Details
                "l1_interview_date": db_candidate.l1_interview_date,
                "l1_interviewers_name": db_candidate.l1_interviewers_name,
                "l1_status": db_candidate.l1_status,
                "l1_feedback": db_candidate.l1_feedback,
                
                # L2 Interview Details
                "l2_interview_date": db_candidate.l2_interview_date,
                "l2_interviewers_name": db_candidate.l2_interviewers_name,
                "l2_status": db_candidate.l2_status,
                "l2_feedback": db_candidate.l2_feedback,
                
                # HR Interview Details
                "hr_interview_date": db_candidate.hr_interview_date,
                "hr_interviewer_name": db_candidate.hr_interviewer_name,
                "hr_status": db_candidate.hr_status,
                "hr_feedback": db_candidate.hr_feedback,
            }

            # Add job & salary details if requested
            if include_job_salary_details:
                candidate_data.update({
                    # Job & Salary Details (gathered during screening)
                    "notice_period": db_candidate.notice_period,
                    "notice_period_units": db_candidate.notice_period_units,
                    "npd_info": db_candidate.npd_info,
                    "current_fixed_ctc": db_candidate.current_fixed_ctc,
                    "current_variable_pay": db_candidate.current_variable_pay,
                    "expected_fixed_ctc": db_candidate.expected_fixed_ctc,
                    "mode_of_work": db_candidate.mode_of_work,
                    "referred_by": db_candidate.referred_by,
                    "reason_for_job_change": db_candidate.reason_for_job_change,
                    "ta_team": db_candidate.ta_team,
                    "ta_comments": db_candidate.ta_comments,
                })

            result.append(candidate_data)

        print(f"Returning {len(result)} candidates.")
        explanation_parts.append(f"pagination: page={page}, items_per_page={items_per_page}, total_before_pagination={total}")
        if search:
            explanation_parts.append(f"search='{search}'")
        if current_status and current_status != "all":
            explanation_parts.append(f"current_status={current_status}")
        if final_status and final_status != "all":
            explanation_parts.append(f"final_status={final_status}")
        if include_job_salary_details:
            explanation_parts.append("include_job_salary_details=true")
        explanation = "; ".join(explanation_parts)
        return {
            "role": interviewer_role,
            "items": result,
            "total": total,
            "page": page,
            "items_per_page": items_per_page,
            "explanation": explanation
        }

    except Exception as e:
        print(f"Error in get_interviewer_candidates_details: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving interviewer candidates: {str(e)}"
        )


@router.put("/alldetails/{candidate_id}")
def update_interviewer_candidate_details(
    candidate_id: str,
    update_data: InterviewUpdateRequest = Body(...),
    db: Session = Depends(get_db)
):
    """
    Update interview details for a specific candidate.
    """
    try:
        # Find the candidate
        candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")

        # Helper function to parse date string
        def _parse_date_str(date_str: str) -> date:
            try:
                return datetime.strptime(date_str.strip(), '%d-%m-%Y').date()
            except ValueError:
                raise HTTPException(status_code=400, detail=f'Invalid date format: {date_str}. Use DD-MM-YYYY format.')

        # Update L1 Interview details
        if update_data.l1_interview_date is not None:
            if update_data.l1_interview_date:
                candidate.l1_interview_date = _parse_date_str(update_data.l1_interview_date)
            else:
                candidate.l1_interview_date = None

        if update_data.l1_interviewers_name is not None:
            candidate.l1_interviewers_name = update_data.l1_interviewers_name

        if update_data.l1_status is not None:
            candidate.l1_status = update_data.l1_status

        if update_data.l1_feedback is not None:
            candidate.l1_feedback = update_data.l1_feedback

        # Update L2 Interview details
        if update_data.l2_interview_date is not None:
            if update_data.l2_interview_date:
                candidate.l2_interview_date = _parse_date_str(update_data.l2_interview_date)
            else:
                candidate.l2_interview_date = None

        if update_data.l2_interviewers_name is not None:
            candidate.l2_interviewers_name = update_data.l2_interviewers_name

        if update_data.l2_status is not None:
            candidate.l2_status = update_data.l2_status

        if update_data.l2_feedback is not None:
            candidate.l2_feedback = update_data.l2_feedback

        # Update HR Interview details
        if update_data.hr_interview_date is not None:
            if update_data.hr_interview_date:
                candidate.hr_interview_date = _parse_date_str(update_data.hr_interview_date)
            else:
                candidate.hr_interview_date = None

        if update_data.hr_interviewer_name is not None:
            candidate.hr_interviewer_name = update_data.hr_interviewer_name

        if update_data.hr_status is not None:
            candidate.hr_status = update_data.hr_status

        if update_data.hr_feedback is not None:
            candidate.hr_feedback = update_data.hr_feedback

        # Save changes
        db.commit()
        db.refresh(candidate)

        return {
            "message": "Interview details updated successfully",
            "candidate_id": candidate_id,
            "updated_fields": {
                "l1_interview_date": update_data.l1_interview_date,
                "l1_interviewers_name": update_data.l1_interviewers_name,
                "l1_status": update_data.l1_status,
                "l1_feedback": update_data.l1_feedback,
                "l2_interview_date": update_data.l2_interview_date,
                "l2_interviewers_name": update_data.l2_interviewers_name,
                "l2_status": update_data.l2_status,
                "l2_feedback": update_data.l2_feedback,
                "hr_interview_date": update_data.hr_interview_date,
                "hr_interviewer_name": update_data.hr_interviewer_name,
                "hr_status": update_data.hr_status,
                "hr_feedback": update_data.hr_feedback,
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in update_interviewer_candidate_details: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error updating interview details: {str(e)}"
        )
