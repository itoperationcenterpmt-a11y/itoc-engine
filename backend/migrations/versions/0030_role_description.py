"""Role: kolom keterangan dan nama role yang konsisten.

Revision ID: 0030
Revises: 0029
"""
from alembic import op

revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None

DESC = {
    "superadmin": ("Super Admin", "Pengelola sistem. Akses ke semua menu, pengaturan, integrasi, dan pengguna."),
    "admin": ("ITOC Koordinator", "Koordinator shift ITOC. Melihat semua menu termasuk Admin (hanya baca) dan boleh mengunggah data SOC, tiket, dan PRTG."),
    "itoc": ("ITOC Shift", "Operator ITOC per shift. Memantau semua halaman monitoring dan mengisi serah terima."),
    "itcare": ("IT Care", "Tim IT Care kantor pusat. Melihat tiket, jaringan, dan jadwal untuk kantor pusat."),
    "eos": ("EOS Cabang", "Tim EOS di cabang. Hanya melihat data lokasi cabangnya sendiri."),
    "wifiview": ("WiFi Viewer", "Hanya halaman WiFi. Untuk tim lain yang perlu memantau pengguna WiFi."),
    "manajemen": ("Manajemen", "Manajemen. Melihat ringkasan, monitoring, dan laporan tanpa mengubah data."),
}
OLD = {"admin": "ITOC Shift Coordinator", "eos": "EOS Branch", "manajemen": "Management"}      # nama lama yang diganti; nama yang sudah diubah admin tidak disentuh


def upgrade():
    op.execute("ALTER TABLE role ADD COLUMN IF NOT EXISTS description varchar(300)")
    for k, (label, desc) in DESC.items():
        op.execute(f"UPDATE role SET description = '{desc}' WHERE key = '{k}' AND description IS NULL")
        if k in OLD:
            op.execute(f"UPDATE role SET label = '{label}' WHERE key = '{k}' AND label = '{OLD[k]}'")


def downgrade():
    op.execute("ALTER TABLE role DROP COLUMN IF EXISTS description")
