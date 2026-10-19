"""Penyesuaian menu pada database yang sudah ada: menu Personel (tanpa filter), badge/notice 'impor' SOC dihapus, label role Analis.
Hanya mengubah baris yang masih bernilai bawaan lama, jadi perubahan yang sudah dibuat di Admin tidak tertimpa.

Revision ID: 0003
Revises: 0002
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""UPDATE "module" SET label = 'Personel', filters = '{"p": 0, "s": 0, "l": 0, "c": 0}'::jsonb, note = NULL,
                  why = 'Personel tidak bergantung filter; jadwal menampilkan bulan berjalan.' WHERE key = 'jadwal' AND label = 'Jadwal & Tim'""")
    op.execute("""UPDATE "module" SET badge = NULL, notice = NULL WHERE key = 'soc' AND (badge ->> 'text' = 'impor' OR notice IS NOT NULL)""")
    op.execute("""UPDATE "role" SET label = 'Analis' WHERE key = 'analis' AND label = 'ITOC Analyst'""")


def downgrade():
    pass