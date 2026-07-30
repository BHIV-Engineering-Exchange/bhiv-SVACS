"""
SVACS — noisy_scenario_builder.py
====================================
Operational Maritime Realism Layer

Extends HybridSignalBuilder with deterministic noisy scenarios
that simulate real maritime conditions:
  - ocean noise (sea state)
  - weather noise (wind/rain interference)
  - sensor dropout (signal gaps)
  - multi-vessel overlap (two vessels simultaneously)
  - AIS inconsistency (label mismatch)
  - anomaly injection (deliberate multi-peak spikes)

All scenarios are deterministic and replay-safe.
Given the same seed, output is always identical.

Usage:
    from noisy_scenario_builder import NoisyScenarioBuilder
    builder = NoisyScenarioBuilder(seed=42)
    chunk = builder.build_ocean_noise("cargo")
    chunk = builder.build_multi_vessel("cargo", "speedboat")
    scenarios = builder.build_all_scenarios()
"""

import numpy as np
import uuid
import time
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))

# Import base builder
import sys
sys.path.insert(0, BASE)
from hybrid_signal_builder import HybridSignalBuilder


class NoisyScenarioBuilder:
    """
    Builds deterministic noisy maritime signal scenarios.
    
    Each method returns a signal_chunk dict compatible with
    perception_node.process_signal() — same schema as HybridSignalBuilder.
    
    The 'scenario' field is added to each chunk to identify
    what noise condition was applied.
    """

    def __init__(self, seed: int = 42, sample_rate: int = 4000, duration: float = 1.0):
        """
        Args:
            seed:        random seed — guarantees deterministic replay
            sample_rate: Hz, default 4000
            duration:    seconds, default 1.0
        """
        self.seed        = seed
        self.sample_rate = sample_rate
        self.duration    = duration
        self.n_samples   = int(sample_rate * duration)
        
        # Base builder for clean signals
        self.base_builder = HybridSignalBuilder(
            sample_rate=sample_rate,
            duration=duration,
            seed=seed
        )
        
        # Seeded RNG — guarantees same noise every time for same seed
        self.rng = np.random.default_rng(seed)

    def _new_trace_id(self) -> str:
        """Generate a fresh UUID4 trace_id."""
        return str(uuid.uuid4())

    def _base_chunk(self, vessel_type: str) -> dict:
        """Get a clean base signal chunk for a vessel type."""
        return self.base_builder.build(vessel_type)

    # ── SCENARIO 1: Ocean Noise ───────────────────────────────────────────────
    def build_ocean_noise(self, vessel_type: str, noise_scale: float = 0.3) -> dict:
        """
        Adds realistic ocean background noise to a clean vessel signal.
        
        Ocean noise is low-frequency (1-200 Hz) random variation
        caused by waves, currents, and distant shipping traffic.
        
        Args:
            vessel_type: the vessel to simulate
            noise_scale: how strong the ocean noise is (0.0-1.0)
                        0.1 = calm sea, 0.3 = moderate, 0.6 = rough sea
        
        Returns:
            signal_chunk with ocean noise added, scenario='ocean_noise'
        """
        chunk = self._base_chunk(vessel_type)
        samples = np.array(chunk["samples"])
        
        # Generate low-frequency ocean noise (1-200 Hz band)
        # Using seeded RNG for determinism
        t = np.linspace(0, self.duration, self.n_samples)
        
        # Ocean noise = sum of several low-frequency sine waves
        # with random amplitudes and phases
        ocean_noise = np.zeros(self.n_samples)
        for freq in [5, 15, 30, 50, 80, 120, 180]:
            amplitude = self.rng.uniform(0.05, 0.2) * noise_scale
            phase     = self.rng.uniform(0, 2 * np.pi)
            ocean_noise += amplitude * np.sin(2 * np.pi * freq * t + phase)
        
        # Add white noise component
        ocean_noise += self.rng.normal(0, 0.05 * noise_scale, self.n_samples)
        
        # Mix vessel signal with ocean noise
        noisy_signal = samples + ocean_noise
        
        # Renormalize to [-1, 1]
        max_val = np.max(np.abs(noisy_signal)) or 1.0
        noisy_signal = noisy_signal / max_val
        
        chunk["samples"]     = noisy_signal.tolist()
        chunk["trace_id"]    = self._new_trace_id()
        chunk["scenario"]    = "ocean_noise"
        chunk["noise_scale"] = noise_scale
        chunk["noise_type"]  = "ocean_background"
        chunk["geo_zone"]    = "open_ocean"
        
        return chunk

    # ── SCENARIO 2: Weather Noise ─────────────────────────────────────────────
    def build_weather_noise(self, vessel_type: str, intensity: float = 0.4) -> dict:
        """
        Adds weather interference — high-frequency noise from wind and rain.
        
        Weather noise is high-frequency (500-2000 Hz) and tends to
        reduce SNR significantly, especially for low-energy signals
        like submarines.
        
        Args:
            vessel_type: the vessel to simulate
            intensity:   weather intensity (0.0-1.0)
                        0.2 = light rain, 0.5 = heavy rain, 0.8 = storm
        
        Returns:
            signal_chunk with weather noise, scenario='weather_noise'
        """
        chunk = self._base_chunk(vessel_type)
        samples = np.array(chunk["samples"])
        t = np.linspace(0, self.duration, self.n_samples)
        
        # Weather noise = high-frequency interference
        weather_noise = np.zeros(self.n_samples)
        for freq in [600, 800, 1000, 1200, 1500, 1800]:
            amplitude = self.rng.uniform(0.02, 0.15) * intensity
            phase     = self.rng.uniform(0, 2 * np.pi)
            weather_noise += amplitude * np.sin(2 * np.pi * freq * t + phase)
        
        # Add burst noise — random spikes simulating rain drops
        burst_count = int(50 * intensity)
        burst_positions = self.rng.integers(0, self.n_samples, burst_count)
        for pos in burst_positions:
            burst_width = self.rng.integers(5, 20)
            end = min(pos + burst_width, self.n_samples)
            weather_noise[pos:end] += self.rng.uniform(0.1, 0.3) * intensity

        noisy_signal = samples + weather_noise
        max_val = np.max(np.abs(noisy_signal)) or 1.0
        noisy_signal = noisy_signal / max_val
        
        chunk["samples"]          = noisy_signal.tolist()
        chunk["trace_id"]         = self._new_trace_id()
        chunk["scenario"]         = "weather_noise"
        chunk["weather_intensity"] = intensity
        chunk["noise_type"]        = "weather_interference"
        chunk["geo_zone"]          = "coastal"
        
        return chunk

    # ── SCENARIO 3: Sensor Dropout ────────────────────────────────────────────
    def build_sensor_dropout(self, vessel_type: str, dropout_rate: float = 0.15) -> dict:
        """
        Simulates sensor dropout — random gaps where the sensor
        stops recording and returns zero or near-zero values.
        
        This is common in real maritime sensors due to:
        - power fluctuations
        - mechanical vibration
        - water ingress
        - network packet loss
        
        Args:
            vessel_type:  the vessel to simulate
            dropout_rate: fraction of samples that drop out (0.0-1.0)
                         0.05 = minor, 0.15 = moderate, 0.30 = severe
        
        Returns:
            signal_chunk with dropout gaps, scenario='sensor_dropout'
        """
        chunk = self._base_chunk(vessel_type)
        samples = np.array(chunk["samples"])
        
        # Create dropout mask — True = keep sample, False = zero it out
        # Dropouts happen in bursts, not randomly scattered
        dropout_mask = np.ones(self.n_samples, dtype=bool)
        
        n_dropouts = int(self.n_samples * dropout_rate / 20)
        for _ in range(n_dropouts):
            start  = self.rng.integers(0, self.n_samples - 20)
            length = self.rng.integers(10, 40)
            end    = min(start + length, self.n_samples)
            dropout_mask[start:end] = False
        
        # Apply dropout — zeroed samples with tiny noise
        samples_with_dropout = samples.copy()
        samples_with_dropout[~dropout_mask] = (
            self.rng.normal(0, 0.01, np.sum(~dropout_mask))
        )
        
        chunk["samples"]       = samples_with_dropout.tolist()
        chunk["trace_id"]      = self._new_trace_id()
        chunk["scenario"]      = "sensor_dropout"
        chunk["dropout_rate"]  = dropout_rate
        chunk["noise_type"]    = "sensor_failure"
        chunk["dropped_samples"] = int(np.sum(~dropout_mask))
        
        return chunk

    # ── SCENARIO 4: Multi-Vessel Overlap ─────────────────────────────────────
    def build_multi_vessel(
        self, vessel_type_1: str, vessel_type_2: str,
        mix_ratio: float = 0.6
    ) -> dict:
        """
        Mixes signals from two vessels to simulate overlap.
        
        In real maritime scenarios, multiple vessels operate
        simultaneously in the same acoustic zone. Their signals
        overlap in the hydrophone recording.
        
        The dominant vessel gets mix_ratio of the amplitude.
        The secondary vessel gets (1 - mix_ratio).
        
        Args:
            vessel_type_1: dominant vessel (primary signal)
            vessel_type_2: secondary vessel (mixed in)
            mix_ratio:     how dominant the first vessel is (0.5-0.9)
                          0.5 = equal mix, 0.7 = first dominates
        
        Returns:
            signal_chunk with mixed signal, scenario='multi_vessel_overlap'
            vessel_type is set to vessel_type_1 (dominant)
        """
        chunk_1 = self._base_chunk(vessel_type_1)
        chunk_2 = self._base_chunk(vessel_type_2)
        
        signal_1 = np.array(chunk_1["samples"])
        signal_2 = np.array(chunk_2["samples"])
        
        # Mix signals with ratio
        mixed = (mix_ratio * signal_1) + ((1 - mix_ratio) * signal_2)
        
        # Renormalize
        max_val = np.max(np.abs(mixed)) or 1.0
        mixed   = mixed / max_val
        
        # Use vessel_type_1 as the primary label
        chunk_1["samples"]    = mixed.tolist()
        chunk_1["trace_id"]   = self._new_trace_id()
        chunk_1["scenario"]   = "multi_vessel_overlap"
        chunk_1["vessel_type_primary"]   = vessel_type_1
        chunk_1["vessel_type_secondary"] = vessel_type_2
        chunk_1["mix_ratio"]  = mix_ratio
        chunk_1["noise_type"] = "multi_vessel_interference"
        
        return chunk_1

    # ── SCENARIO 5: AIS Inconsistency ────────────────────────────────────────
    def build_ais_inconsistency(
        self, true_vessel_type: str, reported_vessel_type: str
    ) -> dict:
        """
        Simulates AIS spoofing or transponder error where the
        reported vessel type doesn't match the acoustic signal.
        
        Example: AIS reports 'cargo' but the acoustic signature
        is actually 'submarine' — a critical security concern.
        
        The signal is generated from true_vessel_type but
        vessel_type field is set to reported_vessel_type.
        
        Args:
            true_vessel_type:     what the vessel actually is (acoustic)
            reported_vessel_type: what AIS says it is (label)
        
        Returns:
            signal_chunk where vessel_type != acoustic truth
            scenario='ais_inconsistency'
        """
        # Build the TRUE signal (what the hydrophone actually hears)
        chunk = self._base_chunk(true_vessel_type)
        
        # But label it as the REPORTED type (what AIS says)
        chunk["trace_id"]              = self._new_trace_id()
        chunk["vessel_type"]           = reported_vessel_type  # AIS label
        chunk["scenario"]              = "ais_inconsistency"
        chunk["ais_reported_type"]     = reported_vessel_type
        chunk["acoustic_true_type"]    = true_vessel_type
        chunk["noise_type"]            = "ais_spoofing"
        chunk["ais_inconsistency_flag"] = True
        
        return chunk

    # ── SCENARIO 6: Anomaly Injection ─────────────────────────────────────────
    def build_anomaly_injection(
        self, vessel_type: str, spike_count: int = 5
    ) -> dict:
        """
        Injects deliberate anomalous spikes into a clean vessel signal.
        Simulates equipment malfunction, jamming, or unknown biologic event.
        
        Args:
            vessel_type: base vessel signal to inject into
            spike_count: how many anomalous frequency spikes to inject
        
        Returns:
            signal_chunk with injected anomalies, scenario='anomaly_injection'
        """
        chunk = self._base_chunk(vessel_type)
        samples = np.array(chunk["samples"])
        t = np.linspace(0, self.duration, self.n_samples)
        
        # Inject random frequency spikes at non-standard bands
        # Frequencies chosen outside known vessel bands
        anomaly_freqs = self.rng.choice(
            [250, 350, 450, 750, 950, 1100, 1700, 1900, 2200, 2800],
            size=spike_count, replace=False
        )
        
        injected = samples.copy()
        for freq in anomaly_freqs:
            amplitude = self.rng.uniform(0.15, 0.4)
            phase     = self.rng.uniform(0, 2 * np.pi)
            injected += amplitude * np.sin(2 * np.pi * freq * t + phase)
        
        # Renormalize
        max_val = np.max(np.abs(injected)) or 1.0
        injected = injected / max_val
        
        chunk["samples"]          = injected.tolist()
        chunk["trace_id"]         = self._new_trace_id()
        chunk["scenario"]         = "anomaly_injection"
        chunk["injected_freqs"]   = [int(f) for f in anomaly_freqs]
        chunk["spike_count"]      = spike_count
        chunk["noise_type"]       = "deliberate_anomaly"
        
        return chunk

    # ── BUILD ALL SCENARIOS ───────────────────────────────────────────────────
    def build_all_scenarios(self) -> list:
        """
        Build a complete set of operational scenarios covering
        all noise conditions for all vessel types.
        
        Returns:
            List of signal_chunks ready for pipeline processing
        """
        scenarios = []
        
        # Ocean noise — all vessel types
        for vtype in ["cargo", "speedboat", "submarine"]:
            scenarios.append(self.build_ocean_noise(vtype, noise_scale=0.3))
        
        # Weather noise — critical vessels
        for vtype in ["submarine", "cargo"]:
            scenarios.append(self.build_weather_noise(vtype, intensity=0.4))
        
        # Sensor dropout
        scenarios.append(self.build_sensor_dropout("cargo", dropout_rate=0.15))
        scenarios.append(self.build_sensor_dropout("submarine", dropout_rate=0.20))
        
        # Multi-vessel overlap
        scenarios.append(self.build_multi_vessel("cargo", "speedboat", mix_ratio=0.7))
        scenarios.append(self.build_multi_vessel("submarine", "cargo", mix_ratio=0.6))
        
        # AIS inconsistency — critical security scenario
        scenarios.append(self.build_ais_inconsistency("submarine", "cargo"))
        
        # Anomaly injection
        scenarios.append(self.build_anomaly_injection("cargo", spike_count=5))
        scenarios.append(self.build_anomaly_injection("anomaly", spike_count=7))
        
        return scenarios


