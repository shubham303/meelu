from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class Campaign(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "campaigns"
    __table_args__ = (
        Index("campaigns_user_idx", "user_id", "created_at"),
        Index("campaigns_project_idx", "project_id"),
    )

    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    requested_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(nullable=False, server_default=text("'running'"))
    summary: Mapped[str | None]
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
