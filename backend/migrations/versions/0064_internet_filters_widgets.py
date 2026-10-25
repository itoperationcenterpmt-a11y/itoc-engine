"""Internet Usage gets the same filters as the other Network and Cyber Security pages (period, location, compare), and the built-in Management and NOC wall Overviews get its widgets.

Revision ID: 0064
Revises: 0063
"""
from alembic import op
from sqlalchemy import text

revision = "0064"
down_revision = "0063"
branch_labels = None
depends_on = None

ADD = {"management": [("w-viz-donut-acat", "c4"), ("w-viz-internet-sites", "c4"), ("w-viz-internet-apps", "c4")], "noc": [("w-viz-internet-sites", "c6"), ("w-viz-donut-acat", "c6")]}


def upgrade():
    c = op.get_bind()
    c.execute(text("""UPDATE module SET filters = '{"p": 1, "s": 0, "l": 1, "c": 1}'::jsonb WHERE key = 'internet'"""))
    for prof, items in ADD.items():
        top = c.execute(text("SELECT COALESCE(MAX(sort), 0) FROM layout WHERE profile = :p AND page = 'ringkasan' AND role = ''"), {"p": prof}).scalar()
        for i, (key, size) in enumerate(items, 1):
            c.execute(text("INSERT INTO layout (profile, page, role, key, title, size, enabled, sort) VALUES (:p, 'ringkasan', '', :k, '', :s, true, :o) ON CONFLICT DO NOTHING"), {"p": prof, "k": key, "s": size, "o": top + i})


def downgrade():
    pass
