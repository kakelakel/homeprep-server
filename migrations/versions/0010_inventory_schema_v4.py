"""Align inventory items with Home Assistant schema v4.

Revision ID: 0010_inventory_schema_v4
Revises: 0009_operations
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_inventory_schema_v4"
down_revision: str | None = "0009_operations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("inventory_items") as batch_op:
        batch_op.add_column(sa.Column("image_id", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("image_token", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("image_content_type", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("image_filename", sa.String(length=255), nullable=True))

    op.execute("UPDATE inventory_items SET schema_version = 4")


def downgrade() -> None:
    op.execute("UPDATE inventory_items SET schema_version = 1")
    with op.batch_alter_table("inventory_items") as batch_op:
        batch_op.drop_column("image_filename")
        batch_op.drop_column("image_content_type")
        batch_op.drop_column("image_token")
        batch_op.drop_column("image_id")
