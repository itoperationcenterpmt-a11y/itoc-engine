"""Management Overview is strategic only (trends, gauges, donuts, no technical lists); Default Overview gets a gauge strip under the status banner.

Revision ID: 0047
Revises: 0046
"""
from alembic import op
from sqlalchemy import text

revision = "0047"
down_revision = "0046"
branch_labels = None
depends_on = None

W = lambda k, s: {"key": "w-viz-" + k, "size": s, "enabled": True}
P = lambda k, s: {"key": k, "size": s, "enabled": True}

TECH = ["needs-attention", "on-duty", "escalation", "it-care", "ticketing", "networking", "cyber-security", "xdr", "devices", "wifi", "milestone", "open-handovers", "top-5-links-by-downtime", "access-points-not-online",
        "client-trend-24h", "ndr-severity", "severity-and-status", "devices-map-network-sdwan", "insights"]

MANAGEMENT = [P("today-s-status", "c12"), W("gauge-sla", "c3"), W("gauge-link", "c3"), W("gauge-devices", "c3"), W("gauge-recording", "c3"),
              W("spark-tickets", "c3"), W("spark-downtime", "c3"), W("spark-ndr", "c3"), W("spark-xdr", "c3"),
              P("tickets-in-and-closed-per-day", "c8"), W("donut-tickets", "c4"), P("link-downtime-per-day", "c8"), W("donut-devices", "c4"),
              P("ndr-critical-and-high-per-day", "c6"), P("alerts-per-day", "c6"), W("heat-tickets", "c8"), W("donut-xdr", "c4")]

DEFAULT = [P("today-s-status", "c12"), W("gauge-sla", "c3"), W("gauge-link", "c3"), W("gauge-devices", "c3"), W("gauge-recording", "c3"),
           P("needs-attention", "c8"), P("on-duty", "c4"), P("insights", "c12"), P("escalation", "c6"), P("it-care", "c6"), P("ticketing", "c4"), P("networking", "c4"), P("cyber-security", "c4"),
           P("xdr", "c4"), P("devices", "c4"), P("wifi", "c4"), P("milestone", "c4"), P("open-handovers", "c8")]


def put(c, profile, blocks):
    shown = {b["key"] for b in blocks}
    rows = blocks + [{"key": k, "size": "", "enabled": False} for k in TECH + ["tickets-in-and-closed-per-day", "link-downtime-per-day", "ndr-critical-and-high-per-day", "alerts-per-day"] if k not in shown]
    c.execute(text("DELETE FROM layout WHERE profile = :p AND page = 'ringkasan'"), {"p": profile})
    for i, b in enumerate(rows, 1):
        c.execute(text("INSERT INTO layout (profile, page, role, key, title, size, enabled, sort) VALUES (:p, 'ringkasan', '', :k, '', :s, :e, :o)"), {"p": profile, "k": b["key"], "s": b["size"], "e": b["enabled"], "o": i})


def upgrade():
    c = op.get_bind()
    c.execute(text("UPDATE layout_profile SET description = 'Strategic view: service levels and trends as gauges, donuts and charts, no technical lists' WHERE key = 'management'"))
    put(c, "management", MANAGEMENT)
    if not c.execute(text("SELECT 1 FROM layout WHERE profile = 'default' AND page = 'ringkasan' LIMIT 1")).first():      # an admin's own default layout is left alone
        put(c, "default", DEFAULT)


def downgrade():
    pass
