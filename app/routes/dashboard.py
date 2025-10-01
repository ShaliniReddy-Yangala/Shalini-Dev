import logging
from fastapi import APIRouter, FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Counter, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
import uvicorn
from enum import Enum
from datetime import date
import calendar
import math
import os
from sqlalchemy import create_engine, extract, func, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import pandas as pd

from app.database import get_db
from app.models import Candidate, Job, TimePeriod
from app.schemas import CandidateStatistics, DashboardOverview, JobStatistics, JobTrend, JobTypeDistributionList, MonthlyHires, PipelineFlow, PriorityDistributionList, SkillsList, TAMetricsAll

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Helper functions
def get_dates_for_period(time_period: TimePeriod, start_date=None, end_date=None):
    today = datetime.now()
    
    # Default case - handle unexpected TimePeriod values
    start_date = today - timedelta(days=30)  # Default to last 30 days
    end_date = today
    
    if time_period == TimePeriod.LAST_7_DAYS:
        end_date = today
        start_date = today - timedelta(days=7)
    elif time_period == TimePeriod.LAST_30_DAYS:
        end_date = today
        start_date = today - timedelta(days=30)
    elif time_period == TimePeriod.THIS_MONTH:
        end_date = today
        start_date = today.replace(day=1)
    elif time_period == TimePeriod.PAST_WEEK:
        end_date = today
        start_date = today - timedelta(days=today.weekday())
    elif time_period == TimePeriod.LAST_90_DAYS:
        end_date = today
        start_date = today - timedelta(days=90)
    elif time_period == TimePeriod.PAST_MONTH:
        end_date = today
        if today.month == 1:
            start_date = today.replace(year=today.year-1, month=12, day=1)
        else:
            start_date = today.replace(month=today.month-1, day=1)
    elif time_period == TimePeriod.LAST_QUARTER:
        end_date = today
        current_quarter = math.ceil(today.month / 3)
        if current_quarter == 1:
            start_date = today.replace(year=today.year-1, month=10, day=1)
        else:
            start_quarter_month = (current_quarter - 1) * 3 - 2
            start_date = today.replace(month=start_quarter_month, day=1)
    elif time_period == TimePeriod.THIS_YEAR:
        end_date = today
        start_date = today.replace(month=1, day=1)
    elif time_period == TimePeriod.PAST_YEAR:
        end_date = today
        start_date = today.replace(year=today.year-1, month=1, day=1)
    elif time_period == TimePeriod.CUSTOM:
        if not start_date or not end_date:
            raise HTTPException(status_code=400, detail="Custom date range requires both start_date and end_date")
        # Convert string dates to datetime objects if they're provided as strings
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%d-%m-%Y")
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, "%d-%m-%Y")
    
    # Safety check to ensure we never return None values
    if start_date is None or end_date is None:
        logger.warning(f"Invalid time_period value: {time_period}. Defaulting to LAST_30_DAYS.")
        start_date = today - timedelta(days=30)
        end_date = today
    
    return start_date, end_date

# Standardize department handling
def normalize_department(department):
    """Standardize department string for consistent handling"""
    if not department:
        return "ALL"
    
    # Handle case where department might be an enum
    if hasattr(department, 'value'):
        department = department.value
    
    # Standardize to uppercase for consistency
    return department.upper()

# Real data functions - These query the database instead of generating mock data
def get_job_statistics(db: Session, department: str, time_period=TimePeriod.LAST_30_DAYS, start_date=None, end_date=None):
    department = normalize_department(department)
    start_date, end_date = get_dates_for_period(time_period, start_date, end_date)
    
    # Convert dates to strings for SQL query
    start_date_str = start_date.strftime('%d-%m-%Y')
    end_date_str = end_date.strftime('%d-%m-%Y')
    
    # Build department filter
    dept_filter = ""
    if department != "ALL":
        dept_filter = f"AND department = '{department}'"
    
    query = text(f"""
        SELECT 
            COUNT(*) as total_jobs,
            SUM(CASE WHEN UPPER(status) = 'OPEN' THEN 1 ELSE 0 END) as open_jobs,
            SUM(CASE WHEN UPPER(status) = 'CLOSED' THEN 1 ELSE 0 END) as closed_jobs,
            SUM(CASE WHEN UPPER(created_by) = 'TA1' THEN 1 ELSE 0 END) as ta1_created_jobs,
            SUM(CASE WHEN UPPER(created_by) = 'TA2' THEN 1 ELSE 0 END) as ta2_created_jobs
        FROM job_requisitions
        WHERE 
            created_on BETWEEN :start_date AND :end_date
            {dept_filter}
    """)
    
    params = {"start_date": start_date_str, "end_date": end_date_str}
    if department != "ALL":
        params["department"] = department
    
    result = db.execute(query, params).fetchone()

    logger.info(f"Job statistics query returned: {result}")
    
    return {
        "totalJobs": result.total_jobs,
        "openJobs": result.open_jobs,
        "closedJobs": result.closed_jobs,
        "ta1CreatedJobs": result.ta1_created_jobs,
        "ta2CreatedJobs": result.ta2_created_jobs
    }


def get_job_trend(db: Session, department: str, time_period=TimePeriod.LAST_30_DAYS, start_date=None, end_date=None):
    department = normalize_department(department)
    start_date, end_date = get_dates_for_period(time_period, start_date, end_date)
    
    # Convert dates to strings for SQL query
    start_date_str = start_date.strftime('%d-%m-%Y')
    end_date_str = end_date.strftime('%d-%m-%Y')
    
    # Build department filter
    dept_filter = ""
    if department != "ALL":
        dept_filter = f"AND UPPER(department) = :department"
    
    query = text(f"""
        SELECT 
            to_char(created_on, 'Mon') as month, 
            COUNT(*) as jobs
        FROM job_requisitions
        WHERE 
            created_on BETWEEN :start_date AND :end_date
            {dept_filter}
        GROUP BY to_char(created_on, 'Mon'), EXTRACT(month FROM created_on)
        ORDER BY EXTRACT(month FROM created_on)
    """)
    
    params = {"start_date": start_date_str, "end_date": end_date_str}
    if department != "ALL":
        params["department"] = department
    
    results = db.execute(query, params).fetchall()
    
    # Add debugging
    logger.info(f"Job trend query returned {len(results)} rows")
    
    monthly_job_trend = [{"month": row.month, "jobs": row.jobs} for row in results]
    
    return {"monthlyJobTrend": monthly_job_trend}


def get_job_types(db: Session, department: str, time_period=TimePeriod.LAST_30_DAYS, start_date=None, end_date=None):
    department = normalize_department(department)
    start_date, end_date = get_dates_for_period(time_period, start_date, end_date)
    
    # Convert dates to strings for SQL query
    start_date_str = start_date.strftime('%d-%m-%Y')
    end_date_str = end_date.strftime('%d-%m-%Y')
    
    # Build department filter
    dept_filter = ""
    if department != "ALL":
         dept_filter = f"AND UPPER(department) = :department"
    
    query = text(f"""
        SELECT 
            COALESCE(job_type, 'Unknown') as type, 
            COUNT(*) as count
        FROM job_requisitions
        WHERE 
            created_on BETWEEN :start_date AND :end_date
            {dept_filter}
        GROUP BY job_type
        ORDER BY count DESC
    """)
    
    params = {"start_date": start_date_str, "end_date": end_date_str}
    if department != "ALL":
        params["department"] = department
    
    results = db.execute(query, params).fetchall()
    
    # Add debugging
    logger.info(f"Job types query returned {len(results)} rows")
    
    job_types = [{"type": row.type, "count": row.count} for row in results]
    
    return {"jobTypes": job_types}


