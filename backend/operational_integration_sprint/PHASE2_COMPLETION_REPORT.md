# Phase 2: Advanced Integration & Security Hardening
## SVACS Operational Integration and Image Validation Sprint - Completion Report

| | |
|---|---|
| Author | Nupur Gavane |
| Report date | 2026-10-07 |
| Brief target date | 2026-09-08 |
| Repository | BHIV-Engineering-Exchange/bhiv-SVACS |
| Branch | nupur/local-image-validation |
| Latest commit | 61f1ac4 |
| Environment verified | Local machine (Windows), backend on Python 3.11, no cloud deployment |

The brief's objective is to add production monitoring, error boundary safety and end-to-end integration verification to the earlier sprint, and to certify the result. This report states what was built, what was verified and how, what was not achieved, and the resulting readiness assessment. Where evidence is missing, the report says so.

---

## Summary

| Brief item | Status | Evidence section |
|---|---|---|
| Production monitoring | Done for a single local process; see limits | 2.4 |
| Error boundary safety | Done | 2.6 |
| Unit test coverage (named in the brief's recommendations) | Done: 172 tests passing | 2.1 |
| Authentication and access safety | Done as a shared API key; not user login | 2.2 |
| Deterministic execution verification | Done on real models: identical across 5 runs | 2.3 |
| Database and storage layer (Bucket) | Writes confirmed stored; no read-back | 2.5 |
| Traceability | Partial: two identifiers per request | 2.8 |
| API contracts | Partial: no response schema, Samachar contract not honored | 3 |
| Production readiness | Not certified for unsupervised production | 4 |

---

## 1. Source Code Implementation & Commits

### 1.1 Commits

Two earlier commits from the first sprint (d44c2cc, 372a72a) are already in origin/main. The commits below are on the branch and not yet in origin/main (output of `git log --oneline origin/main..HEAD`).

| Commit | Message | Relates to |
|---|---|---|
| 1c40afa | Add naval vessel classifier (12 classes + OSV), knowledge pack, ship identifier via OCR pennant matching, and risk-level fix | Feature work requested separately |
| 98cf896 | Update naval vessel classifier | Multi-vessel crops and thumbnails (contributed by a team member) |
| d43386e | Add pennant-versus-class type consistency check and per-detection ship identification for multi-vessel images | Feature work; also carries the retrained 21-class checkpoint |
| 39c5686 | Fix knowledge pack class names to match classifier labels; add missing entries for nine classes to pack and ship registry | Defect fix (risk levels) |
| e375157 | Add unit and data-integrity test suite; correct ship lists in knowledge pack | Phase 2: unit tests |
| 61f1ac4 | Add API key authentication, live runtime metrics and monitoring endpoints, with tests | Phase 2: security and monitoring |

The branch carries feature work done for other tasks as well as the Phase 2 hardening. The Phase 2 items are e375157 and 61f1ac4.

### 1.2 Components added or changed for Phase 2

| File | Purpose |
|---|---|
| backend/app/core/security.py | API key check, applied to every POST route |
| backend/app/core/metrics.py | Request counters, latency percentiles, pipeline stage timings, health snapshot |
| backend/app/main.py | Registers the metrics middleware and stage timing handler; /health, /stage-metrics, /bucket/status, /validation-breakdown now report live values; new /metrics endpoint; /events-over-time returns an empty list |
| frontend/src/pages/Signals.tsx | Sends the API key header on upload requests |
| backend/tests/ | Five test files, 172 tests (section 2.1) |
| verify_determinism.py (repo root) | Evidence tool for section 2.3 |

### 1.3 Reproducing the build

```
cd backend
venv\Scripts\activate
pip install pytest "httpx<0.28"
python -m pytest tests -q
```

---

## 2. System Verification Report

### 2.1 Automated tests

172 tests pass on the author's machine (Starlette 0.36.3, httpx 0.27.2).

| Test file | Tests | Covers |
|---|---|---|
| test_ship_identifier.py | 42 | Pennant extraction, ship lookup, pennant-versus-class type check |
| test_naval_identifier.py | 41 | Length, beam, displacement, type and description scoring; candidate ranking |
| test_metrics.py | 54 | Percentiles, health snapshot, stage log parser, middleware, dashboard field contracts |
| test_security.py | 19 | Key check, behavior behind CORS, policy that every POST route is protected |
| test_data_integrity.py | 16 | Class labels agree across classifier, knowledge pack, ship registry and type map; root and backend data copies identical |

Additional verification, run in clean environments:
- The full suite also passes on the oldest framework versions the project allows (FastAPI 0.110.0, Starlette 0.36.3) and on the newest.
- Each defect found during this work was reintroduced once to confirm the suite fails on it: the "anti-submarine counts as submarine" match, old-style class names in the knowledge pack, a class missing from the ship registry, a wrong pennant prefix, drift between the two data copies, and an unprotected POST route.
- A one-off harness loaded the real main.py with stand-ins for the model modules and checked 24 behaviors end to end, including authentication together with the middleware. This harness is not part of the repository and is listed for completeness only.

Known test-environment note: with Starlette 0.36.3, the test client needs httpx below 0.28.

### 2.2 Authentication and access safety

Mechanism: every POST route requires the header `X-API-Key` when the environment variable `SVACS_API_KEY` is set (401 if missing, 403 if wrong). The key comparison is constant-time.

Live verification on the running backend (`POST /naval/identify`):

| Request | Result |
|---|---|
| No key | 401 |
| Wrong key | 403 |
| Correct key | 200 |

The policy test fails if any `@app.post` route in main.py lacks the check, so a new upload endpoint added without protection is caught.

Limits, stated plainly:
- The key is a shared secret, not user login. The dashboard sends it from the browser, so anyone who can load the dashboard can read it. It stops scripts and scanners that call the API directly; it does not identify individual users.
- If `SVACS_API_KEY` is not set, the POST routes are open and the server logs a warning. This is deliberate for local development and must not be used on a shared server.
- GET endpoints are open, including /metrics, /vessels and the artifact images. Artifact images are loaded by image tags, which cannot send headers.
- There is no rate limiting and no upload size limit.

### 2.3 Deterministic execution verification

Tool: verify_determinism.py sends one image repeatedly and compares every response field. Request-specific values (trace_id and any identifier inside strings) are ignored. The evidence image is compared by SHA-256.

Run on the real models:

| | |
|---|---|
| Image | INS_Kolkata_and_INS_Delhi_alongside_at_Porbandar.jpg |
| Image SHA-256 | 970f96d4505bdfc2657c81af8ab116262b5d23a8575c282d1df490ff24addfde |
| Run 1 | 5 requests, result IDENTICAL, largest numeric difference 0, evidence image identical |
| Class returned | Kolkata Class, confidence 1.0 |

The first request of that run loaded the models, so run 1 also compares a cold start with warm requests.

Restart check: The backend was restarted after the baseline run (start time derived from /health as last_telemetry_utc minus uptime_seconds: 2026-10-07 05:51:30 UTC, against 05:25:12 UTC for the original process). determinism_after_restart.json compares 3 further requests with the saved baseline: IDENTICAL, largest numeric difference 0.

Scope of the claim: one image, one machine, CPU inference. Bit-identical results on this image do not prove identical results on every image or on other hardware.

### 2.4 Production monitoring

All monitoring values come from live traffic. Nothing is a placeholder. Before this work, /health, /stage-metrics, /bucket/status, /validation-breakdown and /events-over-time returned fixed invented numbers.

| Endpoint | Reports |
|---|---|
| /health | status, uptime, successful-upload rate (last 60 s), median upload latency (last 5 min) with sample count, 5xx count (last 60 s), model-loaded flags, whether authentication is enabled |
| /stage-metrics | per image-pipeline stage: lifetime count, rate, p50 and p95 latency, error rate, status (live / degraded / stale / down) |
| /bucket/status | Bucket write outcomes since start |
| /validation-breakdown | allow / flag / deny counts of analysed images |
| /metrics | per-route latency, per-stage timings, requests per minute for the last hour |

Measured on the real models (5 uploads; /metrics snapshot taken within an hour of them):

| Stage | Lifetime events | p50 | p95 |
|---|---|---|---|
| preprocessing | 5 | 0.0 ms | 2.8 ms |
| ocr | 5 | 3900.4 ms | 10147.6 ms |
| detection | 5 | 708.0 ms | 6036.2 ms |
| explainability | 5 | 5.8 ms | 8.0 ms |
| replay | 5 | 13.5 ms | 16.2 ms |
| bucket | 5 | 3261.2 ms | 3277.1 ms |

| Route | Count | 5xx | p50 | p95 |
|---|---|---|---|---|
| POST /intelligence/image | 5 | 0 | 7941.9 ms | 19031.0 ms |
| GET /health | 2 | 0 | 1.9 ms | 13.6 ms |
| GET /bucket/status | 1 | 0 | 2.4 ms | 2.4 ms |
| GET /stage-metrics | 1 | 0 | 2.3 ms | 2.3 ms |

Cross-check: the stage medians sum to 7888.9 ms and the independently measured request median is 7941.9 ms, a difference of 53 ms, which is time outside the logged stages (request parsing, crop extraction, response building). The two measurements agree.

Observations:
- With 5 samples, p95 is the largest value. The slowest request (19.0 s) is consistent with first-request model loading: the OCR maximum (10.1 s) and detection maximum (6.0 s) are far above their medians. A typical warm upload takes about 7.9 s.
- On a warm request the stage medians split roughly 49 percent OCR, 41 percent Bucket write, 9 percent detection. The Bucket write is made inside the request, so it adds about 3.3 s to every upload.

Limits:
- Metrics are held in memory per process; a restart resets them, and several server processes would each keep their own.
- Latency, rate and status use short windows (5 minutes, 60 seconds). An idle server reads 0.0 with a sample count of 0, which means "no data", not "instant". The lifetime stage counts are not windowed.
- Stage timing is read from the orchestrator's log lines. If that wording changes, the tests fail.
- There is no alerting and no export to an external monitoring system.
- The dashboard's Overview and Pipeline Flow tiles for signal, perception, intelligence and state belong to the acoustic pipeline, which this backend does not run, so they read zero. The events-over-time chart plots those same stages and is empty. System Health shows WebSocket connected as NO because this backend serves no WebSocket.

### 2.5 Database and storage layer (Bucket)

Bucket chain state read from the service before and after the five uploads:

| | artifact_count | last_hash (start) |
|---|---|---|
| Before | 22 | 107f5b0a798e2d5b... |
| After five uploads | 27 | 29ae156ca5c8c512... |

The count rose by exactly five and the hash changed, so the service recorded each upload. /bucket/status reported 100 percent synced and zero failed writes. Earlier attempts returned HTTP 503, consistent with the free-tier hosting waking from idle; those requests still returned results because the Bucket step is non-fatal.

What is stored per image: one artifact, built in `backend/app/services/bucket_client.py` and filled in by Stage 7 of the orchestrator.

| Envelope field | Value |
|---|---|
| artifact_id | Generated by the client for each write |
| trace_id | The orchestrator's replay_id (not the trace_id shown in the dashboard) |
| timestamp_utc | Time of the write, UTC, to the second |
| schema_version | 1.0.0 |
| source_module_id | vision_runtime_backend |
| artifact_type | vision_detection |
| parent_hash | The chain's last hash, read from the service just before the write |
| payload | The detections (label, confidence, bounding box and top predictions for each detected ship) and the OCR results (text, confidence, bounding box) |

Not sent to Bucket: the uploaded image, the evidence image, the crop images, ship names and pennant matches, the risk level, and any details typed into the dashboard. Those stay in the local replay record or are returned to the caller only.

Limits: the client writes but does not read back an individual artifact, so retrieval of stored content was not verified; the evidence is the service's own count and hash. The write is synchronous and adds about 3.3 s per upload. Bucket requires network access, so the image path is not fully offline.

### 2.6 Error boundary safety

| Boundary | Behavior | Evidence |
|---|---|---|
| Replay save and Bucket write | Failure is logged and the request still returns its result | A real run with a Bucket 503 returned 200 with the classification; test harness check |
| Any unhandled error in the upload route | Structured JSON 500 with error type and message, and a logged traceback | Code in main.py; harness check |
| Authentication errors | Readable 401 / 403 in the browser; CORS headers are present on the error response | Test using a mini app with CORS |
| Empty upload | HTTP 400 with a clear message | Code in main.py |
| Monitoring | A failure while recording metrics cannot break a request (logging handler traps its own errors; middleware only observes) | Tests and code |

### 2.7 Runtime verification of identification

Observed through the dashboard with real models:

| Photo | Result | Risk level |
|---|---|---|
| Two carriers | Two separate ship cards; headline Vikramaditya; card for Vikrant at 100 percent | CRITICAL |
| Destroyer | Visakhapatnam Class, 100 percent | CRITICAL |
| Frigate | Nilgiri Class, 98.9 percent | HIGH |
| Submarine | Kalvari Class, 95.9 percent | HIGH |
| Kolkata and Delhi alongside | Two detections and two crops returned | n/a |

These confirm the class-name fix. Before it, the class names in the knowledge pack did not match the classifier's labels, so risk levels fell back to MEDIUM (observed earlier for Nilgiri Class and for Vikrant). Vikrant's own risk level (expected CRITICAL) has not been observed since the fix.

Model accuracy: **unrecorded**. The best validation accuracy of the 21-class training run was not retained. The checkpoint stores only weights and class names, and the training split was random and not saved, so the figure cannot be reconstructed from the repository. Dataset facts: 3,819 images across 21 classes (20 naval classes plus one civilian class), 61 to 461 images per class (ratio 7.6 to 1), trained with a weighted sampler and weighted loss to offset the imbalance. A fresh accuracy figure needs a held-out set of photographs never used in training.

Ship-name identification is limited to reading the hull pennant number with OCR. When the pennant is not legible the result is the class roster with no confidence values attached, because sister ships are visually near-identical.

### 2.8 Traceability

Each response carries a `trace_id`, and crop images are stored under that identifier. The replay record is stored under a separate `replay_id` that appears in server logs and in the replay folder name but is not returned in the response. The Bucket artifact is also filed under the `replay_id`, so the trace ID shown on screen cannot be used to look up its Bucket record. Two identifiers per request is a gap against a single canonical trace; a decision on unifying them is outstanding. The replay storage path is a fixed absolute path in the configuration.

---

## 3. Integration Contract Validation

| Contract | Status | How it was validated |
|---|---|---|
| Image upload API: POST /intelligence/image (file, optional naval details, X-API-Key) and its response | Partial | The full response was captured and compared in the determinism runs and is consumed by the dashboard. No automated schema test exists. The generated OpenAPI document does not describe this response because no response model is declared. |
| Authentication contract: X-API-Key, 401 / 403 | Valid | Live requests; policy test over every POST route |
| Dashboard monitoring contract: /health, /stage-metrics, /bucket/status, /validation-breakdown | Valid | Tests run the real handler code against the field names and types the dashboard reads; status values limited to live / degraded / stale / down |
| Class label contract: classifier output = training folder name = knowledge pack = ship registry = type map | Valid | Data-integrity tests; a mismatch fails the suite |
| Knowledge pack and ship registry data | Valid | Tests: numeric dimensions, unique pennants, pennant prefix agrees with class type, every ship in the registry named in the pack |
| Bucket write envelope (fields and payload listed in section 2.5) | Partial | Fields confirmed from the client source; writes accepted by the service and counted; no read-back |
| Replay record (contract.json, metadata.json per request) | Valid | Records inspected on disk earlier in the sprint |
| Samachar ingestion contract | **Not honored** | The image path posts directly to the Vision Runtime and does not go through Samachar. This bypasses a published contract and is a deviation to be resolved with the Samachar owner, who has not provided the contract. |

Changes that affect consumers: `ws_connected` is now false; /events-over-time returns an empty list; /stage-metrics now lists the six image-pipeline stages, so tiles for the four acoustic-pipeline stages show zero.

---

## 4. Production Readiness Certification

### 4.1 Assessment

**Not certified for unsupervised production use.**

The system is suitable for supervised local demonstration and further development, with the limits recorded in this report. It has not been deployed to a server: no external endpoint, no health check from outside the machine and no redeployment procedure was exercised, and metrics do not persist across a restart.

### 4.2 Checklist

| Requirement | Result |
|---|---|
| Unit and data-integrity tests | Met |
| Deterministic execution evidence | Met for one image on CPU |
| Authentication on state-changing and model-running endpoints | Met when a key is configured |
| Real monitoring and health values | Met for a single process |
| Error handling that keeps the service responding | Met |
| Storage layer confirmed | Partly met: writes confirmed, no read-back |
| Single canonical trace identifier | Not met |
| Published integration contracts honored | Not met (Samachar) |
| Model accuracy evidence | Not met (figure unrecorded; no held-out evaluation) |
| Deployment, external access, health checks on a server | Not met (not deployed) |
| User-level authentication, rate limiting, upload size limit | Not met |

### 4.3 Conditions to reach certification

| Condition | Suggested owner |
|---|---|
| Provide the Samachar ingestion contract and route uploads through it | Samachar owner |
| Decide and implement one trace identifier; return it in the response | SVACS runtime owner |
| Add Bucket read-back verification; consider moving the write off the request path | Bucket owner |
| Run a held-out evaluation of the classifier on photographs not used in training and record the result | Vision Runtime owner |
| Declare a response model for the upload endpoint and add a schema test | Author |
| Add an upload size limit and rate limiting; replace the shared key with user-level authentication for any shared deployment | Author |
| Deploy to a server; verify external access, health checks and redeployment | Deployment owner |
| Persist metrics across restarts, or export them to an external system, and add alerting | Author |

---

## 5. Evidence Index

| Evidence | Where |
|---|---|
| Test suite | backend/tests/ (172 tests) |
| Determinism reports | determinism_run1.json, determinism_after_restart.json |
| Monitoring snapshot | metrics_snapshot.json |
| Authentication requests | Section 2.2 |
| Bucket chain readings | Section 2.5 |
| Commit history | `git log --oneline origin/main..HEAD` |

Reproduce the determinism check with the backend running and the key set:

```
python ..\verify_determinism.py "<image path>" --runs 5 --save baseline.json
python ..\verify_determinism.py "<image path>" --runs 3 --compare baseline.json
```
