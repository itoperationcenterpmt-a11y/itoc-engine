"""Menu CCTV (Milestone XProtect): role yang melihat Devices ikut melihat CCTV.

Revision ID: 0028
Revises: 0027
"""
from alembic import op

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""UPDATE role SET modules = array_append(modules, 'cctv') WHERE 'devices' = ANY(modules) AND NOT ('cctv' = ANY(modules))""")


def downgrade():
    op.execute("""UPDATE role SET modules = array_remove(modules, 'cctv')""")
