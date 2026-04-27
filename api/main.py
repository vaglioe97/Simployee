import hashlib
import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, field_validator
from supabase import Client, create_client

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
SUPABASE_URL     = os.environ["SUPABASE_URL"]
SUPABASE_KEY     = os.environ["SUPABASE_KEY"]
JWT_SECRET       = os.environ["JWT_SECRET"]
JWT_ALGORITHM    = "HS256"
JWT_EXPIRE_HOURS = 24

# ── Supabase client ───────────────────────────────────────────────────────────
_supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="Simployee API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Helpers ───────────────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    """SHA-256 hash — matches the logic in app.py and core/database.py."""
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

# ── Auth dependency ───────────────────────────────────────────────────────────
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

# ── Response schema ───────────────────────────────────────────────────────────
def _user_payload(user: dict) -> dict:
    return {
        "id":        user["id"],
        "username":  user["username"],
        "full_name": user["full_name"],
    }

# ── Routes ────────────────────────────────────────────────────────────────────
@app.post("/auth/register", status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest):
    try:
        result = _supabase.table("users").insert({
            "username":  body.username,
            "password":  hash_password(body.password),
            "full_name": body.full_name,
        }).execute()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken.",
        )

    user  = result.data[0]
    token = create_token(user["id"], user["username"])
    return {"token": token, "user": _user_payload(user)}


@app.post("/auth/login")
def login(body: LoginRequest):
    result = (
        _supabase.table("users")
        .select("*")
        .eq("username", body.username)
        .execute()
    )

    # Deliberate generic message — avoids username enumeration
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
