"""
naval_identifier.py — Knowledge-based candidate identification for Indian
Naval vessels, self-contained within backend/ for standalone deployment.

Same logic as the repo-root naval_vessel_identifier.py, adapted to live
inside backend/app/services/ and load its own copy of the knowledge pack
(backend/maritime_knowledge/) so backend/ remains deployable on its own,
consistent with bucket_client.py's self-containment pattern.

This is NOT a vision model — see the module docstring in the original
script for the full rationale.
"""

import json
import os

KNOWLEDGE_PACK_PATH = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "maritime_knowledge", "indian_naval_knowledge_pack.json"
))

VESSEL_TYPE_KEYWORDS = {
    "destroyer": ["destroyer"],
    "frigate": ["frigate"],
    "corvette": ["corvette"],
    "carrier": ["aircraft carrier"],
    "submarine": ["submarine"],
}


def load_knowledge_pack():
    with open(KNOWLEDGE_PACK_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _length_score(entry_length, user_length_m, tolerance_m=25, max_pts=25):
    if user_length_m is None or entry_length is None:
        return 0
    try:
        diff = abs(float(entry_length) - float(user_length_m))
    except (TypeError, ValueError):
        return 0
    if diff <= 5:
        return max_pts
    if diff >= tolerance_m:
        return 0
    return int(max_pts * (1 - diff / tolerance_m))


def _beam_score(entry_beam, user_beam_m, tolerance_m=5, max_pts=15):
    if user_beam_m is None or entry_beam is None:
        return 0
    try:
        diff = abs(float(entry_beam) - float(user_beam_m))
    except (TypeError, ValueError):
        return 0
    if diff <= 1:
        return max_pts
    if diff >= tolerance_m:
        return 0
    return int(max_pts * (1 - diff / tolerance_m))


def _displacement_score(entry_disp, user_disp_tons, tolerance_pct=0.25, max_pts=20):
    """Uses relative (%) difference rather than absolute, since displacement
    ranges from ~1,600 tons (Kalvari) to ~45,000 tons (carriers) — an
    absolute tolerance would be meaningless across that range."""
    if user_disp_tons is None or entry_disp is None:
        return 0
    try:
        entry_disp = float(entry_disp)
        user_disp_tons = float(user_disp_tons)
    except (TypeError, ValueError):
        return 0
    if entry_disp == 0:
        return 0
    pct_diff = abs(entry_disp - user_disp_tons) / entry_disp
    if pct_diff <= 0.05:
        return max_pts
    if pct_diff >= tolerance_pct:
        return 0
    return int(max_pts * (1 - pct_diff / tolerance_pct))


def _type_score(entry, vessel_type, max_pts=20):
    if not vessel_type:
        return 0
    entry_type = (entry.get("vessel_type") or "").lower()
    vt = vessel_type.lower()
    if vt == "submarine":
        # "anti-submarine" describes a corvette/frigate's ROLE, not an
        # actual submarine — exclude it explicitly to avoid a false match.
        return max_pts if "submarine" in entry_type and "anti-submarine" not in entry_type else 0
    keywords = VESSEL_TYPE_KEYWORDS.get(vt, [vt])
    return max_pts if any(k in entry_type for k in keywords) else 0


def _text_score(entry, description, max_pts=25):
    if not description:
        return 0
    haystack = " ".join([
        str(entry.get("hull_superstructure", "")),
        str(entry.get("mast_radar_funnel_profile", "")),
        str(entry.get("radar_signature", "")),
    ]).lower()
    desc_words = [w.strip(".,") for w in description.lower().split() if len(w.strip(".,")) > 3]
    if not desc_words:
        return 0
    matches = sum(1 for w in desc_words if w in haystack)
    return min(max_pts, matches * 6)


def identify_candidates(
    length_m=None,
    beam_m=None,
    displacement_tons=None,
    vessel_type=None,
    hull_color=None,
    description=None,
    top_n=3,
):
    """All parameters are optional — the user may supply any subset."""
    pack = load_knowledge_pack()
    scored = []

    for entry in pack:
        score = 0
        reasons = []

        length_pts = _length_score(entry.get("length_m"), length_m)
        if length_pts:
            score += length_pts
            reasons.append(f"length ~{entry.get('length_m')}m is close to your estimate")

        beam_pts = _beam_score(entry.get("beam_m"), beam_m)
        if beam_pts:
            score += beam_pts
            reasons.append(f"beam ~{entry.get('beam_m')}m is close to your estimate")

        disp_pts = _displacement_score(entry.get("displacement_tons"), displacement_tons)
        if disp_pts:
            score += disp_pts
            reasons.append(f"displacement ~{entry.get('displacement_tons')} tons is close to your estimate")

        type_pts = _type_score(entry, vessel_type)
        if type_pts:
            score += type_pts
            reasons.append(f"vessel type matches ({entry.get('vessel_type')})")

        text_pts = _text_score(entry, description)
        if text_pts:
            score += text_pts
            reasons.append("description matches known hull/mast/funnel characteristics")

        if hull_color and "grey" in hull_color.lower():
            score += 5
            reasons.append("hull colour consistent with standard naval grey (weak signal only)")

        if score > 0:
            scored.append({
                "class_name": entry["class_name"],
                "vessel_id": entry["vessel_id"],
                "confidence_pct": min(99, score),
                "risk_level": entry.get("risk_level", "MEDIUM"),
                "reasoning": reasons,
                "validation_status": entry.get("validation_status"),
            })

    scored.sort(key=lambda x: x["confidence_pct"], reverse=True)
    return scored[:top_n] if scored else [{
        "class_name": None,
        "vessel_id": None,
        "confidence_pct": 0,
        "risk_level": None,
        "reasoning": ["No candidates matched the provided input strongly enough — try providing more detail (length, beam, displacement, vessel type, or a description) or a clearer image."],
        "validation_status": None,
    }]