def get_priority_distribution(db: Session, department: str, time_period=TimePeriod.LAST_30_DAYS, start_date=None, end_date=None):
    department = normalize_department(department)
    start_date, end_date = get_dates_for_period(time_period, start_date, end_date)
    
    # Convert dates to strings for SQL query
    start_date_str = start_date.strftime('%d-%m-%Y')
    end_date_str = end_date.strftime('%d-%m-%Y')
    
    # Build department filter
    dept_filter = ""
    if department != "ALL":
        dept_filter = f"AND UPPER(department) = :department"
    
    query = text(f"""
        SELECT 
           COALESCE(priority, 'Unknown') as priority, 
            COUNT(*) as count
        FROM job_requisitions
        WHERE 
            created_on BETWEEN :start_date AND :end_date
            {dept_filter}
        GROUP BY priority
        ORDER BY count DESC
    """)
    
    params = {"start_date": start_date_str, "end_date": end_date_str}
    if department != "ALL":
        params["department"] = department
    
    results = db.execute(query, params).fetchall()
    
    logger.info(f"Priority distribution query returned {len(results)} rows")
    
    priority_distribution = [{"priority": row.priority, "count": row.count} for row in results]
    
    return {"priorityDistribution": priority_distribution}


def fetch_candidate_statistics(db: Session, department: str, time_period=TimePeriod.LAST_30_DAYS, start_date=None, end_date=None):
    department = normalize_department(department)
    start_date, end_date = get_dates_for_period(time_period, start_date, end_date)
    
    start_date_str = start_date.strftime('%d-%m-%Y')
    end_date_str = end_date.strftime('%d-%m-%Y')
    
    dept_filter = ""
    if department != "ALL":
        dept_filter = f"AND UPPER(j.department) = :department"
    
    query = text(f"""
        SELECT 
            SUM(CASE WHEN UPPER(c.current_status) = 'SCREENING' THEN 1 ELSE 0 END) as screening,
            SUM(CASE WHEN UPPER(c.current_status) = 'SCHEDULED' THEN 1 ELSE 0 END) as scheduled,
            SUM(CASE WHEN UPPER(c.current_status) = 'ONBOARDING' THEN 1 ELSE 0 END) as onboarding,
            SUM(CASE WHEN UPPER(c.current_status) = 'DISCUSSIONS' THEN 1 ELSE 0 END) as discussions,
            SUM(CASE WHEN UPPER(c.current_status) = 'ONBOARDED' THEN 1 ELSE 0 END) as onboarded
        FROM candidates c
        JOIN job_requisitions j ON c.associated_job_id = j.job_id
        WHERE 
            c.created_at BETWEEN :start_date AND :end_date
            {dept_filter}
    """)
    
    params = {"start_date": start_date_str, "end_date": end_date_str}
    if department != "ALL":
        params["department"] = department
    
    result = db.execute(query, params).fetchone()
    logger.info(f"Candidate statistics query returned: {result}")
    
    return {
        "screening": result.screening if result and result.screening else 0,
        "scheduled": result.scheduled if result and result.scheduled else 0,
        "onboarding": result.onboarding if result and result.onboarding else 0,
        "discussions": result.discussions if result and result.discussions else 0,
        "onboarded": result.onboarded if result and result.onboarded else 0
    }



def fetch_pipeline_flow(
    db: Session, 
    department: str, 
    time_period=TimePeriod.LAST_30_DAYS, 
    start_date=None, 
    end_date=None
):
    department = normalize_department(department)
    start_date, end_date = get_dates_for_period(time_period, start_date, end_date)
    
    # Convert dates to strings for SQL query
    start_date_str = start_date.strftime('%d-%m-%Y')
    end_date_str = end_date.strftime('%d-%m-%Y')
    
    # Build department filter
    dept_filter = ""
    if department != "ALL":
        dept_filter = f"AND UPPER(j.department) = :department"
    
    query = text(f"""
        SELECT 
            COALESCE(c.current_status, 'Unknown') as stage, 
            COUNT(*) as count
        FROM candidates c
        JOIN job_requisitions j ON c.associated_job_id = j.job_id
        WHERE 
            c.updated_at BETWEEN :start_date AND :end_date
            {dept_filter}
        GROUP BY c.current_status
        ORDER BY COUNT(*) DESC
    """)
    
    params = {"start_date": start_date_str, "end_date": end_date_str}
    if department != "ALL":
        params["department"] = department
    
    results = db.execute(query, params).fetchall()
    
    # Add debugging
    logger.info(f"Pipeline flow query returned {len(results)} rows")
    
    pipeline_flow = [{"stage": row.stage, "count": row.count} for row in results]
    
    return {"pipelineFlow": pipeline_flow}


def get_candidate_skills_sql(db: Session, department: str, time_period=TimePeriod.LAST_30_DAYS, start_date=None, end_date=None):
    department = normalize_department(department)
    start_date, end_date = get_dates_for_period(time_period, start_date, end_date)
    # Convert dates to strings for SQL query
    start_date_str = start_date.strftime('%d-%m-%Y')
    end_date_str = end_date.strftime('%d-%m-%Y')
    # Build department filter
    dept_filter = ""
    if department != "ALL":
        dept_filter = f"AND UPPER(j.department) = :department"
    query = text(f"""
        WITH skill_list AS (
            SELECT
                c.candidate_id,
                unnest(string_to_array(COALESCE(c.skills_set, ''), ',')) as skill_name
            FROM candidates c
            JOIN job_requisitions j ON c.associated_job_id = j.job_id
            WHERE
                c.created_at BETWEEN :start_date AND :end_date
                AND c.skills_set IS NOT NULL
                AND c.skills_set != ''
                {dept_filter}
        )
        SELECT
            trim(skill_name) as skill,
            COUNT(*) as count
        FROM skill_list
        WHERE trim(skill_name) != ''
        GROUP BY trim(skill_name)
        ORDER BY count DESC
        LIMIT 10
    """)
    
    params = {"start_date": start_date_str, "end_date": end_date_str}
    if department != "ALL":
        params["department"] = department
    
    results = db.execute(query, params).mappings().all()
    
    # Add debugging
    logger.info(f"Candidate skills query returned {len(results)} rows")
    
    skills = [{"skill": row["skill"], "count": row["count"]} for row in results]
    return skills


def get_monthly_hires(db: Session, department: str, time_period=TimePeriod.LAST_30_DAYS, start_date=None, end_date=None):
    department = normalize_department(department)
    start_date_obj, end_date_obj = get_dates_for_period(time_period, start_date, end_date)
    
    # Calculate the start date for showing 6 months of data
    six_months_ago = end_date_obj - timedelta(days=180)
    if start_date_obj > six_months_ago:
        six_months_ago = start_date_obj
    
    # Convert dates to strings for SQL query
    start_date_str = six_months_ago.strftime('%d-%m-%Y')
    end_date_str = end_date_obj.strftime('%d-%m-%Y')
    
    # Build department filter
    dept_filter = ""
    if department != "ALL":
        dept_filter = f"AND UPPER(j.department) = :department"
    
    query = text(f"""
        SELECT 
            to_char(to_date(c.date_of_joining, 'YYYY-MM-DD'), 'Mon') as month, 
            COUNT(*) as hires
        FROM candidates c
        JOIN job_requisitions j ON c.associated_job_id = j.job_id
        WHERE 
            c.date_of_joining IS NOT NULL
            AND c.date_of_joining != ''
            AND to_date(c.date_of_joining, 'YYYY-MM-DD') BETWEEN :start_date AND :end_date
            AND UPPER(c.current_status) = 'ONBOARDED'
            {dept_filter}
        GROUP BY to_char(to_date(c.date_of_joining, 'YYYY-MM-DD'), 'Mon'), EXTRACT(month FROM to_date(c.date_of_joining, 'YYYY-MM-DD'))
        ORDER BY EXTRACT(month FROM to_date(c.date_of_joining, 'YYYY-MM-DD'))
    """)
    
    params = {"start_date": start_date_str, "end_date": end_date_str}
    if department != "ALL":
        params["department"] = department

    results = db.execute(query, params).mappings().all()
    
    # Add debugging
    logger.info(f"Monthly hires query returned {len(results)} rows")

    monthly_hires = [{"month": row["month"], "hires": row["hires"]} for row in results]
    
    return {"monthlyHires": monthly_hires}


