"""
SVACS Signal Layer -- scenario_builder.py
=========================================
Generates all 5 labeled demo scenarios and saves them to scenarios/ folder.
Each scenario includes: scenario_id, description, vessel_type,
expected_behavior, anomaly_flag, confidence expectation, and trace_id.
"""

import os
import json
import time
from hybrid_signal_builder import HybridSignalBuilder


SCENARIOS = [
    {
        "id": 1, "filename": "scenario_1_cargo.json",
        "name": "Normal Cargo Ship", "vessel_type": "cargo",
        "noise_alpha": 0.3, "signal_beta": 1.0,
        "expected_vessel_type": "cargo_ship", "expected_confidence": "high",
        "confidence_range": [0.80, 1.00], "scenario_type": "normal_classification",
        "description": (
            "Stable low-frequency cargo ship signal (50-200 Hz). "
            "Steady amplitude, minimal noise. Clean FFT peak in cargo range. "
            "Use as pipeline baseline."
        ),
        "expected_behavior": (
            "Downstream classifier should produce a STRONG detection with HIGH confidence. "
            "FFT peak falls clearly within 50-200 Hz cargo band. "
            "No ambiguity expected."
        ),
        "pipeline_notes": {
            "detection": "strong", "classification": "cargo_ship",
            "anomaly_flag": False, "expected_samachar_tag": "vessel_detected_high_conf"
        }
    },
    {
        "id": 2, "filename": "scenario_2_speedboat.json",
        "name": "Speedboat -- Clear Classification", "vessel_type": "speedboat",
        "noise_alpha": 0.5, "signal_beta": 1.0,
        "expected_vessel_type": "speedboat", "expected_confidence": "medium_high",
        "confidence_range": [0.65, 0.85], "scenario_type": "normal_classification",
        "description": (
            "High-frequency speedboat signal (500-1500 Hz). "
            "Irregular waveform with 2nd harmonic. High noise from fast engine RPM."
        ),
        "expected_behavior": (
            "Classifier should detect high-frequency dominant peak and classify as speedboat. "
            "Confidence reduced due to noise but still above medium threshold. "
            "2nd harmonic confirms speedboat profile."
        ),
        "pipeline_notes": {
            "detection": "strong", "classification": "speedboat",
            "anomaly_flag": False, "expected_samachar_tag": "vessel_detected_medium_conf"
        }
    },
    {
        "id": 3, "filename": "scenario_3_submarine.json",
        "name": "Submarine / Stealth Object", "vessel_type": "submarine",
        "noise_alpha": 0.4, "signal_beta": 0.8,
        "expected_vessel_type": "submarine", "expected_confidence": "medium",
        "confidence_range": [0.45, 0.70], "scenario_type": "stealth_detection",
        "description": (
            "Very low frequency submarine signal (20-100 Hz). "
            "Low energy, partially masked by stealth factor (0.25-0.60x). "
            "Signal is near-infrasonic."
        ),
        "expected_behavior": (
            "Signal energy is distinctly below cargo range. "
            "Requires sensitive low-frequency detection. "
            "Masking factor reduces confidence to MEDIUM. "
            "Pipeline must NOT dismiss as noise."
        ),
        "pipeline_notes": {
            "detection": "weak", "classification": "submarine",
            "anomaly_flag": False, "expected_samachar_tag": "stealth_object_detected"
        }
    },
    {
        "id": 4, "filename": "scenario_4_low_confidence.json",
        "name": "Low Confidence Signal", "vessel_type": "low_confidence",
        "noise_alpha": 1.0, "signal_beta": 0.3,
        "expected_vessel_type": "unknown", "expected_confidence": "low",
        "confidence_range": [0.10, 0.40], "scenario_type": "low_confidence",
        "description": (
            "Weak signal (amplitude 0.1-0.2) buried under heavy ocean noise (0.5-0.8). "
            "Simulates distant vessel, degraded hydrophone, or heavy sea state."
        ),
        "expected_behavior": (
            "Noise dominates signal completely. "
            "Pipeline MUST NOT misclassify with high confidence. "
            "Expected output: UNCERTAIN detection, unknown vessel type, LOW confidence."
        ),
        "pipeline_notes": {
            "detection": "uncertain", "classification": "unknown",
            "anomaly_flag": False, "expected_samachar_tag": "low_confidence_detection"
        }
    },
    {
        "id": 5, "filename": "scenario_5_anomaly.json",
        "name": "Anomaly -- Unknown Pattern", "vessel_type": "anomaly",
        "noise_alpha": 0.4, "signal_beta": 1.0,
        "expected_vessel_type": "anomaly", "expected_confidence": "unknown",
        "confidence_range": [0.00, 0.30], "scenario_type": "anomaly",
        "description": (
            "Multi-frequency spike pattern (3-7 components, 10-2000 Hz each) "
            "with random amplitude bursts at 12 positions. "
            "Does NOT match any known vessel propulsion profile."
        ),
        "expected_behavior": (
            "No single dominant frequency in a known vessel band. "
            "Burst artifacts indicate non-vessel origin. "
            "Pipeline must flag anomaly_flag=True and trigger alert. "
            "May represent: unknown object, biologic event (whale), "
            "equipment malfunction, or jamming signal."
        ),
        "pipeline_notes": {
            "detection": "triggered", "classification": "anomaly",
            "anomaly_flag": True, "expected_samachar_tag": "anomaly_alert_triggered"
        }
    }
]


