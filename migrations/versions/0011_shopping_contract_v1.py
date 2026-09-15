"""Align shopping persistence with the Home Assistant shopping schema v1.

Revision ID: 0011_shopping_contract_v1
Revises: 0010_inventory_schema_v4
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_shopping_contract_v1"
down_revision: str | None = "0010_inventory_schema_v4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("shopping_items") as batch_op:
        batch_op.add_column(sa.Column("container_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("source_type", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("source_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("reason", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("status", sa.String(length=16), nullable=True))
        batch_op.add_column(
            sa.Column("purchased_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column("ignored_at", sa.DateTime(timezone=True), nullable=True)
        )

    op.execute(
        """
        UPDATE shopping_items
        SET source_type = CASE
                WHEN source = 'expired_inventory' THEN 'inventory_expired'
                ELSE COALESCE(source, 'manual')
            END,
            source_id = source_inventory_item_id,
            status = CASE WHEN completed = 1 THEN 'purchased' ELSE 'pending' END,
            purchased_at = completed_at,
            reason = CASE
                WHEN source = 'expired_inventory' AND notes IS NOT NULL THEN notes
                ELSE NULL
            END,
            schema_version = 1
        """
    )

    with op.batch_alter_table("shopping_items") as batch_op:
        batch_op.alter_column("source_type", nullable=False, server_default="manual")
        batch_op.alter_column("status", nullable=False, server_default="pending")
        batch_op.create_index(
            "ix_shopping_items_source",
            ["household_id", "source_type", "source_id"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("shopping_items") as batch_op:
        batch_op.drop_index("ix_shopping_items_source")
        batch_op.drop_column("ignored_at")
        batch_op.drop_column("purchased_at")
        batch_op.drop_column("status")
        batch_op.drop_column("reason")
        batch_op.drop_column("source_id")
        batch_op.drop_column("source_type")
        batch_op.drop_column("container_id")
