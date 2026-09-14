"""Add HomePrep household assets.

Revision ID: 0006_assets
Revises: 0005_containers
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_assets"
down_revision: str | None = "0005_containers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "assets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("household_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("asset_type", sa.String(length=32), nullable=False, server_default="other"),
        sa.Column("location", sa.String(length=240), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("image_id", sa.String(length=120), nullable=True),
        sa.Column("image_token", sa.String(length=255), nullable=True),
        sa.Column("image_content_type", sa.String(length=120), nullable=True),
        sa.Column("image_filename", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assets_household_id", "assets", ["household_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_assets_household_id", table_name="assets")
    op.drop_table("assets")
