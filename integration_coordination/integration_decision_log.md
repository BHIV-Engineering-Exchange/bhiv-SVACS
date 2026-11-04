# BHIV × SEVA Defence Convergence Quest — Integration Decision Log

**Work Package:** Integration Coordination  
**Lead / Owner:** Rukayya Ansari  
**Date of Audit:** November 04, 2026  
**Audited Target Workspace:** `c:\Users\rukka\OneDrive\Desktop\Rukayya\bhiv-SVACS-main`  
**Governing Directive:** `BHIV_SEVA_Defence_Convergence_Quest_Individual_Tasks.pdf`

---

## 1. Overview & Policy

This decision log tracks architectural, interface, data boundary, and protocol decisions affecting the integration between **SVACS**, **Signals Corps/C5SIR**, and **BIQOS**.

### Governance Rules:
1. **No Invented Approvals**: Unresolved topics are explicitly labelled `OPEN` or `PENDING CONFIRMATION`.
2. **Evidence Traceability**: Every decision cites explicit repository code, sprint packets, test results, or task brief directives.
3. **Conservative Integration Claims**: Proposed architectures or roadmap items are never recorded as approved implementations without reproducible proof.

---

## 2. Decision Record Table

| Decision ID | Date | Topic | Decision / Question | Owner | Approval Status | Impact on Integration | Responsible Person |
|---|---|---|---|---|---|---|---|
| **DEC-INT-001** | 2026-11-04 | Primary Demonstrator Use-Case | Begin with component traceability and lifecycle intelligence; keep secure-drone/counter-drone and surveillance as bounded tracks; no autonomous engagement | Shivam Pal & Harsha | **APPROVED (Brief Directive)** | Constrains integration scope to auditable data pipelines and evidence-backed demonstrator; excludes lethal/autonomous actuation | Shivam Pal (Delivery Commander) |
| **DEC-INT-002** | 2026-11-04 | Data Analogue Policy | Non-classified commercial vessel photographs and synthetic acoustic signals must be explicitly labelled as non-military analogues; no dummy military records | Ansh Gupta & Harsha | **APPROVED (Brief Directive)** | Prevents classification violations and fraudulent claims; all models and UI must flag analogue provenance | Ansh Gupta (Governance) |
| **DEC-INT-003** | 2026-08-26 | Trace ID vs Replay ID Divergence | In `backend/app/main.py`, HTTP handler creates `trace_id` while `vision_orchestrator.py` creates `replay_id`. Question: Should they be unified into a single canonical UUID4? | Ankita & Harsha | **OPEN** | Dual IDs cause confusion in downstream evidence chains (Bucket and TANTRA); unification ensures single trace continuity | Ankita (SVACS Runtime) / Harsha |
| **DEC-INT-004** | 2026-08-26 | Samachar Ingestion Bypass | Dashboard `Signals.tsx` currently uploads directly to SVACS `/intelligence/image?quick=true`, bypassing Chandragupta's Samachar gateway. Question: How and when should Samachar contract be integrated? | Chandragupta & Harsha | **OPEN** | Prevents parallel pipelines; demonstrator currently runs without upstream Samachar intelligence ingestion | Chandragupta (Samachar) / Rukayya Ansari |
| **DEC-INT-005** | 2026-08-26 | Replay Storage Directory Portability | `backend/app/core/config.py` hardcodes `REPLAY_STORAGE_DIR` to `C:\tmp\svacs_replays`. Question: Should this be migrated to a project-relative path (`backend/replays`) or env var? | Rayyan & Vijay Dhawan | **OPEN** | Prevents execution failure on fresh environments or deployed Linux/Docker instances lacking `C:\tmp` | Rayyan (DevOps) / Vijay Dhawan |
| **DEC-INT-006** | 2026-08-26 | Bucket Service Availability Risk | Live write attempts to `https://bhiv-bucket-i1l6.onrender.com` failed with HTTP 503 (Render free-tier cold start). Question: Should Bucket be deployed locally/containerized for the demonstrator? | Rayyan & Siddhesh Narkar | **PENDING CONFIRMATION** | Live image classification currently cannot persist canonical evidence to Bucket without 503 errors; blocks verifiable audit trail | Rayyan (DevOps) / Siddhesh Narkar |
| **DEC-INT-007** | 2026-08-26 | Backend Architecture Duality | Two backend entrypoints exist: `backend/app/main.py` (Vision runtime) and `frontend/services/api/main_api.py` (Acoustic/Pipeline log reader). Question: Which is canonical for demonstrator? | Harsha & Rayyan | **OPEN** | Vite frontend displays empty stubs on non-image tabs when pointing to `backend/app/main.py`; single unified server needed | Harsha (Architecture Authority) |
| **DEC-INT-008** | 2026-11-04 | Signals Corps / C5SIR Intake Scope | Signals Corps domain owner is unconfirmed; no interface spec or test sandbox exists. Question: What is the boundary for C5SIR in the 72-hour demonstrator? | Shivam Pal & Harsha | **PENDING CONFIRMATION** | If domain owner and non-sensitive spec are not provided, C5SIR must be bounded as a documented roadmap contract rather than live integration | Shivam Pal / Harsha |
| **DEC-INT-009** | 2026-11-04 | BIQOS & TANTRA SDK Specification | Brief specifies TANTRA SDK, KSML, MDU, and MasterDB for shared governance. Question: What concrete packages and schemas must be imported into `bhiv-SVACS-main`? | Harsha | **PENDING CONFIRMATION** | Without concrete SDK distribution, SVACS cannot bind to BIQOS governance; remains standalone system | Harsha (Architecture Authority) |
| **DEC-INT-010** | 2026-11-04 | PKB-001 Invariant Enforcement | Sakshi Thakur assigned to verify PKB-001 invariants (append-only review events, single-writer concurrency, cryptographic envelopes). Question: How does SVACS consume PKB-001? | Sakshi Thakur & Harsha | **PENDING CONFIRMATION** | Determines whether review decision events in demonstrator are backed by cryptographic validation | Sakshi Thakur / Harsha |
| **DEC-INT-011** | 2026-08-26 | Quick Mode OCR Skipping (`?quick=true`) | In `POST /intelligence/image?quick=true`, EasyOCR is skipped to optimize latency (<1s vs 15-45s). Resulting replay record has `ocr_results: []`. | Vijay Dhawan & Mohit Sharma | **DECIDED / DOCUMENTED** | Downstream consumers of replay records must not treat empty OCR results as OCR failure when quick mode was requested | Vijay Dhawan (ML/CV) |

