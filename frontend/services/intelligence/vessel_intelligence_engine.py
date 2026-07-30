"""
SVACS Vessel Intelligence Engine
==================================
Deterministic, rule-based vessel classification engine.
No ML. No randomness. Same input always produces same output.

Accepts structured intelligence from Samachar (image/AIS/manual input)
and produces vessel identification with confidence scoring,
explainable reasoning, and evidence chain.

Updated: OCR-based vessel name/operator lookup added.
         Mumbai port vessel registry added.
"""

import uuid
from datetime import datetime, timezone


# ── Maritime Knowledge Registry ───────────────────────────────────────────────
MARITIME_KNOWLEDGE = {
    "cargo": {
        "length_range_m":   (100, 400),
        "beam_range_m":     (15, 60),
        "speed_range_knots": (8, 25),
        "superstructure":   ["aft_bridge", "cargo_holds", "cranes"],
        "risk_profile":     "LOW",
        "description":      "Large commercial cargo vessel with aft bridge and cargo holds.",
    },
    "tanker": {
        "length_range_m":   (150, 450),
        "beam_range_m":     (20, 70),
        "speed_range_knots": (10, 20),
        "superstructure":   ["aft_bridge", "pipeline_deck", "no_cranes"],
        "risk_profile":     "LOW",
        "description":      "Tanker vessel with pipeline deck and aft superstructure.",
    },
    "patrol": {
        "length_range_m":   (30, 120),
        "beam_range_m":     (5, 15),
        "speed_range_knots": (20, 45),
        "superstructure":   ["mid_bridge", "antenna_array", "gun_mount"],
        "risk_profile":     "MEDIUM",
        "description":      "Naval or coast guard patrol vessel with high speed capability.",
    },
    "fishing": {
        "length_range_m":   (10, 50),
        "beam_range_m":     (3, 12),
        "speed_range_knots": (5, 15),
        "superstructure":   ["nets", "outriggers", "small_bridge"],
        "risk_profile":     "LOW",
        "description":      "Fishing vessel with nets or outriggers.",
    },
    "ferry": {
        "length_range_m":   (30, 200),
        "beam_range_m":     (8, 30),
        "speed_range_knots": (10, 30),
        "superstructure":   ["passenger_decks", "ramp", "wide_beam"],
        "risk_profile":     "LOW",
        "description":      "Passenger ferry with multiple decks and boarding ramp.",
    },
    "tug": {
        "length_range_m":   (20, 50),
        "beam_range_m":     (7, 15),
        "speed_range_knots": (10, 20),
        "superstructure":   ["large_engine", "tow_hook", "stocky_hull"],
        "risk_profile":     "LOW",
        "description":      "Tug boat with large engine and tow hook for port assistance.",
    },
    "submarine": {
        "length_range_m":   (50, 200),
        "beam_range_m":     (5, 15),
        "speed_range_knots": (5, 25),
        "superstructure":   ["conning_tower", "no_deck_structures"],
        "risk_profile":     "CRITICAL",
        "description":      "Submarine — conning tower visible when surfaced.",
    },
    "unknown": {
        "length_range_m":   (0, 999),
        "beam_range_m":     (0, 999),
        "speed_range_knots": (0, 50),
        "superstructure":   [],
        "risk_profile":     "HIGH",
        "description":      "Vessel class could not be determined from available evidence.",
    },
}


