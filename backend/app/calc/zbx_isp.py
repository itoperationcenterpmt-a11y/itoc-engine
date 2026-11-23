"""ISP Live Monitoring from Zabbix hosts whose name starts with 'ISP-' (e.g. ISP-ASTINET-BELAWAN, ISP-LINTASARTA-GRK).
Provides live reachability, provider grouping, branch dual-link redundancy matrix, and outage history from zbx_event."""
from datetime import date, datetime, time as _t, timedelta
import re
from sqlalchemy.orm import Session
from .. import models as M
from ..store import Config
from ..timeutil import ms
from .devices import _alias_map, ORDER

# Common normalized tokens in Zabbix ISP host names -> canonical matching tokens
_NORM_FIX = {
    "headoffice": "head office",
    "makasar": "makassar",
    "pare pare": "parepare",
    "kualalangsa": "kuala langsa",
    "pelindoplace": "pelindo place",
    "janirah": "jamrud nilam mirah",
    "tanjung emas": "tanjung emas",
    "tanjung intan": "tanjung intan",
    "tanjung wangi": "tanjung wangi",
}


def _is_isp(h: M.ZbxHost) -> bool:
    return (h.name or "").strip().upper().startswith("ISP-") or (h.dev_code or "").upper() == "ISP"


def _provider_of(h: M.ZbxHost, isp_names: dict[str, str]) -> str:
    raw = (h.zone or "").strip()
    if not raw:
        parts = (h.name or "").strip().split("-")
        raw = parts[1].strip() if len(parts) >= 2 else "OTHER"
    k = raw.lower()
    for kw, label in isp_names.items():
        if kw in k or k in kw:
            return label
    return raw.upper()


def _resolve_loc(h: M.ZbxHost, cmap: dict, amap: dict) -> str:
    """Resolve branch location from subzone (most specific, e.g. TANJUNG-EMAS), then group code, then site aliases."""
    cands = []
    if h.subzone:
        s1 = re.sub(r"[-_]+", " ", h.subzone).strip().lower()
        cands.extend([h.subzone.strip().lower(), s1, _NORM_FIX.get(s1, "")])
    if h.code:
        c1 = h.code.strip().lower()
        cands.extend([c1, _NORM_FIX.get(c1, "")])
    for c in cands:
        if not c:
            continue
        if c in cmap:
            return cmap[c]
        if c in amap:
            return amap[c]
    # Fallback: readable title from subzone or code
    fb = re.sub(r"[-_]+", " ", (h.subzone or h.code or "-")).strip()
    return fb.title() if fb != "-" else "-"


def _agg(items: list) -> dict:
    c = {k: 0 for k in ("up", "down", "degraded", "maintenance", "disabled")}
    for h, _, _ in items:
        c[h.status] = c.get(h.status, 0) + 1
    # For ICMP-based ISP monitoring, 'degraded' means SNMP/Agent interface unavailable while ICMP ping is still UP.
    online = c["up"] + c["degraded"]
    down = c["down"]
    return {
        "total": len(items),
        "online": online,
        "up": c["up"],
        "deg": c["degraded"],
        "down": down,
        "maint": c["maintenance"],
        "off": c["disabled"],
        "avail": online / (online + down) if (online + down) else None,
    }


