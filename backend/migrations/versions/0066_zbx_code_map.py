"""Zabbix location codes that are known: Pelindo Place, Pelindo Tower Direksi and Komisaris belong to Kantor Perwakilan; COREACCESS and SDWAN are device types, not locations.

Revision ID: 0066
Revises: 0065
"""
from alembic import op
from sqlalchemy import text

revision = "0066"
down_revision = "0065"
branch_labels = None
depends_on = None


def upgrade():
    c = op.get_bind()
    for code, site, note in (("PELPLACE", "Kantor Perwakilan", "Pelindo Place"), ("PELTODIR", "Kantor Perwakilan", "Pelindo Tower, Direksi floor"), ("PELTOKOM", "Kantor Perwakilan", "Pelindo Tower, Komisaris floor"),
                             ("COREACCESS", None, "Device type, not a location"), ("SDWAN", None, "Device type, not a location"), ("SBK", None, "Sri Bayintan Kijang"), ("SBP", None, "Sri Bintan Pura"),
                             ("SPA", None, "Selat Panjang"), ("R1", None, "Regional 1 area")):
        c.execute(text("UPDATE zbx_loc_map SET site = COALESCE(:s, site), note = :n WHERE code = :c"), {"s": site, "n": note, "c": code})


def downgrade():
    pass
