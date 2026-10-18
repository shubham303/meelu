from sqlalchemy import Index, UniqueConstraint
from sqlalchemy import text as sql_text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import EMPTY_JSON_ARRAY, EMPTY_JSON_OBJECT, Base, EntityMixin, SiteScopedMixin


class LeadBrief(EntityMixin, SiteScopedMixin, Base):
    __tablename__ = "lead_brief"
    __table_args__ = (
        UniqueConstraint("site_id", "text", name="lead_brief_site_text_key"),
        Index("lead_brief_site_idx", "site_id", "seq"),
    )

    text: Mapped[str] = mapped_column(nullable=False)
    enabled: Mapped[bool] = mapped_column(nullable=False, server_default=sql_text("true"))
    source: Mapped[str] = mapped_column(nullable=False, server_default=sql_text("'user'"))
    sources: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=EMPTY_JSON_ARRAY)
    plan: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=EMPTY_JSON_OBJECT)