---

## 3. Detailed Decision Records

### DEC-INT-001: Primary Demonstrator Use-Case Selection
- **Date:** 2026-11-04
- **Topic:** Demonstrator operational focus and boundary definition.
- **Decision:** Begin with component traceability and lifecycle intelligence as the primary demonstrator. Secure-drone/counter-drone and critical-infrastructure surveillance are bounded as adjacent roadmap tracks. Autonomous engagement and operational countermeasures are strictly forbidden.
- **Evidence / Reference:** `BHIV_SEVA_Defence_Convergence_Quest_Individual_Tasks.pdf`, Page 2, Section 1 ("First use-case decision").
- **Owner:** Shivam Pal (Delivery Commander) & Harsha (Architecture Authority).
- **Approval Status:** **APPROVED (Brief Directive)**.
- **Impact on Integration:** Prevents scope explosion. Focuses integration coordination on:
  1. Image upload and acoustic signal classification.
  2. Deterministic state evaluation.
  3. Replay artifact creation and Bucket evidence persistence.
  4. Observability and audit trail.
- **Open Questions:** Does the verified SVACS dataset support full lifecycle tracking, or will lifecycle metadata be simulated via the Jane's/Mumbai port registry?
- **Next Action:** Harsha and Shivam to formally sign off on the minimum demonstrable workflow during the 0–4 hour window.
- **Responsible Person:** Shivam Pal.

---

