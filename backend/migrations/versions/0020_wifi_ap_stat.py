"""WiFi: tabel wifi_ap (status Access Point) dan wifi_stat (riwayat tren).

Revision ID: 0020
Revises: 0019
"""
from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE IF NOT EXISTS wifi_ap (
        mac varchar(20) PRIMARY KEY, name varchar(160), zone varchar(120), ap_group varchar(120), status varchar(40), model varchar(60),
        ip varchar(64), clients integer, firmware varchar(60), location varchar(200), last_seen timestamp, updated_at timestamp NOT NULL DEFAULT now())""")
    op.execute("""CREATE TABLE IF NOT EXISTS wifi_stat (
        at timestamp PRIMARY KEY, clients integer NOT NULL DEFAULT 0, users integer NOT NULL DEFAULT 0, rx_bytes bigint NOT NULL DEFAULT 0,
        tx_bytes bigint NOT NULL DEFAULT 0, ap_online integer NOT NULL DEFAULT 0, ap_total integer NOT NULL DEFAULT 0)""")


def downgrade():
    op.execute("DROP TABLE IF EXISTS wifi_stat")
    op.execute("DROP TABLE IF EXISTS wifi_ap")