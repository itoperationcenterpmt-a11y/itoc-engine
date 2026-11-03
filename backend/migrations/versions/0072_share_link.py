"""Report share links that work without signing in for at most 3 days.

Revision ID: 0072
Revises: 0071
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0072"
down_revision = "0071"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("share_link", sa.Column("id", sa.Integer, primary_key=True), sa.Column("token_hash", sa.String(64), nullable=False, unique=True), sa.Column("created_by", sa.String(60), nullable=False),
                    sa.Column("spec", JSONB, nullable=False), sa.Column("created_at", sa.DateTime, nullable=False), sa.Column("expires_at", sa.DateTime, nullable=False), sa.Column("revoked_at", sa.DateTime),
                    sa.Column("downloads", sa.Integer, nullable=False, server_default="0"), sa.Column("last_used_at", sa.DateTime))


def downgrade():
    op.drop_table("share_link")
