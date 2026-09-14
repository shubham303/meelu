from sqlalchemy import Index, Integer, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin


class PostMedia(EntityMixin, Base):
    __tablename__ = "post_media"
    __table_args__ = (Index("post_media_user_idx", "user_id", "created_at"),)

    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    content_type: Mapped[str] = mapped_column(nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    original_name: Mapped[str | None]
