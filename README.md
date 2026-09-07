# Attenomy HR API

A RESTful API service for Employee, Leave & Attendance management — built for the **Attenomy Software Engineering Internship Stage 3 Micro-Task**.

**Track:** Option B — Backend / API  
**Stack:** Python · FastAPI · SQLAlchemy · SQLite  

---

## Architecture Overview

```
attenomy-api/
├── main.py          # FastAPI app — all route handlers & business logic
├── database.py      # SQLAlchemy models, engine, session setup
├── schemas.py       # Pydantic request/response schemas & validators
├── requirements.txt
└── README.md
```

**Design decisions:**
- **FastAPI** — async-ready, auto-generates OpenAPI docs, Pydantic-native validation
- **SQLAlchemy ORM** — clean model definitions, easy to swap SQLite → PostgreSQL
- **SQLite** — zero-config persistence, perfect for this scope
- Business logic (quota checks, overlap detection) lives in route handlers, keeping models clean

---

## Setup & Run

### Prerequisites
- Python 3.10+

### 1. Clone & install
```bash
git clone https://github.com/your-username/attenomy-microtask
cd attenomy-microtask
pip install -r requirements.txt
```

### 2. Start the server
```bash
uvicorn main:app --reload
```

Server runs at: `http://localhost:8000`  
Interactive API docs: `http://localhost:8000/docs`

---

## API Endpoints

### Base URL
```
http://localhost:8000
```

---

### 1. `POST /api/employees` — Create Employee

**Request:**
```json
{
  "name": "Ravi Sharma",
  "email": "ravi@company.com",
  "department": "Engineering",
  "designation": "Backend Engineer",
  "join_date": "2025-01-15",
  "status": "Active"
}
```

**Response `201`:**
```json
{
  "id": 1,
  "name": "Ravi Sharma",
  "email": "ravi@company.com",
  "department": "Engineering",
  "designation": "Backend Engineer",
  "status": "Active",
  "join_date": "2025-01-15"
}
```

**Validations:**
- All fields required (name, email, department, designation, join_date)
- Email must be unique and valid format → `409` if duplicate
- Join date cannot be in the future → `422`

**cURL:**
```bash
curl -X POST http://localhost:8000/api/employees \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Ravi Sharma",
    "email": "ravi@company.com",
    "department": "Engineering",
    "designation": "Backend Engineer",
    "join_date": "2025-01-15"
  }'
```

---

### 2. `POST /api/leaves/apply` — Apply for Leave

**Request:**
```json
{
  "employee_id": 1,
  "start_date": "2026-10-01",
  "end_date": "2026-10-05",
  "reason": "Festival vacation"
}
```

**Response `201`:**
```json
{
  "id": 1,
  "employee_id": 1,
  "start_date": "2026-10-01",
  "end_date": "2026-10-05",
  "reason": "Festival vacation",
  "status": "Pending",
  "days_requested": 5
}
```

**Validations:**
- Employee must exist → `404`
- `start_date` cannot be in the past → `422`
- `end_date` must be ≥ `start_date` → `422`
- No date overlap with existing Pending/Approved leaves → `409`
- Max **15 annual leave days** quota (approved + pending combined) → `422`

**cURL:**
```bash
curl -X POST http://localhost:8000/api/leaves/apply \
  -H "Content-Type: application/json" \
  -d '{
    "employee_id": 1,
    "start_date": "2026-10-01",
    "end_date": "2026-10-05",
    "reason": "Festival vacation"
  }'
```

**Error example (quota exceeded):**
```json
{
  "detail": "Quota exceeded. Annual quota: 15 days. Already consumed: 10 days. Remaining: 5 days. Requested: 8 days."
}
```

---

### 3. `GET /api/leaves/balance/{id}` — Leave Balance

**URL params:** `id` = employee ID  
**Query params:** `year` (optional, defaults to current year)

**Response `200`:**
```json
{
  "employee_id": 1,
  "employee_name": "Ravi Sharma",
  "annual_quota": 15,
  "used": 5,
  "pending": 3,
  "remaining": 7
}
```

**cURL:**
```bash
# Current year
curl http://localhost:8000/api/leaves/balance/1

# Specific year
curl http://localhost:8000/api/leaves/balance/1?year=2026
```

---

### 4. `GET /api/attendance/summary` — Monthly Dept-wise Summary

**Query params:**
| Param        | Type    | Default        | Description          |
|--------------|---------|----------------|----------------------|
| `month`      | integer | current month  | 1–12                 |
| `year`       | integer | current year   | 4-digit year         |
| `department` | string  | all depts      | Filter by department |

**Response `200`:**
```json
[
  {
    "department": "Engineering",
    "month": 9,
    "year": 2026,
    "total_employees": 5,
    "total_present_days": 95,
    "total_leave_days": 3,
    "average_attendance_rate": 63.33
  },
  {
    "department": "HR",
    "month": 9,
    "year": 2026,
    "total_employees": 2,
    "total_present_days": 40,
    "total_leave_days": 1,
    "average_attendance_rate": 66.67
  }
]
```

**cURL:**
```bash
# All departments, current month
curl http://localhost:8000/api/attendance/summary

# Specific month/year
curl "http://localhost:8000/api/attendance/summary?month=9&year=2026"

# Filter by department
curl "http://localhost:8000/api/attendance/summary?month=9&year=2026&department=Engineering"
```

---

## Health Check

```bash
curl http://localhost:8000/health
# {"status":"ok","service":"Attenomy HR API","version":"1.0.0"}
```

---

## Postman Collection

Import this JSON into Postman:

```json
{
  "info": { "name": "Attenomy HR API", "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json" },
  "item": [
    {
      "name": "Create Employee",
      "request": {
        "method": "POST", "url": "http://localhost:8000/api/employees",
        "header": [{"key": "Content-Type", "value": "application/json"}],
        "body": { "mode": "raw", "raw": "{\"name\":\"Ravi Sharma\",\"email\":\"ravi@company.com\",\"department\":\"Engineering\",\"designation\":\"Backend Engineer\",\"join_date\":\"2025-01-15\"}" }
      }
    },
    {
      "name": "Apply Leave",
      "request": {
        "method": "POST", "url": "http://localhost:8000/api/leaves/apply",
        "header": [{"key": "Content-Type", "value": "application/json"}],
        "body": { "mode": "raw", "raw": "{\"employee_id\":1,\"start_date\":\"2026-10-01\",\"end_date\":\"2026-10-05\",\"reason\":\"Festival vacation\"}" }
      }
    },
    {
      "name": "Leave Balance",
      "request": { "method": "GET", "url": "http://localhost:8000/api/leaves/balance/1" }
    },
    {
      "name": "Attendance Summary",
      "request": { "method": "GET", "url": "http://localhost:8000/api/attendance/summary?month=9&year=2026" }
    }
  ]
}
```

---

## Error Reference

| Code | Scenario |
|------|----------|
| `201` | Resource created successfully |
| `200` | Successful GET |
| `404` | Employee not found |
| `409` | Duplicate email / Leave date overlap |
| `422` | Validation error (quota exceeded, invalid dates, missing fields) |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI 0.115 |
| ORM | SQLAlchemy 2.0 |
| Database | SQLite (file: `attenomy.db`) |
| Validation | Pydantic v2 |
| Server | Uvicorn |
| Python | 3.10+ |
