"""add skabelon_bibliotek and evidence_comments tables

Revision ID: d4f8a912c5e3
Revises: c3a6c58b4d43
Create Date: 2026-05-10 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4f8a912c5e3'
down_revision: Union[str, None] = 'c3a6c58b4d43'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- skabelon_bibliotek (genbrugbare evidens-skabeloner) -----------
    op.create_table(
        'skabelon_bibliotek',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('artifact_id', sa.String(length=96), nullable=False),
        sa.Column('name', sa.String(length=160), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('content_json', sa.Text(), nullable=False, server_default='{}'),
        sa.Column('source_case_id', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', sa.String(length=64), nullable=True),
        sa.Column('times_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_skabelon_bibliotek_artifact', 'skabelon_bibliotek', ['artifact_id'])

    # ---- evidence_comments (per evidens-felt diskussion) ---------------
    op.create_table(
        'evidence_comments',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('case_id', sa.String(length=64), nullable=False),
        sa.Column('artifact_id', sa.String(length=96), nullable=False),
        sa.Column('section_key', sa.String(length=96), nullable=True),  # null = på hele dokumentet
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('author', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by', sa.String(length=64), nullable=True),
    )
    op.create_index(
        'ix_evidence_comments_case_artifact',
        'evidence_comments',
        ['case_id', 'artifact_id'],
    )
    op.create_index(
        'ix_evidence_comments_section',
        'evidence_comments',
        ['case_id', 'artifact_id', 'section_key'],
    )
    op.create_index(
        'ix_evidence_comments_created_at',
        'evidence_comments',
        ['created_at'],
    )


def downgrade() -> None:
    op.drop_index('ix_evidence_comments_created_at', table_name='evidence_comments')
    op.drop_index('ix_evidence_comments_section', table_name='evidence_comments')
    op.drop_index('ix_evidence_comments_case_artifact', table_name='evidence_comments')
    op.drop_table('evidence_comments')

    op.drop_index('ix_skabelon_bibliotek_artifact', table_name='skabelon_bibliotek')
    op.drop_table('skabelon_bibliotek')
