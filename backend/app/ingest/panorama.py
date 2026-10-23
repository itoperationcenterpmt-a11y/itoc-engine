"""Impor data SOC Panorama dengan validasi sebelum dipakai di KPI. RAW = CSV custom report (utama); workbook 'Impor SOC' tetap terbaca (lama).
Alamat sel, nama laporan, rentang internal, zone internet, dan daftar aplikasi diawasi dari Config."""
from datetime import date
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import SocBatch, SocDay
from ..store import Config
from ..calc.common import top_by, iso
from .excel import Workbook, pdt, s, num

GB = lambda x: x / 1e9
g1 = lambda x: round(x * 100) / 100
p1 = lambda x: round(x * 1000) / 10


def parse(data: bytes, cfg: Config) -> dict:
    xc = cfg.sources["panorama"]["config"]["excel"]
    wb = Workbook(data)
    sheet = xc.get("sheet", "Impor SOC")
    if not wb.has(sheet):
        raise ValueError(f"Sheet '{sheet}' does not exist.")
    allrows = wb.rows(sheet)
    if len(allrows) < 2:
        raise ValueError(f"Sheet '{sheet}' is empty.")
    by = {}
    for r in allrows[1:]:
        k = s(r[0])
        if k:
            by.setdefault(k, []).append(r[3:])
    pc = lambda addr: s(wb.cell(xc.get("param_sheet", "Parameter"), addr)) if addr else ""
    internal = pc(xc.get("internal_cell")) or cfg.p("soc.internal_range")
    zone = pc(xc.get("zone_cell")) or cfg.p("soc.internet_zone")
    return _build(by, cfg, xc, internal, zone)


# Header CSV custom report Panorama (RAW) → kunci laporan. Urutan kolom sama dengan sheet D-* di 3_Dashboard_SOC.xlsx.
CSV_HEADERS = {
    "threat_summary": ["day received", "severity", "threat-type", "threat category", "action", "application", "source country", "destination country", "count"],
    "url_summary": ["day received", "category", "action", "application", "count"],
    "appstats": ["day received", "application name", "bytes", "sessions"],
    "high_critical": ["source address", "source host name", "destination address", "destination host name", "source user", "application", "source zone",
                      "destination zone", "action", "severity", "threat-type", "threat_name", "threat category", "url", "count"],
    "url_blocked": ["source address", "source host name", "destination address", "destination host name", "application", "rule", "source zone",
                    "destination zone", "action", "category", "source user", "url"],
    "internal_host": ["source address", "source host name", "source user", "threat_name", "severity", "action", "destination address", "destination host name", "count"],
    "top_source": ["source address", "source host name", "source country", "severity", "count"],
    "denied": ["source address", "source host name", "source country", "destination address", "destination host name", "destination zone", "application",
               "rule", "action", "sessions", "bytes"],
    "traffic_top": ["source address", "source host name", "destination address", "destination host name", "source zone", "destination zone",
                    "destination country", "bytes", "sessions"],
    "traffic_app": ["application", "app category", "bytes", "bytes sent", "bytes received"],
    "rule_zone": ["rule", "source zone", "destination zone", "bytes", "bytes sent", "bytes received"],
}
CSV_NUMERIC = {"count", "bytes", "bytes sent", "bytes received", "sessions"}
CSV_BY_HEADER = {tuple(v): k for k, v in CSV_HEADERS.items()}


def read_csv_reports(files: list[tuple[str, bytes]]) -> tuple[dict, list[str]]:
    """RAW: kumpulan CSV Panorama → {kunci laporan: baris}. Jenis laporan dikenali dari header, bukan nama file.
    Mengembalikan (laporan, catatan file yang dilewati)."""
    import csv
    import hashlib
    from io import StringIO
    out, notes, seen = {}, [], {}
    for name, data in files:
        digest = hashlib.sha256(data).hexdigest()
        if digest in seen:  # ekspor yang sama terunggah dua kali akan menggandakan angka
            notes.append(f"{name}: identical to {seen[digest]}, not counted twice")
            continue
        seen[digest] = name
        text = data.decode("utf-8-sig", errors="replace")
        rows = list(csv.reader(StringIO(text)))
        if not rows:
            notes.append(f"{name}: empty")
            continue
        head = tuple(c.strip().lower() for c in rows[0])
        key = CSV_BY_HEADER.get(head)
        if key is None:
            notes.append(f"{name}: header not recognised ({', '.join(rows[0][:4])}…)")
            continue
        numeric = [i for i, h in enumerate(head) if h in CSV_NUMERIC]
        for r in rows[1:]:
            if not any(c.strip() for c in r):
                continue
            r = r + [""] * (len(head) - len(r))
            for i in numeric:
                r[i] = num(r[i])
            out.setdefault(key, []).append(r)
    return out, notes


