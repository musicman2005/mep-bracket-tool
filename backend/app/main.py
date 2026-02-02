from __future__ import annotations
import os, json
from datetime import datetime
from uuid import uuid4
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy.orm import Session

from .db import Base, engine, get_db
from . import models, schemas
from .auth import hash_password, verify_password, create_access_token, get_current_user_id
from .calc_engine import run_checks, parse_rod_size
from .pdf_report import build_pdf
from .importers.csv_import import import_profiles, import_rods, import_washers, import_anchors
from sqlalchemy import text

TOOL_VERSION = "0.1.0"
PDF_OUTPUT_DIR = os.getenv("PDF_OUTPUT_DIR", "/data/pdfs")

app = FastAPI(title="MEP Bracket Tool API", version=TOOL_VERSION)

# CORS
cors = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[c.strip() for c in cors if c.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def _startup():
    os.makedirs(PDF_OUTPUT_DIR, exist_ok=True)
    Base.metadata.create_all(bind=engine)

@app.get("/health")
def health():
    return {"ok": True, "version": TOOL_VERSION}

# ---- Auth ----
@app.post("/auth/register")
def register(req: schemas.RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    u = models.User(email=req.email, password_hash=hash_password(req.password))
    db.add(u)
    db.commit()
    db.refresh(u)
    return {"id": u.id, "email": u.email}

@app.post("/auth/login", response_model=schemas.TokenResponse)
def login(req: schemas.LoginRequest, db: Session = Depends(get_db)):
    u = db.query(models.User).filter(models.User.email == req.email).first()
    if not u or not verify_password(req.password, u.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    tok = create_access_token(u.id, u.email)
    return schemas.TokenResponse(access_token=tok)

# ---- Library import (auth required) ----
@app.post("/library/import/{kind}")
def import_library(kind: str, file: UploadFile = File(...), db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
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
# ---- Projects ----
def _get_project(db: Session, project_id: str, user_id: int) -> models.Project:
    p = db.query(models.Project).filter(models.Project.id == project_id, models.Project.owner_user_id == user_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return p

@app.post("/projects")
def create_project(req: schemas.ProjectCreate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
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
    items = db.query(models.Project).filter(models.Project.owner_user_id == user_id).order_by(models.Project.updated_at.desc()).all()
    return schemas.ProjectListResponse(items=[
        schemas.ProjectListItem(id=p.id, name=p.name, bracket_reference=p.bracket_reference, updated_at=p.updated_at)
        for p in items
    ])

@app.get("/projects/{project_id}")
def get_project(project_id: str, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    p = _get_project(db, project_id, user_id)
    return json.loads(p.current_snapshot_json)

@app.post("/projects/{project_id}/check", response_model=schemas.CheckResult)
def check_project(project_id: str, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    p = _get_project(db, project_id, user_id)
    snapshot = json.loads(p.current_snapshot_json)

    # Resolve library selections
    lib = resolve_library(db, snapshot)

    res = run_checks(snapshot, lib)
    return res

def resolve_library(db: Session, snapshot: dict) -> dict:
    b = snapshot.get("bracket") or {}
    profile_key = b.get("strut_profile_id")
    washer_key = b.get("washer_id")
    anchor_key = b.get("anchor_id")
    rod_sel = b.get("drop_rod_size","M10")

    def split_key(k: str):
        if not k or ":" not in k:
            return None, None
        m, pid = k.split(":", 1)
        return m, pid

    prof = None
    if profile_key:
        m, pid = split_key(profile_key)
        prof = db.query(models.Profile).filter(models.Profile.manufacturer_id == m, models.Profile.profile_id == pid).first()

    wash = None
    if washer_key:
        m, wid = split_key(washer_key)
        wash = db.query(models.Washer).filter(models.Washer.manufacturer_id == m, models.Washer.washer_id == wid).first()

    anch = None
    if anchor_key:
        m, aid = split_key(anchor_key)
        anch = db.query(models.Anchor).filter(models.Anchor.manufacturer_id == m, models.Anchor.anchor_id == aid).first()

    # Rod capacities: build dict M10->N from imported rods
    rod_caps = {}
    rods = db.query(models.Rod).all()
    for r in rods:
        key = parse_rod_size(r.diameter_label or r.rod_id)
        if r.allowable_tension_N:
            rod_caps[key] = float(r.allowable_tension_N)

    return {
        "profile": prof.__dict__ if prof else {},
        "washer": wash.__dict__ if wash else {},
        "anchor": anch.__dict__ if anch else {},
        "rod_caps": rod_caps
    }

@app.get("/projects/{project_id}/pdf")
def pdf_project(project_id: str, token: str = Query(default=""), db: Session = Depends(get_db)):
    # Support token via Authorization header or query param (for simple frontend new-tab download)
    # NOTE: In production, prefer header-based auth only.
    from jose import jwt
    from .auth import JWT_SECRET, JWT_ISSUER, JWT_AUDIENCE

    user_id = None
    if token:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"], audience=JWT_AUDIENCE, issuer=JWT_ISSUER)
            user_id = int(payload["sub"])
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token")
    else:
        raise HTTPException(status_code=401, detail="Token required (use header in real frontend)")

    p = _get_project(db, project_id, user_id)
    snapshot = json.loads(p.current_snapshot_json)
    lib = resolve_library(db, snapshot)
    res = run_checks(snapshot, lib)

    pdf_bytes = build_pdf(p.name, p.bracket_reference, snapshot, res, tool_version=TOOL_VERSION)

    # Save revision record + pdf file
    rev_code = f"P{str((db.query(models.Revision).filter(models.Revision.project_id==p.id).count()+1)).zfill(2)}"
    filename = f"{p.bracket_reference}_{rev_code}_{p.id}.pdf"
    path = os.path.join(PDF_OUTPUT_DIR, filename)
    with open(path, "wb") as f:
        f.write(pdf_bytes)

    rev = models.Revision(
        project_id=p.id,
        revision_code=rev_code,
        snapshot_json=json.dumps(snapshot),
        results_json=json.dumps(res),
        pdf_path=path,
        created_by_user_id=user_id,
        created_at=datetime.utcnow(),
    )
    db.add(rev)
    p.updated_at = datetime.utcnow()
    db.commit()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
