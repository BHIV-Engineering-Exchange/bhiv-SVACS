"""
SVACS Signal Utilities
=======================
Helper functions used across the pipeline:
  - Signal statistics
  - SNR calculation
  - Chunk validation
  - Label inference (rule-based, for testing without NICAI)
"""

import numpy as np
from typing import Dict, List, Any



#  Signal statistics
# ══════════════════════════════════════════════════════════════════════════════

def signal_stats(samples: list) -> dict:
    """Return basic descriptive statistics for a sample array."""
    arr = np.array(samples)
    return {
        "mean":    float(np.mean(arr)),
        "std":     float(np.std(arr)),
        "min":     float(np.min(arr)),
        "max":     float(np.max(arr)),
        "rms":     float(np.sqrt(np.mean(arr ** 2))),
        "peak":    float(np.max(np.abs(arr))),
        "n":       len(arr),
    }


def dominant_frequency(samples: list, sample_rate: int) -> float:
    """
    Return the dominant frequency (Hz) via FFT magnitude peak.
    Ignores DC component.
    """
    arr  = np.array(samples)
    fft  = np.fft.rfft(arr)
    mag  = np.abs(fft)
    mag[0] = 0   # zero out DC
    freqs  = np.fft.rfftfreq(len(arr), d=1.0 / sample_rate)
    return float(freqs[np.argmax(mag)])


def snr_db(signal: list, noise_estimate: list) -> float:
    """
    SNR in dB given a clean signal and noise estimate.
    Both should be same length.
    """
    s = np.std(np.array(signal))
    n = np.std(np.array(noise_estimate))
    if n < 1e-12:
        return float("inf")
    return float(20 * np.log10(s / n))



#  Chunk validation
# ══════════════════════════════════════════════════════════════════════════════

REQUIRED_FIELDS = {"timestamp", "samples", "sample_rate", "vessel_type"}


def validate_chunk(chunk: dict) -> dict:
    """
    Validate that a signal_chunk conforms to SVACS pipeline spec.

    Returns:
        (True, "ok")  on success
        (False, reason_str)  on failure
    """
    missing = REQUIRED_FIELDS - set(chunk.keys())
    if missing:
        return False, f"Missing fields: {missing}"

    if not isinstance(chunk["samples"], (list, np.ndarray)) or len(chunk["samples"]) == 0:
        return False, "samples must be a non-empty list"

    if not isinstance(chunk["sample_rate"], (int, float)) or chunk["sample_rate"] <= 0:
        return False, "sample_rate must be a positive number"

    if not isinstance(chunk["timestamp"], (int, float)):
        return False, "timestamp must be numeric"

    return {"valid": True, "reason": "ok"}


def validate_batch(chunks: list) -> list:
    """Validate a list of chunks. Returns list of (ok, reason) tuples."""
    return [validate_chunk(c) for c in chunks]



#  Rule-based classifier (lightweight, no ML)
# ══════════════════════════════════════════════════════════════════════════════

VESSEL_RULES = {
    "cargo":     {"freq_lo": 50,  "freq_hi": 200,  "rms_min": 0.15},
    "speedboat": {"freq_lo": 500, "freq_hi": 1500, "rms_min": 0.20},
    "submarine": {"freq_lo": 20,  "freq_hi": 100,  "rms_min": 0.02},
}


def rule_classify(chunk: dict) -> dict:
    """
    Lightweight rule-based classifier.
    Uses dominant frequency + RMS to infer vessel type and confidence.

    Returns:
        {
          "predicted_type": str,
          "confidence": float (0-1),
          "dominant_freq_hz": float,
          "rms": float,
          "anomaly": bool
        }
    """
    samples     = chunk["samples"]
    sample_rate = chunk["sample_rate"]

    dom_freq = dominant_frequency(samples, sample_rate)
    stats    = signal_stats(samples)
    rms      = stats["rms"]

    # Low energy / buried signal → low confidence
    if rms < 0.05:
        return {
            "predicted_type":  "unknown",
            "confidence":      round(float(rms * 5), 3),
            "dominant_freq_hz": dom_freq,
            "rms":             rms,
            "anomaly":         False,
        }

    # Match rules
    for vtype, rule in VESSEL_RULES.items():
        if rule["freq_lo"] <= dom_freq <= rule["freq_hi"] and rms >= rule["rms_min"]:
            confidence = min(0.99, 0.6 + (rms / 1.5))
            return {
                "predicted_type":  vtype,
                "confidence":      round(float(confidence), 3),
                "dominant_freq_hz": dom_freq,
                "rms":             rms,
                "anomaly":         False,
            }

    # No rule matched → anomaly
    return {
        "predicted_type":  "anomaly",
        "confidence":      0.0,
        "dominant_freq_hz": dom_freq,
        "rms":             rms,
        "anomaly":         True,
    }


def plot_signal(chunk: dict, save_path: str = None):
    import matplotlib.pyplot as plt
    import numpy as np

    samples = np.array(chunk["samples"])
    sr = chunk["sample_rate"]

    t = np.arange(len(samples)) / sr

    plt.figure(figsize=(10, 4))
    plt.plot(t, samples)
    plt.title(f"Signal: {chunk.get('vessel_type', 'unknown')}")
    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude")

    if save_path:
        plt.savefig(save_path)
        plt.close()
    else:
        plt.show()


def summarize(chunk: dict) -> dict:
    samples = chunk["samples"]
    sr = chunk["sample_rate"]

    stats = signal_stats(samples)
    peak_freq = dominant_frequency(samples, sr)

    # Estimate noise (simple: assume small component)
    noise_estimate = np.array(samples) - np.mean(samples)
    snr = 20 * np.log10((np.std(samples) + 1e-9) / (np.std(noise_estimate) + 1e-9))

    return {
        "rms": stats["rms"],
        "peak_freq_hz": peak_freq,
        "amplitude_variance": stats["std"],
        "snr_db": float(snr),  #  ADD THIS
        "vessel_type": chunk.get("vessel_type", "unknown"),
        "confidence_expected": chunk.get("metadata", {}).get("confidence_expected", "unknown")
    }


#  Quick test
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from hybrid_signal_builder import HybridSignalBuilder

    builder = HybridSignalBuilder(seed=99)

    print(f"{'TYPE':<16}  {'DOM_FREQ':>10}  {'RMS':>6}  {'PREDICTED':<14}  {'CONF':>5}  ANOMALY")
    print("─" * 72)

    for vtype in ["cargo", "speedboat", "submarine", "low_confidence", "anomaly"]:
        chunk  = builder.build(vtype)
        result = rule_classify(chunk)
        ok, _  = validate_chunk(chunk)

        print(
            f"{vtype:<16}  "
            f"{result['dominant_freq_hz']:>10.1f}  "
            f"{result['rms']:>6.3f}  "
            f"{result['predicted_type']:<14}  "
            f"{result['confidence']:>5.3f}  "
            f"{'YES' if result['anomaly'] else 'no'}"
        )