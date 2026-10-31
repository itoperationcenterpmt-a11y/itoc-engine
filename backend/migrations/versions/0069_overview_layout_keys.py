"""Overview: the old "Today's Status" block is now two blocks (Right Now, This Period); saved layouts keep their position and size for both.

Revision ID: 0069
Revises: 0068
"""
from alembic import op
from sqlalchemy import text

revision = "0069"
down_revision = "0068"
branch_labels = None
depends_on = None


def upgrade():
    c = op.get_bind()
    c.execute(text("""INSERT INTO layout (page, role, key, title, size, enabled, sort, profile)
                      SELECT page, role, 'right-now', '', 'c12', enabled, sort, profile FROM layout WHERE page = 'ringkasan' AND key = 'today-s-status'
                      ON CONFLICT DO NOTHING"""))
    c.execute(text("UPDATE layout SET key = 'this-period', title = '' WHERE page = 'ringkasan' AND key = 'today-s-status'"))


def downgrade():
    pass
