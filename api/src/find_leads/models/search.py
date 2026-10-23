from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import EMPTY_JSON_ARRAY, Base, EntityMixin, SiteScopedMixin


class LeadSearch(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "lead_search"
    __table_args__ = (
        UniqueConstraint("site_id", "platform", "query", name="lead_search_site_query_key"),
        Index("lead_search_searched_idx", "searched_at"),
    )

    platform: Mapped[str] = mapped_column(nullable=False)
    query: Mapped[str] = mapped_column(nullable=False)
    page: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    searched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    results: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=EMPTY_JSON_ARRAY)
