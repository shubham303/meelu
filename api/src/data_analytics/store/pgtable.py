from __future__ import annotations

import re

import numpy as np
import pandas as pd

from src.agent.context import AgentContext
from src.agent.sql import quote_ident, user_txn
from src.settings import settings

_KIND_MAP = {
    "smallint": "integer",
    "integer": "integer",
    "bigint": "integer",
    "real": "float",
    "double precision": "float",
    "numeric": "decimal",
    "boolean": "bool",
    "date": "datetime",
    "timestamp without time zone": "datetime",
    "timestamp with time zone": "datetime",
    "time without time zone": "datetime",
    "time with time zone": "datetime",
    "text": "string",
    "character varying": "string",
    "character": "string",
}

_ROW_ID = "_ti_row"

_SQL_EXPR_BLOCKLIST = frozenset(
    {
        "select",
        "insert",
        "update",
        "delete",
        "drop",
        "alter",
        "create",
        "grant",
        "revoke",
        "truncate",
        "copy",
        "call",
        "do",
        "set",
        "reset",
        "into",
        "pg_read_file",
        "pg_read_binary_file",
        "pg_ls_dir",
        "pg_stat_file",
        "lo_import",
        "lo_export",
        "dblink",
        "pg_sleep",
        "current_setting",
        "set_config",
        "pg_terminate_backend",
        "pg_cancel_backend",
    }
)
_WORD_RE = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")


class TableError(ValueError):
    pass


def resolve_table(ctx: AgentContext, table: str) -> PgTable:
    if "." in table:
        schema, name = table.split(".", 1)
    else:
        schema, name = None, table
    if schema is not None and schema not in ("public", ctx.schema):
        raise TableError(
            f"Schema {schema!r} is not accessible. Use canonical tables in 'public' "
            f"or your workspace schema {ctx.schema!r}."
        )
    with user_txn(ctx) as conn:
        if schema is None:
            for candidate in (ctx.schema, "public"):
                if _table_exists(conn, candidate, name):
                    schema = candidate
                    break
            if schema is None:
                raise TableError(f"No table named {name!r} in your workspace or in public.")
        elif not _table_exists(conn, schema, name):
            raise TableError(f"No table {schema}.{name}.")
    return PgTable(ctx, schema, name)


def _table_exists(conn, schema: str, name: str) -> bool:
    row = conn.exec_driver_sql(
        "SELECT 1 FROM information_schema.tables WHERE table_schema = %s AND table_name = %s",
        (schema, name),
    ).fetchone()
    return row is not None


class PgTable:
    def __init__(self, ctx: AgentContext, schema: str, name: str):
        self.ctx = ctx
        self.schema = schema
        self.name = name
        self.qualified = f"{quote_ident(schema)}.{quote_ident(name)}"
        self.key = f"{schema}.{name}"
        self.sandbox = schema == ctx.schema

    def _all_columns(self, conn) -> list[str]:
        rows = conn.exec_driver_sql(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position",
            (self.schema, self.name),
        ).fetchall()
        return [r[0] for r in rows]

    def columns(self) -> list[str]:
        with user_txn(self.ctx) as conn:
            return [c for c in self._all_columns(conn) if c != _ROW_ID]

    def column_kind(self, column: str) -> str:
        with user_txn(self.ctx) as conn:
            row = conn.exec_driver_sql(
                "SELECT data_type FROM information_schema.columns "
                "WHERE table_schema = %s AND table_name = %s AND column_name = %s",
                (self.schema, self.name, column),
            ).fetchone()
        if row is None:
            raise KeyError(f"No column {column!r} on {self.key}.")
        return _KIND_MAP.get(row[0], "other")

    def distinct_and_rows(self, column: str) -> tuple[int, int]:
        qc = quote_ident(column)
        with user_txn(self.ctx) as conn:
            row = conn.exec_driver_sql(
                f"SELECT COUNT(DISTINCT {qc}), COUNT(*) FROM {self.qualified}"
            ).fetchone()
        return int(row[0]), int(row[1])

    def count_rows(self) -> int:
        with user_txn(self.ctx) as conn:
            return int(conn.exec_driver_sql(f"SELECT COUNT(*) FROM {self.qualified}").fetchone()[0])

    def count_non_null(self, column: str) -> int:
        cols = self.columns()
        if column not in cols:
            raise KeyError(f"No column {column!r}. Known: {sorted(cols)}")
        with user_txn(self.ctx) as conn:
            return int(
                conn.exec_driver_sql(
                    f"SELECT COUNT({quote_ident(column)}) FROM {self.qualified}"
                ).fetchone()[0]
            )

    def get_frame(self) -> pd.DataFrame:
        with user_txn(self.ctx) as conn:
            all_cols = self._all_columns(conn)
            n, size = conn.exec_driver_sql(
                f"SELECT COUNT(*), COALESCE(SUM(pg_column_size(t.*)), 0) FROM {self.qualified} t"
            ).fetchone()
            if n > settings.agent_max_frame_rows:
                raise TableError(
                    f"{self.key} has {n} rows, above the {settings.agent_max_frame_rows}-row analysis "
                    f"limit. Materialize a filtered or aggregated table in your workspace "
                    f"schema with run_sql first, then analyze that."
                )
            if size > settings.agent_max_frame_bytes:
                raise TableError(
                    f"{self.key} holds {int(size) // 1024**2} MB, above the "
                    f"{settings.agent_max_frame_bytes // 1024**2} MB analysis limit. Materialize "
                    f"a table with only the columns you need in your workspace schema with "
                    f"run_sql first, then analyze that."
                )
            cols = [c for c in all_cols if c != _ROW_ID]
            select = ", ".join(quote_ident(c) for c in cols)
            order = f" ORDER BY {quote_ident(_ROW_ID)}" if _ROW_ID in all_cols else ""
            return pd.read_sql_query(f"SELECT {select} FROM {self.qualified}{order}", conn)

    def _require_sandbox(self, action: str) -> None:
        if not self.sandbox:
            raise TableError(
                f"{self.key} is a canonical read-only table; {action} needs a workspace "
                f"table. Materialize one with run_sql (CREATE TABLE ... AS SELECT ...) "
                f"in your schema {self.ctx.schema!r} first."
            )

    def _ensure_row_ids(self, conn) -> None:
        if _ROW_ID not in self._all_columns(conn):
            conn.exec_driver_sql(
                f"ALTER TABLE {self.qualified} "
                f"ADD COLUMN {quote_ident(_ROW_ID)} BIGINT GENERATED BY DEFAULT AS IDENTITY"
            )

    def _sql_type(self, values: list) -> str:
        present = [v for v in values if v is not None]
        if not present:
            return "text"
        if all(isinstance(v, bool) for v in present):
            return "boolean"
        if all(isinstance(v, int) and not isinstance(v, bool) for v in present):
            return "bigint"
        if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in present):
            return "double precision"
        return "text"

    def write_back_column(self, name: str, values, feature: bool = False) -> None:
        self._require_sandbox("writing a column back")
        cleaned = []
        for v in values:
            if isinstance(v, np.generic):
                v = v.item()
            if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
                v = None
            cleaned.append(v)
        sql_type = self._sql_type(cleaned)
        if sql_type == "text":
            cleaned = [None if v is None else str(v) for v in cleaned]
        qn = quote_ident(name)
        with user_txn(self.ctx) as conn:
            self._ensure_row_ids(conn)
            current = int(
                conn.exec_driver_sql(f"SELECT COUNT(*) FROM {self.qualified}").fetchone()[0]
            )
            if len(cleaned) != current:
                raise ValueError(
                    f"write_back_column expected {current} values (one per row) "
                    f"but got {len(cleaned)}."
                )
            conn.exec_driver_sql(f"CREATE TEMP TABLE _wb (i BIGINT, v {sql_type}) ON COMMIT DROP")
            params = list(enumerate(cleaned))
            for start in range(0, len(params), 5000):
                conn.exec_driver_sql(
                    "INSERT INTO _wb (i, v) VALUES (%s, %s)",
                    params[start : start + 5000],
                )
            conn.exec_driver_sql(f"ALTER TABLE {self.qualified} DROP COLUMN IF EXISTS {qn}")
            conn.exec_driver_sql(f"ALTER TABLE {self.qualified} ADD COLUMN {qn} {sql_type}")
            conn.exec_driver_sql(
                f"WITH ord AS ("
                f"  SELECT {quote_ident(_ROW_ID)} AS rid, "
                f"         row_number() OVER (ORDER BY {quote_ident(_ROW_ID)}) - 1 AS i "
                f"  FROM {self.qualified}"
                f") "
                f"UPDATE {self.qualified} t SET {qn} = w.v "
                f"FROM ord JOIN _wb w ON w.i = ord.i "
                f"WHERE t.{quote_ident(_ROW_ID)} = ord.rid"
            )
            self._register_column(conn, name, feature)
        self.set_cached_type(name, None, clear=True)

    def add_computed_column(self, name: str, expression: str, feature: bool = True) -> int:
        self._require_sandbox("computing a column")
        qn = quote_ident(name)
        with user_txn(self.ctx) as conn:
            self._validate_expression(conn, expression)
            typed = conn.exec_driver_sql(
                f"SELECT pg_typeof(({expression}))::text FROM {self.qualified} LIMIT 1"
            ).fetchone()
            sql_type = typed[0] if typed else "text"
            conn.exec_driver_sql(f"ALTER TABLE {self.qualified} DROP COLUMN IF EXISTS {qn}")
            conn.exec_driver_sql(f"ALTER TABLE {self.qualified} ADD COLUMN {qn} {sql_type}")
            conn.exec_driver_sql(f"UPDATE {self.qualified} SET {qn} = ({expression})")
            count = int(
                conn.exec_driver_sql(f"SELECT COUNT({qn}) FROM {self.qualified}").fetchone()[0]
            )
            self._register_column(conn, name, feature)
        self.set_cached_type(name, None, clear=True)
        return count

    def _validate_expression(self, conn, expression: str) -> None:
        if not expression or not expression.strip():
            raise ValueError("Feature expression is empty.")
        if ";" in expression:
            raise ValueError("Feature expression must be a single expression (no ';').")
        lowered = {w.lower() for w in _WORD_RE.findall(expression)}
        hit = lowered & _SQL_EXPR_BLOCKLIST
        if hit:
            raise ValueError(
                f"Feature expression may not use {sorted(hit)} — only a scalar "
                f"computation over the table's columns is allowed."
            )
        try:
            conn.exec_driver_sql(f"SELECT ({expression}) FROM {self.qualified} WHERE false")
        except Exception as exc:
            raise ValueError(f"Invalid feature expression: {exc}") from exc

    def _ensure_sidecars(self, conn) -> None:
        ws = quote_ident(self.ctx.schema)
        conn.exec_driver_sql(
            f"CREATE TABLE IF NOT EXISTS {ws}._ti_column_types ("
            f"table_key TEXT, column_name TEXT, col_type TEXT, "
            f"PRIMARY KEY (table_key, column_name))"
        )
        conn.exec_driver_sql(
            f"CREATE TABLE IF NOT EXISTS {ws}._ti_derived_columns ("
            f"table_key TEXT, column_name TEXT, "
            f"PRIMARY KEY (table_key, column_name))"
        )

    def _register_column(self, conn, name: str, feature: bool) -> None:
        self._ensure_sidecars(conn)
        ws = quote_ident(self.ctx.schema)
        if feature:
            conn.exec_driver_sql(
                f"DELETE FROM {ws}._ti_derived_columns WHERE table_key = %s AND column_name = %s",
                (self.key, name),
            )
        else:
            conn.exec_driver_sql(
                f"INSERT INTO {ws}._ti_derived_columns (table_key, column_name) "
                f"VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (self.key, name),
            )

    def derived_columns(self) -> set[str]:
        with user_txn(self.ctx) as conn:
            self._ensure_sidecars(conn)
            ws = quote_ident(self.ctx.schema)
            rows = conn.exec_driver_sql(
                f"SELECT column_name FROM {ws}._ti_derived_columns WHERE table_key = %s",
                (self.key,),
            ).fetchall()
        return {r[0] for r in rows}

    def get_cached_type(self, column: str) -> str | None:
        with user_txn(self.ctx) as conn:
            self._ensure_sidecars(conn)
            ws = quote_ident(self.ctx.schema)
            row = conn.exec_driver_sql(
                f"SELECT col_type FROM {ws}._ti_column_types "
                f"WHERE table_key = %s AND column_name = %s",
                (self.key, column),
            ).fetchone()
        return row[0] if row else None

    def set_cached_type(self, column: str, col_type: str | None, clear: bool = False) -> None:
        with user_txn(self.ctx) as conn:
            self._ensure_sidecars(conn)
            ws = quote_ident(self.ctx.schema)
            if clear or col_type is None:
                conn.exec_driver_sql(
                    f"DELETE FROM {ws}._ti_column_types WHERE table_key = %s AND column_name = %s",
                    (self.key, column),
                )
            else:
                conn.exec_driver_sql(
                    f"INSERT INTO {ws}._ti_column_types (table_key, column_name, col_type) "
                    f"VALUES (%s, %s, %s) "
                    f"ON CONFLICT (table_key, column_name) DO UPDATE SET col_type = EXCLUDED.col_type",
                    (self.key, column, col_type),
                )

    def unset_cached_type(self, column: str) -> None:
        self.set_cached_type(column, None, clear=True)
