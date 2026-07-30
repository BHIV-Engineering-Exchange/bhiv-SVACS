# SVACS — DATA READINESS & RISK REPORT
**Sprint:** Dataset Truth Audit + System Mapping
**Auditor:** Nupur Gavane
**Date:** May 28, 2026

---

## 1. Assessment Objective

Determine whether SVACS's current data and pipeline can support operational use correctly. Identify where the system will fail, give wrong answers, or fail silently.

---

## 2. Capability Assessment

### 2.1 Core Pipeline Readiness

| Scenario | Ready? | Confidence | Risk |
|---|---|---|---|
| Classify cargo vessel (clean) | YES | High | LOW |
| Classify speedboat (clean) | YES | Medium-High | LOW |
| Classify submarine (clean, high SNR) | YES | Medium | MEDIUM |
| Classify submarine (noisy, 33Hz) | outputs unknown + CRITICAL | Correct safe-fail | MEDIUM |
| Detect anomalous signal | YES | High | LOW |
| Detect AIS spoofing | YES | High | LOW |
| Run under ocean noise | YES | Confirmed 3/3 | LOW |
| Run under weather noise | YES | Confirmed 2/2 | LOW |
| Run under sensor dropout | YES | Confirmed 2/2 | LOW |
| Run 24/7 continuously | NO | None | ngrok-based servers |
| Classify tanker/fishing/patrol vessels | NO | None | Not in signal_generator.py |

### 2.2 Data Integrity Readiness

| Check | Ready? | Evidence |
|---|---|---|
| Trace continuity across full pipeline | YES | 17/17 ALL MATCH |
| Append-only tamper-proof storage | YES | hash_match 5/5, chain_verified |
| Deterministic replay | YES | seed=42, 12/12 identical |
| No silent failures | YES | All errors structured |
| Full lifecycle reconstruction | YES | operator_replay_engine.py |

### 2.3 Integration Readiness

| Integration | Ready? | Risk | Notes |
|---|---|---|---|
| Ankita (NICAI) | LIVE | Medium | ngrok-based — not always on |
| Raj (State Engine) | LIVE | Medium | ngrok-based — coordination required |
| Soham/Siddhesh (Bucket) | LIVE | Medium | Render cold-start timeouts on perception |
| Nikhil (UI) | PARTIAL | High | Timeline schema confirmed — no live endpoint yet |
| Tanvi (InsightFlow) | ALIGNED | Low | Append-only observability confirmed |

---

## 3. High-Risk Failure Points

| ID | Failure | Trigger | Impact | Fix |
|---|---|---|---|---|
| FAIL-001 | NICAI not connected | Ankita's ngrok drops | Pipeline cannot proceed past perception | Deploy NICAI to stable hosting |
| FAIL-002 | State Engine not connected | Raj's ngrok drops | intelligence_event cannot be processed | Deploy State Engine to stable hosting |
| FAIL-003 | Bucket cold-start timeout | Render free-tier sleep | Perception write fails occasionally | Keep Render warm / upgrade tier |
| FAIL-004 | Unknown vessel type input | Caller sends unsupported type | `ValueError` raised in signal_generator.py | Add input validation + error handling |
| FAIL-005 | Tanker/fishing/patrol vessel | Real deployment sends these | System has no rule — classifies as unknown | Add new vessel types |

---

## 4. Silent Correctness Risks

| ID | Risk | How It Happens | Detection |
|---|---|---|---|
| SILENT-001 | Submarine classified as cargo | Both at 50-100Hz, cargo's energy threshold not met precisely | Run with varied energy levels — check classification |
| SILENT-002 | Wrong risk level from NICAI | Ankita's server has schema evolution | Check validation_status + risk_level fields on every response |
| SILENT-003 | Bucket hash mismatch not caught | read_from_bucket returns wrong payload | `hash_match` field in verify_bucket() output — always check |
| SILENT-004 | trace_id changed by NICAI | Regression in Ankita's code | verify_trace_continuity() — always check `all_match` field |

---

## 5. Retrieval / Classification Ambiguity Risks

| ID | Ambiguity | Example | Risk | Fix |
|---|---|---|---|---|
| AMB-001 | Submarine / cargo overlap at 50-100Hz | Both vessel types produce signals in this range — energy is the only differentiator | High | Energy threshold tuning + documentation |
| AMB-002 | Anomaly vs speedboat | Multi-peak anomaly may have dominant freq in speedboat band | Medium | Anomaly check runs before vessel classification |
| AMB-003 | Low confidence vs any vessel type | Very low SNR makes any vessel type unclassifiable | Medium | Low confidence is explicit output — not ambiguous |

---

## 6. Dataset Insufficiency Risks

| ID | Gap | Impact | Fix |
|---|---|---|---|
| INSUF-001 | No real hydrophone data | Synthetic signals may not match real ocean conditions | Acquire real recordings |
| INSUF-002 | No tanker/fishing/patrol vessel profiles | These vessel types classified as unknown | Add signal profiles |
| INSUF-003 | Geo coordinates are simulated | Nikhil's map cannot show real positions | Real AIS integration (Ankita's roadmap) |

---

## 7. Overall Readiness Score

| Dimension | Score (1–10) | Evidence |
|---|---|---|
| Classification accuracy (synthetic) | 9/10 | 17/17 PASS, honest boundary behavior |
| Classification accuracy (real data) | Unknown | No real hydrophone data |
| Pipeline trace continuity | 10/10 | 17/17 ALL MATCH |
| Data integrity (bucket) | 9/10 | hash_match 5/5, minor cold-start |
| Operational continuity (24/7) | 4/10 | ngrok-based — not stable |
| Vessel type coverage | 6/10 | 5 types, missing tanker/fishing/patrol |
| Geospatial accuracy | 3/10 | Simulated only |
| **OVERALL** | **7/10** | **Strong for controlled demos, not production** |

---

## 8. Priority Fix List

| Priority | Fix | Fixes Which Risks |
|---|---|---|
| P0 | Recalibrate submarine 33Hz boundary | AMB-001, classification accuracy |
| P0 | Deploy NICAI + State Engine to stable hosting | FAIL-001, FAIL-002 |
| P1 | Add tanker/fishing/patrol vessel profiles | FAIL-005, INSUF-002 |
| P1 | Add real AIS geo coordinates | INSUF-003 |
| P1 | Create live API endpoint for Nikhil's dashboard | Integration gap |
| P2 | Acquire real hydrophone test data | INSUF-001 |
| P2 | Upgrade Render bucket tier to eliminate cold-starts | FAIL-003 |

---

*May 28, 2026 — Built from confirmed pipeline evidence + Ankita's direct reply*
