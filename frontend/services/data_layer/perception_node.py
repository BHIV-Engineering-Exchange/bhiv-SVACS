"""
SVACS — Perception Node
========================
Author  : Nupur Gavane
Role    : Signal + Perception — interprets signal_chunk → perception_event
Task    : Make the system UNDERSTAND signals (Signal → Meaning)

Rules (non-negotiable):
  - NO ML
  - NO uncontrolled randomness
  - NO schema contract modifications
  - Deterministic, explainable, traceable output
  - NO silent failures
  - trace_id NEVER modified or regenerated

Pipeline position:
  signal_chunk (from HybridSignalBuilder / mock_server)
      → perception_node.process_signal()
          → perception_event (consumed by NICAI / State Engine)
"""

import numpy as np
import logging

# ─────────────────────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [perception_node] %(message)s"
)
logger = logging.getLogger("perception_node")

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# Calibrated from real HybridSignalBuilder FFT output analysis.
# DO NOT change without re-running signal analysis.
# ─────────────────────────────────────────────────────────────────────────────

# Vessel frequency bands (Hz)
CARGO_FREQ_MIN      = 50
CARGO_FREQ_MAX      = 200
FERRY_FREQ_MIN      = 201
FERRY_FREQ_MAX      = 300
CRUISE_FREQ_MIN     = 301
CRUISE_FREQ_MAX     = 400
RORO_FREQ_MIN       = 401
RORO_FREQ_MAX       = 499
PASSENGER_FREQ_MIN  = 1501
PASSENGER_FREQ_MAX  = 1600
SPEEDBOAT_FREQ_MIN  = 500
SPEEDBOAT_FREQ_MAX  = 1500
SUBMARINE_FREQ_MIN  = 20
SUBMARINE_FREQ_MAX  = 100

# Energy threshold separates submarine from cargo in the 50-100 Hz overlap zone.
# Submarine energy: ~600k–900k | Cargo energy: ~1.9M–2.2M
SUBMARINE_MAX_ENERGY = 1_200_000

# SNR thresholds
SNR_LOW_THRESHOLD       = 15.0   # below this → low_snr anomaly flag
SNR_CONFIDENCE_SCALE    = 250.0  # SNR / this = raw confidence (then capped at 1.0)

# Anomaly detection
MULTI_PEAK_FRACTION = 0.5    # peaks above (this × peak_amplitude) are counted
MULTI_PEAK_MIN      = 3      # if count > this → multi-peak anomaly

# Required fields in incoming signal_chunk
REQUIRED_FIELDS = ["trace_id", "samples", "sample_rate"]


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 1 — SCHEMA VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

def validate_signal_chunk(signal_chunk: dict) -> tuple:
    """
    Validates all required fields in the incoming signal_chunk.

    Returns:
        (True,  "ok")           — valid, proceed
        (False, reason_string)  — invalid, return structured error immediately
    """
    if not isinstance(signal_chunk, dict):
        return False, "signal_chunk must be a dict"

    for field in REQUIRED_FIELDS:
        if field not in signal_chunk:
            return False, f"Missing required field: '{field}'"

    if not signal_chunk.get("trace_id"):
        return False, "trace_id must not be empty or null"

    samples = signal_chunk["samples"]
    if not isinstance(samples, (list, np.ndarray)):
        return False, "samples must be a list or array"
    if len(samples) == 0:
        return False, "samples must not be empty"

    sr = signal_chunk["sample_rate"]
    if not isinstance(sr, (int, float)) or sr <= 0:
        return False, "sample_rate must be a positive number"

    return True, "ok"


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 2 — FFT + FEATURE EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

def extract_features(signal_chunk: dict) -> dict:
    """
    Runs numpy FFT on signal samples.
    Extracts: dominant_freq_hz, peak_amplitude, total_energy, snr, noise_floor.

    All outputs are logged with trace_id for full traceability.
    """
    samples     = np.array(signal_chunk["samples"], dtype=np.float64)
    sample_rate = float(signal_chunk["sample_rate"])
    trace_id    = signal_chunk["trace_id"]

    # Run FFT — rfft for real-valued signals (more efficient, same result)
    fft_result = np.fft.rfft(samples)
    freqs      = np.fft.rfftfreq(len(samples), d=1.0 / sample_rate)
    magnitudes = np.abs(fft_result)

    # Feature extraction
    dominant_idx   = int(np.argmax(magnitudes))
    dominant_freq  = float(freqs[dominant_idx])
    peak_amplitude = float(magnitudes[dominant_idx])
    total_energy   = float(np.sum(magnitudes ** 2))
    noise_floor    = float(np.mean(magnitudes))
    snr            = peak_amplitude / noise_floor if noise_floor > 0 else 0.0

    logger.info(
        f"[FFT] trace_id={trace_id} | "
        f"dominant_freq_hz={dominant_freq:.2f} | "
        f"peak_amplitude={peak_amplitude:.2f} | "
        f"total_energy={total_energy:.0f} | "
        f"snr={snr:.2f}"
    )

    return {
        "trace_id":         trace_id,
        "dominant_freq_hz": dominant_freq,
        "peak_amplitude":   peak_amplitude,
        "total_energy":     total_energy,
        "noise_floor":      noise_floor,
        "snr":              snr,
        "magnitudes":       magnitudes,   # kept for anomaly detection below
        "freqs":            freqs,
    }


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 3 — CLASSIFICATION + CONFIDENCE + ANOMALY DETECTION
# ─────────────────────────────────────────────────────────────────────────────

