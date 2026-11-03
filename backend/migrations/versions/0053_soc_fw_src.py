"""Top source IPs per firewall and day.

Revision ID: 0053
Revises: 0052
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0053"
down_revision = "0052"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("soc_fw_day", sa.Column("src", JSONB, nullable=False, server_default="{}"))


def downgrade():
    pass
