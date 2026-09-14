"""Add HomePrep containers.

Revision ID: 0005_containers
Revises: 0004_client_pairing
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_containers"
down_revision: str | None = "0004_client_pairing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "containers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("household_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("container_type", sa.String(length=32), nullable=False, server_default="other"),
        sa.Column("location", sa.String(length=240), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_containers_household_id", "containers", ["household_id"], unique=False)

    with op.batch_alter_table("inventory_items") as batch_op:
        batch_op.create_foreign_key(
            "fk_inventory_items_container_id_containers",
            "containers",
            ["container_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("inventory_items") as batch_op:
        batch_op.drop_constraint("fk_inventory_items_container_id_containers", type_="foreignkey")
    op.drop_index("ix_containers_household_id", table_name="containers")
    op.drop_table("containers")
