"""Peta Devices: pasang berkas peta dasar bawaan (assets/id-map.json) bila parameternya masih kosong.

Revision ID: 0017
Revises: 0016
"""
from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""UPDATE app_parameter SET value = '"assets/id-map.json"'::jsonb WHERE key = 'dev.basemap_url' AND value = '""'::jsonb""")


def downgrade():
    pass