"""Tabel layout: tata letak halaman dashboard per role (tombol Customize).

Revision ID: 0009
Revises: 0008
"""
from alembic import op
from app import models

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    models.Layout.__table__.create(bind=op.get_bind(), checkfirst=True)


def downgrade():
    pass