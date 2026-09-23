JOB_STATUSES = ("RUNNING", "COMPLETED", "FAILED")

SUGGESTION_STATES = (
    "draft",
    "reviewed",
    "ready",
    "llm_rejected",
    "user_rejected",
    "done",
    "stale",
)

OPEN_STATES = ("draft", "reviewed", "ready")

REVIVABLE_STATES = ("llm_rejected", "stale")

ACTIONS = ("add", "edit", "delete")

KEYWORD_SOURCES = ("gsc", "ideas", "ranked", "competitor", "serp_paa", "serp_related", "user")

COMPETITOR_STATES = ("candidate", "confirmed", "ignored")

COMPETITOR_SOURCES = ("rival", "serp", "user")

EDIT_EVIDENCE = ("gsc", "cluster", "ctr", "questions", "decay")

IMPRESSIONS_FLOOR = 20

CLICKS_FLOOR = 5

WEAK_COVERAGE = 0.55

OWNER_COVERAGE = 0.7

COVERAGE_MARGIN = 0.05

SITE_SIMILARITY_PCT = 25

ADJACENT_DISTANCE = 0.25

CLUSTER_ATTACH_DISTANCE = 0.2

CLUSTER_DISTANCE = 0.15

CLUSTER_MAX_KEYWORDS = 5000

LEADER_MIN_DAYS = 10

DECAY_DROP = 0.3

CTR_MIN_SAMPLE = 30

SCREEN_CONFIDENCE = 0.8

SERP_KEEP = 3

FACTS_FRESH_DAYS = 30

RANKED_FRESH_DAYS = 14

SERP_FRESH_DAYS = 7

RIVALS_FRESH_DAYS = 30

MAX_BRAND_TERMS = 8

WORKSPACE_TABLE = r"^[a-z_][a-z0-9_]{0,62}$"