# ── OCR Vessel Registry ───────────────────────────────────────────────────────
# Maps detected OCR text → vessel operator/name metadata
# Covers global operators + Mumbai port specific vessels
OCR_VESSEL_REGISTRY = {
    # Global operators
    "balearia":        {"operator": "Baleària",        "class": "ferry",     "flag": "ES", "risk": "LOW"},
    "maersk":          {"operator": "Maersk",           "class": "cargo",     "flag": "DK", "risk": "LOW"},
    "msc":             {"operator": "MSC",              "class": "cargo",     "flag": "CH", "risk": "LOW"},
    "evergreen":       {"operator": "Evergreen",        "class": "cargo",     "flag": "TW", "risk": "LOW"},
    "cosco":           {"operator": "COSCO",            "class": "cargo",     "flag": "CN", "risk": "LOW"},
    "hapag":           {"operator": "Hapag-Lloyd",      "class": "cargo",     "flag": "DE", "risk": "LOW"},
    "cma cgm":         {"operator": "CMA CGM",          "class": "cargo",     "flag": "FR", "risk": "LOW"},
    "carnival":        {"operator": "Carnival",         "class": "passenger", "flag": "US", "risk": "LOW"},
    "norwegian":       {"operator": "Norwegian",        "class": "passenger", "flag": "BS", "risk": "LOW"},
    "royal caribbean": {"operator": "Royal Caribbean",  "class": "passenger", "flag": "BS", "risk": "LOW"},

    # Mumbai port specific vessels
    "ajanta":          {"operator": "MMRDA/MSRDC",     "class": "ferry",     "flag": "IN", "risk": "LOW"},
    "elephanta":       {"operator": "MTDC",             "class": "ferry",     "flag": "IN", "risk": "LOW"},
    "gateway":         {"operator": "Mumbai Port",      "class": "ferry",     "flag": "IN", "risk": "LOW"},
    "mandwa":          {"operator": "Alibaug Ferry",    "class": "ferry",     "flag": "IN", "risk": "LOW"},
    "ro-ro":           {"operator": "RoRo Ferry",       "class": "ferry",     "flag": "IN", "risk": "LOW"},
    "roro":            {"operator": "RoRo Ferry",       "class": "ferry",     "flag": "IN", "risk": "LOW"},
    "alibaug":         {"operator": "Alibaug Ferry",    "class": "ferry",     "flag": "IN", "risk": "LOW"},
    "mazagon":         {"operator": "Mazagon Dock",     "class": "cargo",     "flag": "IN", "risk": "LOW"},
    "nhava":           {"operator": "JNPT",             "class": "cargo",     "flag": "IN", "risk": "LOW"},
    "jnpt":            {"operator": "JNPT",             "class": "cargo",     "flag": "IN", "risk": "LOW"},
    "coast guard":     {"operator": "Indian Coast Guard","class": "patrol",   "flag": "IN", "risk": "MEDIUM"},
    "navy":            {"operator": "Indian Navy",      "class": "patrol",    "flag": "IN", "risk": "HIGH"},
    "ins ":            {"operator": "Indian Navy",      "class": "patrol",    "flag": "IN", "risk": "HIGH"},
    "icgs":            {"operator": "Indian Coast Guard","class": "patrol",   "flag": "IN", "risk": "MEDIUM"},

    # IMO / registration
    "imo":             {"operator": "IMO Registered",   "class": "unknown",   "flag": "UN", "risk": "MEDIUM"},
}


def match_ocr_to_registry(ocr_results: list) -> dict:
    """
    Match OCR text results against known vessel operator registry.

    Args:
        ocr_results: list of OCR result dicts from Vision Runtime
                     each has: text, confidence, bounding_box

    Returns:
        dict with matched operator info, or partial info if no match
    """
    if not ocr_results:
        return {}

    # Only use high confidence OCR results (above 0.5)
    high_conf = [r for r in ocr_results if r.get("confidence", 0) >= 0.5]

    for ocr in high_conf:
        raw  = ocr.get("text", "")
        text = raw.lower().strip().strip('"').strip("'")
        for key, info in OCR_VESSEL_REGISTRY.items():
            if key in text or text in key:
                return {
                    "matched_operator": info["operator"],
                    "matched_class":    info["class"],
                    "matched_flag":     info["flag"],
                    "ocr_text":         raw,
                    "ocr_confidence":   ocr.get("confidence"),
                    "risk_override":    info["risk"],
                }

    # No registry match — return best OCR text for evidence
    if high_conf:
        best = max(high_conf, key=lambda x: x.get("confidence", 0))
        return {
            "matched_operator": None,
            "ocr_text":         best.get("text"),
            "ocr_confidence":   best.get("confidence"),
        }

    return {}


# ── Source type confidence weights ────────────────────────────────────────────
SOURCE_WEIGHTS = {
    "image":  0.70,
    "ais":    0.90,
    "manual": 0.50,
    "acoustic": 0.75,
}

# ── Risk level rules ──────────────────────────────────────────────────────────
RISK_RULES = {
    "submarine": "CRITICAL",
    "patrol":    "MEDIUM",
    "unknown":   "HIGH",
    "cargo":     "LOW",
    "tanker":    "LOW",
    "fishing":   "LOW",
    "ferry":     "LOW",
    "tug":       "LOW",
    "passenger": "LOW",
}


def classify_by_dimensions(length_m, beam_m) -> str:
    """Classify vessel class from physical dimensions."""
    if length_m is None:
        return None
    if length_m > 150:
        return "cargo" if beam_m and beam_m > 25 else "tanker"
    if 30 <= length_m <= 120 and beam_m and beam_m < 15:
        return "patrol"
    if 30 <= length_m <= 200 and beam_m and beam_m >= 8:
        return "ferry"
    if 20 <= length_m <= 50:
        return "tug"
    if length_m < 50:
        return "fishing"
    return None


