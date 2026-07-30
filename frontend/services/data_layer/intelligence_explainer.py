"""
SVACS — intelligence_explainer.py
====================================
Phase 5: Intelligence Explanation Engine

Generates human-readable deterministic explanations for why
the system classified a vessel and escalated risk.

NO LLM. NO randomness. NO probabilistic logic.
Pure rule-based explanation assembly from signal data.

Usage:
    from intelligence_explainer import explain, explain_from_replay
    text = explain(perception_event, intelligence_event)
"""

import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))

# ── Frequency band descriptions ───────────────────────────────────────────────
# Maps vessel_type → human-readable description of its frequency band
FREQ_BAND_LABELS = {
    "cargo":      "cargo propulsion band (50-200 Hz)",
    "speedboat":  "high-frequency speedboat band (500-1500 Hz)",
    "submarine":  "near-infrasonic submarine band (20-100 Hz)",
    "unknown":    "no standard vessel classification band",
}

# ── Confidence level labels ───────────────────────────────────────────────────
# Maps confidence score range → plain English label
def confidence_label(score: float) -> str:
    """Convert a 0-1 confidence score to a human-readable label."""
    if score is None:
        return "unknown confidence"
    if score >= 0.8:
        return "high confidence"
    if score >= 0.5:
        return "medium confidence"
    if score >= 0.2:
        return "low confidence"
    return "very low confidence"

# ── Anomaly reason explanations ───────────────────────────────────────────────
# Maps anomaly trigger keywords → plain English explanation
# These match the reasons produced by perception_node.py classify_vessel()
ANOMALY_REASON_MAP = {
    "multi-peak": (
        "Multiple FFT peaks detected across non-standard frequency bands, "
        "indicating a signal that does not match a single vessel propulsion profile."
    ),
    "unclear-band": (
        "Dominant frequency falls outside all known vessel classification bands "
        "(cargo: 50-200Hz, speedboat: 500-1500Hz, submarine: 20-100Hz), "
        "indicating an unrecognized acoustic signature."
    ),
    "low-snr": (
        "Signal-to-noise ratio fell below the classification threshold (SNR < 15.0), "
        "indicating the signal is buried in ocean noise and cannot be reliably classified."
    ),
}

# ── Risk level explanations ───────────────────────────────────────────────────
RISK_EXPLANATIONS = {
    "LOW":      "Signal characteristics match expected profile with high confidence. No operator action required.",
    "MEDIUM":   "Signal classified but with reduced confidence due to noise or partial band overlap. Monitor situation.",
    "HIGH":     "Signal exhibits irregular patterns or reduced confidence suggesting elevated operational risk. Increased vigilance recommended.",
    "CRITICAL": "Signal exhibits anomalous behavior or matches a high-threat profile. Immediate operator attention required.",
    "UNKNOWN":  "Risk level could not be assessed. Intelligence layer did not return a valid risk classification.",
}


