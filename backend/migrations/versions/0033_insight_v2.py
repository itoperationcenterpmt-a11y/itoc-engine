"""Insight v2: English statuses, dismissal reason and suppression, handover link; Insights moves under the Report menu.

Revision ID: 0033
Revises: 0032
"""
from alembic import op

revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE insight ADD COLUMN IF NOT EXISTS reason varchar(200)")
    op.execute("ALTER TABLE insight ADD COLUMN IF NOT EXISTS suppress_until timestamp")
    op.execute("ALTER TABLE insight ADD COLUMN IF NOT EXISTS handover_id integer")
    op.execute("ALTER TABLE insight ALTER COLUMN status SET DEFAULT 'new'")
    for old, new in (("baru", "new"), ("dibaca", "read"), ("selesai", "resolved")):
        op.execute(f"UPDATE insight SET status = '{new}' WHERE status = '{old}'")
    op.execute("""UPDATE module SET label = 'Insights', parent = 'report', sort = 8, note = 'Automatic findings, rankings, location health, and a shift summary, calculated from stored data every 30 minutes.', why = 'Insights are calculated from historical data, so the period, shift, and location filters do not apply.' WHERE key = 'insight'""")
    op.execute("UPDATE module SET sort = 6 WHERE key = 'jadwal'")
    op.execute("UPDATE module SET sort = 7 WHERE key = 'report'")
    op.execute("UPDATE module SET sort = 9 WHERE key = 'serahterima'")
    op.execute("UPDATE module SET sort = 10 WHERE key = 'kelengkapan'")
    op.execute("UPDATE module SET sort = 11 WHERE key = 'admin'")
    op.execute("DELETE FROM insight WHERE status = 'resolved' AND resolved_at < now() - interval '30 days'")


def downgrade():
    op.execute("ALTER TABLE insight DROP COLUMN IF EXISTS handover_id")
    op.execute("ALTER TABLE insight DROP COLUMN IF EXISTS suppress_until")
    op.execute("ALTER TABLE insight DROP COLUMN IF EXISTS reason")
