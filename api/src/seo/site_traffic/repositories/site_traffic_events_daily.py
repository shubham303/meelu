from src.seo.site_traffic.repositories.base import TrafficRollupRepository


class SiteTrafficEventsDailyRepository(TrafficRollupRepository):
    REPORT = "events"
    ROLLUP_DIMS = (("event_name",),)
    ROLLUP_METRICS = {
        "sessions": "event_count",
        "users": "users",
        "engaged": "0",
        "key": "key_events",
        "revenue": "0",
    }


site_traffic_events_dailies = SiteTrafficEventsDailyRepository()
