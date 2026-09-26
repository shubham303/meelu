from enum import StrEnum


class SuggestionState(StrEnum):
    DRAFT = "draft"
    SCREENING_REJECTED = "screening_rejected"
    SCREENING_APPROVED = "screening_approved"
    REVIEW_APPROVED = "review_approved"
    REVIEW_REJECTED = "review_rejected"
    USER_REJECTED = "user_rejected"


VISIBLE_STATES = frozenset({SuggestionState.REVIEW_APPROVED, SuggestionState.USER_REJECTED})


class PillarAction(StrEnum):
    CREATE = "create"
    EXPAND = "expand"


SCREEN_CONFIDENCE = 0.8

HIERARCHY_TYPES = frozenset({"hub", "utility"})

STRUCTURAL_TYPES = frozenset({"utility", "legal", "company"})

STRUCTURAL_SHARE = 0.5

REMOVAL_REGION = "body"

PILLAR_MIN_SIZE = 4

PILLAR_MIN_COHESION = 0.35

PILLAR_COVERED = 0.7

PILLAR_PARTLY_COVERED = 0.3

PILLAR_OVERLAP = 0.6

PILLAR_BUDGET = 5

PILLAR_DONE_FRACTION = 0.6

PILLAR_STALE_FRACTION = 0.5

WORKSPACE_TABLE = r"^[a-z_][a-z0-9_]{0,62}$"
