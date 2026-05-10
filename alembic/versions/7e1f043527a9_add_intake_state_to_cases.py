"""add intake_state to cases

Revision ID: 7e1f043527a9
Revises: ab8a73e13ad8
Create Date: 2026-05-10 12:57:25.209515

Tilføjer JSON-kolonne til persistering af indkøbsproces-wizardens state
(behov, dobbeltsystem-tjek, indkøb-vs-udvikling, system-beskrivelse, current step).

Bruges af IndkoebsprocesPage's auto-save så brugere kan lukke browseren og
genoptage præcis hvor de slap, samt af 'Mine sager'-stripen til at liste drafts.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7e1f043527a9'
down_revision: Union[str, None] = 'ab8a73e13ad8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'cases',
        sa.Column('intake_state', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('cases', 'intake_state')
