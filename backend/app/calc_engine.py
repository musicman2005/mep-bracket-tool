from typing import Any, Dict, List, Tuple
import math


def _fy_from_grade(grade: str) -> float:
    # MPa == N/mm2
    g = (grade or "").upper()
    if "355" in g:
        return 355.0
    if "275" in g:
        return 275.0
    if "235" in g:
        return 235.0
    # fallback
    return 235.0


def _parse_tier_loads(snapshot: dict, span_mm: float, tier: int) -> List[Dict[str, Any]]:
    """
    Supports:
    - legacy: loads[tier] = [1500, 1000] (assumes evenly spaced)
    - v3: loads[tier] = [{N:..., x_mm:..., label:...}, ...]
    """
    loads = (snapshot.get("loads") or {})  # may be dict with int keys or str keys
    key_int = tier
    key_str = str(tier)

    arr = loads.get(key_int)
    if arr is None:
        arr = loads.get(key_str, [])

    if not isinstance(arr, list):
        return []

    # Legacy numbers
    if len(arr) > 0 and isinstance(arr[0], (int, float)):
        nums = [float(x) for x in arr if isinstance(x, (int, float))]
        if not nums:
            return []
        # Evenly space them along the span excluding supports
        n = len(nums)
        out = []
        for i, P in enumerate(nums):
            x = span_mm * (i + 1) / (n + 1)
            out.append({"N": float(P), "x_mm": float(x), "label": f"Load {i+1}"})
        return out

    # v3 objects
    out = []
    for it in arr:
        if not isinstance(it, dict):
            continue
        try:
            P = float(it.get("N", 0.0))
            x = float(it.get("x_mm", span_mm / 2.0))
        except Exception:
            continue
        x = max(0.0, min(span_mm, x))
        if P <= 0:
            continue
        out.append({"N": P, "x_mm": x, "label": str(it.get("label", ""))})
    return out


def _reactions_for_point_loads(span_mm: float, loads: List[Dict[str, Any]]) -> Tuple[float, float]:
    L = span_mm
    if L <= 0:
        return (0.0, 0.0)
    Rl = 0.0
    Rr = 0.0
    for it in loads:
        P = float(it["N"])
        a = float(it["x_mm"])
        # Simply supported reactions
        Rl += P * (L - a) / L
        Rr += P * (a) / L
    return (Rl, Rr)


def _moment_at_x(span_mm: float, loads: List[Dict[str, Any]], x: float) -> float:
    """
    Returns bending moment at x (N*mm), taking left support as origin.
    M(x) = sum(P*(x-a)) for loads to left, using left reaction.
    """
    L = span_mm
    if L <= 0:
        return 0.0
    Rl, _ = _reactions_for_point_loads(L, loads)
    M = Rl * x
    for it in loads:
        P = float(it["N"])
        a = float(it["x_mm"])
        if a <= x:
            M -= P * (x - a)
    return M


def _max_moment(span_mm: float, loads: List[Dict[str, Any]]) -> float:
    """
    Sample at key points: load positions + ends.
    Returns max absolute moment (N*mm).
    """
    L = span_mm
    pts = [0.0, L]
    pts += [float(it["x_mm"]) for it in loads]
    pts = sorted(set(max(0.0, min(L, p)) for p in pts))
    mmax = 0.0
    for p in pts:
        m = _moment_at_x(L, loads, p)
        mmax = max(mmax, abs(m))
    # Also sample midpoints between loads for safety
    for i in range(len(pts) - 1):
        mid = 0.5 * (pts[i] + pts[i + 1])
        m = _moment_at_x(L, loads, mid)
        mmax = max(mmax, abs(m))
    return mmax


def _deflection_at_x_point_load(P: float, a: float, L: float, E: float, I: float, x: float) -> float:
    """
    Deflection for simply supported beam with a point load P at position a from left support.
    Uses standard piecewise formula. Returns deflection in mm (positive downward).
    Inputs in N, mm, N/mm2, mm4.
    """
    if L <= 0 or E <= 0 or I <= 0:
        return 0.0
    b = L - a
    if x <= a:
        return (P * b * x * (L * L - b * b - x * x)) / (6.0 * L * E * I)
    else:
        xr = L - x
        return (P * a * xr * (L * L - a * a - xr * xr)) / (6.0 * L * E * I)


def _max_deflection(span_mm: float, loads: List[Dict[str, Any]], E: float, I: float) -> float:
    """
    Numerically sample deflection along the beam using superposition.
    """
    L = span_mm
    if L <= 0:
        return 0.0
    # sampling step (mm)
    step = max(10.0, min(50.0, L / 120.0))
    xmax = 0.0
    x = 0.0
    while x <= L + 1e-6:
        d = 0.0
        for it in loads:
            P = float(it["N"])
            a = float(it["x_mm"])
            d += _deflection_at_x_point_load(P, a, L, E, I, x)
        xmax = max(xmax, abs(d))
        x += step
    return xmax