def classify_vessel(features: dict) -> dict:
    """
    Deterministic rule-based vessel classification.
    Uses dominant frequency + energy to identify vessel type.

    Classification rules (in priority order):
      1. submarine : 20–100 Hz AND energy < SUBMARINE_MAX_ENERGY
         (energy check separates sub from cargo in 50–100 Hz overlap)
      2. cargo     : 50–200 Hz
      3. speedboat : 500–1500 Hz
      4. unknown   : no rule matched

    Confidence score:
      - Derived from SNR (peak clarity vs noise floor)
      - Normalized to 0–1 range

    Anomaly detection (three independent checks):
      1. multi-peak    : multiple strong frequency components
      2. unclear-band  : vessel_type = unknown (no rule matched)
      3. low-snr       : signal buried in noise
    """
    trace_id    = features["trace_id"]
    freq        = features["dominant_freq_hz"]
    total_energy= features["total_energy"]
    peak        = features["peak_amplitude"]
    snr         = features["snr"]
    magnitudes  = features["magnitudes"]

    # ── Classification (deterministic, priority order) ──────────────────────
    # Submarine check FIRST — it overlaps with cargo in the 50-100 Hz band.
    # The energy threshold is the only reliable discriminator in that zone.
    if SUBMARINE_FREQ_MIN <= freq <= SUBMARINE_FREQ_MAX and total_energy < SUBMARINE_MAX_ENERGY:
        vessel_type = "submarine"
    elif CARGO_FREQ_MIN <= freq <= CARGO_FREQ_MAX:
        vessel_type = "cargo"
    elif FERRY_FREQ_MIN <= freq <= FERRY_FREQ_MAX:
        vessel_type = "ferry"
    elif CRUISE_FREQ_MIN <= freq <= CRUISE_FREQ_MAX:
        vessel_type = "cruise"
    elif RORO_FREQ_MIN <= freq <= RORO_FREQ_MAX:
        vessel_type = "roro"
    elif PASSENGER_FREQ_MIN <= freq <= PASSENGER_FREQ_MAX:
        vessel_type = "passenger"
    elif SPEEDBOAT_FREQ_MIN <= freq <= SPEEDBOAT_FREQ_MAX:
        vessel_type = "speedboat"
    else:
        vessel_type = "unknown"

    # ── Confidence Score ─────────────────────────────────────────────────────
    # SNR / scale factor, capped at 1.0
    # Higher SNR = cleaner peak = higher confidence
    confidence_score = float(min(snr / SNR_CONFIDENCE_SCALE, 1.0))

    # ── Anomaly Detection ────────────────────────────────────────────────────
    anomaly_flag    = False
    anomaly_reasons = []

    # 1. Multi-peak: count FFT components above 50% of peak magnitude
    peaks_above = int(np.sum(magnitudes > (MULTI_PEAK_FRACTION * peak)))
    if peaks_above > MULTI_PEAK_MIN:
        anomaly_flag = True
        anomaly_reasons.append(f"multi-peak ({peaks_above} components above threshold)")

    # 2. Unclear band: frequency doesn't match any vessel rule
    if vessel_type == "unknown":
        anomaly_flag = True
        anomaly_reasons.append(f"unclear-band (freq={freq:.1f}Hz matches no vessel rule)")

    # 3. Low SNR: signal buried in noise
    if snr < SNR_LOW_THRESHOLD:
        anomaly_flag = True
        anomaly_reasons.append(f"low-snr (snr={snr:.2f} < threshold={SNR_LOW_THRESHOLD})")

    logger.info(
        f"[CLASS] trace_id={trace_id} | "
        f"vessel_type={vessel_type} | "
        f"confidence_score={confidence_score:.4f} | "
        f"anomaly_flag={anomaly_flag} | "
        f"reasons={anomaly_reasons}"
    )

    return {
        "vessel_type":      vessel_type,
        "confidence_score": round(confidence_score, 4),
        "anomaly_flag":     anomaly_flag,
        "anomaly_reasons":  anomaly_reasons,
    }


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 4 — OUTPUT CONTRACT: perception_event
# ─────────────────────────────────────────────────────────────────────────────

