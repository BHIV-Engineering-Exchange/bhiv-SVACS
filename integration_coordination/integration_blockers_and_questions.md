# BHIV × SEVA Defence Convergence Quest — Integration Blockers and Questions

**Work Package:** Integration Coordination  
**Lead / Owner:** Rukayya Ansari  
**Date of Audit:** November 04, 2026  
**Audited Target Workspace:** `c:\Users\rukka\OneDrive\Desktop\Rukayya\bhiv-SVACS-main`  
**Governing Directive:** `BHIV_SEVA_Defence_Convergence_Quest_Individual_Tasks.pdf`

---

## 1. Executive Summary

This document consolidates all critical technical blockers, interface ambiguities, and coordination questions required to progress the integration across **SVACS**, **Signals Corps/C5SIR**, and **BIQOS**.

Each item specifies:
1. **Target Stakeholder**: Assigned role from the Quest Brief.
2. **Specific Information Needed**: Concrete data, specification, or architectural decision.
3. **Operational Justification**: Why this information is strictly necessary.
4. **Integration Impact**: Consequences if unresolved.
5. **Concrete Next Action**: Accountable next step and deadline.

---

## 2. Blockers and Questions by Stakeholder

### 2.1 SVACS Domain Owners (Ankita / Nupur Gavane / Vijay Dhawan)

#### BLK-SVACS-01: Trace ID vs Replay ID Reconciliation
- **Responsible Owner:** Ankita (SVACS Runtime & Trace Design) & Vijay Dhawan (ML/CV)
- **Information Needed:** Canonical decision on unifying the HTTP-layer `trace_id` and the orchestrator `replay_id` in `backend/app/main.py`.
- **Why Required:** Currently, `POST /intelligence/image` generates `trace_id` for the HTTP response, while `vision_orchestrator.py` generates a separate `replay_id` saved to `contract.json`, `metadata.json`, and passed to Bucket.
- **Integration Impact:** Downstream systems (TANTRA SDK, Bucket audit, State Engine) cannot reliably correlate vision analysis with subsequent state events using a single trace identifier.
- **Next Action:** Ankita to confirm whether `vision_orchestrator.process_bytes()` should accept an optional `trace_id: Optional[str] = None` parameter so the API layer's ID is used universally.
- **Target Window:** Hour 0–4 baseline checkpoint.

#### BLK-SVACS-02: Portable Replay Directory Path
- **Responsible Owner:** Vijay Dhawan (Backend Maintainer) & Rayyan (DevOps)
- **Information Needed:** Approval to migrate `REPLAY_STORAGE_DIR` in `backend/app/core/config.py` from hardcoded `C:\tmp\svacs_replays` to a project-relative or environment-configurable path.
- **Why Required:** The hardcoded Windows path fails in Linux containers, fresh developer clones, and CI/CD runners without manual filesystem modification.
- **Integration Impact:** Harsha and Rayyan cannot independently reproduce test evidence in a clean environment, failing Gate 6.
- **Next Action:** Rayyan to update `config.py` with `os.getenv("REPLAY_STORAGE_DIR", os.path.join(ROOT, "replays"))`.
- **Target Window:** Hour 4–24.

---

### 2.2 Signals Corps / C5SIR Domain Owner (TBD / Unconfirmed)

#### BLK-C5SIR-01: Confirmation of Named Domain Authority & Interface Contact
- **Responsible Owner:** Signals Corps Domain Owner (To be named by Signals Corps team)
- **Information Needed:** Official appointment of the domain owner, interface engineer contact, and working communication channel.
- **Why Required:** Task Card K explicitly mandates an approved interface outline.names marked "TBD/confirm" cannot be assumed to be available.
- **Integration Impact:** **CRITICAL BLOCKER**. Without a domain owner, no specifications can be approved, no data boundaries agreed, and no joint demonstrator built.
- **Next Action:** Shivam Pal (Delivery Commander) to escalate to leadership to confirm the named domain contact by Hour 4.
- **Target Window:** Hour 0–4 checkpoint.

