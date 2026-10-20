from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin


class ConnectedApp(EntityMixin, Base):
    __tablename__ = "connected_app"
    __table_args__ = (Index("connected_app_site_idx", "site_id", "desk", "toolkit"),)

    user_id: Mapped[str | None] = mapped_column(ForeignKey("user.id", ondelete="SET NULL"))
    site_id: Mapped[str | None] = mapped_column(ForeignKey("site.id", ondelete="SET NULL"))
    desk: Mapped[str] = mapped_column(nullable=False)
    toolkit: Mapped[str] = mapped_column(nullable=False)
    account_id: Mapped[str] = mapped_column(nullable=False, unique=True)
    status: Mapped[str] = mapped_column(nullable=False)
    label: Mapped[str | None]
