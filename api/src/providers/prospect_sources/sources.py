SOURCES = [
    {"id": "web-search", "label": "Web search", "access": "direct"},
    {"id": "hackernews", "label": "Hacker News", "access": "direct"},
    {
        "id": "apify:linkedin",
        "label": "LinkedIn",
        "access": "apify",
        "platform": "linkedin",
        "actor": "harvestapi~linkedin-profile-search",
        "backup_actor": "curious_coder~linkedin-people-search-scraper",
    },
    {
        "id": "apify:reddit",
        "label": "Reddit",
        "access": "apify",
        "platform": "reddit",
        "actor": "trudax~reddit-scraper-lite",
        "backup_actor": "harshmaur~reddit-scraper",
    },
    {
        "id": "apify:x",
        "label": "X (Twitter)",
        "access": "apify",
        "platform": "x",
        "actor": "kaitoeasyapi~twitter-x-data-tweet-scraper-pay-per-result-cheapest",
        "backup_actor": "apidojo~tweet-scraper",
    },
    {
        "id": "apify:youtube",
        "label": "YouTube",
        "access": "apify",
        "platform": "youtube",
        "actor": "streamers~youtube-scraper",
        "backup_actor": "apidojo~youtube-scraper",
    },
    {
        "id": "apify:instagram",
        "label": "Instagram",
        "access": "apify",
        "platform": "instagram",
        "actor": "apify~instagram-search-scraper",
        "backup_actor": "apidojo~instagram-scraper",
    },
]


def source_entry(source_id: str) -> dict | None:
    return next((s for s in SOURCES if s["id"] == source_id), None)
