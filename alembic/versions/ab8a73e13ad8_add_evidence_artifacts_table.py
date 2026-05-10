"""add evidence_artifacts table

Revision ID: ab8a73e13ad8
Revises: 5df7504ce7f5
Create Date: 2026-05-10 11:58:37.950727

Persisterer per-sag udfyldte evidens-artefakter (risikostyringsplan, DPIA,
partshøringsbrev osv.) som bruges af V3VurderingPage's interaktive
checkliste. Alle 19 priority-skabeloner + 47 generic-fallbacks identificeret
af Tyrs regelmotor kan udfyldes og gemmes pr. sag.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ab8a73e13ad8'
down_revision: Union[str, None] = '5df7504ce7f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'evidence_artifacts',
        sa.Column('case_id', sa.String(length=64), nullable=False),
        sa.Column('artifact_id', sa.String(length=96), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False, server_default='mangler'),
        sa.Column('content_json', sa.Text(), nullable=False, server_default='{}'),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_edited_by', sa.String(length=64), nullable=True),
        sa.Column('completed_by', sa.String(length=64), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('case_id', 'artifact_id', name='pk_evidence_artifacts'),
    )
    op.create_index(
        'ix_evidence_case_status',
        'evidence_artifacts',
        ['case_id', 'status'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_evidence_case_status', table_name='evidence_artifacts')
    op.drop_table('evidence_artifacts')
