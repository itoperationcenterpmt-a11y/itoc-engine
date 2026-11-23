"""Add /isp command to stored chat.commands parameter (if missing) so WA/Telegram bots and Admin > Notifications > Bot & Notifier API list it automatically.

Revision ID: 0082
Revises: 0081
"""
import json
from alembic import op
from sqlalchemy import text

revision = "0082"
down_revision = "0081"
branch_labels = None
depends_on = None

ISP_CMD = {
    "name": "isp",
    "kind": "isp",
    "scope": "duty",
    "branch_arg": True,
    "group": "area",
    "help": "status ISP per provider & cabang (Zabbix ISP-* dan PRTG)",
}


def upgrade() -> None:
    bind = op.get_bind()
    row = bind.execute(text("SELECT value FROM app_parameter WHERE key = 'chat.commands'")).fetchone()
    if not row or not row[0]:
        return
    val = row[0] if isinstance(row[0], dict) else json.loads(row[0])
    cmds = val.get("commands") if isinstance(val, dict) else None
    if not isinstance(cmds, list):
        return
    if any(isinstance(c, dict) and str(c.get("name", "")).lower() == "isp" for c in cmds):
        return
    idx = next((i + 1 for i, c in enumerate(cmds) if isinstance(c, dict) and str(c.get("name", "")).lower() == "link"), len(cmds))
    cmds.insert(idx, ISP_CMD)
    bind.execute(
        text("UPDATE app_parameter SET value = CAST(:v AS jsonb) WHERE key = 'chat.commands'"),
        {"v": json.dumps(val)},
    )


def downgrade() -> None:
    bind = op.get_bind()
    row = bind.execute(text("SELECT value FROM app_parameter WHERE key = 'chat.commands'")).fetchone()
    if not row or not row[0]:
        return
    val = row[0] if isinstance(row[0], dict) else json.loads(row[0])
    cmds = val.get("commands") if isinstance(val, dict) else None
    if not isinstance(cmds, list):
        return
    val["commands"] = [c for c in cmds if not (isinstance(c, dict) and str(c.get("name", "")).lower() == "isp")]
    bind.execute(
        text("UPDATE app_parameter SET value = CAST(:v AS jsonb) WHERE key = 'chat.commands'"),
        {"v": json.dumps(val)},
    )
