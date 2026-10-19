"""Izin per role sesuai fungsi: IT Care (kantor pusat) dan EOS (lokasi sendiri) hanya data lokasinya dan tanpa SOC; ITOC Shift hanya lihat;
Admin = koordinator (semua menu, Admin hanya baca); Management hanya lihat + Report; Super Admin semuanya. Menu baru Report.
Kolom role.scope dan role.admin_view ditambahkan. Mengatur ulang baris role bawaan (itoc, itcare, eos, manajemen, admin, superadmin).

Revision ID: 0005
Revises: 0004
"""
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

ROLES = {
    "superadmin": (["*"], True, True, "all", ["*"]),
    "admin": (["*"], False, True, "all", ["soc", "tickets", "prtg"]),
    "itoc": (["ringkasan", "servicedesk", "noc", "soc", "jadwal", "report"], False, False, "all", []),
    "itcare": (["ringkasan", "servicedesk", "noc", "jadwal", "report"], False, False, "ho", []),
    "eos": (["ringkasan", "servicedesk", "noc", "jadwal", "report"], False, False, "own", []),
    "manajemen": (["ringkasan", "servicedesk", "noc", "soc", "jadwal", "kelengkapan", "report"], False, False, "all", []),
}


def arr(xs):
    return "ARRAY[" + ",".join("'" + x + "'" for x in xs) + "]::varchar[]" if xs else "ARRAY[]::varchar[]"


def upgrade():
    op.execute("""ALTER TABLE "role" ADD COLUMN IF NOT EXISTS admin_view boolean NOT NULL DEFAULT false""")
    op.execute("""ALTER TABLE "role" ADD COLUMN IF NOT EXISTS scope varchar(10) NOT NULL DEFAULT 'all'""")
    for key, (mods, write, admin_view, scope, uploads) in ROLES.items():
        op.execute(f"""UPDATE "role" SET modules = {arr(mods)}, can_write = {str(write).lower()}, admin_view = {str(admin_view).lower()},
                       scope = '{scope}', uploads = {arr(uploads)} WHERE key = '{key}'""")
    op.execute("""UPDATE "role" SET is_admin = (key = 'superadmin') WHERE key IN ('superadmin', 'admin')""")
    op.execute("""INSERT INTO "module" (key, label, sort, enabled, icon, filters, note)
                  VALUES ('report', 'Report', 8, true, 'report', '{"p": 1, "s": 1, "l": 1, "c": 0}'::jsonb, 'Filter di atas menentukan isi laporan yang diunduh.')
                  ON CONFLICT (key) DO NOTHING""")
    op.execute("""UPDATE "module" SET sort = 9 WHERE key = 'admin' AND sort = 8""")


def downgrade():
    pass