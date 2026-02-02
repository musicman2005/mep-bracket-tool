from pydantic import BaseModel, EmailStr
from typing import Any, Dict, List, Optional
from datetime import datetime


# -------- Auth --------
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# -------- Projects --------
class ProjectCreate(BaseModel):
    name: str
    bracket_reference: str


class ProjectListItem(BaseModel):
    id: str
    name: str
    bracket_reference: str
    updated_at: datetime


class ProjectListResponse(BaseModel):
    items: List[ProjectListItem]


class ProjectUpdate(BaseModel):
    # Store current tool snapshot (bracket + loads + any UI state)
    snapshot: Dict[str, Any]
    name: Optional[str] = None
    bracket_reference: Optional[str] = None


# -------- Checks --------
class CheckResult(BaseModel):
    status: str
    governing_check: str
    total_weight_kg: float
    per_tier_weight_kg: Dict[str, float]
    rod_min_size: str

    checks: Dict[str, str]
    notes: List[str]

    reactions_N: Dict[str, Dict[str, float]]  # {"tier1":{"left":..,"right":..}, ...} and "total"
    max_moment_kNm: Dict[str, float]          # per tier + "total"
    max_deflection_mm: Dict[str, float]       # per tier + "total"

    deflection_limit_mm: float

    library_used: Dict[str, Any] = {}