def build_perception_event(signal_chunk: dict, features: dict, classification: dict) -> dict:
    """
    Assembles the final perception_event.

    STRICT CONTRACT:
      - trace_id       : copied unchanged from signal_chunk — NEVER regenerated
      - vessel_type    : from classification
      - confidence_score : from classification (0.0–1.0 float)
      - dominant_freq_hz : from FFT features (rounded to 4 decimal places)
      - anomaly_flag   : from classification (bool)

    All 5 fields are ALWAYS present. No missing fields, ever.
    """
    return {
        "trace_id":         signal_chunk["trace_id"],         # UNCHANGED — critical
        "vessel_type":      classification["vessel_type"],
        "confidence_score": classification["confidence_score"],
        "dominant_freq_hz": round(features["dominant_freq_hz"], 4),
        "anomaly_flag":     classification["anomaly_flag"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def process_signal(signal_chunk: dict) -> dict:
    """
    Full pipeline: signal_chunk → perception_event

    Steps:
      1. Validate incoming signal_chunk schema
      2. Extract FFT features
      3. Classify vessel + detect anomalies
      4. Build and return structured perception_event

    On validation failure:
      Returns structured error dict (trace_id preserved).
      NEVER crashes silently. NEVER returns None.

    Usage:
        from perception_node import process_signal
        perception_event = process_signal(signal_chunk)
    """
    trace_id = signal_chunk.get("trace_id", "MISSING") if isinstance(signal_chunk, dict) else "MISSING"
    logger.info(f"[START] trace_id={trace_id}")

    # ── Step 1: Validate ─────────────────────────────────────────────────────
    valid, reason = validate_signal_chunk(signal_chunk)
    if not valid:
        logger.error(f"[INVALID] trace_id={trace_id} | reason={reason}")
        return {
            "error":    True,
            "reason":   reason,
            "trace_id": trace_id,
        }

    # ── Step 2: FFT + Feature Extraction ─────────────────────────────────────
    features = extract_features(signal_chunk)

    # ── Step 3: Classification + Anomaly Detection ────────────────────────────
    classification = classify_vessel(features)

    # ── Step 4: Build perception_event ────────────────────────────────────────
    perception_event = build_perception_event(signal_chunk, features, classification)

    logger.info(f"[OUTPUT] perception_event={perception_event}")
    return perception_event


# ─────────────────────────────────────────────────────────────────────────────
# QUICK SELF-TEST (run directly: python perception_node.py)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    try:
        from hybrid_signal_builder import HybridSignalBuilder
    except ImportError:
        print("[ERROR] Run from svacs-demo/services/data_layer/ — cannot import HybridSignalBuilder")
        sys.exit(1)

    print("\n" + "=" * 65)
    print("  PERCEPTION NODE — SELF TEST")
    print("=" * 65)

    builder = HybridSignalBuilder(sample_rate=4000, duration=1.0, seed=42)
    vessel_types = ["cargo", "speedboat", "submarine", "low_confidence", "anomaly"]

    results = []
    for vtype in vessel_types:
        chunk = builder.build(vtype)
        event = process_signal(chunk)

        trace_ok = (event.get("trace_id") == chunk["trace_id"])
        has_all  = all(k in event for k in ["trace_id","vessel_type","confidence_score","dominant_freq_hz","anomaly_flag"])
        status   = "PASS" if (trace_ok and has_all and "error" not in event) else "FAIL"
        results.append(status)

        print(f"\n  [{vtype.upper()}]")
        print(f"    vessel_type    : {event.get('vessel_type')}")
        print(f"    confidence     : {event.get('confidence_score')}")
        print(f"    dominant_freq  : {event.get('dominant_freq_hz')} Hz")
        print(f"    anomaly_flag   : {event.get('anomaly_flag')}")
        print(f"    trace_id match : {'YES' if trace_ok else 'NO — MISMATCH'}")
        print(f"    all fields     : {'YES' if has_all else 'NO — MISSING FIELDS'}")
        print(f"    result         : {status}")

    # Validation test
    print("\n" + "─" * 65)
    print("  VALIDATION TEST (bad inputs)")
    bad_cases = [
        ({}, "empty dict"),
        ({"trace_id": "abc", "samples": [], "sample_rate": 4000}, "empty samples"),
        ({"trace_id": "abc", "samples": [0.1]*100, "sample_rate": -1}, "negative sample_rate"),
        ({"samples": [0.1]*100, "sample_rate": 4000}, "missing trace_id"),
    ]
    for bad_chunk, desc in bad_cases:
        result = process_signal(bad_chunk)
        ok = result.get("error") == True
        print(f"    {'PASS' if ok else 'FAIL'} — {desc}: {result.get('reason', 'no reason returned')}")

    passed = results.count("PASS")
    print(f"\n{'=' * 65}")
    print(f"  SUMMARY: {passed}/5 vessel types PASS")
    if passed == 5:
        print("  ALL TESTS PASSED — Perception Node is ready")
    else:
        print("  SOME TESTS FAILED — check output above")
    print("=" * 65 + "\n")
