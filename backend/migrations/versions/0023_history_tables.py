"""Riwayat: wifi_session (sesi client WiFi), zbx_event (kejadian down Zabbix), zbx_stat (cuplikan per jam), dan filter periode di menu WiFi dan Devices.

Revision ID: 0023
Revises: 0022
"""
from alembic import op

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE IF NOT EXISTS wifi_session (
        mac varchar(20) NOT NULL, started_at timestamp NOT NULL, ended_at timestamp, last_seen timestamp, ip varchar(64), username varchar(160),
        hostname varchar(160), device varchar(80), ssid varchar(120), ap_mac varchar(20), ap_name varchar(160), zone varchar(120), loc varchar(120),
        auth varchar(60), rx_bytes bigint, tx_bytes bigint, PRIMARY KEY (mac, started_at))""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_wifi_session_start ON wifi_session (started_at)")
    op.execute("""CREATE TABLE IF NOT EXISTS zbx_event (
        eventid varchar(20) PRIMARY KEY, hostid varchar(20) NOT NULL, host_name varchar(255), kind varchar(40), code varchar(40), dev_code varchar(20),
        name varchar(255), start_at timestamp NOT NULL, end_at timestamp)""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_zbx_event_host ON zbx_event (hostid)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_zbx_event_start ON zbx_event (start_at)")
    op.execute("""CREATE TABLE IF NOT EXISTS zbx_stat (
        hour timestamp NOT NULL, kind varchar(40) NOT NULL, total integer NOT NULL DEFAULT 0, up integer NOT NULL DEFAULT 0, down integer NOT NULL DEFAULT 0,
        degraded integer NOT NULL DEFAULT 0, maintenance integer NOT NULL DEFAULT 0, PRIMARY KEY (hour, kind))""")
    op.execute("""UPDATE "module" SET filters = filters || '{"p": 1}'::jsonb WHERE key IN ('wifi', 'devices')""")


def downgrade():
    op.execute("DROP TABLE IF EXISTS zbx_stat")
    op.execute("DROP TABLE IF EXISTS zbx_event")
    op.execute("DROP TABLE IF EXISTS wifi_session")