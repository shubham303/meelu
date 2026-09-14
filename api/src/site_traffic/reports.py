import re
from dataclasses import dataclass

from src.site_traffic.models.site_traffic_channels_daily import SiteTrafficChannelsDaily
from src.site_traffic.models.site_traffic_events_daily import SiteTrafficEventsDaily
from src.site_traffic.models.site_traffic_geo_daily import SiteTrafficGeoDaily
from src.site_traffic.models.site_traffic_landing_daily import SiteTrafficLandingDaily
from src.site_traffic.models.site_traffic_pages_daily import SiteTrafficPagesDaily
from src.site_traffic.models.site_traffic_tech_daily import SiteTrafficTechDaily
from src.site_traffic.models.site_traffic_totals_daily import SiteTrafficTotalsDaily


def snake(name: str) -> str:
    return re.sub(r"[A-Z]", lambda m: f"_{m.group(0).lower()}", name)


@dataclass(frozen=True)
class ReportSpec:
    model: type
    name: str
    dims: tuple[str, ...]
    metrics: tuple[str, ...]


REPORT_SPECS: dict[str, ReportSpec] = {
    "totals": ReportSpec(
        SiteTrafficTotalsDaily,
        "site_traffic_totals_daily",
        (),
        (
            "users",
            "newUsers",
            "sessions",
            "engagedSessions",
            "pageViews",
            "engagementSeconds",
            "keyEvents",
            "revenue",
        ),
    ),
    "channels": ReportSpec(
        SiteTrafficChannelsDaily,
        "site_traffic_channels_daily",
        ("channel", "source", "medium"),
        ("sessions", "users", "newUsers", "engagedSessions", "keyEvents", "revenue"),
    ),
    "landing": ReportSpec(
        SiteTrafficLandingDaily,
        "site_traffic_landing_daily",
        ("landingPage", "channel"),
        ("sessions", "engagedSessions", "keyEvents", "revenue"),
    ),
    "pages": ReportSpec(
        SiteTrafficPagesDaily,
        "site_traffic_pages_daily",
        ("pagePath",),
        ("views", "users", "engagementSeconds", "keyEvents"),
    ),
    "events": ReportSpec(
        SiteTrafficEventsDaily,
        "site_traffic_events_daily",
        ("eventName",),
        ("eventCount", "users", "keyEvents"),
    ),
    "geo": ReportSpec(
        SiteTrafficGeoDaily,
        "site_traffic_geo_daily",
        ("country",),
        ("sessions", "users", "newUsers", "keyEvents", "revenue"),
    ),
    "tech": ReportSpec(
        SiteTrafficTechDaily,
        "site_traffic_tech_daily",
        ("deviceCategory", "os", "browser"),
        ("sessions", "users"),
    ),
}

TRAFFIC_REPORTS = tuple(REPORT_SPECS)
