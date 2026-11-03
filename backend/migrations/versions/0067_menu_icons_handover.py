"""Menu: distinct icons per page, and Handover becomes its own top-level menu (it is a shift workflow, not a report).

Revision ID: 0067
Revises: 0066
"""
from alembic import op
from sqlalchemy import text

revision = "0067"
down_revision = "0066"
branch_labels = None
depends_on = None

ICONS = {"network": "network", "noc": "link", "internet": "globe", "insight": "bulb", "devnet": "router", "devops": "wrench"}


def upgrade():
    c = op.get_bind()
    for key, icon in ICONS.items():
        c.execute(text("UPDATE module SET icon = :i WHERE key = :k"), {"i": icon, "k": key})
    c.execute(text("UPDATE module SET parent = NULL, sort = 7 WHERE key = 'serahterima'"))
    c.execute(text("UPDATE module SET sort = 8 WHERE key = 'report'"))
    c.execute(text("UPDATE module SET sort = 9 WHERE key = 'insight'"))


def downgrade():
    c = op.get_bind()
    c.execute(text("UPDATE module SET parent = 'report', sort = 9 WHERE key = 'serahterima'"))
    c.execute(text("UPDATE module SET sort = 7 WHERE key = 'report'"))
    c.execute(text("UPDATE module SET sort = 8 WHERE key = 'insight'"))
