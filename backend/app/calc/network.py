"""NOC — agregasi PRTG per jam dari database (buildNet) + perhitungan SLA link (netCalc,
sheet Perhitungan 2_Dashboard_Network_SLA). Target, cakupan minimal, ambang utilisasi, ISP, dan kelompok
availability berasal dari Config."""
from datetime import datetime, date, timedelta
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session
from ..models import PrtgSensor, PrtgHourly, PrtgEvent, PrtgDaily
from ..store import Config
from ..timeutil import ms
from .common import iso, top_by


def device_names(db: Session, site: str) -> list[str]:
    """Nama device PRTG yang dianggap lokasi ini: nama site, alias di master Lokasi, dan nama tanpa awalan "Branch " (huruf kecil)."""
    from ..models import Site
    names = {site.lower(), site.lower().removeprefix("branch ").strip()}
    s = db.query(Site).filter_by(name=site).first()
    for al in (s.aliases or []) if s else []:
        names.add(al.lower().strip())
    return sorted(n for n in names if n)


def site_resolver(db: Session):
    """Function (code, zone, ...) -> master location, shared by systems that name things differently (WiFi AP code and zone, Zabbix code): Admin > Mapping Zabbix codes first, then site names and aliases. None when nothing matches."""
    from ..models import Site, ZbxLocMap
    cmap = {m.code.lower(): m.site for m in db.query(ZbxLocMap) if m.site}
    amap: dict = {}
    for s in db.query(Site).filter_by(active=True):
        for n in device_names(db, s.name):
            amap.setdefault(n, s.name)

    def to_site(*tokens):
        for t in tokens:
            k = (t or "").strip().lower()
            for v in (k, k.replace("_", " ")):
                if v and (cmap.get(v) or amap.get(v)):
                    return cmap.get(v) or amap.get(v)
        return None
    return to_site


def shared_isp(db: Session, site: str) -> list[str]:
    """Locations that use the same ISP links (parameter net.shared_isp, e.g. Head Office and Belawan): choosing one shows the links of all. Tickets and WiFi are not affected."""
    from ..models import Parameter
    p = db.get(Parameter, "net.shared_isp")
    for g in (p.value if p else [["Head Office", "Branch Belawan"]]) or []:
        if site in g:
            return list(g)
    return [site]


def site_cond(db: Session, site: str):
    """Sensor milik lokasi: device PRTG cocok dengan nama/alias lokasi, ATAU kode di awal nama sensor ("MDN - Astinet" -> "mdn") ada di alias lokasi. Tidak peka huruf besar/kecil."""
    names = sorted({n for x in shared_isp(db, site) for n in device_names(db, x)})
    code = func.regexp_replace(func.lower(PrtgSensor.name), r"^\s*([a-z0-9]+).*$", r"\1")
    return or_(func.lower(PrtgSensor.device).in_(names), code.in_(names))


def _bounds(cfg: Config, d_from: date, d_to: date):
    start = datetime.fromisoformat(cfg.p("data_start"))
    now_h = cfg.now().replace(minute=0, second=0)
    a = max(start, datetime.combine(d_from, datetime.min.time()))
    b = min(now_h, datetime.combine(d_to, datetime.min.time()) + timedelta(days=1))
    return a, b


