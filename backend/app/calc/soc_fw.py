"""NDR per firewall and location, from soc_fw_day (Panorama device names). A firewall is matched to a location by name ('SPMT-TANJUNG-EMAS-PA440' -> Tanjung Emas) unless an admin override exists."""
import re
from datetime import date, timedelta
from difflib import SequenceMatcher
from sqlalchemy import Text, cast, func, select
from ..models import DataSource, Site, SocFwDay, SocFwMap

PASS = ("alert", "allow")        # actions that do not stop the traffic


def progress(db, cfg) -> list:
    """How much of the Palo Alto history that is collected in the background (a few days per sync) is in: [{label, done, total, pending, per}]."""
    today = cfg.now().date()
    yest = today - timedelta(days=1)
    src = db.get(DataSource, "panorama")
    c = (src.config or {}) if src else {}
    lower = date.fromisoformat(c["backfill_from"]) if c.get("backfill_from") else yest - timedelta(days=int(c.get("backfill_days", 14)) - 1)
    lower = max(lower, today - timedelta(days=int(c.get("fw_days", 210))))
    rows = db.execute(select(SocFwDay.day, func.sum(SocFwDay.bytes), func.bool_or(cast(SocFwDay.src, Text) != "{}"), func.bool_or(cast(SocFwDay.urlc, Text) != "{}"), func.bool_or(cast(SocFwDay.acat, Text) != "{}"))
                      .where(SocFwDay.day >= lower, SocFwDay.day <= yest).group_by(SocFwDay.day)).all()
    traffic = [r for r in rows if r[1]]
    det = [r for r in traffic if r[0] >= today - timedelta(days=int(c.get("fw_detail_days", 45)))]
    item = lambda label, done, total, per: {"label": label, "done": done, "total": total, "pending": max(total - done, 0), "per": per}
    return [item("Events, traffic and applications per firewall", len(rows), max((yest - lower).days + 1, 0), int(c.get("max_fw_days_per_run", 8))),
            item("Source networks and web users", sum(1 for r in traffic if r[2]), len(traffic), int(c.get("max_fw_days_per_run", 8))),
            item("Application and web categories", sum(1 for r in det if r[3] or r[4]), len(det), int(c.get("max_fw_detail_per_run", 3)))]


