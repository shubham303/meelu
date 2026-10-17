import re

COMPETITOR_ID_PREFIX = "scmp"

BACKLINK_ID_PREFIX = "sbl"

MAX_COMPETITORS = 50

MAX_DOMAINS_PER_CALL = 20

BACKLINKS_PER_DOMAIN = 1000

GENUINE_MAX_SPAM_SCORE = 30

GENUINE_MAX_DOMAIN_SPAM_SCORE = 30

GENUINE_MIN_DOMAIN_RANK = 100

GENUINE_MAX_EXTERNAL_LINKS = 150

GENUINE_MAX_LINKS_FROM_DOMAIN = 10

GENUINE_ITEM_TYPES = frozenset({"anchor", "image"})

PAID_LINK_ATTRIBUTES = frozenset({"sponsored"})

PAID_PLACEMENT = re.compile(
    r"sponsor|advertorial|paid[\s_-]*post|guest[\s_-]*post|write[\s_-]*for[\s_-]*us|partner[\s_-]*content",
    re.IGNORECASE,
)

TOO_MANY_COMPETITORS = f"A website keeps at most {MAX_COMPETITORS} competitors."

COMPETITOR_NOT_FOUND = "No such competitor on this website."
