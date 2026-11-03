"""Uptime Kuma: status now plus availability and response time over the report period, per monitor, location, and type.
A monitor belongs to a location when its name, first word, or host matches a site name or alias (the same naming bridge as Zabbix, WiFi, and PRTG); the rest is listed under "Unmapped"."""
import re
from datetime import date, datetime, timedelta
from sqlalchemy import func
from ..models import DataSource, KumaHourly, KumaMonitor
from ..store import Config
from ..timeutil import ms
from .network import site_resolver

LABEL = {0: "Down", 1: "Up", 2: "Pending", 3: "Maintenance"}
UNMAPPED = "Unmapped"
CERT_WARN_DAYS = 14
STALE_MIN = 20                                  # minutes without a sync before the data counts as stale


def _target(m: KumaMonitor) -> str:
    host = m.hostname or ""
    if host:
        return host + (":" + m.port if m.port else "")
    return (m.url or "").replace("https://", "").replace("http://", "").rstrip("/")


def _words(name: str) -> list[str]:
    return [w for w in re.split(r"[\s\-_/|:()\[\]]+", name) if w]


def build(db, cfg: Config, a: date, b: date, site: str = "") -> dict:
    src = db.get(DataSource, "uptimekuma")
    rows = db.query(KumaMonitor).all()
    to_site = site_resolver(db)
    t0, t1 = datetime.combine(a, datetime.min.time()), datetime.combine(b + timedelta(days=1), datetime.min.time())
    h = {k: (s, d, sm, nm, mx, dh) for k, s, d, sm, nm, mx, dh in db.query(
        KumaHourly.monitor_key, func.sum(KumaHourly.samples), func.sum(KumaHourly.down), func.sum(KumaHourly.sum_ms), func.sum(KumaHourly.n_ms), func.max(KumaHourly.max_ms),
        func.sum(KumaHourly.down * 1.0 / func.nullif(KumaHourly.samples, 0))).filter(KumaHourly.ts >= t0, KumaHourly.ts < t1).group_by(KumaHourly.monitor_key)}
    mons = []
    for m in rows:
        w = _words(m.name)
        loc = to_site(m.name, " ".join(w[:2]), w[0] if w else "", m.hostname) or UNMAPPED
        if site and loc != site:
            continue
        s, d, sm, nm, mx, dh = h.get(m.key, (0, 0, 0, 0, None, 0))
        mons.append({"key": m.key, "name": m.name, "type": m.type or "-", "target": _target(m), "loc": loc, "status": m.status, "label": LABEL.get(m.status, "-"), "resp": m.response_ms,
                     "cert": m.cert_days, "avail": 1 - d / s if s else None, "samples": int(s or 0), "downH": round(float(dh or 0), 2), "avgMs": sm / nm if nm else None, "maxMs": mx})
    keys = {m["key"] for m in mons}
    daily: dict = {}
    q = db.query(func.date(KumaHourly.ts), func.sum(KumaHourly.samples), func.sum(KumaHourly.down)).filter(KumaHourly.ts >= t0, KumaHourly.ts < t1)
    if site:
        q = q.filter(KumaHourly.monitor_key.in_(keys or [""]))
    for d, s, dn in q.group_by(func.date(KumaHourly.ts)):
        daily[d] = (int(s or 0), int(dn or 0))
    days = []
    x = a
    while x <= b:
        s, dn = daily.get(x, (0, 0))
        days.append({"date": x.isoformat(), "avail": 1 - dn / s if s else None, "down": dn, "samples": s})
        x += timedelta(days=1)
    tot_s, tot_d = sum(m["samples"] for m in mons), sum(round(m["samples"] * (1 - m["avail"])) for m in mons if m["avail"] is not None)

    def agg(key):
        g: dict = {}
        for m in mons:
            o = g.setdefault(m[key], {"k": m[key], "n": 0, "down": 0, "samples": 0, "dn": 0, "sum": 0.0, "nms": 0})
            o["n"] += 1
            o["down"] += m["status"] == 0
            if m["avail"] is not None:
                o["samples"] += m["samples"]
                o["dn"] += round(m["samples"] * (1 - m["avail"]))
            if m["avgMs"] is not None:
                o["sum"] += m["avgMs"]
                o["nms"] += 1
        return sorted(({"k": o["k"], "n": o["n"], "down": o["down"], "avail": 1 - o["dn"] / o["samples"] if o["samples"] else None, "avgMs": o["sum"] / o["nms"] if o["nms"] else None} for o in g.values()),
                      key=lambda r: (-r["down"], r["avail"] if r["avail"] is not None else 2, r["k"]))
    last = max((m.updated_at for m in rows), default=None)
    first = db.query(func.min(KumaHourly.ts)).scalar()
    count = lambda st: sum(1 for m in mons if m["status"] == st)
    avg_ms = [m["avgMs"] for m in mons if m["avgMs"] is not None]
    mons.sort(key=lambda m: (m["status"] != 0, m["avail"] if m["avail"] is not None else 2, m["name"]))
    return {"configured": bool(src and src.enabled and rows), "enabled": bool(src and src.enabled), "error": src.last_error if src else None, "total": len(mons), "up": count(1), "down": count(0), "pending": count(2), "maint": count(3),
            "avail": 1 - tot_d / tot_s if tot_s else None, "avgMs": sum(avg_ms) / len(avg_ms) if avg_ms else None, "certSoon": sum(1 for m in mons if m["cert"] is not None and m["cert"] <= CERT_WARN_DAYS),
            "certWarn": CERT_WARN_DAYS, "mons": mons, "daily": days, "byLoc": agg("loc"), "byType": agg("type"), "unmapped": sorted({m["name"] for m in mons if m["loc"] == UNMAPPED}),
            "since": first.isoformat() if first else None, "updated": ms(last) if last else None, "stale": bool(last) and (cfg.now() - last).total_seconds() > STALE_MIN * 60}
