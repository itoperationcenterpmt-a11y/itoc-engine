"""On-hold tickets pause the SLA clock.

Revision ID: 0046
Revises: 0045
"""
import json
from alembic import op
from sqlalchemy import text

revision = "0046"
down_revision = "0045"
branch_labels = None
depends_on = None

PARAMS = [("sd.onhold_statuses", ["Onhold", "On Hold"], "Ticket statuses that pause the SLA clock (one per line)", "list", 16), ("sd.onhold_pauses_sla", 1, "On-hold tickets are not counted as late or old (1 = yes, 0 = no)", "number", 17)]


def upgrade():
    c = op.get_bind()
    for k, v, label, ed, sort in PARAMS:
        c.execute(text("INSERT INTO app_parameter (key, value, label, \"group\", editor, ui, sort) VALUES (:k, CAST(:v AS jsonb), :l, 'servicedesk', :e, '{}'::jsonb, :s) ON CONFLICT (key) DO NOTHING"), {"k": k, "v": json.dumps(v), "l": label, "e": ed, "s": sort})


def downgrade():
    pass
