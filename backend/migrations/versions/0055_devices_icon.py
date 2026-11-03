"""The Devices menu uses a server icon instead of the camera.

Revision ID: 0055
Revises: 0054
"""
from alembic import op
from sqlalchemy import text

revision = "0055"
down_revision = "0054"
branch_labels = None
depends_on = None


def upgrade():
    op.get_bind().execute(text("UPDATE module SET icon = 'server' WHERE key = 'devices' AND icon = 'camera'"))


def downgrade():
    pass
