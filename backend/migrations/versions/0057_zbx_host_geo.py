"""Zabbix host inventory coordinates (the Devices map follows Zabbix).

Revision ID: 0057
Revises: 0056
"""
import sqlalchemy as sa
from alembic import op

revision = "0057"
down_revision = "0056"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("zbx_host", sa.Column("lat", sa.Float))
    op.add_column("zbx_host", sa.Column("lon", sa.Float))


def downgrade():
    pass
