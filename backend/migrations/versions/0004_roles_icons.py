"""Role per fungsi (ITOC Shift, IT Care, Management, Admin, Super Admin) dengan hak unggah per sumber, ikon menu dari database,
label menu Handover/Data, nama dashboard dan footer sebagai parameter. Baris yang sudah diubah di Admin tidak ditimpa.

Revision ID: 0004
Revises: 0003
"""
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

ALL = "ARRAY['ringkasan','servicedesk','noc','soc','jadwal','serahterima','kelengkapan']::varchar[]"


def upgrade():
    op.execute("""ALTER TABLE "role" ADD COLUMN IF NOT EXISTS uploads varchar[] NOT NULL DEFAULT '{}'""")
    op.execute("""ALTER TABLE "module" ADD COLUMN IF NOT EXISTS icon varchar(30)""")
    # ikon dan label menu
    op.execute("""UPDATE "module" SET icon = CASE key WHEN 'ringkasan' THEN 'dashboard' WHEN 'servicedesk' THEN 'ticket' WHEN 'noc' THEN 'activity'
                  WHEN 'soc' THEN 'shield' WHEN 'jadwal' THEN 'users' WHEN 'serahterima' THEN 'handover' WHEN 'kelengkapan' THEN 'database'
                  WHEN 'admin' THEN 'sliders' END WHERE icon IS NULL""")
    op.execute("""UPDATE "module" SET label = 'Handover' WHERE key = 'serahterima' AND label = 'Serah Terima'""")
    op.execute("""UPDATE "module" SET label = 'Data' WHERE key = 'kelengkapan' AND label = 'Kelengkapan Data'""")
    # role baru
    op.execute(f"""INSERT INTO "role" (key, label, modules, can_write, is_admin, uploads, sort) VALUES
        ('itoc', 'ITOC Shift', {ALL}, true, false, ARRAY['soc','tickets','prtg']::varchar[], 3),
        ('itcare', 'IT Care', ARRAY['servicedesk','jadwal','kelengkapan']::varchar[], false, false, ARRAY['tickets']::varchar[], 4)
        ON CONFLICT (key) DO NOTHING""")
    op.execute("""UPDATE "role" SET uploads = ARRAY['*']::varchar[] WHERE key IN ('superadmin', 'admin') AND cardinality(uploads) = 0""")
    op.execute("""UPDATE "role" SET label = 'Management' WHERE key = 'manajemen' AND label = 'Manajemen'""")
    # Lead dan Analis lama memakai akses yang sama dengan ITOC Shift
    op.execute("""UPDATE app_user SET role_key = 'itoc' WHERE role_key IN ('lead', 'analis')""")
    op.execute("""DELETE FROM "role" WHERE key IN ('lead', 'analis') AND NOT EXISTS (SELECT 1 FROM app_user u WHERE u.role_key = "role".key)""")
    # parameter
    op.execute("""DELETE FROM app_parameter WHERE key = 'itcare'""")
    op.execute("""UPDATE app_parameter SET value = '["EOS", "IT Care"]'::jsonb WHERE key = 'sd.rank_units' AND value::text = '["EOS"]'""")
    op.execute("""UPDATE app_parameter SET value = to_jsonb('© {year} ITOC Team · IT Pelindo Multi Terminal'::text)
                  WHERE key = 'ui.footer' AND value::text LIKE '%Rumus mengikuti%'""")


def downgrade():
    pass
