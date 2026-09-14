from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class SitePageIndexStatus(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "site_page_index_status"
    __table_args__ = (
        Index("site_page_index_status_page_idx", "page_id", unique=True),
        Index("site_page_index_status_state_idx", "site_id", "index_state"),
    )

    page_id: Mapped[str] = mapped_column(
        ForeignKey("site_pages.id", ondelete="CASCADE"), nullable=False
    )
    index_state: Mapped[str | None]
    coverage_state: Mapped[str | None]
    google_canonical: Mapped[str | None]
    last_crawl_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    index_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
