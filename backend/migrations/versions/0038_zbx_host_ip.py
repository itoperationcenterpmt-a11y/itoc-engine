"""Zabbix hosts keep their interface IP so Milestone cameras can be matched to their online status.

Revision ID: 0038
Revises: 0037
"""
import sqlalchemy as sa
from alembic import op

revision = "0038"
down_revision = "0037"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("zbx_host", sa.Column("ip", sa.String(45), nullable=False, server_default=""))
    op.create_index("ix_zbx_host_ip", "zbx_host", ["ip"])


def downgrade():
    pass