def parse_csv(files: list[tuple[str, bytes]], cfg: Config) -> dict:
    xc = cfg.sources["panorama"]["config"]["excel"]
    reports, notes = read_csv_reports(files)
    if not reports:
        raise ValueError("No recognised Panorama custom report CSV. " + "; ".join(notes))
    by = {xc["reports"].get(k, k): rows for k, rows in reports.items()}
    P = _build(by, cfg, xc, cfg.p("soc.internal_range"), cfg.p("soc.internet_zone"))
    P["notes"] = notes
    P["found"] = sorted(reports)
    return P


def _build(by, cfg, xc, internal, zone):
    rep = lambda k: [r for r in by.get(xc["reports"].get(k, k), []) if s(r[0]) != ""]
    chs = set(cfg.p("soc.critical_high"))
    isCH = lambda v: s(v) in chs
    days, skipped, read = {}, 0, 0
    day = lambda d: days.setdefault(d, {"th": {}, "url": {}, "b": 0, "s": 0})

    def add(o, k, v):
        o[k] = o.get(k, 0) + v
    for key, fn in [("threat_summary", lambda d, r: add(d["th"], "|".join([s(r[1]), s(r[2]), s(r[3]), s(r[4]), "1" if s(r[6]) == internal else "0"]), num(r[8]))),
                    ("url_summary", lambda d, r: add(d["url"], s(r[1]) + "|" + ("1" if s(r[2]).lower().startswith("block") else "0"), num(r[4]))),
                    ("appstats", None)]:
        for r in rep(key):
            t = pdt(r[0])
            if t is None:
                skipped += 1
                continue
            read += 1
            d = day(iso(t))
            if fn:
                fn(d, r)
            else:
                d["b"] += num(r[2]); d["s"] += num(r[3])
    T = []
    tab = lambda id_, t, h, r, note="": T.append({"id": id_, "t": t, "h": h, "r": r, "note": note})
    ts, W = rep("top_source"), (lambda r: num(r[4]))
    tab("negara", "Top attack source countries", ["Country", "Total events", "Critical + High", "IP count"],
        [[x["k"], x["sum"], sum(W(r) for r in x["rows"] if isCH(r[3])), len({s(r[0]) for r in x["rows"]})] for x in top_by(ts, lambda r: s(r[2]), W, 10)],
        "From the Top 500 report: covers the largest sources, not all events.")
    tab("ip", "Top attack source IPs", ["Source IP", "Host name", "Country", "Total events", "Critical + High"],
        [[x["k"], s(x["first"][1]), s(x["first"][2]), x["sum"], sum(W(r) for r in x["rows"] if isCH(r[3]))] for x in top_by(ts, lambda r: s(r[0]), W, 15)])
    ih, WI = rep("internal_host"), (lambda r: num(r[8]))
    ih_top = top_by(ih, lambda r: s(r[0]), WI)
    tab("host", "Internal hosts suspected infected", ["Internal IP", "Total events", "Critical + High", "Top threat", "Action"],
        [[x["k"], x["sum"], sum(WI(r) for r in x["rows"] if isCH(r[4])), s(x["first"][3]), s(x["first"][5])] for x in ih_top[:15]],
        "Bila IP ini server DNS internal, pelaku sebenarnya adalah klien di belakangnya.")
    tab("hostch", "Critical/high detections on internal hosts", ["Internal IP", "Threat name", "Severity", "Action", "Destination", "Count"],
        [[s(r[0]), s(r[3]), s(r[4]), s(r[5]), s(r[6]), WI(r)] for r in sorted((r for r in ih if isCH(r[4])), key=lambda r: -WI(r))[:15]])
    hc = rep("high_critical")
    WH = lambda r: r[14] if len(r) > 14 and isinstance(r[14], (int, float)) else 1
    hc_tot = sum(WH(r) for r in hc)
    tab("hcaksi", "High/Critical per action", ["Action", "Event count", "% of total"],
        [[a, c, f"{p1(c / hc_tot)}%" if hc_tot else "–"] for a in cfg.p("soc.hc_actions") for c in [sum(WH(r) for r in hc if s(r[8]) == a)]],
        "The source report is limited to the top 10,000 rows.")
    tab("hcsumber", "High/Critical: top sources", ["Source IP", "Count", "Source zone", "Alert only"],
        [[x["k"], x["sum"], s(x["first"][6]), sum(WH(r) for r in x["rows"] if s(r[8]) == "alert")] for x in top_by(hc, lambda r: s(r[0]), WH, 10)])
    tab("hcalert", "High/Critical alert only (not blocked)", ["Source", "Destination", "Threat name", "Application", "Severity", "Count"],
        [[s(r[0]), s(r[2]), s(r[11]), s(r[5]), s(r[9]), WH(r)] for r in sorted((r for r in hc if s(r[8]) == "alert"), key=lambda r: -WH(r))[:12]],
        "Serious threats that were let through. Each row needs a decision: block it, or exclude it if the application is legitimate.")
    tab("hcnama", "High/Critical: top threat names", ["Threat name", "Count", "Category", "Severity"],
        [[x["k"], x["sum"], s(x["first"][12]), s(x["first"][9])] for x in top_by(hc, lambda r: s(r[11]), WH, 15)])
    ub = rep("url_blocked")
    WU = lambda r: r[12] if len(r) > 12 and isinstance(r[12], (int, float)) else 1
    tab("urlrule", "Blocked URLs: most targeted rules", ["Rule", "Count", "Top category"], [[x["k"], x["sum"], s(x["first"][9])] for x in top_by(ub, lambda r: s(r[5]), WU, 10)])
    tab("urlsrc", "Blocked URLs: top sources", ["Source IP", "Count", "Source zone", "Rule"], [[x["k"], x["sum"], s(x["first"][6]), s(x["first"][5])] for x in top_by(ub, lambda r: s(r[0]), WU, 10)])
    tab("url", "Blocked URLs: top URLs", ["URL", "Count", "Category"], [[x["k"][:90], x["sum"], s(x["first"][9])] for x in top_by(ub, lambda r: s(r[11]), WU, 10)])
    ap = rep("traffic_app")
    ap_tot = sum(num(r[2]) for r in ap)
    apS = sorted(ap, key=lambda r: -num(r[2]))
    pct = lambda v: f"{p1(v / ap_tot)}%" if ap_tot else "–"
    tab("app", "Top applications by volume", ["Application", "Category", "Volume (GB)", "% of total", "Sent (GB)", "Received (GB)"],
        [[s(r[0]), s(r[1]), g1(GB(num(r[2]))), pct(num(r[2])), g1(GB(num(r[3]))), g1(GB(num(r[4])))] for r in apS[:15]])
    tab("appcat", "Volume per application category", ["Application category", "Volume (GB)", "% of total", "Application count"],
        [[x["k"], g1(GB(x["sum"])), pct(x["sum"]), len(x["rows"])] for x in top_by(ap, lambda r: s(r[1]), lambda r: num(r[2]), 10)])
    wrows = []
    for a in cfg.p("soc.watch_apps"):
        L = [r for r in ap if s(r[0]) == a]
        wrows.append([a, g1(GB(sum(num(r[2]) for r in L))), g1(GB(sum(num(r[3]) for r in L))), g1(GB(sum(num(r[4]) for r in L))), "Ya" if L else "–"])
    tab("watch", "Applications to watch", ["Application", "Volume (GB)", "Sent (GB)", "Received (GB)", "Seen?"], wrows,
        "File sharing, remote access, VPN/anonymizers, and unencrypted protocols.")
    rz = rep("rule_zone")
    rz_tot = sum(num(r[3]) for r in rz)
    rzS = sorted(rz, key=lambda r: -num(r[3]))
    tab("rule", "Top rules and zones by volume", ["Rule", "Source zone", "Destination zone", "Volume (GB)", "% of total"],
        [[s(r[0]) or "(unnamed)", s(r[1]), s(r[2]), g1(GB(num(r[3]))), f"{p1(num(r[3]) / rz_tot)}%" if rz_tot else "–"] for r in rzS[:15]])
    tab("inbound", "Services open from the internet", ["Rule", "Destination zone", "Volume (GB)", "Outbound volume from inside (GB)"],
        [[s(r[0]) or "(unnamed)", s(r[2]), g1(GB(num(r[3]))), g1(GB(num(r[5])))] for r in [r for r in rzS[:30] if s(r[1]) == zone and s(r[2]) != zone][:15]],
        "Inbound traffic from the internet zone to the inside, from the 30 rows with the largest volume.")
    tt = rep("traffic_top")
    tab("talker", "Top source–destination pairs", ["Source", "Destination", "Destination host", "Destination zone", "Destination country", "Volume (GB)", "Sessions"],
        [[s(r[0]), s(r[2]), s(r[3]), s(r[5]), s(r[6]), g1(GB(num(r[7]))), num(r[8])] for r in sorted(tt, key=lambda r: -num(r[7]))[:15]])
    tab("trsrc", "Top traffic sources", ["Source", "Volume (GB)", "Sessions", "Destination count"],
        [[x["k"], g1(GB(x["sum"])), sum(num(r[8]) for r in x["rows"]), len(x["rows"])] for x in top_by(tt, lambda r: s(r[0]), lambda r: num(r[7]), 10)])
    dn = rep("denied")
    pr = lambda v: f"{p1(v / len(dn))}%" if dn else "–"
    tab("denaksi", "Denied traffic per action", ["Action", "Row count", "Session count"],
        [[x["k"], x["sum"], sum(num(r[9]) for r in x["rows"])] for x in top_by(dn, lambda r: s(r[8]), lambda r: 1)],
        "The size is the number of source–destination–application–rule combinations, not the number of sessions. Source: Top 500 report.")
    tab("denrule", "Denied traffic: top rules", ["Rule", "Row count", "% of rows"], [[x["k"], x["sum"], pr(x["sum"])] for x in top_by(dn, lambda r: s(r[7]), lambda r: 1, 10)])
    tab("denapp", "Denied traffic: top applications", ["Application", "Row count", "% of rows", "Top rule"],
        [[x["k"], x["sum"], pr(x["sum"]), s(x["first"][7])] for x in top_by(dn, lambda r: s(r[6]), lambda r: 1, 10)])
    tab("densrc", "Denied traffic: top sources", ["Source", "Row count", "Country / network", "Application (first row)"],
        [[x["k"], x["sum"], s(x["first"][2]), s(x["first"][6])] for x in top_by(dn, lambda r: s(r[0]), lambda r: 1, 10)])
    K = {"hosts": len(ih_top), "hostsCH": sum(1 for x in ih_top if any(isCH(r[4]) for r in x["rows"])), "trafficTB": ap_tot / 1e12,
         "topApp": s(apS[0][0]) if apS else "", "topAppPct": num(apS[0][2]) / ap_tot if apS and ap_tot else 0, "watchSeen": sum(1 for r in wrows if r[4] == "Ya"),
         "inboundRules": sum(1 for r in rz if s(r[1]) == zone and s(r[2]) != zone and num(r[3]) > 0), "hcCovered": hc_tot}
    ds = sorted(days)
    present = [k for k in xc["top_reports"] if rep(k)]
    return {"from": ds[0] if ds else None, "to": ds[-1] if ds else None, "days": days, "tables": [t for t in T if t["r"]], "K": K if present else None,
            "read": read, "skipped": skipped, "top_present": present}


