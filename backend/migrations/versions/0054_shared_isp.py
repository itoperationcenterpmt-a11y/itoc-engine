"""Locations that share ISP links (Head Office and Belawan).

Revision ID: 0054
Revises: 0053
"""
import json
from alembic import op
from sqlalchemy import text

revision = "0054"
down_revision = "0053"
branch_labels = None
depends_on = None


def upgrade():
    op.get_bind().execute(text("INSERT INTO app_parameter (key, value, label, \"group\", editor, ui, sort) VALUES ('net.shared_isp', CAST(:v AS jsonb), :l, 'network', 'json', '{}'::jsonb, 30) ON CONFLICT (key) DO NOTHING"),
                          {"v": json.dumps([["Head Office", "Branch Belawan"]]), "l": "Locations that share the same ISP links (each list = locations using the same links; tickets and WiFi stay separate)"})


def downgrade():
    pass
