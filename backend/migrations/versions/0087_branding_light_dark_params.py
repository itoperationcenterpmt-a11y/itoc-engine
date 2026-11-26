"""Add Light & Dark branding assets, colors, wordmarks, login background, and subtitle params.

Revision ID: 0087
Revises: 0086
Create Date: 2026-11-27
"""
import json
from alembic import op
import sqlalchemy as sa

revision = "0087"
down_revision = "0086"
branch_labels = None
depends_on = None

BRAND_PARAMS = [
    ("ui.wordmark_light_img", "tampilan", "Wordmark Light Mode (Data URL)", "", "text", {}, "Custom wordmark image for Light mode (PNG/SVG/WebP). Empty = default TERA wordmark.", 11),
    ("ui.wordmark_dark_img", "tampilan", "Wordmark Dark/Sidebar Mode (Data URL)", "", "text", {}, "Custom wordmark image for Dark mode & Sidebar (PNG/SVG/WebP). Empty = default TERA wordmark.", 12),
    ("ui.login_bg_img", "tampilan", "Login Background Image (Data URL)", "", "text", {}, "Custom background image on the Login page. Empty = default Belawan terminal photo.", 13),
    ("ui.accent_light", "tampilan", "Accent Color (Light Mode)", "#1c5cab", "text", {}, "Primary accent hex color in Light Mode.", 14),
    ("ui.accent_dark", "tampilan", "Accent Color (Dark Mode)", "#6da7ec", "text", {}, "Primary accent hex color in Dark Mode.", 15),
    ("ui.side_bg", "tampilan", "Sidebar Background Color", "#0f1b2d", "text", {}, "Sidebar background hex color.", 16),
    ("ui.side_wm_px", "tampilan", "Sidebar Wordmark Height (px)", 19, "number", {"min": 12, "max": 34, "step": 1}, "Height of the wordmark logo in the sidebar (pixels).", 17),
    ("ui.brand_sub", "tampilan", "Brand Subtitle", "Dashboard", "text", {}, "Subtitle shown under the brand name in the sidebar.", 18),
    ("ui.brand_by", "tampilan", "Brand Byline", "by IT Operation Center", "text", {}, "Small attribution line shown under the subtitle in the sidebar.", 19),
]


def upgrade():
    conn = op.get_bind()
    for key, grp, label, val, editor, ui, desc, sort in BRAND_PARAMS:
        conn.execute(
            sa.text(
                """INSERT INTO app_parameter (key, "group", label, value, editor, ui, description, sort, updated_by)
                   VALUES (:k, :g, :l, CAST(:v AS jsonb), :e, CAST(:u AS jsonb), :d, :s, 'system')
                   ON CONFLICT (key) DO NOTHING"""
            ),
            {"k": key, "g": grp, "l": label, "v": json.dumps(val), "e": editor, "u": json.dumps(ui), "d": desc, "s": sort},
        )


def downgrade():
    conn = op.get_bind()
    for key, *_ in BRAND_PARAMS:
        conn.execute(sa.text("DELETE FROM app_parameter WHERE key = :k"), {"k": key})
