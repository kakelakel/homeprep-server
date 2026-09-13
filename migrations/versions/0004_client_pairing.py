"""Add one-time client pairing requests.

Revision ID: 0004_client_pairing
Revises: 0003_client_credentials
Create Date: 2026-09-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_client_pairing"
down_revision: str | None = "0003_client_credentials"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "client_pairings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("pairing_token_hash", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("client_type", sa.String(length=32), nullable=False),
        sa.Column("access_role", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_client_pairings_pairing_token_hash"),
        "client_pairings",
        ["pairing_token_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_client_pairings_pairing_token_hash"), table_name="client_pairings")
    op.drop_table("client_pairings")
