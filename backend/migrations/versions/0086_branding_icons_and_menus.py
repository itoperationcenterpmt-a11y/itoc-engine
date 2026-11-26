"""Add custom icon image params (sidebar, login, favicon) and clean up remaining vendor menu labels.

Revision ID: 0086
Revises: 0085
Create Date: 2026-11-27
"""
import json
from alembic import op
import sqlalchemy as sa

revision = "0086"
down_revision = "0085"
branch_labels = None
depends_on = None

ICON_PARAMS = [
    ("ui.side_icon_img", "tampilan", "Sidebar Custom Icon (Data URL)", "", "text", {}, "Custom uploaded sidebar icon image (PNG/SVG/WebP data URL). Empty = built-in TERA icon.", 8),
    ("ui.login_icon_img", "tampilan", "Login Custom Logo (Data URL)", "", "text", {}, "Custom uploaded login logo image (PNG/SVG/WebP data URL). Empty = built-in TERA logo.", 9),
    ("ui.favicon_img", "tampilan", "Browser Favicon (Data URL)", "", "text", {}, "Custom uploaded browser tab favicon (PNG/SVG/ICO data URL). Empty = built-in TERA favicon.", 10),
]


def upgrade():
    conn = op.get_bind()
    for key, grp, label, val, editor, ui, desc, sort in ICON_PARAMS:
        conn.execute(
            sa.text(
                """INSERT INTO app_parameter (key, "group", label, value, editor, ui, description, sort, updated_by)
                   VALUES (:k, :g, :l, CAST(:v AS jsonb), :e, CAST(:u AS jsonb), :d, :s, 'system')
                   ON CONFLICT (key) DO NOTHING"""
            ),
            {"k": key, "g": grp, "l": label, "v": json.dumps(val), "e": editor, "u": json.dumps(ui), "d": desc, "s": sort},
        )
    # De-brand remaining sub-menu labels
    conn.execute(sa.text("UPDATE module SET label = 'Surveillance' WHERE key = 'cctv' AND label = 'Milestone'"))
    conn.execute(sa.text("UPDATE module SET label = 'Web Availability' WHERE key = 'kuma' AND label = 'Link / Web Availability'"))


def downgrade():
    conn = op.get_bind()
    for key, *_ in ICON_PARAMS:
        conn.execute(sa.text("DELETE FROM app_parameter WHERE key = :k"), {"k": key})
