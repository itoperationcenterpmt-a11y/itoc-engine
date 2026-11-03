"""The app stays English: the login page returns to its own texts (no EN/ID switch). Handover moves under Personnel (shown below the ITOC group), and the Uptime Kuma page is named Link / Web Availability.

Revision ID: 0071
Revises: 0070
"""
import json

from alembic import op
from sqlalchemy import text

revision = "0071"
down_revision = "0070"
branch_labels = None
depends_on = None


def upgrade():
    c = op.get_bind()
    row = c.execute(text("SELECT value FROM app_parameter WHERE key = 'ui.login_id'")).first()
    if row:
        for k, v in (row[0] or {}).items():
            c.execute(text("UPDATE app_parameter SET value = CAST(:v AS jsonb) WHERE key = :k"), {"v": json.dumps(v, ensure_ascii=False), "k": "ui.login_" + k})
        c.execute(text("DELETE FROM app_parameter WHERE key = 'ui.login_id'"))
    c.execute(text("UPDATE module SET parent = 'jadwal', sort = 61 WHERE key = 'serahterima'"))
    c.execute(text("UPDATE module SET sort = 7 WHERE key = 'report'"))
    c.execute(text("UPDATE module SET sort = 8 WHERE key = 'insight'"))
    c.execute(text("UPDATE module SET label = 'Link / Web Availability', note = :n WHERE key = 'kuma'"),
              {"n": "Availability and response time of the links and web services watched by Uptime Kuma (websites, ports, ping, certificates)."})


def downgrade():
    pass
