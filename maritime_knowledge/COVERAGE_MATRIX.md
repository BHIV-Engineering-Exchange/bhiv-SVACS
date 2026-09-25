# SVACS — Indian Naval Knowledge Pack: Coverage Matrix

**Author:** Nupur Gavane
**Task:** SVACS Indian Maritime Knowledge Pack & Samachar Grounding
**Date:** August 2026
**Source file:** `maritime_knowledge/indian_naval_knowledge_pack.json`

---

## Field Coverage Per Class

Legend: ✅ Present and plausible | ⚠️ Present but unverified against a second source | ❌ Missing / not publicly available | 🔒 Genuinely classified, deliberately not estimated

| Class | Dimensions/Displacement | Propulsion | Hull/Superstructure | Mast/Radar/Funnel | Lineage | Images | Cross-verified? |
|---|---|---|---|---|---|---|---|
| Kolkata Class | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ❌ | No |
| Visakhapatnam Class / INS Mormugao | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ❌ | No |
| Talwar Class | ✅ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ❌ | **Yes** — cross-checked against existing `janes_runtime_registry.json` entry |
| Delhi Class | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ❌ | **Partial** — lineage cross-checked against existing `vessel_lineage_registry.json` |
| Shivalik Class | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ✅ | ❌ | **Partial** — lineage cross-checked against existing `vessel_lineage_registry.json` |
| Nilgiri Class | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ❌ | No — note: minor date discrepancy found (this pack says commissioned 2024, `fleet_history_registry.json` says introduced 2025 — unresolved) |
| Kamorta Class | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ❌ | No |
| INS Vikrant | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ❌ | No |
| INS Vikramaditya | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | ❌ | No |
| Arihant Class | ⚠️ (partial) | ⚠️ | 🔒 | 🔒 | ⚠️ | ❌ | No — several fields deliberately marked classified/unavailable rather than estimated |
| Kalvari Class | ⚠️ | ⚠️ | ⚠️ | 🔒 (partial) | ⚠️ | ❌ | No |

---

## Summary

- **11 of 11 classes have a base data entry.** No class is entirely missing.
- **0 of 11 classes have verified images.** This is the single largest gap across the whole pack — every class currently has zero curated multi-angle images, which the task requires "at minimum."
- **3 of 11 classes have at least one field cross-verified** against pre-existing SVACS registry data (Talwar, Delhi, Shivalik) — everything else is currently single-source compilation, not yet independently confirmed.
- **2 classes (Arihant, Kalvari)** have deliberately incomplete fields where genuine classification/unavailability made further detail inappropriate to estimate, per the task's own instruction not to claim unverified operational truth.
- **1 unresolved cross-source discrepancy** — Nilgiri Class commissioning year (2024 vs. 2025 across two sources).

## Recommended Next Priority

Given the above, the highest-value next step is **image sourcing** — it's the most complete gap (0/11) and is explicitly required "at minimum" per the task. Spec verification (moving ⚠️ to ✅) is valuable but lower urgency, since the underlying values are plausible and already flagged as unverified rather than presented as confirmed.
