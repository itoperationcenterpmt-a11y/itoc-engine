"""Tabel zbx_host untuk konektor Zabbix (CCTV dan Gate System).

Revision ID: 0013
Revises: 0012
"""
from alembic import op
from app import models

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade():
    models.ZbxHost.__table__.create(bind=op.get_bind(), checkfirst=True)


def downgrade():
    pass