def build(db: Session, cfg: Config, d_from: date, d_to: date, shift: int = 0, site: str = "") -> dict:
    a, b = _bounds(cfg, d_from, d_to)
    q = select(PrtgSensor).where(PrtgSensor.active.is_(True))
    if site:
        q = q.where(site_cond(db, site))
    sensors = list(db.scalars(q.order_by(PrtgSensor.id)))
    clk = cfg.clock
    hours = []
    t = a
    while t < b:
        if not shift or clk.shift_of(t.hour) == shift:
            hours.append(t)
        t += timedelta(hours=1)
    hidx = {h: j for j, h in enumerate(hours)}
    ids = [s.id for s in sensors]
    data = {}
    if ids and hours:
        for r in db.execute(select(PrtgHourly).where(PrtgHourly.sensor_id.in_(ids), PrtgHourly.ts >= a, PrtgHourly.ts < b)).scalars():
            if r.ts in hidx:
                data[(r.sensor_id, r.ts)] = r
    # Ringkasan harian dari unggahan RAW (PDF): hanya untuk hari penuh yang sensornya tidak punya data per jam, dan tanpa filter shift (PDF tidak memuat jam).
    daily = {}
    if ids and hours and not shift:
        d0, d1 = a.date(), (b - timedelta(seconds=1)).date()
        for r in db.execute(select(PrtgDaily).where(PrtgDaily.sensor_id.in_(ids), PrtgDaily.day >= d0, PrtgDaily.day <= d1)).scalars():
            if datetime.combine(r.day, datetime.min.time()) >= a and datetime.combine(r.day, datetime.min.time()) + timedelta(days=1) <= b:
                daily.setdefault(r.sensor_id, {})[iso(r.day)] = r
    dayhit = 0
    tin, tout, tseen, ttot = [0.0] * len(hours), [0.0] * len(hours), [0] * len(hours), [0.0] * len(hours)
    out, harian = [], []
    for s in sensors:
        up = dn = sm = si = so = mx = vol = 0.0
        n = 0
        rg = rf = 0.0
        dd = {}
        for j, h in enumerate(hours):
            x = dd.setdefault(iso(h), {"m": 0.0, "h": 0, "t": 0.0})
            r = data.get((s.id, h))
            if r is None or not r.seen:
                continue
            ii, oo, dw = r.in_mbps or 0, r.out_mbps or 0, r.down_s or 0
            tt = ii + oo
            up += 3600 - dw; dn += dw; sm += tt; si += ii; so += oo; n += 1; mx = max(mx, tt); vol += tt * 3600 / 8
            x["m"] += dw / 60; x["h"] += 1; x["t"] += tt
            tin[j] += ii; tout[j] += oo; tseen[j] += 1; ttot[j] += tt
        upH, dnH = up, dn
        for k, r in daily.get(s.id, {}).items():
            if dd.get(k, {}).get("h"):
                continue  # hari ini sudah punya data per jam (API): jangan dihitung dua kali
            heq = (r.up_s + r.down_s) / 3600
            tt = r.avg_total or 0
            up += r.up_s; dn += r.down_s; sm += tt * heq; n += heq; mx = max(mx, r.max_mbps or 0)
            si += (r.avg_in or 0) * heq; so += (r.avg_out or 0) * heq
            vol += r.vol_total_mb if r.vol_total_mb is not None else tt * 3600 * heq / 8
            rg += r.req_good or 0; rf += r.req_fail or 0
            dd[k] = {"m": r.down_s / 60, "h": max(1, round(heq)), "t": tt * max(1, round(heq))}
            for j, h in enumerate(hours):
                if iso(h) == k:
                    ttot[j] += tt; tseen[j] += 1
            dayhit += 1 if r.down_s > 0 else 0
        out.append({"id": s.id, "name": s.name, "dev": s.device, "up": up, "down": dn, "good": round(upH / 60) + round(rg), "fail": round(dnH / 60) + round(rf),
                    "avg": round(sm / n, 2) if n else 0, "vol": round(vol), "max": round(mx, 2), "cap": s.capacity_mbps,
                    "avgIn": si / n if n else 0, "avgOut": so / n if n else 0})
        for k, x in dd.items():
            harian.append([s.id, k, round(x["m"], 1), x["h"], round(x["t"] / x["h"], 2) if x["h"] else None])
    hset = set(hours)
    kej = []
    if ids:
        for e in db.scalars(select(PrtgEvent).where(PrtgEvent.sensor_id.in_(ids), PrtgEvent.end_at > a, PrtgEvent.start_at < b)):
            st, en = max(e.start_at, a), min(e.end_at, b)
            if st.replace(minute=0, second=0) in hset:
                kej.append([e.sensor_id, st, en, round((en - st).total_seconds() / 6) / 10])
    kej.sort(key=lambda k: -k[3])
    N = {"from": a, "to": b, "hours": len(hours), "P": cfg.net_params(), "sensors": out, "harian": harian, "kej": kej, "dayhit": dayhit}
    return {"N": N, "hourly": {"k": [ms(h) for h in hours], "tin": tin, "tout": tout, "ttot": ttot, "tseen": tseen}}


def series(db: Session, cfg: Config, sensor_id: str, d_from: date, d_to: date, shift: int = 0) -> dict | None:
    if not sensor_id or not db.get(PrtgSensor, sensor_id):
        return None
    a, b = _bounds(cfg, d_from, d_to)
    rows = {r.ts: r for r in db.scalars(select(PrtgHourly).where(PrtgHourly.sensor_id == sensor_id, PrtgHourly.ts >= a, PrtgHourly.ts < b))}
    res = {"t": [], "i": [], "o": [], "a": [], "d": []}
    day_avg = {iso(r.day): r for r in db.scalars(select(PrtgDaily).where(PrtgDaily.sensor_id == sensor_id, PrtgDaily.day >= a.date(), PrtgDaily.day <= b.date()))}
    t = a
    while t < b:
        if not shift or cfg.clock.shift_of(t.hour) == shift:
            r = rows.get(t)
            ok = r is not None and r.seen
            dr = None if ok else day_avg.get(iso(t))      # jam tanpa data API: pakai rata-rata harian dari PDF
            res["t"].append(ms(t)); res["i"].append(r.in_mbps if ok else None); res["o"].append(r.out_mbps if ok else None)
            res["a"].append((r.in_mbps or 0) + (r.out_mbps or 0) if ok else (dr.avg_total if dr else None)); res["d"].append(r.down_s if r else 0)
        t += timedelta(hours=1)
    return res


