"""Internet usage from Sangfor IAG Report Center exports (table sangfor_batch): one summary per site and period, shown as the batch the person picks (default: latest).
Head Office and Belawan share one IAG (parameter net.shared_isp), so choosing either shows the same data."""
from sqlalchemy import select
from ..models import SangforBatch
from .network import shared_isp


def _ts(d):
    return d.isoformat() if d else None


def batch_row(b: SangforBatch) -> dict:
    return {"id": b.id, "site": b.site, "from": _ts(b.date_from), "to": _ts(b.date_to), "at": b.uploaded_at.isoformat() if b.uploaded_at else None, "by": b.uploaded_by, "file": b.file_name}


def detail(b: SangforBatch) -> dict:
    d = b.data or {}
    cat = {x["k"]: x for x in d.get("cat", [])}
    tot = cat.get("Total") or {}
    rank = d.get("rank", [])
    cats = sorted((x for k, x in cat.items() if k != "Total"), key=lambda x: -(x.get("bi") or 0)) or sorted((x for x in rank if x["k"] != "Total"), key=lambda x: -(x.get("bi") or 0))   # the category export often holds only the total: the ranking has the split
    apps: dict = {}
    users: dict = {}
    for r in rank:
        for name, v, _ in r.get("apps", []):
            if name != "Others" and v:
                apps[name] = apps.get(name, 0) + v
        for name, v, _ in r.get("users", []):
            if name != "Others" and v:
                users[name] = users.get(name, 0) + v
    ac = {x["k"]: x for x in d.get("access", [])}
    total_users = (ac.get("Total") or {}).get("users")
    sharing = d.get("sharing", [])
    mobile = d.get("mobile", [])
    bi = tot.get("bi") or sum(x.get("bi") or 0 for x in cats)
    inn = tot.get("in")
    top = next((x for x in cats if x["k"] != "Others"), None)
    return {"batch": batch_row(b), "topCat": {"k": top["k"], "pct": top.get("pct")} if top else None, "totalGb": bi, "avg": tot.get("avg"), "max": tot.get("max"), "inPct": (inn / bi) if inn and bi else None, "outGb": tot.get("out"), "inGb": inn, "users": total_users,
            "reject": sum(x.get("reject") or 0 for x in d.get("reject", [])), "shareMax": max((x[1] or 0 for x in sharing), default=None), "mobileMax": max((x[1] or 0 for x in mobile), default=None),
            "cats": [{"k": x["k"], "gb": x.get("bi") or 0, "pct": x.get("pct")} for x in cats[:15]],
            "dirs": [{"k": x["k"], "gb": x.get("bi") or 0} for x in d.get("dir", []) if x["k"] in ("Outbound", "Inbound")],
            "apps": [{"k": k, "gb": round(v, 1)} for k, v in sorted(apps.items(), key=lambda kv: -kv[1])[:15]],
            "topUsers": [{"k": k, "gb": round(v, 1)} for k, v in sorted(users.items(), key=lambda kv: -kv[1])[:15]],
            "peakUsers": [{"k": n, "mbps": v, "pct": p} for n, v, p in (tot.get("users") or [])[:10]],
            "access": [{"k": x["k"], "users": x.get("users") or 0, "pct": x.get("pct")} for x in d.get("access", []) if x["k"] != "Total"][:15],
            "sharing": sharing, "mobile": mobile,
            "rankRows": [{"k": r["k"], "gb": r.get("bi"), "pct": r.get("pct"), "topUser": (r.get("users") or [["-"]])[0][0], "topApp": (r.get("apps") or [["-"]])[0][0]} for r in rank[:15]]}


def build(db, cfg, site: str = "", batch_id: str = "") -> dict:
    rows = db.scalars(select(SangforBatch).order_by(SangforBatch.date_to.desc(), SangforBatch.id.desc())).all()
    sites = sorted({b.site for b in rows})
    group = set(shared_isp(db, site)) if site else None
    mine = [b for b in rows if group is None or b.site in group]
    pick = next((b for b in mine if str(b.id) == str(batch_id)), None)
    if pick is None and mine and (site or len(sites) == 1):
        pick = mine[0]
    latest: dict = {}
    for b in rows:
        latest.setdefault(b.site, b)
    summary = []
    for s, b in sorted(latest.items()):
        if group is not None and s not in group:
            continue
        x = detail(b)
        summary.append({"site": s, "from": _ts(b.date_from), "to": _ts(b.date_to), "gb": x["totalGb"], "avg": x["avg"], "max": x["max"], "users": x["users"], "id": b.id})
    return {"batches": [batch_row(b) for b in mine], "cur": detail(pick) if pick else None, "summary": summary, "sites": sites, "site": site}
