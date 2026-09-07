from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import extract, func
from datetime import date
from typing import List, Optional
import calendar

from app_database import get_db, init_db, Employee, Leave, Attendance, LeaveStatus, EmployeeStatus
from app_schemas import (
    EmployeeCreate, EmployeeResponse,
    LeaveApply, LeaveResponse, LeaveBalance,
    AttendanceSummaryItem,
)

app = FastAPI(
    title="Attenomy HR API",
    description="RESTful API for Employee, Leave & Attendance management — Attenomy Stage 3 Micro-Task",
    version="1.0.0",
)

ANNUAL_LEAVE_QUOTA = 15  # days per year


@app.on_event("startup")
def on_startup():
    init_db()


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/employees  — Create & validate a new employee record
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/api/employees", response_model=EmployeeResponse, status_code=201)
def create_employee(payload: EmployeeCreate, db: Session = Depends(get_db)):
    """
    Create a new employee record.

    Validations:
    - All required fields must be non-empty
    - Email must be unique & valid format
    - Join date cannot be in the future
    """
    # Duplicate email check
    existing = db.query(Employee).filter(Employee.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Email '{payload.email}' is already registered.")

    employee = Employee(
        name=payload.name,
        email=payload.email,
        department=payload.department,
        designation=payload.designation,
        join_date=payload.join_date,
        status=payload.status,
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/leaves/apply  — Apply for leave with overlap + quota check
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/api/leaves/apply", response_model=LeaveResponse, status_code=201)
def apply_leave(payload: LeaveApply, db: Session = Depends(get_db)):
    """
    Apply for leave.

    Validations:
    - Employee must exist
    - start_date cannot be in the past
    - end_date must be >= start_date
    - No overlapping approved/pending leaves
    - Max 15 annual leave days quota check (approved + pending + this request)
    """
    # Employee existence
    employee = db.query(Employee).filter(Employee.id == payload.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail=f"Employee with id {payload.employee_id} not found.")

    days_requested = (payload.end_date - payload.start_date).days + 1

    # Overlap check — any approved or pending leave that overlaps the requested range
    overlap = (
        db.query(Leave)
        .filter(
            Leave.employee_id == payload.employee_id,
            Leave.status.in_([LeaveStatus.approved, LeaveStatus.pending]),
            Leave.start_date <= payload.end_date,
            Leave.end_date >= payload.start_date,
        )
        .first()
    )
    if overlap:
        raise HTTPException(
            status_code=409,
            detail=f"Leave dates overlap with an existing {overlap.status} leave "
                   f"({overlap.start_date} to {overlap.end_date}).",
        )

    # Annual quota check — count days used/pending in the same calendar year
    year = payload.start_date.year
    existing_leaves = (
        db.query(Leave)
        .filter(
            Leave.employee_id == payload.employee_id,
            Leave.status.in_([LeaveStatus.approved, LeaveStatus.pending]),
            extract("year", Leave.start_date) == year,
        )
        .all()
    )
    days_consumed = sum((l.end_date - l.start_date).days + 1 for l in existing_leaves)

    if days_consumed + days_requested > ANNUAL_LEAVE_QUOTA:
        remaining = max(0, ANNUAL_LEAVE_QUOTA - days_consumed)
        raise HTTPException(
            status_code=422,
            detail=(
                f"Quota exceeded. Annual quota: {ANNUAL_LEAVE_QUOTA} days. "
                f"Already consumed: {days_consumed} days. "
                f"Remaining: {remaining} days. Requested: {days_requested} days."
            ),
        )

    leave = Leave(
        employee_id=payload.employee_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        reason=payload.reason,
        status=LeaveStatus.pending,
    )
    db.add(leave)
    db.commit()
    db.refresh(leave)

    return {
        "id": leave.id,
        "employee_id": leave.employee_id,
        "start_date": leave.start_date,
        "end_date": leave.end_date,
        "reason": leave.reason,
        "status": leave.status,
        "days_requested": days_requested,
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/leaves/balance/{id}  — Query leave balance for an employee
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/api/leaves/balance/{employee_id}", response_model=LeaveBalance)
def get_leave_balance(employee_id: int, year: Optional[int] = None, db: Session = Depends(get_db)):
    """
    Get leave balance for an employee.

    Returns: total quota, used (approved), pending, and remaining days.
    Optionally filter by year (defaults to current year).
    """
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail=f"Employee with id {employee_id} not found.")

    target_year = year or date.today().year

    approved_leaves = (
        db.query(Leave)
        .filter(
            Leave.employee_id == employee_id,
            Leave.status == LeaveStatus.approved,
            extract("year", Leave.start_date) == target_year,
        )
        .all()
    )
    pending_leaves = (
        db.query(Leave)
        .filter(
            Leave.employee_id == employee_id,
            Leave.status == LeaveStatus.pending,
            extract("year", Leave.start_date) == target_year,
        )
        .all()
    )

    used = sum((l.end_date - l.start_date).days + 1 for l in approved_leaves)
    pending = sum((l.end_date - l.start_date).days + 1 for l in pending_leaves)
    remaining = max(0, ANNUAL_LEAVE_QUOTA - used - pending)

    return {
        "employee_id": employee_id,
        "employee_name": employee.name,
        "annual_quota": ANNUAL_LEAVE_QUOTA,
        "used": used,
        "pending": pending,
        "remaining": remaining,
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/attendance/summary  — Monthly dept-wise attendance & leave roll-up
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/api/attendance/summary", response_model=List[AttendanceSummaryItem])
def attendance_summary(
    month: int = Query(default=None, ge=1, le=12, description="Month (1-12)"),
    year: int = Query(default=None, description="4-digit year"),
    department: Optional[str] = Query(default=None, description="Filter by department name"),
    db: Session = Depends(get_db),
):
    """
    Monthly department-wise attendance & leave roll-up.

    Returns per-department stats: total employees, present days, leave days,
    and average attendance rate for the given month/year.
    Defaults to current month/year if not provided.
    """
    today = date.today()
    target_month = month or today.month
    target_year = year or today.year

    # Working days in the month
    _, days_in_month = calendar.monthrange(target_year, target_month)

    # Fetch all employees (optionally filter by department)
    emp_query = db.query(Employee)
    if department:
        emp_query = emp_query.filter(Employee.department == department)
    employees = emp_query.all()

    if not employees:
        return []

    # Build department map
    dept_map: dict = {}
    for emp in employees:
        dept = emp.department
        if dept not in dept_map:
            dept_map[dept] = {"employee_ids": [], "emp_count": 0}
        dept_map[dept]["employee_ids"].append(emp.id)
        dept_map[dept]["emp_count"] += 1

    result = []
    for dept, info in dept_map.items():
        emp_ids = info["employee_ids"]
        emp_count = info["emp_count"]

        # Attendance present days
        present_days = (
            db.query(func.count(Attendance.id))
            .filter(
                Attendance.employee_id.in_(emp_ids),
                Attendance.present == True,
                extract("month", Attendance.date) == target_month,
                extract("year", Attendance.date) == target_year,
            )
            .scalar()
            or 0
        )

        # Leave days (approved leaves intersecting this month)
        month_start = date(target_year, target_month, 1)
        month_end = date(target_year, target_month, days_in_month)

        dept_leaves = (
            db.query(Leave)
            .filter(
                Leave.employee_id.in_(emp_ids),
                Leave.status == LeaveStatus.approved,
                Leave.start_date <= month_end,
                Leave.end_date >= month_start,
            )
            .all()
        )

        leave_days = 0
        for lv in dept_leaves:
            # Clamp leave range to this month's bounds
            effective_start = max(lv.start_date, month_start)
            effective_end = min(lv.end_date, month_end)
            leave_days += (effective_end - effective_start).days + 1

        # Avg attendance rate = present / (employees × working days)
        total_possible = emp_count * days_in_month
        avg_rate = round((present_days / total_possible) * 100, 2) if total_possible > 0 else 0.0

        result.append(
            AttendanceSummaryItem(
                department=dept,
                month=target_month,
                year=target_year,
                total_employees=emp_count,
                total_present_days=present_days,
                total_leave_days=leave_days,
                average_attendance_rate=avg_rate,
            )
        )

    return result
