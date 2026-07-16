"""Add processing progress fields

Revision ID: d4a8c2f10b31
Revises: cf5556774762
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d4a8c2f10b31"
down_revision: Union[str, Sequence[str], None] = "cf5556774762"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("processing_progress", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("documents", sa.Column("processing_stage", sa.String(), nullable=False, server_default="Uploaded"))


def downgrade() -> None:
    op.drop_column("documents", "processing_stage")
    op.drop_column("documents", "processing_progress")
