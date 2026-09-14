"""Add Shopping List and internal notifications.

Revision ID: 0009_operations
Revises: 0008_planning
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_operations"
down_revision: str | None = "0008_planning"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "shopping_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("household_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False, server_default="1"),
        sa.Column("unit", sa.String(length=32), nullable=False, server_default="pcs"),
        sa.Column("category", sa.String(length=64), nullable=False, server_default="other"),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="manual"),
        sa.Column("source_inventory_item_id", sa.String(length=36), nullable=True),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_shopping_items_household_id",
        "shopping_items",
        ["household_id"],
        unique=False,
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("household_id", sa.String(length=36), nullable=False),
        sa.Column("event_key", sa.String(length=255), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False, server_default="attention"),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=True),
        sa.Column("resource_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_notifications_household_id",
        "notifications",
        ["household_id"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_event_key",
        "notifications",
        ["event_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_event_key", table_name="notifications")
    op.drop_index("ix_notifications_household_id", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_shopping_items_household_id", table_name="shopping_items")
    op.drop_table("shopping_items")
