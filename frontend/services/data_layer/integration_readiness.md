# Integration Readiness Report — Signal Layer
**Author:** Nupur Gavane
**Date:** 28/04/2026
**Component:** `services/data_layer/` + `api/ingestion_server/mock_server.py`
**Status:**  READY FOR DOWNSTREAM INTEGRATION

---

## Endpoint
| Field | Value |
|---|---|
| Method | POST |
| URL | `http://localhost:8000/ingest/signal` |
| Content-Type | `application/json` |
| Schema | `shared/schemas/signal_chunk_schema.json` |

---

## Schema Contract (Guaranteed Fields)

Every chunk posted to `/ingest/signal` is guaranteed to contain:

| Field | Type | Notes |
|---|---|---|
| `trace_id` | UUID4 string | Fresh per chunk. Never null. Never missing. |
| `timestamp` | float | Unix epoch |
| `samples` | array of 4000 floats | Normalized to [-1, 1] |
| `sample_rate` | int | Always 4000 Hz |
| `vessel_type` | string | One of: cargo / speedboat / submarine / low_confidence / anomaly |
| `expected_label.anomaly_flag` | bool | True ONLY for scenario 5 (anomaly) |
| `snr_db` | float | Signal-to-noise ratio in dB |
| `noise_floor_db` | float | Ocean noise floor estimate |
| `metadata.freq_hz` | number OR "mixed" | "mixed" for anomaly type only |

---

## Self-Validation Results

All 5 vessel types tested against 6 checks simulating Acoustic Node parsing:

| Vessel Type | Samples | trace_id | anomaly_flag | Classifiable | Result |
|---|---|---|---|---|---|
| cargo | 4000  | UUID4  | False  | Yes  | PASS |
| speedboat | 4000  | UUID4  | False  | Yes  | PASS |
| submarine | 4000  | UUID4  | False  | Yes  | PASS |
| low_confidence | 4000  | UUID4  | False  | Yes  | PASS |
| anomaly | 4000  | UUID4  | True  | Yes  | PASS |

Full output: `services/data_layer/day2_integration_log.txt`
Structured results: `services/data_layer/day2_integration_results.json`

---

## Frequency Bands (For Acoustic Node FFT Parser)

| Vessel Type | Dominant Freq Range | `metadata.freq_hz` type | Notes |
|---|---|---|---|
| cargo | 50 – 200 Hz | float | Clean single peak |
| speedboat | 500 – 1500 Hz | float | Includes 2nd harmonic |
| submarine | 20 – 100 Hz | float | Low energy, may be near noise floor |
| low_confidence | 80 – 600 Hz | float | Signal buried in noise |
| anomaly | multi-peak | **"mixed"** (string) | Parser must handle non-numeric value |

>  **Important for Acoustic Node parser:** `metadata.freq_hz` is the string `"mixed"` 
> for anomaly signals. Do NOT cast this field to float without checking type first.

---

## trace_id Contract

- Generated via `uuid.uuid4()` — fresh per chunk
- Present on **every** POST body
- Returned unchanged in server response: `{"status": "ok", "trace_id": "..."}`
- Downstream rule: **copy from input, do not generate a new one**

Quick verification snippet (run once connected):
```python
import requests
from hybrid_signal_builder import HybridSignalBuilder
chunk = HybridSignalBuilder(4000, 1.0).build("cargo")
r = requests.post("http://localhost:8000/ingest/signal", json=chunk)
assert r.json()["trace_id"] == chunk["trace_id"], "TRACE MISMATCH"
print("TRACE CONFIRMED:", chunk["trace_id"][:8])
```

---

## Import Path (If Acoustic Node Uses Python)

```python
# From svacs-demo root:
import sys
sys.path.insert(0, "services/data_layer")
from hybrid_signal_builder import HybridSignalBuilder

builder = HybridSignalBuilder(sample_rate=4000, duration=1.0)
chunk = builder.build("cargo")   # returns pipeline-ready dict
```

Or use the pre-generated samples in `services/data_layer/example_outputs/` for offline testing.

---

## Risk Assessment

| Risk | Severity | Status |
|---|---|---|
| Schema mismatch with Acoustic Node | Low | Schema is fixed and documented |
| `freq_hz = "mixed"` causing parse error | Medium | Documented above — parser must handle string |
| trace_id dropped downstream | High | Explicitly documented — copy, don't regenerate |
| Sample count mismatch | None | Always exactly 4000 floats |

---

## Blocking Issues from Signal Layer
**None.** Signal layer is stable, validated, and ready.

Acoustic Node integration is pending on their build completion — not on any unresolved issue from this layer.