#### BLK-C5SIR-02: Non-Sensitive Signal Specification & Data Boundary
- **Responsible Owner:** Signals Corps Domain Owner & Ansh Gupta (Governance)
- **Information Needed:** Interface schema, transport protocol (REST, gRPC, WebSocket), telemetry format (frequency, bandwidth, framing), and non-sensitive sample datasets.
- **Why Required:** Quest boundary strictly prohibits unapproved or classified data. The integration team requires approved development data.
- **Integration Impact:** No adapter can be implemented by Rukayya or tested by Mohit.
- **Next Action:** Rukayya to transmit the Integration Intake Questionnaire upon domain owner confirmation.
- **Target Window:** Hour 4–24.

---

### 2.3 BIQOS / Technical Governance Owner (TBD / Harsha)

#### BLK-BIQOS-01: TANTRA SDK Package Distribution & Integration Guide
- **Responsible Owner:** BIQOS Technical Owner & Harsha (Architecture Authority)
- **Information Needed:** Python wheel or package coordinates for TANTRA SDK, along with official KSML and MDU schema validators.
- **Why Required:** The brief specifies: *"Use TANTRA SDK for approved service discovery/authentication/contracts/traceability; KSML and MDU for approved semantics."* No TANTRA SDK library is currently available in the repository.
- **Integration Impact:** Systems remain connected via ad-hoc REST/JSON calls without formal BIQOS governance, risking compliance rejection.
- **Next Action:** Harsha to define whether TANTRA SDK is required as an imported dependency or if its governance invariants are verified via adapter wrappers.
- **Target Window:** Hour 4–24.

#### BLK-BIQOS-02: MASTERDB / God's Eye View Connection & Schema
- **Responsible Owner:** Data / Source Owner (TBD) & Harsha
- **Information Needed:** MasterDB host address, authentication credentials, schema definition, and access permissions.
- **Why Required:** Brief Section 4 mandates: *"MasterDB/God's Eye View/other store: exact location, owner, access permission, dataset inventory, freshness and provenance. Availability must be confirmed, not inferred from product names."*
- **Integration Impact:** **BLOCKER**. Currently, SVACS relies solely on a local static JSON file (`vessel_registry.json`). MasterDB cannot be claimed as integrated without verifiable access.
- **Next Action:** Shivam Pal to determine whether MasterDB access can be cleared within the 72-hour window; if not, freeze the fallback to explicitly labelled static analogues.
- **Target Window:** Hour 0–4 checkpoint.

---

### 2.4 Architecture Authority & Independent Acceptance (Harsha)

#### BLK-ARCH-01: Backend Architecture Duality & Single Demonstrator Build
- **Responsible Owner:** Harsha (Architecture Authority) & Rayyan (DevOps)
- **Information Needed:** Architectural sign-off on consolidating `backend/app/main.py` and `frontend/services/api/main_api.py`.
- **Why Required:** `backend/app/main.py` handles the vision runtime but stubs out pipeline telemetry (signals, perception, intelligence, alerts). `frontend/services/api/main_api.py` handles historical log streaming but proxies images to a stale ngrok URL.
- **Integration Impact:** The Vite UI either has a working vision tab with blank telemetry pages, or working telemetry pages with broken image uploads. Violates the core objective: *"Deliver one coherent, working demonstrator rather than separate products stitched together."*
- **Next Action:** Harsha to approve merging vision orchestrator endpoints into `main_api.py` (or extending `backend/app/main.py` with real pipeline state).
- **Target Window:** Hour 4–24.

#### BLK-ARCH-02: Primary Demonstrator Scope Freeze
- **Responsible Owner:** Harsha & Shivam Pal
- **Information Needed:** Formal approval of the frozen minimum demonstrator scope: "Maritime Component Traceability and Surveillance Lifecycle Intelligence".
- **Why Required:** Stage 0 gate requires: *"Shared workspace, source/repository inventory, current-state register, scope freeze... Gate: baseline approved; no assumed integration."*
- **Integration Impact:** Prevents drift into unachievable autonomy or robotics tracks (Stage 5).
- **Next Action:** Record formal scope freeze in `integration_decision_log.md` (DEC-INT-001).
- **Target Window:** Hour 0–4.

---

### 2.5 Delivery Lead (Shivam Pal)

