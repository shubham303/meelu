from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.social_listening.models.cursor import SocialListeningCursor


class SocialListeningCursorRepository:
    ID_PREFIX = "slk"

    async def by_keyword(
        self, db: AsyncSession, site_id: str, platform: str, keywords: list[str]
    ) -> dict[str, datetime]:
        if not keywords:
            return {}
        result = await db.execute(
            select(SocialListeningCursor.keyword, SocialListeningCursor.last_fetched_at).where(
                SocialListeningCursor.site_id == site_id,
                SocialListeningCursor.platform == platform,
                SocialListeningCursor.keyword.in_(keywords),
            )
        )
        return dict(result.all())

    async def since(
        self, db: AsyncSession, site_id: str, platform: str, cutoff: datetime
    ) -> dict[str, datetime]:
        result = await db.execute(
            select(SocialListeningCursor.keyword, SocialListeningCursor.last_fetched_at).where(
                SocialListeningCursor.site_id == site_id,
                SocialListeningCursor.platform == platform,
                SocialListeningCursor.last_fetched_at >= cutoff,
            )
        )
        return dict(result.all())

    async def advance(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        platform: str,
        keywords: list[str],
        fetched_at: datetime,
    ) -> None:
        if not keywords:
            return
        now = datetime.now(UTC)
        stmt = pg_insert(SocialListeningCursor).values(
            [
                {
                    "id": uid(self.ID_PREFIX),
                    "user_id": user_id,
                    "site_id": site_id,
                    "platform": platform,
                    "keyword": keyword,
                    "last_fetched_at": fetched_at,
                    "created_at": now,
                    "updated_at": now,
                }
                for keyword in keywords
            ]
        )
        stmt = stmt.on_conflict_do_update(
            constraint="social_listening_cursor_site_keyword_key",
            set_={"last_fetched_at": stmt.excluded.last_fetched_at, "updated_at": now},
        )
        await db.execute(stmt)
        await db.flush()

    async def delete_older_than(self, db: AsyncSession, cutoff: datetime) -> int:
        result = await db.execute(
            delete(SocialListeningCursor).where(SocialListeningCursor.last_fetched_at < cutoff)
        )
        await db.flush()
        return int(result.rowcount or 0)


social_listening_cursors = SocialListeningCursorRepository()
