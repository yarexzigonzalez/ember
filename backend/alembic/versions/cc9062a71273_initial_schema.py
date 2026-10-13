"""initial schema

Revision ID: cc9062a71273
Revises: 
Create Date: 2026-10-12 22:18:25.541092

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'cc9062a71273'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # CITEXT lets emails compare case-insensitively (Alex@x.com == alex@x.com).
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    op.create_table('extraction_cache',
    sa.Column('input_hash', sa.CHAR(length=64), nullable=False),
    sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('model', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('input_hash', name=op.f('pk_extraction_cache'))
    )
    op.create_table('users',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('email', postgresql.CITEXT(), nullable=False),
    sa.Column('password_hash', sa.Text(), nullable=False),
    sa.Column('display_name', sa.Text(), nullable=True),
    sa.Column('is_demo', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('weekly_goal', sa.Integer(), server_default='12', nullable=False),
    sa.Column('ghost_after_days', sa.Integer(), server_default='14', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
    sa.UniqueConstraint('email', name=op.f('uq_users_email'))
    )
    op.create_table('applications',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('company', sa.Text(), nullable=False),
    sa.Column('role', sa.Text(), nullable=False),
    sa.Column('location', sa.Text(), nullable=True),
    sa.Column('source', sa.Text(), nullable=True),
    sa.Column('posting_url', sa.Text(), nullable=True),
    sa.Column('dedupe_key', sa.Text(), nullable=False),
    sa.Column('status', sa.Text(), server_default='saved', nullable=False),
    sa.Column('seniority', sa.Text(), nullable=True),
    sa.Column('role_type', sa.Text(), nullable=True),
    sa.Column('requirements', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('applied_at', sa.Date(), nullable=True),
    sa.Column('last_status_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status IN ('saved', 'applied', 'oa', 'interview', 'offer', 'rejected', 'ghosted')", name=op.f('ck_applications_status')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_applications_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_applications')),
    sa.UniqueConstraint('user_id', 'dedupe_key', name='uq_applications_user_id_dedupe_key')
    )
    op.create_index(op.f('ix_applications_user_id'), 'applications', ['user_id'], unique=False)
    op.create_table('sessions',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('token_hash', sa.Text(), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_sessions_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_sessions')),
    sa.UniqueConstraint('token_hash', name=op.f('uq_sessions_token_hash'))
    )
    op.create_index(op.f('ix_sessions_user_id'), 'sessions', ['user_id'], unique=False)
    op.create_table('status_events',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('application_id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('from_status', sa.Text(), nullable=True),
    sa.Column('to_status', sa.Text(), nullable=False),
    sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("from_status IS NULL OR from_status IN ('saved', 'applied', 'oa', 'interview', 'offer', 'rejected', 'ghosted')", name=op.f('ck_status_events_from_status')),
    sa.CheckConstraint("to_status IN ('saved', 'applied', 'oa', 'interview', 'offer', 'rejected', 'ghosted')", name=op.f('ck_status_events_to_status')),
    sa.ForeignKeyConstraint(['application_id'], ['applications.id'], name=op.f('fk_status_events_application_id_applications'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_status_events_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_status_events'))
    )
    op.create_index(op.f('ix_status_events_application_id'), 'status_events', ['application_id'], unique=False)
    op.create_index(op.f('ix_status_events_user_id'), 'status_events', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_status_events_user_id'), table_name='status_events')
    op.drop_index(op.f('ix_status_events_application_id'), table_name='status_events')
    op.drop_table('status_events')
    op.drop_index(op.f('ix_sessions_user_id'), table_name='sessions')
    op.drop_table('sessions')
    op.drop_index(op.f('ix_applications_user_id'), table_name='applications')
    op.drop_table('applications')
    op.drop_table('users')
    op.drop_table('extraction_cache')
    # Leave the citext extension in place; other objects might depend on it.
