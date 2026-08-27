# SVACS — Testing Packet

**Author:** Nupur Gavane
**Sprint:** SVACS Operational Integration and Image Validation
**Date:** August 2026
**Note:** No `TESTING_PACKET.md` existed anywhere in this repository prior to this sprint; this is a new document, not an update.

---

## Purpose

This packet documents *how* today's testing was carried out — environment, tools, methodology, and a consolidated pass/fail summary across every test performed during this sprint. Case-by-case image results are in the Image Validation Pack; raw replay artifacts are in Replay Validation Evidence; this document is the connecting reference for both.

---

## Test Environment

- **Machine:** Local development machine (Windows), no cloud/VM involved
- **Python:** 3.11, separate virtual environments for `backend/` and `frontend/`
- **Node/npm:** for the React dashboard (`frontend/`)
- **Network condition for offline verification:** Wi-Fi and Ethernet physically disabled for the specific offline-capability test (see below); otherwise online (required for Bucket, and for `pip`/`npm install` steps)
- **Backend server:** `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- **Dashboard:** `npm run dev -- --host 0.0.0.0 --port 5173` (Vite; drifted to port 5174 in one session due to a stale process holding 5173 — CORS allowlist updated accordingly)

---

## Test Categories

### 1. Offline Capability Verification
**Method:** Full machine restart, Wi-Fi and Ethernet physically disabled before launching any process, then backend + dashboard started fresh and a known-good image uploaded.
**Result:** PASS. Image upload → detection → classification → dashboard display completed with no network errors, no hangs, no `ConnectionError`. Confirms the core image-classification path has no hidden runtime network dependency.
**Caveat:** Bucket (Stage 7) is excluded from this claim by nature — it is a remote service and was not expected to succeed offline; this was verified separately (see below).

### 2. Image Classification — Real Photographs
**Method:** Real photographs (self-captured and select web-sourced reference images) uploaded through the dashboard's Signals page and via direct `test_api.py` calls to `/api/v1/analyze`.
**Result:** See Image Validation Pack for full case-by-case detail. Summary: 3 of 6 recorded cases PASS, 1 flagged with an unresolved inconsistency, 2 are expected/explained misses due to documented scope gaps (camera angle, untrained vessel classes), 1 pre-retrain baseline case excluded from scoring.

### 3. Classifier Retraining
**Method:** `backend/scripts/train_classifier.py`, run with `--epochs 50 --batch_size 32` against a reorganized `dataset/classifier/` folder (9 classes: the original 8 plus a new "Offshore Support Vessel" class built from ~300 self-captured photographs, sorted using a purpose-built keyboard-driven sorting tool).
**Result:** Training manually stopped at epoch 19/49 after observing training accuracy plateau (~97–98%) across several consecutive epochs, indicating diminishing returns. The checkpoint saved at that point (`efficientnet_vessel_best.pth`) was used for all subsequent testing in this packet and validated against previously-unseen photographs (see Image Validation Pack, Cases 1–2).
**Note:** Two classes (Cruise Ship, Fishing Trawler) had zero available training images and were excluded from this training run entirely; they are not currently predictable by this checkpoint.

### 4. Bucket Integration
**Method:** New `bucket_client.py` built to mirror the already-proven Bucket contract from the acoustic pipeline (`bucket_verification.py`), wired into `vision_orchestrator.py` as a non-fatal Stage 7. Tested with two live upload requests against Siddhesh's hosted Bucket service.
**Result:** FAIL (both attempts) — `HTTP 503` on both, consistent with Render free-tier cold-start behavior observed elsewhere in the project today. The integration code itself was not observed to error; both failures were server-side unavailability responses.
**Not yet done:** a confirmed successful write for this specific path. Recommend retrying when there is time to wait out a possible cold-start window, or coordinating with Siddhesh on service warm-up.

### 5. CORS / Dashboard Connectivity
**Method:** Manual dashboard upload testing, browser DevTools console inspection.
**Result:** One real bug found and fixed — `backend/app/main.py`'s CORS `allow_origins` list did not include the dashboard's actual running origin (`http://localhost:5174`, due to Vite port drift from a stale process on 5173). Symptom was a `net::ERR_FAILED` / `TypeError: Failed to fetch` in the browser despite the server log showing a genuine `200 OK` — root-caused via DevTools console output showing the explicit CORS block message. Fixed by adding the correct origin to the allowlist; confirmed working immediately after.

### 6. Acoustic Pipeline (separate system, tested earlier in this sprint for comparison/local-intelligence-engine work)
**Method:** `pipeline_connector.py --count 5`, local signal generation through to Bucket write.
**Result:** 5/5 chunks passed, trace continuity 5/5, Bucket writes 5/5 successful (this pipeline's Bucket calls succeeded on the day they were tested, unlike the image path's later attempts — timing-dependent on Bucket/Render availability, not a difference in code correctness).
**Note:** This is a genuinely separate system from the image-classification path and does not feed the same dashboard views; included here for completeness since local-intelligence-engine wiring work was done on it during this sprint.

---

## Consolidated Pass/Fail Summary

| Test Category | Result |
|---|---|
| Offline capability (image path) | PASS |
| Image classification — trained-class, matching-style photos | PASS |
| Image classification — untrained classes / mismatched camera angle | Expected miss (documented scope gap) |
| Image classification — one filename inconsistency | Unresolved, flagged |
| Classifier retraining | Completed (partial — 6 of planned classes covered, 2 classes had no data) |
| Bucket write (image path) | FAIL (2/2 attempts, external service unavailability) |
| Bucket write (acoustic path) | PASS (5/5, tested separately) |
| CORS / dashboard connectivity | PASS (after fix) |
| Replay artifact persistence | PASS (2/2 verified against real files on disk) |

---

## Tools Used

- `test_api.py` — direct backend testing without the dashboard, for isolating classification results from frontend issues
- Browser DevTools (Console, Network tabs) — for diagnosing the CORS failure
- PowerShell (`Get-ChildItem`, `netstat`, `git`) — environment and repo inspection
- A custom-built keyboard-driven image sorting tool (`sort_images.py`) — used to rapidly sort 800+ unlabeled training photographs into class folders ahead of retraining
- Git LFS — for committing the retrained model checkpoint (~81 MB)

---

## Known Limitations of This Testing

- Testing was conducted by a single person on a single machine; no multi-user or concurrent-load testing was performed.
- The image test set, while real, is small and skewed toward Offshore Support Vessel (the class with the most available training and test data). Confidence in other classes' real-world accuracy is lower and less tested.
- Samachar-routed testing could not be performed at all, since that integration does not yet exist in this path.
