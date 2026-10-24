"""Palo Alto events per firewall: tables soc_fw_day and soc_fw_map; the NDR page can be filtered by location.

Revision ID: 0051
Revises: 0050
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB

revision = "0051"
down_revision = "0050"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("soc_fw_day", sa.Column("day", sa.Date, primary_key=True), sa.Column("fw", sa.String(120), primary_key=True), sa.Column("sev", JSONB, nullable=False, server_default="{}"),
                    sa.Column("act", JSONB, nullable=False, server_default="{}"), sa.Column("bytes", sa.BigInteger, nullable=False, server_default="0"), sa.Column("sessions", sa.BigInteger, nullable=False, server_default="0"))
    op.create_index("ix_soc_fw_day_day", "soc_fw_day", ["day"])
    op.create_table("soc_fw_map", sa.Column("fw", sa.String(120), primary_key=True), sa.Column("site", sa.String(120)))
    c = op.get_bind()
    c.execute(text("""UPDATE module SET filters = '{"c": 1, "l": 1, "p": 1, "s": 0}'::jsonb,
                      why = 'The all-location totals come from a daily summary of every firewall. Choosing a location shows that location''s firewalls (data collected per firewall since the first sync after this update); shift does not apply.' WHERE key = 'soc'"""))


def downgrade():
    op.drop_table("soc_fw_map")
    op.drop_table("soc_fw_day")
