"""Fix overview profile widget keys, enrich all 5 profiles, and add icon/scale appearance params.

Revision ID: 0085_presets_and_appearance_v2
Revises: 0084_appearance_theme_params
Create Date: 2026-11-27
"""
import json
from alembic import op
import sqlalchemy as sa

revision = "0085"
down_revision = "0084"
branch_labels = None
depends_on = None

NEW_PARAMS = [
    ("ui.scale", "tampilan", "Global UI Scale", 0.90, "number", {"min": 0.75, "max": 1.10, "step": 0.05}, "Global zoom/scale multiplier for dashboard typography and spacing (0.90 = crisp 90% view at 100% browser zoom).", 5),
    ("ui.side_icon_px", "tampilan", "Sidebar Icon Size (px)", 44, "number", {"min": 28, "max": 60, "step": 2}, "Size of the TERA brand icon in the sidebar (pixels).", 6),
    ("ui.login_icon_px", "tampilan", "Login Logo Size (px)", 56, "number", {"min": 36, "max": 88, "step": 4}, "Size of the TERA brand icon on the login page (pixels).", 7),
]

# Every key below is verified against page-ringkasan.js, widgets.js, and viz.js
ALL_BUILTIN_RINGKASAN = [
    "needs-attention",
    "on-duty",
    "right-now",
    "insights",
    "this-period",
    "tickets-in-and-closed-per-day",
    "top-5-links-by-downtime",
    "isp-status-by-provider",
    "isp-links-down-now",
    "link-downtime-per-day",
    "access-points-not-online",
    "client-trend-24h",
    "ndr-critical-and-high-per-day",
    "ndr-severity",
    "alerts-per-day",
    "severity-and-status",
    "open-handovers",
    "contacts",
    "devices-map-network-sdwan",
]

PRESETS = {
    "default": [
        ("w-viz-gauge-sla", "c3"),
        ("w-viz-gauge-link", "c3"),
        ("w-viz-gauge-devices", "c3"),
        ("w-viz-gauge-ms-servers", "c3"),
        ("needs-attention", "c4"),
        ("insights", "c4"),
        ("on-duty", "c4"),
        ("right-now", "c12"),
        ("this-period", "c12"),
        ("tickets-in-and-closed-per-day", "c8"),
        ("top-5-links-by-downtime", "c4"),
        ("isp-links-down-now", "c6"),
        ("isp-status-by-provider", "c6"),
        ("devices-map-network-sdwan", "c12"),
        ("open-handovers", "c6"),
        ("contacts", "c6"),
    ],
    "noc": [
        ("w-viz-gauge-link", "c3"),
        ("w-viz-gauge-zbxisp", "c3"),
        ("w-viz-gauge-devices", "c3"),
        ("w-viz-gauge-ap", "c3"),
        ("isp-status-by-provider", "c6"),
        ("isp-links-down-now", "c6"),
        ("w-viz-zbxisp-matrix", "c12"),
        ("link-downtime-per-day", "c8"),
        ("top-5-links-by-downtime", "c4"),
        ("client-trend-24h", "c8"),
        ("access-points-not-online", "c4"),
        ("w-viz-wall", "c8"),
        ("on-duty", "c4"),
        ("devices-map-network-sdwan", "c12"),
        ("needs-attention", "c12"),
    ],
    "security": [
        ("w-viz-spark-ndr", "c3"),
        ("w-viz-spark-xdr", "c3"),
        ("w-viz-donut-ndr-action", "c3"),
        ("w-viz-donut-xdr", "c3"),
        ("ndr-critical-and-high-per-day", "c8"),
        ("ndr-severity", "c4"),
        ("alerts-per-day", "c8"),
        ("severity-and-status", "c4"),
        ("w-xdr-models", "c6"),
        ("w-soc-action", "c6"),
        ("needs-attention", "c8"),
        ("on-duty", "c4"),
        ("insights", "c12"),
    ],
    "management": [
        ("w-viz-gauge-sla", "c3"),
        ("w-viz-gauge-link", "c3"),
        ("w-viz-gauge-devices", "c3"),
        ("w-viz-gauge-ms-servers", "c3"),
        ("this-period", "c12"),
        ("right-now", "c12"),
        ("tickets-in-and-closed-per-day", "c8"),
        ("w-viz-donut-tickets", "c4"),
        ("w-tk-groups", "c12"),
        ("w-viz-wall", "c8"),
        ("on-duty", "c4"),
        ("isp-status-by-provider", "c6"),
        ("top-5-links-by-downtime", "c6"),
        ("needs-attention", "c6"),
        ("insights", "c6"),
        ("devices-map-network-sdwan", "c12"),
    ],
    "branch": [
        ("w-viz-gauge-link", "c3"),
        ("w-viz-gauge-zbxisp", "c3"),
        ("w-viz-gauge-devices", "c3"),
        ("w-viz-gauge-sla", "c3"),
        ("right-now", "c12"),
        ("needs-attention", "c8"),
        ("on-duty", "c4"),
        ("w-tk-open", "c6"),
        ("w-viz-top-devices", "c6"),
        ("w-viz-top-links", "c6"),
        ("w-wifi-apdown", "c6"),
        ("w-dev-category", "c6"),
        ("open-handovers", "c6"),
        ("devices-map-network-sdwan", "c12"),
    ],
}


def upgrade():
    conn = op.get_bind()
    for key, grp, label, val, editor, ui, desc, sort in NEW_PARAMS:
        conn.execute(
            sa.text(
                """INSERT INTO app_parameter (key, "group", label, value, editor, ui, description, sort, updated_by)
                   VALUES (:k, :g, :l, CAST(:v AS jsonb), :e, CAST(:u AS jsonb), :d, :s, 'system')
                   ON CONFLICT (key) DO NOTHING"""
            ),
            {"k": key, "g": grp, "l": label, "v": json.dumps(val), "e": editor, "u": json.dumps(ui), "d": desc, "s": sort},
        )

    for prof, blocks in PRESETS.items():
        # Only update profiles that exist
        exists = conn.execute(sa.text("SELECT 1 FROM layout_profile WHERE key = :p"), {"p": prof}).first()
        if not exists:
            continue
        conn.execute(sa.text("DELETE FROM layout WHERE profile = :p AND page = 'ringkasan' AND role = ''"), {"p": prof})
        shown = set()
        order = 1
        for k, sz in blocks:
            shown.add(k)
            conn.execute(
                sa.text(
                    """INSERT INTO layout (profile, page, role, key, title, size, enabled, sort)
                       VALUES (:p, 'ringkasan', '', :k, '', :sz, true, :s)"""
                ),
                {"p": prof, "k": k, "sz": sz, "s": order},
            )
            order += 1
        # Explicitly disable remaining built-in ringkasan panels so they don't leak into the profile
        for k in ALL_BUILTIN_RINGKASAN:
            if k not in shown:
                conn.execute(
                    sa.text(
                        """INSERT INTO layout (profile, page, role, key, title, size, enabled, sort)
                           VALUES (:p, 'ringkasan', '', :k, '', '', false, :s)"""
                    ),
                    {"p": prof, "k": k, "s": order},
                )
                order += 1


def downgrade():
    conn = op.get_bind()
    for key, *_ in NEW_PARAMS:
        conn.execute(sa.text("DELETE FROM app_parameter WHERE key = :k"), {"k": key})
