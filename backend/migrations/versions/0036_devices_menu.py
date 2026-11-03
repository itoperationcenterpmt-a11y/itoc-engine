"""Devices becomes a menu group (Summary, Network, CCTV, Operational, Milestone); the Milestone camera inventory moves under it.

Revision ID: 0036
Revises: 0035
"""
import json
from alembic import op
from sqlalchemy import text

revision = "0036"
down_revision = "0035"
branch_labels = None
depends_on = None

WHY = "Device status is the current state from Zabbix, so period and shift do not apply."
FILT = {"p": 0, "s": 0, "l": 1, "c": 0, "t": 1, "g": 1, "y": 1}
NEW = [("devnet", "Network", 51), ("devcctv", "CCTV", 52), ("devops", "Operational", 53)]
KINDS = {"devnet": "NETWORK", "devcctv": "CCTV", "devops": "OPERASIONAL"}


def upgrade():
    c = op.get_bind()
    c.execute(text("UPDATE module SET label = 'Milestone', parent = 'devices', sort = 54 WHERE key = 'cctv'"))
    for key, label, sort in NEW:
        c.execute(text("INSERT INTO module (key, label, sort, enabled, filters, why, parent, icon) VALUES (:k, :l, :s, true, CAST(:f AS jsonb), :w, 'devices', 'camera') ON CONFLICT (key) DO NOTHING"),
                  {"k": key, "l": label, "s": sort, "f": json.dumps(FILT), "w": WHY})
    c.execute(text("INSERT INTO app_parameter (key, value, label, \"group\", editor, ui, description, sort) VALUES ('dev.tab_kinds', CAST(:v AS jsonb), 'Devices sub-menu to Zabbix category', 'devices', 'json', '{}'::jsonb, 'menu key: category code (Zabbix host group prefix)', 2) ON CONFLICT (key) DO NOTHING"),
              {"v": json.dumps(KINDS)})
    for key, _, _ in NEW:
        c.execute(text("UPDATE role SET modules = array_append(modules, :k) WHERE 'devices' = ANY(modules) AND NOT (:k = ANY(modules))"), {"k": key})


def downgrade():
    pass
