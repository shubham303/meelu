from datetime import datetime

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.scratchpad.models.scratchpad import Scratchpad
from src.scratchpad.models.scratchpad_row import ScratchpadRow
from src.scratchpad.schemas import NewRow, ScratchpadRecord, ScratchpadRowRecord

INSERT_CHUNK = 5000


class ScratchpadRepository:
    ID_PREFIX = "spad"

    async def create(
        self, db: AsyncSession, user_id: str, tool_name: str, now: datetime
    ) -> ScratchpadRecord:
        row = Scratchpad(
            id=uid(self.ID_PREFIX),
            user_id=user_id,
            tool_name=tool_name,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        await db.flush()
        return ScratchpadRecord.model_validate(row)

    async def get(
        self, db: AsyncSession, user_id: str, scratchpad_id: str
    ) -> ScratchpadRecord | None:
        result = await db.execute(
            select(Scratchpad).where(Scratchpad.user_id == user_id, Scratchpad.id == scratchpad_id)
        )
        row = result.scalar_one_or_none()
        return None if row is None else ScratchpadRecord.model_validate(row)

    async def lock(
        self, db: AsyncSession, user_id: str, scratchpad_id: str
    ) -> ScratchpadRecord | None:
        result = await db.execute(
            select(Scratchpad)
            .where(Scratchpad.user_id == user_id, Scratchpad.id == scratchpad_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        row = result.scalar_one_or_none()
        return None if row is None else ScratchpadRecord.model_validate(row)

    async def touch(self, db: AsyncSession, scratchpad_id: str, now: datetime) -> None:
        await db.execute(
            update(Scratchpad).where(Scratchpad.id == scratchpad_id).values(updated_at=now)
        )

    async def delete(self, db: AsyncSession, scratchpad_id: str) -> None:
        await db.execute(delete(Scratchpad).where(Scratchpad.id == scratchpad_id))
        await db.flush()

    async def delete_updated_before(self, db: AsyncSession, cutoff: datetime) -> int:
        result = await db.execute(delete(Scratchpad).where(Scratchpad.updated_at < cutoff))
        return result.rowcount


class ScratchpadRowRepository:
    async def existing_hashes(
        self, db: AsyncSession, scratchpad_id: str, hashes: list[str]
    ) -> set[str]:
        if not hashes:
            return set()
        result = await db.execute(
            select(ScratchpadRow.text_hash).where(
                ScratchpadRow.scratchpad_id == scratchpad_id,
                ScratchpadRow.text_hash.in_(hashes),
            )
        )
        return set(result.scalars())

    async def max_row_id(self, db: AsyncSession, scratchpad_id: str) -> int:
        result = await db.execute(
            select(func.coalesce(func.max(ScratchpadRow.row_id), 0)).where(
                ScratchpadRow.scratchpad_id == scratchpad_id
            )
        )
        return result.scalar_one()

    async def insert(
        self, db: AsyncSession, scratchpad_id: str, rows: list[NewRow], now: datetime
    ) -> None:
        values = [
            {
                "scratchpad_id": scratchpad_id,
                "row_id": r.row_id,
                "text": r.text,
                "text_hash": r.text_hash,
                "priority": r.priority,
                "status": "pending",
                "status_updated_at": now,
                "attempt_count": 0,
            }
            for r in rows
        ]
        for start in range(0, len(values), INSERT_CHUNK):
            await db.execute(insert(ScratchpadRow), values[start : start + INSERT_CHUNK])
        await db.flush()

    async def status_counts(self, db: AsyncSession, scratchpad_id: str) -> dict[str, int]:
        result = await db.execute(
            select(ScratchpadRow.status, func.count())
            .where(ScratchpadRow.scratchpad_id == scratchpad_id)
            .group_by(ScratchpadRow.status)
        )
        return {status: count for status, count in result.all()}

    async def first(self, db: AsyncSession, scratchpad_id: str) -> ScratchpadRowRecord | None:
        result = await db.execute(
            select(ScratchpadRow)
            .where(ScratchpadRow.scratchpad_id == scratchpad_id)
            .order_by(ScratchpadRow.row_id)
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return None if row is None else ScratchpadRowRecord.model_validate(row)

    async def get_many(
        self, db: AsyncSession, scratchpad_id: str, row_ids: list[int]
    ) -> list[ScratchpadRowRecord]:
        if not row_ids:
            return []
        result = await db.execute(
            select(ScratchpadRow).where(
                ScratchpadRow.scratchpad_id == scratchpad_id,
                ScratchpadRow.row_id.in_(row_ids),
            )
        )
        return [ScratchpadRowRecord.model_validate(r) for r in result.scalars()]

    async def pending_ids(self, db: AsyncSession, scratchpad_id: str, limit: int) -> list[int]:
        result = await db.execute(
            select(ScratchpadRow.row_id)
            .where(ScratchpadRow.scratchpad_id == scratchpad_id, ScratchpadRow.status == "pending")
            .order_by(ScratchpadRow.priority.desc(), ScratchpadRow.row_id.asc())
            .limit(limit)
        )
        return list(result.scalars())

    async def mark_processing(
        self, db: AsyncSession, scratchpad_id: str, row_ids: list[int], now: datetime
    ) -> list[ScratchpadRowRecord]:
        if not row_ids:
            return []
        result = await db.execute(
            update(ScratchpadRow)
            .where(
                ScratchpadRow.scratchpad_id == scratchpad_id,
                ScratchpadRow.row_id.in_(row_ids),
                ScratchpadRow.status == "pending",
            )
            .values(
                status="processing",
                status_updated_at=now,
                attempt_count=ScratchpadRow.attempt_count + 1,
            )
            .returning(ScratchpadRow)
            .execution_options(populate_existing=True)
        )
        return [ScratchpadRowRecord.model_validate(r) for r in result.scalars()]

    async def update(self, db: AsyncSession, scratchpad_id: str, row_id: int, values: dict) -> None:
        await db.execute(
            update(ScratchpadRow)
            .where(ScratchpadRow.scratchpad_id == scratchpad_id, ScratchpadRow.row_id == row_id)
            .values(**values)
        )

    async def page_by_status(
        self, db: AsyncSession, scratchpad_id: str, status: str, offset: int, limit: int
    ) -> list[ScratchpadRowRecord]:
        result = await db.execute(
            select(ScratchpadRow)
            .where(ScratchpadRow.scratchpad_id == scratchpad_id, ScratchpadRow.status == status)
            .order_by(ScratchpadRow.row_id.asc())
            .offset(offset)
            .limit(limit)
        )
        return [ScratchpadRowRecord.model_validate(r) for r in result.scalars()]

    async def search(
        self,
        db: AsyncSession,
        scratchpad_id: str,
        pattern: str,
        statuses: list[str],
        offset: int,
        limit: int,
    ) -> tuple[list[ScratchpadRowRecord], int]:
        where = (
            ScratchpadRow.scratchpad_id == scratchpad_id,
            ScratchpadRow.status.in_(statuses),
            ScratchpadRow.text.ilike(pattern, escape="\\"),
        )
        total = (
            await db.execute(select(func.count()).select_from(ScratchpadRow).where(*where))
        ).scalar_one()
        result = await db.execute(
            select(ScratchpadRow)
            .where(*where)
            .order_by(ScratchpadRow.priority.desc(), ScratchpadRow.row_id.asc())
            .offset(offset)
            .limit(limit)
        )
        return [ScratchpadRowRecord.model_validate(r) for r in result.scalars()], total

    async def requeue_stuck(
        self, db: AsyncSession, cutoff: datetime, max_attempts: int, now: datetime
    ) -> int:
        result = await db.execute(
            update(ScratchpadRow)
            .where(
                ScratchpadRow.status == "processing",
                ScratchpadRow.status_updated_at < cutoff,
                ScratchpadRow.attempt_count < max_attempts,
            )
            .values(status="pending", status_updated_at=now)
        )
        return result.rowcount

    async def fail_stuck(
        self,
        db: AsyncSession,
        cutoff: datetime,
        max_attempts: int,
        error_reason: str,
        now: datetime,
    ) -> int:
        result = await db.execute(
            update(ScratchpadRow)
            .where(
                ScratchpadRow.status == "processing",
                ScratchpadRow.status_updated_at < cutoff,
                ScratchpadRow.attempt_count >= max_attempts,
            )
            .values(status="failed", status_updated_at=now, error_reason=error_reason)
        )
        return result.rowcount


scratchpads = ScratchpadRepository()
scratchpad_rows = ScratchpadRowRepository()
