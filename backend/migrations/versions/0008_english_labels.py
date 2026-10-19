"""Label menu dan preset periode berbahasa Inggris (hanya baris yang masih bernilai bawaan lama).

Revision ID: 0008
Revises: 0007
"""
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""UPDATE "module" SET label = 'Overview' WHERE key = 'ringkasan' AND label = 'Ringkasan'""")
    op.execute("""UPDATE "module" SET label = 'Personnel' WHERE key = 'jadwal' AND label = 'Personel'""")
    op.execute("""UPDATE app_parameter SET value = '[["hari", "Today"], ["kemarin", "Yesterday"], ["7", "7 days"], ["30", "30 days"], ["bulan", "This month"], ["lalu", "Last month"]]'::jsonb
                  WHERE key = 'ui.presets' AND value::text LIKE '%Hari ini%'""")


def downgrade():
    pass