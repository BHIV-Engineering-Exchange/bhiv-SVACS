# SVACS — Image Validation Pack

**Author:** Nupur Gavane
**Sprint:** SVACS Operational Integration and Image Validation
**Scope:** Task 2 — Operational Image Validation
**Date:** August 2026
**Status:** Partial — see Runtime Validation Report for full chain status (Samachar and Bucket not covered by this pack)

---

## Purpose

This document records real-photograph test cases run through the SVACS Vision Runtime (`backend/`) image classification path, per Task 2 of the Operational Integration and Image Validation sprint. Each case records the original image, expected vessel (where known), identified class, confidence, evidence, and runtime trace, with an honest success/failure observation.

All tests below were run **locally, offline** (Wi-Fi disabled), against the retrained classifier checkpoint (epoch 19/49, classes: Container Ship, Fishing Vessel, LPG Carrier, Offshore Support Vessel, Oil Tanker, Passenger Ferry).

---

## Test Case Log

### Case 1
- **Image:** `osv_1.jpeg` — held-out test photo (not in training set), Offshore Support Vessel, near-eye-level, mobile phone capture
- **Expected vessel:** Offshore Support Vessel
- **Identified vessel/class:** Offshore Support Vessel
- **Confidence:** 98.93% (verbatim from `contract.json`)
- **Evidence:** Top predictions (verbatim) — 1. Offshore Support Vessel (98.93%), 2. Fishing Vessel (0.57%), 3. Passenger Ferry (0.33%). Bounding box covers full frame (0,0)–(960,1280).
- **Runtime trace:** `replay_id=16984279-c12c-41c9-8edb-b935b7bf4128`; confirmed present at `C:\tmp\svacs_replays\16984279-c12c-41c9-8edb-b935b7bf4128\` with `contract.json` and `metadata.json`; Stage 6 (Replay) OK; Bucket write attempted, failed HTTP 503 (Stage 7, non-fatal)
- **Result:** **PASS** — correct, high confidence, on a genuinely unseen image

### Case 2
- **Image:** `osv_2.jpeg` (Google-sourced), Offshore Support Vessel, near-eye-level angle
- **Expected vessel:** Offshore Support Vessel
- **Identified vessel/class:** Offshore Support Vessel
- **Confidence:** 79.5%
- **Evidence:** Top predictions — 1. Offshore Support Vessel (79.5%), 2. _skipped (18.6%)*, 3. Passenger Ferry (1.0%). Explanation: "Identified forward bridge and large open working deck."
- **Runtime trace:** trace_id logged in dashboard session; Replay saved
- **Result:** **PASS**, with caveat — a later re-run of an image with the same filename returned Passenger Ferry (77.8%) instead. This inconsistency was not root-caused before this pack was compiled; flagged as an open item (see Findings).
  \* *`_skipped` was a stray training-data artifact from an unlabeled folder that leaked into one training run; removed before the final retrain that produced the epoch-19 checkpoint used in Case 1 and subsequent cases.*

### Case 3
- **Image:** OSV photo sourced from Google, aerial/drone angle (steep overhead view)
- **Expected vessel:** Offshore Support Vessel
- **Identified vessel/class:** Passenger Ferry
- **Confidence:** Not recorded precisely (dashboard test, high confidence)
- **Evidence:** Detection succeeded (YOLO found the vessel); classifier misassigned type
- **Runtime trace:** Not retained
- **Result:** **FAIL** — attributed to camera-angle mismatch. All ~300 OSV training photos were mobile-phone captures taken at or near eye level; this test image was a steep aerial/drone shot, a viewpoint absent from training data. This is a genuine generalization gap, not a code defect.

### Case 4
- **Image:** `cordelia-cruise-2.jpeg` — Cordelia Cruises vessel (India-based short-cruise operator), bow-on angle
- **Expected vessel:** Cruise ship (Cordelia Cruises)
- **Identified vessel/class:** Passenger Ferry
- **Confidence:** 99.89% (verbatim, `?quick=true` run) — a separate, non-quick-mode run on an earlier date returned 87% for the same image
- **Evidence:** Top predictions (verbatim, quick-mode run) — 1. Passenger Ferry (99.89%), 2. Oil Tanker (0.04%), 3. LPG Carrier (0.03%). Bounding box covers full frame (0,0)–(1200,900). **Note:** `ocr_results` is empty (`[]`) in this specific replay record, because `?quick=true` skips OCR entirely (`vision_orchestrator.py` Stage 2: `ocr_results = [] if quick else ocr_service.extract_text(...)`). A separate, non-quick run of the same image on a different date did extract partial hull text (`'CORDEEA'`, a garbled read of "Cordelia") at ~31% OCR confidence — that result belongs to a different replay record, not this one.
- **Runtime trace:** `replay_id=f9f4f9cc-add9-4f16-b824-77f321853f1b`; confirmed present at `C:\tmp\svacs_replays\f9f4f9cc-add9-4f16-b824-77f321853f1b\`
- **Result:** **Expected miss, not a defect** — "Cruise Ship" is not currently a class in the retrained checkpoint (zero training images were available for it). The classifier correctly fell back to its nearest visual match (Passenger Ferry). This is a scope gap in the training data, not a classification error.

### Case 5 — pre-retrain baseline (for comparison only)
- **Image:** `ship1.jpeg`, colorful passenger ferry, near-eye-level
- **Expected vessel:** Passenger/tourist ferry
- **Identified vessel/class:** Cruise Ship
- **Confidence:** 13%
- **Evidence:** Detection succeeded; classifier running on **random, untrained weights** at time of this test (before `efficientnet_vessel_best.pth` was obtained/retrained)
- **Result:** **Not evaluable** — recorded only to document the difference between pre-retrain (meaningless output) and post-retrain (Cases 1–4) classifier behavior.

### Case 6
- **Image:** `20260722_145501.jpg`, distant cargo/bulk carrier, overcast/foggy conditions, broadside angle, far from camera
- **Expected vessel:** Bulk carrier / general cargo
- **Identified vessel/class:** Unknown (no detection)
- **Confidence:** 0.0%
- **Evidence:** YOLO returned zero bounding boxes above threshold at both primary (0.35) and fallback (0.25) confidence levels
- **Result:** **FAIL — detection stage, not classification.** Likely cause: the YOLO detector's own training set (`dataset/`, ~35 images) is small and may skew toward closer, clearer, front-facing shots; a distant, foggy, broadside vessel fell outside what it reliably recognizes as a vessel-shaped object.

---

## Summary Table

| Case | Vessel Type | Expected | Identified | Confidence | Result |
|---|---|---|---|---|---|
| 1 | OSV | OSV | OSV | 98.9% | PASS |
| 2 | OSV | OSV | OSV (inconsistent on re-run) | 79.5% | PASS, flagged |
| 3 | OSV (aerial) | OSV | Passenger Ferry | — | FAIL (angle gap) |
| 4 | Cruise ship | Cruise ship | Passenger Ferry | 87–99.9% | Expected miss (scope gap) |
| 5 | Passenger ferry | Ferry | Cruise Ship | 13% | Not evaluable (pre-retrain) |
| 6 | Bulk carrier | Cargo | Unknown | 0.0% | FAIL (detection miss) |

---

## Findings

1. **Offshore Support Vessel classification is reliable** on photos resembling the training data's style (mobile-phone, near-eye-level). This is the vessel type most likely to be photographed in the intended demo scenario (client's seaside window view).
2. **Camera angle is a real, unaddressed generalization gap.** All training photos share a narrow range of viewpoints (eye-level, mobile capture). Aerial/drone angles are not represented and reliably fail.
3. **Vocabulary gaps produce plausible-looking wrong answers, not errors.** Vessel types absent from training (Cruise Ship, Fishing Trawler, Chemical Tanker, general cargo/bulk carriers, AHTS as a formally distinct class from OSV) will always be misclassified as the nearest available class. This is a training-data scope limitation, not a defect in the pipeline.
4. **One unresolved inconsistency (Case 2)** — the same filename returned different classifications across two sessions. Not root-caused; needs further investigation (possible causes: different underlying files sharing a filename, or a difference between the `quick=true` code path and the full path used in earlier manual testing).
5. **Detection (YOLO) can fail outright** on distant, low-visibility, or unusual-angle photos (Case 6), independent of the classifier. The YOLO detector's own training set is very small (~35 images).

---

## Scope Note

This pack covers only the **Vision Runtime → classification** portion of the sprint's target chain. It does **not** cover Samachar ingestion (bypassed in the current local demo path) or confirmed Bucket storage (two live write attempts both failed with HTTP 503, Render cold-start). See the accompanying Runtime Validation Report for the full chain status.
