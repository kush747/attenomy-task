from pydantic import BaseModel, EmailStr, field_validator, model_validator
from datetime import date
from typing import Optional
from app_database import EmployeeStatus, LeaveStatus


# ── Employee Schemas ──────────────────────────────────────────────────────────

class EmployeeCreate(BaseModel):
    name: str
    email: str
    department: str
    designation: str
    join_date: date
    status: Optional[EmployeeStatus] = EmployeeStatus.active

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()

    @field_validator("email")
    @classmethod
    def email_valid(cls, v):
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email format")
        return v.lower().strip()

    @field_validator("department", "designation")
    @classmethod
    def not_empty(cls, v):
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()

    @field_validator("join_date")
    @classmethod
    def join_date_not_future(cls, v):
        if v > date.today():
            raise ValueError("Join date cannot be in the future")
        return v


class EmployeeResponse(BaseModel):
    id: int
    name: str
    email: str
    department: str
    designation: str
    status: str
    join_date: date

    class Config:
        from_attributes = True


# ── Leave Schemas ─────────────────────────────────────────────────────────────

class LeaveApply(BaseModel):
    employee_id: int
    start_date: date
    end_date: date
    reason: Optional[str] = None

    @model_validator(mode="after")
    def end_after_start(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self

    @field_validator("start_date")
    @classmethod
    def start_not_past(cls, v):
        if v < date.today():
            raise ValueError("start_date cannot be in the past")
        return v


class LeaveResponse(BaseModel):
    id: int
    employee_id: int
    start_date: date
    end_date: date
    reason: Optional[str]
    status: str
    days_requested: int

    class Config:
        from_attributes = True


class LeaveBalance(BaseModel):
    employee_id: int
    employee_name: str
    annual_quota: int
    used: int
    pending: int
    remaining: int


# ── Attendance Schemas ────────────────────────────────────────────────────────

class AttendanceSummaryItem(BaseModel):
    department: str
    month: int
    year: int
    total_employees: int
    total_present_days: int
    total_leave_days: int
    average_attendance_rate: float
