from __future__ import annotations

import datetime as _dt
import math
from decimal import Decimal
from typing import Any

import numpy as np


def jsonable(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [jsonable(v) for v in obj]
    if isinstance(obj, np.generic):
        obj = obj.item()
    if isinstance(obj, Decimal):
        obj = float(obj)
    elif isinstance(obj, (_dt.date, _dt.datetime, _dt.time)):
        return obj.isoformat()
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj
