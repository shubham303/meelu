from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from src.agent.security import drop_orphan_tenants
from src.agent.sql import engine, quote_ident, tenant_txn
from src.settings import settings

SIDECARS = ("_ti_column_types", "_ti_derived_columns")

WORKSPACE_RELATIONS = """
SELECT c.relname, c.relkind,
       coalesce(s.seq_scan, 0) + coalesce(s.idx_scan, 0) + coalesce(s.n_tup_ins, 0)
         + coalesce(s.n_tup_upd, 0) + coalesce(s.n_tup_del, 0)
  FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
  LEFT JOIN pg_stat_user_tables s ON s.relid = c.oid
 WHERE n.nspname = %s AND c.relkind IN ('r', 'v', 'm', 'p') AND c.relname NOT LIKE '\\_ti\\_%%'
"""

DROP_KEYWORD = {"r": "TABLE", "p": "TABLE", "v": "VIEW", "m": "MATERIALIZED VIEW"}


@dataclass
class SweepResult:
    orphans: list[str] = field(default_factory=list)
    dropped: list[str] = field(default_factory=list)
    models: list[str] = field(default_factory=list)


def _expired_relations(conn, role: str, schema: str, now: datetime, cutoff: datetime):
    live = {
        name: (kind, int(activity))
        for name, kind, activity in conn.exec_driver_sql(WORKSPACE_RELATIONS, (schema,))
    }
    known = {
        name: (int(activity), last_used)
        for name, activity, last_used in conn.exec_driver_sql(
            "SELECT table_name, activity, last_used_at FROM public.agent_workspace_tables "
            "WHERE role_name = %s",
            (role,),
        )
    }
    gone = [name for name in known if name not in live]
    if gone:
        conn.exec_driver_sql(
            "DELETE FROM public.agent_workspace_tables WHERE role_name = %s "
            "AND table_name = ANY(%s)",
            (role, gone),
        )

    expired = []
    for name, (kind, activity) in live.items():
        if name not in known:
            conn.exec_driver_sql(
                "INSERT INTO public.agent_workspace_tables "
                "(role_name, table_name, activity, first_seen_at, last_used_at) "
                "VALUES (%s, %s, %s, %s, %s)",
                (role, name, activity, now, now),
            )
            continue
        seen, last_used = known[name]
        if activity != seen:
            conn.exec_driver_sql(
                "UPDATE public.agent_workspace_tables SET activity = %s, last_used_at = %s "
                "WHERE role_name = %s AND table_name = %s",
                (activity, now, role, name),
            )
            continue
        if last_used < cutoff:
            expired.append((name, kind))
    return expired


def _drop_as_tenant(role: str, schema: str, expired: list[tuple[str, str]]) -> None:
    qs = quote_ident(schema)
    with tenant_txn(role, schema) as conn:
        for name, kind in expired:
            conn.exec_driver_sql(
                f"DROP {DROP_KEYWORD[kind]} IF EXISTS {qs}.{quote_ident(name)} CASCADE"
            )
            for sidecar in SIDECARS:
                if conn.exec_driver_sql("SELECT to_regclass(%s)", (f"{qs}.{sidecar}",)).scalar():
                    conn.exec_driver_sql(
                        f"DELETE FROM {qs}.{sidecar} WHERE table_key = %s",
                        (f"{schema}.{name}",),
                    )


def _sweep_tenant(role: str, schema: str, now: datetime, cutoff: datetime) -> list[str]:
    with engine.begin() as conn:
        expired = _expired_relations(conn, role, schema, now, cutoff)
    if not expired:
        return []
    _drop_as_tenant(role, schema, expired)
    names = [name for name, _ in expired]
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "DELETE FROM public.agent_workspace_tables WHERE role_name = %s "
            "AND table_name = ANY(%s)",
            (role, names),
        )
    return [f"{schema}.{name}" for name in names]


def _expire_models(cutoff: datetime) -> list[str]:
    root = settings.agent_data_dir / "models"
    if not root.exists():
        return []
    limit = cutoff.timestamp()
    removed = []
    for path in root.glob("*/*.pkl"):
        if path.stat().st_mtime < limit:
            path.unlink(missing_ok=True)
            removed.append(str(path.relative_to(root)))
    return removed


def sweep(now: datetime | None = None) -> SweepResult:
    now = now or datetime.now(UTC)
    cutoff = now - timedelta(days=settings.agent_workspace_ttl_days)
    result = SweepResult(orphans=drop_orphan_tenants())
    with engine.begin() as conn:
        tenants = conn.exec_driver_sql(
            "SELECT role_name, schema_name FROM public.agent_tenants"
        ).fetchall()
    for role, schema in tenants:
        result.dropped += _sweep_tenant(role, schema, now, cutoff)
    result.models = _expire_models(cutoff)
    return result