def build(db: Session, cfg: Config, a: date, b: date, site: str = "", provider: str = "", status: str = "", full: bool = False) -> dict:
    amap = _alias_map(db)
    cmap = {m.code.lower(): m.site for m in db.query(M.ZbxLocMap) if m.site}
    isp_names = {i["keyword"].lower(): i["name"] for i in (cfg.isps or []) if i.get("keyword")}
    now = cfg.now()

    all_hosts = [h for h in db.query(M.ZbxHost).all() if _is_isp(h)]
    enriched = [(h, _resolve_loc(h, cmap, amap), _provider_of(h, isp_names)) for h in all_hosts]
    providers_all = sorted({p for _, _, p in enriched})

    by_site = [r for r in enriched if not site or r[1] == site]
    rows = [r for r in by_site if not provider or r[2].lower() == provider.lower()]

    def age(h):
        return round((now - h.down_since).total_seconds() / 3600, 1) if h.down_since else None

    def item(h, loc, prov):
        return {
            "hostid": h.hostid,
            "name": h.name,
            "provider": prov,
            "loc": loc,
            "ip": h.ip or "-",
            "group": h.group_name or "-",
            "status": h.status,
            "reachable": h.status in ("up", "degraded"),
            "since": ms(h.down_since) if h.down_since else None,
            "ageH": age(h),
            "problem": h.problem or "",
        }

    # Group by provider
    p_map: dict[str, list] = {}
    for r in by_site:
        p_map.setdefault(r[2], []).append(r)
    by_provider = sorted(({"k": k, **_agg(v)} for k, v in p_map.items()), key=lambda x: (-x["down"], -x["total"], x["k"]))

    # Group by location with redundancy assessment
    l_map: dict[str, list] = {}
    for r in rows:
        l_map.setdefault(r[1], []).append(r)
    by_loc = []
    dual_sites = single_risk = site_down = 0
    for loc, v in l_map.items():
        ag = _agg(v)
        links = sorted(
            [{"provider": prov, "name": h.name, "status": h.status, "reachable": h.status in ("up", "degraded"), "ageH": age(h)} for h, _, prov in v],
            key=lambda x: (x["reachable"], x["provider"]),
        )
        if ag["total"] >= 2:
            dual_sites += 1
            if ag["online"] == 0 and ag["down"] > 0:
                red, rtone = "Site down", "crit"
                site_down += 1
            elif ag["down"] > 0:
                red, rtone = "Single-link risk", "warn"
                single_risk += 1
            else:
                red, rtone = "Dual OK", "good"
        else:
            if ag["down"] > 0:
                red, rtone = "Link down", "crit"
                site_down += 1
            else:
                red, rtone = "Single link", "idle"
        by_loc.append({"k": loc, **ag, "links": links, "redundancy": red, "rtone": rtone})
    by_loc.sort(key=lambda x: (-x["down"], 0 if x["rtone"] == "crit" else 1 if x["rtone"] == "warn" else 2, x["k"]))

    down_list = sorted(
        (item(h, loc, prov) for h, loc, prov in rows if h.status == "down"),
        key=lambda d: (d["ageH"] is None, -(d["ageH"] or 0), d["name"]),
    )

    lst = []
    if full:
        if status == "online":
            sel = [r for r in rows if r[0].status in ("up", "degraded")]
        elif status:
            sel = [r for r in rows if r[0].status == status]
        else:
            sel = list(rows)
        sel.sort(key=lambda r: (ORDER.get(r[0].status, 9), -(age(r[0]) or 0), r[1], r[2]))
        lst = [item(h, loc, prov) for h, loc, prov in sel]

    # Outage history from zbx_event for ISP-* hosts over a..b
    hist = _history(db, cfg, a, b, rows)

    src = db.get(M.DataSource, "zabbix")
    last = max((h.updated_at for h in all_hosts), default=None)
    every = (src.interval_min if src else 5) or 5
    stale = bool(last) and (datetime.utcnow() - last).total_seconds() > every * 60 * 3
    ag_all = _agg(rows)
    return {
        "all": {**ag_all, "dualSites": dual_sites, "singleRisk": single_risk, "siteDown": site_down, "providers": len(by_provider), "locations": len(by_loc)},
        "byProvider": by_provider,
        "byLoc": by_loc,
        "down": down_list,
        "downN": len(down_list),
        "list": lst,
        "listN": len(rows),
        "hist": hist,
        "opts": {"providers": providers_all},
        "updated": ms(last + (now - datetime.utcnow())) if last else None,
        "stale": stale,
        "configured": bool(src and (src.config or {}).get("base_url")),
        "enabled": bool(src and src.enabled),
        "error": src.last_error if src else None,
    }


