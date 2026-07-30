"""add device_id to push tokens

Revision ID: 052fdc2388be
Revises: 4ff7c6bb6aa9
Create Date: 2026-07-30 16:09:28.245569

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "052fdc2388be"
down_revision: str | Sequence[str] | None = "4ff7c6bb6aa9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "push_tokens",
        sa.Column("device_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.create_index(op.f("ix_push_tokens_device_id"), "push_tokens", ["device_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_push_tokens_device_id"), table_name="push_tokens")
    op.drop_column("push_tokens", "device_id")
