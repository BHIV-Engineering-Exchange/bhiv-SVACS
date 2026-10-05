"""Unit tests for app/services/ship_identifier.py

Covers pennant-number extraction from OCR text, matching a pennant to a
named ship inside a class roster, and the cross-check between the
predicted class's vessel type and the type implied by a pennant's prefix
letter.
"""

import pytest

from app.services import ship_identifier as si


class TestExtractPennantCandidates:
    def test_plain_pennant(self):
        assert si.extract_pennant_candidates("D63") == ["D63"]

    def test_pennant_inside_noisy_text(self):
        assert "D63" in si.extract_pennant_candidates("INS KOLKATA D63 stbd side")

    @pytest.mark.parametrize("text", ["D 63", "D-63", "d63", "d 63", "d-63"])
    def test_separator_and_case_variants_normalise(self, text):
        assert si.extract_pennant_candidates(text) == ["D63"]

    @pytest.mark.parametrize("text", [None, "", "INS", "12345", "no pennant here"])
    def test_text_without_a_pennant_returns_empty_list(self, text):
        assert si.extract_pennant_candidates(text) == []

    def test_multiple_candidates_keep_reading_order(self):
        assert si.extract_pennant_candidates("S21 then D63") == ["S21", "D63"]

    def test_digit_runs_longer_than_three_are_not_read_as_pennants(self):
        assert si.extract_pennant_candidates("D6300") == []


class TestIdentifyShip:
    def test_matching_pennant_identifies_the_specific_ship(self):
        result = si.identify_ship("Kolkata Class", "D63")
        assert result["matched"] is True
        assert result["ship_name"] == "INS Kolkata"
        assert result["pennant"] == "D63"
        assert result["method"] == "ocr_pennant_match"

    def test_every_registry_ship_is_found_by_its_own_pennant(self):
        registry = si.load_ship_registry()
        for class_name, ships in registry.items():
            for ship in ships:
                result = si.identify_ship(class_name, ship["pennant"])
                assert result["matched"], (class_name, ship)
                assert result["ship_name"] == ship["name"], (class_name, ship)

    def test_pennant_belonging_to_another_class_does_not_match(self):
        # D61 is INS Delhi, which is not a Kolkata Class ship
        result = si.identify_ship("Kolkata Class", "D61")
        assert result["matched"] is False
        assert result["method"] == "class_roster_fallback"
        assert {s["pennant"] for s in result["roster"]} == {"D63", "D64", "D65"}

    @pytest.mark.parametrize("text", [None, ""])
    def test_no_ocr_text_returns_the_full_class_roster(self, text):
        result = si.identify_ship("Shivalik Class", text)
        assert result["matched"] is False
        assert result["method"] == "class_roster_fallback"
        assert len(result["roster"]) == 3

    def test_roster_fallback_carries_no_confidence_values(self):
        """Design rule: with no pennant evidence, no ship is favoured, so the
        roster must never carry percentages or scores."""
        result = si.identify_ship("Kolkata Class", "")
        assert "confidence" not in result
        for ship in result["roster"]:
            assert set(ship.keys()) == {"name", "pennant"}

    @pytest.mark.parametrize(
        "class_name",
        ["OSV Class", "Container Ship", "Unknown", "", "Not A Real Class"],
    )
    def test_non_naval_or_unknown_class_is_not_applicable(self, class_name):
        result = si.identify_ship(class_name, "D63")
        assert result == {"matched": False, "roster": [], "method": "not_applicable"}

    def test_a_later_candidate_can_match_when_an_earlier_one_does_not(self):
        result = si.identify_ship("Kolkata Class", "Z9 D64")
        assert result["matched"] is True
        assert result["ship_name"] == "INS Kochi"


class TestCheckPennantTypeConsistency:
    def test_consistent_pennant_is_confirmed(self):
        result = si.check_pennant_type_consistency("Kolkata Class", "D63")
        assert result == {
            "checked": True,
            "consistent": True,
            "pennant": "D63",
            "expected_type": "Destroyer",
        }

    def test_mismatch_reports_both_types(self):
        result = si.check_pennant_type_consistency("Kalvari Class", "D63")
        assert result["checked"] is True
        assert result["consistent"] is False
        assert result["pennant"] == "D63"
        assert result["predicted_class_type"] == "Submarine"
        assert result["ocr_implied_type"] == "Destroyer"

    @pytest.mark.parametrize(
        "class_name,pennant",
        [
            ("Veer Class", "K91"),       # corvette, K prefix
            ("Kamorta Class", "P28"),    # corvette, P prefix
            ("Vikrant", "R11"),          # aircraft carrier
            ("Arihant Class", "S2"),     # submarine, single digit
            ("Talwar Class", "F40"),     # frigate
        ],
    )
    def test_every_vessel_type_prefix_is_recognised(self, class_name, pennant):
        result = si.check_pennant_type_consistency(class_name, pennant)
        assert result["checked"] is True
        assert result["consistent"] is True

    def test_pennant_is_found_inside_noisy_text(self):
        result = si.check_pennant_type_consistency("Arihant Class", "garbled S2 text")
        assert result["checked"] is True
        assert result["pennant"] == "S2"

    def test_civilian_class_is_skipped(self):
        assert si.check_pennant_type_consistency("Container Ship", "D63") == {
            "checked": False,
            "reason": "not_a_naval_class",
        }

    @pytest.mark.parametrize("text", [None, "", "some random text 42"])
    def test_no_pennant_read_is_skipped(self, text):
        assert si.check_pennant_type_consistency("Nilgiri Class", text) == {
            "checked": False,
            "reason": "no_pennant_read",
        }

    def test_unrecognised_prefix_letter_is_skipped(self):
        assert si.check_pennant_type_consistency("Kolkata Class", "Z99") == {
            "checked": False,
            "reason": "pennant_prefix_not_recognized",
        }

    def test_unrecognised_prefix_is_passed_over_for_a_later_candidate(self):
        result = si.check_pennant_type_consistency("Kolkata Class", "Z99 D63")
        assert result["checked"] is True
        assert result["consistent"] is True
        assert result["pennant"] == "D63"

    def test_no_registry_ship_ever_flags_its_own_class(self):
        """A correctly identified ship must never trigger a false
        'possible misclassification' warning from its own pennant."""
        registry = si.load_ship_registry()
        for class_name, ships in registry.items():
            for ship in ships:
                result = si.check_pennant_type_consistency(class_name, ship["pennant"])
                assert result["checked"] is True, (class_name, ship)
                assert result["consistent"] is True, (class_name, ship)

    def test_first_classifiable_pennant_decides_known_limitation(self):
        """KNOWN LIMITATION, recorded here deliberately rather than endorsed.

        When the OCR text holds more than one pennant-like token, the first
        one with a recognised prefix decides the outcome. A stray token read
        before the real pennant can therefore raise a false warning even
        though a later token confirms the class. If this behaviour is
        changed, update this test.
        """
        result = si.check_pennant_type_consistency("Kolkata Class", "S21 D63")
        assert result["checked"] is True
        assert result["consistent"] is False
        assert result["pennant"] == "S21"
