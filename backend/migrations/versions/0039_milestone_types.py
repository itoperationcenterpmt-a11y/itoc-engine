"""Milestone: public announcer classification, licence-free models, and the Type filter.

Revision ID: 0039
Revises: 0038
"""
import json
from alembic import op
from sqlalchemy import text

revision = "0039"
down_revision = "0038"
branch_labels = None
depends_on = None

PARAMS = [
    ("ms.pa_patterns", ["speaker"], "Milestone devices counted as Public Announcers (text found in model, hardware, or device name; one per line)", "list", 10),
    ("ms.no_license_models", ["ICPDriver"], "Milestone models that do not use a licence on this server (Interconnect hardware; one per line)", "list", 11),
]


def upgrade():
    c = op.get_bind()
    for key, val, label, editor, sort in PARAMS:
        c.execute(text("INSERT INTO app_parameter (key, value, label, \"group\", editor, ui, sort) VALUES (:k, CAST(:v AS jsonb), :l, 'devices', :e, '{}'::jsonb, :s) ON CONFLICT (key) DO NOTHING"),
                  {"k": key, "v": json.dumps(val), "l": label, "e": editor, "s": sort})
    c.execute(text("UPDATE module SET filters = CAST('{\"p\": 0, \"s\": 0, \"l\": 0, \"c\": 0, \"g\": 1, \"y\": 1, \"t\": 1, \"k\": 1}' AS jsonb) WHERE key = 'cctv'"))


def downgrade():
    pass
