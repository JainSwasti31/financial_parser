"""Add active status to users

Revision ID: a91f04c7e2b8
Revises: d4a8c2f10b31
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a91f04c7e2b8"
down_revision: Union[str, Sequence[str], None] = "d4a8c2f10b31"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade() -> None:
    op.drop_column("users", "is_active")
