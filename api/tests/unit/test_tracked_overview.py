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


def test_position_is_the_latest_month_with_impressions():
    months = months_back(date(2026, 10, 6), 12)
    positions = [
        ("crm", date(2026, 8, 1), 12.04, "https://ex.com/a"),
        ("crm", date(2026, 9, 1), 9.46, "https://ex.com/b"),
    ]
    volumes = [("crm", date(2026, 9, 1), 500), ("erp", date(2026, 9, 1), 300)]
    crm, erp = tracked_keywords(months, positions, volumes)
    assert (crm.position, crm.previous_position, crm.change) == (9.5, 12.0, 2.6)
    assert crm.url == "https://ex.com/b"
    assert crm.history[-3:] == [12.0, 9.5, None]
    assert erp.keyword == "erp" and erp.position is None and erp.volume == 300
