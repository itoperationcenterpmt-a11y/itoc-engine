"""Milestone menu gets filters: server, hardware, and state.

Revision ID: 0037
Revises: 0036
"""
from alembic import op
from sqlalchemy import text

revision = "0037"
down_revision = "0036"
branch_labels = None
depends_on = None


def upgrade():
    op.get_bind().execute(text("UPDATE module SET filters = CAST('{\"p\": 0, \"s\": 0, \"l\": 0, \"c\": 0, \"g\": 1, \"y\": 1, \"t\": 1}' AS jsonb), why = 'The Milestone camera inventory is the current state, so period, shift, and location do not apply. Filter by server, hardware, and state.' WHERE key = 'cctv'"))


def downgrade():
    pass
