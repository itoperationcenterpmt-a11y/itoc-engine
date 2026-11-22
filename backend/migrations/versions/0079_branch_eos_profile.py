"""Built-in Branch / EOS dashboard profile: single-branch operational focus (link SLA, devices down, WiFi APs, open tickets, and handover).

Revision ID: 0079
Revises: 0078
"""
from alembic import op
from sqlalchemy import text

revision = "0079"
down_revision = "0078"
branch_labels = None
depends_on = None

BLOCKS = [
    {"key": "right-now", "size": "c12", "enabled": True},
    {"key": "needs-attention", "size": "c8", "enabled": True},
    {"key": "on-duty", "size": "c4", "enabled": True},
    {"key": "w-viz-gauge-link", "size": "c3", "enabled": True},
    {"key": "w-viz-gauge-devices", "size": "c3", "enabled": True},
    {"key": "w-viz-gauge-sla", "size": "c3", "enabled": True},
    {"key": "w-viz-gauge-ap", "size": "c3", "enabled": True},
    {"key": "w-tk-open", "size": "c6", "enabled": True},
    {"key": "w-viz-top-devices", "size": "c6", "enabled": True},
    {"key": "w-viz-top-links", "size": "c6", "enabled": True},
    {"key": "w-wifi-apdown", "size": "c6", "enabled": True},
    {"key": "open-handovers", "size": "c12", "enabled": True},
    {"key": "this-period", "size": "", "enabled": False},
    {"key": "insights", "size": "", "enabled": False},
    {"key": "tickets-in-and-closed-per-day", "size": "", "enabled": False},
    {"key": "top-5-links-by-downtime", "size": "", "enabled": False},
    {"key": "link-downtime-per-day", "size": "", "enabled": False},
    {"key": "access-points-not-online", "size": "", "enabled": False},
    {"key": "client-trend-24h", "size": "", "enabled": False},
    {"key": "ndr-critical-and-high-per-day", "size": "", "enabled": False},
    {"key": "ndr-severity", "size": "", "enabled": False},
    {"key": "alerts-per-day", "size": "", "enabled": False},
    {"key": "severity-and-status", "size": "", "enabled": False},
    {"key": "contacts", "size": "", "enabled": False},
    {"key": "devices-map-network-sdwan", "size": "", "enabled": False},
]


def upgrade():
    c = op.get_bind()
    c.execute(text(
        "INSERT INTO layout_profile (key, name, description, builtin, sort) "
        "VALUES ('branch', 'Branch / EOS', 'Branch operational focus: link SLA, devices down, WiFi APs, and open tickets', true, 40) "
        "ON CONFLICT (key) DO NOTHING"
    ))
    c.execute(text("DELETE FROM layout WHERE profile = 'branch' AND page = 'ringkasan'"))
    for i, b in enumerate(BLOCKS, 1):
        c.execute(text(
            "INSERT INTO layout (profile, page, role, key, title, size, enabled, sort) "
            "VALUES ('branch', 'ringkasan', '', :k, '', :s, :e, :o)"
        ), {"k": b["key"], "s": b["size"], "e": b["enabled"], "o": i})


def downgrade():
    c = op.get_bind()
    c.execute(text("DELETE FROM layout WHERE profile = 'branch'"))
    c.execute(text("DELETE FROM layout_profile WHERE key = 'branch'"))
