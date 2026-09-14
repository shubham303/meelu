from datetime import datetime

from sqlalchemy import REAL, BigInteger, DateTime, ForeignKey, Identity, Text, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


class Base(DeclarativeBase):
    type_annotation_map = {str: Text(), float: REAL()}


class TimestampedMixin:
    seq: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class EntityMixin(TimestampedMixin):
    id: Mapped[str] = mapped_column(primary_key=True)

    @declared_attr
    def user_id(cls) -> Mapped[str]:
        return mapped_column(ForeignKey("user.id", ondelete="CASCADE"), nullable=False)


class SiteScopedMixin:
    @declared_attr
    def site_id(cls) -> Mapped[str]:
        return mapped_column(ForeignKey("site.id", ondelete="CASCADE"), nullable=False)


EMPTY_JSON_ARRAY = text("'[]'::jsonb")
EMPTY_JSON_OBJECT = text("'{}'::jsonb")
EMPTY_TEXT_ARRAY = text("'{}'::text[]")
