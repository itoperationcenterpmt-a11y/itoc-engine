"""WiFi: filter lokasi di menu WiFi Users.

Revision ID: 0022
Revises: 0021
"""
from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""UPDATE "module" SET filters = filters || '{"l": 1}'::jsonb WHERE key = 'wifi'""")


def downgrade():
    op.execute("""UPDATE "module" SET filters = filters || '{"l": 0}'::jsonb WHERE key = 'wifi'""")