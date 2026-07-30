# Provenance Manifests

Author: Nupur Gavane
Project: SVACS – Maritime Provenance and Lineage Validation
Status: Complete
Date: June 2026

---

# Purpose

This document establishes provenance manifests for all observable maritime intelligence, AIS, governance, lineage, and knowledge-grounding datasets currently present within the SVACS ecosystem.

The objective is to document:

* Dataset origin
* Ownership
* Repository location
* Runtime usage
* Trust indicators
* Lineage participation
* Replay participation

Only directly observable repository artifacts are included.

---

# Manifest 01 – AIS Feed Dataset

Dataset ID:

```text id="hfq95p"
AIS_FEED_001
```

Dataset Type:

```text id="gz5qyj"
AIS Observation Dataset
```

Repository Evidence:

```text id="avte3n"
AIS_file.xls

external_grounding/ais_ingestor.py

external_grounding/ais_feed_contract.json
```

Origin:

```text id="m8vz4m"
AIS
```

Owner:

```text id="6j23ya"
SVACS
```

Trust Indicators:

```text id="xekbgr"
dataset_trust_score = 92

approval_state = APPROVED

validation_status = VALID

source_confidence = HIGH
```

Runtime Participation:

```text id="gjr1m4"
AIS Ingestion
AIS Grounding
AIS Validation
Intelligence Enrichment
```

Lineage Participation:

```text id="0t7fwa"
Yes
```

Replay Participation:

```text id="hknb3q"
Yes
```

Manifest Status:

```text id="xh9v5y"
Active
```

---

# Manifest 02 – Jane's Maritime Intelligence Dataset

Dataset Type:

```text id="3xksmu"
Maritime Intelligence Dataset
```

Repository Evidence:

```text id="ly2ecg"
maritime_knowledge/janes_runtime_registry.json

external_grounding/janes_ingestion_pipeline.py
```

Origin:

```text id="qg8nzh"
Jane's Fighting Ships
```

Owner:

```text id="xh5jlt"
SVACS Maritime Knowledge Layer
```

Observed Metadata:

```text id="7odm6j"
Vessel Name
Vessel Class
Nation
Length
Beam
Displacement
Edition
Page Reference
```

Runtime Participation:

```text id="v5jlwm"
Knowledge Grounding
Registry Enrichment
Maritime Intelligence Generation
```

Lineage Participation:

```text id="2sm4yb"
Yes
```

Replay Participation:

```text id="c7r63v"
Yes
```

Manifest Status:

```text id="mwvpgs"
Active
```

---

# Manifest 03 – Maritime Knowledge Registry

Dataset Type:

```text id="c5s6ca"
Knowledge Registry
```

Repository Evidence:

```text id="q9qkeb"
maritime_knowledge/maritime_knowledge_registry.json
```

Origin:

```text id="37r3hq"
Jane's Fighting Ships
```

Observed Metadata:

```text id="8ho0ow"
Vessel Class
Nation
Dimensions
Displacement
Propulsion
Operational Role
Radar Signature
Source Reference
```

Runtime Participation:

```text id="o7hj7t"
Knowledge Grounding
Maritime Enrichment
Intelligence Support
```

Lineage Participation:

```text id="38pajw"
Yes
```

Replay Participation:

```text id="dfz8lv"
Yes
```

Manifest Status:

```text id="x09qf7"
Active
```

---

# Manifest 04 – Fleet History Registry

Dataset Type:

```text id="a9yucb"
Historical Fleet Registry
```

Repository Evidence:

```text id="tm0glw"
maritime_knowledge/fleet_history_registry.json
```

Observed Scope:

```text id="88m1db"
Fleet Evolution
Historical Fleet Progression
Class Introduction History
```

Observed Examples:

```text id="q6m2u3"
Delhi Class Destroyer

Kolkata Class Destroyer

Visakhapatnam Class Destroyer
```

Runtime Participation:

```text id="s5qjgt"
Historical Context
Fleet Validation
Fleet Lineage Analysis
```

Lineage Participation:

```text id="udx9eo"
Yes
```

Replay Participation:

```text id="ehyb9l"
Indirect
```

Manifest Status:

```text id="byquk4"
Active
```

---

# Manifest 05 – Vessel Lineage Registry

Dataset Type:

```text id="0c0h9n"
Lineage Registry
```

Repository Evidence:

```text id="tt45hn"
maritime_knowledge/vessel_lineage_registry.json
```

Observed Scope:

```text id="0xrgz5"
Predecessor Relationships
Successor Relationships
Class Evolution Chains
```

Observed Examples:

```text id="nktm5h"
Delhi Class
→ Kolkata Class
→ Visakhapatnam Class

Spruance
→ Arleigh Burke
→ DDG(X)
```

Runtime Participation:

```text id="29cnv6"
Lineage Validation
Historical Correlation
Class Evolution Analysis
```

Lineage Participation:

```text id="6u4lfr"
Primary Source
```

Replay Participation:

```text id="8r2y7q"
Indirect
```

Manifest Status:

```text id="sjlf5n"
Active
```

---

# Manifest 06 – Governance Registry

Dataset Type:

```text id="mkhdff"
Governance Registry
```

Repository Evidence:

```text id="myovd6"
governance/dataset_governance_registry.json

governance/dataset_governance_schema.json

governance/dataset_governance_validator.py
```

Observed Governance Fields:

```text id="olgc2j"
Dataset Owner
Dataset Origin
Trust Score
Approval State
Validation Status
Source Confidence
```

Runtime Participation:

```text id="tw2lzv"
Governance Validation
Trust Validation
Source Validation
```

Lineage Participation:

```text id="lqbjlwm"
Yes
```

Replay Participation:

```text id="r4h52g"
Yes
```

Manifest Status:

```text id="r78t7l"
Active
```

---

# Manifest 07 – Runtime Lineage Dataset

Dataset Type:

```text id="nobv5h"
Lineage Evidence Dataset
```

Repository Evidence:

```text id="o1pkdx"
lineage/runtime_lineage_report.json
```

Observed Metadata:

```text id="akp06e"
lineage_status = ACTIVE

runtime_tracking = true

replay_tracking = true

bucket_tracking = true
```

Runtime Participation:

```text id="ahq0r8"
Runtime Validation
Trace Validation
Replay Validation
```

Lineage Participation:

```text id="93l8yi"
Primary Source
```

Replay Participation:

```text id="n1mfxe"
Primary Source
```

Manifest Status:

```text id="1v7h5u"
Active
```

---

# Provenance Summary

| Dataset                     | Lineage | Replay   | Status |
| --------------------------- | ------- | -------- | ------ |
| AIS Feed Dataset            | Yes     | Yes      | Active |
| Jane's Runtime Registry     | Yes     | Yes      | Active |
| Maritime Knowledge Registry | Yes     | Yes      | Active |
| Fleet History Registry      | Yes     | Indirect | Active |
| Vessel Lineage Registry     | Yes     | Indirect | Active |
| Governance Registry         | Yes     | Yes      | Active |
| Runtime Lineage Dataset     | Yes     | Yes      | Active |

---

# Conclusion

Observable SVACS datasets demonstrate documented provenance, identifiable ownership, governance visibility, lineage participation, and replay compatibility. The current repository contains sufficient provenance artifacts to support lineage validation, trace continuity validation, AIS-to-intelligence validation, replay validation, and review packet generation activities.