def _compare_api(db: Session, P: dict, tol: float = 0.03) -> list[dict]:
    """Validasi: hari yang sudah diisi dari Panorama API dibandingkan dengan CSV manual (event ancaman, event URL, volume). Hanya selisih di atas toleransi yang dicatat."""
    keys = [date.fromisoformat(k) for k in P["days"]]
    if not keys:
        return []
    rows = db.execute(select(SocDay, SocBatch.file_name).join(SocBatch).where(SocBatch.status != "failed", SocBatch.file_name.like("Panorama API%"), SocDay.day.in_(keys))).all()
    out, bad = [], 0
    for sd, _ in rows:
        n = P["days"][sd.day.isoformat()]
        pairs = [("ancaman", sum((sd.threats or {}).values()), sum(n["th"].values())), ("URL", sum((sd.urls or {}).values()), sum(n["url"].values())), ("volume (GB)", (sd.bytes or 0) / 1e9, n["b"] / 1e9)]
        diff = [(lbl, a, b) for lbl, a, b in pairs if max(a, b) > 0 and abs(a - b) / max(a, b) > tol]
        if diff:
            bad += 1
            if len(out) < 6:
                out.append({"k": "warn", "t": f"{sd.day.isoformat()}: " + "; ".join(f"{lbl} API {a:,.0f} vs CSV {b:,.0f}".replace(",", ".") for lbl, a, b in diff)})
    if bad:
        out.insert(0, {"k": "warn", "t": f"Validation against Panorama API data: {bad} of {len(rows)} overlapping days differ by more than {tol * 100:.0f}%. The manual CSV is used."})
    return out


