"""Insight otomatis: tabel insight, menu Insight, dan akses role monitoring.

Revision ID: 0032
Revises: 0031
"""
from alembic import op

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE IF NOT EXISTS insight (
        id serial PRIMARY KEY, key varchar(160) NOT NULL, kind varchar(20) NOT NULL, severity varchar(10) NOT NULL, title varchar(200) NOT NULL, detail text NOT NULL,
        tab varchar(30), site varchar(120), metric jsonb, status varchar(10) NOT NULL DEFAULT 'baru', first_seen timestamp NOT NULL, last_seen timestamp NOT NULL,
        resolved_at timestamp, ack_by varchar(60), ack_at timestamp, notified boolean NOT NULL DEFAULT false)""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_insight_key_open ON insight (key, status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_insight_last ON insight (last_seen)")
    op.execute("""INSERT INTO module (key, label, sort, enabled, filters, note, why, parent, icon) VALUES
        ('insight', 'Insight', 2, true, '{"p": 0, "s": 0, "l": 0, "c": 0}', 'Temuan analisis otomatis: lonjakan, tren menurun, dan kejadian berulang. Dihitung ulang tiap 30 menit dari data yang sudah tersimpan.', 'Insight dihitung dari riwayat data, jadi filter periode, shift, dan lokasi tidak berlaku.', NULL, 'activity')
        ON CONFLICT (key) DO NOTHING""")
    op.execute("""UPDATE role SET modules = array_append(modules, 'insight') WHERE key IN ('itoc', 'manajemen') AND NOT ('insight' = ANY(modules))""")


def downgrade():
    op.execute("DROP TABLE IF EXISTS insight")
    op.execute("DELETE FROM module WHERE key = 'insight'")
    op.execute("UPDATE role SET modules = array_remove(modules, 'insight')")
