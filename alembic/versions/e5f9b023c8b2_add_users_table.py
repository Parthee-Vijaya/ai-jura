"""add users table for @-mentions and future RBAC

Revision ID: e5f9b023c8b2
Revises: d4f8a912c5e3
Create Date: 2026-05-14 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e5f9b023c8b2'
down_revision: Union[str, None] = 'd4f8a912c5e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('email', sa.String(length=255), nullable=False, unique=True),
        sa.Column('display_name', sa.String(length=120), nullable=False),
        sa.Column('role', sa.String(length=32), nullable=False, server_default='sagsbehandler'),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_users_email_lower', 'users', [sa.text('LOWER(email)')])
    op.create_index('ix_users_active_email', 'users', ['active', 'email'])


def downgrade() -> None:
    op.drop_index('ix_users_active_email', table_name='users')
    op.drop_index('ix_users_email_lower', table_name='users')
    op.drop_table('users')
