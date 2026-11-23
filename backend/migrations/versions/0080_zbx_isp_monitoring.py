"""Integrate Zabbix ISP-* monitoring widgets into NOC wall & Branch/EOS presets (Overview, Network Summary, and existing ISP sub-menu).

Revision ID: 0080
Revises: 0079
"""
from alembic import op
from sqlalchemy import text

revision = "0080"
down_revision = "0079"
branch_labels = None
depends_on = None

NOC_RINGKASAN = [
    {"key": "right-now", "size": "c12", "enabled": True},
    {"key": "w-viz-wall", "size": "c12", "enabled": True},
    {"key": "w-viz-gauge-zbxisp", "size": "c3", "enabled": True},
    {"key": "w-viz-gauge-link", "size": "c3", "enabled": True},
    {"key": "w-viz-gauge-devices", "size": "c3", "enabled": True},
    {"key": "w-viz-gauge-sla", "size": "c3", "enabled": True},
    {"key": "w-viz-zbxisp-providers", "size": "c5", "enabled": True},
    {"key": "w-viz-zbxisp-down", "size": "c7", "enabled": True},
    {"key": "w-viz-zbxisp-matrix", "size": "c12", "enabled": True},
    {"key": "w-viz-timeline", "size": "c12", "enabled": True},
    {"key": "w-viz-donut-devices", "size": "c4", "enabled": True},
    {"key": "w-viz-donut-cameras", "size": "c4", "enabled": True},
    {"key": "w-viz-donut-xdr", "size": "c4", "enabled": True},
    {"key": "needs-attention", "size": "c8", "enabled": True},
    {"key": "on-duty", "size": "c4", "enabled": True},
    {"key": "w-viz-top-links", "size": "c6", "enabled": True},
    {"key": "w-viz-top-devices", "size": "c6", "enabled": True},
]

NOC_NETWORK = [
    {"key": "attention", "size": "c12", "enabled": True},
    {"key": "kpis", "size": "c12", "enabled": True},
    {"key": "kpis-2", "size": "c12", "enabled": True},
    {"key": "kpis-3", "size": "c12", "enabled": True},
    {"key": "w-viz-gauge-zbxisp", "size": "c3", "enabled": True},
    {"key": "w-viz-gauge-link", "size": "c3", "enabled": True},
    {"key": "w-viz-gauge-ap", "size": "c3", "enabled": True},
    {"key": "w-viz-spark-zbxisp", "size": "c3", "enabled": True},
    {"key": "isp-status-by-provider", "size": "c5", "enabled": True},
    {"key": "isp-links-down-now", "size": "c7", "enabled": True},
    {"key": "branch-isp-redundancy-matrix", "size": "c12", "enabled": True},
    {"key": "w-viz-zbxisp-timeline", "size": "c12", "enabled": True},
    {"key": "w-viz-timeline", "size": "c12", "enabled": True},
    {"key": "link-downtime-per-day", "size": "c8", "enabled": True},
    {"key": "access-points-not-online", "size": "c4", "enabled": True},
]

NOC_ISP = [
    {"key": "kpis", "size": "c12", "enabled": True},
    {"key": "kpis-2", "size": "c12", "enabled": True},
    {"key": "isp-live-availability", "size": "c3", "enabled": True},
    {"key": "isp-links-by-provider", "size": "c4", "enabled": True},
    {"key": "isp-status-by-provider", "size": "c5", "enabled": True},
    {"key": "isp-links-down-now", "size": "c6", "enabled": True},
    {"key": "isp-outages-by-provider", "size": "c6", "enabled": True},
    {"key": "branch-isp-redundancy-matrix", "size": "c12", "enabled": True},
    {"key": "isp-outage-timeline-zabbix", "size": "c12", "enabled": True},
    {"key": "w-viz-gauge-link", "size": "c4", "enabled": True},
    {"key": "w-viz-spark-downtime", "size": "c4", "enabled": True},
    {"key": "w-viz-top-links", "size": "c4", "enabled": True},
    {"key": "w-viz-timeline", "size": "c12", "enabled": True},
    {"key": "link-ranking-by-downtime", "size": "c12", "enabled": True},
]


def _set_layout(c, profile: str, page: str, blocks: list[dict]):
    c.execute(text("DELETE FROM layout WHERE profile = :p AND page = :g AND role = ''"), {"p": profile, "g": page})
    for i, b in enumerate(blocks, 1):
        c.execute(text(
            "INSERT INTO layout (profile, page, role, key, title, size, enabled, sort) "
            "VALUES (:p, :g, '', :k, '', :s, :e, :o)"
        ), {"p": profile, "g": page, "k": b["key"], "s": b["size"], "e": b["enabled"], "o": i})


def upgrade():
    c = op.get_bind()
    _set_layout(c, "noc", "ringkasan", NOC_RINGKASAN)
    _set_layout(c, "noc", "network", NOC_NETWORK)
    _set_layout(c, "noc", "noc", NOC_ISP)
    c.execute(text(
        "UPDATE layout SET key = 'w-viz-gauge-zbxisp' "
        "WHERE profile = 'branch' AND page = 'ringkasan' AND key = 'w-viz-gauge-ap'"
    ))


def downgrade():
    pass
