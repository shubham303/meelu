from src.seo.site_traffic.repositories.base import TrafficRollupRepository


class SiteTrafficTechDailyRepository(TrafficRollupRepository):
    REPORT = "tech"
    ROLLUP_DIMS = (("device_category",), ("os",), ("browser",))
    ROLLUP_METRICS = {
        "sessions": "sessions",
        "users": "users",
        "engaged": "0",
        "key": "0",
        "revenue": "0",
    }


site_traffic_tech_dailies = SiteTrafficTechDailyRepository()
