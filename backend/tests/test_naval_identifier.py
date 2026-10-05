"""Unit tests for app/services/naval_identifier.py

Covers the individual scoring functions (length, beam, displacement,
vessel type, description) and the ranking behaviour of
identify_candidates against the real knowledge pack.
"""

import pytest

from app.services import naval_identifier as ni


class TestLengthScore:
    def test_exact_match_gets_full_points(self):
        assert ni._length_score(163.0, 163.0) == 25

    def test_within_five_metres_still_gets_full_points(self):
        assert ni._length_score(163.0, 158.0) == 25

    def test_at_or_beyond_tolerance_gets_zero(self):
        assert ni._length_score(163.0, 188.0) == 0
        assert ni._length_score(163.0, 300.0) == 0

    def test_partial_credit_in_between(self):
        assert 0 < ni._length_score(163.0, 175.0) < 25

    @pytest.mark.parametrize(
        "entry,user", [(None, 160), (160, None), ("abc", 160), (160, "xyz")]
    )
    def test_missing_or_non_numeric_input_scores_zero(self, entry, user):
        assert ni._length_score(entry, user) == 0


class TestBeamScore:
    def test_within_one_metre_gets_full_points(self):
        assert ni._beam_score(17.4, 17.4) == 15
        assert ni._beam_score(17.4, 16.5) == 15

    def test_five_metres_or_more_off_gets_zero(self):
        assert ni._beam_score(17.4, 22.4) == 0

    def test_missing_input_scores_zero(self):
        assert ni._beam_score(17.4, None) == 0
        assert ni._beam_score(None, 17.4) == 0


class TestDisplacementScore:
    def test_tolerance_is_relative_not_absolute(self):
        """A 4 percent error must score the same at 1,600 t and at 45,000 t."""
        assert ni._displacement_score(1615, 1615 * 1.04) == 20
        assert ni._displacement_score(45000, 45000 * 1.04) == 20

    def test_far_off_scores_zero(self):
        assert ni._displacement_score(1615, 1615 + 2000) == 0

    def test_zero_or_missing_values_score_zero(self):
        assert ni._displacement_score(0, 1000) == 0
        assert ni._displacement_score(7500, None) == 0
        assert ni._displacement_score(None, 7500) == 0


class TestTypeScore:
    def test_submarine_does_not_match_anti_submarine_corvette(self):
        """Regression: 'Anti-submarine corvette' contains the word
        'submarine' but is not a submarine."""
        assert ni._type_score({"vessel_type": "Anti-submarine corvette"}, "submarine") == 0

    @pytest.mark.parametrize(
        "vessel_type",
        [
            "Diesel-electric attack submarine (SSK)",
            "Nuclear-powered ballistic missile submarine (SSBN)",
        ],
    )
    def test_submarine_matches_real_submarines(self, vessel_type):
        assert ni._type_score({"vessel_type": vessel_type}, "submarine") == 20

    def test_corvette_matches_anti_submarine_corvette(self):
        assert ni._type_score({"vessel_type": "Anti-submarine corvette"}, "corvette") == 20

    @pytest.mark.parametrize(
        "dropdown,vessel_type",
        [
            ("destroyer", "Guided-missile destroyer"),
            ("frigate", "Stealth multi-role frigate"),
            ("carrier", "Aircraft carrier (STOBAR)"),
        ],
    )
    def test_each_dropdown_value_matches_its_vessel_type(self, dropdown, vessel_type):
        assert ni._type_score({"vessel_type": vessel_type}, dropdown) == 20

    def test_matching_ignores_case(self):
        assert ni._type_score({"vessel_type": "Guided-missile destroyer"}, "DESTROYER") == 20

    @pytest.mark.parametrize("value", [None, ""])
    def test_blank_type_scores_zero(self, value):
        assert ni._type_score({"vessel_type": "Frigate"}, value) == 0