### DEC-INT-002: Data Analogue Policy & Classification Boundary
- **Date:** 2026-11-04
- **Topic:** Development data sources and military data boundaries.
- **Decision:** All work must use authorised, non-classified development data. Real public datasets (e.g. NOAA/USCG AIS data, self-captured maritime vessel photographs) and synthetic acoustic signals are approved. Genuine non-military commercial equipment/vessel data must be explicitly labelled as analogues. Under no circumstances may analogue data be represented as real military data, nor may dummy records be fabricated.
- **Evidence / Reference:** `BHIV_SEVA_Defence_Convergence_Quest_Individual_Tasks.pdf`, Page 2, "Data rule" and "Hard boundary".
- **Owner:** Ansh Gupta (Governance) & Harsha (Architecture Authority).
- **Approval Status:** **APPROVED (Brief Directive)**.
- **Impact on Integration:** Every schema and adapter must include provenance tags indicating source type (`commercial_analogue`, `synthetic_acoustic`, `public_ais`).
- **Open Questions:** None. Rule is absolute.
- **Next Action:** Ansh Gupta to perform governance review on all sample datasets in `dataset/` and `vessel_registry.json`.
- **Responsible Person:** Ansh Gupta.

---

### DEC-INT-003: Trace ID vs Replay ID Divergence in Vision Runtime
- **Date:** 2026-08-26 (Audited 2026-11-04)
- **Topic:** Correlation identifier consistency in `backend/app/main.py`.
- **Context:** In `backend/app/main.py` (`upload_image`), the API handler generates `trace_id = str(uuid.uuid4())` and returns it in `UploadImageResponse`. However, the orchestrator call `vision_orchestrator.process_bytes()` generates an independent `replay_id = str(uuid.uuid4())` which is written to `contract.json`, `metadata.json`, and passed to `bucket_client.py`.
- **Evidence / Reference:**
  - `backend/app/main.py`, lines 218–220
  - `backend/operational_integration_sprint/REPLAY_TRACE_EVIDENCE.md`, lines 80–92
  - `backend/REVIEW_PACKET.md`, lines 68–69
- **Owner:** Ankita (SVACS Runtime/Trace Design) & Harsha (Architecture Authority).
- **Approval Status:** **OPEN**.
- **Impact on Integration:** Downstream systems querying Bucket by `trace_id` will fail to find artifacts saved under `replay_id`. Breaks unbroken trace continuity requirement.
- **Open Questions:** Should `process_bytes` accept an optional incoming `trace_id` parameter to use as `replay_id`?
- **Next Action:** Coordinate with Ankita and Vijay to update `vision_orchestrator.py` signature to accept `trace_id: Optional[str] = None`.
- **Responsible Person:** Rukayya Ansari (Coordinate) / Ankita (SVACS Runtime).

---

### DEC-INT-004: Samachar Ingestion Routing vs Direct Dashboard Upload
- **Date:** 2026-08-26 (Audited 2026-11-04)
- **Topic:** Direct client ingestion vs governed gateway ingestion.
- **Context:** The task brief specifies that SVACS receives intelligence through Samachar (`Image → Samachar → SVACS → Bucket → Replay → Dashboard`). In the current workspace, the frontend `Signals.tsx` bypasses Samachar and calls `http://localhost:8000/intelligence/image` directly because Samachar's actual contract and endpoint were not provided by Chandragupta.
- **Evidence / Reference:**
  - `backend/operational_integration_sprint/RUNTIME_VALIDATION_REPORT.md`, lines 39–42
  - `frontend/src/pages/Signals.tsx`, lines 130–133
- **Owner:** Chandragupta (Samachar Domain Lead) & Harsha (Architecture Authority).
- **Approval Status:** **OPEN / PENDING CONFIRMATION**.
- **Impact on Integration:** The demonstrator cannot claim an integrated ingestion chain without Samachar; direct upload is an acknowledged local workaround.
- **Open Questions:** Is Samachar available as a running service, or should Chandragupta deliver a mock adapter / schema contract?
- **Next Action:** Rukayya to issue interface clarification request to Chandragupta for the official Samachar OpenAPI spec.
- **Responsible Person:** Rukayya Ansari (Coordination) / Chandragupta (Samachar).

---

