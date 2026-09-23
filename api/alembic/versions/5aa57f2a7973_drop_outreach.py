"""drop outreach

Revision ID: 5aa57f2a7973
Revises: 642bc22a2697
Create Date: 2026-09-14 23:45:31.597853

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '5aa57f2a7973'
down_revision = '642bc22a2697'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index(op.f('conversations_message_idx'), table_name='conversations', postgresql_where='(message_id IS NOT NULL)')
    op.drop_index(op.f('conversations_prospect_idx'), table_name='conversations')
    op.drop_index(op.f('conversations_user_idx'), table_name='conversations')
    op.drop_table('conversations')
    op.drop_index(op.f('prospects_campaign_idx'), table_name='prospects')
    op.drop_index(op.f('prospects_dedupe_idx'), table_name='prospects', postgresql_using='gin')
    op.drop_index(op.f('prospects_user_idx'), table_name='prospects')
    op.drop_table('prospects')
    op.drop_index(op.f('campaigns_project_idx'), table_name='campaigns')
    op.drop_index(op.f('campaigns_user_idx'), table_name='campaigns')
    op.drop_table('campaigns')
    op.drop_index(op.f('projects_user_idx'), table_name='projects')
    op.drop_table('projects')

def downgrade() -> None:
    op.create_table('projects',
    sa.Column('name', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('goal', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('prompt', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('prospect_profile', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('search_criteria', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('email_tone', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('value_prop', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('cta', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('user_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('seq', sa.BIGINT(), sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), autoincrement=True, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('site_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], name=op.f('projects_site_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('projects_user_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('projects_pkey'))
    )
    op.create_index(op.f('projects_user_idx'), 'projects', ['user_id', 'created_at'], unique=False)
    op.create_table('campaigns',
    sa.Column('project_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('requested_count', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('status', sa.TEXT(), server_default=sa.text("'running'::text"), autoincrement=False, nullable=False),
    sa.Column('summary', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('finished_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('user_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('seq', sa.BIGINT(), sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), autoincrement=True, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('site_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name=op.f('campaigns_project_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], name=op.f('campaigns_site_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('campaigns_user_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('campaigns_pkey'))
    )
    op.create_index(op.f('campaigns_user_idx'), 'campaigns', ['user_id', 'created_at'], unique=False)
    op.create_index(op.f('campaigns_project_idx'), 'campaigns', ['project_id'], unique=False)
    op.create_table('prospects',
    sa.Column('campaign_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('name', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('company', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('role', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('email', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('website', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('source_url', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('fit_reason', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('status', sa.TEXT(), server_default=sa.text("'found'::text"), autoincrement=False, nullable=False),
    sa.Column('dedupe_keys', postgresql.ARRAY(sa.TEXT()), server_default=sa.text("'{}'::text[]"), autoincrement=False, nullable=False),
    sa.Column('id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('user_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('seq', sa.BIGINT(), sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), autoincrement=True, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('site_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], name=op.f('prospects_campaign_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], name=op.f('prospects_site_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('prospects_user_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('prospects_pkey'))
    )
    op.create_index(op.f('prospects_user_idx'), 'prospects', ['user_id', 'created_at'], unique=False)
    op.create_index(op.f('prospects_dedupe_idx'), 'prospects', ['dedupe_keys'], unique=False, postgresql_using='gin')
    op.create_index(op.f('prospects_campaign_idx'), 'prospects', ['campaign_id'], unique=False)
    op.create_table('conversations',
    sa.Column('prospect_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('status', sa.TEXT(), server_default=sa.text("'draft'::text"), autoincrement=False, nullable=False),
    sa.Column('from', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('to', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('cc', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('bcc', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('subject', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('body', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('message_id', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('thread_ref', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('user_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('seq', sa.BIGINT(), sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), autoincrement=True, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('site_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['prospect_id'], ['prospects.id'], name=op.f('conversations_prospect_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], name=op.f('conversations_site_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('conversations_user_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('conversations_pkey'))
    )
    op.create_index(op.f('conversations_user_idx'), 'conversations', ['user_id', 'created_at'], unique=False)
    op.create_index(op.f('conversations_prospect_idx'), 'conversations', ['prospect_id', 'created_at'], unique=False)
    op.create_index(op.f('conversations_message_idx'), 'conversations', ['user_id', 'message_id'], unique=True, postgresql_where='(message_id IS NOT NULL)')
