from sqlalchemy import Index, UniqueConstraint
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin, SiteScopedMixin


class GeoQuery(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "geo_query"
    __table_args__ = (
        UniqueConstraint("site_id", "text", name="geo_query_site_text_key"),
        Index("geo_query_site_idx", "site_id", "seq"),
    )

    text: Mapped[str] = mapped_column(nullable=False)
    source: Mapped[str] = mapped_column(nullable=False, server_default=sql_text("'user'"))
    enabled: Mapped[bool] = mapped_column(nullable=False, server_default=sql_text("true"))
