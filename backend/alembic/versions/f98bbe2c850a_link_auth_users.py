"""link_auth_users

Revision ID: f98bbe2c850a
Revises: 77619896af41
Create Date: 2026-09-15 19:27:24.513913
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa



revision: str = 'f98bbe2c850a'
down_revision: str | None = '77619896af41'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        schema="public",
    )
    op.create_foreign_key(
        "users_auth_user_id_fkey", "users", "users", ["auth_user_id"], ["id"],
        source_schema="public", referent_schema="auth",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("users_auth_user_id_fkey", "users", schema="public", type_="foreignkey")
    op.drop_column("users", "is_active", schema="public")
