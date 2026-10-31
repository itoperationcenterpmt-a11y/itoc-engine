"""Uptime Kuma: monitor snapshot and hourly samples, the data source, and a page in the Network menu.

Revision ID: 0070
Revises: 0069
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision = "0070"
down_revision = "0069"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("kuma_monitor", sa.Column("key", sa.String(240), primary_key=True), sa.Column("name", sa.String(200), nullable=False), sa.Column("type", sa.String(30)), sa.Column("url", sa.String(300)),
                    sa.Column("hostname", sa.String(200)), sa.Column("port", sa.String(10)), sa.Column("status", sa.SmallInteger, nullable=False, server_default="1"), sa.Column("response_ms", sa.Float),
                    sa.Column("cert_days", sa.Integer), sa.Column("updated_at", sa.DateTime, nullable=False))
    op.create_table("kuma_hourly", sa.Column("monitor_key", sa.String(240), primary_key=True), sa.Column("ts", sa.DateTime, primary_key=True), sa.Column("samples", sa.Integer, nullable=False, server_default="0"),
                    sa.Column("down", sa.Integer, nullable=False, server_default="0"), sa.Column("sum_ms", sa.Float, nullable=False, server_default="0"), sa.Column("n_ms", sa.Integer, nullable=False, server_default="0"), sa.Column("max_ms", sa.Float))
    op.create_index("ix_kuma_hourly_ts", "kuma_hourly", ["ts"])
    c = op.get_bind()
    c.execute(text("""INSERT INTO data_source (key, label, mode, enabled, interval_min, config, tip, cursor) VALUES ('uptimekuma', 'Uptime Kuma', 'api', false, 5, CAST(:c AS jsonb), :t, '{}'::jsonb) ON CONFLICT (key) DO NOTHING"""),
              {"c": '{"base_url": "", "user_env": "KUMA_USER", "pass_env": "KUMA_PASS", "verify_tls": true, "timeout_s": 30}', "t": "Uptime Kuma /metrics: monitor status, response time, and availability (read only)"})
    c.execute(text("INSERT INTO module (key, label, sort, enabled, filters, note, why, parent, icon) VALUES ('kuma', 'Uptime Kuma', 34, true, CAST(:f AS jsonb), :n, :w, 'network', 'pulse') ON CONFLICT (key) DO NOTHING"),
              {"f": '{"p": 1, "s": 0, "l": 1, "c": 0}', "n": "Availability and response time of the services watched by Uptime Kuma (websites, ports, ping, certificates).",
               "w": "Samples are taken on every sync (about every 5 minutes) and kept per hour, so shift does not apply. A location shows the monitors whose name or host matches it."})
    c.execute(text("UPDATE role SET modules = array_append(modules, 'kuma') WHERE 'noc' = ANY(modules) AND NOT ('*' = ANY(modules)) AND NOT ('kuma' = ANY(modules))"))


def downgrade():
    op.drop_table("kuma_hourly")
    op.drop_table("kuma_monitor")
