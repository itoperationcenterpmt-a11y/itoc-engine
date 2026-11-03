"""Devices: kamus kode perangkat, penguraian nama host (zona, sub zona, kode perangkat), dan pemetaan kode lokasi dari daftar Pelindo.

Revision ID: 0018
Revises: 0017
"""
from alembic import op
from app import models

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None

# kode lokasi pada nama host group/host -> (lokasi di master, nama lokasi); lokasi None = belum ada di master Lokasi
LOC = [
    ('HO', 'Head Office', 'Head Office'),
    ('BLW', 'Branch Belawan', 'Belawan'),
    ('PBB', 'Branch Badas', 'Badas'),
    ('BGD', 'Branch Bagendang', 'Bagendang'),
    ('BPN', 'Branch Balikpapan', 'Balikpapan'),
    ('BMU', 'Branch Bima', 'Bima'),
    ('BMH', 'Branch Bumiharjo', 'Bumiharjo'),
    ('DUM', 'Branch Dumai', 'Dumai'),
    ('GRK', 'Branch Garongkong', 'Garongkong'),
    ('GLM', None, 'Gilimas'),
    ('GRE', 'Branch Gresik', 'Gresik'),
    ('JNR', 'Branch Janirah', 'Jamrud Nilam Mirah'),
    ('KLS', 'Branch Kalimas', 'Kalimas'),
    ('KUA', 'Branch Kuala Langsa', 'Kuala Langsa'),
    ('LBR', 'Branch Lembar', 'Lembar'),
    ('LSW', 'Branch Lhokseumawe', 'Lhokseumawe'),
    ('MAK', 'Branch Makassar', 'Makassar'),
    ('MLH', 'Branch Malahayati', 'Malahayati'),
    ('PAP', 'Branch Parepare', 'Pare pare'),
    ('JKT', 'Kantor Perwakilan', 'Pelindo Tower'),
    ('SLG', 'Branch Sibolga', 'Sibolga'),
    ('SRG', 'Branch Tanjung Emas', 'Tanjung Emas'),
    ('CXP', 'Branch Tanjung Intan', 'Tanjung Intan'),
    ('TJW', 'Branch Tanjung Wangi', 'Tanjung Wangi'),
    ('BDJ', 'Branch Trisakti', 'Trisakti (BJM)'),
    ('BOA', 'Branch Benoa', 'Benoa'),
    ('MKP', 'Branch Mekarputih', 'Mekar Putih'),
    ('MEQ', 'Branch Meulaboh', 'Meulaboh'),
    ('SBY', 'Kantor Perwakilan', 'Pelindo Place'),
    ('SPA', None, 'Selat Panjang'),
    ('TJB', 'Branch Tanjung Balai Karimun', 'Tanjung Balai Karimun'),
    ('BTG', 'Branch Tanjung Emas', 'Tanjung Emas (Batang)'),
    ('BAM', 'Branch Tanjung Pinang', 'Tanjung Pinang (Batu Anam)'),
    ('KID', 'Branch Tanjung Pinang', 'Tanjung Pinang (Sei Kolak Kijang)'),
    ('TNJ', 'Branch Tanjung Pinang', 'Tanjung Pinang (Sri Bintan Pura)'),
]
# kode perangkat pada nama host -> label
DEV = [
    ('SVR', 'Server'),
    ('NGFW', 'Next Gen Firewall'),
    ('BW', 'Bandwidth Management'),
    ('CSW', 'Switch Core'),
    ('ASW', 'Switch Access'),
    ('MSW', 'Switch Managed'),
    ('USW', 'Switch Unmanaged'),
    ('AP', 'Access Point'),
    ('CFIX', 'CCTV Fixed'),
    ('CPTZ', 'CCTV PTZ'),
    ('IOC', 'I/O Controller'),
    ('CVR', 'Converter'),
    ('DPC', 'Desktop PC'),
    ('DPM', 'Display Monitor'),
    ('IPC', 'Industrial PC'),
    ('IOT', 'Internet of Things'),
    ('KKG', 'Kiosk Gate'),
    ('NB', 'Laptop'),
    ('MPC', 'Mini PC'),
    ('MDM', 'Modem'),
    ('MM', 'Multimedia Devices'),
    ('NFC', 'NFC Reader'),
    ('OTB', 'Optical Terminal Box'),
    ('BOX', 'Panel Box'),
    ('PE', 'Photoelectric'),
    ('UPS', 'UPS (Uninterruptible Power Supply)'),
    ('PRT', 'Printer'),
    ('PA', 'Public Announcer Speaker'),
    ('POC', 'Push to Talk over Cellular'),
    ('SCN', 'Scanner'),
    ('SMP', 'Smartphone'),
    ('TB', 'Tablet Handheld'),
    ('TV', 'Televisi'),
    ('TLP', 'Telepon'),
    ('VOIP', 'Voice over IP'),
    ('DAS', 'Face Recording (Absensi)'),
]


def esc(s):
    return s.replace("'", "''")


def upgrade():
    for col, size in (("zone", 40), ("subzone", 80), ("dev_code", 20)):
        op.execute(f"ALTER TABLE zbx_host ADD COLUMN IF NOT EXISTS {col} VARCHAR({size}) NOT NULL DEFAULT ''")
    models.DevCode.__table__.create(bind=op.get_bind(), checkfirst=True)
    for code, label in DEV:
        op.execute(f"INSERT INTO dev_code (code, label) VALUES ('{code}', '{esc(label)}') ON CONFLICT (code) DO NOTHING")
    for code, site, note in LOC:
        s = "NULL" if site is None else "'" + esc(site) + "'"
        op.execute(f"INSERT INTO zbx_loc_map (code, site, note) VALUES ('{code}', {s}, '{esc(note)}') "
                   f"ON CONFLICT (code) DO UPDATE SET site = COALESCE(zbx_loc_map.site, EXCLUDED.site), note = COALESCE(zbx_loc_map.note, EXCLUDED.note)")
    op.execute("""UPDATE "module" SET filters = filters || '{"y": 1}'::jsonb WHERE key = 'devices' AND NOT (filters ? 'y')""")


def downgrade():
    pass