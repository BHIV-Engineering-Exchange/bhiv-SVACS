# SVACS — Signal → Perception Integration + SNR Fix
## Complete Step-by-Step Execution Guide
**Author:** Nupur Gavane  
**Task:** Data Layer to Perception Bridge  
**Builds on:** Previous task (Perception Node + Pipeline Stability)

---

## What This Task Is 

The previous task built the perception node (FFT → classify → perception_event).  

**Three things to must deliver:**

| # | Deliverable | What's Broken Now | Fix |
|---|---|---|---|
| 1 | Realistic SNR values | `snr_db` is wrong (wrong formula, no per-vessel variation) | Use `10*log10(power)` + per-vessel noise scaling |
| 2 | Both `/ingest` + `/ingest/signal` endpoints | Only `/ingest/signal` exists | Add `/ingest` as an identical alias |
| 3 | Live signal→perception pipeline | Perception node runs offline only | Call it inside the server on every ingest |


---

## PHASE 1 — Fix SNR 

### The Bug

In `hybrid_signal_builder.py` line ~74, the current formula is:
```python
# WRONG — amplitude-based, ignores per-vessel signal strength differences
chunk["snr_db"] = round(float(20 * np.log10(
    (np.std(vessel_signal) + 1e-9) / (np.std(ocean_noise) + 1e-9)
)), 2)
```

This produces wrong values because:
- Submarine signals are very low amplitude (~0.05) → SNR comes out **negative**  
- All vessel types use the same noise level → no variation  
- `20*log10` is the amplitude formula; the task requires `10*log10` (power)

### The Fix

**Step 1.1 — Replace `hybrid_signal_builder.py`**

Copy `hybrid_signal_builder_fixed.py` → `services/data_layer/hybrid_signal_builder.py`  
(overwrite the existing file)

Key changes in the fixed version:

```python
# 1. Add this constant at top of file (after imports):
VESSEL_NOISE_SCALE = {
    "cargo":          0.443,   # target ~20 dB  (range: 15–25 dB)
    "speedboat":      0.606,   # target ~15 dB  (range: 10–20 dB)
    "submarine":      0.184,   # target  ~7 dB  (range:  5–10 dB)
    "low_confidence": 1.024,   # target  ~2 dB  (range:   <5 dB)
    "anomaly":        0.801,   # target ~12 dB  (variable)
}

# 2. In HybridSignalBuilder.build(), replace the noise + SNR lines:

# OLD (lines ~74-80 in original):
ocean_noise = self._get_noise_slice(len(vessel_signal))
hybrid = vessel_signal + ocean_noise
max_val = np.max(np.abs(hybrid)) or 1.0
hybrid = hybrid / max_val
chunk["noise_floor_db"] = round(float(20 * np.log10(np.std(ocean_noise) + 1e-9)), 2)
chunk["snr_db"] = round(float(20 * np.log10(
    (np.std(vessel_signal) + 1e-9) / (np.std(ocean_noise) + 1e-9)
)), 2)

# NEW :
ocean_noise_base = self._get_noise_slice(len(vessel_signal))
scale = VESSEL_NOISE_SCALE.get(vessel_type, 0.5)
ocean_noise = ocean_noise_base * scale
hybrid = vessel_signal + ocean_noise
max_val = np.max(np.abs(hybrid)) or 1.0
hybrid = hybrid / max_val

signal_power = float(np.mean(vessel_signal ** 2))
noise_power  = float(np.mean(ocean_noise  ** 2))
snr_db_val   = float(10 * np.log10((signal_power + 1e-9) / (noise_power + 1e-9)))
noise_floor_db_val = float(10 * np.log10(noise_power + 1e-9))

chunk["samples"]        = hybrid.tolist()
chunk["hybrid"]         = True
chunk["noise_floor_db"] = round(noise_floor_db_val, 2)
chunk["snr_db"]         = round(snr_db_val, 2)
```

**Step 1.2 — Verify the fix**

```bash
cd svacs-demo/services/data_layer
python hybrid_signal_builder.py
```

Expected output:
```
cargo           SNR=+19.8 dB   NoiseFloor=-25.9 dB
speedboat       SNR=+16.0 dB   NoiseFloor=-24.9 dB
submarine       SNR= +6.4 dB   NoiseFloor=-34.1 dB
low_confidence  SNR= +2.1 dB   NoiseFloor=-18.6 dB
anomaly         SNR=+11.3 dB   NoiseFloor=-20.7 dB
```

**Target ranges:**
- cargo: 15–25 dB ✓  
- speedboat: 10–20 dB ✓  
- submarine: 5–10 dB ✓  
- low_confidence: <5 dB ✓  
- anomaly: variable ✓  

---

## PHASE 2 — Dual Endpoint 

### What to do

Replace `api/ingestion_server/mock_server.py` with `mock_server_updated.py`.