### DEC-INT-005: Replay Storage Directory Portability
- **Date:** 2026-08-26 (Audited 2026-11-04)
- **Topic:** Hardcoded absolute file path for replay evidence storage.
- **Context:** In `backend/app/core/config.py`, `REPLAY_STORAGE_DIR` is defined as an absolute string: `C:\tmp\svacs_replays`. On any environment lacking `C:\tmp` (e.g. Linux staging, fresh developer machine, CI/CD runner), replay persistence crashes or fails silently.
- **Evidence / Reference:**
  - `backend/app/core/config.py`
  - `backend/operational_integration_sprint/REPLAY_TRACE_EVIDENCE.md`, lines 18–34
  - `backend/REVIEW_PACKET.md`, line 72
- **Owner:** Rayyan (DevOps / Reproducible Deployment) & Vijay Dhawan.
- **Approval Status:** **OPEN**.
- **Impact on Integration:** Harsha and Rayyan cannot independently reproduce test evidence in clean CI/CD or Linux containers without manual directory creation.
- **Open Questions:** Should default be changed to `os.path.join(os.path.dirname(__file__), "..", "..", "replays")` with an `os.getenv("REPLAY_STORAGE_DIR")` override?
- **Next Action:** Recommend configuration patch to Rayyan for the reproducible deployment runbook.
- **Responsible Person:** Rayyan (DevOps).

---

### DEC-INT-006: Bucket Evidence Store Infrastructure Strategy
- **Date:** 2026-08-26 (Audited 2026-11-04)
- **Topic:** Mitigation of Render free-tier cold starts (HTTP 503) for Bucket writes.
- **Context:** Live testing of `backend/app/services/bucket_client.py` against `https://bhiv-bucket-i1l6.onrender.com` failed twice with HTTP 503. Render free-tier spun down the container, exceeding request timeouts.
- **Evidence / Reference:**
  - `backend/TESTING_PACKET.md`, lines 43–47
  - `backend/operational_integration_sprint/RUNTIME_VALIDATION_REPORT.md`, lines 47–50
- **Owner:** Rayyan (DevOps) & Siddhesh Narkar / Soham Kotkar.
- **Approval Status:** **PENDING CONFIRMATION**.
- **Impact on Integration:** Verifiable immutable audit trail cannot be demonstrated live if external hosting drops connections.
- **Open Questions:** Can Rayyan package Bucket into a local Docker container or standing background service for local demonstrator runs?
- **Next Action:** Rayyan to evaluate running a local Bucket instance or implementing pre-warm health checks before demonstrator execution.
- **Responsible Person:** Rayyan (DevOps) / Siddhesh Narkar.

---

### DEC-INT-007: Single Backend Server Consolidation
- **Date:** 2026-08-26 (Audited 2026-11-04)
- **Topic:** Architectural conflict between `backend/app/main.py` and `frontend/services/api/main_api.py`.
- **Context:** The workspace has two distinct FastAPI backends:
  1. `backend/app/main.py`: Serves vision runtime (`/intelligence/image`, `/api/v1/analyze`), stubs non-image endpoints as empty lists `[]` or hardcoded numbers.
  2. `frontend/services/api/main_api.py`: Serves signal, perception, intelligence, and state logs from `.jsonl` files, with image proxy to ngrok.
  If the frontend runs against `backend/app/main.py`, the Vessels, Alerts, and Live Pipeline pages are empty.
- **Evidence / Reference:**
  - `backend/app/main.py`, lines 386–475
  - `frontend/services/api/main_api.py`, lines 74–258
  - `backend/operational_integration_sprint/RUNTIME_VALIDATION_REPORT.md`, line 80
- **Owner:** Harsha (Architecture Authority) & Rayyan (DevOps).
- **Approval Status:** **OPEN**.
- **Impact on Integration:** Violates Definition of Done ("Deliver one coherent, working demonstrator rather than separate products stitched together with a dashboard").
- **Open Questions:** Should `main_api.py` import `vision_orchestrator` directly to create a single true backend?
- **Next Action:** Harsha to approve architecture decision; Rayyan to configure unified startup command.
- **Responsible Person:** Harsha (Architecture Authority).

---

