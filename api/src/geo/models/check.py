from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import EMPTY_JSON_ARRAY, EMPTY_JSON_OBJECT, Base, EntityMixin, SiteScopedMixin


class GeoCheck(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "geo_check"
    __table_args__ = (
        Index("geo_check_query_idx", "query_id", "seq"),
        Index("geo_check_site_idx", "site_id", "seq"),
        Index(
            "geo_check_one_running_per_query",
            "query_id",
            unique=True,
            postgresql_where=text("status = 'running'"),
        ),
    )

    query_id: Mapped[str] = mapped_column(
        ForeignKey("geo_query.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(nullable=False, server_default=text("'running'"))
    progress: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=EMPTY_JSON_OBJECT)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None]
    intent: Mapped[str | None]
    required_points: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=EMPTY_JSON_ARRAY
    )
    verdict: Mapped[str | None]
    page_id: Mapped[str | None] = mapped_column(ForeignKey("site_pages.id", ondelete="SET NULL"))
    page_url: Mapped[str | None]
    position: Mapped[float | None]
    pages: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=EMPTY_JSON_ARRAY)
    ai_answers: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=EMPTY_JSON_ARRAY)
    page_adds: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=EMPTY_JSON_ARRAY)
    suggestion: Mapped[str | None]
    model: Mapped[str | None]
