"""Penyeragaman teks: label periode, kalimat halaman login, nama menu Personnel, dan petunjuk jalur menu Admin yang baru.

Revision ID: 0031
Revises: 0030
"""
import json
from alembic import op
from sqlalchemy import text

revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None

PATHS = [
    ("Admin → Master Data → Zabbix: kode ke lokasi", "Admin → Sumber Data → Pemetaan → Kode Lokasi Zabbix"), ("Admin → Master Data → Lokasi", "Admin → Sumber Data → Pemetaan → Lokasi"),
    ("Admin → Master data → ISP", "Admin → Sumber Data → Pemetaan → ISP"), ("Admin → Integrations →", "Admin → Sumber Data → Integrasi →"), ("Admin → Sensor & kapasitas", "Admin → Sumber Data → Pemetaan → Sensor dan Kapasitas"),
    ("Admin → Target SLA", "Admin → Operasional → Target dan Parameter"), ("Admin → ISP", "Admin → Sumber Data → Pemetaan → ISP"), ("Admin → Parameter", "Admin → Operasional → Target dan Parameter"),
]
PRESETS_OLD = [["hari", "Today"], ["kemarin", "Yesterday"], ["7", "7 days"], ["30", "30 days"], ["bulan", "This month"], ["lalu", "Last month"]]
PRESETS_NEW = [["hari", "Hari ini"], ["kemarin", "Kemarin"], ["7", "7 hari"], ["30", "30 hari"], ["bulan", "Bulan ini"], ["lalu", "Bulan lalu"]]
TAG_OLD = "Pantau lebih dini, putuskan lebih cepat. Layanan TI, jaringan, dan keamanan siber seluruh terminal dalam satu layar."
TAG_NEW = "Dashboard operasional IT Operation Center untuk memantau tiket, jaringan, keamanan siber, dan CCTV seluruh terminal."


def upgrade():
    c = op.get_bind()
    c.execute(text("UPDATE app_parameter SET value = CAST(:n AS jsonb) WHERE key = 'ui.presets' AND value = CAST(:o AS jsonb)"), {"n": json.dumps(PRESETS_NEW), "o": json.dumps(PRESETS_OLD)})
    c.execute(text("UPDATE app_parameter SET value = CAST(:n AS jsonb) WHERE key = 'ui.login_tagline' AND value = CAST(:o AS jsonb)"), {"n": json.dumps(TAG_NEW), "o": json.dumps(TAG_OLD)})
    c.execute(text("UPDATE module SET label = 'Personnel' WHERE key = 'jadwal' AND label = 'Personel'"))
    for old, new in PATHS:
        for tbl, col in (("formula", "text"), ("app_parameter", "label"), ("app_parameter", "description"), ("module", "note"), ("module", "why"), ("data_source", "tip")):
            c.execute(text(f"UPDATE {tbl} SET {col} = REPLACE({col}, :o, :n) WHERE {col} LIKE :l"), {"o": old, "n": new, "l": "%" + old + "%"})


def downgrade():
    pass