The updated server adds:
- `POST /ingest` — new PRIMARY endpoint
- `POST /ingest/signal` — existing ALIAS (unchanged behaviour)
- Both routes call a shared `_handle_ingest()` function → **identical logic, identical responses**
- Latency measurement added per event
- `GET /perception_log` — new endpoint to inspect perception events

**Step 2.1 — Start the server**

```bash
# Terminal 1 — start server
python api/ingestion_server/mock_server.py
```

You should see:
```
[SERVER] Endpoints: POST /ingest  POST /ingest/signal  GET /health
[SERVER] Starting on: http://0.0.0.0:8000
```

**Step 2.2 — Test both endpoints manually**

```bash
# Terminal 2 — test that both endpoints return identical responses
cd services/data_layer
python -c "
import requests, sys
sys.path.insert(0, '.')
from hybrid_signal_builder import HybridSignalBuilder
b = HybridSignalBuilder()
chunk = b.build('cargo')

r1 = requests.post('http://localhost:8000/ingest', json=chunk)
r2 = requests.post('http://localhost:8000/ingest/signal', json=chunk)

print('PRIMARY  /ingest       :', r1.status_code, r1.json().get('status'))
print('ALIAS  /ingest/signal  :', r2.status_code, r2.json().get('status'))
print('Codes match:', r1.status_code == r2.status_code)
"
```

Expected:
```
PRIMARY  /ingest       : 200 ok
ALIAS  /ingest/signal  : 200 ok
Codes match: True
```

---

## PHASE 3 — Live Perception Connection (Hour 2.5–4)

The updated `mock_server.py` already calls `process_signal()` internally on every accepted chunk.  
The import path resolution handles both flat-layout and nested-layout repos automatically.

**What happens on each POST now:**

```
POST /ingest (or /ingest/signal)
  ↓
validate_chunk()
  ↓
process_signal(chunk)          ← perception_node called HERE
  ↓
write to perception_log.jsonl  ← transformation logged
  ↓
return { status, trace_id, perception_event }
```

**Step 3.1 — Confirm perception_node is importable from server location**

```bash
cd svacs-demo/api/ingestion_server
python -c "
import sys
sys.path.insert(0, '../../services/data_layer')
from perception_node import process_signal
print('Import OK')
"
```

If this fails, add a symlink or adjust the path in `mock_server.py` line ~25:
```python
_DATA_LAYER = os.path.join(os.path.dirname(_SERVER_DIR), "services", "data_layer")
```

**Step 3.2 — Send a test chunk and verify perception_event in response**

```bash
python -c "
import requests, sys
sys.path.insert(0, '../../services/data_layer')
from hybrid_signal_builder import HybridSignalBuilder
b = HybridSignalBuilder()
chunk = b.build('cargo')
r = requests.post('http://localhost:8000/ingest', json=chunk)
resp = r.json()
print('trace_id match:', resp.get('trace_id') == chunk['trace_id'])
print('perception_event:', resp.get('perception_event'))
"
```

Expected: `perception_event` with `vessel_type`, `confidence_score`, `dominant_freq_hz`, `anomaly_flag`.

---

## PHASE 4 — Full Transformation Log (Hour 4–5)

**Step 4.1 — Run the full integration script**

```bash
# Terminal 1: server must still be running
# Terminal 2:
cd svacs-demo/services/data_layer
python snr_perception_integration.py
```

This sends 15 chunks (3 per vessel type) and logs all transformations.

**Step 4.2 — Verify the log files exist**

```bash
ls api/ingestion_server/perception_log.jsonl
cat api/ingestion_server/perception_log.jsonl | head -5
```

Each line should look like:
```json
{
  "trace_id": "...",
  "input_vessel": "cargo",
  "predicted_vessel": "cargo",
  "confidence": 0.91,
  "dominant_freq": 120.5,
  "anomaly": false,
  "snr_db": 19.8,
  "latency_ms": 4.2
}
```

**Step 4.3 — Verify all 5 vessel types are in the log**

```bash
python -c "
import json
events = [json.loads(l) for l in open('services/data_layer/transformation_log.jsonl')]
for e in events:
    print(e['input_vessel'], '->', e['predicted_vessel'], '| conf:', e['confidence'])
"
```

---

## PHASE 5 — Latency Measurement (Hour 5–6)

Latency is measured in `snr_perception_integration.py` for each of the 15 events.

**Step 5.1 — Read latency from health endpoint**

```bash
curl http://localhost:8000/health
```

Response includes:
```json
{
  "avg_latency_ms": 4.2,
  "max_latency_ms": 11.8
}
```

**Step 5.2 — Check the integration runner output**

The `snr_perception_integration.py` output will show:
```
PHASE 5 — LATENCY REPORT
  Events measured  : 15
  Average latency  : X.X ms
  Max latency      : X.X ms
  Under 100ms      : 15/15
  Target (<100ms)  : PASS
```

**Target:** avg < 100ms, max < 100ms. With numpy FFT on 4000 samples, expect ~2–15ms typically.

---

