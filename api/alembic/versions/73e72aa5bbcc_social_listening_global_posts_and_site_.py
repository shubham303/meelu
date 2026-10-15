"""social listening global posts and site cursors

Revision ID: 73e72aa5bbcc
Revises: e68f7848a9fb
Create Date: 2026-10-15 21:33:11.764923

"""

from alembic import op
import pgvector.sqlalchemy
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "73e72aa5bbcc"
down_revision = "e68f7848a9fb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "social_post",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("post_key", sa.Text(), nullable=False),
        sa.Column("platform", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("author_handle", sa.Text(), nullable=True),
        sa.Column("author_name", sa.Text(), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "engagement",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "context",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("content_hash", sa.Text(), nullable=True),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "search",
            postgresql.TSVECTOR(),
            sa.Computed(
                "to_tsvector('english', coalesce(title, '') || ' ' || coalesce(text, ''))",
                persisted=True,
            ),
            nullable=False,
        ),
        sa.Column("embedding", pgvector.sqlalchemy.vector.VECTOR(dim=384), nullable=True),
        sa.Column("embed_model", sa.Text(), nullable=True),
        sa.Column("embed_attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("embed_error", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("post_key"),
    )
    op.create_index(
        "social_post_pending_embed_idx",
        "social_post",
        ["seq"],
        unique=False,
        postgresql_where=sa.text("embedding IS NULL"),
    )
    op.create_index(
        "social_post_platform_fetched_idx", "social_post", ["platform", "fetched_at"], unique=False
    )
    op.create_index("social_post_posted_idx", "social_post", ["posted_at"], unique=False)
    op.create_index(
        "social_post_search_idx", "social_post", ["search"], unique=False, postgresql_using="gin"
    )
    op.create_table(
        "social_listening_cursor",
        sa.Column("platform", sa.Text(), nullable=False),
        sa.Column("keyword", sa.Text(), nullable=False),
        sa.Column("last_fetched_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.UniqueConstraint(
            "site_id", "platform", "keyword", name="social_listening_cursor_site_keyword_key"
        ),
    )
    op.execute("DELETE FROM social_listening_post")
    op.execute("UPDATE social_listening_query SET keywords = '[]'::jsonb")
    op.execute(
        "UPDATE social_listening_run SET status = 'error', finished_at = now() WHERE status = 'running'"
    )
    op.execute(
        "UPDATE social_listening_config SET platforms = coalesce(("
        "SELECT jsonb_agg(p) FROM jsonb_array_elements(platforms) p "
        "WHERE p #>> '{}' NOT IN ('youtube', 'instagram', 'tiktok')), '[]'::jsonb)"
    )
    op.drop_column("social_listening_config", "results_per_keyword")
    op.drop_column("social_listening_config", "max_age_days")
    op.drop_column("social_listening_config", "strictness")
    op.add_column("social_listening_post", sa.Column("post_id", sa.Text(), nullable=False))
    op.drop_index(
        op.f("social_listening_post_content_hash_idx"), table_name="social_listening_post"
    )
    op.drop_index(
        op.f("social_listening_post_pending_idx"),
        table_name="social_listening_post",
        postgresql_where="(embedding IS NULL)",
    )
    op.drop_index(op.f("social_listening_post_site_idx"), table_name="social_listening_post")
    op.drop_constraint(
        op.f("social_listening_post_site_key_key"), "social_listening_post", type_="unique"
    )
    op.create_index(
        "social_listening_post_post_idx", "social_listening_post", ["post_id"], unique=False
    )
    op.create_unique_constraint(
        "social_listening_post_site_post_key", "social_listening_post", ["site_id", "post_id"]
    )
    op.create_foreign_key(
        "social_listening_post_post_id_fkey",
        "social_listening_post",
        "social_post",
        ["post_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_column("social_listening_post", "external_id")
    op.drop_column("social_listening_post", "platform")
    op.drop_column("social_listening_post", "url")
    op.drop_column("social_listening_post", "author_name")
    op.drop_column("social_listening_post", "embedding")
    op.drop_column("social_listening_post", "posted_at")
    op.drop_column("social_listening_post", "context")
    op.drop_column("social_listening_post", "engagement")
    op.drop_column("social_listening_post", "embed_error")
    op.drop_column("social_listening_post", "embed_attempts")
    op.drop_column("social_listening_post", "relevance")
    op.drop_column("social_listening_post", "post_key")
    op.drop_column("social_listening_post", "title")
    op.drop_column("social_listening_post", "content_hash")
    op.drop_column("social_listening_post", "drop_reason")
    op.drop_column("social_listening_post", "text")
    op.drop_column("social_listening_post", "embed_model")
    op.drop_column("social_listening_post", "composite_score")
    op.drop_column("social_listening_post", "author_handle")
    op.drop_column("social_listening_query", "negative_keywords")
    op.create_index(
        "social_listening_run_one_running_per_user",
        "social_listening_run",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'running'"),
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS meelu_agent_select ON social_post")
    op.execute("DELETE FROM social_listening_post")
    op.add_column(
        "social_listening_config",
        sa.Column(
            "strictness",
            sa.TEXT(),
            server_default=sa.text("'balanced'"),
            autoincrement=False,
            nullable=False,
        ),
    )
    op.drop_index(
        "social_listening_run_one_running_per_user",
        table_name="social_listening_run",
        postgresql_where=sa.text("status = 'running'"),
    )
    op.add_column(
        "social_listening_query",
        sa.Column(
            "negative_keywords",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            autoincrement=False,
            nullable=False,
        ),
    )
    op.add_column(
        "social_listening_post",
        sa.Column("author_handle", sa.TEXT(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "social_listening_post",
        sa.Column("composite_score", sa.REAL(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "social_listening_post",
        sa.Column("embed_model", sa.TEXT(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "social_listening_post", sa.Column("text", sa.TEXT(), autoincrement=False, nullable=True)
    )
    op.add_column(
        "social_listening_post",
        sa.Column("drop_reason", sa.TEXT(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "social_listening_post",
        sa.Column("content_hash", sa.TEXT(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "social_listening_post", sa.Column("title", sa.TEXT(), autoincrement=False, nullable=True)
    )
    op.add_column(
        "social_listening_post",
        sa.Column("post_key", sa.TEXT(), autoincrement=False, nullable=False),
    )
    op.add_column(
        "social_listening_post",
        sa.Column("relevance", sa.REAL(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "social_listening_post",
        sa.Column(
            "embed_attempts",
            sa.INTEGER(),
            server_default=sa.text("0"),
            autoincrement=False,
            nullable=False,
        ),
    )
    op.add_column(
        "social_listening_post",
        sa.Column("embed_error", sa.TEXT(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "social_listening_post",
        sa.Column(
            "engagement",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            autoincrement=False,
            nullable=False,
        ),
    )
    op.add_column(
        "social_listening_post",
        sa.Column(
            "context",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            autoincrement=False,
            nullable=False,
        ),
    )
    op.add_column(
        "social_listening_post",
        sa.Column(
            "posted_at", postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True
        ),
    )
    op.add_column(
        "social_listening_post",
        sa.Column(
            "embedding",
            pgvector.sqlalchemy.vector.VECTOR(dim=384),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "social_listening_post",
        sa.Column("author_name", sa.TEXT(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "social_listening_post", sa.Column("url", sa.TEXT(), autoincrement=False, nullable=False)
    )
    op.add_column(
        "social_listening_post",
        sa.Column("platform", sa.TEXT(), autoincrement=False, nullable=False),
    )
    op.add_column(
        "social_listening_post",
        sa.Column("external_id", sa.TEXT(), autoincrement=False, nullable=True),
    )
    op.drop_constraint(
        "social_listening_post_post_id_fkey", "social_listening_post", type_="foreignkey"
    )
    op.drop_constraint(
        "social_listening_post_site_post_key", "social_listening_post", type_="unique"
    )
    op.drop_index("social_listening_post_post_idx", table_name="social_listening_post")
    op.create_unique_constraint(
        op.f("social_listening_post_site_key_key"),
        "social_listening_post",
        ["site_id", "post_key"],
        postgresql_nulls_not_distinct=False,
    )
    op.create_index(
        op.f("social_listening_post_site_idx"),
        "social_listening_post",
        ["site_id", "seq"],
        unique=False,
    )
    op.create_index(
        op.f("social_listening_post_pending_idx"),
        "social_listening_post",
        ["site_id"],
        unique=False,
        postgresql_where="(embedding IS NULL)",
    )
    op.create_index(
        op.f("social_listening_post_content_hash_idx"),
        "social_listening_post",
        ["site_id", "content_hash"],
        unique=False,
    )
    op.drop_column("social_listening_post", "post_id")
    op.add_column(
        "social_listening_config",
        sa.Column(
            "max_age_days",
            sa.INTEGER(),
            server_default=sa.text("365"),
            autoincrement=False,
            nullable=False,
        ),
    )
    op.add_column(
        "social_listening_config",
        sa.Column(
            "results_per_keyword",
            sa.INTEGER(),
            server_default=sa.text("50"),
            autoincrement=False,
            nullable=False,
        ),
    )
    op.drop_table("social_listening_cursor")
    op.drop_index("social_post_search_idx", table_name="social_post", postgresql_using="gin")
    op.drop_index("social_post_posted_idx", table_name="social_post")
    op.drop_index("social_post_platform_fetched_idx", table_name="social_post")
    op.drop_index(
        "social_post_pending_embed_idx",
        table_name="social_post",
        postgresql_where=sa.text("embedding IS NULL"),
    )
    op.drop_table("social_post")
