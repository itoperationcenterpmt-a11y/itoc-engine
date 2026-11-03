"""Login page: English by default with an Indonesian variant (parameter ui.login_id, EN/ID switch on the page); English labels for five parameters.

Revision ID: 0068
Revises: 0067
"""
import json

from alembic import op
from sqlalchemy import text

revision = "0068"
down_revision = "0067"
branch_labels = None
depends_on = None

OLD_ID = {"headline": "Satu layar untuk seluruh terminal", "tagline": "Dashboard terpusat Divisi Teknologi Informasi PT Pelindo Multi Terminal."}
EN = {"headline": "One screen for every terminal", "tagline": "The central dashboard of the Information Technology Division, PT Pelindo Multi Terminal.",
      "acronym": [["T", "Telemetry", "Real-time ISP links and infrastructure"], ["E", "Events", "Tickets, threats, and firewall actions"], ["R", "Response", "Incident handling and SLA"], ["A", "Analytics", "Trends, evaluation, and reports"]]}
LABELS = {"soc.internet_zone": "Internet zone name", "report.company": "Company name on the PowerPoint report cover",
          "dev.map_bounds": "Devices map bounds (degrees): lat_min, lat_max, lon_min, lon_max", "wifi.weak_rssi": "Weak client signal below (dBm)"}


def upgrade():
    c = op.get_bind()
    cur = {k: v for k, v in c.execute(text("SELECT key, value FROM app_parameter WHERE key LIKE 'ui.login_%'"))}
    idv = {}
    for k in ("headline", "tagline"):
        if cur.get("ui.login_" + k) == OLD_ID[k]:
            idv[k] = OLD_ID[k]
            c.execute(text("UPDATE app_parameter SET value = CAST(:v AS jsonb) WHERE key = :k"), {"v": json.dumps(EN[k]), "k": "ui.login_" + k})
    acr = cur.get("ui.login_acronym")
    if acr and len(acr[0]) > 2 and "real-time" in acr[0][2]:
        idv["acronym"] = acr
        c.execute(text("UPDATE app_parameter SET value = CAST(:v AS jsonb) WHERE key = 'ui.login_acronym'"), {"v": json.dumps(EN["acronym"])})
    if idv:
        c.execute(text("""INSERT INTO app_parameter (key, value, label, "group", editor, ui, sort) VALUES ('ui.login_id', CAST(:v AS jsonb), 'Login page text in Indonesian (shown when ID is selected)', 'tampilan', 'json', '{}'::jsonb, 96)
                          ON CONFLICT (key) DO NOTHING"""), {"v": json.dumps(idv, ensure_ascii=False)})
    for k, label in LABELS.items():
        c.execute(text("UPDATE app_parameter SET label = :l WHERE key = :k"), {"l": label, "k": k})
    c.execute(text("UPDATE data_source SET tip = 'Milestone XProtect RESTful API (API Gateway + IDP): camera and recording server status (read only)' WHERE key = 'milestone' AND tip LIKE '%status kamera%'"))


def downgrade():
    pass