def classify_by_speed(speed_knots) -> str:
    """Classify vessel class from AIS speed."""
    if speed_knots is None:
        return None
    if speed_knots > 30:
        return "patrol"
    if 8 <= speed_knots <= 25:
        return "cargo"
    if 10 <= speed_knots <= 30:
        return "ferry"
    if speed_knots < 8:
        return "fishing"
    return None


def classify_by_features(visual_features: list) -> str:
    """Classify vessel class from visual features."""
    if not visual_features:
        return None
    f = [x.lower() for x in visual_features]
    if any(x in f for x in ["conning_tower", "periscope"]):
        return "submarine"
    if any(x in f for x in ["gun_mount", "antenna_array", "radar_array"]):
        return "patrol"
    if any(x in f for x in ["cargo_holds", "cranes", "aft_bridge"]):
        return "cargo"
    if any(x in f for x in ["pipeline_deck", "manifold"]):
        return "tanker"
    if any(x in f for x in ["passenger_decks", "ramp", "car_deck"]):
        return "ferry"
    if any(x in f for x in ["nets", "outriggers", "fish_hold"]):
        return "fishing"
    if any(x in f for x in ["tow_hook", "stocky_hull"]):
        return "tug"
    return None


def compute_confidence(
    base_confidence: float,
    source_type: str,
    feature_count: int,
    rule_matches: int,
    ocr_match: bool = False,
) -> float:
    """
    Compute final confidence score.

    Blends: source weight + feature completeness + rule match strength + OCR boost.
    """
    source_weight      = SOURCE_WEIGHTS.get(source_type, 0.5)
    feature_completeness = min(1.0, feature_count / 5.0)
    rule_strength      = min(1.0, rule_matches / 3.0)
    ocr_boost          = 0.15 if ocr_match else 0.0

    raw = (
        base_confidence * 0.35
        + source_weight  * 0.25
        + feature_completeness * 0.15
        + rule_strength  * 0.15
        + ocr_boost      * 0.10
    )
    return round(min(1.0, max(0.0, raw)), 4)


