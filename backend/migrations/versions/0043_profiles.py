"""Dashboard profiles: named layout sets, chosen per user.

Revision ID: 0043
Revises: 0042
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision = "0043"
down_revision = "0042"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("layout_profile", sa.Column("key", sa.String(40), primary_key=True), sa.Column("name", sa.String(80), nullable=False), sa.Column("description", sa.String(200)),
                    sa.Column("builtin", sa.Boolean, nullable=False, server_default="false"), sa.Column("sort", sa.Integer, nullable=False, server_default="0"))
    c = op.get_bind()
    c.execute(text("INSERT INTO layout_profile (key, name, description, builtin, sort) VALUES ('default', 'Default', 'The standard layout of every page', true, 0)"))
    op.add_column("layout", sa.Column("profile", sa.String(40), nullable=False, server_default="default"))
    op.drop_constraint("layout_pkey", "layout", type_="primary")
    op.create_primary_key("layout_pkey", "layout", ["profile", "page", "role", "key"])
    op.add_column("app_user", sa.Column("profile", sa.String(40), nullable=False, server_default="default"))


def downgrade():
    pass
