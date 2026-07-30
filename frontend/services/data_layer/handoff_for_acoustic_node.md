# Signal Layer Handoff — Acoustic Node
**From:** Nupur Gavane (Signal Layer / Data Layer)
**Date:** 28/04/2026
**Status:** READY — Signal layer fully validated. Awaiting your build completion.

---

## Endpoint
- **Method:** POST
- **URL:** `http://localhost:8000/ingest/signal`
- **Content-Type:** `application/json`
- **Schema:** `shared/schemas/signal_chunk_schema.json`

---

## Key Fields Your Parser Must Read

| Field | Type | Notes |
|---|---|---|
| `samples` | array of 4000 floats | Raw acoustic signal, normalized to [-1, 1] |
| `sample_rate` | int | Always 4000 Hz |
| `trace_id` | UUID4 string | **COPY THIS to your output. Do NOT generate a new one.** |
| `vessel_type` | string | cargo / speedboat / submarine / low_confidence / anomaly |
| `expected_label.anomaly_flag` | bool | True ONLY for anomaly (scenario 5) |
| `snr_db` | float | Signal-to-noise ratio in dB |
| `metadata.freq_hz` | float OR "mixed" |  See warning below |

---

##  Critical: anomaly freq_hz is a String

For `vessel_type = "anomaly"`, `metadata.freq_hz` is the string `"mixed"` — not a number.

**This will crash your parser if you do:**
```python
freq = float(chunk["metadata"]["freq_hz"])  # ValueError for anomaly!
```

**Safe pattern:**
```python
freq_hz = chunk["metadata"].get("freq_hz")
if isinstance(freq_hz, (int, float)):
    freq = float(freq_hz)
else:
    freq = None  # anomaly — multi-peak, no single dominant frequency
```

---

## trace_id Rule (CRITICAL)

- Generated fresh per chunk via `uuid.uuid4()`
- Present on **every** POST body, never null
- Server returns it unchanged: `{"status": "ok", "trace_id": "..."}`
- **You must copy it to your output — do NOT generate a new UUID**

The same `trace_id` must flow: `signal → perception → intelligence → state → UI`

**Quick verification once you're connected:**
```python
import requests
from hybrid_signal_builder import HybridSignalBuilder
chunk = HybridSignalBuilder(4000, 1.0).build("cargo")
r = requests.post("http://localhost:8000/ingest/signal", json=chunk)
assert r.json()["trace_id"] == chunk["trace_id"], "TRACE MISMATCH"
print("TRACE CONFIRMED:", chunk["trace_id"][:8])
```

---

## FFT Classification Bands

| Vessel Type | Frequency Range | Confidence Expected |
|---|---|---|
| cargo | 50 – 200 Hz | high |
| speedboat | 500 – 1500 Hz | medium_high |
| submarine | 20 – 100 Hz | medium (low energy, near noise floor) |
| low_confidence | any | low (noise-dominated) |
| anomaly | multi-peak | unknown → flag it |

---

## Import Path (Python)

```python
import sys
sys.path.insert(0, "services/data_layer")
from hybrid_signal_builder import HybridSignalBuilder

builder = HybridSignalBuilder(sample_rate=4000, duration=1.0)
chunk = builder.build("cargo")  # pipeline-ready dict
```

Or use pre-generated samples in `services/data_layer/example_outputs/` for offline testing.

---

## What You Must Output (perception_event)

```json
{
  "trace_id": "<same as input — copy, do not regenerate>",
  "vessel_type": "cargo",
  "confidence": 0.94,
  "dominant_freq_hz": 194.0,
  "anomaly_flag": false
}
```

---

## This signal output has been validated for schema correctness
## and is ready for downstream consumption.