# SVACS — DATA AUDIT REPORT
**Sprint:** Dataset Truth Audit + System Mapping
**Auditor:** Nupur Gavane
**Date:** May 28, 2026
**Status:**  COMPLETE — Evidence-based from confirmed pipeline runs

---

## 1. Audit Objective

Establish factual ground truth about what data exists in SVACS, what the system can and cannot do, and where risks remain.

---

## 2. Storage Locations — CONFIRMED

| Location | Type | Path | Status | Role |
|---|---|---|---|---|
| Signal generation | Runtime (in-memory) | `services/data_layer/` | LIVE | Generates vessel acoustic signals |
| Pipeline logs | JSONL flat files | `services/data_layer/*.jsonl` | LIVE | Full pipeline audit trail |
| Bucket (artifact storage) | REST API — Render | `https://bhiv-bucket.onrender.com` | LIVE | Append-only artifact chain |
| Execution observability | JSONL | `execution_observability.jsonl` | LIVE | Unified pipeline event log |
| Incident timelines | JSONL | `incident_timelines.jsonl` | LIVE | UI-ready timeline exports |

---

## 3. Signal Dataset Inventory

### 3.1 Vessel Signal Types

| Vessel Type | Frequency Band | SNR Target | Amplitude | Classification Status |
|---|---|---|---|---|
| `cargo` | 50–200 Hz | 15–25 dB | High stable | CONFIRMED WORKING |
| `speedboat` | 500–1500 Hz | 10–20 dB | High irregular + 2nd harmonic | CONFIRMED WORKING |
| `submarine` | 20–100 Hz (low energy) | 5–10 dB | Low masked (stealth design) | CONFIRMED (boundary case at 33Hz) |
| `low_confidence` | 80–600 Hz buried | <5 dB | Very low — noise dominated | CONFIRMED WORKING |
| `anomaly` | 10–2000 Hz multi-peak | Variable | Multi-peak + burst spikes | CONFIRMED WORKING |

### 3.2 Signal Generation Stack

| Component | File | Role | Status |
|---|---|---|---|
| Pure signal generator | `signal_generator.py` | Creates clean vessel acoustic profiles | CONFIRMED |
| Ocean noise mixer | `hybrid_signal_builder.py` | Adds realistic ocean background | CONFIRMED |
| Noise scaling | `VESSEL_NOISE_SCALE` dict | Per-vessel SNR calibration | CONFIRMED |
| Scenario builder | `scenario_builder.py` | Saves 5 named scenario JSONs | CONFIRMED |
| Noisy scenario builder | `noisy_scenario_builder.py` | 6 noise types, 12 scenarios | CONFIRMED |

### 3.3 Noisy Scenario Inventory

| Scenario | Seed | Count | Result |
|---|---|---|---|
| `ocean_noise` | 42 | 3 | 3/3 PASS |
| `weather_noise` | 42 | 2 | 2/2 PASS |
| `sensor_dropout` | 42 | 2 | 2/2 PASS |
| `multi_vessel_overlap` | 42 | 2 | 2/2 PASS |
| `ais_inconsistency` | 42 | 1 | 1/1 PASS |
| `anomaly_injection` | 42 | 2 | 2/2 PASS |
| **Total** | | **12** | **12/12 PASS** |

### 3.4 AIS-Derived Data (Ankita's NICAI — confirmed)

Ankita confirmed NICAI now has:
- NOAA/USCG AIS samples for runtime grounding
- Additional vessel types: tanker-class, fishing vessel, patrol patterns
- Real AIS-backed coordinates for cargo/fishing/commercial patterns
- Operational anomaly scenarios (piracy, smuggling, sensor deception)

---

## 4. Pipeline Stage Coverage — CONFIRMED

| Stage | Owner | Technology | Status | Last Verified |
|---|---|---|---|---|
| Signal generation | Nupur | Python / numpy | LIVE | 21/05/2026 |
| FFT + perception | Nupur | `numpy.fft.rfft` | LIVE | 21/05/2026 |
| NICAI intelligence | Ankita | FastAPI + ngrok | LIVE | 21/05/2026 |
| State Engine | Raj Prajapati | FastAPI + ngrok | LIVE | 21/05/2026 |
| Bucket storage | Soham/Siddhesh | Render hosted | LIVE | 21/05/2026 |
| Replay engine | Nupur | Python log reader | LIVE | 09/05/2026 |
| Observability | Nupur | Python JSONL logger | LIVE | 15/05/2026 |

---

## 5. Log Files Inventory

| File | Contents | Status | Size |
|---|---|---|---|
| `full_pipeline_log.jsonl` | Complete pipeline run per chunk | LIVE | Growing |
| `execution_observability.jsonl` | All pipeline events unified | LIVE | Growing |
| `bucket_verification_log.jsonl` | Write/read/hash results | LIVE | Growing |
| `incident_timelines.jsonl` | UI-ready timelines | LIVE | 5 exported |
| `replay_log.jsonl` | Lifecycle reconstructions | LIVE | 5 replays |
| `noisy_pipeline_log.jsonl` | Noisy scenario runs | LIVE | 12 scenarios |
| `noisy_scenario_log.jsonl` | Standalone scenario results | LIVE | 12 entries |
| `trace_log.jsonl` | Signal ingestion trace | LIVE | Growing |
| `transformation_log.jsonl` | Signal→perception transforms | LIVE | Growing |

---

## 6. Critical Findings

| # | Finding | Severity | Evidence |
|---|---|---|---|
| FIND-001 | Submarine at 33Hz boundary → classifies as `unknown` |  Medium | 5-trace proof + noisy scenarios. Expected behavior — documented |
| FIND-002 | Bucket Render cold-start causes occasional perception write timeouts | Medium | Pipeline run logs — intelligence/state writes succeed consistently |
| FIND-003 | Ankita's NICAI schema has additional fields not in SVACS output | Medium | Ankita's direct reply — NICAI enriches on its side, no schema change needed |
| FIND-004 | No real AIS coordinates — all geo data simulated | Medium | geo_event_schema.json note, Ankita confirmed gap |
| FIND-005 | NICAI and Raj servers are ngrok-based — not always on | Medium | Multiple runs across days — coordination required |

---

## 7. Evidence Artifacts

| Artifact | Source | Status |
|---|---|---|
| `full_pipeline_log.jsonl` | Pipeline runs | PRESENT |
| `bucket_verification_log.jsonl` | Bucket runs | PRESENT |
| `noisy_scenario_log.jsonl` | Noisy scenario runs | PRESENT |
| `5_trace_cases.json` | 5-case trace proof for Raj | PRESENT |
| Ankita direct reply | Ankita Prajapati | RECEIVED |
| Shravani direct reply | Shravani Harde (N/A for SVACS) | RECEIVED for Namami Gange |

---

*May 28, 2026*