def process_intelligence(intelligence_input: dict) -> dict:
    """
    Main intelligence processing function.

    Args:
        intelligence_input: structured intelligence from Samachar containing:
            trace_id, source_type, vessel_class, confidence_score,
            vision_confidence, visual_features, dimensions_estimate,
            ais_data, ocr_results, timestamp_utc

    Returns:
        Complete intelligence result with vessel_class, confidence_score,
        risk_level, validation_status, explanation, evidence_chain,
        vessel_candidates, knowledge_references, operator_action_required
    """
    # ── Extract input fields ──────────────────────────────────────────────────
    trace_id         = intelligence_input.get("trace_id", str(uuid.uuid4()))
    source_type      = intelligence_input.get("source_type", "manual")
    vessel_class     = intelligence_input.get("vessel_class", "unknown")
    base_confidence  = float(intelligence_input.get("confidence_score") or 0.0)
    vision_conf      = float(intelligence_input.get("vision_confidence") or 0.0)
    visual_features  = intelligence_input.get("visual_features", []) or []
    dimensions       = intelligence_input.get("dimensions_estimate", {}) or {}
    ais_data         = intelligence_input.get("ais_data", {}) or {}
    ocr_results      = intelligence_input.get("ocr_results", []) or []
    timestamp_utc    = intelligence_input.get("timestamp_utc",
                       datetime.now(timezone.utc).isoformat())

    length_m    = dimensions.get("length_m")
    beam_m      = dimensions.get("beam_m")
    speed_knots = ais_data.get("speed_knots")
    mmsi        = ais_data.get("mmsi")

    evidence_chain  = []
    knowledge_refs  = []
    rule_matches    = 0

    # ── OCR-based vessel name/operator lookup ─────────────────────────────────
    ocr_match    = match_ocr_to_registry(ocr_results)
    ocr_operator = ocr_match.get("matched_operator")
    ocr_class    = ocr_match.get("matched_class")
    ocr_text     = ocr_match.get("ocr_text")
    ocr_conf     = ocr_match.get("ocr_confidence", 0)

    if ocr_operator and ocr_class and ocr_class != "unknown":
        vessel_class  = ocr_class
        base_confidence = min(1.0, base_confidence + 0.20)
        rule_matches += 1
        evidence_chain.append(
            f"OCR detected operator: {ocr_operator} "
            f"(text='{ocr_text}', confidence={ocr_conf:.2f})"
        )
        knowledge_refs.append(f"OCR Registry: {ocr_operator}")
    elif ocr_text:
        evidence_chain.append(
            f"OCR text detected: '{ocr_text}' "
            f"(confidence={ocr_conf:.2f}) — no registry match"
        )

    # ── Vision confidence ─────────────────────────────────────────────────────
    if vision_conf > 0:
        effective_confidence = max(base_confidence, vision_conf)
        evidence_chain.append(
            f"Vision Runtime detection confidence: {vision_conf:.2f}"
        )
    else:
        effective_confidence = base_confidence

    # ── Rule-based classification ─────────────────────────────────────────────
    candidates = {}

    # Rule 1: Samachar vessel_class (if not unknown)
    if vessel_class and vessel_class != "unknown":
        candidates[vessel_class] = candidates.get(vessel_class, 0) + 0.4
        rule_matches += 1
        evidence_chain.append(f"Samachar classified as: {vessel_class}")

    # Rule 2: Dimension-based classification
    dim_class = classify_by_dimensions(length_m, beam_m)
    if dim_class:
        candidates[dim_class] = candidates.get(dim_class, 0) + 0.3
        rule_matches += 1
        evidence_chain.append(
            f"Dimension match: length={length_m}m, beam={beam_m}m → {dim_class}"
        )

    # Rule 3: Speed-based classification
    speed_class = classify_by_speed(speed_knots)
    if speed_class:
        candidates[speed_class] = candidates.get(speed_class, 0) + 0.2
        rule_matches += 1
        evidence_chain.append(
            f"Speed match: {speed_knots} knots → {speed_class}"
        )

    # Rule 4: Visual feature classification
    feature_class = classify_by_features(visual_features)
    if feature_class:
        candidates[feature_class] = candidates.get(feature_class, 0) + 0.3
        rule_matches += 1
        evidence_chain.append(
            f"Visual features match: {visual_features} → {feature_class}"
        )

    # Rule 5: MMSI lookup
    if mmsi:
        evidence_chain.append(f"AIS MMSI provided: {mmsi}")
        knowledge_refs.append(f"AIS: MMSI {mmsi}")
        rule_matches += 1

    # ── Determine final vessel class ──────────────────────────────────────────
    if candidates:
        final_class = max(candidates, key=candidates.get)
    else:
        final_class = vessel_class if vessel_class != "unknown" else "unknown"

    # ── Compute confidence ────────────────────────────────────────────────────
    confidence_score = compute_confidence(
        base_confidence    = effective_confidence,
        source_type        = source_type,
        feature_count      = len(visual_features),
        rule_matches       = rule_matches,
        ocr_match          = bool(ocr_operator),
    )

    # ── Build ranked candidate list ───────────────────────────────────────────
    vessel_candidates = sorted(
        [
            {
                "class":      cls,
                "confidence": round(min(1.0, score * confidence_score * 2), 4),
                "evidence":   [e for e in evidence_chain if cls in e],
            }
            for cls, score in candidates.items()
        ],
        key=lambda x: x["confidence"],
        reverse=True,
    )[:3]

    # ── Determine risk level ──────────────────────────────────────────────────
    risk_level = RISK_RULES.get(final_class, "HIGH")
    if ocr_match.get("risk_override"):
        risk_level = ocr_match["risk_override"]
    if confidence_score < 0.3:
        risk_level = "HIGH"
    if final_class == "submarine":
        risk_level = "CRITICAL"

    # ── Determine validation status ───────────────────────────────────────────
    if confidence_score >= 0.6 and risk_level in ("LOW", "MEDIUM"):
        validation_status = "ALLOW"
    elif confidence_score >= 0.3 or risk_level == "HIGH":
        validation_status = "FLAG"
    else:
        validation_status = "DENY"

    if risk_level == "CRITICAL":
        validation_status = "DENY"

    # ── Operator action required ──────────────────────────────────────────────
    operator_action = validation_status in ("FLAG", "DENY") or confidence_score < 0.5

    # ── Add knowledge references ──────────────────────────────────────────────
    if final_class in MARITIME_KNOWLEDGE:
        knowledge_refs.append(f"Maritime Knowledge Registry: {final_class}")
        evidence_chain.append(
            f"Registry profile: {MARITIME_KNOWLEDGE[final_class]['description']}"
        )

    # ── Build explanation ─────────────────────────────────────────────────────
    explanation = (
        f"Vessel classified as {final_class.upper()}"
        + (f" — OCR identified operator: {ocr_operator}" if ocr_operator else "")
        + (f" — OCR text detected: '{ocr_text}'" if ocr_text and not ocr_operator else "")
        + f" with confidence {confidence_score:.2f}."
        + f" Risk: {risk_level}."
        + (f" Operator action required." if operator_action else " No operator action required.")
    )

    if confidence_score < 0.3:
        explanation += (
            " Confidence below threshold — vessel could not be reliably identified."
        )

    return {
        "trace_id":               trace_id,
        "vessel_class":           final_class,
        "vessel_candidates":      vessel_candidates,
        "confidence_score":       confidence_score,
        "risk_level":             risk_level,
        "validation_status":      validation_status,
        "explanation":            explanation,
        "evidence_chain":         evidence_chain,
        "knowledge_references":   knowledge_refs,
        "operator_action_required": operator_action,
        "ocr_operator":           ocr_operator,
        "ocr_text":               ocr_text,
        "timestamp_utc":          timestamp_utc,
    }