def get_ta_performance(db: Session, ta_id: int, department: str, time_period=TimePeriod.LAST_30_DAYS, start_date=None, end_date=None):
    department = normalize_department(department)
    start_date, end_date = get_dates_for_period(time_period, start_date, end_date)
    
    # Calculate the start date for showing 6 months of data
    six_months_ago = end_date - timedelta(days=180)
    if start_date > six_months_ago:
        six_months_ago = start_date
    
    # Convert dates to strings for SQL query
    start_date_str = six_months_ago.strftime('%d-%m-%Y')
    end_date_str = end_date.strftime('%d-%m-%Y')
    
    # Build department filter
    dept_filter = ""
    if department != "ALL":
        dept_filter = f"AND UPPER(j.department) = :department"
    
    query = text(f"""
        SELECT 
            to_char(c.created_at, 'Mon') as month,
            COUNT(DISTINCT c.candidate_id) as sourced,
            COUNT(DISTINCT CASE WHEN UPPER(c.current_status) = 'ONBOARDED' THEN c.candidate_id ELSE NULL END) as hired
        FROM candidates c
        JOIN job_requisitions j ON c.associated_job_id = j.job_id
        WHERE 
            c.created_at BETWEEN :start_date AND :end_date
            AND UPPER(c.ta_team) = :ta_id
            {dept_filter}
        GROUP BY to_char(c.created_at, 'Mon'), EXTRACT(month FROM c.created_at)
        ORDER BY EXTRACT(month FROM c.created_at)
    """)
    
    params = {"start_date": start_date_str, "end_date": end_date_str, "ta_id": f"TA{ta_id}"}
    if department != "ALL":
        params["department"] = department
    
    results = db.execute(query, params).fetchall()
    
    # Add debugging
    logger.info(f"TA{ta_id} performance query returned {len(results)} rows")
    
    monthly_performance = [{"month": row.month, "sourced": row.sourced, "hired": row.hired} for row in results]
    
    return monthly_performance


def get_ta_metrics(db: Session, department: str, time_period=TimePeriod.LAST_30_DAYS, start_date=None, end_date=None):
    department = normalize_department(department)
    start_date, end_date = get_dates_for_period(time_period, start_date, end_date)
    
    # Convert dates to strings for SQL query
    start_date_str = start_date.strftime('%d-%m-%Y')
    end_date_str = end_date.strftime('%d-%m-%Y')
    
    # Build department filter
    dept_filter = ""
    dept_filter_jobs = ""
    if department != "ALL":
        dept_filter = f"AND UPPER(j.department) = :department"
        dept_filter_jobs = f"AND UPPER(department) = :department"
    
    # Get TA1 metrics
    ta1_query = text(f"""
        SELECT 
            (SELECT COUNT(*) FROM job_requisitions WHERE UPPER(created_by) = 'TA1' AND created_on BETWEEN :start_date AND :end_date {dept_filter_jobs}) as jobs_created,
            (SELECT COUNT(*) FROM candidates c JOIN job_requisitions j ON c.associated_job_id = j.job_id WHERE UPPER(c.ta_team) = 'TA1' AND c.created_at BETWEEN :start_date AND :end_date {dept_filter}) as candidates_sourced,
            (SELECT COUNT(*) FROM candidates c JOIN job_requisitions j ON c.associated_job_id = j.job_id WHERE UPPER(c.ta_team) = 'TA1' AND UPPER(c.current_status) = 'Screening' AND c.created_at BETWEEN :start_date AND :end_date {dept_filter}) as candidates_in_screening,
            (SELECT COUNT(*) FROM candidates c JOIN job_requisitions j ON c.associated_job_id = j.job_id WHERE UPPER(c.ta_team) = 'TA1' AND UPPER(c.offer_status) = 'OFFER_RELEASED' AND c.created_at BETWEEN :start_date AND :end_date {dept_filter}) as offers_released,
            (SELECT COUNT(*) FROM candidates c JOIN job_requisitions j ON c.associated_job_id = j.job_id WHERE UPPER(c.ta_team) = 'TA1' AND UPPER(c.current_status) = 'ONBOARDED' AND c.created_at BETWEEN :start_date AND :end_date {dept_filter}) as candidates_onboarded
    """)
    
    params = {"start_date": start_date_str, "end_date": end_date_str}
    if department != "ALL":
        params["department"] = department
    
    ta1_result = db.execute(ta1_query, params).fetchone()
    
    # Get TA2 metrics
    ta2_query = text(f"""
        SELECT 
            (SELECT COUNT(*) FROM job_requisitions WHERE UPPER(created_by) = 'TA2' AND created_on BETWEEN :start_date AND :end_date {dept_filter_jobs}) as jobs_created,
            (SELECT COUNT(*) FROM candidates c JOIN job_requisitions j ON c.associated_job_id = j.job_id WHERE UPPER(c.ta_team) = 'TA2' AND c.created_at BETWEEN :start_date AND :end_date {dept_filter}) as candidates_sourced,
            (SELECT COUNT(*) FROM candidates c JOIN job_requisitions j ON c.associated_job_id = j.job_id WHERE UPPER(c.ta_team) = 'TA2' AND UPPER(c.current_status) = 'SCREENING' AND c.created_at BETWEEN :start_date AND :end_date {dept_filter}) as candidates_in_screening,
            (SELECT COUNT(*) FROM candidates c JOIN job_requisitions j ON c.associated_job_id = j.job_id WHERE UPPER(c.ta_team) = 'TA2' AND UPPER(c.offer_status) = 'OFFER_RELEASED' AND c.created_at BETWEEN :start_date AND :end_date {dept_filter}) as offers_released,
            (SELECT COUNT(*) FROM candidates c JOIN job_requisitions j ON c.associated_job_id = j.job_id WHERE UPPER(c.ta_team) = 'TA2' AND UPPER(c.current_status) = 'ONBOARDED' AND c.created_at BETWEEN :start_date AND :end_date {dept_filter}) as candidates_onboarded
    """)
    
    ta2_result = db.execute(ta2_query, params).fetchone()
    
    # Get monthly performance data
    ta1_monthly = get_ta_performance(db, 1, department, time_period, start_date, end_date)
    ta2_monthly = get_ta_performance(db, 2, department, time_period, start_date, end_date)
    
    # Add debugging
    logger.info(f"TA1 metrics: {ta1_result}")
    logger.info(f"TA2 metrics: {ta2_result}")
    
    return {
        "ta1": {
            "jobsCreated": ta1_result.jobs_created if ta1_result and ta1_result.jobs_created else 0,
            "candidatesSourced": ta1_result.candidates_sourced if ta1_result and ta1_result.candidates_sourced else 0,
            "candidatesInScreening": ta1_result.candidates_in_screening if ta1_result and ta1_result.candidates_in_screening else 0,
            "offersReleased": ta1_result.offers_released if ta1_result and ta1_result.offers_released else 0,
            "candidatesOnboarded": ta1_result.candidates_onboarded if ta1_result and ta1_result.candidates_onboarded else 0,
            "monthlyPerformance": ta1_monthly
        },
        "ta2": {
            "jobsCreated": ta2_result.jobs_created if ta2_result and ta2_result.jobs_created else 0,
            "candidatesSourced": ta2_result.candidates_sourced if ta2_result and ta2_result.candidates_sourced else 0,
            "candidatesInScreening": ta2_result.candidates_in_screening if ta2_result and ta2_result.candidates_in_screening else 0,
            "offersReleased": ta2_result.offers_released if ta2_result and ta2_result.offers_released else 0,
            "candidatesOnboarded": ta2_result.candidates_onboarded if ta2_result and ta2_result.candidates_onboarded else 0,
            "monthlyPerformance": ta2_monthly
        }
    }