if __name__ == "__main__":
    import sys
    sys.path.insert(0, BASE)
    from perception_node import process_signal
    from geo_injector import inject_geo

    print("=" * 68)
    print("  NOISY SCENARIO BUILDER — SELF TEST")
    print("  Deterministic maritime operational scenarios")
    print("=" * 68)

    builder   = NoisyScenarioBuilder(seed=42)
    scenarios = builder.build_all_scenarios()

    print(f"\n  Total scenarios built: {len(scenarios)}")
    print("  " + "-" * 60)

    passed = 0
    failed = 0
    log    = []

    for chunk in scenarios:
        # Run through perception
        perception = process_signal(chunk)
        
        # Inject geo coordinates
        geo_event = inject_geo(perception, vessel_type=chunk.get("vessel_type"))
        
        # Check trace continuity
        trace_ok = (chunk["trace_id"] == perception.get("trace_id"))
        
        status = "PASS" if trace_ok and "error" not in perception else "FAIL"
        if status == "PASS":
            passed += 1
        else:
            failed += 1

        print(
            f"  [{chunk['scenario']:<25}] "
            f"input={chunk.get('vessel_type', 'N/A'):<12} "
            f"predicted={perception.get('vessel_type', 'N/A'):<12} "
            f"anomaly={perception.get('anomaly_flag')} "
            f"conf={perception.get('confidence_score', 0):.3f} "
            f"trace={trace_ok} → {status}"
        )

        log.append({
            "scenario":         chunk["scenario"],
            "input_vessel":     chunk.get("vessel_type"),
            "predicted_vessel": perception.get("vessel_type"),
            "confidence":       perception.get("confidence_score"),
            "anomaly_flag":     perception.get("anomaly_flag"),
            "dominant_freq_hz": perception.get("dominant_freq_hz"),
            "trace_id":         chunk["trace_id"],
            "trace_continuity": trace_ok,
            "geo_lat":          geo_event.get("latitude"),
            "geo_lon":          geo_event.get("longitude"),
            "geo_zone":         geo_event.get("operational_zone"),
            "noise_type":       chunk.get("noise_type"),
        })

    # Save log
    log_path = os.path.join(BASE, "noisy_scenario_log.jsonl")
    with open(log_path, "w", encoding="utf-8") as f:
        for entry in log:
            f.write(json.dumps(entry) + "\n")

    print(f"\n  Results: {passed}/{len(scenarios)} PASS  {failed}/{len(scenarios)} FAIL")
    print(f"  Log saved: {log_path}")
    print("=" * 68)