# ── Self-test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import json

    test_cases = [
        {
            "name": "High confidence cargo via AIS",
            "input": {
                "trace_id":       "test-001",
                "source_type":    "ais",
                "vessel_class":   "cargo",
                "confidence_score": 0.92,
                "vision_confidence": 0.0,
                "visual_features": ["aft_bridge", "cargo_holds"],
                "dimensions_estimate": {"length_m": 180, "beam_m": 28},
                "ais_data":       {"mmsi": "368084090", "speed_knots": 12.4},
                "ocr_results":    [],
            }
        },
        {
            "name": "Balearia ferry via OCR",
            "input": {
                "trace_id":       "test-002",
                "source_type":    "image",
                "vessel_class":   "unknown",
                "confidence_score": 0.0,
                "vision_confidence": 0.55,
                "visual_features": [],
                "dimensions_estimate": {"length_m": None, "beam_m": None},
                "ais_data":       {"mmsi": None, "speed_knots": None},
                "ocr_results":    [
                    {"text": "BALEARIA", "confidence": 0.945, "bounding_box": {}},
                    {"text": "BobNoah",  "confidence": 0.919, "bounding_box": {}},
                ],
            }
        },
        {
            "name": "Mumbai Elephanta ferry via OCR",
            "input": {
                "trace_id":       "test-003",
                "source_type":    "image",
                "vessel_class":   "unknown",
                "confidence_score": 0.0,
                "vision_confidence": 0.62,
                "visual_features": ["passenger_decks", "ramp"],
                "dimensions_estimate": {"length_m": 45, "beam_m": 10},
                "ais_data":       {"mmsi": None, "speed_knots": 12},
                "ocr_results":    [
                    {"text": "ELEPHANTA", "confidence": 0.88, "bounding_box": {}},
                ],
            }
        },
        {
            "name": "Unknown low confidence",
            "input": {
                "trace_id":       "test-004",
                "source_type":    "image",
                "vessel_class":   "unknown",
                "confidence_score": 0.15,
                "vision_confidence": 0.22,
                "visual_features": [],
                "dimensions_estimate": {"length_m": None, "beam_m": None},
                "ais_data":       {"mmsi": None, "speed_knots": None},
                "ocr_results":    [],
            }
        },
        {
            "name": "Indian Navy patrol vessel",
            "input": {
                "trace_id":       "test-005",
                "source_type":    "image",
                "vessel_class":   "patrol",
                "confidence_score": 0.78,
                "vision_confidence": 0.81,
                "visual_features": ["gun_mount", "antenna_array"],
                "dimensions_estimate": {"length_m": 90, "beam_m": 12},
                "ais_data":       {"mmsi": None, "speed_knots": 28},
                "ocr_results":    [
                    {"text": "INS Vikrant", "confidence": 0.91, "bounding_box": {}},
                ],
            }
        },
    ]

    print("=" * 68)
    print("  VESSEL INTELLIGENCE ENGINE — SELF TEST")
    print("=" * 68)

    for case in test_cases:
        result = process_intelligence(case["input"])
        print(f"\n  CASE: {case['name']}")
        print("  " + "-" * 60)
        print(f"  vessel_class    : {result['vessel_class']}")
        print(f"  confidence      : {result['confidence_score']}")
        print(f"  risk_level      : {result['risk_level']}")
        print(f"  validation      : {result['validation_status']}")
        print(f"  ocr_operator    : {result['ocr_operator']}")
        print(f"  ocr_text        : {result['ocr_text']}")
        print(f"  explanation     : {result['explanation'][:90]}...")
        print(f"  evidence_chain  : {result['evidence_chain'][:2]}")

    print("\n" + "=" * 68)