def _history(db: Session, cfg: Config, a: date, b: date, rows: list) -> dict:
    now = cfg.now()
    t0, t1 = datetime.combine(a, _t.min), min(datetime.combine(b + timedelta(days=1), _t.min), now)
    by_id = {h.hostid: (h, loc, prov) for h, loc, prov in rows}
    daily: dict[date, list] = {}
    d = a
    while d <= b:
        daily[d] = [0, 0.0]
        d += timedelta(days=1)

    if not by_id or t1 <= t0:
        return {"from": a.isoformat(), "to": b.isoformat(), "events": 0, "hours": 0.0, "hosts": 0, "devices": len(by_id), "mttr": None, "avail": 1.0 if by_id else None,
                "daily": [{"date": x.isoformat(), "events": 0, "hours": 0.0} for x in sorted(daily)], "byProvider": [], "byLoc": [], "byHost": [], "timeline": [], "tlFrom": ms(t0), "tlTo": ms(t1)}

    evs = db.query(M.ZbxEvent).filter(M.ZbxEvent.hostid.in_(list(by_id)), M.ZbxEvent.start_at < t1, (M.ZbxEvent.end_at.is_(None)) | (M.ZbxEvent.end_at >= t0)).all()
    ov = lambda s, e, x0, x1: max(0.0, (min(e, x1) - max(s, x0)).total_seconds()) / 3600

    tot_h, n_ev, dur_closed = 0.0, 0, []
    per_prov: dict[str, list] = {}
    per_loc: dict[str, list] = {}
    per_host: dict[str, list] = {}
    tl_map: dict[str, list] = {}
    affected: set[str] = set()

    # Timeline window: last 7 days ending at t1 (or full period if <= 7d)
    tl_from = max(t0, t1 - timedelta(days=7))

    for e in evs:
        meta = by_id.get(e.hostid)
        if not meta:
            continue
        h, loc, prov = meta
        end = e.end_at or now
        hrs = ov(e.start_at, end, t0, t1)
        if hrs <= 0:
            continue
        n_ev += 1
        tot_h += hrs
        affected.add(h.hostid)
        if e.end_at:
            dur_closed.append((e.end_at - e.start_at).total_seconds() / 3600)
        for dct, k in ((per_prov, prov), (per_loc, loc), (per_host, h.name)):
            rec = dct.setdefault(k, [0, 0.0])
            rec[0] += 1
            rec[1] += hrs
        cur = max(e.start_at.date(), a)
        last_d = min(end.date(), b)
        while cur <= last_d:
            if cur in daily:
                dh = ov(e.start_at, end, datetime.combine(cur, _t.min), datetime.combine(cur + timedelta(days=1), _t.min))
                if dh > 0:
                    daily[cur][0] += 1
                    daily[cur][1] += dh
            cur += timedelta(days=1)
        if end > tl_from and e.start_at < t1:
            s_cl = max(e.start_at, tl_from)
            e_cl = min(end, t1)
            tl_map.setdefault(h.name, []).append([ms(s_cl), ms(e_cl)])

    span_h = max(1.0, (t1 - t0).total_seconds() / 3600)
    avail = max(0.0, 1.0 - tot_h / (len(by_id) * span_h)) if by_id else None

    def pack(dct, counts=None):
        out = []
        for k, (ev_c, hr) in dct.items():
            cnt = counts.get(k, 1) if counts else 1
            out.append({"k": k, "events": ev_c, "hours": round(hr, 2), "avail": max(0.0, 1.0 - hr / (cnt * span_h)) if counts else None})
        return sorted(out, key=lambda x: (-x["hours"], -x["events"], x["k"]))

    prov_cnt: dict[str, int] = {}
    loc_cnt: dict[str, int] = {}
    for _, loc, prov in rows:
        prov_cnt[prov] = prov_cnt.get(prov, 0) + 1
        loc_cnt[loc] = loc_cnt.get(loc, 0) + 1

    tl_rows = []
    for nm, segs in tl_map.items():
        mins = sum((e - s) / 60000 for s, e in segs)
        tl_rows.append({"name": nm.replace("ISP-", ""), "minutes": round(mins, 1), "events": sorted(segs)})
    tl_rows.sort(key=lambda x: -x["minutes"])

    return {
        "from": a.isoformat(),
        "to": b.isoformat(),
        "events": n_ev,
        "hours": round(tot_h, 2),
        "hosts": len(affected),
        "devices": len(by_id),
        "mttr": round(sum(dur_closed) / len(dur_closed), 2) if dur_closed else None,
        "avail": avail,
        "daily": [{"date": x.isoformat(), "events": daily[x][0], "hours": round(daily[x][1], 2)} for x in sorted(daily)],
        "byProvider": pack(per_prov, prov_cnt),
        "byLoc": pack(per_loc, loc_cnt)[:12],
        "byHost": pack(per_host)[:15],
        "timeline": tl_rows[:12],
        "tlFrom": ms(tl_from),
        "tlTo": ms(t1),
    }
