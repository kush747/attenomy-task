from sqlalchemy import create_engine, Column, Integer, String, Date, Boolean, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import enum

DATABASE_URL = "sqlite:///./attenomy.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class EmployeeStatus(str, enum.Enum):
    active = "Active"
    on_leave = "On Leave"


class LeaveStatus(str, enum.Enum):
    pending = "Pending"
    approved = "Approved"
    rejected = "Rejected"


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    department = Column(String, nullable=False)
    designation = Column(String, nullable=False)
    status = Column(String, default=EmployeeStatus.active)
    join_date = Column(Date, nullable=False)

    leaves = relationship("Leave", back_populates="employee")
    attendance = relationship("Attendance", back_populates="employee")


class Leave(Base):
    __tablename__ = "leaves"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    reason = Column(String)
    status = Column(String, default=LeaveStatus.pending)

    employee = relationship("Employee", back_populates="leaves")


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    date = Column(Date, nullable=False)
    present = Column(Boolean, default=True)

    employee = relationship("Employee", back_populates="attendance")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
