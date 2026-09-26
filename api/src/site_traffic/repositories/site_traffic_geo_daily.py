from src.site_traffic.repositories.base import TrafficRollupRepository


class SiteTrafficGeoDailyRepository(TrafficRollupRepository):
    REPORT = "geo"
    ROLLUP_DIMS = (("country",),)
    ROLLUP_METRICS = {
        "sessions": "sessions",
        "users": "users",
        "engaged": "0",
        "key": "key_events",
        "revenue": "revenue",
    }


site_traffic_geo_dailies = SiteTrafficGeoDailyRepository()
