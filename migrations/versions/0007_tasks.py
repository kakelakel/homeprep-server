"""Add HomePrep recurring tasks.

Revision ID: 0007_tasks
Revises: 0006_assets
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_tasks"
down_revision: str | None = "0006_assets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("household_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("task_kind", sa.String(length=32), nullable=False, server_default="general"),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("linked_item_id", sa.String(length=36), nullable=True),
        sa.Column("linked_container_id", sa.String(length=36), nullable=True),
        sa.Column("linked_asset_id", sa.String(length=36), nullable=True),
        sa.Column("recurrence_type", sa.String(length=16), nullable=False, server_default="months"),
        sa.Column("recurrence_interval", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "reschedule_mode",
            sa.String(length=16),
            nullable=False,
            server_default="completion",
        ),
        sa.Column("last_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_due_at", sa.Date(), nullable=True),
        sa.Column("reminder_before_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("completion_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tasks_household_id", "tasks", ["household_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tasks_household_id", table_name="tasks")
    op.drop_table("tasks")
