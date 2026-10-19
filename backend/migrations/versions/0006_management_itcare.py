"""Management tanpa menu Data; empat personel dummy IT Care bila unit IT Care belum punya anggota (nama bertanda Dummy, ganti di Admin → Master data → Personel).

Revision ID: 0006
Revises: 0005
"""
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""UPDATE "role" SET modules = array_remove(modules, 'kelengkapan') WHERE key = 'manajemen'""")
    unit = """COALESCE((SELECT g ->> 'unit' FROM app_parameter p, jsonb_array_elements(p.value -> 'groups') g
                         WHERE p.key = 'personel' AND g ->> 'kind' = 'office' LIMIT 1), 'IT Care')"""
    op.execute(f"""INSERT INTO person (name, unit, job, phone, is_coordinator, is_shared, exclude_rank, active)
                   SELECT v.name, {unit}, v.job, v.phone, v.coord, false, false, true
                   FROM (VALUES ('Dian Pratama (Dummy)', 'IT Care Coordinator', '0813-0000-010', true),
                                ('Rizky Nugroho (Dummy)', 'IT Care Support', '0813-0000-020', false),
                                ('Sinta Lestari (Dummy)', 'IT Care Support', '0813-0000-030', false),
                                ('Bagas Santoso (Dummy)', 'IT Care Support', '0813-0000-040', false)) AS v(name, job, phone, coord)
                   WHERE NOT EXISTS (SELECT 1 FROM person WHERE unit = {unit})""")


def downgrade():
    pass