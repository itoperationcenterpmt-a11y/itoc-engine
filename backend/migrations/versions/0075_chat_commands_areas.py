"""Chat commands: /cctv, /wifi, /devices and /link are added to the stored list (only when it has no command called cctv yet), so edits made in Admin stay.

Revision ID: 0075
Revises: 0074
"""
import json

from alembic import op
from sqlalchemy import text

revision = "0075"
down_revision = "0074"
branch_labels = None
depends_on = None

NEW = [
    {
        "name": "cctv",
        "kind": "cctv",
        "scope": "duty",
        "branch_arg": True,
        "group": "area",
        "line": "status per bidang, bisa per cabang: /cctv-parepare",
        "help": "status CCTV (Milestone dan Zabbix)"
    },
    {
        "name": "wifi",
        "kind": "wifi",
        "scope": "duty",
        "branch_arg": True,
        "group": "area",
        "help": "status WiFi (Access Point dan client)"
    },
    {
        "name": "devices",
        "aliases": [
            "perangkat"
        ],
        "kind": "device",
        "scope": "duty",
        "branch_arg": True,
        "group": "area",
        "help": "status perangkat Zabbix"
    },
    {
        "name": "link",
        "aliases": [
            "web"
        ],
        "kind": "link",
        "scope": "duty",
        "branch_arg": True,
        "group": "area",
        "help": "status link ISP dan web (PRTG dan Uptime Kuma)"
    }
]


def upgrade():
    c = op.get_bind()
    row = c.execute(text("SELECT value FROM app_parameter WHERE key = 'chat.commands'")).first()
    if not row or not isinstance(row[0], dict) or any(x.get("name") == "cctv" for x in row[0].get("commands", []) if isinstance(x, dict)):
        return
    v = dict(row[0])
    cmds = list(v.get("commands", []))
    at = next((i for i, x in enumerate(cmds) if isinstance(x, dict) and x.get("name") == "7hari"), len(cmds))      # before /7hari, like the built-in order
    v["commands"] = cmds[:at] + NEW + cmds[at:]
    c.execute(text("UPDATE app_parameter SET value = CAST(:v AS jsonb) WHERE key = 'chat.commands'"), {"v": json.dumps(v, ensure_ascii=False)})


def downgrade():
    pass
