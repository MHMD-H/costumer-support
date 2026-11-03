"""harden_shopify_connection_state

Revision ID: 8f3c1a7d2b44
Revises: 309b92d5b8f1
Create Date: 2026-10-25
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "8f3c1a7d2b44"
down_revision: str | None = "309b92d5b8f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Bind new states to a shop and purge application-database tokens."""
    op.execute(sa.text("delete from public.shopify_oauth_states"))
    op.add_column(
        "shopify_oauth_states",
        sa.Column("shop_domain", sa.Text(), nullable=False),
        schema="public",
    )
    op.drop_column("shopify_connections", "access_token_encrypted", schema="public")


def downgrade() -> None:
    """Restore the previous shape without attempting to reconstruct deleted tokens."""
    op.add_column(
        "shopify_connections",
        sa.Column("access_token_encrypted", sa.Text(), nullable=True),
        schema="public",
    )
    op.drop_column("shopify_oauth_states", "shop_domain", schema="public")