def coverage(db: Session, cfg: Config, day: date, site: str = "") -> dict:
    """Jam-sensor yang terpantau ÷ jam-sensor yang diharapkan pada satu hari."""
    a = datetime.combine(day, datetime.min.time())
    b = min(a + timedelta(days=1), cfg.now().replace(minute=0, second=0))
    q = select(PrtgSensor.id).where(PrtgSensor.active.is_(True))
    if site:
        q = q.where(site_cond(db, site))
    ids = list(db.scalars(q))
    exp = len(ids) * max(0, int((b - a).total_seconds() // 3600))
    if not exp:
        return {"seen": 0, "exp": 0}
    seen = db.query(PrtgHourly).filter(PrtgHourly.sensor_id.in_(ids), PrtgHourly.ts >= a, PrtgHourly.ts < b, PrtgHourly.seen.is_(True)).count()
    per = int((b - a).total_seconds() // 3600)
    hourly_ids = {r[0] for r in db.query(PrtgHourly.sensor_id).filter(PrtgHourly.sensor_id.in_(ids), PrtgHourly.ts >= a, PrtgHourly.ts < b, PrtgHourly.seen.is_(True)).distinct()}
    for r in db.query(PrtgDaily).filter(PrtgDaily.sensor_id.in_(ids), PrtgDaily.day == day):
        if r.sensor_id not in hourly_ids:  # unggahan RAW harian mengisi hari yang kosong dari API
            seen += min(per, round((r.up_s + r.down_s) / 3600))
    return {"seen": seen, "exp": exp}


def calc(N: dict, cfg: Config) -> dict | None:
    if not N["hours"]:
        return None
    P = N["P"]
    perH = N["hours"]
    buckets = cfg.p("net.av_buckets")
    S = []
    for s in N["sensors"]:
        hit = next((i for i in P["isps"] if i["kw"].lower() in s["name"].lower()), None)
        isp = hit["name"] if hit else cfg.p("net.other_isp_label")
        tot = s["up"] + s["down"]
        av = s["up"] / tot if tot else None
        cov = tot / (perH * 3600) if perH else 0
        target = hit["target"] if hit and hit["target"] is not None else P["target"]
        st = cfg.p("net.status_labels")
        status = st["nodata"] if (av is None or cov < P["minCov"]) else st["ok"] if av >= target else st["bad"]
        bucket = None if av is None else next((i for i, bk in enumerate(buckets) if av >= bk["min"]), len(buckets) - 1)
        cap = s["cap"]
        S.append({**s, "isp": isp, "link": s["dev"] + " – " + isp, "monH": tot / 3600, "downMin": s["down"] / 60, "av": av, "cov": cov,
                  "target": target, "status": status, "sisa": (1 - target) * tot / 60 - s["down"] / 60,
                  "failPct": s["fail"] / (s["good"] + s["fail"]) if s["good"] + s["fail"] else 0, "bucket": bucket,
                  "uA": s["avg"] / cap if cap else None, "uP": s["max"] / cap if cap else None})
    st = cfg.p("net.status_labels")
    n = len(S)
    U, Dn = sum(s["up"] for s in S), sum(s["down"] for s in S)
    cs = lambda k: sum(1 for s in S if s["status"] == st[k])
    R = {"n": n, "from": ms(N["from"]), "to": ms(N["to"]), "P": P, "links": n, "avail": U / (U + Dn) if U + Dn else None, "ok": cs("ok"), "bad": cs("bad"),
         "nodata": cs("nodata"), "downH": Dn / 3600, "noDown": sum(1 for s in S if s["down"] == 0),
         "cov": sum(s["monH"] for s in S) / (n * perH) if n and perH else 0, "mbps": sum(s["avg"] for s in S), "volTB": sum(s["vol"] for s in S) / 1e6,
         "utilHigh": sum(1 for s in S if s["uP"] is not None and s["uP"] >= P["utilPeak"]),
         "utilAvgHigh": sum(1 for s in S if s["uA"] is not None and s["uA"] >= P["utilAvg"]), "noCap": sum(1 for s in S if not s["cap"])}
    R["okPct"] = R["ok"] / (R["ok"] + R["bad"]) if R["ok"] + R["bad"] else 0

    def grp(L, extra):
        u, d = sum(s["up"] for s in L), sum(s["down"] for s in L)
        ok, bad = sum(1 for s in L if s["status"] == st["ok"]), sum(1 for s in L if s["status"] == st["bad"])
        return {"n": len(L), "av": u / (u + d) if u + d else None, "downH": d / 3600, "ok": ok, "bad": bad,
                "nodata": sum(1 for s in L if s["status"] == st["nodata"]), "okPct": ok / (ok + bad) if ok + bad else None,
                "mbps": sum(s["avg"] for s in L), "volGB": sum(s["vol"] for s in L) / 1000, **extra}
    names = list(dict.fromkeys([i["name"] for i in P["isps"]] + [cfg.p("net.other_isp_label")]))
    R["isp"] = []
    for nm in names:
        L = [s for s in S if s["isp"] == nm]
        if not L:
            continue
        hit = next((i for i in P["isps"] if i["name"] == nm), None)
        R["isp"].append(grp(L, {"k": nm, "target": hit["target"] if hit and hit["target"] is not None else P["target"]}))
    lab = cfg.p("net.same_labels")
    tol = cfg.p("net.same_tolerance_min")
    R["lokasi"] = []
    for x in top_by(S, lambda s: s["dev"], lambda s: 0):
        L = x["rows"]
        dm = [s["down"] / 60 for s in L]
        g = grp(L, {"k": x["k"]})
        g["downMin"], g["maxMin"], g["minMin"] = sum(dm), max(dm), min(dm)
        avs = [s["av"] for s in L if s["av"] is not None]
        g["minAv"] = min(avs) if avs else None
        g["same"] = (lab["single"] if len(L) < 2 else lab["nocmp"] if g["nodata"] > 0 else lab["nodown"] if g["maxMin"] == 0
                     else lab["yes"] if g["maxMin"] - g["minMin"] <= tol else lab["no"])
        R["lokasi"].append(g)
    R["sameYes"] = sum(1 for x in R["lokasi"] if x["same"] == lab["yes"])
    R["sameCmp"] = R["sameYes"] + sum(1 for x in R["lokasi"] if x["same"] == lab["no"])
    R["locations"] = len(R["lokasi"])
    R["lokasiTop"] = sorted(R["lokasi"], key=lambda x: -x["downMin"])[:10]
    rank = [s for _, s in sorted(enumerate(S), key=lambda p: (-p[1]["down"], p[0]))]
    for s in rank:
        s["rank"] = 1 + sum(1 for y in S if y["down"] > s["down"])
    R["rank"], R["worst"] = rank, (rank[0] if rank else None)
    R["unmappedIsp"] = [s["name"] for s in S if s["isp"] == cfg.p("net.other_isp_label")][:10]  # nama sensor belum cocok dengan kata kunci ISP mana pun
    R["buckets"] = [{"k": bk["label"], "n": c, "pct": c / n if n else 0} for i, bk in enumerate(buckets) for c in [sum(1 for s in S if s["bucket"] == i)]]
    R["traffic"] = sorted(S, key=lambda s: -s["avg"])[:10]
    ul = cfg.p("net.util_labels")
    R["util"] = [{**s, "ust": ul["peak"] if s["uP"] >= P["utilPeak"] else ul["avg"] if s["uA"] >= P["utilAvg"] else ul["ok"]}
                 for s in sorted((s for s in S if s["uP"] is not None), key=lambda s: -s["uP"])[:15]]
    link = {s["id"]: s["link"] for s in S}
    by_day = {}
    for h in N["harian"]:
        by_day.setdefault(h[1], []).append(h)
    R["daily"] = []
    t = N["from"].replace(hour=0)
    while t < N["to"]:
        L = by_day.get(iso(t), [])
        R["daily"].append({"date": iso(t), "down": sum(h[2] for h in L), "hit": sum(1 for h in L if h[2] > 0), "mbps": sum(h[4] or 0 for h in L),
                           "seen": sum(1 for h in L if h[3] > 0)})
        t += timedelta(days=1)
    wd = max(R["daily"], key=lambda x: x["down"], default=None)
    R["worstDay"] = wd if wd and wd["down"] > 0 else None
    R["daysHit"] = sum(1 for x in R["daily"] if x["hit"] > 0)
    R["events"] = len(N["kej"]) + N.get("dayhit", 0)  # link-hari dari PDF harian dihitung sebagai satu kejadian (jam tidak diketahui)
    R["kej"] = [{"link": link.get(k[0], k[0]), "start": ms(k[1]), "end": ms(k[2]), "min": k[3]} for k in N["kej"][:20]]
    return R