def run_checks(snapshot: dict, library: dict) -> dict:
    """
    Returns a structured result usable by UI + PDF.
    snapshot keys expected (v3):
      - span_mm
      - tier_count
      - loads: {1:[{N,x_mm,label,...}], 2:[], 3:[]}
      - profile_id, rod_id, washer_id, anchor_id
    library expected:
      - profile (dict), rod (dict), washer (dict), anchor (dict)
      - bearing_area_multiplier (float)
    """
    span_mm = float(snapshot.get("span_mm") or 0)
    tier_count = int(snapshot.get("tier_count") or 1)
    tier_count = max(1, min(3, tier_count))

    prof = library.get("profile") or {}
    rod = library.get("rod") or {}
    washer = library.get("washer") or {}
    anchor = library.get("anchor") or {}

    E = float(prof.get("E_N_per_mm2") or 200000.0)
    Ixx = float(prof.get("Ixx_mm4") or 1.0)
    Zxx = float(prof.get("Zxx_mm3") or 1.0)

    grade = str(prof.get("material_grade") or "S235")
    fy = _fy_from_grade(grade)
    sigma_allow = 0.6 * fy  # basic allowable stress (placeholder rule)

    defl_limit_mm = span_mm / 200.0 if span_mm > 0 else 0.0

    reactions = {}
    max_moment = {}
    max_defl = {}
    notes: List[str] = []

    total_Rl = 0.0
    total_Rr = 0.0
    total_mmax = 0.0
    total_dmax = 0.0
    total_weight_kg = 0.0
    per_tier_weight_kg = {}

    # Tier-by-tier
    for t in range(1, tier_count + 1):
        loads_t = _parse_tier_loads(snapshot, span_mm, t)
        Rl, Rr = _reactions_for_point_loads(span_mm, loads_t)
        mmax = _max_moment(span_mm, loads_t)          # Nmm
        dmax = _max_deflection(span_mm, loads_t, E, Ixx)  # mm

        reactions[f"tier{t}"] = {"left": Rl, "right": Rr}
        max_moment[f"tier{t}"] = (mmax / 1e6)  # kNm (since Nmm -> kN*m = /1e6)
        max_defl[f"tier{t}"] = dmax

        total_Rl += Rl
        total_Rr += Rr
        total_mmax = max(total_mmax, mmax)
        total_dmax = max(total_dmax, dmax)

        # Weight estimate (kg): N / 9.81
        tier_N = sum(float(it["N"]) for it in loads_t)
        tier_kg = tier_N / 9.81 if tier_N > 0 else 0.0
        per_tier_weight_kg[str(t)] = tier_kg
        total_weight_kg += tier_kg

    reactions["total"] = {"left": total_Rl, "right": total_Rr}
    max_moment["total"] = (total_mmax / 1e6)
    max_defl["total"] = total_dmax

    # Checks
    checks = {"deflection": "PASS", "bending": "PASS", "rod": "PASS", "anchor": "PASS"}

    # Bending stress from max moment
    # sigma = M / Z (Nmm / mm3 = N/mm2)
    sigma = (total_mmax / Zxx) if Zxx > 0 else float("inf")
    if sigma > sigma_allow:
        checks["bending"] = "FAIL"
        notes.append(f"Bending stress {sigma:.1f} N/mm² exceeds allowable {sigma_allow:.1f} N/mm² (rule-of-thumb).")

    if defl_limit_mm > 0 and total_dmax > defl_limit_mm:
        checks["deflection"] = "FAIL"
        notes.append(f"Deflection {total_dmax:.2f} mm exceeds limit {defl_limit_mm:.2f} mm (L/200 placeholder).")

    # Rod check (tension per rod = max(total left/right) assuming 2 rods)
    rod_force = max(total_Rl, total_Rr)
    rod_per = rod_force  # per rod if one rod per support
    # If you later do 2 rods per support, modify here.
    rod_cap = None
    for k in ["tension_capacity_N", "capacity_N", "tension_N"]:
        if k in rod and rod.get(k) not in (None, ""):
            try:
                rod_cap = float(rod.get(k))
                break
            except Exception:
                pass
    if rod_cap is not None and rod_per > rod_cap:
        checks["rod"] = "FAIL"
        notes.append(f"Rod demand {rod_per:.0f} N exceeds capacity {rod_cap:.0f} N.")

    # Anchor check (same as rod demand for now)
    anchor_cap = None
    for k in ["tension_capacity_N", "capacity_N", "tension_N"]:
        if k in anchor and anchor.get(k) not in (None, ""):
            try:
                anchor_cap = float(anchor.get(k))
                break
            except Exception:
                pass
    if anchor_cap is not None and rod_per > anchor_cap:
        checks["anchor"] = "FAIL"
        notes.append(f"Anchor demand {rod_per:.0f} N exceeds capacity {anchor_cap:.0f} N.")

    # Governing
    governing = "PASS"
    if "FAIL" in checks.values():
        for k in ["bending", "deflection", "rod", "anchor"]:
            if checks[k] == "FAIL":
                governing = k
                break

    status = "PASS" if governing == "PASS" else "FAIL"

    return {
        "status": status,
        "governing_check": governing,
        "total_weight_kg": float(total_weight_kg),
        "per_tier_weight_kg": {**{"1": 0.0, "2": 0.0, "3": 0.0}, **per_tier_weight_kg},
        "rod_min_size": str(snapshot.get("rod_id") or "—"),
        "checks": checks,
        "notes": notes,
        "reactions_N": reactions,
        "max_moment_kNm": max_moment,
        "max_deflection_mm": max_defl,
        "deflection_limit_mm": float(defl_limit_mm),
        "library_used": {
            "profile": prof,
            "rod": rod,
            "washer": washer,
            "anchor": anchor,
            "bearing_area_multiplier": float(library.get("bearing_area_multiplier") or 1.0),
        },
    }
