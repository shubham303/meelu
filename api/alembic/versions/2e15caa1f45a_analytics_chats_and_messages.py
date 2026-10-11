"""analytics chats and messages

Revision ID: 2e15caa1f45a
Revises: 327625500c84
Create Date: 2026-10-10 21:48:59.681315

"""

import sqlalchemy as sa

from alembic import op

revision = "2e15caa1f45a"
down_revision = "327625500c84"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analytics_chats",
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("sdk_session_id", sa.Text(), nullable=True),
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("seq", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("site_id", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["site.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "analytics_chats_site_idx",
        "analytics_chats",
        ["user_id", "site_id", "updated_at"],
        unique=False,
    )
    op.create_table(
        "analytics_chat_messages",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("chat_id", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("seq", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["chat_id"], ["analytics_chats.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "analytics_chat_messages_chat_idx",
        "analytics_chat_messages",
        ["chat_id", "seq"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("analytics_chat_messages_chat_idx", table_name="analytics_chat_messages")
    op.drop_table("analytics_chat_messages")
    op.drop_index("analytics_chats_site_idx", table_name="analytics_chats")
    op.drop_table("analytics_chats")
