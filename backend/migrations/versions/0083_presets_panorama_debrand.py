"""Upgrade 5 dashboard presets (Default, NOC Wall, SOC Wall, Management, Branch/EOS) for sharper relevance and set Panorama schedule to every 6 hours.

Revision ID: 0083
Revises: 0082
"""
import json
from alembic import op
from sqlalchemy import text

revision = "0083"
down_revision = "0082"
branch_labels = None
depends_on = None

# Tailored Overview layouts per role preset
SOC_WALL = [
    {"key": "w-viz-spark-ndr", "size": "c3", "enabled": True},
    {"key": "w-viz-spark-xdr", "size": "c3", "enabled": True},
    {"key": "w-viz-donut-ndr-act", "size": "c3", "enabled": True},
    {"key": "w-viz-donut-xdr", "size": "c3", "enabled": True},
    {"key": "ndr-critical-and-high-per-day", "size": "c8", "enabled": True},
    {"key": "ndr-severity", "size": "c4", "enabled": True},
    {"key": "alerts-per-day", "size": "c8", "enabled": True},
    {"key": "severity-and-status", "size": "c4", "enabled": True},
    {"key": "needs-attention", "size": "c8", "enabled": True},
    {"key": "on-duty", "size": "c4", "enabled": True},
    {"key": "insights", "size": "c12", "enabled": True},
    {"key": "right-now", "size": "", "enabled": False},
    {"key": "this-period", "size": "", "enabled": False},
    {"key": "tickets-in-and-closed-per-day", "size": "", "enabled": False},
    {"key": "top-5-links-by-downtime", "size": "", "enabled": False},
    {"key": "isp-status-by-provider", "size": "", "enabled": False},
    {"key": "isp-links-down-now", "size": "", "enabled": False},
    {"key": "link-downtime-per-day", "size": "", "enabled": False},
    {"key": "access-points-not-online", "size": "", "enabled": False},
    {"key": "client-trend-24h", "size": "", "enabled": False},
    {"key": "open-handovers", "size": "", "enabled": False},
    {"key": "contacts", "size": "", "enabled": False},
    {"key": "devices-map-network-sdwan", "size": "", "enabled": False},
]

MANAGEMENT = [
    {"key": "w-viz-gauge-sla", "size": "c3", "enabled": True},
    {"key": "w-viz-gauge-link", "size": "c3", "enabled": True},
    {"key": "w-viz-gauge-devices", "size": "c3", "enabled": True},
    {"key": "w-viz-gauge-ms-servers", "size": "c3", "enabled": True},
    {"key": "this-period", "size": "c12", "enabled": True},
    {"key": "w-viz-health-wall", "size": "c8", "enabled": True},
    {"key": "on-duty", "size": "c4", "enabled": True},
    {"key": "needs-attention", "size": "c12", "enabled": True},
    {"key": "right-now", "size": "", "enabled": False},
    {"key": "insights", "size": "", "enabled": False},
    {"key": "tickets-in-and-closed-per-day", "size": "", "enabled": False},
    {"key": "top-5-links-by-downtime", "size": "", "enabled": False},
    {"key": "isp-status-by-provider", "size": "", "enabled": False},
    {"key": "isp-links-down-now", "size": "", "enabled": False},
    {"key": "link-downtime-per-day", "size": "", "enabled": False},
    {"key": "access-points-not-online", "size": "", "enabled": False},
    {"key": "client-trend-24h", "size": "", "enabled": False},
    {"key": "ndr-critical-and-high-per-day", "size": "", "enabled": False},
    {"key": "ndr-severity", "size": "", "enabled": False},
    {"key": "alerts-per-day", "size": "", "enabled": False},
    {"key": "severity-and-status", "size": "", "enabled": False},
    {"key": "open-handovers", "size": "", "enabled": False},
    {"key": "contacts", "size": "", "enabled": False},
    {"key": "devices-map-network-sdwan", "size": "", "enabled": False},
]

