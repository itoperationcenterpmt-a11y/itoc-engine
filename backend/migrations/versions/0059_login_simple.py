"""Simpler landing page: a headline, one sentence, and one short line per letter.

Revision ID: 0059
Revises: 0058
"""
import json
from alembic import op
from sqlalchemy import text

revision = "0059"
down_revision = "0058"
branch_labels = None
depends_on = None

OLD_TAG = "TERA adalah Dashboard terpusat Divisi Teknologi Informasi PT Pelindo Multi Terminal. Satu layar untuk memantau Telemetry Jaringan, Ticket dan SLA, serta Threat Event di seluruh terminal."
NEW_TAG = "Dashboard terpusat Divisi Teknologi Informasi PT Pelindo Multi Terminal."
OLD_ACR = [["T", "Telemetry", "Kondisi Link ISP dan infrastruktur secara real-time"], ["E", "Events", "Ticket, Threat, dan aksi Firewall dari seluruh terminal"],
           ["R", "Response", "Penanganan insiden dan pemenuhan SLA oleh tim ITOC"], ["A", "Analytics", "Trend, evaluasi, dan report Excel, PDF, serta PowerPoint"]]
NEW_ACR = [["T", "Telemetry", "Link ISP dan infrastruktur real-time"], ["E", "Events", "Ticket, threat, dan aksi firewall"], ["R", "Response", "Penanganan insiden dan SLA"], ["A", "Analytics", "Trend, evaluasi, dan report"]]


def upgrade():
    c = op.get_bind()
    c.execute(text("UPDATE app_parameter SET value = CAST(:n AS jsonb) WHERE key = 'ui.login_tagline' AND value = CAST(:o AS jsonb)"), {"n": json.dumps(NEW_TAG), "o": json.dumps(OLD_TAG)})
    c.execute(text("UPDATE app_parameter SET value = CAST(:n AS jsonb) WHERE key = 'ui.login_acronym' AND value = CAST(:o AS jsonb)"), {"n": json.dumps(NEW_ACR), "o": json.dumps(OLD_ACR)})
    c.execute(text("INSERT INTO app_parameter (key, value, label, \"group\", editor, ui, sort) VALUES ('ui.login_headline', CAST(:v AS jsonb), 'Headline on the login page', 'tampilan', 'text', '{}'::jsonb, 94) ON CONFLICT (key) DO NOTHING"),
              {"v": json.dumps("Satu layar untuk seluruh terminal")})


def downgrade():
    pass
