from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base


class Profile(Base):
    __tablename__ = "profile"
    __table_args__ = (Index("profile_user_idx", "user_id", unique=True),)

    id: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    full_name: Mapped[str] = mapped_column(nullable=False)
    role: Mapped[str | None]
    company: Mapped[str | None]
    timezone: Mapped[str | None]
    signature: Mapped[str | None]
    bio: Mapped[str | None]
    writing_voice: Mapped[str | None]
    linkedin_url: Mapped[str | None]
    x_url: Mapped[str | None]
    website_url: Mapped[str | None]
