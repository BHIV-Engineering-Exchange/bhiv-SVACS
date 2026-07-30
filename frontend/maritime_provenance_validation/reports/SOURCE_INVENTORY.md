# Maritime Source Inventory

Author: Nupur Gavane
Project: SVACS – Maritime Provenance and Lineage Validation
Status: Complete
Date: June 2026

---

# Purpose

This document inventories all currently observable maritime intelligence, provenance, governance, AIS, lineage, and replay sources available within the SVACS ecosystem.

The objective is to identify:

* Source origin
* Repository location
* Purpose
* Runtime usage
* Provenance relevance
* Validation status

Only directly observable repository artifacts and datasets are included.

---

# Source Category 1: AIS Sources

## AIS Observation Dataset

Location:

```text
AIS_file.xls
```

Type:

```text
External Maritime Dataset
```

Purpose:

Provides vessel observation records used for AIS validation, vessel tracking, grounding, and intelligence enrichment.

Observed Fields:

* MMSI
* BaseDateTime
* Latitude
* Longitude
* Speed Over Ground (SOG)
* VesselType

Runtime Usage:

* AIS ingestion
* Vessel observation grounding
* Intelligence enrichment
* AIS-to-Intelligence validation

Validation Status:

```text
Available
Observed
Usable
```

---

## AIS Feed Contract

Location:

```text
external_grounding/ais_feed_contract.json
```

Type:

```text
Data Contract
```

Purpose:

Defines AIS ingestion structure and expected AIS source interface.

Runtime Usage:

AIS ingestion validation.

Validation Status:

```text
Present
```

---

## AIS Ingestor

Location:

```text
external_grounding/ais_ingestor.py
```

Type:

```text
Runtime Component
```

Purpose:

Imports AIS observations into runtime processing.

Runtime Usage:

AIS ingestion pipeline.

Validation Status:

```text
Present
```

---

# Source Category 2: Jane's Maritime Intelligence Sources

## Jane's Runtime Registry

Location:

```text
maritime_knowledge/janes_runtime_registry.json
```

Type:

```text
Maritime Intelligence Registry
```

Purpose:

Provides vessel intelligence records sourced from Jane's Fighting Ships.

Observed Data:

* Vessel name
* Vessel class
* Nation
* Length
* Beam
* Displacement
* Source reference
* Edition metadata

Runtime Usage:

Knowledge grounding and maritime intelligence enrichment.

Validation Status:

```text
Active
```

---

## Jane's Provenance Manifest

Location:

```text
maritime_knowledge/janes_provenance_manifest.json
```

Type:

```text
Provenance Manifest
```

Purpose:

Documents the observable provenance chain used for maritime intelligence ingestion.

Observed Pipeline:

```text
Guptchar Ingestion
→ Samachar Processing
→ Maritime Knowledge Store
```

Observed Status:

```text
lineage_status = ACTIVE
replay_safe = true
```

Validation Status:

```text
Active
```

---

## Jane's Ingestion Pipeline

Location:

```text
external_grounding/janes_ingestion_pipeline.py
```

Type:

```text
Runtime Component
```

Purpose:

Imports Jane's maritime intelligence data into runtime registries.

Validation Status:

```text
Present
```

---

# Source Category 3: Maritime Knowledge Sources

## Maritime Knowledge Registry

Location:

```text
maritime_knowledge/maritime_knowledge_registry.json
```

Type:

```text
Knowledge Registry
```

Purpose:

Primary maritime knowledge source used for intelligence grounding.

Observed Data:

* Vessel identifiers
* Vessel class
* Nation
* Dimensions
* Displacement
* Propulsion
* Operational role
* Radar signature
* Source reference
* Source version

Source Attribution:

```text
Jane's Fighting Ships
```

Runtime Usage:

Knowledge enrichment and intelligence generation.

Validation Status:

```text
Active
```

---

# Source Category 4: Fleet History Sources

## Fleet History Registry

Location:

```text
maritime_knowledge/fleet_history_registry.json
```

Type:

```text
Historical Maritime Registry
```

Purpose:

Stores fleet evolution and historical vessel-class progression information.

Observed Examples:

```text
Delhi Class → Kolkata Class → Visakhapatnam Class

Spruance → Arleigh Burke
```

Runtime Usage:

Historical context and fleet lineage validation.

Validation Status:

```text
Active
```

---

# Source Category 5: Vessel Lineage Sources

## Vessel Lineage Registry

Location:

```text
maritime_knowledge/vessel_lineage_registry.json
```

Type:

```text
Lineage Registry
```

Purpose:

Stores predecessor-successor relationships between vessel classes.

Observed Examples:

```text
Delhi Class
↓
Kolkata Class
↓
Visakhapatnam Class
```

```text
Spruance
↓
Arleigh Burke
↓
DDG(X)
```

Runtime Usage:

Vessel lineage reconstruction and provenance validation.

Validation Status:

```text
Active
```

---

# Source Category 6: Governance Sources

## Dataset Governance Registry

Location:

```text
governance/dataset_governance_registry.json
```

Type:

```text
Governance Registry
```

Observed Metadata:

* Dataset ID
* Dataset Owner
* Dataset Origin
* Trust Score
* Approval State
* Validation Status
* Source Confidence

Runtime Usage:

Dataset trust and governance validation.

Validation Status:

```text
Approved
```

---

## Governance Schema

Location:

```text
governance/dataset_governance_schema.json
```

Purpose:

Defines governance structure for dataset registration.

Validation Status:

```text
Present
```

---

## Governance Validator

Location:

```text
governance/dataset_governance_validator.py
```

Purpose:

Runtime governance validation component.

Validation Status:

```text
Present
```

---

# Source Category 7: Lineage Sources

## Runtime Lineage Report

Location:

```text
lineage/runtime_lineage_report.json
```

Type:

```text
Runtime Lineage Evidence
```

Observed Metadata:

```text
lineage_status = ACTIVE
runtime_tracking = true
replay_tracking = true
bucket_tracking = true
```

Purpose:

Provides runtime lineage validation evidence.

Validation Status:

```text
Active
```

---

# Source Category 8: Replay Sources

## Replay Engine Components

Locations:

```text
replay/replay_engine.py

replay/provenance_reconstruction.py

replay/intelligence_lineage.py

replay/execution_replay.py

replay/full_operational_replay.py
```

Type:

```text
Replay Infrastructure
```

Purpose:

Supports reconstruction of execution history, lineage reconstruction, and provenance replay validation.

Validation Status:

```text
Present
```

---

# Inventory Summary

| Category                   | Status    |
| -------------------------- | --------- |
| AIS Sources                | Available |
| Jane's Sources             | Available |
| Maritime Knowledge Sources | Available |
| Fleet History Sources      | Available |
| Vessel Lineage Sources     | Available |
| Governance Sources         | Available |
| Runtime Lineage Sources    | Available |
| Replay Sources             | Available |

---

# Conclusion

The SVACS repository currently contains observable AIS, maritime knowledge, fleet history, vessel lineage, governance, lineage, and replay artifacts sufficient to support provenance validation, trace continuity analysis, AIS-to-intelligence validation, replay reconstruction validation, and evidence packet generation activities.
