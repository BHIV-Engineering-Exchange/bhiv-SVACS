"""
SVACS Signal Generator
======================
Generates synthetic acoustic signals for 3 base vessel types + 2 special cases:
  - Cargo Ship      : 50-200 Hz, stable, low noise
  - Speedboat       : 500-1500 Hz, irregular, high noise
  - Submarine       : 20-100 Hz, low energy, partially masked
  - Low Confidence  : weak amplitude + dominant noise (any freq)
  - Anomaly         : multi-frequency spike pattern, bursts, no vessel match

Output format per chunk (pipeline-ready):
  {
    "trace_id":    str (UUID4),
    "scenario_id": int | None,
    "timestamp":   float,
    "samples":     [float, ...],
    "sample_rate": int,
    "vessel_type": str,
    "expected_label": {
        "vessel_type":       str,
        "confidence_range":  [float, float],
        "scenario_type":     str,
        "anomaly_flag":      bool
    },
    "metadata": { ... }
  }
"""

import uuid
import numpy as np
import time

CONFIDENCE_RANGES = {
    "high":        [0.80, 1.00],
    "medium_high": [0.65, 0.85],
    "medium":      [0.45, 0.70],
    "low":         [0.10, 0.40],
    "unknown":     [0.00, 0.30],
}

SCENARIO_TYPE_MAP = {
    "cargo":          "normal_classification",
    "ferry":          "normal_classification",
    "cruise":         "normal_classification",
    "roro":           "normal_classification",
    "passenger":      "normal_classification",
    "speedboat":      "normal_classification",
    "submarine":      "stealth_detection",
    "low_confidence": "low_confidence",
    "anomaly":        "anomaly",
}

ANOMALY_FLAG_MAP = {
    "cargo":          False,
    "ferry":          False,
    "cruise":         False,
    "roro":           False,
    "passenger":      False,
    "speedboat":      False,
    "submarine":      False,
    "low_confidence": False,
    "anomaly":        True,
}


