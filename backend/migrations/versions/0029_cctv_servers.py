"""Milestone banyak server: kolom server pada cctv_hardware dan cctv_camera, dan daftar server di konfigurasi sumber (server pertama = Base URL lama).

Revision ID: 0029
Revises: 0028
"""
from alembic import op

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE cctv_hardware ADD COLUMN IF NOT EXISTS server varchar(80) NOT NULL DEFAULT 'HO'")
    op.execute("ALTER TABLE cctv_camera ADD COLUMN IF NOT EXISTS server varchar(80) NOT NULL DEFAULT 'HO'")
    op.execute("""UPDATE data_source SET config = config || jsonb_build_object('servers', jsonb_build_array('HO|' || (config->>'base_url')))
                  WHERE key = 'milestone' AND NOT (config ? 'servers') AND coalesce(config->>'base_url', '') <> ''""")


def downgrade():
    op.execute("ALTER TABLE cctv_camera DROP COLUMN IF EXISTS server")
    op.execute("ALTER TABLE cctv_hardware DROP COLUMN IF EXISTS server")
