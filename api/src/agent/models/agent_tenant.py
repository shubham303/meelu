from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base


class AgentTenant(Base):
    __tablename__ = "agent_tenants"
    __table_args__ = (UniqueConstraint("user_id", "site_id", name="agent_tenants_user_site_key"),)

    role_name: Mapped[str] = mapped_column(primary_key=True)
    schema_name: Mapped[str] = mapped_column(nullable=False, unique=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    site_id: Mapped[str] = mapped_column(ForeignKey("site.id", ondelete="CASCADE"), nullable=False)
