"""Landing page: the brand letters explained on their own, and a supporting sentence in plain English.

Revision ID: 0056
Revises: 0055
"""
import json
from alembic import op
from sqlalchemy import text

revision = "0056"
down_revision = "0055"
branch_labels = None
depends_on = None

OLD = "Terminal Event, Response & Analytics. Pantau, tanggapi, analisis seluruh terminal dalam satu layar."
NEW = "One screen for every terminal: watch what happens, respond quickly, and learn from the data."


def upgrade():
    c = op.get_bind()
    c.execute(text("UPDATE app_parameter SET value = CAST(:n AS jsonb) WHERE key = 'ui.login_tagline' AND value = CAST(:o AS jsonb)"), {"n": json.dumps(NEW), "o": json.dumps(OLD)})
    c.execute(text("INSERT INTO app_parameter (key, value, label, \"group\", editor, ui, sort) VALUES ('ui.login_acronym', CAST(:v AS jsonb), :l, 'tampilan', 'json', '{}'::jsonb, 95) ON CONFLICT (key) DO NOTHING"),
              {"v": json.dumps([["T", "Terminal"], ["E", "Event"], ["R", "Response"], ["A", "Analytics"]]), "l": "What each letter of the brand stands for (letter, word)"})


def downgrade():
    pass
