"""Report widget titles in English, one sentence-case style.

Revision ID: 0060
Revises: 0059
"""
from alembic import op
from sqlalchemy import text

revision = "0060"
down_revision = "0059"
branch_labels = None
depends_on = None

TITLES = {"noc_status": "Link SLA status", "noc_availability": "Link distribution by availability", "noc_isp_status": "SLA status per ISP", "sd_duration": "Distribution of resolution time",
          "sd_hour": "Tickets received per hour", "sd_tech": "Top 10 technicians", "sd_sla": "SLA compliance per level", "soc_severity": "Events per severity", "soc_action": "Firewall actions"}


def upgrade():
    c = op.get_bind()
    for k, t in TITLES.items():
        c.execute(text("UPDATE widget SET title = :t WHERE key = :k AND title <> ''"), {"k": k, "t": t})


def downgrade():
    pass
