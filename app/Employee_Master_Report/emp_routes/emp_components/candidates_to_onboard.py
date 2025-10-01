from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, date
from typing import List

from app.database import get_db
from app.models import Candidate
from app.Employee_Master_Report.emp_models.employee_master import EmployeeMaster
from app.Employee_Master_Report.emp_schema.candidate_onboard import CandidateOnboardOut


router = APIRouter(prefix="/employee-master", tags=["Employee Master Report"])


def _parse_date(value: str) -> date | None:
    if not value:
        return None
    # Try a few common formats since Candidate.date_of_joining is a string
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%b-%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


@router.get("/candidates-to-onboard", response_model=List[CandidateOnboardOut])
def get_candidates_to_onboard(db: Session = Depends(get_db)) -> List[CandidateOnboardOut]:
    # Step 1: Pull candidates that are Offer Accepted and have an expected DOJ
    candidates = (
        db.query(Candidate)
        .filter(
            Candidate.current_status.in_(["Offer Accepted", "OFFER_ACCEPTED"]),
            Candidate.expected_date_of_joining.isnot(None),
        )
        .all()
    )

    # Step 2: Filter by date condition: expected DOJ must be today
    today = date.today()
    eligible: List[Candidate] = []
    for c in candidates:
        expected = _parse_date(getattr(c, "expected_date_of_joining", None))
        if expected and expected == today:
            eligible.append(c)

    if not eligible:
        return []

    # Step 3: Exclude those already present in employee_master using PAN or email match
    pans = [c.pan_card_no for c in eligible if getattr(c, "pan_card_no", None)]
    emails = [c.email_id for c in eligible if getattr(c, "email_id", None)]

    existing_pans = set()
    if pans:
        for (pan,) in db.query(EmployeeMaster.pan_card_no).filter(EmployeeMaster.pan_card_no.in_(pans)).all():
            if pan:
                existing_pans.add(pan)

    existing_emails = set()
    if emails:
        for (email,) in (
            db.query(EmployeeMaster.personal_email_id)
            .filter(EmployeeMaster.personal_email_id.in_(emails))
            .all()
        ):
            if email:
                existing_emails.add(email)

    result: List[CandidateOnboardOut] = []
    for c in eligible:
        # Exclude if present by PAN or email
        if (c.pan_card_no and c.pan_card_no in existing_pans) or (
            c.email_id and c.email_id in existing_emails
        ):
            continue

        result.append(CandidateOnboardOut.model_validate(c))

    return result


