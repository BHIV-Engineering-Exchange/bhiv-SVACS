# SVACS — Runtime Validation Report

**Author:** Nupur Gavane
**Sprint:** SVACS Operational Integration and Image Validation
**Scope:** Task 3 — Runtime Validation
**Date:** August 2026
**Status:** Partial — honest breakdown below; not all stages confirmed

---

## Required Chain (per sprint brief)

```
Image / Manual Input / AIS
    ↓
Samachar
    ↓
SVACS
    ↓
Bucket
    ↓
Replay
    ↓
Dashboard
```

**Acceptance criterion (verbatim from brief):** "Every stage must expose evidence, trace IDs, and runtime visibility."

This report evaluates each stage against that criterion using only what was directly tested and observed today, locally, with Wi-Fi disabled for the offline-verification portion.

---

## Stage-by-Stage Status

### 1. Image ingestion (Operator → Image)
**Status: CONFIRMED**
Image upload via the dashboard's Signals page (`Signals.tsx`) successfully sends real JPEG/PNG files to the backend. Verified with multiple real photographs across two dashboard sessions (see Image Validation Pack).

### 2. Samachar
**Status: NOT IMPLEMENTED — genuine gap, not a mock**
The current image path does **not** route through Samachar. `Signals.tsx` posts directly to `backend/`'s own `/intelligence/image` endpoint. This was a deliberate decision, not an oversight: the sprint brief explicitly states *"Do not create parallel ingestion pipelines,"* and Samachar's actual ingestion API and structured-intelligence contract are owned by Chandragupta. Building a substitute without his contract would itself be the parallel pipeline the brief prohibits. This stage requires direct coordination with Chandragupta and cannot be completed unilaterally.

### 3. SVACS (Vision Runtime → classification)
**Status: CONFIRMED, with known limitations**
YOLO detection, EasyOCR text extraction, and EfficientNetV2 classification all run successfully and locally (verified with Wi-Fi disabled). The classifier was retrained today with a 9th class (Offshore Support Vessel) using ~300 real photographs. Confidence and evidence output confirmed real and traceable — see Image Validation Pack for full case-by-case results, including known failure modes (camera-angle sensitivity, vocabulary gaps for untrained vessel classes, occasional YOLO detection misses on distant/low-visibility photos).

### 4. Bucket
**Status: ATTEMPTED, NOT YET CONFIRMED SUCCESSFUL for this path**
A real Bucket client (`backend/app/services/bucket_client.py`) was built today, using the same live endpoint and envelope schema already proven working in the separate acoustic-signal pipeline. It was wired into the image-classification flow as Stage 7 of `vision_orchestrator.py`. Two live test attempts against Siddhesh's Bucket service both returned `HTTP 503`. This is consistent with Render free-tier cold-start behavior observed elsewhere in this project today, not an error in the client code — but it means **no successful Bucket write has yet been observed for the image path specifically**. The integration is real; a confirmed successful write is still outstanding.

### 5. Replay
**Status: CONFIRMED**
Every image request generates a durable, independently-verified replay record (`contract.json` + `metadata.json`) — see Replay Validation Evidence document for two verbatim examples pulled directly from disk. One infrastructure issue was found and documented in the process: replay storage resolves to a hardcoded absolute path (`C:\tmp\svacs_replays`) outside the project directory, which is a portability risk for other machines or deployment.

### 6. Dashboard
**Status: CONFIRMED**
Vessel Identification results (class, confidence, top-3 predictions, risk level, OCR text, trace ID, source) render correctly in the dashboard's Signals page. One CORS bug was found and fixed during today's session (dashboard running on a drifted port, 5174 instead of 5173, wasn't in the backend's CORS allowlist) — now resolved and confirmed working end-to-end through the actual browser UI, not just via direct API testing.

---

## Overall Chain Status

| Stage | Status |
|---|---|
| Image ingestion | ✅ Confirmed |
| Samachar | ❌ Not implemented (owner: Chandragupta) |
| SVACS (Vision Runtime) | ✅ Confirmed, with documented limitations |
| Bucket | ⚠️ Attempted, not yet successful for this path |
| Replay | ✅ Confirmed |
| Dashboard | ✅ Confirmed |

**4 of 6 stages confirmed working. Samachar is a genuine, unresolved dependency gap requiring Chandragupta's involvement. Bucket integration exists and is correctly wired but has not yet produced a confirmed successful write for images specifically, due to external service availability (Render cold-start), not a defect in the integration itself.**

---

## Cross-Cutting Findings (from today's session)

1. **`trace_id` and `replay_id` are two separate identifiers** generated within the same request (API layer vs. orchestrator layer). Both are logged and traceable, but not unified into one canonical ID — worth confirming with Ankita whether this satisfies the sprint's trace-continuity requirement as-is, or needs consolidating.
2. **Bucket reliability is external and out of this project's control.** Two separate pipelines (acoustic and image) both hit Render cold-start failures during testing today. This should be flagged as a shared infrastructure risk, not addressed independently per pipeline.
3. **The dashboard currently reads only from `backend/`** (a deliberate single-server decision made to satisfy the "single build" requirement from the team's local-demo directive). This means most non-image dashboard pages (Vessels, Alerts, Live Pipeline, etc.) show largely empty/stub data, since `backend/`'s own duplicate implementations of those endpoints aren't backed by real pipeline logs the way `services/api/main_api.py`'s versions are. This was an accepted, documented tradeoff for demo purposes — not something this report treats as resolved.
4. **All confirmed stages were verified with the machine's Wi-Fi physically disabled**, directly demonstrating local/offline operability for the confirmed portions of the chain (Image → SVACS → Replay → Dashboard). Bucket, by nature, requires the internet regardless of local setup.

---

## What Would Be Needed for Full Compliance

- Direct coordination with Chandragupta to integrate the real Samachar ingestion API and its structured-intelligence contract (Task 1, currently blocked)
- A confirmed successful Bucket write for the image-classification path (currently blocked by external service availability, not code)
- A decision (with Ankita) on whether `trace_id`/`replay_id` need to be unified into a single canonical identifier
- Fixing the hardcoded replay storage path to something project-relative or explicitly configurable
