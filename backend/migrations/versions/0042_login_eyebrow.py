"""Login page eyebrow text.

Revision ID: 0042
Revises: 0041
"""
import json
from alembic import op
from sqlalchemy import text

revision = "0042"
down_revision = "0041"
branch_labels = None
depends_on = None


def upgrade():
    op.get_bind().execute(text("UPDATE app_parameter SET value = CAST(:v AS jsonb) WHERE key = 'ui.login_eyebrow'"), {"v": json.dumps("PT. Pelindo Multi Terminal · Divisi Teknologi Informasi")})


def downgrade():
    pass
