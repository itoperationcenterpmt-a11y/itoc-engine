"""Milestone: PTZ classification pattern (everything that is not PTZ or a public announcer is FIX).

Revision ID: 0040
Revises: 0039
"""
import json
from alembic import op
from sqlalchemy import text

revision = "0040"
down_revision = "0039"
branch_labels = None
depends_on = None


def upgrade():
    op.get_bind().execute(text("INSERT INTO app_parameter (key, value, label, \"group\", editor, ui, sort) VALUES ('ms.ptz_patterns', CAST(:v AS jsonb), :l, 'devices', 'list', '{}'::jsonb, 12) ON CONFLICT (key) DO NOTHING"),
                          {"v": json.dumps(["ptz"]), "l": "Milestone devices counted as PTZ (text found in model, hardware, or device name; one per line). Everything else is FIX"})


def downgrade():
    pass
