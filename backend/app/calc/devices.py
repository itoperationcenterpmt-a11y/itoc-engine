"""Devices (CCTV, Gate System, dan kategori lain) dari snapshot Zabbix (tabel zbx_host).
Kategori = prefix host group (label di parameter dev.kind_labels). Lokasi dari kode di nama grup: tabel pemetaan zbx_loc_map lebih dulu, lalu alias lokasi,
lalu kode apa adanya. Koordinat peta dari master Lokasi (lat, lon)."""
from datetime import datetime
from sqlalchemy.orm import Session
from .. import models as M
from ..store import Config
from ..timeutil import ms
from .network import device_names

ORDER = {"down": 0, "degraded": 1, "maintenance": 2, "up": 3, "disabled": 4}


def _alias_map(db: Session) -> dict:
    out = {}
    for s in db.query(M.Site).filter_by(active=True):
        for n in device_names(db, s.name):
            out.setdefault(n, s.name)
    return out


def _agg(items):
    c = {k: 0 for k in ("up", "down", "degraded", "maintenance", "disabled")}
    for h, _ in items:
        c[h.status] = c.get(h.status, 0) + 1
    up, down = c["up"], c["down"]
    return {"total": len(items), "up": up, "down": down, "deg": c["degraded"], "maint": c["maintenance"], "off": c["disabled"], "avail": up / (up + down) if up + down else None}


def build(db: Session, cfg: Config, site: str = "", kind: str = "", status: str = "", full: bool = False) -> dict:
    labels = cfg.p("dev.kind_labels", {}) or {}
    chronic_h = 24 * int(cfg.p("dev.chronic_days", 30) or 30)
    amap = _alias_map(db)
    cmap = {m.code.lower(): m.site for m in db.query(M.ZbxLocMap) if m.site}
    sites = {s.name: s for s in db.query(M.Site)}
    now = cfg.now()
    unmapped: dict = {}
    allrows = []
    for h in db.query(M.ZbxHost).all():
        c = (h.code or "").lower()
        loc = cmap.get(c) or amap.get(c)
        if not loc:
            loc = h.code or "-"
            unmapped[loc] = unmapped.get(loc, 0) + 1
        allrows.append((h, loc))
    by_site = [r for r in allrows if not site or r[1] == site]
    rows = [r for r in by_site if not kind or r[0].kind == kind]

    def age(h):
        return round((now - h.down_since).total_seconds() / 3600, 1) if h.down_since else None

    def item(h, loc):
        return {"name": h.name, "kind": h.kind, "kindLabel": labels.get(h.kind, h.kind), "loc": loc, "status": h.status,
                "since": ms(h.down_since) if h.down_since else None, "ageH": age(h), "problem": h.problem or ""}

    kinds, locs = {}, {}
    for r in by_site:
        kinds.setdefault(r[0].kind or "-", []).append(r)
    for r in rows:
        locs.setdefault(r[1], []).append(r)
    by_kind = sorted(({"k": labels.get(k, k), "key": k, **_agg(v)} for k, v in kinds.items()), key=lambda x: -x["total"])
    by_loc = sorted(({"k": k, **_agg(v)} for k, v in locs.items()), key=lambda x: (-x["down"], -x["total"], x["k"]))
    down = sorted((item(h, loc) for h, loc in rows if h.status == "down"), key=lambda d: (d["ageH"] is None, -(d["ageH"] or 0), d["name"]))
    cdays = chronic_h // 24
    buckets = [("kurang dari 1 hari", 0, 24), ("1 sampai 7 hari", 24, 168), (f"7 sampai {cdays} hari", 168, chronic_h), (f"lebih dari {cdays} hari", chronic_h, 1e12)]
    age_dist = [{"k": lb, "n": sum(1 for d in down if d["ageH"] is not None and lo <= d["ageH"] < hi)} for lb, lo, hi in buckets]
    nt = sum(1 for d in down if d["ageH"] is None)
    if nt:
        age_dist.append({"k": "tanpa waktu", "n": nt})
    mp, nocoord = [], []
    for k, v in locs.items():
        s = sites.get(k)
        a = _agg(v)
        if s is not None and s.lat is not None and s.lon is not None:
            mp.append({"k": k, "lat": s.lat, "lon": s.lon, **a})
        else:
            nocoord.append(k)
    kind_loc, kind_down = {}, {}
    for key, v in kinds.items():
        lg = {}
        for h, loc in v:
            lg.setdefault(loc, []).append((h, loc))
        kind_loc[key] = sorted(({"k": k, **_agg(x)} for k, x in lg.items()), key=lambda x: (-x["down"], -x["total"], x["k"]))[:8]
        kind_down[key] = sorted((item(h, loc) for h, loc in v if h.status == "down"), key=lambda d: (d["ageH"] is None, -(d["ageH"] or 0), d["name"]))[:10]
    lst, list_n = [], 0
    if full:
        sel = [r for r in rows if not status or r[0].status == status]
        list_n = len(sel)
        sel.sort(key=lambda r: (ORDER.get(r[0].status, 9), -(age(r[0]) or 0), r[0].name))
        lst = [item(h, loc) for h, loc in sel[:500]]
    src = db.get(M.DataSource, "zabbix")
    last = max((h.updated_at for h, _ in allrows), default=None)
    every = (src.interval_min if src else 5) or 5
    stale = bool(last) and (datetime.utcnow() - last).total_seconds() > every * 60 * 3
    return {"all": _agg(rows), "chronic": sum(1 for d in down if d["ageH"] is not None and d["ageH"] > chronic_h), "chronicDays": cdays,
            "byKind": by_kind, "byLoc": by_loc, "down": down[:200], "downN": len(down), "ageDist": age_dist, "map": mp, "noCoord": sorted(nocoord),
            "unmapped": [{"code": c, "n": n} for c, n in sorted(unmapped.items(), key=lambda x: -x[1])], "kindLoc": kind_loc, "kindDown": kind_down,
            "list": lst, "listN": list_n, "updated": ms(last + (now - datetime.utcnow())) if last else None, "stale": stale,
            "configured": bool(src and (src.config or {}).get("base_url")), "enabled": bool(src and src.enabled), "error": src.last_error if src else None}