"""
SVACS Hybrid Signal Builder  (SNR-FIXED)
=========================================
CHANGES vs previous version:
  1. SNR formula changed from 20*log10(amplitude) → 10*log10(power)
     This is the correct formula per the task spec.
  2. Per-vessel noise_scale applied BEFORE mixing.
     This ensures each vessel type hits its target SNR range:
       cargo          → ~20 dB  (range: 15-25)
       speedboat      → ~15 dB  (range: 10-20)
       submarine      →  ~7 dB  (range:  5-10)
       low_confidence →  ~2 dB  (range:   <5)
       anomaly        → ~12 dB  (variable)

Layer model:
    scaled_noise  = ocean_noise * NOISE_SCALE[vessel_type]
    final_signal  = vessel_signal + scaled_noise
    snr_db        = 10 * log10( mean(vessel^2) / mean(noise^2) )
"""

import numpy as np
import time
import os


# ─────────────────────────────────────────────────────────────────────────────
# Per-vessel noise scale — calibrated to hit task-specified SNR target ranges.
# Higher scale = more noise added = lower SNR.
# DO NOT change without re-running SNR calibration.
# ─────────────────────────────────────────────────────────────────────────────
VESSEL_NOISE_SCALE = {
    "cargo":          0.443,   # target ~20 dB  (range: 15–25 dB)
    "ferry":          0.443,
    "cruise":         0.300,   # cleaner signal
    "roro":           0.500,   # slightly noisier
    "passenger":      0.400,   # passenger boat
    "speedboat":      0.606,   # target ~15 dB  (range: 10–20 dB)
    "submarine":      0.184,   # target  ~7 dB  (range:  5–10 dB)
    "low_confidence": 1.024,   # target  ~2 dB  (range:   <5 dB)
    "anomaly":        0.801,   # target ~12 dB  (variable)
}


class OceanNoiseGenerator:
    def __init__(self, sample_rate: int = 4000, seed: int = None):
        self.sample_rate = sample_rate
        self.rng = np.random.default_rng(seed)

    def generate(self, n_samples: int) -> np.ndarray:
        t          = np.arange(n_samples) / self.sample_rate
        background = self.rng.normal(0, 0.25, n_samples)
        swell_freq = self.rng.uniform(0.1, 1.0)
        swell      = 0.08 * np.sin(2 * np.pi * swell_freq * t)
        tonal_freq = self.rng.uniform(50, 150)
        tonal      = 0.05 * np.sin(2 * np.pi * tonal_freq * t)
        bio_freq   = self.rng.uniform(200, 800)
        bio        = 0.04 * np.sin(2 * np.pi * bio_freq * t)
        ocean      = background + swell + tonal + bio
        peak       = np.max(np.abs(ocean)) or 1.0
        return ocean / peak * 0.4


class HybridSignalBuilder:
    def __init__(self, sample_rate: int = 4000, duration: float = 1.0,
                 noise_file: str = None, seed: int = None):
        from signal_generator import SignalGenerator
        self.generator   = SignalGenerator(sample_rate=sample_rate, duration=duration, seed=seed)
        self.ocean       = OceanNoiseGenerator(sample_rate=sample_rate, seed=seed)
        self.noise_file  = noise_file
        self._real_noise_cache = None
        if noise_file and os.path.exists(noise_file):
            self._load_real_noise(noise_file)

    def _load_real_noise(self, path: str):
        try:
            import scipy.io.wavfile as wav
            rate, data = wav.read(path)
            if data.ndim > 1:
                data = data[:, 0]
            data = data.astype(np.float32)
            data /= np.max(np.abs(data)) or 1.0
            self._real_noise_cache = (rate, data)
            print(f"[HybridBuilder] Loaded real noise: {path} ({rate} Hz, {len(data)} samples)")
        except Exception as exc:
            print(f"[HybridBuilder] Could not load noise file ({exc}). Using synthetic noise.")

    def _get_noise_slice(self, n_samples: int) -> np.ndarray:
        if self._real_noise_cache is not None:
            rate, data = self._real_noise_cache
            if len(data) >= n_samples:
                start = np.random.randint(0, len(data) - n_samples)
                return data[start: start + n_samples]
        return self.ocean.generate(n_samples)

    def build(self, vessel_type: str, scenario_id: int = None) -> dict:
        """
        Build a hybrid signal chunk with pipeline-ready schema.

        FIXED SNR computation:
          1. Apply per-vessel noise_scale to ocean noise (controls SNR level)
          2. Mix vessel + scaled_noise
          3. Normalize final hybrid signal to [-1, 1]
          4. Compute SNR = 10 * log10(signal_power / noise_power)  ← POWER formula
        """
        chunk = self.generator.generate_chunk(vessel_type, scenario_id=scenario_id)

        vessel_signal = np.array(chunk["samples"])

        # Step 1: Get base ocean noise
        ocean_noise_base = self._get_noise_slice(len(vessel_signal))

        # Step 2: Scale noise per vessel type to hit target SNR range
        scale       = VESSEL_NOISE_SCALE.get(vessel_type, 0.5)
        ocean_noise = ocean_noise_base * scale

        # Step 3: Mix
        hybrid  = vessel_signal + ocean_noise
        max_val = np.max(np.abs(hybrid)) or 1.0
        hybrid  = hybrid / max_val

        # Step 4: Compute SNR using POWER formula (10*log10, not amplitude)
        #   SNR = 10 * log10( E[vessel^2] / E[noise^2] )
        #   NOTE: uses pre-normalization signals for true SNR measurement
        signal_power = float(np.mean(vessel_signal ** 2))
        noise_power  = float(np.mean(ocean_noise  ** 2))
        snr_db_val   = float(10 * np.log10((signal_power + 1e-9) / (noise_power + 1e-9)))

        # noise_floor_db: level of the noise floor (power-referenced to 1)
        noise_floor_db_val = float(10 * np.log10(noise_power + 1e-9))

        chunk["samples"]        = hybrid.tolist()
        chunk["hybrid"]         = True
        chunk["noise_floor_db"] = round(noise_floor_db_val, 2)
        chunk["snr_db"]         = round(snr_db_val, 2)

        return chunk

    def build_batch(self, vessel_type: str, n: int = 10) -> list:
        return [self.build(vessel_type) for _ in range(n)]


if __name__ == "__main__":
    builder = HybridSignalBuilder(seed=7)
    print(f"\n{'TYPE':<16}  {'SNR_DB':>8}  {'NOISE_FLOOR_DB':>14}  {'TRACE_ID':>10}")
    print("─" * 58)
    for vtype in ["cargo", "speedboat", "submarine", "low_confidence", "anomaly"]:
        chunk = builder.build(vtype)
        s     = chunk["samples"]
        print(
            f"[{vtype:<16}]  "
            f"SNR={chunk['snr_db']:+6.1f} dB  "
            f"NoiseFloor={chunk['noise_floor_db']:+6.1f} dB  "
            f"trace={chunk['trace_id'][:8]}..."
        )