#### BLK-DEL-01: Cross-Team Dependency Assignment & Unblocking
- **Responsible Owner:** Shivam Pal (Delivery Commander)
- **Information Needed:** Assignment of named owners for unassigned dependencies (Signals Corps lead, MasterDB owner, Samachar integration contact).
- **Why Required:** The brief requires: *"Every unresolved dependency has an owner and status."*
- **Integration Impact:** Work cannot proceed across team boundaries without clear ownership.
- **Next Action:** Shivam Pal to publish the daily checkpoint owner register with named individuals for all blocked tracks.
- **Target Window:** Daily 15-minute checkpoint.

#### BLK-DEL-02: SEVA Submission Claim Verification
- **Responsible Owner:** Shivam Pal & Ansh Gupta
- **Information Needed:** Review of SEVA form draft wording against the Integration Matrix.
- **Why Required:** Mandatory release gate: *"SEVA application claims match recorded evidence; no unverified production, certification or procurement claims."*
- **Integration Impact:** Prevents non-compliant submission claims.
- **Next Action:** Rukayya to provide the completed `integration_matrix.csv` to Shivam and Ansh for line-by-line verification.
- **Target Window:** Hour 48–72.

---

### 2.6 DevOps, CI/CD & Deployment (Rayyan)

#### BLK-OPS-01: Bucket Service Local / Staging Hosting Strategy
- **Responsible Owner:** Rayyan (DevOps) & Siddhesh Narkar (Bucket Owner)
- **Information Needed:** Decision and runbook for running a local containerized Bucket instance or keeping Render warm.
- **Why Required:** Live test attempts against Render failed twice with HTTP 503. A failing dependency prevents automated contract testing and demonstrator execution.
- **Integration Impact:** Cannot demonstrate tamper-proof chained audit trail in live evaluation.
- **Next Action:** Rayyan to create a local Docker compose profile or background startup script for `bhiv-bucket`.
- **Target Window:** Hour 4–24.

#### BLK-OPS-02: Reproducible Environment & Service Orchestration
- **Responsible Owner:** Rayyan
- **Information Needed:** Single repeatable startup script (e.g. `run-demonstrator.cmd` or `docker-compose.yml`) that starts backend, frontend, and local dependencies with verified health checks.
- **Why Required:** Handover package mandates a reproducible deployment bundle and runbook.
- **Integration Impact:** Testing and independent reproduction by Harsha is blocked if services must be manually stitched together.
- **Next Action:** Rayyan to integrate backend and frontend startup into a validated runbook.
- **Target Window:** Hour 24–48.

---

### 2.7 QA & Evidence Verification (Mohit Sharma)

#### BLK-QA-01: Acceptance Checklist & Negative Test Execution
- **Responsible Owner:** Mohit Sharma (QA)
- **Information Needed:** Execution schedule and test plan for negative paths (malformed image, corrupted UUID, offline bucket, timeout).
- **Why Required:** Acceptance scorecard allocates 10% to testing and recovery (positive/negative tests, retry/timeout, recovery results).
- **Integration Impact:** Defect severity cannot be assessed without negative testing.
- **Next Action:** Mohit to execute test cases derived from `contract_test_status.md` and report pass/fail evidence.
- **Target Window:** Hour 24–48.

---

### 2.8 Upstream Ingestion & Intelligence Partners (Chandragupta & Sakshi Thakur)

#### BLK-PART-01: Samachar Ingestion Contract (Chandragupta)
- **Responsible Owner:** Chandragupta & Om Patil (Samachar)
- **Information Needed:** OpenAPI specification, schema definition, and active endpoint for Samachar image ingestion.
- **Why Required:** Required chain in brief includes Samachar between Image Ingestion and SVACS.
- **Integration Impact:** Demonstrator must continue using direct client upload workaround until Samachar is connected.
- **Next Action:** Rukayya to coordinate with Chandragupta for contract alignment.
- **Target Window:** Hour 4–24.

#### BLK-PART-02: PKB-001 Invariant Matrix & Envelope Contract (Sakshi Thakur)
- **Responsible Owner:** Sakshi Thakur (Intelligence Integration & PKB Invariants)
- **Information Needed:** Invariant-to-test matrix and cryptographic envelope schema for PKB-001 Niyantran task workflow.
- **Why Required:** Brief Task Card E requires verification of append-only review decision events and single-writer concurrency.
- **Integration Impact:** Cannot claim cryptographic envelope validation without Sakshi's contract.
- **Next Action:** Sakshi Thakur to supply test evidence and envelope specifications to Integration Coordination.
- **Target Window:** Hour 4–24.

