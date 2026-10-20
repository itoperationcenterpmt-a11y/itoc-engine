"""Menu Devices: letakkan sebelum Personnel dan beri akses ke ITOC Shift dan Management (hanya bila belum diubah Admin).

Revision ID: 0014
Revises: 0013
"""
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""UPDATE "module" SET sort = 6 WHERE key = 'jadwal' AND sort = 5""")
    op.execute("""UPDATE "role" SET modules = array_append(modules, 'devices')
                  WHERE key IN ('itoc', 'manajemen') AND NOT ('devices' = ANY(modules)) AND NOT ('*' = ANY(modules))""")


def downgrade():
    pass