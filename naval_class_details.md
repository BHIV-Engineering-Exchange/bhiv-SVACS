# Naval Class Details — Reference Table

**Source:** `maritime_knowledge/indian_naval_knowledge_pack.json`
**Purpose:** Quick reference for the fields a user can supply to the Naval Vessel Identifier (length, beam, draft, displacement, vessel type). Used for testing and for briefing others on what data exists.

---

| Class | Vessel Type | Length (m) | Beam (m) | Draft (m) | Displacement (tons) | Risk Level |
|---|---|---|---|---|---|---|
| Kolkata Class | Destroyer | 163.0 | 17.4 | 6.5 | 7,500 | CRITICAL |
| Visakhapatnam Class (incl. INS Mormugao) | Destroyer | 163.0 | 17.4 | 6.5 | 7,400 | CRITICAL |
| Talwar Class | Frigate | 124.8 | 15.2 | 4.2 | 4,035 | HIGH |
| Delhi Class | Destroyer | 163.0 | 17.0 | 6.5 | 6,900 | CRITICAL |
| Shivalik Class | Frigate | 142.5 | 16.9 | 4.5 | 6,200 | HIGH |
| Nilgiri Class | Frigate | 149.0 | 17.8 | 4.5 | 6,670 | HIGH |
| Kamorta Class | Corvette | 109.0 | 12.8 | 4.5 | 3,300 | MEDIUM |
| INS Vikrant | Aircraft Carrier | 262.5 | 62.0 | 8.4 | 45,000 | CRITICAL |
| INS Vikramaditya | Aircraft Carrier | 283.5 | 59.8 | 10.2 | 44,500 | CRITICAL |
| Arihant Class | Submarine (SSBN) | 111.0 | 11.0 | Classified | 6,000 | CRITICAL |
| Kalvari Class | Submarine (SSK) | 67.5 | 6.2 | 5.8 | 1,615 | HIGH |

---

## Known Gaps

- **Hull colour** is not a discriminating field — all 11 classes are standard naval grey. The matching tool only gives colour a weak +5 point signal for this reason.
- **Height/freeboard** was never curated in the knowledge pack and is not available. Not fabricated here — flagged as a genuine gap if it's needed later.
- **Arihant Class draft** is not reliably available in public sources and is marked Classified rather than estimated, per the task's instruction not to claim unverified operational detail.

## Note on Similar Dimensions

Kolkata, Visakhapatnam, and Delhi Class all share nearly identical length/beam/draft (~163m / 17m / 6.5m). Dimensions alone cannot reliably separate these three — the free-text description field (funnel count, superstructure shape, mast/radar profile) is what actually discriminates between them in the matching tool.
