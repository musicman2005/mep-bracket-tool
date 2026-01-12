from __future__ import annotations
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

# Trapeze bracket snapshot schema (stored as JSON in DB)
class BracketConfig(BaseModel):
    spacing_mm: int = 1500
    overall_width_mm: int = 600
    tier_count: int = 3
    tier_spacing_mm: int = 300
    drop_rod_size: str = "M10"

    # Library selections (IDs refer to manufacturer parts)
    strut_profile_id: Optional[str] = None   # e.g. "hilti:MQ-41" or "atkore:P1000T"
    washer_id: Optional[str] = None          # e.g. "hilti:XYZ"
    anchor_id: Optional[str] = None          # e.g. "hilti:HST3"

class ServiceItem(BaseModel):
    service_type: str  # pipe/duct/tray/basket/ladder/trunking
    tier: int
    weight_kg_per_m: float
    spacing_mm: int = 300
    notes: str = ""

class ProjectCreate(BaseModel):
    name: str
    bracket_reference: str = "BKT001"
    bracket: BracketConfig = Field(default_factory=BracketConfig)
    services: List[ServiceItem] = Field(default_factory=list)

class ProjectListItem(BaseModel):
    id: str
    name: str
    bracket_reference: str
    updated_at: datetime

class ProjectListResponse(BaseModel):
    items: List[ProjectListItem]

class CheckResult(BaseModel):
    status: str
    governing_check: str
    total_weight_kg: float
    per_tier_weight_kg: Dict[int, float]
    rod_min_size: str
    checks: Dict[str, str]
    notes: List[str] = []
    deflection_mm: Dict[int, float] = {}
    max_moment_knm: Dict[int, float] = {}
    library_used: Dict[str, Any] = {}
