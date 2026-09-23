JOB_STATUSES = ("RUNNING", "COMPLETED", "FAILED")

SUGGESTION_STATES = ("draft", "ready", "llm_rejected", "user_rejected", "done", "stale")

OPEN_STATES = ("draft", "ready")

REVIVABLE_STATES = ("llm_rejected", "stale")

LINK_ACTIONS = ("create", "delete", "edit")

PILLAR_ACTIONS = ("create", "expand")

SCREEN_CONFIDENCE = 0.8

HIERARCHY_TYPES = ("hub", "utility")

REMOVAL_REGION = "body"

PILLAR_MIN_SIZE = 4

PILLAR_MIN_COHESION = 0.35

PILLAR_COVERED = 0.7

PILLAR_PARTLY_COVERED = 0.3

PILLAR_OVERLAP = 0.6

PILLAR_BUDGET = 5

PILLAR_DONE_FRACTION = 0.6

PILLAR_STALE_FRACTION = 0.5

STRUCTURAL_TYPES = ("utility", "legal", "company")

WORKSPACE_TABLE = r"^[a-z_][a-z0-9_]{0,62}$"
