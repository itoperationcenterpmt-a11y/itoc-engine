"""Nama menu: Service Desk -> Ticketing, NOC -> Networking, SOC -> Cyber Security (hanya bila belum diubah Admin).

Revision ID: 0011
Revises: 0010
"""
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade():
    for key, old, new in (("servicedesk", "Service Desk", "Ticketing"), ("noc", "NOC", "Networking"), ("soc", "SOC", "Cyber Security")):
        op.execute(f"""UPDATE "module" SET label = '{new}' WHERE key = '{key}' AND label = '{old}'""")


def downgrade():
    pass