"""Menu Devices: tambah filter Group (mis. Network-SDWAN) di bar filter.

Revision ID: 0016
Revises: 0015
"""
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""UPDATE "module" SET filters = filters || '{"g": 1}'::jsonb WHERE key = 'devices' AND NOT (filters ? 'g')""")


def downgrade():
    pass