def get_dashboard_overview(db: Session, department: str, time_period=TimePeriod.LAST_30_DAYS, start_date=None, end_date=None):
    department = normalize_department(department)
    start_date, end_date = get_dates_for_period(time_period, start_date, end_date)
    
    # Convert dates to strings for SQL query
    start_date_str = start_date.strftime('%d-%m-%Y')
    end_date_str = end_date.strftime('%d-%m-%Y')
    
    # Build department filter
    dept_filter = ""
    if department != "ALL":
        dept_filter = f"AND UPPER(j.department) = :department"
    
    query = text(f"""
SELECT
    (SELECT AVG(EXTRACT(DAY FROM to_date(c.date_of_joining, 'YYYY-MM-DD') - c.created_at)) 
     FROM candidates c 
     JOIN job_requisitions j ON c.associated_job_id = j.job_id 
     WHERE UPPER(c.current_status) = 'ONBOARDED' 
       AND to_date(c.date_of_joining, 'YYYY-MM-DD') BETWEEN :start_date AND :end_date
       {dept_filter}) as avg_days_to_hire,
    
    (SELECT COUNT(*) 
     FROM candidates c 
     JOIN job_requisitions j ON c.associated_job_id = j.job_id 
     WHERE c.created_at >= CURRENT_DATE - INTERVAL '1 day' 
       {dept_filter}) as new_applications,
    
    (SELECT COUNT(*) 
     FROM candidates c 
     JOIN job_requisitions j ON c.associated_job_id = j.job_id 
     WHERE (
            c.l1_interview_date = CURRENT_DATE OR
            c.l2_interview_date = CURRENT_DATE OR
            c.hr_interview_date = CURRENT_DATE
          )
       {dept_filter}) as interviews_scheduled_today,
    
    (SELECT 
        CASE 
            WHEN offers_extended > 0 THEN (offers_accepted * 100.0 / offers_extended) 
            ELSE 0 
        END
     FROM (
        SELECT 
            COUNT(CASE WHEN UPPER(c.offer_status) IN ('OFFER_INITIATED', 'OFFER_ACCEPTED', 'OFFER_DECLINED') THEN 1 ELSE NULL END) as offers_extended,
            COUNT(CASE WHEN UPPER(c.offer_status) = 'OFFER_ACCEPTED' THEN 1 ELSE NULL END) as offers_accepted
        FROM candidates c
        JOIN job_requisitions j ON c.associated_job_id = j.job_id
        WHERE c.updated_at BETWEEN :start_date AND :end_date
          {dept_filter}
     ) as offer_stats) as offer_acceptance_rate,
    
    (SELECT COUNT(*) 
     FROM candidates c 
     JOIN job_requisitions j ON c.associated_job_id = j.job_id 
     WHERE UPPER(c.current_status) = 'HR_ROUND' 
       AND c.updated_at BETWEEN :start_date AND :end_date
       {dept_filter}) as candidates_in_final_stage
""")

    params = {"start_date": start_date_str, "end_date": end_date_str}
    if department != "ALL":
        params["department"] = department

    result = db.execute(query, params).fetchone()

    return {
        "avgDaysToHire": float(result.avg_days_to_hire) if result.avg_days_to_hire else 0.0,
        "newApplications": result.new_applications or 0,
        "interviewsScheduledToday": result.interviews_scheduled_today or 0,
        "offerAcceptanceRate": float(result.offer_acceptance_rate) if result.offer_acceptance_rate else 0.0,
        "candidatesInFinalStage": result.candidates_in_final_stage or 0
    }


router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/overview", response_model=DashboardOverview, tags=["Dashboard"])
async def get_dashboard_overview_endpoint(
    department: str = Query("ALL", description="Department filter"),
    time_period: TimePeriod = Query(TimePeriod.LAST_30_DAYS, description="Time period filter"),
    start_date: Optional[str] = Query(None, description="Start date for custom range (YYYY-MM-DD)", regex=r'^\d{4}-\d{2}-\d{2}$'),
    end_date: Optional[str] = Query(None, description="End date for custom range (YYYY-MM-DD)", regex=r'^\d{4}-\d{2}-\d{2}$'),
    db: Session = Depends(get_db)
):
    """
    Get overview statistics for the dashboard.
    
    Returns:
    - avgDaysToHire: Average days to hire a candidate
    - newApplications: Number of new applications received
    - interviewsScheduledToday: Number of interviews scheduled for today
    - offerAcceptanceRate: Percentage of offers accepted
    - candidatesInFinalStage: Number of candidates in the final stage
    """
    try:
        logger.info(f"Received dashboard overview request - department: {department}, time_period: {time_period}")
        
        # Process date range
        if time_period == TimePeriod.CUSTOM:
            if not start_date or not end_date:
                raise HTTPException(
                    status_code=400, 
                    detail="Custom date range requires both start_date and end_date in YYYY-MM-DD format"
                )
            
            # Validate date format and order
            try:
                from datetime import datetime
                start_dt = datetime.strptime(start_date, '%d-%m-%Y')
                end_dt = datetime.strptime(end_date, '%d-%m-%Y')
                
                if start_dt > end_dt:
                    raise HTTPException(
                        status_code=400,
                        detail="start_date must be before or equal to end_date"
                    )
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid date format. Use YYYY-MM-DD format"
                )
        
        # Get real data from database
        return get_dashboard_overview(db, department, time_period, start_date, end_date)
        
    except HTTPException:
        # Re-raise HTTP exceptions without modification
        raise
    except Exception as e:
        logger.error(f"Error in dashboard overview: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/jobs/statistics", response_model=JobStatistics, tags=["Jobs"])
