import hashlib
import io
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import anthropic
import openpyxl
import pandas as pd
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, field_validator
from supabase import Client, create_client

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
SUPABASE_URL     = os.environ["SUPABASE_URL"]
SUPABASE_KEY     = os.environ["SUPABASE_KEY"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
JWT_SECRET       = os.environ["JWT_SECRET"]
JWT_ALGORITHM    = "HS256"
JWT_EXPIRE_HOURS = 24

# ── Clients ───────────────────────────────────────────────────────────────────
_supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
_ai = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ── Job paths (mirrors core/job_paths.py — no st dependency here) ─────────────
JOB_PATHS = {
    "junior_data_analyst": {
        "id": "junior_data_analyst",
        "title": "Junior Data Analyst",
        "company": "NovaRetail Inc.",
        "industry": "Retail & E-commerce",
        "manager": "Sophie Chen",
        "manager_title": "Senior Data Analyst",
        "stack": ["SQL", "Python", "Excel", "Power BI"],
        "duration_weeks": 24,
        "responsibilities": [
            "Clean and transform sales and inventory datasets",
            "Create weekly reports for the operations team",
            "Analyze customer behavior trends",
            "Maintain and update Power BI dashboards",
            "Handle ad-hoc data requests from the business team",
        ],
        "schema": """
NovaRetail Inc. — Database Schema (use these exact table and column names in all SQL tasks):

Table: sales
  - order_id (INTEGER) — unique order identifier
  - product_name (TEXT) — name of the product sold
  - category (TEXT) — product category (e.g. Electronics, Apparel, Home, Food)
  - units_sold (INTEGER) — number of units in the order
  - unit_price (DECIMAL) — price per unit
  - total_revenue (DECIMAL) — units_sold * unit_price
  - sale_date (DATE) — date of the transaction (format: YYYY-MM-DD)
  - region (TEXT) — sales region (North, South, East, West, International)
  - store_id (INTEGER) — store where the sale occurred

Table: inventory
  - product_id (INTEGER) — unique product identifier
  - product_name (TEXT) — name of the product
  - category (TEXT) — product category
  - stock_level (INTEGER) — current units in stock
  - reorder_point (INTEGER) — minimum stock before reorder is triggered
  - last_restocked (DATE) — date of last restock

Table: customers
  - customer_id (INTEGER) — unique customer identifier
  - full_name (TEXT) — customer full name
  - email (TEXT) — customer email
  - region (TEXT) — customer region
  - signup_date (DATE) — date they joined NovaRetail
  - total_orders (INTEGER) — lifetime number of orders
  - total_spent (DECIMAL) — lifetime spend
""",
    }
}

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="Simployee API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Auth helpers ──────────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    """SHA-256 — matches app.py and core/database.py."""
    return hashlib.sha256(password.encode()).hexdigest()

def create_token(user_id: int, username: str) -> str:
    payload = {
        "sub": str(user_id),
        "username": username,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

_bearer = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    payload = decode_token(credentials.credentials)
    result = (
        _supabase.table("users")
        .select("id, username, full_name, created_at")
        .eq("id", int(payload["sub"]))
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    return result.data[0]

# ── Progress helpers ──────────────────────────────────────────────────────────
def get_or_create_progress(user_id: int) -> dict:
    """Return user_progress row, creating one with the default job path if absent."""
    result = _supabase.table("user_progress").select("*").eq("user_id", user_id).execute()
    if result.data:
        return result.data[0]
    insert = _supabase.table("user_progress").insert({
        "user_id":     user_id,
        "job_path_id": "junior_data_analyst",
    }).execute()
    return insert.data[0]

# ── Task helpers ──────────────────────────────────────────────────────────────
def get_task_owned_by(task_id: int, user_id: int) -> dict:
    result = (
        _supabase.table("tasks")
        .select("*")
        .eq("id", task_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    return result.data[0]

# ── File reading (mirrors 1_Tasks.py logic) ───────────────────────────────────
async def read_uploaded_file(file: UploadFile) -> str:
    content = await file.read()
    name = (file.filename or "").lower()
    try:
        if name.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
            return df.to_string(max_rows=100)
        elif name.endswith((".xlsx", ".xls")):
            wb = openpyxl.load_workbook(io.BytesIO(content))
            parts = []
            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                rows = [
                    "\t".join(str(c) if c is not None else "" for c in row)
                    for row in ws.iter_rows(max_row=50, values_only=True)
                ]
                parts.append(f"Sheet: {sheet_name}\n" + "\n".join(rows))
            return "\n\n".join(parts)
        else:
            return content.decode("utf-8", errors="ignore")
    except Exception as e:
        return f"Could not read file: {e}"

# ── AI: generate tasks (mirrors core/ai_engine.py) ────────────────────────────
def _generate_weekly_tasks(job_path: dict, week_number: int) -> list[dict]:
    prompt = f"""You are a simulation engine for a job training platform called Simployee.

The user has been hired as a {job_path['title']} at {job_path['company']},
a company in the {job_path['industry']} industry.

Their manager is {job_path['manager']} ({job_path['manager_title']}).

Key responsibilities:
{chr(10).join(f"- {r}" for r in job_path['responsibilities'])}

Required stack: {', '.join(job_path['stack'])}

Company database schema (always reference exact table/column names in SQL tasks):
{job_path.get('schema', 'No schema provided.')}

Generate 3 realistic work tasks for Week {week_number} of their simulated job.
Each task should feel like a real ticket a junior analyst would receive at work.

Rules:
- Tasks must be practical and doable (the user will actually attempt them)
- Increase complexity gradually based on the week number
- Tasks must relate to the company context (retail, sales, inventory, customers)
- When tasks involve SQL, always mention the exact table and column names from the schema above
- Week 1-4: Basic tasks (data cleaning, simple queries, basic reports)
- Week 5-12: Intermediate tasks (analysis, visualization, Python scripts)
- Week 13-24: Advanced tasks (dashboards, automation, insights presentations)

Respond ONLY with a valid JSON array. No explanation, no markdown, no extra text.
Format:
[
  {{
    "title": "Short task title",
    "description": "2-3 sentences describing the task with business context, as if written by the manager in Slack. If the task involves SQL, mention the exact table and columns to use.",
    "deliverable": "Exactly what the user must submit (e.g. SQL query, Python script, Excel file, written analysis)"
  }},
  {{"title": "...", "description": "...", "deliverable": "..."}},
  {{"title": "...", "description": "...", "deliverable": "..."}}
]"""

    message = _ai.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    return json.loads(raw)

# ── AI: evaluate submission (mirrors core/ai_engine.py) ───────────────────────
def _evaluate_submission(
    task: dict,
    submission_text: str,
    job_path: dict,
    file_content: Optional[str] = None,
    file_name: Optional[str] = None,
) -> str:
    if file_content and submission_text.strip():
        submission_context = f"""The analyst submitted both a file and a written comment.

File uploaded: {file_name}
File content (first 3000 chars):
{file_content[:3000]}

Written comment:
{submission_text}"""
    elif file_content:
        submission_context = f"""The analyst submitted a file only.

File uploaded: {file_name}
File content (first 3000 chars):
{file_content[:3000]}"""
    elif submission_text.strip():
        submission_context = f"""The analyst submitted a written response only (no file attached).

Written response:
{submission_text}"""
    else:
        submission_context = "The analyst submitted nothing meaningful."

    prompt = f"""You are Sophie Chen, a {job_path['manager_title']} at {job_path['company']}.
You are reviewing work submitted by your junior analyst.

Task assigned:
Title: {task['title']}
Description: {task['description']}
Expected deliverable: {task['deliverable']}

What was submitted:
{submission_context}

Instructions for your response:
- Write exactly like a real manager messaging their junior on Slack — direct, human, no corporate speak
- NEVER start with "Great job!" or "Excellent work!" or any generic praise opener
- If the deliverable was supposed to be a file (Excel, CSV, script) and they only sent text, call it out directly and ask for the actual file. Example tone: "Hey, I appreciate the explanation but I actually need the file itself here, not just a description of what you did."
- If they submitted a file but it's missing something, point it out specifically
- If the work is genuinely good, acknowledge it but still give one concrete improvement tip
- If the work has real errors or problems, be honest about it — don't sugarcoat
- Keep it 150-250 words
- Sound like a real person, not an AI. No bullet point lists in your response.
- End with either a follow-up question or a next step, like a real manager would"""

    message = _ai.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()

# ── Request schemas ───────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    full_name: str
    username:  str
    password:  str

    @field_validator("full_name", "username")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be blank.")
        return v.strip()

    @field_validator("password")
    @classmethod
    def min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters.")
        return v

class LoginRequest(BaseModel):
    username: str
    password: str

class SelectJobPathRequest(BaseModel):
    job_path_id: str

# ── Shared response shape ─────────────────────────────────────────────────────
def _user_payload(user: dict) -> dict:
    return {"id": user["id"], "username": user["username"], "full_name": user["full_name"]}

# ═══════════════════════════════════════════════════════════════════════════════
# Auth routes
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/auth/register", status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest):
    try:
        result = _supabase.table("users").insert({
            "username":  body.username,
            "password":  hash_password(body.password),
            "full_name": body.full_name,
        }).execute()
    except Exception:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken.")

    user  = result.data[0]
    token = create_token(user["id"], user["username"])
    return {"token": token, "user": _user_payload(user)}


@app.post("/auth/login")
def login(body: LoginRequest):
    result = _supabase.table("users").select("*").eq("username", body.username).execute()

    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid username or password.",
    )
    if not result.data:
        raise invalid

    user = result.data[0]
    if user["password"] != hash_password(body.password):
        raise invalid

    token = create_token(user["id"], user["username"])
    return {"token": token, "user": _user_payload(user)}


@app.get("/auth/me")
def me(current_user: dict = Depends(get_current_user)):
    return current_user

# ═══════════════════════════════════════════════════════════════════════════════
# User progress routes
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/users/me/progress")
def get_progress(current_user: dict = Depends(get_current_user)):
    result = _supabase.table("user_progress").select("*").eq("user_id", current_user["id"]).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="No job path selected.")
    progress = result.data[0]
    job_path = JOB_PATHS.get(progress["job_path_id"], {})
    return {
        "current_week":  progress["current_week"],
        "job_path_id":   progress["job_path_id"],
        "started_at":    progress.get("started_at"),
        "job_path": {
            "title":          job_path.get("title"),
            "company":        job_path.get("company"),
            "duration_weeks": job_path.get("duration_weeks"),
        },
    }


@app.post("/users/me/progress", status_code=status.HTTP_201_CREATED)
def select_job_path(
    body: SelectJobPathRequest,
    current_user: dict = Depends(get_current_user),
):
    if body.job_path_id not in JOB_PATHS:
        raise HTTPException(status_code=400, detail="Invalid job path ID.")

    existing = (
        _supabase.table("user_progress")
        .select("id")
        .eq("user_id", current_user["id"])
        .execute()
    )
    if existing.data:
        raise HTTPException(status_code=409, detail="Job path already selected.")

    result = _supabase.table("user_progress").insert({
        "user_id":     current_user["id"],
        "job_path_id": body.job_path_id,
    }).execute()
    return result.data[0]


@app.post("/users/me/advance")
def advance_week(current_user: dict = Depends(get_current_user)):
    progress = get_or_create_progress(current_user["id"])
    week     = progress["current_week"]
    job_path = JOB_PATHS.get(progress["job_path_id"], {})

    # Verify all tasks for this week are reviewed
    tasks_result = (
        _supabase.table("tasks")
        .select("status")
        .eq("user_id", current_user["id"])
        .eq("week", week)
        .execute()
    )
    tasks = tasks_result.data or []

    if not tasks:
        raise HTTPException(status_code=400, detail="Generate and complete tasks before advancing.")
    if any(t["status"] != "reviewed" for t in tasks):
        raise HTTPException(status_code=400, detail="Complete all tasks before advancing to the next week.")

    max_weeks = job_path.get("duration_weeks", 24)
    if week >= max_weeks:
        raise HTTPException(status_code=400, detail="You have completed the full program!")

    result = (
        _supabase.table("user_progress")
        .update({"current_week": week + 1})
        .eq("user_id", current_user["id"])
        .execute()
    )
    return {"current_week": result.data[0]["current_week"]}

# ═══════════════════════════════════════════════════════════════════════════════
# Task routes
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/tasks")
def list_tasks(week: int, current_user: dict = Depends(get_current_user)):
    result = (
        _supabase.table("tasks")
        .select("*")
        .eq("user_id", current_user["id"])
        .eq("week", week)
        .order("id")
        .execute()
    )
    return result.data or []


@app.post("/tasks/generate", status_code=status.HTTP_201_CREATED)
def generate_tasks(current_user: dict = Depends(get_current_user)):
    progress = get_or_create_progress(current_user["id"])
    week     = progress["current_week"]
    job_path = JOB_PATHS.get(progress["job_path_id"])

    if not job_path:
        raise HTTPException(status_code=400, detail="Invalid job path.")

    # Prevent re-generation if tasks already exist for this week
    existing = (
        _supabase.table("tasks")
        .select("id")
        .eq("user_id", current_user["id"])
        .eq("week", week)
        .execute()
    )
    if existing.data:
        raise HTTPException(status_code=409, detail="Tasks for this week already exist.")

    try:
        generated = _generate_weekly_tasks(job_path, week)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI generation failed: {e}")

    rows = [
        {
            "user_id":     current_user["id"],
            "week":        week,
            "title":       t["title"],
            "description": t["description"],
            "deliverable": t["deliverable"],
        }
        for t in generated
    ]
    result = _supabase.table("tasks").insert(rows).execute()
    return result.data


@app.post("/tasks/{task_id}/submit")
async def submit_task(
    task_id:         int,
    submission_text: str              = Form(""),
    file:            Optional[UploadFile] = File(None),
    current_user:    dict             = Depends(get_current_user),
):
    task = get_task_owned_by(task_id, current_user["id"])

    if task["status"] == "reviewed":
        raise HTTPException(status_code=400, detail="Task already reviewed. Use resubmit instead.")

    if not submission_text.strip() and not file:
        raise HTTPException(status_code=400, detail="Submit something — text, code, or a file.")

    # Read file content
    file_content: Optional[str] = None
    file_name:    Optional[str] = None
    if file and file.filename:
        file_content = await read_uploaded_file(file)
        file_name    = file.filename

    # Build the submission record stored in DB
    if file_name and submission_text.strip():
        submission_record = f"[File: {file_name}]\n\n{submission_text}"
    elif file_name:
        submission_record = f"[File submitted: {file_name}]"
    else:
        submission_record = submission_text

    progress = get_or_create_progress(current_user["id"])
    job_path = JOB_PATHS.get(progress["job_path_id"], {})

    try:
        feedback = _evaluate_submission(
            task, submission_text, job_path,
            file_content=file_content, file_name=file_name,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI feedback failed: {e}")

    result = (
        _supabase.table("tasks")
        .update({
            "submission": submission_record,
            "feedback":   feedback,
            "status":     "reviewed",
        })
        .eq("id", task_id)
        .execute()
    )
    return result.data[0]


@app.post("/tasks/{task_id}/resubmit")
def resubmit_task(task_id: int, current_user: dict = Depends(get_current_user)):
    get_task_owned_by(task_id, current_user["id"])  # ownership check

    result = (
        _supabase.table("tasks")
        .update({"status": "pending", "submission": None, "feedback": None})
        .eq("id", task_id)
        .execute()
    )
    return result.data[0]
