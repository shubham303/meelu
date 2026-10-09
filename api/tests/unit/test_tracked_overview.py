from datetime import date

from src.seo.keyword_tracking.overview import demand, months_back, tracked_keywords


def test_months_back_ends_with_the_current_month():
    months = months_back(date(2026, 2, 14), 3)
    assert months == [date(2025, 12, 1), date(2026, 1, 1), date(2026, 2, 1)]


def test_demand_labels():
    assert demand([100] * 5) is None
    assert demand([100, 100, 100, 100, 100, 100]) == "steady"
    assert demand([100, 100, 100, 130, 130, 130]) == "rising"
    assert demand([100, 100, 100, 70, 70, 70]) == "falling"
    assert demand([50, 60, 120, 110, 60, 55]) == "seasonal"


def test_a_keyword_that_dropped_out_of_the_top_thirty_has_no_position():
    months = months_back(date(2026, 10, 6), 12)
    days = [("crm", date(2026, 9, 1)), ("crm", date(2026, 10, 1))]
    ranks = [("crm", date(2026, 9, 1), 12, "https://ex.com/a")]
    [row] = tracked_keywords(months, days, ranks, [])
    assert row.position is None
    assert row.previous_position == 12
    assert row.change is None
    assert row.history[-2:] == [12, None]
