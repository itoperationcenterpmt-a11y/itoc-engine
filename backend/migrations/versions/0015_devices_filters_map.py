"""Devices: koordinat lokasi (lat, lon), tabel pemetaan kode Zabbix ke lokasi, dan filter kategori/status di menu Devices.

Revision ID: 0015
Revises: 0014
"""
from alembic import op
from app import models

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None

# Koordinat perkiraan pelabuhan (derajat desimal); Admin dapat mengoreksinya di Master Data > Lokasi. Hanya mengisi yang masih kosong.
COORDS = {
    "Branch Belawan": (3.7833, 98.6833), "Branch Dumai": (1.6833, 101.4500), "Branch Malahayati": (5.5833, 95.4833),
    "Branch Lhokseumawe": (5.2167, 97.0500), "Branch Sibolga": (1.7425, 98.7792), "Branch Meulaboh": (4.1333, 96.1167),
    "Branch Kuala Langsa": (4.5200, 97.9700), "Branch Tanjung Balai Karimun": (1.0000, 103.4167), "Branch Tanjung Pinang": (0.9167, 104.4500),
    "Branch Janirah": (-7.2000, 112.7333), "Branch Tanjung Emas": (-6.9500, 110.4167), "Branch Gresik": (-7.1500, 112.6500),
    "Branch Tanjung Intan": (-7.7333, 109.0167), "Branch Tanjung Wangi": (-8.1500, 114.3667), "Branch Kalimas": (-7.2100, 112.7200),
    "Branch Benoa": (-8.7500, 115.2167), "Branch Trisakti": (-3.3333, 114.5667), "Branch Bumiharjo": (-2.7300, 111.7300),
    "Branch Bagendang": (-2.5500, 112.9500), "Branch Balikpapan": (-1.2667, 116.8167), "Branch Makassar": (-5.1167, 119.4000),
    "Branch Parepare": (-4.0167, 119.6167), "Branch Garongkong": (-4.4167, 119.6167), "Branch Lembar": (-8.7333, 116.0667),
    "Branch Badas": (-8.5000, 117.4167), "Branch Bima": (-8.4500, 118.7167), "Branch Tanjung Uban": (1.0667, 104.2167),
}


def upgrade():
    op.execute('ALTER TABLE site ADD COLUMN IF NOT EXISTS lat DOUBLE PRECISION')
    op.execute('ALTER TABLE site ADD COLUMN IF NOT EXISTS lon DOUBLE PRECISION')
    models.ZbxLocMap.__table__.create(bind=op.get_bind(), checkfirst=True)
    for name, (la, lo) in COORDS.items():
        op.execute(f"""UPDATE site SET lat = {la}, lon = {lo} WHERE name = '{name}' AND lat IS NULL AND lon IS NULL""")
    op.execute("""UPDATE "module" SET filters = filters || '{"k": 1, "t": 1}'::jsonb WHERE key = 'devices' AND NOT (filters ? 'k')""")


def downgrade():
    pass