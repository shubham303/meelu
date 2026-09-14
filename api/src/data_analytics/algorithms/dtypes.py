from __future__ import annotations

COLUMN_TYPES = frozenset(
    {
        "continuous",
        "categorical",
        "categorical_nominal",
        "categorical_ordinal",
        "datetime",
        "identifier",
    }
)

SETTABLE_TYPES = frozenset({"categorical_nominal", "categorical_ordinal"})

_IDENTIFIER_DISTINCT_RATIO = 0.9
_NUMERIC_CATEGORICAL_MAX_DISTINCT = 15
_CONTINUOUS_DISTINCT_RATIO = 0.5

_DATETIME_KINDS = {"datetime"}
_BOOL_KINDS = {"bool"}
_INTEGER_KINDS = {"integer"}
_REAL_KINDS = {"float", "decimal"}
_STRING_KINDS = {"string"}


def classify_column(col_name: str, store: object, override: bool = False) -> str:
    if not override:
        get_cached = getattr(store, "get_cached_type", None)
        if get_cached:
            cached = get_cached(col_name)
            if cached:
                return cached

    computed = _detect(col_name, store)

    set_cached = getattr(store, "set_cached_type", None)
    if set_cached:
        set_cached(col_name, computed)
    return computed


def _detect(col_name: str, store: object) -> str:
    kind = store.column_kind(col_name)

    if kind in _DATETIME_KINDS:
        return "datetime"
    if kind in _BOOL_KINDS:
        return "categorical"

    if kind in _INTEGER_KINDS or kind in _REAL_KINDS:
        n_distinct, n_rows = store.distinct_and_rows(col_name)
        if n_distinct > _NUMERIC_CATEGORICAL_MAX_DISTINCT:
            return "continuous"
        if kind in _REAL_KINDS:
            if n_rows > 0 and (n_distinct / n_rows) > _CONTINUOUS_DISTINCT_RATIO:
                return "continuous"
        return "categorical"

    if kind in _STRING_KINDS:
        n_distinct, n_rows = store.distinct_and_rows(col_name)
        if n_rows > 0 and (n_distinct / n_rows) > _IDENTIFIER_DISTINCT_RATIO:
            return "identifier"
        return "categorical"

    return "categorical"


def classify_table(store: object, override: bool = False) -> dict[str, str]:
    return {col: classify_column(col, store, override=override) for col in store.columns()}