async def get_job_statistics_endpoint(
    department: str = Query("ALL", description="Department filter"),
    time_period: TimePeriod = Query(TimePeriod.LAST_30_DAYS, description="Time period filter"),
    start_date: Optional[str] = Query(None, description="Start date for custom range (YYYY-MM-DD)", regex=r'^\d{4}-\d{2}-\d{2}$'),
    end_date: Optional[str] = Query(None, description="End date for custom range (YYYY-MM-DD)", regex=r'^\d{4}-\d{2}-\d{2}$'),
    db: Session = Depends(get_db)
):
    """
    Get job statistics.
    
    Returns:
    - totalJobs: Total number of jobs
    - openJobs: Number of open jobs
    - closedJobs: Number of closed jobs
    - ta1CreatedJobs: Number of jobs created by TA1
    - ta2CreatedJobs: Number of jobs created by TA2
    """
    try:
        logger.info(f"Received job statistics request - department: {department}, time_period: {time_period}")
        
        # Process date range
        if time_period == TimePeriod.CUSTOM:
            if not start_date or not end_date:
                raise HTTPException(
                    status_code=400, 
                    detail="Custom date range requires both start_date and end_date in YYYY-MM-DD format"
                )
            
            # Validate date format and order
            try:
                from datetime import datetime
                start_dt = datetime.strptime(start_date, '%d-%m-%Y')
                end_dt = datetime.strptime(end_date, '%d-%m-%Y')
                
                if start_dt > end_dt:
                    raise HTTPException(
                        status_code=400,
                        detail="start_date must be before or equal to end_date"
                    )
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid date format. Use YYYY-MM-DD format"
                )
        
        # Pass the db session to get_job_statistics
        return get_job_statistics(db, department, time_period, start_date, end_date)
        
    except HTTPException:
        # Re-raise HTTP exceptions without modification
        raise
    except Exception as e:
        logger.error(f"Error in job statistics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    
    
@router.get("/jobs/trend", response_model=JobTrend, tags=["Jobs"])
async def get_job_trend_endpoint(
    department: str = Query("ALL", description="Department filter"),
    time_period: TimePeriod = Query(TimePeriod.LAST_30_DAYS, description="Time period filter"),
    start_date: Optional[str] = Query(None, description="Start date for custom range (YYYY-MM-DD)", regex=r'^\d{4}-\d{2}-\d{2}$'),
    end_date: Optional[str] = Query(None, description="End date for custom range (YYYY-MM-DD)", regex=r'^\d{4}-\d{2}-\d{2}$'),
    db: Session = Depends(get_db)
):
    """
    Get job trend data.
    
    Returns:
    - monthlyJobTrend: List of job counts by month
    """
    try:
        logger.info(f"Received job trend request - department: {department}, time_period: {time_period}")
        
        # Process date range
        if time_period == TimePeriod.CUSTOM:
            if not start_date or not end_date:
                raise HTTPException(
                    status_code=400, 
                    detail="Custom date range requires both start_date and end_date in YYYY-MM-DD format"
                )
            
            # Validate date format and order
            try:
                from datetime import datetime
                start_dt = datetime.strptime(start_date, '%d-%m-%Y')
                end_dt = datetime.strptime(end_date, '%d-%m-%Y')
                
                if start_dt > end_dt:
                    raise HTTPException(
                        status_code=400,
                        detail="start_date must be before or equal to end_date"
                    )
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid date format. Use YYYY-MM-DD format"
                )
        
        # Call helper function and pass the db session as the first parameter
        return get_job_trend(db, department, time_period, start_date, end_date)
        
    except HTTPException:
        # Re-raise HTTP exceptions without modification
        raise
    except Exception as e:
        logger.error(f"Error getting job trend: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/jobs/types", response_model=JobTypeDistributionList, tags=["Jobs"])
async def get_job_types_endpoint(
    department: str = Query("ALL", description="Department filter"),
    time_period: TimePeriod = Query(TimePeriod.LAST_30_DAYS, description="Time period filter"),
    start_date: Optional[str] = Query(None, description="Start date for custom range (YYYY-MM-DD)", regex=r'^\d{4}-\d{2}-\d{2}$'),
    end_date: Optional[str] = Query(None, description="End date for custom range (YYYY-MM-DD)", regex=r'^\d{4}-\d{2}-\d{2}$'),
    db: Session = Depends(get_db)
):
    """
    Get job type distribution.
    
    Returns:
    - jobTypes: List of job types with counts
    """
    try:
        logger.info(f"Received job types request - department: {department}, time_period: {time_period}")
        
        # Process date range
        if time_period == TimePeriod.CUSTOM:
            if not start_date or not end_date:
                raise HTTPException(
                    status_code=400, 
                    detail="Custom date range requires both start_date and end_date in YYYY-MM-DD format"
                )
            
            # Validate date format and order
            try:
                from datetime import datetime
                start_dt = datetime.strptime(start_date, '%d-%m-%Y')
                end_dt = datetime.strptime(end_date, '%d-%m-%Y')
                
                if start_dt > end_dt:
                    raise HTTPException(
                        status_code=400,
                        detail="start_date must be before or equal to end_date"
                    )
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid date format. Use YYYY-MM-DD format"
                )
        
        # Call the correct function with the db parameter
        return get_job_types(db, department, time_period, start_date, end_date)
        
    except HTTPException:
        # Re-raise HTTP exceptions without modification
        raise
    except Exception as e:
        logger.error(f"Error getting job types: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/jobs/priority", response_model=PriorityDistributionList, tags=["Jobs"])
async def get_job_priority_endpoint(
    department: str = Query("ALL", description="Department filter"),
    time_period: TimePeriod = Query(TimePeriod.LAST_30_DAYS, description="Time period filter"),
    start_date: Optional[str] = Query(None, description="Start date for custom range (YYYY-MM-DD)", regex=r'^\d{4}-\d{2}-\d{2}$'),
    end_date: Optional[str] = Query(None, description="End date for custom range (YYYY-MM-DD)", regex=r'^\d{4}-\d{2}-\d{2}$'),
    db: Session = Depends(get_db)
):
    """
    Get job priority distribution.
    
    Returns:
    - priorityDistribution: List of priority levels with counts
    """
    try:
        logger.info(f"Received job priority request - department: {department}, time_period: {time_period}")
        
        # Process date range
        if time_period == TimePeriod.CUSTOM:
            if not start_date or not end_date:
                raise HTTPException(
                    status_code=400, 
                    detail="Custom date range requires both start_date and end_date in YYYY-MM-DD format"
                )
            
            # Validate date format and order
            try:
                from datetime import datetime
                start_dt = datetime.strptime(start_date, '%d-%m-%Y')
                end_dt = datetime.strptime(end_date, '%d-%m-%Y')
                
                if start_dt > end_dt:
                    raise HTTPException(
                        status_code=400,
                        detail="start_date must be before or equal to end_date"
                    )
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid date format. Use YYYY-MM-DD format"
                )
        
        return get_priority_distribution(db, department, time_period, start_date, end_date)
        
    except HTTPException:
        # Re-raise HTTP exceptions without modification
        raise
    except Exception as e:
        logger.error(f"Error getting job priority: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    
@router.get("/candidates/statistics", response_model=CandidateStatistics, tags=["Candidates"])
async def get_candidate_statistics_endpoint(
    department: str = Query("ALL", description="Department filter"),
    time_period: TimePeriod = Query(TimePeriod.LAST_30_DAYS, description="Time period filter"),
    start_date: Optional[str] = Query(None, description="Start date for custom range (YYYY-MM-DD)", regex=r'^\d{4}-\d{2}-\d{2}$'),
    end_date: Optional[str] = Query(None, description="End date for custom range (YYYY-MM-DD)", regex=r'^\d{4}-\d{2}-\d{2}$'),
    db: Session = Depends(get_db)
):
    """
    Get candidate statistics.
    
    Returns comprehensive candidate statistics including counts by status, source, etc.
    """
    try:
        logger.info(f"Received candidate statistics request - department: {department}, time_period: {time_period}")
        
        # Process date range
        if time_period == TimePeriod.CUSTOM:
            if not start_date or not end_date:
                raise HTTPException(
                    status_code=400, 
                    detail="Custom date range requires both start_date and end_date in YYYY-MM-DD format"
                )
            
            # Validate date format and order
            try:
                from datetime import datetime
                start_dt = datetime.strptime(start_date, '%d-%m-%Y')
                end_dt = datetime.strptime(end_date, '%d-%m-%Y')
                
                if start_dt > end_dt:
                    raise HTTPException(
                        status_code=400,
                        detail="start_date must be before or equal to end_date"
                    )
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid date format. Use YYYY-MM-DD format"
                )

        return fetch_candidate_statistics(db, department, time_period, start_date, end_date)
        
    except HTTPException:
        # Re-raise HTTP exceptions without modification
        raise
    except Exception as e:
        logger.error(f"Error getting candidate statistics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/candidates/pipeline", response_model=PipelineFlow, tags=["Candidates"])
