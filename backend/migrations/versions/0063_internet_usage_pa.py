"""Internet Usage now comes from Palo Alto (Panorama): application categories, web categories, and top web users per firewall and day. The Sangfor upload is removed.

Revision ID: 0063
Revises: 0062
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB

revision = "0063"
down_revision = "0062"
branch_labels = None
depends_on = None


def upgrade():
    for col in ("acat", "urlc", "webu"):
        op.add_column("soc_fw_day", sa.Column(col, JSONB, nullable=False, server_default="{}"))
    op.drop_table("sangfor_batch")
    c = op.get_bind()
    c.execute(text("DELETE FROM module WHERE key = 'sangfor'"))
    c.execute(text("INSERT INTO module (key, label, sort, enabled, filters, note, why, parent, icon) VALUES ('internet', 'Internet Usage', 33, true, CAST(:f AS jsonb), :n, :w, 'network', 'activity') ON CONFLICT (key) DO NOTHING"),
              {"f": '{"p": 1, "s": 0, "l": 1, "c": 0}', "n": "Traffic, applications, web categories, and top users per location, from the Palo Alto firewalls (Panorama).",
               "w": "Figures are collected per firewall and day, so shift does not apply. A location shows the firewalls matched to it; Head Office and Belawan share one."})
    c.execute(text("UPDATE role SET modules = array_remove(modules, 'sangfor')"))
    c.execute(text("UPDATE role SET uploads = array_remove(uploads, 'sangfor')"))
    c.execute(text("UPDATE role SET modules = array_append(modules, 'internet') WHERE 'noc' = ANY(modules) AND NOT ('*' = ANY(modules)) AND NOT ('internet' = ANY(modules))"))


def downgrade():
    pass
