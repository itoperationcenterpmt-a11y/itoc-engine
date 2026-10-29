"""WiFi zones and AP codes resolve to master locations through site aliases (Admin > Mapping), like Zabbix codes and PRTG devices; stored WiFi session locations are recalculated.

Revision ID: 0065
Revises: 0064
"""
from alembic import op
from sqlalchemy import text

revision = "0065"
down_revision = "0064"
branch_labels = None
depends_on = None

ALIASES = {"Head Office": ["ho_belawan"], "Branch Tanjung Emas": ["tj emas"], "Branch Tanjung Pinang": ["tj pinang"], "Branch Tanjung Intan": ["tj intan"], "Branch Tanjung Wangi": ["tj wangi"],
           "Branch Tanjung Balai Karimun": ["tb karimun", "tjb"], "Branch Lembar": ["lembar gilmas", "glm"], "Branch Parepare": ["pare pare"], "Branch Janirah": ["jamrud nilam mirah"],
           "Kantor Perwakilan": ["pelindo tower_mesh"], "Branch Lhokseumawe": ["lhoksumawe", "lhk"], "Branch Dumai": ["dum"], "Branch Garongkong": ["garongkong"], "Branch Badas": ["bds"]}


def upgrade():
    c = op.get_bind()
    for site, als in ALIASES.items():
        for a in als:
            c.execute(text("UPDATE site SET aliases = array_append(COALESCE(aliases, '{}'), :a) WHERE name = :s AND NOT (:a = ANY(COALESCE(aliases, '{}')))"), {"a": a, "s": site})
    cmap = {r[0].lower(): r[1] for r in c.execute(text("SELECT code, site FROM zbx_loc_map WHERE site IS NOT NULL"))}
    amap = {}
    for name, als in c.execute(text("SELECT name, aliases FROM site WHERE active")):
        for n in {name.lower(), name.lower().removeprefix("branch ").strip(), *[x.lower().strip() for x in (als or [])]}:
            if n:
                amap.setdefault(n, name)

    def to_site(*tokens):
        for t in tokens:
            k = (t or "").strip().lower()
            for v in (k, k.replace("_", " ")):
                if v and (cmap.get(v) or amap.get(v)):
                    return cmap.get(v) or amap.get(v)
        return None
    for ap, zone in c.execute(text("SELECT DISTINCT ap_name, zone FROM wifi_session")).fetchall():
        loc = to_site((ap or "").split("-")[0], zone) or zone
        c.execute(text("UPDATE wifi_session SET loc = :l WHERE ap_name IS NOT DISTINCT FROM :a AND zone IS NOT DISTINCT FROM :z AND loc IS DISTINCT FROM :l"), {"l": loc, "a": ap, "z": zone})


def downgrade():
    pass
