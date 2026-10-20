"""Devices (CCTV, Gate System) dari snapshot Zabbix (tabel zbx_host). Lokasi dari kode di nama host group dipetakan lewat alias lokasi (master Lokasi);
kode yang belum dikenal tampil apa adanya. Label kategori diambil dari parameter dev.kind_labels."""
from datetime import datetime
from sqlalchemy.orm import Session
from .. import models as M
from ..store import Config
from ..timeutil import ms
from .network import device_names


def _loc_map(db: Session) -> dict:
    out = {}
    for s in db.query(M.Site).filter_by(active=True):
        for n in device_names(db, s.name):
            out.setdefault(n, s.name)
    return out


def build(db: Session, cfg: Config, site: str = "") -> dict:
    labels = cfg.p("dev.kind_labels", {}) or {}
    amap = _loc_map(db)
    rows = []
    for h in db.query(M.ZbxHost).all():
        loc = amap.get((h.code or "").lower()) or (h.code or "-")
        if site and loc != site:
            continue
        rows.append((h, loc))
    src = db.get(M.DataSource, "zabbix")
    now = cfg.now()

    def agg(items):
        up = sum(1 for h, _ in items if h.status == "up")
        down = sum(1 for h, _ in items if h.status == "down")
        mt = sum(1 for h, _ in items if h.status == "maintenance")
        off = sum(1 for h, _ in items if h.status == "disabled")
        deg = sum(1 for h, _ in items if h.status == "degraded")
        return {"total": len(items), "up": up, "down": down, "deg": deg, "maint": mt, "off": off, "avail": up / (up + down) if up + down else None}

    kinds = {}
    for h, loc in rows:
        kinds.setdefault(h.kind or "-", []).append((h, loc))
    locs = {}
    for h, loc in rows:
        locs.setdefault(loc, []).append((h, loc))
    by_kind = sorted(({"k": labels.get(k, k), "key": k, **agg(v)} for k, v in kinds.items()), key=lambda x: -x["total"])
    by_loc = sorted(({"k": k, **agg(v)} for k, v in locs.items()), key=lambda x: (-x["down"], -x["total"], x["k"]))
    down = []
    for h, loc in rows:
        if h.status == "down":
            age = (now - h.down_since).total_seconds() / 3600 if h.down_since else None
            down.append({"name": h.name, "kind": labels.get(h.kind, h.kind), "loc": loc, "since": ms(h.down_since) if h.down_since else None,
                         "ageH": round(age, 1) if age is not None else None, "problem": h.problem or ""})
    down.sort(key=lambda d: (d["ageH"] is None, -(d["ageH"] or 0), d["name"]))
    last = max((h.updated_at for h, _ in rows), default=None)
    every = (src.interval_min if src else 5) or 5
    stale = bool(last) and (datetime.utcnow() - last).total_seconds() > every * 60 * 3
    chronic = sum(1 for d in down if d["ageH"] is not None and d["ageH"] > 24 * 30)
    return {"all": agg(rows), "chronic": chronic, "byKind": by_kind, "byLoc": by_loc, "down": down[:200], "downN": len(down),
            "updated": ms(last + (now - datetime.utcnow())) if last else None, "stale": stale,
            "configured": bool(src and (src.config or {}).get("base_url")), "enabled": bool(src and src.enabled),
            "error": src.last_error if src else None}