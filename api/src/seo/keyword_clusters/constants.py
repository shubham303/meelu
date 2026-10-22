from typing import Literal

CLUSTER_ID_PREFIX = "kcl"

MAX_SEEDS = 10

SearchIntent = Literal["informational", "navigational", "commercial", "transactional"]

Importance = Literal["hot", "warm", "cold"]

MAX_KEYWORDS_TO_ADD = 50

DEFAULT_SEARCH_CONSOLE_QUERIES = 300

MAX_SEARCH_CONSOLE_QUERIES = 1000

DISCOVERED_FROM_SEEDS = 200

NOISE_SHARE_OF_CORE = 0.02

LLM_BATCH = 25

RELEVANCE_BATCH = 25

LLM_CONCURRENCY = 16

SERP_DEPTH = 30

SERP_DEVICE = "desktop"

CLUSTER_NOT_FOUND = "No such keyword cluster on this website."

NO_CLUSTER_GIVEN = "Pass cluster ids or keywords."

MAX_DELETE = 100

TOO_MANY_TO_DELETE = f"Pass at most {MAX_DELETE} cluster ids and keywords per call."

KEYWORD_NOT_IN_CLUSTER = "Not in this cluster: {keywords}."

MAIN_KEYWORD_STAYS = (
    "The main keyword {keyword} cannot be removed from its cluster; delete the cluster instead."
)

MAX_COMPETITOR_KEYWORDS_PER_DOMAIN = 1000

MIN_COMPETITOR_KEYWORDS_PER_DOMAIN = 100

COMPETITOR_KEYWORDS_PER_CLUSTER = 4

DEFAULT_COMPETITOR_CLUSTERS = 100

MAX_COMPETITOR_CLUSTERS = 100

DEFAULT_IMPRESSIONS_LOOKBACK = 28

MAX_IMPRESSIONS_LOOKBACK = 180

RELEVANCE_ROUND = 200

NO_SAVED_COMPETITORS = "This website has no saved competitors yet; find and save them first."
