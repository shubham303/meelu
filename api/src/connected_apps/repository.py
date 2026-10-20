from datetime import UTC, datetime

from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.connected_apps.models.connected_app import ConnectedApp
from src.connected_apps.schemas import ConnectedAppRecord
from src.core.ids import uid


class ConnectedAppRepository:
    async def list_for_site(
        self, db: AsyncSession, user_id: str, site_id: str, desk: str | None = None
    ) -> list[ConnectedAppRecord]:
        conds = [ConnectedApp.user_id == user_id, ConnectedApp.site_id == site_id]
        if desk is not None:
            conds.append(ConnectedApp.desk == desk)
        rows = (
            (await db.execute(select(ConnectedApp).where(*conds).order_by(ConnectedApp.seq)))
            .scalars()
            .all()
        )
        return [ConnectedAppRecord.model_validate(r) for r in rows]

    async def get(
        self, db: AsyncSession, user_id: str, site_id: str, connected_app_id: str
    ) -> ConnectedAppRecord | None:
        row = (
            await db.execute(
                select(ConnectedApp).where(
                    ConnectedApp.user_id == user_id,
                    ConnectedApp.site_id == site_id,
                    ConnectedApp.id == connected_app_id,
                )
            )
        ).scalar_one_or_none()
        return None if row is None else ConnectedAppRecord.model_validate(row)

    async def create(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        desk: str,
        toolkit: str,
        account_id: str,
        status: str,
    ) -> ConnectedAppRecord:
        now = datetime.now(UTC)
        row = ConnectedApp(
            id=uid("capp"),
            user_id=user_id,
            site_id=site_id,
            desk=desk,
            toolkit=toolkit,
            account_id=account_id,
            status=status,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        await db.flush()
        return ConnectedAppRecord.model_validate(row)

    async def update_state(
        self, db: AsyncSession, connected_app_id: str, status: str, label: str | None
    ) -> None:
        await db.execute(
            update(ConnectedApp)
            .where(ConnectedApp.id == connected_app_id)
            .values(status=status, label=label, updated_at=datetime.now(UTC))
        )

    async def delete(self, db: AsyncSession, connected_app_id: str) -> None:
        await db.execute(delete(ConnectedApp).where(ConnectedApp.id == connected_app_id))

    async def list_stale(
        self, db: AsyncSession, active_status: str, pending_before: datetime, limit: int
    ) -> list[ConnectedAppRecord]:
        rows = (
            (
                await db.execute(
                    select(ConnectedApp)
                    .where(
                        or_(
                            ConnectedApp.site_id.is_(None),
                            ConnectedApp.user_id.is_(None),
                            (ConnectedApp.status != active_status)
                            & (ConnectedApp.updated_at < pending_before),
                        )
                    )
                    .order_by(ConnectedApp.seq)
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
        return [ConnectedAppRecord.model_validate(r) for r in rows]


connected_apps = ConnectedAppRepository()