async def get_pipeline_flow_endpoint(
    department: str = Query("ALL", description="Department filter"),
    time_period: TimePeriod = Query(TimePeriod.LAST_30_DAYS, description="Time period filter"),
    start_date: Optional[str] = Query(None, description="Start date for custom range (YYYY-MM-DD)", regex=r'^\d{4}-\d{2}-\d{2}$'),
    end_date: Optional[str] = Query(None, description="End date for custom range (YYYY-MM-DD)", regex=r'^\d{4}-\d{2}-\d{2}$'),
    db: Session = Depends(get_db)
):
    """
    Get candidate pipeline flow data.
    
    Returns the flow of candidates through different pipeline stages.
    """
    try:
        logger.info(f"Received pipeline flow request - department: {department}, time_period: {time_period}")
        
        # Process date range
        if time_period == TimePeriod.CUSTOM:
            if not start_date or not end_date:
                raise HTTPException(
                    status_code=400, 
                    detail="Custom date range requires both start_date and end_date in YYYY-MM-DD format"
                )
            
            # Validate date format and order
            try:
                from datetime import datetime
                start_dt = datetime.strptime(start_date, '%d-%m-%Y')
                end_dt = datetime.strptime(end_date, '%d-%m-%Y')
                
                if start_dt > end_dt:
                    raise HTTPException(
                        status_code=400,
                        detail="start_date must be before or equal to end_date"
                    )
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid date format. Use YYYY-MM-DD format"
                )
        
        return fetch_pipeline_flow(db, department, time_period, start_date, end_date)
        
    except HTTPException:
        # Re-raise HTTP exceptions without modification
        raise
    except Exception as e:
        logger.error(f"Error getting candidate pipeline flow: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/candidates/skills", response_model=SkillsList, tags=["Candidates"])
async def get_candidate_skills_endpoint(
    department: str = Query("ALL", description="Department filter"),
    time_period: TimePeriod = Query(TimePeriod.LAST_30_DAYS, description="Time period filter"),
    start_date: Optional[str] = Query(None, description="Start date for custom range (YYYY-MM-DD)", regex=r'^\d{4}-\d{2}-\d{2}$'),
    end_date: Optional[str] = Query(None, description="End date for custom range (YYYY-MM-DD)", regex=r'^\d{4}-\d{2}-\d{2}$'),
    db: Session = Depends(get_db)
):
    """
    Get top candidate skills.
    
    Returns:
    - candidatesBySkill: List of skills with counts
    """
    try:
        logger.info(f"Received candidate skills request - department: {department}, time_period: {time_period}")
        
        # Process date range
        if time_period == TimePeriod.CUSTOM:
            if not start_date or not end_date:
                raise HTTPException(
                    status_code=400, 
                    detail="Custom date range requires both start_date and end_date in YYYY-MM-DD format"
                )
            
            # Validate date format and order
            try:
                from datetime import datetime
                start_dt = datetime.strptime(start_date, '%d-%m-%Y')
                end_dt = datetime.strptime(end_date, '%d-%m-%Y')
                
                if start_dt > end_dt:
                    raise HTTPException(
                        status_code=400,
                        detail="start_date must be before or equal to end_date"
                    )
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid date format. Use DD-MM-YYYY format"
                )

        # Use the SQL implementation which is working correctly
        skills_data = get_candidate_skills_sql(db, department, time_period, start_date, end_date)
        return {"candidatesBySkill": skills_data}
        
    except HTTPException:
        # Re-raise HTTP exceptions without modification
        raise
    except Exception as e:
        logger.error(f"Error getting candidate skills: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/candidates/monthly-hires", response_model=MonthlyHires, tags=["Candidates"])
async def get_monthly_hires_endpoint(
    department: str = Query("ALL", description="Department filter"),
    time_period: TimePeriod = Query(TimePeriod.LAST_30_DAYS, description="Time period filter"),
    start_date: Optional[str] = Query(None, description="Start date for custom range (DD-MM-YYYY)", regex=r'^\d{4}-\d{2}-\d{2}$'),
    end_date: Optional[str] = Query(None, description="End date for custom range (DD-MM-YYYY)", regex=r'^\d{4}-\d{2}-\d{2}$'),
    db: Session = Depends(get_db)
):
    """
    Get monthly hire counts.
    
    Returns monthly hiring trends and statistics.
    """
    try:
        logger.info(f"Received monthly hires request - department: {department}, time_period: {time_period}")
        
        # Process date range
        if time_period == TimePeriod.CUSTOM:
            if not start_date or not end_date:
                raise HTTPException(
                    status_code=400, 
                    detail="Custom date range requires both start_date and end_date in YYYY-MM-DD format"
                )
            
            # Validate date format and order
            try:
                from datetime import datetime
                start_dt = datetime.strptime(start_date, '%d-%m-%Y')
                end_dt = datetime.strptime(end_date, '%d-%m-%Y')
                
                if start_dt > end_dt:
                    raise HTTPException(
                        status_code=400,
                        detail="start_date must be before or equal to end_date"
                    )
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid date format. Use DD-MM-YYYY format"
                )

        return get_monthly_hires(db=db, department=department, time_period=time_period, start_date=start_date, end_date=end_date)
        
    except HTTPException:
        # Re-raise HTTP exceptions without modification
        raise
    except Exception as e:
        logger.error(f"Error getting monthly hires: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/ta/metrics", response_model=TAMetricsAll, tags=["TA"])
