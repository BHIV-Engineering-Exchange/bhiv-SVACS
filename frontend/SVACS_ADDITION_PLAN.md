# SVACS — DATA ADDITION PLAN
**Sprint:** Dataset Truth Audit + System Mapping
**Auditor:** Nupur Gavane
**Date:** May 28, 2026

> Principle: No blind additions. Every item is evidence-based and prioritized by impact.

---

## Priority Legend

| Priority | Criteria |
|---|---|
|  P0 | Blocks correct operation or review survivability. Fix immediately. |
|  P1 | Significant gap. Add this sprint. |
|  P2 | Important for completeness. Next sprint. |
|  P3 | Nice to have. Backlog. |

---

## SECTION 1 — Signal Data Additions

###  P0 — Critical

| # | Item | Why Critical | Owner |
|---|---|---|---|
| ADD-001 | Real hydrophone test recordings (even 1–2 samples per vessel type) | All current signals are synthetic — reviewer will question real-world validity | Ankita / future |
| ADD-002 | Submarine 33Hz band — recalibrate classification boundary | Submarine at 33Hz falls outside 20-100Hz rule → classified as unknown. Needs boundary tuning or explicit rule | Nupur |

###  P1 — High Priority

| # | Item | Why Important | Owner |
|---|---|---|---|
| ADD-003 | Tanker-class vessel type (confirmed in Ankita's NICAI) | Ankita's system supports tanker-class but SVACS doesn't generate tanker signals | Nupur |
| ADD-004 | Fishing vessel signal type | Ankita confirmed fishing vessel supported in NICAI — SVACS needs to match | Nupur |
| ADD-005 | Patrol boat signal type | Ankita confirmed patrol patterns in NICAI | Nupur |
| ADD-006 | NOAA/USCG AIS sample integration | Ankita confirmed AIS samples integrated in NICAI — SVACS geo layer should align | Nupur + Ankita |

###  P2 — Medium Priority

| # | Item | Source | Notes |
|---|---|---|---|
| ADD-007 | Real ocean noise recordings | NOAA / oceanographic databases | Replace synthetic ocean noise with real recordings |
| ADD-008 | Weather-condition-specific noise profiles | Meteorological datasets | Improve weather_noise scenario realism |
| ADD-009 | Multi-vessel scenarios with 3+ vessels | Synthetic extension | Currently only 2-vessel overlap |

###  P3 — Low Priority

| # | Item | Notes |
|---|---|---|
| ADD-010 | Biologic event signal profiles (whales, schools of fish) | Would improve anomaly classification |
| ADD-011 | Equipment malfunction signal profiles | Would improve anomaly classification |
| ADD-012 | Jamming signal profiles | Advanced threat scenario |

---

## SECTION 2 — Infrastructure / Pipeline Additions

###  P0 — Critical

| # | Fix | Why Critical | Owner |
|---|---|---|---|
| INFRA-001 | Deploy NICAI to stable hosting (not ngrok) | ngrok drops unpredictably — system cannot run continuously | Ankita |
| INFRA-002 | Deploy State Engine to stable hosting (not ngrok) | Same issue | Raj |
| INFRA-003 | Ensure Render bucket stays warm (avoid cold-start timeouts) | Perception write timeouts break bucket chain | Soham/Siddhesh |

###  P1

| # | Fix | Why Important | Owner |
|---|---|---|---|
| INFRA-004 | Add real AIS geo coordinates to perception_event | All geo data currently simulated — Ankita working toward this | Ankita |
| INFRA-005 | Expose a stable live endpoint for Nikhil's dashboard | Timeline exports are JSONL file — needs a live API endpoint | Nupur |

---

## SECTION 3 — Schema / Metadata Gaps

| # | Gap | Impact | Fix | Priority |
|---|---|---|---|---|
| SCHEMA-001 | No `vessel_id` in signal_chunk (only in timeline builder) | Vessel tracking across multiple chunks needs stable ID | Add persistent vessel_id to signal generation |  P1 |
| SCHEMA-002 | No dataset version on synthetic signal specs | Cannot detect if calibration is outdated | Add calibration version to HybridSignalBuilder |  P2 |
| SCHEMA-003 | `cet_hash` not propagated if received | Tanvi's InsightFlow requirement | Add passthrough for cet_hash if present in incoming payload |  P1 |

---

## SECTION 4 — Classification Additions

| # | Gap | Fix | Priority |
|---|---|---|---|
| CLASS-001 | Submarine 33Hz boundary — classifies as unknown | Extend submarine rule to 20–110Hz OR add 30–40Hz dedicated low-freq rule |  P0 |
| CLASS-002 | Tanker-class vessels not supported | Add tanker signal profile + classification rule |  P1 |
| CLASS-003 | Fishing vessel not supported | Add fishing vessel profile |  P1 |
| CLASS-004 | Patrol boat not supported | Add patrol boat profile |  P1 |

---

## SECTION 5 — Today's P0 Action List

| # | Action | Owner | Status |
|---|---|---|---|
| 1 | Fix submarine 33Hz classification boundary | Nupur | PENDING |
| 2 | Add tanker/fishing/patrol vessel types to signal_generator.py | Nupur | PENDING |
| 3 | Coordinate with Ankita on AIS geo data integration | Nupur + Ankita | PENDING |
| 4 | Ask Ankita + Raj about stable hosting timeline | Nupur | PENDING |

---

*May 28, 2026*
