from sqlalchemy import Index
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin


class Scratchpad(EntityMixin, Base):
    __tablename__ = "scratchpad"
    __table_args__ = (
        Index("scratchpad_user_idx", "user_id"),
        Index("scratchpad_updated_idx", "updated_at"),
    )

    tool_name: Mapped[str] = mapped_column(nullable=False)
