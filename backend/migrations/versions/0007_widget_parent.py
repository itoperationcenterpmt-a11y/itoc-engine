"""Tabel widget (grafik laporan yang bisa diatur di Admin) dan menu induk: Handover menjadi sub-menu Report.

Revision ID: 0007
Revises: 0006
"""
from alembic import op
from app import models

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    models.Widget.__table__.create(bind=op.get_bind(), checkfirst=True)
    op.execute("""ALTER TABLE "module" ADD COLUMN IF NOT EXISTS parent varchar(40)""")
    op.execute("""UPDATE "module" SET parent = 'report' WHERE key = 'serahterima' AND parent IS NULL""")


def downgrade():
    pass