def explain(
    perception_event: dict,
    intelligence_event: dict = None,
    vessel_registry: dict = None
) -> str:
    """
    Generate a human-readable deterministic explanation for one event.

    Args:
        perception_event:  output from perception_node.process_signal()
                           must contain: vessel_type, confidence_score,
                           dominant_freq_hz, anomaly_flag
        intelligence_event: output from NICAI (optional)
                           if provided, adds risk and validation sentences
        vessel_registry:   contents of vessel_registry.json (optional)
                           if provided, adds vessel profile sentence

    Returns:
        Single string — plain English explanation of the classification
    """
    # Extract fields from perception_event
    vessel_type   = perception_event.get("vessel_type", "unknown")
    confidence    = perception_event.get("confidence_score")
    freq_hz       = perception_event.get("dominant_freq_hz", 0.0)
    anomaly_flag  = perception_event.get("anomaly_flag", False)
    # anomaly_reasons is set by perception_node but may not be in the log
    anomaly_reasons = perception_event.get("anomaly_reasons", [])

    # Extract fields from intelligence_event (if provided)
    risk_level        = (intelligence_event or {}).get("risk_level", "UNKNOWN")
    validation_status = (intelligence_event or {}).get("validation_status", "UNKNOWN")
    nicai_explanation = (intelligence_event or {}).get("explanation", "")

    # Build explanation as a list of sentences
    # We'll join them at the end
    parts = []

    # ── Part 1: Classification sentence ──────────────────────────────────────
    # Explains WHAT the system found and WHERE in the frequency spectrum
    band_label  = FREQ_BAND_LABELS.get(vessel_type, f"frequency band at {freq_hz} Hz")
    conf_label  = confidence_label(confidence)

    if vessel_type not in ("unknown", None):
        parts.append(
            f"Dominant acoustic frequency of {freq_hz} Hz falls within the {band_label}. "
            f"Classification: {vessel_type.upper()} with {conf_label} "
            f"(score: {confidence:.3f})."
            if confidence is not None
            else
            f"Dominant acoustic frequency of {freq_hz} Hz falls within the {band_label}. "
            f"Classification: {vessel_type.upper()}."
        )
    else:
        parts.append(
            f"Dominant acoustic frequency of {freq_hz} Hz does not match any known "
            f"vessel classification band (cargo: 50-200Hz, speedboat: 500-1500Hz, "
            f"submarine: 20-100Hz). Vessel type could not be determined."
        )

    # ── Part 2: Anomaly explanation ───────────────────────────────────────────
    # Explains WHY the anomaly flag was set (if it was)
    if anomaly_flag:
        if anomaly_reasons:
            # Map each reason to its plain English explanation
            reason_texts = []
            for reason in anomaly_reasons:
                matched = False
                # Check if any known keyword is in this reason string
                for keyword, text in ANOMALY_REASON_MAP.items():
                    if keyword in reason.lower():
                        reason_texts.append(text)
                        matched = True
                        break
                if not matched:
                    # Unknown anomaly reason — include it verbatim
                    reason_texts.append(f"Anomaly condition detected: {reason}.")

            parts.append("Anomaly escalation triggered: " + " ".join(reason_texts))
        else:
            # anomaly_flag is True but no specific reasons available
            parts.append(
                "Anomaly flag set by detection system. "
                "Specific trigger conditions not available in this log entry."
            )

    # ── Part 3: Risk explanation ──────────────────────────────────────────────
    # Explains what the risk level means operationally
    if risk_level and risk_level != "UNKNOWN":
        risk_text = RISK_EXPLANATIONS.get(risk_level, f"Risk assessed as {risk_level}.")
        parts.append(f"Risk assessment: {risk_level}. {risk_text}")

    # ── Part 4: Validation explanation ───────────────────────────────────────
    if validation_status == "ALLOW":
        parts.append(
            "NICAI validation: ALLOW — signal accepted for downstream state propagation."
        )
    elif validation_status == "FLAG":
        parts.append(
            "NICAI validation: FLAG — signal flagged for operator review. "
            "State propagation may be affected."
        )

    # ── Part 5: NICAI explanation passthrough ─────────────────────────────────
    # Include NICAI's own explanation if it adds something new
    if nicai_explanation and nicai_explanation not in ("N/A", "", "None"):
        parts.append(f"Intelligence layer note: {nicai_explanation}")

    # ── Part 6: Vessel registry enrichment ───────────────────────────────────
    # If vessel registry is provided, add the vessel's acoustic behavior description
    if vessel_registry and vessel_type in vessel_registry.get("vessels", {}):
        reg = vessel_registry["vessels"][vessel_type]
        behavior = reg.get("expected_acoustic_behavior", "")
        snr_expected = reg.get("snr_expected_db", "N/A")
        note = reg.get("classification_note", "")
        if behavior:
            parts.append(
                f"Vessel profile ({vessel_type}): {behavior} "
                f"Expected SNR: {snr_expected} dB. {note}"
            )

    # Join all sentences into one explanation string
    return " ".join(parts)


def explain_from_replay(replay: dict, vessel_registry: dict = None) -> str:
    """
    Generate explanation directly from a replay object.
    Convenience wrapper around explain().

    Args:
        replay: output from operator_replay_engine.extract_replay_object()
        vessel_registry: optional vessel registry dict

    Returns:
        Plain English explanation string
    """
    perception_event  = replay["stages"].get("perception", {})
    intelligence_event = replay["stages"].get("intelligence", {})
    return explain(perception_event, intelligence_event, vessel_registry)


