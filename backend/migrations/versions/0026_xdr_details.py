"""XDR: kolom detail alert (deskripsi, hasil investigasi, entitas terdampak, teknik MITRE, aturan yang cocok).

Revision ID: 0026
Revises: 0025
"""
from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade():
    for col, typ in (("description", "text"), ("investigation_result", "varchar(80)"), ("entities", "jsonb"), ("techniques", "jsonb"), ("rules", "jsonb")):
        op.execute(f"ALTER TABLE xdr_alert ADD COLUMN IF NOT EXISTS {col} {typ}")
    op.execute("""UPDATE data_source SET cursor = '{}'::jsonb WHERE key = 'trendmicro'""")     # tarik ulang agar alert lama ikut terisi detailnya


def downgrade():
    for col in ("description", "investigation_result", "entities", "techniques", "rules"):
        op.execute(f"ALTER TABLE xdr_alert DROP COLUMN IF EXISTS {col}")