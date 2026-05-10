"""add notifications table

Revision ID: c3a6c58b4d43
Revises: 7e1f043527a9
Create Date: 2026-05-10 16:30:49.091705

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3a6c58b4d43'
down_revision: Union[str, None] = '7e1f043527a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'notifications',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('kind', sa.String(length=32), nullable=False),
        sa.Column('severity', sa.String(length=16), nullable=False, server_default='info'),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('case_id', sa.String(length=64), nullable=True),
        sa.Column('link_url', sa.String(length=255), nullable=True),
        sa.Column('actor', sa.String(length=64), nullable=True),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_notifications_created_at', 'notifications', ['created_at'])
    op.create_index('ix_notifications_kind', 'notifications', ['kind'])
    op.create_index('ix_notifications_case_id', 'notifications', ['case_id'])
    op.create_index('ix_notifications_read_at', 'notifications', ['read_at'])
    op.create_index('ix_notifications_unread', 'notifications', ['read_at', 'created_at'])


def downgrade() -> None:
    op.drop_index('ix_notifications_unread', table_name='notifications')
    op.drop_index('ix_notifications_read_at', table_name='notifications')
    op.drop_index('ix_notifications_case_id', table_name='notifications')
    op.drop_index('ix_notifications_kind', table_name='notifications')
    op.drop_index('ix_notifications_created_at', table_name='notifications')
    op.drop_table('notifications')
