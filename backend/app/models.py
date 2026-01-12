from __future__ import annotations
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    bracket_reference: Mapped[str] = mapped_column(String(80), default="BKT001")
    current_snapshot_json: Mapped[str] = mapped_column(Text)  # full project snapshot
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Revision(Base):
    __tablename__ = "project_revisions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    revision_code: Mapped[str] = mapped_column(String(20), default="P01")
    snapshot_json: Mapped[str] = mapped_column(Text)
    results_json: Mapped[str] = mapped_column(Text)
    pdf_path: Mapped[str] = mapped_column(String(500))
    created_by_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

# Library tables (safe: user imports)
class Profile(Base):
    __tablename__ = "lib_profiles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    manufacturer_id: Mapped[str] = mapped_column(String(50), index=True)
    profile_id: Mapped[str] = mapped_column(String(80), index=True)
    profile_name: Mapped[str] = mapped_column(String(200))
    material_grade: Mapped[str] = mapped_column(String(80), default="")
    finish: Mapped[str] = mapped_column(String(80), default="")
    slotted: Mapped[bool] = mapped_column(Boolean, default=True)
    width_mm: Mapped[int] = mapped_column(Integer, default=0)
    height_mm: Mapped[int] = mapped_column(Integer, default=0)
    thickness_mm: Mapped[float] = mapped_column(Integer, default=0)
    area_mm2: Mapped[float] = mapped_column(Integer, default=0)
    mass_kg_per_m: Mapped[float] = mapped_column(Integer, default=0)
    E_N_per_mm2: Mapped[float] = mapped_column(Integer, default=200000)
    Ixx_mm4: Mapped[float] = mapped_column(Integer, default=0)
    Iyy_mm4: Mapped[float] = mapped_column(Integer, default=0)
    Zxx_mm3: Mapped[float] = mapped_column(Integer, default=0)
    Zyy_mm3: Mapped[float] = mapped_column(Integer, default=0)
    allowable_stress_N_per_mm2: Mapped[float] = mapped_column(Integer, default=0)
    notes: Mapped[str] = mapped_column(Text, default="")
    source_ref: Mapped[str] = mapped_column(Text, default="")

class Rod(Base):
    __tablename__ = "lib_rods"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    manufacturer_id: Mapped[str] = mapped_column(String(50), index=True)
    rod_id: Mapped[str] = mapped_column(String(50), index=True)
    rod_name: Mapped[str] = mapped_column(String(200), default="")
    thread_type: Mapped[str] = mapped_column(String(40), default="M")
    diameter_label: Mapped[str] = mapped_column(String(20), default="")
    diameter_mm: Mapped[float] = mapped_column(Integer, default=0)
    stress_area_mm2: Mapped[float] = mapped_column(Integer, default=0)
    material_grade: Mapped[str] = mapped_column(String(80), default="")
    finish: Mapped[str] = mapped_column(String(80), default="")
    mass_kg_per_m: Mapped[float] = mapped_column(Integer, default=0)
    allowable_tension_N: Mapped[float] = mapped_column(Integer, default=0)
    allowable_shear_N: Mapped[float] = mapped_column(Integer, default=0)
    fire_reduction_factor: Mapped[float] = mapped_column(Integer, default=1)
    notes: Mapped[str] = mapped_column(Text, default="")
    source_ref: Mapped[str] = mapped_column(Text, default="")

class Washer(Base):
    __tablename__ = "lib_washers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    manufacturer_id: Mapped[str] = mapped_column(String(50), index=True)
    washer_id: Mapped[str] = mapped_column(String(80), index=True)
    washer_name: Mapped[str] = mapped_column(String(200), default="")
    washer_type: Mapped[str] = mapped_column(String(80), default="penny")
    outer_diameter_mm: Mapped[float] = mapped_column(Integer, default=0)
    thickness_mm: Mapped[float] = mapped_column(Integer, default=0)
    hole_diameter_mm: Mapped[float] = mapped_column(Integer, default=0)
    shape: Mapped[str] = mapped_column(String(40), default="round")
    material_grade: Mapped[str] = mapped_column(String(80), default="")
    finish: Mapped[str] = mapped_column(String(80), default="")
    bearing_area_multiplier: Mapped[float] = mapped_column(Integer, default=1)
    slot_protection_multiplier: Mapped[float] = mapped_column(Integer, default=1)
    notes: Mapped[str] = mapped_column(Text, default="")
    source_ref: Mapped[str] = mapped_column(Text, default="")

class Anchor(Base):
    __tablename__ = "lib_anchors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    manufacturer_id: Mapped[str] = mapped_column(String(50), index=True)
    anchor_id: Mapped[str] = mapped_column(String(80), index=True)
    anchor_name: Mapped[str] = mapped_column(String(200), default="")
    substrate_type: Mapped[str] = mapped_column(String(80), default="concrete")
    diameter_mm: Mapped[float] = mapped_column(Integer, default=0)
    embedment_mm: Mapped[float] = mapped_column(Integer, default=0)
    allowable_tension_N: Mapped[float] = mapped_column(Integer, default=0)
    allowable_shear_N: Mapped[float] = mapped_column(Integer, default=0)
    fire_reduction_factor: Mapped[float] = mapped_column(Integer, default=1)
    notes: Mapped[str] = mapped_column(Text, default="")
    source_ref: Mapped[str] = mapped_column(Text, default="")
