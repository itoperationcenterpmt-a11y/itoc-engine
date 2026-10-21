"""Trend Micro Vision One (XDR): tabel xdr_alert dan akses modul XDR untuk role ITOC Shift dan Management.

Revision ID: 0024
Revises: 0023
"""
from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE IF NOT EXISTS xdr_alert (
        id varchar(80) PRIMARY KEY, incident_id varchar(80), model varchar(300), model_type varchar(40), severity varchar(20), score integer,
        status varchar(40), investigation_status varchar(40), provider varchar(80), created_at timestamp NOT NULL, updated_at timestamp,
        owners jsonb, impact jsonb, indicators jsonb, link varchar(600), fetched_at timestamp NOT NULL DEFAULT now())""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_xdr_alert_created ON xdr_alert (created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_xdr_alert_severity ON xdr_alert (severity)")
    op.execute("""UPDATE role SET modules = array_append(modules, 'xdr') WHERE key IN ('itoc', 'manajemen') AND NOT ('xdr' = ANY(modules))""")


def downgrade():
    op.execute("DROP TABLE IF EXISTS xdr_alert")