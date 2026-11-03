"""Milestone: servers are the main figure on the Overview, cameras online on the Milestone page; the recording gauge is replaced in the built-in layouts (still in the widget catalog).

Revision ID: 0050
Revises: 0049
"""
from alembic import op
from sqlalchemy import text

revision = "0050"
down_revision = "0049"
branch_labels = None
depends_on = None


def upgrade():
    c = op.get_bind()
    c.execute(text("UPDATE layout SET key = 'w-viz-gauge-ms-servers' WHERE key = 'w-viz-gauge-recording' AND page = 'ringkasan' AND profile IN ('default', 'management')"))
    c.execute(text("UPDATE layout l SET key = 'w-viz-gauge-cameras' WHERE key = 'w-viz-gauge-recording' AND NOT EXISTS (SELECT 1 FROM layout x WHERE x.profile = l.profile AND x.page = l.page AND x.role = l.role AND x.key = 'w-viz-gauge-cameras')"))


def downgrade():
    pass