def _k(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def core(fw: str) -> str:
    """Firewall name without the SPMT prefix and the model suffix."""
    n = re.sub(r"^SPMT-", "", fw or "", flags=re.I)
    return re.sub(r"-(PA|FW)[-\d].*$", "", n, flags=re.I)


def guess(fw: str, sites: list) -> str | None:
    c = _k(core(fw))
    if not c:
        return None
    best, score = None, 0.0
    for s in sites:
        keys = [_k(re.sub(r"^(Branch|Kantor)\s+", "", s.name, flags=re.I))] + [_k(a) for a in (s.aliases or [])]
        for i, k in enumerate(keys):
            if not k:
                continue
            if k == c or (i and len(k) >= 3 and c.startswith(k)):
                return s.name
            r = SequenceMatcher(None, c, k).ratio()
            if (len(k) >= 5 and (k in c or c in k)) or r >= 0.84:
                if r + 0.1 > score:
                    best, score = s.name, r + 0.1
    return best


def shared(cfg) -> list:
    """Locations that share one NDR (for example Head Office and Belawan use the same firewall)."""
    return [list(g) for g in (cfg.p("soc.shared_ndr", [["Head Office", "Branch Belawan"]]) or []) if len(g) > 1]


def short(n: str) -> str:
    return re.sub(r"^(Branch|Kantor)\s+", "", n, flags=re.I)


def canon(cfg, site):
    """A location's NDR label: shared locations get one joined label."""
    for g in shared(cfg):
        if site in g:
            return " + ".join(short(x) for x in g)
    return site


def site_map(db, fws) -> dict:
    over = {m.fw: m.site for m in db.scalars(select(SocFwMap))}
    sites = db.scalars(select(Site).where(Site.active.is_(True))).all()
    return {fw: (over[fw] or None) if fw in over else guess(fw, sites) for fw in fws}


def build(db, cfg, a, b, site: str = "") -> dict:
    rows = db.scalars(select(SocFwDay).where(SocFwDay.day >= a, SocFwDay.day <= b)).all()
    first, last = db.execute(select(func.min(SocFwDay.day), func.max(SocFwDay.day))).one()
    allfw = sorted({r.fw for r in db.scalars(select(SocFwDay))}) if rows or first else []
    smap = {k: canon(cfg, v) if v else v for k, v in site_map(db, allfw).items()}
    want = canon(cfg, site) if site else ""
    fw: dict = {}
    daily: dict = {}
    agg = {"cat": {}, "typ": {}, "app": {}, "sev": {}, "act": {}, "src": {}, "acat": {}, "urlc": {}, "webu": {}}
    for r in rows:
        st = smap.get(r.fw)
        if want and st != want:
            continue
        x = fw.setdefault(r.fw, {"fw": r.fw, "site": st, "events": 0, "crit": 0, "high": 0, "med": 0, "low": 0, "blocked": 0, "bytes": 0, "sessions": 0, "days": set(), "tfrom": None})
        for k, src in (("cat", r.cat), ("typ", r.typ), ("app", r.app), ("src", r.src), ("acat", r.acat), ("urlc", r.urlc), ("webu", r.webu)):
            for kk, vv in (src or {}).items():
                agg[k][kk] = agg[k].get(kk, 0) + vv
        for kk, vv in r.sev.items():
            agg["sev"][kk] = agg["sev"].get(kk, 0) + vv
        for kk, vv in r.act.items():
            agg["act"][kk] = agg["act"].get(kk, 0) + vv
        n = sum(r.sev.values())
        x["events"] += n
        x["crit"] += r.sev.get("critical", 0)
        x["high"] += r.sev.get("high", 0)
        x["med"] += r.sev.get("medium", 0)
        x["low"] += r.sev.get("low", 0) + r.sev.get("informational", 0)
        x["blocked"] += sum(v for k, v in r.act.items() if k not in PASS)
        x["bytes"] += r.bytes
        x["sessions"] += r.sessions
        x["days"].add(r.day)
        if r.bytes and (x["tfrom"] is None or r.day < x["tfrom"]):
            x["tfrom"] = r.day
        d = daily.setdefault(r.day, {"critical": 0, "high": 0, "other": 0, "bytes": 0, "sessions": 0, "blocked": 0})
        d["bytes"] += r.bytes
        d["sessions"] += r.sessions
        d["blocked"] += sum(v for k, v in r.act.items() if k not in PASS)
        d["critical"] += r.sev.get("critical", 0)
        d["high"] += r.sev.get("high", 0)
        d["other"] += n - r.sev.get("critical", 0) - r.sev.get("high", 0)
    days, d = [], a
    while d <= b:
        days.append({"date": d.isoformat(), **daily.get(d, {"critical": 0, "high": 0, "other": 0, "bytes": 0, "sessions": 0, "blocked": 0})})
        d += timedelta(days=1)
    by_site: dict = {}
    for x in fw.values():
        s = by_site.setdefault(x["site"] or "Unmapped", {"site": x["site"] or "Unmapped", "events": 0, "ch": 0, "blocked": 0, "bytes": 0, "fw": 0})
        s["events"] += x["events"]
        s["ch"] += x["crit"] + x["high"]
        s["blocked"] += x["blocked"]
        s["bytes"] += x["bytes"]
        s["fw"] += 1
    tot = lambda k: sum(x[k] for x in fw.values())
    top = lambda d, n=10: [{"k": k, "n": v} for k, v in sorted(d.items(), key=lambda kv: -kv[1])[:n] if k not in ("-", "")]
    return {"from": first.isoformat() if first else None, "to": last.isoformat() if last else None, "site": site, "nFw": len(fw), "days": days,
            "total": {"events": tot("events"), "ch": tot("crit") + tot("high"), "crit": tot("crit"), "blocked": tot("blocked"), "bytes": tot("bytes"), "sessions": tot("sessions")},
            "span": (b - a).days + 1, "cat": top(agg["cat"]), "typ": top(agg["typ"]), "app": top(agg["app"]), "src": top(agg["src"], 15), "acat": top(agg["acat"], 10), "urlc": top(agg["urlc"], 12), "webu": top(agg["webu"], 15), "webTotal": sum(agg["urlc"].values()), "progress": progress(db, cfg),
            "detailFrom": min((r.day.isoformat() for r in rows if r.urlc or r.acat), default=None), "sev": top(agg["sev"], 6), "act": top(agg["act"], 8), "dayN": len({r.day for r in rows}), "fw": sorted(({**x, "days": len(x["days"]), "tfrom": x["tfrom"].isoformat() if x["tfrom"] else None} for x in fw.values()), key=lambda x: -(x["crit"] * 1000 + x["high"] * 10 + x["events"] / 1e6)),
            "bySite": sorted(by_site.values(), key=lambda s: -s["ch"]), "unmapped": sorted(fw_ for fw_, s in smap.items() if not s)}
