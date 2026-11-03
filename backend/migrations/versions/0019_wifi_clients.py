"""Client WiFi dari Ruckus vSZ: tabel wifi_client dan akses menu WiFi untuk role ITOC Shift.

Revision ID: 0019
Revises: 0018
"""
from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE IF NOT EXISTS wifi_client (
        mac varchar(20) PRIMARY KEY, ip varchar(64), username varchar(160), hostname varchar(160), ssid varchar(120),
        ap_name varchar(160), ap_mac varchar(20), zone varchar(120), os varchar(120), rssi integer, vlan integer,
        started_at timestamp, rx_bytes bigint, tx_bytes bigint, raw jsonb, updated_at timestamp NOT NULL DEFAULT now())""")
    op.execute("""UPDATE role SET modules = array_append(modules, 'wifi') WHERE key = 'itoc' AND NOT ('wifi' = ANY(modules))""")


def downgrade():
    op.execute("DROP TABLE IF EXISTS wifi_client")