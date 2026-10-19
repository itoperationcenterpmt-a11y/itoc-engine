"""Tabel integrasi: secret, api_key, webhook.

Revision ID: 0012
Revises: 0011
"""
from alembic import op
from app import models

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade():
    for t in (models.Secret, models.ApiKey, models.Webhook):
        t.__table__.create(bind=op.get_bind(), checkfirst=True)


def downgrade():
    pass