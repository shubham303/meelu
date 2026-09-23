PLATFORMS = [
    {"id": "hackernews", "label": "Hacker News", "access": "direct"},
    {"id": "stackexchange", "label": "Stack Exchange", "access": "direct"},
    {"id": "devto", "label": "Dev.to", "access": "direct"},
    {"id": "github", "label": "GitHub Issues", "access": "direct"},
    {
        "id": "reddit",
        "label": "Reddit",
        "access": "apify",
        "actor": "trudax~reddit-scraper-lite",
        "backup_actor": "harshmaur~reddit-scraper",
    },
    {
        "id": "x",
        "label": "X (Twitter)",
        "access": "apify",
        "actor": "kaitoeasyapi~twitter-x-data-tweet-scraper-pay-per-result-cheapest",
        "backup_actor": "apidojo~tweet-scraper",
    },
    {
        "id": "linkedin",
        "label": "LinkedIn",
        "access": "apify",
        "actor": "apimaestro~linkedin-posts-search-scraper-no-cookies",
        "backup_actor": "curious_coder~linkedin-post-search-scraper",
    },
    {
        "id": "youtube",
        "label": "YouTube",
        "access": "apify",
        "actor": "streamers~youtube-scraper",
        "backup_actor": "apidojo~youtube-scraper",
    },
    {
        "id": "bluesky",
        "label": "Bluesky",
        "access": "apify",
        "actor": "lexis-solutions~bluesky-posts-scraper",
        "backup_actor": "axery~bluesky-posts-scraper",
    },
    {
        "id": "instagram",
        "label": "Instagram",
        "access": "apify",
        "actor": "apify~instagram-hashtag-scraper",
        "backup_actor": "apidojo~instagram-scraper",
    },
    {
        "id": "tiktok",
        "label": "TikTok",
        "access": "apify",
        "actor": "clockworks~tiktok-scraper",
        "backup_actor": "apidojo~tiktok-scraper",
    },
]


def platform_entry(platform_id: str) -> dict | None:
    return next((p for p in PLATFORMS if p["id"] == platform_id), None)
