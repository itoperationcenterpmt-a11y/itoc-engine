"""Tabel prtg_daily (unggah RAW PRTG berupa PDF laporan harian).

Revision ID: 0002
Revises: 0001
"""
from alembic import op
from app import models

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    models.PrtgDaily.__table__.create(bind=op.get_bind(), checkfirst=True)


def downgrade():
    op.drop_table("prtg_daily")