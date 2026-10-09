import pytest

from src.seo.keyword_clusters.winnability import (
    authority_pass,
    climb,
    pass_chance,
    smoothed,
    strength,
)


def test_the_worked_example_from_the_research_notes():
    flattened = smoothed([120, 110, 300, 100, 90])
    assert [round(s) for s in flattened] == [177, 177, 177, 100, 90]
    outcome = climb([authority_pass(s, 74) for s in flattened], start=6)
    assert outcome["likely_position"] == 5
    assert outcome["p_top_three"] == pytest.approx(0.106, abs=0.001)


def test_a_result_that_misses_the_intent_is_passed_whatever_its_links():
    assert pass_chance(900, 0, fit=0.0) == 1.0
    assert pass_chance(900, 0, fit=1.0) == pytest.approx(authority_pass(900, 0))


def test_strength_leans_on_the_page():
    assert strength(100, 500) == pytest.approx(160)
    assert strength(None, None) == 0
