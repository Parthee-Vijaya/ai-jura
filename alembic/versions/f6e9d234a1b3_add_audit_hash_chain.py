"""add prev_hash + entry_hash columns to audit-tabeller (tamper-evidens)

Revision ID: f6e9d234a1b3
Revises: e5f9b023c8b2
Create Date: 2026-05-14 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f6e9d234a1b3'
down_revision: Union[str, None] = 'e5f9b023c8b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Tabeller der får hash-chain. Hver entry får:
#   prev_hash  — entry_hash for forrige entry (genesis hvis første)
#   entry_hash — sha256(prev_hash || canonical_json(payload))
HASH_CHAINED_TABLES = (
    "v3_assessment_log",
    "audit_access_log",
)


def upgrade() -> None:
    for table in HASH_CHAINED_TABLES:
        op.add_column(
            table,
            sa.Column("prev_hash", sa.String(length=64), nullable=True),
        )
        op.add_column(
            table,
            sa.Column("entry_hash", sa.String(length=64), nullable=True),
        )
        # Index på entry_hash så vi hurtigt kan finde chain-head
        op.create_index(
            f"ix_{table}_entry_hash", table, ["entry_hash"]
        )


def downgrade() -> None:
    for table in HASH_CHAINED_TABLES:
        op.drop_index(f"ix_{table}_entry_hash", table_name=table)
        op.drop_column(table, "entry_hash")
        op.drop_column(table, "prev_hash")
