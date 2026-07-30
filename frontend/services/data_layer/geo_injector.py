"""
SVACS — geo_injector.py
========================
Phase 3: Geospatial Event Preparation

Injects simulated geospatial coordinates into pipeline events.
Prepares events for OpenGL/map rendering on Nikhil's UI dashboard.

Coordinates are SIMULATED — based on realistic Indian Ocean /
Arabian Sea zones per vessel type. Real AIS integration is future.

Usage:
    from geo_injector import inject_geo, inject_geo_batch
    enriched_event = inject_geo(perception_event, vessel_type="cargo")
"""

import random
import time
import json
import os

# ── Geographic zones per vessel type ─────────────────────────────────────────
# Each zone is a lat/lon bounding box in the Indian Ocean / Arabian Sea region
# These are realistic operational zones for naval monitoring in this region
#
# Format: lat_range = (min_lat, max_lat), lon_range = (min_lon, max_lon)
# India's EEZ and surrounding maritime zones roughly span:
#   Latitude:  5°N to 25°N
#   Longitude: 60°E to 90°E

ZONE_CONFIGS = {
    "cargo": {
        # Cargo ships use major shipping lanes — open ocean, moderate depth
        "lat_range":  (8.0, 20.0),
        "lon_range":  (70.0, 85.0),
        "zone":       "open_ocean",
        "speed_range": (8, 15),     # cargo ships do 8-15 knots
    },
    "speedboat": {
        # Speedboats stay near coast
        "lat_range":  (10.0, 15.0),
        "lon_range":  (72.0, 76.0),
        "zone":       "coastal",
        "speed_range": (25, 45),    # speedboats do 25-45 knots
    },
    "submarine": {
        # Submarines operate in deep international waters
        "lat_range":  (5.0, 15.0),
        "lon_range":  (65.0, 80.0),
        "zone":       "international",
        "speed_range": (5, 20),     # submarines are slower
    },
    "low_confidence": {
        # Unknown distant vessel — broad area
        "lat_range":  (8.0, 18.0),
        "lon_range":  (68.0, 82.0),
        "zone":       "open_ocean",
        "speed_range": (0, 10),
    },
    "anomaly": {
        # Anomalies flagged near restricted zones
        "lat_range":  (12.0, 22.0),
        "lon_range":  (60.0, 75.0),
        "zone":       "restricted",
        "speed_range": (0, 30),     # unknown speed
    },
    "unknown": {
        # Unknown vessel — international waters
        "lat_range":  (8.0, 20.0),
        "lon_range":  (65.0, 85.0),
        "zone":       "international",
        "speed_range": (0, 20),
    },
}

# Default zone if vessel type not found
DEFAULT_ZONE = {
    "lat_range":   (10.0, 20.0),
    "lon_range":   (70.0, 80.0),
    "zone":        "open_ocean",
    "speed_range": (0, 15),
}


def inject_geo(event: dict, vessel_type: str = None) -> dict:
    """
    Inject simulated geospatial coordinates into a single pipeline event.

    Args:
        event: any pipeline event dict (perception, intelligence, or state)
        vessel_type: override vessel type for zone selection
                     (uses event's vessel_type field if not provided)

    Returns:
        New dict — original event with geo fields added.
        Does NOT modify the original event dict.

    Fields added:
        latitude, longitude, heading_degrees, speed_knots,
        operational_zone, source_confidence, geo_simulated=True
    """
    # Determine vessel type for zone selection
    vtype = vessel_type or event.get("vessel_type", "unknown")

    # Get the geographic zone config for this vessel type
    # Falls back to DEFAULT_ZONE if vessel type not in our config
    config = ZONE_CONFIGS.get(vtype, DEFAULT_ZONE)

    # Generate random coordinates within the zone
    lat = round(random.uniform(*config["lat_range"]), 6)
    lon = round(random.uniform(*config["lon_range"]), 6)

    # Generate random heading (0-360 degrees, where 0/360 = North)
    heading = round(random.uniform(0, 360), 1)

    # Generate speed within realistic range for this vessel type
    speed = round(random.uniform(*config["speed_range"]), 1)

    # Source confidence = same as classification confidence if available
    # Otherwise default to 0.5 (uncertain)
    source_conf = round(float(event.get("confidence_score") or
                              event.get("confidence") or 0.5), 4)

    # Build the geo fields dict
    geo_fields = {
        "latitude":          lat,
        "longitude":         lon,
        "heading_degrees":   heading,
        "speed_knots":       speed,
        "operational_zone":  config["zone"],
        "source_confidence": source_conf,
        "geo_simulated":     True,   # always True — we don't have real AIS
        "geo_timestamp":     time.time(),
    }

    # Return a new dict merging original event + geo fields
    # ** unpacking merges two dicts — geo_fields overrides any duplicate keys
    return {**event, **geo_fields}