class TestTextScore:
    ENTRY = {
        "hull_superstructure": "Stealth-shaped hull with angled surfaces",
        "mast_radar_funnel_profile": "Integrated mast, single sloped funnel",
        "radar_signature": "Reduced",
    }

    def test_empty_description_scores_zero(self):
        assert ni._text_score(self.ENTRY, None) == 0
        assert ni._text_score(self.ENTRY, "") == 0

    def test_matching_words_score_points(self):
        assert ni._text_score(self.ENTRY, "angled stealth funnel") > 0

    def test_short_words_are_ignored(self):
        assert ni._text_score(self.ENTRY, "a an of the") == 0

    def test_score_is_capped(self):
        many = "stealth shaped hull angled surfaces integrated mast single sloped funnel reduced"
        assert ni._text_score(self.ENTRY, many) <= 25

    def test_propulsion_words_do_not_influence_the_score(self):
        """Only hull, mast/radar/funnel and radar-signature text is searched.
        Typing 'nuclear' therefore does not help rank a nuclear submarine."""
        entry = dict(self.ENTRY, propulsion="Nuclear")
        assert ni._text_score(entry, "nuclear") == 0


class TestIdentifyCandidates:
    def test_the_two_carriers_are_told_apart_by_dimensions(self):
        vikrant = ni.identify_candidates(length_m=262.5, beam_m=62, displacement_tons=45000)
        assert vikrant[0]["class_name"] == "Vikrant"
        vikramaditya = ni.identify_candidates(length_m=283.5, beam_m=59.8, displacement_tons=44500)
        assert vikramaditya[0]["class_name"] == "Vikramaditya"

    def test_submarine_of_111_metres_ranks_arihant_first(self):
        result = ni.identify_candidates(length_m=111, vessel_type="submarine")
        assert result[0]["class_name"] == "Arihant Class"

    def test_submarine_search_never_returns_anti_submarine_corvettes(self):
        result = ni.identify_candidates(vessel_type="submarine", top_n=50)
        names = {c["class_name"] for c in result}
        assert names == {
            "Arihant Class",
            "Kalvari Class",
            "Shishumar Class",
            "Sindhughosh Class",
        }

    def test_destroyer_search_returns_exactly_the_destroyer_classes(self):
        result = ni.identify_candidates(vessel_type="destroyer", top_n=50)
        names = {c["class_name"] for c in result}
        assert names == {
            "Kolkata Class",
            "Visakhapatnam Class",
            "Delhi Class",
            "Rajput Class",
        }

    def test_no_input_returns_a_single_placeholder(self):
        result = ni.identify_candidates()
        assert len(result) == 1
        assert result[0]["class_name"] is None
        assert result[0]["confidence_pct"] == 0
        assert result[0]["risk_level"] is None

    def test_unrelated_description_returns_the_placeholder(self):
        result = ni.identify_candidates(description="zzzz qqqq wwww")
        assert result[0]["class_name"] is None

    def test_results_are_sorted_best_first_and_capped_at_99(self):
        result = ni.identify_candidates(
            length_m=163,
            beam_m=17.4,
            displacement_tons=7500,
            vessel_type="destroyer",
            hull_color="grey",
            description="stealth angled single funnel",
            top_n=10,
        )
        scores = [c["confidence_pct"] for c in result]
        assert scores == sorted(scores, reverse=True)
        assert all(0 < s <= 99 for s in scores)

    @pytest.mark.parametrize("top_n", [1, 2, 3])
    def test_top_n_limits_the_number_of_results(self, top_n):
        result = ni.identify_candidates(vessel_type="destroyer", top_n=top_n)
        assert len(result) == top_n

    def test_every_real_candidate_carries_risk_level_and_reasoning(self):
        result = ni.identify_candidates(length_m=163, vessel_type="destroyer")
        for candidate in result:
            assert candidate["risk_level"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
            assert candidate["reasoning"]
            assert candidate["validation_status"]

    def test_hull_colour_alone_is_only_a_weak_signal(self):
        """Colour on its own must never produce a confident-looking result."""
        result = ni.identify_candidates(hull_color="grey", top_n=50)
        assert all(c["confidence_pct"] <= 5 for c in result)
