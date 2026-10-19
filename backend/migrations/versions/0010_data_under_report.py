"""Menu Data menjadi sub-menu Report (Report | Handover | Data).

Revision ID: 0010
Revises: 0009
"""
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""UPDATE "module" SET parent = 'report' WHERE key = 'kelengkapan' AND parent IS NULL""")


def downgrade():
    pass