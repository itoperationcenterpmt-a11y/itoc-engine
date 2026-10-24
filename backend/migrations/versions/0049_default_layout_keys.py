"""Default profile layouts saved before the English rename still use Indonesian panel keys: map them to the current keys, and put Insights first on the pages that have it.

Revision ID: 0049
Revises: 0048
"""
from alembic import op
from sqlalchemy import text

revision = "0049"
down_revision = "0048"
branch_labels = None
depends_on = None

RENAME = {
    "xdr": {"alert-per-hari": "alerts-per-day", "severity-dan-status": "severity-and-status", "host-terdampak": "hosts-affected", "akun-terdampak": "accounts-affected",
            "model-deteksi-teratas": "top-detection-models", "insiden": "incidents", "umur-backlog": "backlog-age", "cakupan-dampak": "impact-scope"},
    "wifi": {"client-trend-24-jam": "client-trend-24h", "band-dan-tipe-perangkat": "band-and-device-type", "client-per-ssid": "clients-per-ssid", "client-per-ap": "clients-per-ap",
             "client-per-zone": "clients-per-zone", "client-per-lokasi": "clients-per-location", "access-point-tidak-online": "access-points-not-online"},
}


def upgrade():
    c = op.get_bind()
    for page, m in RENAME.items():
        for old, new in m.items():
            c.execute(text("UPDATE layout l SET key = :n WHERE page = :pg AND key = :o AND NOT EXISTS (SELECT 1 FROM layout x WHERE x.profile = l.profile AND x.page = l.page AND x.role = l.role AND x.key = :n)"), {"n": new, "o": old, "pg": page})
    c.execute(text("UPDATE layout SET enabled = true WHERE profile = 'default' AND page = 'xdr' AND key = 'ticket-coverage'"))
    for page in ("xdr", "wifi", "soc", "cctv"):
        for prof, role in c.execute(text("SELECT DISTINCT profile, role FROM layout WHERE page = :pg"), {"pg": page}).all():
            c.execute(text("INSERT INTO layout (profile, page, role, key, title, size, enabled, sort) VALUES (:p, :pg, :r, 'insights', '', 'c12', :e, 0) "
                           "ON CONFLICT (profile, page, role, key) DO UPDATE SET sort = 0, enabled = true"), {"p": prof, "pg": page, "r": role, "e": True})


def downgrade():
    pass
