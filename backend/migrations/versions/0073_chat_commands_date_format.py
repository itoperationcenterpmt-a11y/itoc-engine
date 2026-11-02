"""Chat commands: the date in the help footer is YYYYMMDD (the short yymmdd form still works). Only the untouched default text is replaced.

Revision ID: 0073
Revises: 0072
"""
from alembic import op
from sqlalchemy import text

revision = "0073"
down_revision = "0072"
branch_labels = None
depends_on = None


def upgrade():
    op.get_bind().execute(text("""UPDATE app_parameter SET value = REPLACE(value::text, 'Tambahkan tanggal yymmdd untuk hari lain, contoh /fullday-261101 atau /eos-parepare-261101.',
                                  'Tambahkan tanggal YYYYMMDD untuk hari lain, contoh /fullday-20261101 atau /eos-parepare-20261101.')::jsonb WHERE key = 'chat.commands'"""))


def downgrade():
    pass
