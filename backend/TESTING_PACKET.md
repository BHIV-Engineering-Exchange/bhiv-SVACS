# SVACS - Testing Packet

**Author:** Nupur Gavane
**Sprint:** SVACS Operational Integration and Image Validation, and its Phase 2 follow-up (Advanced Integration & Security Hardening)
**Dates:** Part A August 2026, Part B October 2026
**Note:** Part A is preserved as it was recorded in August. Where a result has since changed, a line marked "Status as of October 2026" says so. Part B documents the October testing in summary; the Phase 2 report (`operational_integration_sprint/PHASE2_COMPLETION_REPORT.md`) holds the full evidence.

---

## Purpose

This packet documents how testing was carried out: environment, tools, methodology and a consolidated pass/fail summary. Case-by-case image results from August are in the Image Validation Pack; raw replay artifacts are in Replay Validation Evidence; this document is the connecting reference.

---

# Part A - August 2026 testing (as recorded)

## Test Environment

- **Machine:** Local development machine (Windows), no cloud/VM involved
- **Python:** 3.11, separate virtual environments for `backend/` and `frontend/`
- **Node/npm:** for the React dashboard (`frontend/`)
- **Network condition for offline verification:** Wi-Fi and Ethernet physically disabled for the specific offline-capability test (see below); otherwise online (required for Bucket, and for `pip`/`npm install` steps)
- **Backend server:** `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- **Dashboard:** `npm run dev -- --host 0.0.0.0 --port 5173` (Vite; drifted to port 5174 in one session due to a stale process holding 5173, so the CORS allowlist was updated)

## Test Categories

### 1. Offline Capability Verification
**Method:** Full machine restart, Wi-Fi and Ethernet physically disabled before launching any process, then backend and dashboard started fresh and a known-good image uploaded.
**Result:** PASS. Image upload, detection, classification and dashboard display completed with no network errors, no hangs, no `ConnectionError`. Confirms the core image-classification path has no hidden runtime network dependency.
**Caveat:** Bucket (Stage 7) is excluded from this claim by nature, as it is a remote service.
**Status as of October 2026:** still valid for the classification path. Bucket writes need network access, so the full image path is not offline.

### 2. Image Classification - Real Photographs
**Method:** Real photographs (self-captured and select web-sourced reference images) uploaded through the dashboard's Signals page and via direct `test_api.py` calls to `/api/v1/analyze`.
**Result:** See the Image Validation Pack for case-by-case detail. Summary: 3 of 6 recorded cases PASS, 1 flagged with an unresolved inconsistency, 2 expected/explained misses due to documented scope gaps (camera angle, untrained vessel classes), 1 pre-retrain baseline case excluded from scoring.
**Status as of October 2026:** these cases were run against the August 6-class checkpoint, which has been replaced by a 21-class naval checkpoint. They are historical; the October checks are in Part B.

### 3. Classifier Retraining (August)
**Method:** `backend/scripts/train_classifier.py`, run with `--epochs 50 --batch_size 32` against a reorganized `dataset/classifier/` folder (9 classes: the original 8 plus a new "Offshore Support Vessel" class built from about 300 self-captured photographs, sorted with a purpose-built keyboard-driven sorting tool).
**Result:** Training manually stopped at epoch 19 of 49 after training accuracy plateaued (about 97 to 98 percent). The checkpoint saved at that point was used for all August testing and validated against previously unseen photographs (Image Validation Pack, Cases 1 and 2).
**Note:** Two classes (Cruise Ship, Fishing Trawler) had zero training images and were excluded.
**Status as of October 2026:** superseded by the 21-class naval checkpoint (Part B, section 6).

### 4. Bucket Integration (August)
**Method:** New `bucket_client.py`, built to mirror the Bucket contract already proven in the acoustic pipeline, wired into `vision_orchestrator.py` as a non-fatal Stage 7. Tested with two live upload requests against the hosted Bucket service.
**Result:** FAIL (both attempts): HTTP 503 on both, consistent with free-tier cold-start behaviour. The integration code itself did not error.
**Status as of October 2026:** PASS. See Part B, section 5: five uploads on 2026-10-07 raised Bucket's own artifact count from 22 to 27.

### 5. CORS / Dashboard Connectivity
**Method:** Manual dashboard upload testing, browser DevTools console inspection.
**Result:** One real bug found and fixed: the `allow_origins` list in `backend/app/main.py` did not include the dashboard's actual running origin (`http://localhost:5174`, due to Vite port drift). The symptom was `TypeError: Failed to fetch` in the browser although the server log showed a genuine `200 OK`; the cause was found from the explicit CORS block message in DevTools. Fixed by adding the origin.
**Status as of October 2026:** still valid. A test now also checks that authentication errors carry CORS headers, so they stay readable in the browser.

