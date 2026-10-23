"""Overview: clear saved layouts so the redesigned default order applies; normalize insight kinds to English.

Revision ID: 0034
Revises: 0033
"""
from alembic import op

revision = "0034"
down_revision = "0033"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("DELETE FROM layout WHERE page = 'ringkasan'")
    for old, new in (("link", "links"), ("tiket", "tickets"), ("perangkat", "devices"), ("ndr", "security"), ("xdr", "security")):
        op.execute(f"UPDATE insight SET kind = '{new}' WHERE kind = '{old}'")


def downgrade():
    pass
