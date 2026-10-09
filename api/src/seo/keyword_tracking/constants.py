from datetime import timedelta

RANK_HISTORY_ID_PREFIX = "rnk"

VOLUME_HISTORY_ID_PREFIX = "vol"

MAX_TRACK_KEYWORDS = 50

TRACKED_DEPTH = 30

TRACKED_DEVICE = "desktop"

BACKFILL_LOOKBACK = timedelta(days=365)

BATCH_ROWS = 2000


class RankSource:
    LIVE = "live"
    HISTORY = "history"


HISTORY_MONTHS = 12

SEASONAL_SWING = 2.0

DEMAND_SHIFT = 0.2