### 6. Acoustic Pipeline (separate system, tested in August)
**Method:** `pipeline_connector.py --count 5`, local signal generation through to Bucket write.
**Result:** 5 of 5 chunks passed, trace continuity 5 of 5, Bucket writes 5 of 5 successful.
**Note:** A separate system from the image-classification path; included for completeness. Not re-tested in October.

## Consolidated Summary - Part A

| Test Category | Result in August | Status as of October 2026 |
|---|---|---|
| Offline capability (image path) | PASS | Still valid for classification |
| Image classification, trained-class, matching-style photos | PASS | Historical (6-class checkpoint replaced) |
| Image classification, untrained classes / mismatched angle | Expected miss | Historical |
| Image classification, one filename inconsistency | Unresolved, flagged | Not re-examined |
| Classifier retraining | Completed (partial) | Superseded by 21-class model |
| Bucket write (image path) | FAIL (2 of 2 attempts) | PASS (October) |
| Bucket write (acoustic path) | PASS (5 of 5) | Not re-tested |
| CORS / dashboard connectivity | PASS (after fix) | Still valid |
| Replay artifact persistence | PASS (2 of 2) | Not re-tested |

## Tools Used (August)

- `test_api.py` - direct backend testing without the dashboard
- Browser DevTools (Console, Network) - diagnosing the CORS failure
- PowerShell (`Get-ChildItem`, `netstat`, `git`) - environment and repo inspection
- `sort_images.py` - a keyboard-driven image sorting tool used to sort 800 or more unlabeled photographs
- Git LFS - committing the model checkpoint

## Known Limitations of the August Testing

- One person, one machine; no multi-user or concurrent-load testing.
- The image test set was small and skewed toward Offshore Support Vessel.
- Samachar-routed testing could not be performed, since that integration does not exist in this path.

---

# Part B - October 2026 testing (Phase 2)

## Test Environment

- **Machine:** Local development machine (Windows), no cloud/VM involved; backend in its own virtual environment (Python 3.11)
- **Framework versions on the test machine:** Starlette 0.36.3, httpx 0.27.2 (the test client needs httpx below 0.28 with this Starlette)
- **Also run in clean environments:** FastAPI 0.110.0 with Starlette 0.36.3 (oldest allowed by the project) and the newest versions
- **Backend:** started without `--reload` for the evidence runs, so in-memory metrics were not reset mid-run
- **Authentication:** `SVACS_API_KEY` set for the backend; the same value in `frontend/.env.local` as `VITE_API_KEY`

## Test Categories

### 1. Automated unit and data-integrity tests
**Method:** `python -m pytest tests -q` from `backend/`.
**Result:** PASS. 172 tests (ship identifier 42, naval identifier 41, metrics 54, security 19, data integrity 16) on the test machine, and on both framework version ends in clean environments.
**Test quality check:** each defect found during the work was put back once to confirm the suite fails on it: the "anti-submarine counts as submarine" match, old-style class names in the knowledge pack, a class missing from the ship registry, a wrong pennant prefix, drift between the two copies of the data files, and an unprotected POST route.
**What it guards:** the classifier's class labels, the knowledge pack, the ship registry and the vessel-type map must agree, because several lookups match them by exact text and a mismatch otherwise fails silently.

### 2. Authentication
**Method:** live requests with `curl.exe` to `POST /naval/identify` on the running backend.
**Result:** PASS. No key gives 401, a wrong key gives 403, the correct key gives 200. A policy test fails if any POST route in `main.py` lacks the key check.
**Limit:** a shared secret, not user login (see the Phase 2 report, section 2.2).

