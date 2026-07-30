# SVACS — COVERAGE MATRIX
**Sprint:** Dataset Truth Audit + System Mapping
**Auditor:** Nupur Gavane
**Date:** May 28, 2026

---

## SECTION A — Classification Coverage

| Input Vessel | Clean Signal | Ocean Noise | Weather Noise | Sensor Dropout | Multi-Vessel | AIS Spoof |
|---|---|---|---|---|---|---|
| cargo |  cargo |  cargo |  cargo |  cargo |  cargo | N/A |
| speedboat |  speedboat |  speedboat |  speedboat | N/A |  speedboat | N/A |
| submarine |  submarine (clean) /  unknown (33Hz) |  submarine | unknown + anomaly |  submarine |  unknown + anomaly |  submarine (acoustic truth beats AIS) |
| low_confidence |  unknown (correct) | N/A | N/A | N/A | N/A | N/A |
| anomaly |  unknown + anomaly | N/A | N/A | N/A | N/A |  anomaly injected |

**Total classification scenarios tested: 17 (5 standard + 12 noisy)**
**All 17 PASS — trace continuity confirmed on all**

---

## SECTION B — Pipeline Stage Coverage

| Stage | Standard Run | Noisy Run | Bucket Verified | Replay Available |
|---|---|---|---|---|
| Signal generation | 5/5 | 12/12 | N/A | YES |
| Perception (FFT) | 5/5 | 12/12 | PASS | YES |
| NICAI intelligence | 5/5 ALLOW | 12/12 | PASS | YES |
| State Engine | 5/5 OK | 12/12 OK | PASS | YES |
| Bucket storage | 5/5 PASS | N/A | hash_match | chain_verified |

---

## SECTION C — Operator Intelligence Coverage

| Capability | File | Status |
|---|---|---|
| Replay any trace_id | `operator_replay_engine.py` | 5/5 reconstructed |
| Plain-English explanation | `intelligence_explainer.py` | All scenarios |
| Incident timeline for UI | `incident_timeline_builder.py` | 5 timelines exported |
| Geospatial enrichment | `geo_injector.py` | All events enriched |
| Vessel knowledge base | `vessel_registry.json` | 6 vessel types documented |
| Unified observability | `execution_observability.py` | 7 event types logged |

---

## SECTION D — Risk Coverage by Vessel Type

| Vessel | NICAI Risk Level | Validation | Anomaly Flag | Notes |
|---|---|---|---|---|
| cargo (clean) | LOW | ALLOW | False | Normal — no escalation |
| speedboat | HIGH / CRITICAL | ALLOW | Varies | High-frequency pattern triggers escalation |
| submarine (clean) | CRITICAL | ALLOW | False | High risk by vessel class |
| submarine (noisy/33Hz) | CRITICAL | ALLOW | True | Unknown + anomaly → CRITICAL correct escalation |
| low_confidence | CRITICAL | ALLOW | True | Buried signal → always escalated |
| anomaly | CRITICAL | ALLOW | True | Always CRITICAL |

---

## SECTION E — Data Gap Coverage

| Gap | Severity | Workaround | Future Fix |
|---|---|---|---|
| No real AIS coordinates | Medium | Simulated Indian Ocean zones | Ankita working toward live AIS |
| Submarine 33Hz boundary | Medium | Documented — `unknown` + CRITICAL correct | Increase classification bands (needs tuning) |
| No real noisy sensor datasets | Medium | Deterministic synthetic noise (seed=42) | Real hydrophone data acquisition |
| ngrok-based teammate servers | Medium | Coordinate before running pipeline | Deploy to stable hosting |

---

*May 28, 2026*
