"""Landing page copy: TERA = Telemetry, Events, Response & Analytics, each letter explained, an ITOC Portal badge, the IT Care WhatsApp contact, and an optional security verification key.

Revision ID: 0058
Revises: 0057
"""
import json
from alembic import op
from sqlalchemy import text

revision = "0058"
down_revision = "0057"
branch_labels = None
depends_on = None

ACR = [["T", "Telemetry", "Kondisi Link ISP dan infrastruktur secara real-time"], ["E", "Events", "Ticket, Threat, dan aksi Firewall dari seluruh terminal"],
       ["R", "Response", "Penanganan insiden dan pemenuhan SLA oleh tim ITOC"], ["A", "Analytics", "Trend, evaluasi, dan report Excel, PDF, serta PowerPoint"]]
TAG = "TERA adalah Dashboard terpusat Divisi Teknologi Informasi PT Pelindo Multi Terminal. Satu layar untuk memantau Telemetry Jaringan, Ticket dan SLA, serta Threat Event di seluruh terminal."
OLD_TAG = "One screen for every terminal: watch what happens, respond quickly, and learn from the data."
OLD_ACR = [["T", "Terminal"], ["E", "Event"], ["R", "Response"], ["A", "Analytics"]]


def put(c, key, value, label, group, editor, sort):
    c.execute(text("INSERT INTO app_parameter (key, value, label, \"group\", editor, ui, sort) VALUES (:k, CAST(:v AS jsonb), :l, :g, :e, '{}'::jsonb, :s) ON CONFLICT (key) DO NOTHING"),
              {"k": key, "v": json.dumps(value), "l": label, "g": group, "e": editor, "s": sort})


def upgrade():
    c = op.get_bind()
    c.execute(text("UPDATE app_parameter SET value = CAST(:n AS jsonb) WHERE key = 'ui.login_tagline' AND value IN (CAST(:o AS jsonb), CAST(:o2 AS jsonb))"),
              {"n": json.dumps(TAG), "o": json.dumps(OLD_TAG), "o2": json.dumps("Terminal Event, Response & Analytics. Pantau, tanggapi, analisis seluruh terminal dalam satu layar.")})
    c.execute(text("UPDATE app_parameter SET value = CAST(:n AS jsonb), label = 'What each letter of the brand stands for (letter, word, description)' WHERE key = 'ui.login_acronym' AND value = CAST(:o AS jsonb)"),
              {"n": json.dumps(ACR), "o": json.dumps(OLD_ACR)})
    phone = c.execute(text("SELECT value ->> 'phone' FROM app_parameter WHERE key = 'report.contact'")).scalar() or ""
    put(c, "ui.login_badge", "ITOC Portal", "Badge under the login page title", "tampilan", "text", 96)
    put(c, "ui.support_phone", phone, "IT Care WhatsApp number for the login page (digits with country code; empty = no link)", "tampilan", "text", 97)
    put(c, "security.turnstile_site_key", "", "Cloudflare Turnstile site key for the login page (empty = off; the secret goes in the ITOC_TURNSTILE_SECRET environment variable)", "keamanan", "text", 5)


def downgrade():
    pass
