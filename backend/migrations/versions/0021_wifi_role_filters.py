"""WiFi: filter SSID/zone/band di menu WiFi Users dan role WiFi Viewer (hanya melihat WiFi Users).

Revision ID: 0021
Revises: 0020
"""
from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""UPDATE "module" SET filters = filters || '{"k": 1, "g": 1, "y": 1}'::jsonb WHERE key = 'wifi'""")
    op.execute("""INSERT INTO role (key, label, modules, can_write, is_admin, admin_view, scope, uploads, sort)
                  SELECT 'wifiview', 'WiFi Viewer', ARRAY['wifi'], false, false, false, 'all', ARRAY[]::varchar[], 7
                  WHERE NOT EXISTS (SELECT 1 FROM role WHERE key = 'wifiview')""")


def downgrade():
    op.execute("DELETE FROM role WHERE key = 'wifiview'")