from datetime import timedelta
from typing import Literal

CLUSTER_ID_PREFIX = "kcl"

MAX_SEEDS = 10

ClusterSource = Literal["seeds", "search_console", "ranked_keywords", "competitor_keywords"]

DEFAULT_SOURCE_KEYWORDS = 300

MAX_SOURCE_KEYWORDS = 1000

RANKED_PULL = 1000

MAX_COMPETITORS_READ = 10

MIN_COMPETITORS_FOR_GAP = 2

DISCOVERED_PER_SOURCE = 200

NOISE_SHARE_OF_CORE = 0.02

LLM_BATCH = 25

LLM_CONCURRENCY = 8

TOP_N = 10

SERP_DEPTH = 30

SERP_DEVICE = "desktop"

SERP_TTL = timedelta(days=7)

PAGE_WEIGHT = 0.85

MARGIN = 50.0

SCALE = 50.0

INTENT_FIT = {"full": 1.0, "partial": 0.5, "none": 0.0}

METRICS_TTL = timedelta(days=30)

DEFAULT_METRICS_LIMIT = 10

MAX_METRICS_LIMIT = 50

CLUSTER_NOT_FOUND = "No such keyword cluster on this website."
