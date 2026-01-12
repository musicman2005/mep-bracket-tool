from __future__ import annotations
import io
import pandas as pd
from sqlalchemy.orm import Session
from .. import models

def _read_csv_bytes(data: bytes) -> pd.DataFrame:
    return pd.read_csv(io.BytesIO(data)).fillna("")

def import_profiles(db: Session, data: bytes) -> dict:
    df = _read_csv_bytes(data)
    inserted = 0
    for _, r in df.iterrows():
        if not r.get("profile_id"):
            continue
        obj = models.Profile(
            manufacturer_id=str(r.get("manufacturer_id")),
            profile_id=str(r.get("profile_id")),
            profile_name=str(r.get("profile_name")),
            material_grade=str(r.get("material_grade")),
            finish=str(r.get("finish")),
            slotted=bool(r.get("slotted")) if str(r.get("slotted")) != "" else True,
            width_mm=int(r.get("width_mm") or 0),
            height_mm=int(r.get("height_mm") or 0),
            thickness_mm=float(r.get("thickness_mm") or 0),
            area_mm2=float(r.get("area_mm2") or 0),
            mass_kg_per_m=float(r.get("mass_kg_per_m") or 0),
            E_N_per_mm2=float(r.get("E_N_per_mm2") or 200000),
            Ixx_mm4=float(r.get("Ixx_mm4") or 0),
            Iyy_mm4=float(r.get("Iyy_mm4") or 0),
            Zxx_mm3=float(r.get("Zxx_mm3") or 0),
            Zyy_mm3=float(r.get("Zyy_mm3") or 0),
            allowable_stress_N_per_mm2=float(r.get("allowable_stress_N_per_mm2") or 0),
            notes=str(r.get("notes")),
            source_ref=str(r.get("source_ref")),
        )
        db.add(obj)
        inserted += 1
    db.commit()
    return {"inserted": inserted, "rows": len(df)}

def import_rods(db: Session, data: bytes) -> dict:
    df = _read_csv_bytes(data)
    inserted = 0
    for _, r in df.iterrows():
        if not r.get("rod_id"):
            continue
        obj = models.Rod(
            manufacturer_id=str(r.get("manufacturer_id")),
            rod_id=str(r.get("rod_id")),
            rod_name=str(r.get("rod_name")),
            thread_type=str(r.get("thread_type")),
            diameter_label=str(r.get("diameter_label")),
            diameter_mm=float(r.get("diameter_mm") or 0),
            stress_area_mm2=float(r.get("stress_area_mm2") or 0),
            material_grade=str(r.get("material_grade")),
            finish=str(r.get("finish")),
            mass_kg_per_m=float(r.get("mass_kg_per_m") or 0),
            allowable_tension_N=float(r.get("allowable_tension_N") or 0),
            allowable_shear_N=float(r.get("allowable_shear_N") or 0),
            fire_reduction_factor=float(r.get("fire_reduction_factor") or 1),
            notes=str(r.get("notes")),
            source_ref=str(r.get("source_ref")),
        )
        db.add(obj)
        inserted += 1
    db.commit()
    return {"inserted": inserted, "rows": len(df)}

def import_washers(db: Session, data: bytes) -> dict:
    df = _read_csv_bytes(data)
    inserted = 0
    for _, r in df.iterrows():
        if not r.get("washer_id"):
            continue
        obj = models.Washer(
            manufacturer_id=str(r.get("manufacturer_id")),
            washer_id=str(r.get("washer_id")),
            washer_name=str(r.get("washer_name")),
            washer_type=str(r.get("washer_type")),
            outer_diameter_mm=float(r.get("outer_diameter_mm") or 0),
            thickness_mm=float(r.get("thickness_mm") or 0),
            hole_diameter_mm=float(r.get("hole_diameter_mm") or 0),
            shape=str(r.get("shape")),
            material_grade=str(r.get("material_grade")),
            finish=str(r.get("finish")),
            bearing_area_multiplier=float(r.get("bearing_area_multiplier") or 1),
            slot_protection_multiplier=float(r.get("slot_protection_multiplier") or 1),
            notes=str(r.get("notes")),
            source_ref=str(r.get("source_ref")),
        )
        db.add(obj)
        inserted += 1
    db.commit()
    return {"inserted": inserted, "rows": len(df)}

def import_anchors(db: Session, data: bytes) -> dict:
    df = _read_csv_bytes(data)
    inserted = 0
    for _, r in df.iterrows():
        if not r.get("anchor_id"):
            continue
        obj = models.Anchor(
            manufacturer_id=str(r.get("manufacturer_id")),
            anchor_id=str(r.get("anchor_id")),
            anchor_name=str(r.get("anchor_name")),
            substrate_type=str(r.get("substrate_type")),
            diameter_mm=float(r.get("diameter_mm") or 0),
            embedment_mm=float(r.get("embedment_mm") or 0),
            allowable_tension_N=float(r.get("allowable_tension_N") or 0),
            allowable_shear_N=float(r.get("allowable_shear_N") or 0),
            fire_reduction_factor=float(r.get("fire_reduction_factor") or 1),
            notes=str(r.get("notes")),
            source_ref=str(r.get("source_ref")),
        )
        db.add(obj)
        inserted += 1
    db.commit()
    return {"inserted": inserted, "rows": len(df)}