def explain_batch(pipeline_results: list, vessel_registry: dict = None) -> list:
    """
    Generate explanations for a batch of pipeline results.
    Used when processing multiple chunks at once.

    Args:
        pipeline_results: list of result dicts from pipeline_connector.run_full_pipeline()
        vessel_registry: optional vessel registry dict

    Returns:
        List of dicts with trace_id, vessel_type, explanation
    """
    explanations = []
    for result in pipeline_results:
        pe = result.get("perception_event", {})
        ie = result.get("intelligence_event", {})
        text = explain(pe, ie, vessel_registry)
        explanations.append({
            "trace_id":    result.get("trace_id"),
            "vessel_type": pe.get("vessel_type"),
            "risk_level":  ie.get("risk_level"),
            "explanation": text,
        })
    return explanations


if __name__ == "__main__":
    # Load vessel registry for enriched explanations
    registry_path = os.path.join(BASE, "vessel_registry.json")
    registry = None
    if os.path.exists(registry_path):
        with open(registry_path) as f:
            registry = json.load(f)
        print(f"[INFO] Vessel registry loaded: {len(registry['vessels'])} vessel types\n")

    # Test cases — one per scenario type
    test_cases = [
        {
            "name": "Clean cargo detection",
            "perception": {
                "trace_id": "test-001",
                "vessel_type": "cargo",
                "confidence_score": 1.0,
                "dominant_freq_hz": 125.0,
                "anomaly_flag": False,
                "anomaly_reasons": []
            },
            "intelligence": {
                "risk_level": "LOW",
                "validation_status": "ALLOW",
                "explanation": "Normal condition"
            }
        },
        {
            "name": "Submarine under noise (classified as unknown)",
            "perception": {
                "trace_id": "test-002",
                "vessel_type": "unknown",
                "confidence_score": 0.358,
                "dominant_freq_hz": 33.0,
                "anomaly_flag": True,
                "anomaly_reasons": ["unclear-band (freq=33.0Hz matches no vessel rule)"]
            },
            "intelligence": {
                "risk_level": "CRITICAL",
                "validation_status": "ALLOW",
                "explanation": "Anomalous acoustic pattern detected — classified as critical risk"
            }
        },
        {
            "name": "Anomaly — multi-peak",
            "perception": {
                "trace_id": "test-003",
                "vessel_type": "unknown",
                "confidence_score": 0.021,
                "dominant_freq_hz": 396.0,
                "anomaly_flag": True,
                "anomaly_reasons": [
                    "multi-peak (11 components above threshold)",
                    "unclear-band (freq=396.0Hz matches no vessel rule)",
                    "low-snr (snr=5.24 < threshold=15.0)"
                ]
            },
            "intelligence": {
                "risk_level": "CRITICAL",
                "validation_status": "ALLOW",
                "explanation": "Anomalous acoustic pattern detected"
            }
        },
        {
            "name": "Low confidence — noise buried",
            "perception": {
                "trace_id": "test-004",
                "vessel_type": "unknown",
                "confidence_score": 0.025,
                "dominant_freq_hz": 274.0,
                "anomaly_flag": True,
                "anomaly_reasons": [
                    "unclear-band (freq=274.0Hz matches no vessel rule)",
                    "low-snr (snr=7.53 < threshold=15.0)"
                ]
            },
            "intelligence": {
                "risk_level": "CRITICAL",
                "validation_status": "ALLOW",
                "explanation": "Low confidence signal"
            }
        },
    ]

    print("=" * 68)
    print("  INTELLIGENCE EXPLAINER — SELF TEST")
    print("=" * 68)

    for case in test_cases:
        print(f"\n  CASE: {case['name']}")
        print("  " + "-" * 60)
        explanation = explain(
            case["perception"],
            case["intelligence"],
            registry
        )
        # Word-wrap at 70 chars for readability
        words = explanation.split()
        line  = "  "
        for word in words:
            if len(line) + len(word) > 70:
                print(line)
                line = "  " + word + " "
            else:
                line += word + " "
        if line.strip():
            print(line)

    print("\n" + "=" * 68)