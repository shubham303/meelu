from sqlalchemy import BigInteger, ForeignKey, Index, Integer, text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base, EntityMixin


class LlmCall(EntityMixin, Base):
    __tablename__ = "llm_call"
    __table_args__ = (Index("llm_call_user_idx", "user_id", "seq"),)

    site_id: Mapped[str | None] = mapped_column(ForeignKey("site.id", ondelete="SET NULL"))
    model: Mapped[str] = mapped_column(nullable=False)
    purpose: Mapped[str] = mapped_column(nullable=False)
    generation_id: Mapped[str | None]
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    cache_read_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    cache_write_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    cost_micros: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))
    charged_micros: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )
    status: Mapped[str] = mapped_column(nullable=False)
    error: Mapped[str | None]
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
