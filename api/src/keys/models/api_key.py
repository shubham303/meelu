from datetime import datetime

from sqlalchemy import DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin


class ApiKey(EntityMixin, Base):
    __tablename__ = "api_keys"
    __table_args__ = (Index("api_keys_user_idx", "user_id"),)

    name: Mapped[str] = mapped_column(nullable=False)
    key_hash: Mapped[str] = mapped_column(nullable=False, unique=True)
    preview: Mapped[str] = mapped_column(nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
