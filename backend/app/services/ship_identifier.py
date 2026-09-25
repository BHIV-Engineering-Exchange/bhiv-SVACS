"""
ship_identifier.py — Identifies the specific named ship within a vessel
class by reading the pennant number off the hull via OCR, and matching
it against the curated ship registry.

This is NOT a visual classifier for individual ships. Sister ships within
a class are usually visually near-identical (same hull, same design) —
there is no reliable visual feature to tell them apart. Pennant numbers
(e.g. D63, F47, S21) are the actual real-world method used to
distinguish sister ships, so that is what this module does, using the
OCR pipeline that already exists in this system.

If no pennant number is legible or matched, this returns the class's
full ship roster with NO confidence percentages attached — a roster is
useful information (here's who it could be), but assigning percentages
across it would imply evidence that doesn't exist.
"""

import json
import os
import re

SHIP_REGISTRY_PATH = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "maritime_knowledge", "ship_registry.json"
))

# Pennant numbers follow a letter-prefix + digits pattern, e.g. D63, F47,
# S21, S2, R11 — we look for this pattern anywhere in the combined OCR text.
PENNANT_PATTERN = re.compile(r"\b([A-Z])[\s\-]?(\d{1,3})\b")


def load_ship_registry():
    with open(SHIP_REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _normalize_pennant(letter, digits):
    return f"{letter.upper()}{digits}"


def extract_pennant_candidates(ocr_text: str):
    """Returns a list of pennant-number-like strings found in the OCR text."""
    if not ocr_text:
        return []
    return [
        _normalize_pennant(m.group(1), m.group(2))
        for m in PENNANT_PATTERN.finditer(ocr_text.upper())
    ]


def identify_ship(vessel_class: str, ocr_text: str = None):
    """
    Given a visually-classified vessel_class and combined OCR text read
    from the hull, attempt to identify the specific named ship by
    matching a pennant number.

    Returns one of three shapes:
      - Matched:      {"matched": True, "ship_name": ..., "pennant": ..., "method": "ocr_pennant_match"}
      - No match:      {"matched": False, "roster": [{"name", "pennant"}, ...], "method": "class_roster_fallback"}
      - Not applicable (class has no registry entry, e.g. a civilian class):
                       {"matched": False, "roster": [], "method": "not_applicable"}
    """
    registry = load_ship_registry()
    roster = registry.get(vessel_class)

    if not roster:
        return {"matched": False, "roster": [], "method": "not_applicable"}

    for pennant in extract_pennant_candidates(ocr_text):
        for ship in roster:
            if ship["pennant"].upper() == pennant:
                return {
                    "matched": True,
                    "ship_name": ship["name"],
                    "pennant": ship["pennant"],
                    "method": "ocr_pennant_match",
                }

    return {
        "matched": False,
        "roster": roster,
        "method": "class_roster_fallback",
    }