NOC_WALL = [
    {"key": "w-viz-gauge-link", "size": "c3", "enabled": True},
    {"key": "w-viz-gauge-devices", "size": "c3", "enabled": True},
    {"key": "w-viz-gauge-ap", "size": "c3", "enabled": True},
    {"key": "w-viz-gauge-ms-servers", "size": "c3", "enabled": True},
    {"key": "isp-status-by-provider", "size": "c5", "enabled": True},
    {"key": "isp-links-down-now", "size": "c7", "enabled": True},
    {"key": "w-zbx-isp-matrix", "size": "c12", "enabled": True},
    {"key": "w-viz-health-wall", "size": "c8", "enabled": True},
    {"key": "on-duty", "size": "c4", "enabled": True},
    {"key": "devices-map-network-sdwan", "size": "c12", "enabled": True},
    {"key": "needs-attention", "size": "c12", "enabled": True},
    {"key": "right-now", "size": "", "enabled": False},
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
    {"key": "open-handovers", "size": "", "enabled": False},
    {"key": "contacts", "size": "", "enabled": False},
]


def upgrade() -> None:
    bind = op.get_bind()
    # 1. Update Panorama schedule to every 6 hours (00:00, 06:00, 12:00, 18:00)
    row = bind.execute(text("SELECT config FROM data_source WHERE key = 'panorama'")).fetchone()
    if row is not None:
        cfg = row[0] if isinstance(row[0], dict) else (json.loads(row[0]) if row[0] else {})
        cfg["schedule"] = ["00:00", "06:00", "12:00", "18:00"]
        bind.execute(text("UPDATE data_source SET config = CAST(:c AS jsonb) WHERE key = 'panorama'"), {"c": json.dumps(cfg)})

    # 2. Rename 'security' profile to 'SOC Wall' & polish descriptions
    bind.execute(text(
        "UPDATE layout_profile SET name = 'SOC Wall', description = 'Cyber security wallboard: NDR threat trends, XDR critical/high backlog, and security insights' WHERE key = 'security'"
    ))
    bind.execute(text(
        "UPDATE layout_profile SET name = 'NOC Wall', description = 'Infrastructure & ISP wallboard: dual-link redundancy, live links, device health, and site map' WHERE key = 'noc'"
    ))
    bind.execute(text(
        "UPDATE layout_profile SET description = 'Executive summary: SLA gauges, period posture, and location health scoreboard' WHERE key = 'management'"
    ))

    # 3. Apply tailored Overview layouts for SOC Wall, Management, and NOC Wall
    for prof, blocks in (("security", SOC_WALL), ("management", MANAGEMENT), ("noc", NOC_WALL)):
        exists = bind.execute(text("SELECT 1 FROM layout_profile WHERE key = :p"), {"p": prof}).fetchone()
        if not exists:
            continue
        bind.execute(text("DELETE FROM layout WHERE profile = :p AND page = 'ringkasan' AND role = ''"), {"p": prof})
        for i, b in enumerate(blocks, 1):
            bind.execute(
                text("INSERT INTO layout (profile, page, role, key, title, size, enabled, sort) VALUES (:p, 'ringkasan', '', :k, '', :s, :e, :o)"),
                {"p": prof, "k": b["key"], "s": b["size"], "e": b["enabled"], "o": i},
            )


def downgrade() -> None:
    bind = op.get_bind()
    row = bind.execute(text("SELECT config FROM data_source WHERE key = 'panorama'")).fetchone()
    if row is not None:
        cfg = row[0] if isinstance(row[0], dict) else (json.loads(row[0]) if row[0] else {})
        cfg["schedule"] = ["00:00", "12:00"]
        bind.execute(text("UPDATE data_source SET config = CAST(:c AS jsonb) WHERE key = 'panorama'"), {"c": json.dumps(cfg)})
