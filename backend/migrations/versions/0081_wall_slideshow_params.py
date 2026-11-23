"""Add Wall Mode slideshow & auto-refresh settings to app_parameter (editable in Admin > Operations > Targets & Parameters > Appearance).

Revision ID: 0081
Revises: 0080
"""
import json
from alembic import op
from sqlalchemy import text

revision = "0081"
down_revision = "0080"
branch_labels = None
depends_on = None

PARAMS = [
    (
        "ui.wall_slide_sec",
        15,
        "Wall Mode: slide duration (seconds)",
        "tampilan",
        "number",
        {"min": 5, "max": 300, "step": 5, "unit": "s"},
        "How many seconds each slide stays on screen in TV / Wall Mode before advancing to the next slide or menu.",
        81,
    ),
    (
        "ui.wall_refresh_sec",
        60,
        "Wall Mode: data refresh interval (seconds)",
        "tampilan",
        "number",
        {"min": 15, "max": 600, "step": 15, "unit": "s"},
        "How often TV / Wall Mode fetches fresh data from the server in the background.",
        82,
    ),
    (
        "ui.wall_rotate_tabs",
        ["ringkasan", "network", "noc", "servicedesk", "cyber", "devices"],
        "Wall Mode: menus to rotate in slideshow",
        "tampilan",
        "list",
        {},
        "Menus rotated automatically in TV / Wall Mode after a page finishes its slides. Leave empty to loop only the current menu.",
        83,
    ),
]


def upgrade():
    c = op.get_bind()
    for key, val, label, grp, ed, ui, desc, sort in PARAMS:
        c.execute(
            text(
                "INSERT INTO app_parameter (key, value, label, \"group\", editor, ui, description, sort) "
                "VALUES (:k, CAST(:v AS jsonb), :l, :g, :e, CAST(:u AS jsonb), :d, :s) "
                "ON CONFLICT (key) DO NOTHING"
            ),
            {"k": key, "v": json.dumps(val), "l": label, "g": grp, "e": ed, "u": json.dumps(ui), "d": desc, "s": sort},
        )


def downgrade():
    c = op.get_bind()
    c.execute(text("DELETE FROM app_parameter WHERE key IN ('ui.wall_slide_sec', 'ui.wall_refresh_sec', 'ui.wall_rotate_tabs')"))
