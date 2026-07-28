"""add match coordinates

Revision ID: 0bb63757da75
Revises: b4fcc804c2cd
Create Date: 2026-07-28 13:03:05.433499

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0bb63757da75"
down_revision: str | Sequence[str] | None = "b4fcc804c2cd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("matches", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("matches", sa.Column("longitude", sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("matches", "longitude")
    op.drop_column("matches", "latitude")