class SignalGenerator:
    def __init__(self, sample_rate: int = 4000, duration: float = 1.0, seed: int = None):
        self.sample_rate = sample_rate
        self.duration = duration
        self.rng = np.random.default_rng(seed)

    def _time_axis(self):
        n = int(self.sample_rate * self.duration)
        return np.linspace(0, self.duration, n, endpoint=False)

    def _sine_wave(self, freq, amplitude):
        t = self._time_axis()
        return amplitude * np.sin(2 * np.pi * freq * t)

    def _noise(self, level, size):
        return level * self.rng.standard_normal(size)

    def _amplitude_modulate(self, signal, mod_depth=0.1):
        t = self._time_axis()
        mod = 1.0 + mod_depth * np.sin(2 * np.pi * 0.5 * t)
        return signal * mod

    def cargo_ship(self):
        freq      = float(self.rng.uniform(50, 200))
        amplitude = 1.0
        noise_lvl = 0.08
        signal = self._sine_wave(freq, amplitude)
        signal = self._amplitude_modulate(signal, mod_depth=0.05)
        signal += self._noise(noise_lvl, len(signal))
        return {
            "vessel_type": "cargo",
            "metadata": {
                "freq_hz": round(freq, 2), "amplitude": amplitude,
                "noise_level": noise_lvl, "confidence_expected": "high",
                "scenario_tag": "normal_cargo"
            },
            "samples": signal
        }

    def ferry(self):
        freq      = float(self.rng.uniform(201, 300))
        amplitude = 1.1
        noise_lvl = 0.09
        signal = self._sine_wave(freq, amplitude)
        signal = self._amplitude_modulate(signal, mod_depth=0.06)
        signal += self._noise(noise_lvl, len(signal))
        return {
            "vessel_type": "ferry",
            "metadata": {
                "freq_hz": round(freq, 2), "amplitude": amplitude,
                "noise_level": noise_lvl, "confidence_expected": "high",
                "scenario_tag": "normal_ferry"
            },
            "samples": signal
        }

    def cruise(self):
        freq      = float(self.rng.uniform(301, 400))
        amplitude = 1.05
        noise_lvl = 0.05
        signal = self._sine_wave(freq, amplitude)
        signal = self._amplitude_modulate(signal, mod_depth=0.02)
        signal += self._noise(noise_lvl, len(signal))
        return {
            "vessel_type": "cruise",
            "metadata": {
                "freq_hz": round(freq, 2), "amplitude": amplitude,
                "noise_level": noise_lvl, "confidence_expected": "high",
                "scenario_tag": "normal_cruise"
            },
            "samples": signal
        }

    def roro(self):
        freq      = float(self.rng.uniform(401, 499))
        amplitude = 1.15
        noise_lvl = 0.12
        signal = self._sine_wave(freq, amplitude)
        signal = self._amplitude_modulate(signal, mod_depth=0.1)
        signal += self._noise(noise_lvl, len(signal))
        return {
            "vessel_type": "roro",
            "metadata": {
                "freq_hz": round(freq, 2), "amplitude": amplitude,
                "noise_level": noise_lvl, "confidence_expected": "medium_high",
                "scenario_tag": "normal_roro"
            },
            "samples": signal
        }

    def passenger(self):
        freq      = float(self.rng.uniform(1501, 1600))
        amplitude = 1.05
        noise_lvl = 0.1
        signal = self._sine_wave(freq, amplitude)
        signal = self._amplitude_modulate(signal, mod_depth=0.08)
        signal += self._noise(noise_lvl, len(signal))
        return {
            "vessel_type": "passenger",
            "metadata": {
                "freq_hz": round(freq, 2), "amplitude": amplitude,
                "noise_level": noise_lvl, "confidence_expected": "medium_high",
                "scenario_tag": "normal_passenger"
            },
            "samples": signal
        }


    def speedboat(self):
        freq      = float(self.rng.uniform(500, 1500))
        amplitude = 1.2
        noise_lvl = 0.45
        signal  = self._sine_wave(freq, amplitude)
        signal  = self._amplitude_modulate(signal, mod_depth=0.25)
        signal += self._noise(noise_lvl, len(signal))
        signal += 0.3 * self._sine_wave(freq * 2, amplitude)
        return {
            "vessel_type": "speedboat",
            "metadata": {
                "freq_hz": round(freq, 2), "harmonic_hz": round(freq * 2, 2),
                "amplitude": amplitude, "noise_level": noise_lvl,
                "confidence_expected": "medium_high", "scenario_tag": "speedboat_clear"
            },
            "samples": signal
        }

    def submarine(self):
        freq      = float(self.rng.uniform(20, 45))
        amplitude = 0.4
        noise_lvl = 0.04
        signal = self._sine_wave(freq, amplitude)
        signal = self._amplitude_modulate(signal, mod_depth=0.02)
        mask = float(self.rng.uniform(0.25, 0.60))
        signal *= mask
        signal += self._noise(noise_lvl, len(signal))
        return {
            "vessel_type": "submarine",
            "metadata": {
                "freq_hz": round(freq, 2), "amplitude": round(amplitude * mask, 4),
                "noise_level": noise_lvl, "mask_factor": round(mask, 3),
                "confidence_expected": "medium", "scenario_tag": "submarine_stealth"
            },
            "samples": signal
        }

    def low_confidence(self):
        freq      = float(self.rng.uniform(80, 600))
        amplitude = float(self.rng.uniform(0.1, 0.2))
        noise_lvl = float(self.rng.uniform(0.5, 0.8))
        signal = self._sine_wave(freq, amplitude)
        signal += self._noise(noise_lvl, len(signal))
        return {
            "vessel_type": "unknown",
            "metadata": {
                "freq_hz": round(freq, 2), "amplitude": round(amplitude, 4),
                "noise_level": round(noise_lvl, 4),
                "confidence_expected": "low", "scenario_tag": "low_confidence_noisy"
            },
            "samples": signal
        }

    def anomaly(self):
        t = self._time_axis()
        n = len(t)
        freqs  = self.rng.uniform(30, 2000, size=5)
        signal = np.zeros(n)
        for f in freqs:
            signal += float(self.rng.uniform(0.1, 0.8)) * np.sin(2 * np.pi * f * t)
        spike_pos = self.rng.integers(0, n, size=12)
        for sp in spike_pos:
            signal[sp] += float(self.rng.choice([-2.5, 2.5]))
        signal += self._noise(0.5, n)
        return {
            "vessel_type": "anomaly",
            "metadata": {
                "freq_hz": "mixed",
                "component_freqs_hz": [round(float(f), 2) for f in freqs],
                "amplitude": "variable", "noise_level": 0.5,
                "confidence_expected": "unknown", "scenario_tag": "anomaly_unknown_pattern",
                "anomaly_reason": (
                    "Multi-peak frequency spectrum with random burst artifacts. "
                    "Does not match cargo (50-200 Hz), speedboat (500-1500 Hz), "
                    "or submarine (20-100 Hz) propulsion profiles."
                )
            },
            "samples": signal
        }

    def generate_chunk(self, vessel_type: str, scenario_id: int = None) -> dict:
        dispatch = {
            "cargo": self.cargo_ship,
            "ferry": self.ferry,
            "cruise": self.cruise,
            "roro": self.roro,
            "passenger": self.passenger,
            "speedboat": self.speedboat,
            "submarine": self.submarine,
            "low_confidence": self.low_confidence,
            "anomaly": self.anomaly,
        }
        if vessel_type not in dispatch:
            raise ValueError(f"Unknown vessel_type '{vessel_type}'. Choose from: {list(dispatch.keys())}")

        raw = dispatch[vessel_type]()
        samples = raw.pop("samples")

        conf_key    = raw.get("metadata", {}).get("confidence_expected", "unknown")
        conf_range  = CONFIDENCE_RANGES.get(conf_key, [0.0, 1.0])
        scen_type   = SCENARIO_TYPE_MAP.get(vessel_type, "unknown")
        anomaly_flag = ANOMALY_FLAG_MAP.get(vessel_type, False)

        return {
            "trace_id":    str(uuid.uuid4()),
            "scenario_id": scenario_id,
            "timestamp":   time.time(),
            "samples":     samples.tolist(),
            "sample_rate": self.sample_rate,
            "vessel_type": raw.get("vessel_type", vessel_type),
            "expected_label": {
                "vessel_type":      raw.get("vessel_type", vessel_type),
                "confidence_range": conf_range,
                "scenario_type":    scen_type,
                "anomaly_flag":     anomaly_flag,
            },
            "metadata": raw.get("metadata", {})
        }


if __name__ == "__main__":
    gen = SignalGenerator(seed=42)
    for vtype in ["cargo", "speedboat", "submarine", "low_confidence", "anomaly"]:
        chunk = gen.generate_chunk(vtype)
        s = chunk["samples"]
        print(
            f"[{vtype:<16}] trace={chunk['trace_id'][:8]}...  "
            f"n={len(s):5d}  conf_range={chunk['expected_label']['confidence_range']}  "
            f"anomaly={chunk['expected_label']['anomaly_flag']}"
        )