def inject_geo_batch(events: list, vessel_type: str = None) -> list:
    """
    Inject geo coordinates into a list of events.
    Each event gets its own randomized coordinates.

    Args:
        events: list of pipeline event dicts
        vessel_type: if provided, use this for all events in the batch
                     otherwise each event uses its own vessel_type field

    Returns:
        List of enriched event dicts
    """
    return [inject_geo(event, vessel_type) for event in events]


def build_geo_event(event: dict, stage: str, vessel_type: str = None) -> dict:
    """
    Build a complete GeoEvent object conforming to geo_event_schema.json.
    Used specifically for feeding Nikhil's UI map layer.

    Args:
        event: pipeline event dict
        stage: "perception" | "intelligence" | "state"
        vessel_type: override vessel type

    Returns:
        GeoEvent dict ready for UI consumption
    """
    enriched = inject_geo(event, vessel_type)
    vtype    = vessel_type or event.get("vessel_type", "unknown")

    return {
        "trace_id":          event.get("trace_id"),
        "timestamp":         event.get("geo_timestamp") or time.time(),
        "latitude":          enriched["latitude"],
        "longitude":         enriched["longitude"],
        "heading_degrees":   enriched["heading_degrees"],
        "speed_knots":       enriched["speed_knots"],
        "operational_zone":  enriched["operational_zone"],
        "source_confidence": enriched["source_confidence"],
        "vessel_type":       vtype,
        "stage":             stage,
        "geo_simulated":     True,
        "anomaly_flag":      event.get("anomaly_flag"),
        "risk_level":        event.get("risk_level"),
    }


if __name__ == "__main__":
    # Self-test — inject geo into sample events for all vessel types
    print("=" * 60)
    print("  GEO INJECTOR — SELF TEST")
    print("=" * 60)

    vessel_types = ["cargo", "speedboat", "submarine",
                    "low_confidence", "anomaly", "unknown"]

    for vtype in vessel_types:
        sample_event = {
            "trace_id":       "test-trace-001",
            "vessel_type":    vtype,
            "confidence_score": 0.75,
            "anomaly_flag":   vtype in ("anomaly", "unknown"),
        }

        # inject_geo returns the event with geo fields added
        enriched = inject_geo(sample_event, vtype)

        print(f"\n  [{vtype:<16}]")
        print(f"    lat={enriched['latitude']}  lon={enriched['longitude']}")
        print(f"    heading={enriched['heading_degrees']}°  "
              f"speed={enriched['speed_knots']} knots")
        print(f"    zone={enriched['operational_zone']}")

    print("\n" + "=" * 60)
    print("  GeoEvent for UI (build_geo_event sample):")
    print("=" * 60)

    sample = {
        "trace_id":       "abc123",
        "vessel_type":    "submarine",
        "confidence_score": 0.35,
        "anomaly_flag":   True,
        "risk_level":     "CRITICAL",
    }

    geo_event = build_geo_event(sample, stage="perception", vessel_type="submarine")
    print(json.dumps(geo_event, indent=2))