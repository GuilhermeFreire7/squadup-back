"""add push tokens table

Revision ID: 4ff7c6bb6aa9
Revises: 0bb63757da75
Create Date: 2026-07-28 13:03:05.433499

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4ff7c6bb6aa9"
down_revision: str | Sequence[str] | None = "0bb63757da75"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "push_tokens",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("user_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("token", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_push_tokens_token"), "push_tokens", ["token"], unique=True)
    op.create_index(op.f("ix_push_tokens_user_id"), "push_tokens", ["user_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_push_tokens_user_id"), table_name="push_tokens")
    op.drop_index(op.f("ix_push_tokens_token"), table_name="push_tokens")
    op.drop_table("push_tokens")
