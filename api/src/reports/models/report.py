from sqlalchemy import Index, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class Report(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "reports"
    __table_args__ = (
        Index("reports_site_idx", "user_id", "site_id", "created_at"),
        Index("reports_desk_idx", "site_id", "desk", "created_at"),
    )

    desk: Mapped[str] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(nullable=False)
    html: Mapped[str] = mapped_column(nullable=False)
    created_by: Mapped[str] = mapped_column(nullable=False, server_default=text("'agent'"))
