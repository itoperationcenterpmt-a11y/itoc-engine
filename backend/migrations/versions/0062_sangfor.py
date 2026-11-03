"""Internet usage from Sangfor IAG Report Center exports: table sangfor_batch and the Internet Usage menu under Network.

Revision ID: 0062
Revises: 0061
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB

revision = "0062"
down_revision = "0061"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("sangfor_batch", sa.Column("id", sa.Integer, primary_key=True, autoincrement=True), sa.Column("site", sa.String(120), nullable=False), sa.Column("date_from", sa.Date, nullable=False),
                    sa.Column("date_to", sa.Date, nullable=False), sa.Column("uploaded_by", sa.String(60), nullable=False, server_default=""), sa.Column("uploaded_at", sa.DateTime, server_default=sa.func.now()),
                    sa.Column("file_name", sa.String(300), nullable=False, server_default=""), sa.Column("data", JSONB, nullable=False, server_default="{}"))
    op.create_index("ix_sangfor_batch_site", "sangfor_batch", ["site"])
    c = op.get_bind()
    c.execute(text("INSERT INTO module (key, label, sort, enabled, filters, note, why, parent, icon) VALUES ('sangfor', 'Internet Usage', 33, true, CAST(:f AS jsonb), :n, :w, 'network', 'activity') ON CONFLICT (key) DO NOTHING"),
              {"f": '{"p": 0, "s": 0, "l": 1, "c": 0, "g": 1}', "n": "Bandwidth, applications, and users from the Sangfor IAG Report Center export of each site.",
               "w": "Each figure covers the period of the uploaded Report Center export; choose the report period in the top filter bar. Shift and period filters do not apply."})
    c.execute(text("UPDATE role SET modules = array_append(modules, 'sangfor') WHERE 'noc' = ANY(modules) AND NOT ('*' = ANY(modules)) AND NOT ('sangfor' = ANY(modules))"))
    c.execute(text("UPDATE role SET uploads = array_append(uploads, 'sangfor') WHERE ('prtg' = ANY(uploads) OR 'soc' = ANY(uploads)) AND NOT ('*' = ANY(uploads)) AND NOT ('sangfor' = ANY(uploads))"))


def downgrade():
    pass