### 3. Deterministic execution
**Method:** `verify_determinism.py` sends one image repeatedly to `/intelligence/image` and compares every response field, ignoring only request-specific values (`trace_id` and identifiers inside strings). Image: `INS_Kolkata_and_INS_Delhi_alongside_at_Porbandar.jpg` (SHA-256 970f96d4505bdfc2657c81af8ab116262b5d23a8575c282d1df490ff24addfde).
**Result:** PASS. Five runs, identical, largest numeric difference 0, evidence image identical. The first run loaded the models, so cold and warm requests were compared. The comparison after a server restart is in the Phase 2 report, section 2.3.
**Limit:** one image, one machine, CPU inference.

### 4. Monitoring on the real models
**Method:** after the five uploads, `/stage-metrics`, `/health`, `/bucket/status` and `/metrics` were read.
**Result:** PASS. Each of the six pipeline stages recorded 5 events. Median stage times: OCR 3.9 s, Bucket write 3.3 s, detection 0.7 s, all others under 15 ms. The request median measured separately (7.94 s) matches the sum of the stage medians (7.89 s). The slowest request (19.0 s) is consistent with first-request model loading.
**Note:** readings taken more than 5 minutes after the last upload show status "stale" and latency 0.0 because those figures use a 5-minute window; the lifetime counts (5 per stage) are not windowed. The one-hour `/metrics` snapshot holds the latencies.

### 5. Bucket write
**Method:** Bucket's chain state (`/bucket/chain-state`) was read before and after the five uploads.
**Result:** PASS. `artifact_count` rose from 22 to 27 and the last hash changed; `/bucket/status` reported 100 percent synced and 0 failed.
**Limit:** the client does not read an artifact back, so retrieval of stored content was not verified.

### 6. Classification and risk levels on the 21-class model
**Method:** real photographs uploaded through the dashboard.
**Result:** PASS for the cases observed: a two-carrier photo returned two separate ship cards (headline Vikramaditya, CRITICAL); a destroyer returned Visakhapatnam Class (CRITICAL); a frigate returned Nilgiri Class (HIGH); a submarine returned Kalvari Class (HIGH). These confirm the class-name fix; before it, risk levels fell back to MEDIUM (observed earlier for Nilgiri Class and Vikrant). A photo with Kolkata and Delhi alongside returned two detections and two crops. A carrier with a smaller ship behind it returned Vikrant (100 percent, CRITICAL) as the headline and a second detection, Kora Class (87.3 percent).
**Risk levels:** all five renamed classes (Vikrant, Vikramaditya, Visakhapatnam, Nilgiri, Kalvari) have now been seen returning the expected risk level.
**Accuracy:** the best validation accuracy of the training run was not recorded, and no held-out evaluation has been done.

### 7. Error boundaries
**Result:** PASS. A Bucket failure does not fail the request (observed on a real run with HTTP 503, and in a test harness); an unhandled error returns a structured JSON 500 (test harness); authentication errors are readable in the browser (test); a failure while recording metrics cannot break a request (tests).
**Note:** the test harness replaced the model modules with stand-ins and is not part of the repository.

## Consolidated Summary - Part B

| Test Category | Result |
|---|---|
| Unit and data-integrity tests (172) | PASS |
| Authentication (401 / 403 / 200) | PASS |
| Deterministic execution (5 runs, real models) | PASS |
| Monitoring values on real models | PASS |
| Bucket write (artifact count 22 to 27) | PASS |
| Class names and risk levels on the 21-class model | PASS for all five renamed classes |
| Error boundaries | PASS |
| Model accuracy evaluation | Not done (figure unrecorded) |
| Samachar-routed testing | Not possible (integration absent) |
| Load, concurrency and deployed-environment testing | Not done |

## Tools Used (October)

- `pytest` - automated suite
- `verify_determinism.py` (repo root) - determinism check and JSON report
- `curl.exe` - authentication, health, monitoring and Bucket chain-state checks
- PowerShell - reading the saved metrics snapshot and the reports
- Browser (the dashboard) - classification and risk-level checks

## Known Limitations of the October Testing

- One person, one machine, CPU inference; no load, concurrency or deployed-environment testing.
- Determinism was checked on one image.
- With 5 requests, the 95th percentile equals the largest value.
- Classification was checked on a handful of photographs and gives no accuracy estimate.
- Samachar-routed testing remains impossible, since that integration does not exist in this path.
