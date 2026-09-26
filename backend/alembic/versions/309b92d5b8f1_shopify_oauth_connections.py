"""shopify_oauth_connections

Revision ID: 309b92d5b8f1
Revises: f98bbe2c850a
Create Date: 2026-09-18 16:45:41.569064
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa



revision: str = '309b92d5b8f1'
down_revision: str | None = 'f98bbe2c850a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column("users", "tenant_id", existing_type=sa.UUID(), nullable=True, schema="public")
    op.create_table(
        "shopify_oauth_states",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("state_hash", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("state_hash", name="shopify_oauth_states_state_hash_key"),
        schema="public",
    )
    op.create_index("shopify_oauth_states_expires_at_idx", "shopify_oauth_states", ["expires_at"], schema="public")
    op.create_table(
        "shopify_connections",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("shop_id", sa.Text(), nullable=False),
        sa.Column("shop_domain", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'active'"), nullable=False),
        sa.Column("access_token_encrypted", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status = 'active'", name="shopify_connections_status_check"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", name="shopify_connections_tenant_id_key"),
        sa.UniqueConstraint("shop_id", name="shopify_connections_shop_id_key"),
        sa.UniqueConstraint("shop_domain", name="shopify_connections_shop_domain_key"),
        schema="public",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("shopify_connections", schema="public")
    op.drop_index("shopify_oauth_states_expires_at_idx", table_name="shopify_oauth_states", schema="public")
    op.drop_table("shopify_oauth_states", schema="public")
    op.alter_column("users", "tenant_id", existing_type=sa.UUID(), nullable=False, schema="public")
