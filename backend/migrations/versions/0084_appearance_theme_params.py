"""Add Appearance visual theme parameters (accent color, UI density, card radius, default theme) to app_parameter.

Revision ID: 0084
Revises: 0083
"""
import json
from alembic import op
from sqlalchemy import text

revision = "0084"
down_revision = "0083"
branch_labels = None
depends_on = None

PARAMS = [
    ("ui.accent_color", "#1c5cab", "Primary accent color (hex)", "tampilan", "text", {}, "Primary brand accent color applied across all menus.", 210),
    ("ui.density", "compact", "UI density across all menus", "tampilan", "text", {}, "compact, comfortable, or spacious.", 211),
    ("ui.card_radius", 14, "Card corner radius (px)", "tampilan", "number", {"min": 6, "max": 22, "step": 2, "unit": "px"}, "Panel and card corner radius in pixels.", 212),
    ("ui.default_theme", "auto", "Default theme for new sessions", "tampilan", "text", {}, "auto, light, or dark.", 213),
]


def upgrade() -> None:
    bind = op.get_bind()
    for key, val, label, grp, ed, ui, desc, sort in PARAMS:
        bind.execute(
            text(
                'INSERT INTO app_parameter ("key", "value", label, "group", editor, ui, description, sort) '
                "VALUES (:k, CAST(:v AS jsonb), :l, :g, :e, CAST(:u AS jsonb), :d, :s) ON CONFLICT (\"key\") DO NOTHING"
            ),
            {"k": key, "v": json.dumps(val), "l": label, "g": grp, "e": ed, "u": json.dumps(ui), "d": desc, "s": sort},
        )


def downgrade() -> None:
    bind = op.get_bind()
    for key, *_ in PARAMS:
        bind.execute(text('DELETE FROM app_parameter WHERE "key" = :k'), {"k": key})
