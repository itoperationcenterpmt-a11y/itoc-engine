"""Insights stay visible on the XDR, NDR, WiFi and Milestone pages in every profile; the renamed MITRE panel keeps its layout; the new Ticket Coverage panel.

Revision ID: 0048
Revises: 0047
"""
from alembic import op
from sqlalchemy import text

revision = "0048"
down_revision = "0047"
branch_labels = None
depends_on = None


def upgrade():
    c = op.get_bind()
    c.execute(text("UPDATE layout SET key = 'mitre-att-ck-techniques' WHERE key = 'teknik-mitre-att-ck'"))
    c.execute(text("UPDATE layout SET enabled = true WHERE key = 'insights' AND page IN ('xdr', 'soc', 'wifi', 'cctv')"))
    for prof in [r[0] for r in c.execute(text("SELECT DISTINCT profile FROM layout WHERE page = 'xdr'"))]:
        c.execute(text("INSERT INTO layout (profile, page, role, key, title, size, enabled, sort) VALUES (:p, 'xdr', '', 'ticket-coverage', '', '', :e, 99) ON CONFLICT DO NOTHING"), {"p": prof, "e": prof == "security"})


def downgrade():
    pass
