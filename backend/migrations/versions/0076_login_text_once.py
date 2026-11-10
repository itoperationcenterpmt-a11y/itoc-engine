"""Login page: the division is named once (in the logo) instead of four times. Only values that still hold the old default text are changed, so edits made in Admin stay.

Revision ID: 0076
Revises: 0075
"""
import json

from alembic import op
from sqlalchemy import text

revision = "0076"
down_revision = "0075"
branch_labels = None
depends_on = None

CHANGES = [
    ("ui.login_eyebrow", "PT. Pelindo Multi Terminal · Divisi Teknologi Informasi", "PT Pelindo Multi Terminal"),
    ("ui.login_tagline", "Dashboard terpusat Divisi Teknologi Informasi PT Pelindo Multi Terminal.", "Dashboard terpusat untuk memantau seluruh terminal."),
    ("ui.footer", "© {year} IT Operation Center · Divisi Teknologi Informasi · Pelindo Multi Terminal", "© {year} IT Operation Center"),
]


def upgrade():
    c = op.get_bind()
    for key, old, new in CHANGES:
        c.execute(text("UPDATE app_parameter SET value = CAST(:n AS jsonb) WHERE key = :k AND value = CAST(:o AS jsonb)"),
                  {"k": key, "o": json.dumps(old, ensure_ascii=False), "n": json.dumps(new, ensure_ascii=False)})


def downgrade():
    pass
