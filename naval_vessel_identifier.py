"""
naval_vessel_identifier.py — Knowledge-based candidate identification for
Indian Naval vessels, using the curated maritime_knowledge/indian_naval_knowledge_pack.json.

This is NOT a vision model and does NOT do image classification. It is a
knowledge-grounding / candidate-validation layer, matching whatever the
user can provide (estimated dimensions, hull colour, number of
funnels/masts, vessel type, or free-text description of what they see)
against the curated knowledge pack, and returns ranked candidate matches
with the reasoning behind each score. This is meant to help when a clear
photo isn't available or the vision model can't confidently classify —
consistent with the task's "Vision Candidate Validation" step, which uses
knowledge grounding to support identification, not replace it.

Usage (interactive):
    python naval_vessel_identifier.py

Usage (programmatic):
    from naval_vessel_identifier import identify_candidates
    results = identify_candidates(
        length_m=160, vessel_type="destroyer", hull_color="grey",
        description="single funnel, angled superstructure, looks stealthy"
    )
"""

import json
import os

KNOWLEDGE_PACK_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "maritime_knowledge", "indian_naval_knowledge_pack.json"
)


def load_knowledge_pack():
    with open(KNOWLEDGE_PACK_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


VESSEL_TYPE_KEYWORDS = {
    "destroyer": ["destroyer"],
    "frigate": ["frigate"],
    "corvette": ["corvette"],
    "carrier": ["aircraft carrier"],
    "submarine": ["submarine"],
}


def _length_score(entry_length, user_length_m, tolerance_m=25):
    """Returns 0-40 points based on how close the lengths are."""
    if user_length_m is None or entry_length is None:
        return 0
    try:
        diff = abs(float(entry_length) - float(user_length_m))
    except (TypeError, ValueError):
        return 0
    if diff <= 5:
        return 40
    if diff >= tolerance_m:
        return 0
    return int(40 * (1 - diff / tolerance_m))


def _type_score(entry, vessel_type):
    """Returns 0-25 points if the stated vessel_type matches entry's vessel_type field."""
    if not vessel_type:
        return 0
    entry_type = (entry.get("vessel_type") or "").lower()
    keywords = VESSEL_TYPE_KEYWORDS.get(vessel_type.lower(), [vessel_type.lower()])
    return 25 if any(k in entry_type for k in keywords) else 0


def _text_score(entry, description):
    """Returns 0-35 points based on free-text keyword overlap against
    hull/superstructure and mast/radar/funnel fields."""
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
    return min(35, matches * 8)


def identify_candidates(length_m=None, vessel_type=None, hull_color=None, description=None, top_n=3):
    """
    Returns a ranked list of candidate vessel classes with a 0-100 match
    score and the reasoning behind it — same top_predictions shape used
    elsewhere in SVACS, for consistency.
    """
    pack = load_knowledge_pack()
    scored = []

    for entry in pack:
        score = 0
        reasons = []

        length_pts = _length_score(entry.get("length_m"), length_m)
        if length_pts:
            score += length_pts
            reasons.append(f"length ~{entry.get('length_m')}m is close to your estimate")

        type_pts = _type_score(entry, vessel_type)
        if type_pts:
            score += type_pts
            reasons.append(f"vessel type matches ({entry.get('vessel_type')})")

        text_pts = _text_score(entry, description)
        if text_pts:
            score += text_pts
            reasons.append("description matches known hull/mast/funnel characteristics")

        if hull_color and "grey" in hull_color.lower():
            score += 5  # nearly all naval vessels are grey; weak signal, not diagnostic alone
            reasons.append("hull colour consistent with standard naval grey (weak signal only)")

        if score > 0:
            scored.append({
                "class_name": entry["class_name"],
                "vessel_id": entry["vessel_id"],
                "confidence_pct": min(99, score),  # cap below 100 — this is heuristic, never certain
                "reasoning": reasons,
                "validation_status": entry.get("validation_status"),
            })

    scored.sort(key=lambda x: x["confidence_pct"], reverse=True)
    return scored[:top_n] if scored else [{
        "class_name": None,
        "confidence_pct": 0,
        "reasoning": ["No candidates matched the provided input strongly enough — provide more detail (length, vessel type, or a description of the hull/mast/funnel) or a clearer image."],
    }]


def interactive():
    print("=== SVACS Naval Vessel Candidate Identifier (knowledge-based, not a vision model) ===")
    print("Provide whatever you know — leave blank and press Enter to skip any field.\n")

    length_input = input("Estimated length in meters (e.g. 160): ").strip()
    length_m = float(length_input) if length_input else None

    vessel_type = input("Vessel type if known (destroyer/frigate/corvette/carrier/submarine): ").strip() or None
    hull_color = input("Hull colour (e.g. grey): ").strip() or None
    description = input("Describe what you see (e.g. 'single funnel, angled stealth superstructure'): ").strip() or None

    results = identify_candidates(length_m, vessel_type, hull_color, description)

    print("\n--- Candidate Matches ---")
    for i, r in enumerate(results, start=1):
        print(f"{i}. {r['class_name']} — {r['confidence_pct']}% match")
        for reason in r["reasoning"]:
            print(f"     - {reason}")
        if r.get("validation_status"):
            print(f"     (data status: {r['validation_status']})")


if __name__ == "__main__":
    interactive()
