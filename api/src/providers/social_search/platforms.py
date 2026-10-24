PLATFORMS = [
    {"id": "hackernews", "label": "Hacker News", "access": "direct"},
    {"id": "stackexchange", "label": "Stack Exchange", "access": "direct"},
    {"id": "devto", "label": "Dev.to", "access": "direct"},
    {"id": "github", "label": "GitHub Issues", "access": "direct"},
    {"id": "bluesky", "label": "Bluesky", "access": "direct"},
    {"id": "reddit", "label": "Reddit", "access": "web"},
    {"id": "x", "label": "X (Twitter)", "access": "web"},
    {"id": "linkedin", "label": "LinkedIn", "access": "web"},
    {"id": "facebook", "label": "Facebook", "access": "web"},
]

WEB_SEARCHED_PLATFORMS = tuple(p["id"] for p in PLATFORMS if p["access"] == "web")
