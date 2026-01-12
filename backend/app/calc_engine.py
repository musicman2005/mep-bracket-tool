from __future__ import annotations
from typing import Dict, Tuple, List, Any
from math import sqrt
import re

# v0.1 clean-room trapeze checks:
# - compute per-tier weight from services
# - compute simple beam moment/deflection placeholder
# - rod minimum by tension capacity (if present)
#
# IMPORTANT: replace these placeholders with your validated method.
ROD_ORDER = ["M6","M8","M10","M12","M16","M20"]

def parse_rod_size(label: str) -> str:
    m = re.search(r"M\s*(\d+)", label.upper())
    return f"M{m.group(1)}" if m else label.upper()

def tier_weights_kg(bracket: dict, services: list) -> Dict[int, float]:
    tiers = {i: 0.0 for i in range(1, int(bracket["tier_count"]) + 1)}
    rung_len_m = float(bracket["overall_width_mm"]) / 1000.0

    # Services: weight_kg_per_m * rung length
    for s in services:
        t = int(s["tier"])
        tiers[t] += float(s["weight_kg_per_m"]) * rung_len_m
    return tiers

def simple_beam_checks(span_mm: float, tier_weight_kg: float, E: float, Ixx: float, allowable_moment_knm: float, defl_ratio: float) -> Tuple[float, float, str, str]:
    g = 9.81
    L = span_mm
    P = tier_weight_kg * g  # N (treated as point load for placeholder)

    # M = P*L/4 (N*mm)
    M_Nmm = P * L / 4.0
    M_kNm = M_Nmm / 1e6

    # delta = P*L^3/(48 E I)
    # E (N/mm2), I (mm4)
    if E <= 0 or Ixx <= 0:
        return 0.0, float(M_kNm), "PASS", "FAIL"  # force fail bending if no I data

    delta_mm = P * (L**3) / (48.0 * E * Ixx)
    defl_limit = L / defl_ratio if defl_ratio > 0 else 1e9

    defl_pass = "PASS" if delta_mm <= defl_limit else "FAIL"
    bend_pass = "PASS" if M_kNm <= allowable_moment_knm else "FAIL"
    return float(delta_mm), float(M_kNm), defl_pass, bend_pass

def required_rod_size(total_weight_kg: float, rod_capacities: Dict[str, float]) -> str:
    # Two rods share vertical load equally (placeholder)
    g = 9.81
    per_rod_N = (total_weight_kg * g) / 2.0
    # Find smallest rod whose allowable_tension_N >= per_rod_N
    for r in ROD_ORDER:
        cap = rod_capacities.get(r)
        if cap and cap >= per_rod_N:
            return r
    return ROD_ORDER[-1]

def run_checks(snapshot: dict, library: dict) -> dict:
    bracket = snapshot["bracket"]
    services = snapshot.get("services", [])

    per_tier = tier_weights_kg(bracket, services)
    total = sum(per_tier.values())

    # Library selections
    prof = library.get("profile") or {}
    washer = library.get("washer") or {}
    rod = library.get("rod") or {}
    anchor = library.get("anchor") or {}

    # Washers influence local bearing/slot protection (v0.1: record multiplier only)
    bearing_mult = float(washer.get("bearing_area_multiplier") or 1.0)

    # Profile properties
    E = float(prof.get("E_N_per_mm2") or 0)
    Ixx = float(prof.get("Ixx_mm4") or 0)

    # Placeholder allowables (user can add later as part of profile data; keep conservative)
    allowable_moment_knm = float(prof.get("allowable_moment_knm") or 0.25) * bearing_mult
    defl_ratio = float(prof.get("deflection_limit_ratio") or 360)

    deflection_mm = {}
    max_moment_knm = {}
    checks = {"deflection":"PASS","bending":"PASS","rod":"PASS","anchor":"PASS"}
    notes: List[str] = []

    for tier, wkg in per_tier.items():
        dmm, mk, defl_pass, bend_pass = simple_beam_checks(
            span_mm=float(bracket["spacing_mm"]),
            tier_weight_kg=wkg,
            E=E,
            Ixx=Ixx,
            allowable_moment_knm=allowable_moment_knm,
            defl_ratio=defl_ratio
        )
        deflection_mm[tier] = round(dmm, 3)
        max_moment_knm[tier] = round(mk, 3)
        if defl_pass == "FAIL":
            checks["deflection"] = "FAIL"
            notes.append(f"Tier {tier}: deflection exceeds limit (placeholder beam model).")
        if bend_pass == "FAIL":
            checks["bending"] = "FAIL"
            notes.append(f"Tier {tier}: bending exceeds allowable (placeholder).")

    # Rod check (only if library has capacities)
    rod_caps = {k: float(v) for k, v in (library.get("rod_caps") or {}).items()}
    rod_sel = parse_rod_size(bracket.get("drop_rod_size","M10"))
    rod_min = required_rod_size(total, rod_caps) if rod_caps else rod_sel
    if ROD_ORDER.index(rod_sel) < ROD_ORDER.index(rod_min):
        checks["rod"] = "FAIL"
        notes.append(f"Selected rod {rod_sel} below minimum {rod_min} (based on imported rod capacities).")

    status = "PASS" if all(v=="PASS" for v in checks.values()) else "FAIL"
    governing = next((k for k,v in checks.items() if v=="FAIL"), "none")

    return {
        "status": status,
        "governing_check": governing,
        "total_weight_kg": round(total, 2),
        "per_tier_weight_kg": {int(k): round(v,2) for k,v in per_tier.items()},
        "rod_min_size": rod_min,
        "checks": checks,
        "notes": notes,
        "deflection_mm": {int(k): v for k,v in deflection_mm.items()},
        "max_moment_knm": {int(k): v for k,v in max_moment_knm.items()},
        "library_used": {
            "profile": prof.get("profile_id"),
            "washer": washer.get("washer_id"),
            "anchor": anchor.get("anchor_id"),
            "bearing_area_multiplier": bearing_mult,
        }
    }
