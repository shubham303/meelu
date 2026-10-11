from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.orm import Base


class AgentWorkspaceTable(Base):
    __tablename__ = "agent_workspace_tables"

    role_name: Mapped[str] = mapped_column(
        ForeignKey("agent_tenants.role_name", ondelete="CASCADE"), primary_key=True
    )
    table_name: Mapped[str] = mapped_column(primary_key=True)
    activity: Mapped[int] = mapped_column(BigInteger, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
