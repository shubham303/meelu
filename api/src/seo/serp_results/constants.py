from datetime import timedelta
from typing import Literal

Verdict = Literal["clean", "suspect", "poisoned"]

TOP_POSITIONS = 10

TOP_CHECKED = 3

WEAK_PAGE_RANK = 50

WEAK_TOP_SUSPECT = 2

MAX_SIBLINGS = 2

MIN_SIBLING_OVERLAP = 0.3

SERP_TTL = timedelta(days=7)

POISONED_MESSAGE = (
    "Google appears to be serving fake results for this keyword to rank trackers. "
    "Do not trust DataForSEO data for it."
)
