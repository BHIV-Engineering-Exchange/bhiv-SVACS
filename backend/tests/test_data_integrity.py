"""Data integrity tests for the naval reference data.

The classifier outputs a label that is simply the name of a training
folder. Several lookups (risk level, ship roster, type cross-check) match
that label by exact string, so any drift between these files fails
silently at runtime. These tests make that drift fail loudly instead.

If a class is added to or removed from training, update
EXPECTED_NAVAL_CLASSES below and the failing tests will point to every
file that must change with it.
"""

import json
import re
from pathlib import Path

import pytest

from app.services import naval_identifier as ni
from app.services import ship_identifier as si

# Exact labels the classifier can output for naval vessels, i.e. the names
# of the training folders produced by consolidate_naval_dataset.ps1.
# "OSV Class" is deliberately absent: it is civilian.
EXPECTED_NAVAL_CLASSES = {
    "Vikrant",
    "Vikramaditya",
    "Visakhapatnam Class",
    "Kolkata Class",
    "Delhi Class",
    "Rajput Class",
    "Nilgiri Class",
    "Shivalik Class",
    "Talwar Class",
    "Brahmaputra Class",
    "Arihant Class",
    "Kalvari Class",
    "Shishumar Class",
    "Sindhughosh Class",
    "Arnala Class",
    "Mahe Class",
    "Kamorta Class",
    "Kora Class",
    "Khukri Class",
    "Veer Class",
}

VALID_RISK_LEVELS = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}

TYPE_KEYWORD = {
    "Destroyer": "destroyer",
    "Frigate": "frigate",
    "Corvette": "corvette",
    "Aircraft Carrier": "aircraft carrier",
    "Submarine": "submarine",
}

# Risk policy by vessel type, with the one submarine exception (strategic SSBN).
RISK_BY_TYPE = {
    "Destroyer": "CRITICAL",
    "Aircraft Carrier": "CRITICAL",
    "Frigate": "HIGH",
    "Corvette": "MEDIUM",
    "Submarine": "HIGH",
}
RISK_OVERRIDES = {"Arihant Class": "CRITICAL"}


@pytest.fixture(scope="module")
def pack():
    return ni.load_knowledge_pack()


@pytest.fixture(scope="module")
def registry():
    return si.load_ship_registry()


class TestClassNamesMatchTheClassifier:
    def test_knowledge_pack_names_match_classifier_labels(self, pack):
        assert {e["class_name"] for e in pack} == EXPECTED_NAVAL_CLASSES

    def test_knowledge_pack_has_no_duplicate_class_names(self, pack):
        names = [e["class_name"] for e in pack]
        assert len(names) == len(set(names))

    def test_ship_registry_keys_match_classifier_labels(self, registry):
        assert set(registry.keys()) == EXPECTED_NAVAL_CLASSES

    def test_class_to_type_keys_match_classifier_labels(self):
        assert set(si.CLASS_TO_TYPE.keys()) == EXPECTED_NAVAL_CLASSES


class TestKnowledgePackEntries:
    def test_required_fields_present_and_dimensions_numeric(self, pack):
        required = {"vessel_id", "class_name", "vessel_type", "risk_level", "validation_status"}
        for entry in pack:
            assert required <= set(entry), entry["class_name"]
            for field in ("length_m", "beam_m", "displacement_tons"):
                assert isinstance(entry[field], (int, float)), (entry["class_name"], field)
                assert entry[field] > 0, (entry["class_name"], field)

    def test_vessel_ids_are_unique(self, pack):
        ids = [e["vessel_id"] for e in pack]
        assert len(ids) == len(set(ids))

    def test_risk_levels_are_valid(self, pack):
        for entry in pack:
            assert entry["risk_level"] in VALID_RISK_LEVELS, entry["class_name"]

    def test_risk_level_follows_the_vessel_type_policy(self, pack):
        for entry in pack:
            name = entry["class_name"]
            expected = RISK_OVERRIDES.get(name, RISK_BY_TYPE[si.CLASS_TO_TYPE[name]])
            assert entry["risk_level"] == expected, name

    def test_vessel_type_text_agrees_with_the_type_mapping(self, pack):
        for entry in pack:
            keyword = TYPE_KEYWORD[si.CLASS_TO_TYPE[entry["class_name"]]]
            assert keyword in entry["vessel_type"].lower(), entry["class_name"]


class TestShipRegistry:
    def test_every_class_has_a_nonempty_well_formed_roster(self, registry):
        for class_name, ships in registry.items():
            assert ships, class_name
            for ship in ships:
                assert ship["name"].startswith("INS "), (class_name, ship)
                assert re.fullmatch(r"[A-Z]\d{1,3}", ship["pennant"]), (class_name, ship)

    def test_pennant_numbers_are_unique_across_all_classes(self, registry):
        pennants = [s["pennant"] for ships in registry.values() for s in ships]
        duplicates = {p for p in pennants if pennants.count(p) > 1}
        assert not duplicates, duplicates

    def test_ship_names_are_unique_across_all_classes(self, registry):
        names = [s["name"] for ships in registry.values() for s in ships]
        duplicates = {n for n in names if names.count(n) > 1}
        assert not duplicates, duplicates

    def test_every_pennant_prefix_agrees_with_its_class_type(self, registry):
        for class_name, ships in registry.items():
            expected = si.CLASS_TO_TYPE[class_name]
            for ship in ships:
                assert si.PENNANT_PREFIX_TO_TYPE[ship["pennant"][0]] == expected, (class_name, ship)


class TestPackAndRegistryAgree:
    def test_every_active_ship_in_the_registry_is_named_in_the_pack(self, pack, registry):
        """The pack may list extra hulls that are not yet active, but must
        never omit or misspell a ship the registry knows about."""
        problems = []
        for entry in pack:
            known = set(entry["vessel_names"])
            for ship in registry[entry["class_name"]]:
                if ship["name"] not in known:
                    problems.append((entry["class_name"], ship["name"]))
        assert not problems, problems


class TestCopiesStayInSync:
    """The reference data exists twice: backend/maritime_knowledge (what the
    backend loads) and maritime_knowledge at the repo root. Drift between the
    two caused a real bug, so compare the parsed contents."""

    @pytest.mark.parametrize(
        "filename", ["indian_naval_knowledge_pack.json", "ship_registry.json"]
    )
    def test_root_copy_matches_backend_copy(self, filename):
        backend_dir = Path(ni.KNOWLEDGE_PACK_PATH).parents[1]
        backend_copy = backend_dir / "maritime_knowledge" / filename
        root_copy = backend_dir.parent / "maritime_knowledge" / filename
        if not root_copy.exists():
            pytest.skip("repo-root copy not present (backend deployed on its own)")
        with open(backend_copy, encoding="utf-8-sig") as a, open(root_copy, encoding="utf-8-sig") as b:
            assert json.load(a) == json.load(b)
