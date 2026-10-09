import pytest

from src.seo.market import ENGLISH_MARKETS, markets


def test_the_site_markets_win_over_the_default():
    assert markets(["GB", "IE"], "en") == [
        {"location_code": 2826, "language_code": "en"},
        {"location_code": 2372, "language_code": "en"},
    ]
    assert markets(["DE"], "de") == [{"location_code": 2276, "language_code": "de"}]


def test_no_markets_in_english_means_english_speaking_worldwide():
    found = markets([], None)
    assert len(found) == len(ENGLISH_MARKETS)
    assert {m["language_code"] for m in found} == {"en"}


def test_one_location_code_narrows_to_that_market():
    assert markets(["GB"], "en", 2840) == [{"location_code": 2840, "language_code": "en"}]


def test_a_non_english_site_without_markets_must_be_asked():
    with pytest.raises(ValueError, match="Ask the user"):
        markets([], "fr")
