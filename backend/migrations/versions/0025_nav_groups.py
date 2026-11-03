"""Menu induk: Network (Summary + PRTG + WiFi) dan Cyber Security (Summary + NDR Palo Alto + XDR Trend Micro).

Revision ID: 0025
Revises: 0024
"""
from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""INSERT INTO module (key, label, sort, enabled, filters, note, why, parent, icon) VALUES
        ('network', 'Network', 3, true, '{"p": 1, "s": 1, "l": 1, "c": 0}', 'Ringkasan gabungan PRTG (link) dan Ruckus (WiFi). Filter periode, shift, dan lokasi berlaku untuk data PRTG; data WiFi adalah kondisi terkini.', NULL, NULL, 'activity'),
        ('cyber', 'Cyber Security', 4, true, '{"p": 1, "s": 0, "l": 0, "c": 0}', 'Ringkasan gabungan NDR (Palo Alto Panorama) dan XDR (Trend Micro). Filter periode berlaku untuk keduanya.', NULL, NULL, 'shield')
        ON CONFLICT (key) DO NOTHING""")
    op.execute("""UPDATE module SET parent = 'network', label = 'PRTG', sort = 31 WHERE key = 'noc'""")
    op.execute("""UPDATE module SET parent = 'network', label = 'WiFi', sort = 32 WHERE key = 'wifi'""")
    op.execute("""UPDATE module SET parent = 'cyber', label = 'NDR', sort = 41 WHERE key = 'soc'""")
    op.execute("""UPDATE module SET parent = 'cyber', label = 'XDR', sort = 42 WHERE key = 'xdr'""")
    op.execute("""UPDATE role SET modules = array_append(modules, 'network') WHERE 'noc' = ANY(modules) AND NOT ('network' = ANY(modules))""")
    op.execute("""UPDATE role SET modules = array_append(modules, 'cyber') WHERE ('soc' = ANY(modules) OR 'xdr' = ANY(modules)) AND NOT ('cyber' = ANY(modules))""")


def downgrade():
    op.execute("""UPDATE module SET parent = NULL, label = 'Networking', sort = 3 WHERE key = 'noc'""")
    op.execute("""UPDATE module SET parent = NULL, label = 'WiFi Users', sort = 5 WHERE key = 'wifi'""")
    op.execute("""UPDATE module SET parent = NULL, label = 'Cyber Security', sort = 4 WHERE key = 'soc'""")
    op.execute("""UPDATE module SET parent = NULL, label = 'XDR', sort = 5 WHERE key = 'xdr'""")
    op.execute("DELETE FROM module WHERE key IN ('network', 'cyber')")