class ScenarioBuilder:
    def __init__(self, output_dir="scenarios", sample_rate=4000, duration=1.0):
        self.output_dir = output_dir
        self.builder = HybridSignalBuilder(sample_rate=sample_rate, duration=duration)
        os.makedirs(output_dir, exist_ok=True)

    def build_scenario(self, scenario_def):
        print(f"[BUILD] Scenario {scenario_def['id']}: {scenario_def['name']}")
        chunk = self.builder.build(
            vessel_type=scenario_def["vessel_type"],
            scenario_id=scenario_def["id"]
        )
        return {
            "scenario_id":   scenario_def["id"],
            "scenario_name": scenario_def["name"],
            "scenario_type": scenario_def["scenario_type"],
            "description":   scenario_def["description"],
            "labels": {
                "vessel_type":          scenario_def["vessel_type"],
                "expected_vessel_type": scenario_def["expected_vessel_type"],
                "expected_confidence":  scenario_def["expected_confidence"],
                "confidence_range":     scenario_def["confidence_range"],
                "anomaly_flag":         scenario_def["pipeline_notes"]["anomaly_flag"]
            },
            "expected_behavior": scenario_def["expected_behavior"],
            "pipeline_hints":    scenario_def["pipeline_notes"],
            "signal":            chunk,
            "generated_at":      time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }

    def save_scenario(self, scenario_data, filename):
        path = os.path.join(self.output_dir, filename)
        with open(path, "w") as f:
            json.dump(scenario_data, f, indent=2)
        print(f"  [SAVED] -> {path}  [trace_id={scenario_data['signal']['trace_id'][:8]}...]")
        return path

    def build_all(self):
        print("\n" + "="*60)
        print("SVACS SCENARIO BUILDER -- Building all 5 scenarios")
        print("="*60)
        saved_paths = []
        for s in SCENARIOS:
            data = self.build_scenario(s)
            path = self.save_scenario(data, s["filename"])
            saved_paths.append(path)
        self._write_index()
        print("\n[DONE] All 5 scenarios generated.")
        return saved_paths

    def _write_index(self):
        index = [
            {
                "id":                  s["id"],
                "name":                s["name"],
                "file":                s["filename"],
                "vessel_type":         s["vessel_type"],
                "expected_confidence": s["expected_confidence"],
                "scenario_type":       s["scenario_type"],
                "anomaly_flag":        s["pipeline_notes"]["anomaly_flag"],
                "description":         s["description"]
            }
            for s in SCENARIOS
        ]
        path = os.path.join(self.output_dir, "index.json")
        with open(path, "w") as f:
            json.dump({"scenarios": index, "total": len(index)}, f, indent=2)
        print(f"  [INDEX] -> {path}")


if __name__ == "__main__":
    sb = ScenarioBuilder(output_dir="scenarios")
    sb.build_all()