async def get_ta_metrics_endpoint(
    department: str = Query("ALL", description="Department filter"),
    time_period: TimePeriod = Query(TimePeriod.LAST_30_DAYS, description="Time period filter"),
    start_date: Optional[str] = Query(None, description="Start date for custom range (DD-MM-YYYY)", regex=r'^\d{2}-\d{2}-\d{4}$'),
    end_date: Optional[str] = Query(None, description="End date for custom range (DD-MM-YYYY)", regex=r'^\d{2}-\d{2}-\d{4}$'),
    db: Session = Depends(get_db)
):
    """
    Get TA (Talent Acquisition) metrics for both TA1 and TA2 teams.
    
    Returns:
    - ta1: TA1 team metrics (jobs created, candidates sourced, etc.)
    - ta2: TA2 team metrics (jobs created, candidates sourced, etc.)
    """
    try:
        logger.info(f"Received TA metrics request - department: {department}, time_period: {time_period}")
        
        # Process date range
        if time_period == TimePeriod.CUSTOM:
            if not start_date or not end_date:
                raise HTTPException(
                    status_code=400, 
                    detail="Custom date range requires both start_date and end_date in YYYY-MM-DD format"
                )
            
            # Validate date format and order
            try:
                from datetime import datetime
                start_dt = datetime.strptime(start_date, '%d-%m-%Y')
                end_dt = datetime.strptime(end_date, '%d-%m-%Y')
                
                if start_dt > end_dt:
                    raise HTTPException(
                        status_code=400,
                        detail="start_date must be before or equal to end_date"
                    )
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid date format. Use DD-MM-YYYY format"
                )
            
        # Call the actual implementation function
        return get_ta_metrics(
            db=db, 
            department=department, 
            time_period=time_period, 
            start_date=start_date, 
            end_date=end_date
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions without modification
        raise
    except Exception as e:
        logger.error(f"Error getting TA metrics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    


# DEMAND-SUPPLY-GAP ANALYTICS
@router.get("/demand-supply-gap", tags=["Dashboard"])
async def get_demand_supply_gap(
    department: str = Query("ALL", description="Department filter"),
    time_period: TimePeriod = Query(TimePeriod.LAST_30_DAYS, description="Time period filter"),
    start_date: Optional[str] = Query(None, description="Start date for custom range"),
    end_date: Optional[str] = Query(None, description="End date for custom range"),
    db: Session = Depends(get_db)
):
    """
    Get demand-supply-gap analytics
    Returns:
    - demand: Number of jobs created
    - supply: Number of candidates onboarded  
    - inProcess: Candidates in interview stages
    - gap: demand - supply
    """
    department = normalize_department(department)
    start_date, end_date = get_dates_for_period(time_period, start_date, end_date)
    
    start_date_str = start_date.strftime('%d-%m-%Y')
    end_date_str = end_date.strftime('%d-%m-%Y')
    
    dept_filter = ""
    if department != "ALL":
        dept_filter = f"AND UPPER(j.department) = :department"
    
    query = text("""
    SELECT
        (SELECT COUNT(*) FROM job_requisitions
         WHERE created_on BETWEEN TO_DATE(:start_date, 'DD-MM-YYYY') AND TO_DATE(:end_date, 'DD-MM-YYYY')
         ) as demand,

        (SELECT COUNT(*) FROM candidates c
         JOIN job_requisitions j ON c.associated_job_id = j.job_id
         WHERE UPPER(c.current_status) = 'ONBOARDED'
         AND c.created_at BETWEEN TO_DATE(:start_date, 'DD-MM-YYYY') AND TO_DATE(:end_date, 'DD-MM-YYYY')
         ) as supply,

        (SELECT COUNT(*) FROM candidates c
         JOIN job_requisitions j ON c.associated_job_id = j.job_id
         WHERE UPPER(c.current_status) IN ('SCHEDULED', 'L1_ROUND', 'L2_ROUND', 'HR_ROUND')
         AND c.created_at BETWEEN TO_DATE(:start_date, 'DD-MM-YYYY') AND TO_DATE(:end_date, 'DD-MM-YYYY')
         ) as in_process
""")

    
    params = {"start_date": start_date_str, "end_date": end_date_str}
    if department != "ALL":
        params["department"] = department
    
    result = db.execute(query, params).fetchone()
    
    demand = result.demand or 0
    supply = result.supply or 0
    in_process = result.in_process or 0
    gap = demand - supply
    
    return {
        "demand": demand,
        "supply": supply, 
        "inProcess": in_process,
        "gap": gap
    }

# DEPARTMENT-WISE JOB DETAILS (Drill-down)
@router.get("/jobs/department-details", tags=["Jobs"])
async def get_department_wise_jobs(
    department: str = Query("ALL", description="Department filter"),
    time_period: TimePeriod = Query(TimePeriod.LAST_30_DAYS, description="Time period filter"),
    start_date: Optional[str] = Query(None, description="Start date for custom range, DD-MM-YYYY"),
    end_date: Optional[str] = Query(None, description="End date for custom range, DD-MM-YYYY"),
    db: Session = Depends(get_db)
):
    """
    Get detailed job information by department
    """
    department = normalize_department(department)

    # Convert input date strings (if any) to datetime objects, else get default range
    if start_date:
        start_date_obj = datetime.strptime(start_date, "%d-%m-%Y")
    else:
        start_date_obj, _ = get_dates_for_period(time_period, None, None)

    if end_date:
        end_date_obj = datetime.strptime(end_date, "%d-%m-%Y")
    else:
        _, end_date_obj = get_dates_for_period(time_period, None, None)

    # Prepare date strings for SQL query (ISO format)
    start_date_sql = start_date_obj.strftime("%Y-%m-%d")
    end_date_sql = end_date_obj.strftime("%Y-%m-%d")

    if department != "ALL":
        dept_filter = "WHERE UPPER(department) = :department AND created_on BETWEEN :start_date AND :end_date"
    else:
        dept_filter = "WHERE created_on BETWEEN :start_date AND :end_date"

    query = text(f"""
        SELECT 
            job_id,
            job_title,
            department,
            job_type,
            priority,
            status,
            no_of_positions,
            created_by,
            created_on,
            office_location
        FROM job_requisitions 
        {dept_filter}
        ORDER BY created_on DESC
    """)

    params = {"start_date": start_date_sql, "end_date": end_date_sql}
    if department != "ALL":
        params["department"] = department.upper()

    results = db.execute(query, params).fetchall()

    jobs = []
    for row in results:
        # Format created_on date to DD-MM-YYYY for output
        created_on_str = row.created_on.strftime("%d-%m-%Y") if row.created_on else None

        jobs.append({
            "jobId": row.job_id,
            "jobTitle": row.job_title,
            "department": row.department,
            "jobType": row.job_type,
            "priority": row.priority,
            "status": row.status,
            "no_of_positions": row.no_of_positions,
            "createdBy": row.created_by,
            "createdOn": created_on_str,
            "office_location": row.office_location
        })

    return {"jobs": jobs}


# ONBOARDED CANDIDATES DETAILS (Drill-down)
@router.get("/candidates/onboarded-details", tags=["Candidates"])
async def get_onboarded_candidates_details(
    department: str = Query("ALL", description="Department filter"),
    time_period: TimePeriod = Query(TimePeriod.LAST_30_DAYS, description="Time period filter"),
    start_date: Optional[str] = Query(None, description="Start date for custom range, DD-MM-YYYY"),
    end_date: Optional[str] = Query(None, description="End date for custom range, DD-MM-YYYY"),
    db: Session = Depends(get_db)
):
    """
    Get detailed list of onboarded candidates with DOJ, department, designation
    """
    department = normalize_department(department)

    # Convert input date strings to datetime or get defaults from your helper
    if start_date:
        start_date_obj = datetime.strptime(start_date, "%d-%m-%Y")
    else:
        start_date_obj, _ = get_dates_for_period(time_period, None, None)

    if end_date:
        end_date_obj = datetime.strptime(end_date, "%d-%m-%Y")
    else:
        _, end_date_obj = get_dates_for_period(time_period, None, None)

    # Convert to YYYY-MM-DD format for SQL query
    start_date_sql = start_date_obj.strftime("%Y-%m-%d")
    end_date_sql = end_date_obj.strftime("%Y-%m-%d")

    dept_filter = ""
    if department != "ALL":
        dept_filter = "AND UPPER(j.department) = :department"

    query = text(f"""
        SELECT 
            c.candidate_id,
            c.candidate_name,
            c.email_id,
            c.mobile_no,
            c.date_of_joining,
            j.department,
            c.current_designation,
            c.ta_team,
            c.created_at
        FROM candidates c
        JOIN job_requisitions j ON c.associated_job_id = j.job_id
        WHERE UPPER(c.current_status) = 'ONBOARDED'
        AND c.created_at BETWEEN :start_date AND :end_date
        {dept_filter}
        ORDER BY c.date_of_joining DESC
    """)

    params = {"start_date": start_date_sql, "end_date": end_date_sql}
    if department != "ALL":
        params["department"] = department.upper()

    results = db.execute(query, params).fetchall()

    candidates = []
    for row in results:
        # Format dates to DD-MM-YYYY for output
        doj_str = row.date_of_joining.strftime("%d-%m-%Y") if row.date_of_joining else None
        created_at_str = row.created_at.strftime("%d-%m-%Y") if row.created_at else None

        candidates.append({
            "candidateId": row.candidate_id,
            "candidateName": row.candidate_name,
            "email_id": row.email_id,
            "Mobile_no": row.mobile_no,
            "dateOfJoining": doj_str,
            "department": row.department,
            "designation": row.current_designation,
            "taTeam": row.ta_team,
            "appliedDate": created_at_str
        })

    return {"onboardedCandidates": candidates}


from datetime import datetime

def format_date(d):
    if d is None:
        return None
    if isinstance(d, str):
        # Try to parse string to date (if needed)
        try:
            dt = datetime.strptime(d, "%Y-%m-%d")  # Adjust if your DB returns date string in this format
            return dt.strftime("%d-%m-%Y")
        except Exception:
            return d  # If parsing fails, return as-is
    else:
        # If already date/datetime object
        return d.strftime("%d-%m-%Y")

#CANDIDATES IN INTERVIEW PROCESS DETAILS
@router.get("/candidates/interview-details", tags=["Candidates"])
async def get_interview_process_details(
    department: str = Query("ALL", description="Department filter"),
    time_period: TimePeriod = Query(TimePeriod.LAST_30_DAYS, description="Time period filter"),
    start_date: Optional[str] = Query(None, description="Start date for custom range"),
    end_date: Optional[str] = Query(None, description="End date for custom range"),
    db: Session = Depends(get_db)
):
    department = normalize_department(department)
    start_date, end_date = get_dates_for_period(time_period, start_date, end_date)
    
    start_date_str = start_date.strftime('%Y-%m-%d')  # Use DB-friendly format for querying
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    dept_filter = ""
    if department != "ALL":
        dept_filter = f"AND UPPER(j.department) = :department"
    
    query = text(f"""
        SELECT 
            c.candidate_id,
            c.candidate_name,
            c.email_id,
            c.mobile_no,
            c.current_status,
            j.department,
            j.job_title,
            c.ta_team,
            c.l1_interview_date,
            c.l2_interview_date,
            c.hr_interview_date,
            c.created_at
        FROM candidates c
        JOIN job_requisitions j ON c.associated_job_id = j.job_id
        WHERE UPPER(c.current_status) IN ('SCHEDULED', 'L1_ROUND', 'L2_ROUND', 'HR_ROUND')
        AND c.created_at BETWEEN :start_date AND :end_date
        {dept_filter}
        ORDER BY c.created_at DESC
    """)
    
    params = {"start_date": start_date_str, "end_date": end_date_str}
    if department != "ALL":
        params["department"] = department
    
    results = db.execute(query, params).fetchall()
    
    candidates = []
    for row in results:
        candidates.append({
            "candidateId": row.candidate_id,
            "candidateName": row.candidate_name,
            "email_id": row.email_id,
            "mobile_no": row.mobile_no,
            "currentStatus": row.current_status,
            "department": row.department,
            "jobTitle": row.job_title,
            "taTeam": row.ta_team,
            "l1InterviewDate": format_date(row.l1_interview_date),
            "l2InterviewDate": format_date(row.l2_interview_date),
            "hrInterviewDate": format_date(row.hr_interview_date),
            "appliedDate": format_date(row.created_at)
        })
    
    return {"interviewCandidates": candidates}

# ENHANCED JOB STATISTICS WITH POSITIONS
@router.get("/jobs/statistics-enhanced", tags=["Jobs"])
async def get_enhanced_job_statistics(
    department: str = Query("ALL", description="Department filter"),
    time_period: TimePeriod = Query(TimePeriod.LAST_30_DAYS, description="Time period filter"),
    start_date: Optional[str] = Query(None, description="Start date for custom range"),
    end_date: Optional[str] = Query(None, description="End date for custom range"),
    db: Session = Depends(get_db)
):
    """
    Get enhanced job statistics including position counts
    """
    department = normalize_department(department)
    start_date, end_date = get_dates_for_period(time_period, start_date, end_date)
    
    # Use ISO format for DB filtering:
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    dept_filter = ""
    if department != "ALL":
        dept_filter = f"AND UPPER(department) = :department"
    
    query = text(f"""
        SELECT 
            COUNT(*) as total_jobs,
            SUM(CASE WHEN UPPER(status) = 'OPEN' THEN 1 ELSE 0 END) as open_jobs,
            SUM(CASE WHEN UPPER(status) = 'CLOSED' THEN 1 ELSE 0 END) as closed_jobs,
            SUM(COALESCE(no_of_positions, 1)) as total_positions,
            SUM(CASE WHEN UPPER(status) = 'OPEN' THEN COALESCE(no_of_positions, 1) ELSE 0 END) as open_positions,
            SUM(CASE WHEN UPPER(status) = 'CLOSED' THEN COALESCE(no_of_positions, 1) ELSE 0 END) as closed_positions,
            SUM(CASE WHEN UPPER(created_by) = 'TA1' THEN 1 ELSE 0 END) as ta1_created_jobs,
            SUM(CASE WHEN UPPER(created_by) = 'TA2' THEN 1 ELSE 0 END) as ta2_created_jobs
        FROM job_requisitions
        WHERE created_on BETWEEN :start_date AND :end_date
        {dept_filter}
    """)
    
    params = {"start_date": start_date_str, "end_date": end_date_str}
    if department != "ALL":
        params["department"] = department
    
    result = db.execute(query, params).fetchone()
    
    return {
        "totalJobs": result.total_jobs or 0,
        "openJobs": result.open_jobs or 0,
        "closedJobs": result.closed_jobs or 0,
        "totalPositions": result.total_positions or 0,
        "openPositions": result.open_positions or 0,
        "closedPositions": result.closed_positions or 0,
        "ta1CreatedJobs": result.ta1_created_jobs or 0,
        "ta2CreatedJobs": result.ta2_created_jobs or 0
    }

# TA CANDIDATE PROCESSING DETAILS
@router.get("/ta/candidate-processing", tags=["TA"])
async def get_ta_candidate_processing(
    department: str = Query("ALL", description="Department filter"),
    time_period: TimePeriod = Query(TimePeriod.LAST_30_DAYS, description="Time period filter"),
    start_date: Optional[str] = Query(None, description="Start date for custom range"),
    end_date: Optional[str] = Query(None, description="End date for custom range"),
    db: Session = Depends(get_db)
):
    """
    Get detailed TA performance - candidates processed by each TA with status breakdown
    """
    department = normalize_department(department)
    start_date, end_date = get_dates_for_period(time_period, start_date, end_date)
    
    # Use ISO format for DB filtering:
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    dept_filter = ""
    if department != "ALL":
        dept_filter = f"AND UPPER(j.department) = :department"
    
    query = text(f"""
        SELECT 
            c.ta_team,
            c.current_status,
            COUNT(*) as candidate_count,
            COUNT(DISTINCT c.candidate_id) as unique_candidates
        FROM candidates c
        JOIN job_requisitions j ON c.associated_job_id = j.job_id
        WHERE c.created_at BETWEEN :start_date AND :end_date
        {dept_filter}
        GROUP BY c.ta_team, c.current_status
        ORDER BY c.ta_team, c.current_status
    """)
    
    params = {"start_date": start_date_str, "end_date": end_date_str}
    if department != "ALL":
        params["department"] = department
    
    results = db.execute(query, params).fetchall()
    
    # Organize by TA team
    ta_processing = {"TA1": {}, "TA2": {}}
    
    for row in results:
        ta_team = row.ta_team or "Unknown"
        if ta_team not in ta_processing:
            ta_processing[ta_team] = {}
        
        ta_processing[ta_team][row.current_status] = {
            "count": row.candidate_count,
            "uniqueCandidates": row.unique_candidates
        }
    
    return {"taProcessing": ta_processing}