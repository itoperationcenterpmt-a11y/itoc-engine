"""Per firewall detail (threat type, category, applications) and the shared NDR parameter (Head Office and Belawan).

Revision ID: 0052
Revises: 0051
"""
import json
import sqlalchemy as sa
from alembic import op
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB

revision = "0052"
down_revision = "0051"
branch_labels = None
depends_on = None


def upgrade():
    for col in ("typ", "cat", "app"):
        op.add_column("soc_fw_day", sa.Column(col, JSONB, nullable=False, server_default="{}"))
    c = op.get_bind()
    c.execute(text("INSERT INTO app_parameter (key, value, label, \"group\", editor, ui, sort) VALUES ('soc.shared_ndr', CAST(:v AS jsonb), :l, 'soc', 'json', '{}'::jsonb, 9) ON CONFLICT (key) DO NOTHING"),
              {"v": json.dumps([["Head Office", "Branch Belawan"]]), "l": "Locations that share one NDR (each list = locations using the same firewall)"})
    c.execute(text("DELETE FROM soc_fw_day"))          # refilled with the new detail on the next syncs


def downgrade():
    pass
