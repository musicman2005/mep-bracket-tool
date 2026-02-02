import json
from datetime import datetime
from uuid import uuid4
from typing import Any, Dict

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy.orm import Session
from sqlalchemy import text

from . import models, schemas
from .db import get_db
from .auth import (
    create_access_token,
    get_current_user_id,
    hash_password,
    verify_password,
)
from .importers.csv_import import (
    import_profiles,
    import_rods,
    import_washers,
    import_anchors,
)
from .calc_engine import run_checks
from .pdf_report import build_pdf

app = FastAPI(title="mep-bracket-tool")

# CORS for simple LAN hosting
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Auth ----------
@app.post("/auth/register")
def register(req: schemas.RegisterRequest, db: Session = Depends(get_db)):
    exists = db.query(models.User).filter(models.User.email == req.email).first()
    if exists:
        raise HTTPException(status_code=400, detail="Email already registered")
    u = models.User(email=req.email, password_hash=hash_password(req.password))
    db.add(u)
    db.commit()
    return {"ok": True}

@app.post("/auth/login", response_model=schemas.TokenResponse)
def login(req: schemas.LoginRequest, db: Session = Depends(get_db)):
    u = db.query(models.User).filter(models.User.email == req.email).first()
    if not u or not verify_password(req.password, u.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    tok = create_access_token(u.id, u.email)
    return schemas.TokenResponse(access_token=tok)

# ---------- Library import (auth required) ----------
@app.post("/library/import/{kind}")
def import_library(
    kind: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    data = file.file.read()
    if kind == "profiles":
        return import_profiles(db, data)
    if kind == "rods":
        return import_rods(db, data)
    if kind == "washers":
        return import_washers(db, data)
    if kind == "anchors":
        return import_anchors(db, data)
    raise HTTPException(status_code=404, detail="Unknown kind")

# ---------- Library read (auth required) ----------
LIB_TABLES = {
    "profiles": "lib_profiles",
    "rods": "lib_rods",
    "washers": "lib_washers",
    "anchors": "lib_anchors",
}

@app.get("/library/{kind}")
def list_library(
    kind: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    table = LIB_TABLES.get(kind)
    if not table:
        raise HTTPException(status_code=400, detail=f"Unknown library kind: {kind}")
    rows = db.execute(text(f"SELECT * FROM {table} ORDER BY id")).mappings().all()
    return {"items": [dict(r) for r in rows]}

@app.get("/library/{kind}/{item_id}")
def get_library_item(
    kind: str,
    item_id: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    table = LIB_TABLES.get(kind)
    if not table:
        raise HTTPException(status_code=400, detail=f"Unknown library kind: {kind}")
    row = db.execute(
        text(f"SELECT * FROM {table} WHERE id = :id LIMIT 1"),
        {"id": item_id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    return dict(row)

# ---------- Projects ----------
def _get_project(db: Session, project_id: str, user_id: int) -> models.Project:
    p = (
        db.query(models.Project)
        .filter(models.Project.id == project_id, models.Project.owner_user_id == user_id)
        .first()
    )
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return p

@app.post("/projects")
def create_project(
    req: schemas.ProjectCreate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)
):
    pid = str(uuid4())
    snapshot = req.model_dump()
    p = models.Project(
        id=pid,
        owner_user_id=user_id,
        name=req.name,
        bracket_reference=req.bracket_reference,
        current_snapshot_json=json.dumps(snapshot),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(p)
    db.commit()
    return {"id": pid}

@app.get("/projects", response_model=schemas.ProjectListResponse)
def list_projects(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    items = (
        db.query(models.Project)
        .filter(models.Project.owner_user_id == user_id)
        .order_by(models.Project.updated_at.desc())
        .all()
    )
    return schemas.ProjectListResponse(
        items=[
            schemas.ProjectListItem(
                id=p.id,
                name=p.name,
                bracket_reference=p.bracket_reference,
                updated_at=p.updated_at,
            )
            for p in items
        ]
    )

@app.get("/projects/{project_id}")
def get_project(project_id: str, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    p = _get_project(db, project_id, user_id)
    return json.loads(p.current_snapshot_json)

def resolve_library(db: Session, snapshot: dict) -> Dict[str, Any]:
    """
    Resolve the selected library items based on snapshot ids.
    Snapshot uses keys:
      profile_id, rod_id, washer_id, anchor_id
    Library tables store those as columns like profile_id etc.
    """
    out: Dict[str, Any] = {"profile": None, "rod": None, "washer": None, "anchor": None}

    # Note: the DB primary key is `id` (int), but selections are the *string ids*
    # like GEN_41x41 etc. So we lookup by the appropriate column.
    prof_id = snapshot.get("profile_id")
    rod_id = snapshot.get("rod_id")
    washer_id = snapshot.get("washer_id")
    anchor_id = snapshot.get("anchor_id")

    if prof_id:
        row = db.execute(
            text("SELECT * FROM lib_profiles WHERE profile_id = :x LIMIT 1"),
            {"x": prof_id},
        ).mappings().first()
        out["profile"] = dict(row) if row else None

    if rod_id:
        row = db.execute(
            text("SELECT * FROM lib_rods WHERE rod_id = :x LIMIT 1"),
            {"x": rod_id},
        ).mappings().first()
        out["rod"] = dict(row) if row else None

    if washer_id:
        row = db.execute(
            text("SELECT * FROM lib_washers WHERE washer_id = :x LIMIT 1"),
            {"x": washer_id},
        ).mappings().first()
        out["washer"] = dict(row) if row else None

    if anchor_id:
        row = db.execute(
            text("SELECT * FROM lib_anchors WHERE anchor_id = :x LIMIT 1"),
            {"x": anchor_id},
        ).mappings().first()
        out["anchor"] = dict(row) if row else None

    # Bearing multiplier (defaults to 1.0)
    bm = 1.0
    try:
        if out["washer"] and out["washer"].get("bearing_area_multiplier") not in (None, ""):
            bm = float(out["washer"]["bearing_area_multiplier"])
    except Exception:
        bm = 1.0

    out["bearing_area_multiplier"] = bm

    # Optional: rod capacities dict if present in your table (or leave empty)
    # calc_engine currently checks library.get("rod_caps") - keep compatible:
    out["rod_caps"] = {}

    return out

@app.post("/projects/{project_id}/check", response_model=schemas.CheckResult)
def check_project(project_id: str, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    p = _get_project(db, project_id, user_id)
    snapshot = json.loads(p.current_snapshot_json)

    lib = resolve_library(db, snapshot)
    res = run_checks(snapshot, lib)
    return res

@app.post("/projects/{project_id}/pdf")
def pdf_project(project_id: str, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    p = _get_project(db, project_id, user_id)
    snapshot = json.loads(p.current_snapshot_json)
    lib = resolve_library(db, snapshot)
    res = run_checks(snapshot, lib)

    pdf_bytes = build_pdf(
        project_name=p.name,
        bracket_reference=p.bracket_reference,
        snapshot=snapshot,
        result=res,
        tool_version="v2",
        library_version="user-supplied",
    )
    return {"pdf_base64": pdf_bytes.decode("latin1")}