### DEC-INT-008: Signals Corps / C5SIR Intake Scope
- **Date:** 2026-11-04
- **Topic:** Boundary and delivery criteria for Signals Corps / C5SIR.
- **Context:** The quest image depicts joint maritime and signals convergence. However, no Signals Corps repository, owner, schema, or endpoint exists in the workspace.
- **Evidence / Reference:** `BHIV_SEVA_Defence_Convergence_Quest_Individual_Tasks.pdf`, Page 3 Stage 2; Page 5 Task K.
- **Owner:** Shivam Pal (Delivery Commander) & Harsha (Architecture Authority).
- **Approval Status:** **PENDING CONFIRMATION**.
- **Impact on Integration:** Risk of failing Gate 2 and Gate 6 if integration is claimed without proof.
- **Open Questions:** Who is the named contact for Signals Corps? Can they provide a non-sensitive sample dataset (e.g. RF spectrum logs, link telemetry) by Hour 24?
- **Next Action:** Shivam Pal to resolve ownership gap during the 0–4 hour baseline checkpoint.
- **Responsible Person:** Shivam Pal.

---

### DEC-INT-009: BIQOS & TANTRA SDK Adoption
- **Date:** 2026-11-04
- **Topic:** Technical mechanism for BIQOS governance and TANTRA SDK integration.
- **Context:** Brief principle states: *"Use TANTRA SDK for approved service discovery/authentication/contracts/traceability; KSML and MDU for approved semantics and metadata."* Currently, no TANTRA SDK package is installed in Python or Node.
- **Evidence / Reference:** `BHIV_SEVA_Defence_Convergence_Quest_Individual_Tasks.pdf`, Page 6, "Integration principle".
- **Owner:** Harsha (Architecture Authority).
- **Approval Status:** **PENDING CONFIRMATION**.
- **Impact on Integration:** Systems currently integrate via direct REST HTTP and local JSON files rather than TANTRA SDK bus.
- **Open Questions:** Is TANTRA SDK an external Python wheel, a Git submodule, or an architectural pattern implemented in user space?
- **Next Action:** Harsha to specify concrete TANTRA SDK package version or reference architecture.
- **Responsible Person:** Harsha.

---

### DEC-INT-010: PKB-001 Niyantran Invariant Verification
- **Date:** 2026-11-04
- **Topic:** Incorporation of PKB-001 task workflow invariants.
- **Context:** Task Card E assigns Sakshi Thakur to verify append-only review decision events, single-writer concurrency protection, and cryptographic envelope validation. No PKB-001 code exists in the current SVACS workspace.
- **Evidence / Reference:** `BHIV_SEVA_Defence_Convergence_Quest_Individual_Tasks.pdf`, Page 4, Task Card E.
- **Owner:** Sakshi Thakur & Harsha.
- **Approval Status:** **PENDING CONFIRMATION**.
- **Impact on Integration:** Ensures review decision events cannot be tampered with or overwritten.
- **Open Questions:** Does Sakshi Thakur have an independent repository for PKB-001, and how does it interface with SVACS State Engine?
- **Next Action:** Coordinate with Sakshi Thakur to inspect invariant-to-test matrix and envelope contract.
- **Responsible Person:** Sakshi Thakur / Rukayya Ansari.

---

### DEC-INT-011: Quick Mode OCR Skipping (`?quick=true`)
- **Date:** 2026-08-26
- **Topic:** OCR latency tradeoff in image analysis endpoint.
- **Context:** When `quick=true` is passed to `POST /intelligence/image`, EasyOCR is skipped, reducing latency from ~15–45s down to <1s. Detections and classifications are preserved, but `ocr_results` is returned as empty `[]`.
- **Evidence / Reference:**
  - `backend/app/main.py`, line 98
  - `backend/REVIEW_PACKET.md`, line 73
  - `backend/operational_integration_sprint/REPLAY_TRACE_EVIDENCE.md`, line 136
- **Owner:** Vijay Dhawan (ML/CV) & Mohit Sharma (QA).
- **Approval Status:** **DECIDED / DOCUMENTED**.
- **Impact on Integration:** Replay consumers and QA test suites must not interpret `ocr_results: []` as an OCR subsystem crash when `quick=true` is queried.
- **Open Questions:** None.
- **Next Action:** Mohit Sharma to include `quick=true` and `quick=false` variants in positive/negative test suites.
- **Responsible Person:** Mohit Sharma (QA).

