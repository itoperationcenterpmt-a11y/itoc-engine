"""XDR: keep the complete Vision One alert (raw JSON) plus case id, model id and schema version, so every detail of the ticket/incident is in the database.

Revision ID: 0078
Revises: 0077
"""
from alembic import op

revision = "0078"
down_revision = "0077"
branch_labels = None
depends_on = None


def upgrade():
    for col, typ in (("raw", "jsonb"), ("case_id", "varchar(80)"), ("model_id", "varchar(80)"), ("schema_version", "varchar(20)")):
        op.execute(f"ALTER TABLE xdr_alert ADD COLUMN IF NOT EXISTS {col} {typ}")
    op.execute("CREATE INDEX IF NOT EXISTS ix_xdr_alert_incident ON xdr_alert (incident_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_xdr_alert_case ON xdr_alert (case_id)")
    op.execute("""UPDATE data_source SET cursor = '{}'::jsonb WHERE key = 'trendmicro'""")     # pull history again so old alerts get the full payload


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_xdr_alert_case")
    op.execute("DROP INDEX IF EXISTS ix_xdr_alert_incident")
    for col in ("raw", "case_id", "model_id", "schema_version"):
        op.execute(f"ALTER TABLE xdr_alert DROP COLUMN IF EXISTS {col}")
