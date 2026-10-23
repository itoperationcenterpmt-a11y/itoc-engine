"""TERA branding: product name, login texts, and footer.

Revision ID: 0041
Revises: 0040
"""
import json
from alembic import op
from sqlalchemy import text

revision = "0041"
down_revision = "0040"
branch_labels = None
depends_on = None

NEW = {'ui.brand_name': 'TERA Dashboard', 'ui.brand_split': 1, 'ui.footer': '© {year} IT Operation Center · Divisi Teknologi Informasi · Pelindo Multi Terminal', 'ui.login_tagline': 'Terminal Event, Response & Analytics. Pantau, tanggapi, analisis seluruh terminal dalam satu layar.', 'ui.login_eyebrow': 'Pelindo Multi Terminal · IT Operation Center'}


def upgrade():
    c = op.get_bind()
    for k, v in NEW.items():
        c.execute(text("UPDATE app_parameter SET value = CAST(:v AS jsonb) WHERE key = :k"), {"k": k, "v": json.dumps(v)})


def downgrade():
    pass
