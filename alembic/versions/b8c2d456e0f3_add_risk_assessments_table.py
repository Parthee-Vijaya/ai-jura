"""add risk_assessments table — persistens + journalisering af risikovurderinger

Revision ID: b8c2d456e0f3
Revises: f6e9d234a1b3
Create Date: 2026-06-10 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b8c2d456e0f3'
down_revision: Union[str, None] = 'f6e9d234a1b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'risk_assessments',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('systemnavn', sa.String(length=200), nullable=False),
        # Valgfri kobling til en sag (eksternt case_id, fx 'K-2026-0042')
        sa.Column('case_id', sa.String(length=64), nullable=True),
        sa.Column('created_by', sa.String(length=128), nullable=True),
        # Hele Risikovurdering-objektet (facts + risici + felttekster) som JSON
        # — render kan reproduceres deterministisk uden nye LLM-kald.
        sa.Column('rv_json', sa.JSON(), nullable=False),
        # Denormaliseret til liste-visning uden at parse JSON
        sa.Column('n_risici', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('verify_valid', sa.Boolean(), nullable=True),
    )
    op.create_index('ix_risk_assessments_created_at', 'risk_assessments', ['created_at'])
    op.create_index('ix_risk_assessments_case_id', 'risk_assessments', ['case_id'])
    op.create_index('ix_risk_assessments_systemnavn', 'risk_assessments', ['systemnavn'])


def downgrade() -> None:
    op.drop_index('ix_risk_assessments_systemnavn', table_name='risk_assessments')
    op.drop_index('ix_risk_assessments_case_id', table_name='risk_assessments')
    op.drop_index('ix_risk_assessments_created_at', table_name='risk_assessments')
    op.drop_table('risk_assessments')