def import_file(db: Session, cfg: Config, data: bytes, file_name: str, username: str, d_from: date | None = None, d_to: date | None = None,
                files: list[tuple[str, bytes]] | None = None) -> SocBatch:
    """Validasi lalu simpan. Batch gagal tetap tersimpan (untuk riwayat), tetapi tidak dipakai di KPI.
    `files` = CSV RAW Panorama (beberapa laporan sekaligus); tanpa itu, `data` dibaca sebagai workbook 3_Dashboard_SOC.xlsx."""
    P = parse_csv(files, cfg) if files is not None else parse(data, cfg)
    issues = [{"k": "warn", "t": "Files skipped: " + n} for n in P.get("notes", [])]
    if P["skipped"]:
        issues.append({"k": "crit", "t": f"{P['skipped']:,} daily summary rows skipped: the Time column could not be read as a Panorama export date.".replace(",", ".")})
    if not P["days"]:
        issues.append({"k": "crit", "t": "No daily summary rows with a readable date."})
    missing = [k for k in cfg.sources["panorama"]["config"]["excel"]["top_reports"] if k not in P["top_present"]]
    if missing:
        issues.append({"k": "warn", "t": "Top report not uploaded: " + ", ".join(missing) + ". Period tables are not available."})
    f, t = P["from"], P["to"]
    f = date.fromisoformat(f) if f else d_from or date.today()
    t = date.fromisoformat(t) if t else d_to or f
    overlap = [iso(x.day) for x in db.scalars(select(SocDay).join(SocBatch).where(SocBatch.status != "failed", SocDay.day.in_([date.fromisoformat(k) for k in P["days"]])))]
    if overlap:
        issues.append({"k": "warn", "t": f"Dates {', '.join(sorted(set(overlap)))} are also in an earlier batch. The latest batch is used so nothing is counted twice."})
    issues += _compare_api(db, P)
    status = "failed" if any(i["k"] == "crit" for i in issues) else "warn" if issues else "valid"
    b = SocBatch(file_name=file_name, uploaded_by=username, uploaded_at=cfg.now(), date_from=f, date_to=t, rows_read=P["read"], rows_skipped=P["skipped"],
                 status=status, issues=issues, tables=P["tables"], kpi=P["K"])
    for k, v in P["days"].items():
        b.days.append(SocDay(day=date.fromisoformat(k), threats=v["th"], urls=v["url"], bytes=int(v["b"]), sessions=int(v["s"])))
    db.add(b)
    return b
