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
        raise ValueError(f"Sheet '{sheet}' tidak ada.")
    allrows = wb.rows(sheet)
    if len(allrows) < 2:
        raise ValueError(f"Sheet '{sheet}' kosong.")
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
            notes.append(f"{name}: isinya sama persis dengan {seen[digest]}, tidak dihitung dua kali")
            continue
        seen[digest] = name
        text = data.decode("utf-8-sig", errors="replace")
        rows = list(csv.reader(StringIO(text)))
        if not rows:
            notes.append(f"{name}: kosong")
            continue
        head = tuple(c.strip().lower() for c in rows[0])
        key = CSV_BY_HEADER.get(head)
        if key is None:
            notes.append(f"{name}: header tidak dikenali ({', '.join(rows[0][:4])}…)")
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
        raise ValueError("Tidak ada CSV custom report Panorama yang dikenali. " + "; ".join(notes))
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
    tab("negara", "Negara sumber serangan teratas", ["Negara", "Total event", "Critical + High", "Jumlah IP"],
        [[x["k"], x["sum"], sum(W(r) for r in x["rows"] if isCH(r[3])), len({s(r[0]) for r in x["rows"]})] for x in top_by(ts, lambda r: s(r[2]), W, 10)],
        "Dari laporan Top 500: mencakup sumber terbesar, bukan seluruh event.")
    tab("ip", "IP sumber serangan teratas", ["IP sumber", "Host name", "Negara", "Total event", "Critical + High"],
        [[x["k"], s(x["first"][1]), s(x["first"][2]), x["sum"], sum(W(r) for r in x["rows"] if isCH(r[3]))] for x in top_by(ts, lambda r: s(r[0]), W, 15)])
    ih, WI = rep("internal_host"), (lambda r: num(r[8]))
    ih_top = top_by(ih, lambda r: s(r[0]), WI)
    tab("host", "Host internal terindikasi terinfeksi", ["IP internal", "Total event", "Critical + High", "Ancaman terbanyak", "Tindakan"],
        [[x["k"], x["sum"], sum(WI(r) for r in x["rows"] if isCH(r[4])), s(x["first"][3]), s(x["first"][5])] for x in ih_top[:15]],
        "Bila IP ini server DNS internal, pelaku sebenarnya adalah klien di belakangnya.")
    tab("hostch", "Deteksi critical/high pada host internal", ["IP internal", "Nama ancaman", "Severity", "Tindakan", "Tujuan", "Count"],
        [[s(r[0]), s(r[3]), s(r[4]), s(r[5]), s(r[6]), WI(r)] for r in sorted((r for r in ih if isCH(r[4])), key=lambda r: -WI(r))[:15]])
    hc = rep("high_critical")
    WH = lambda r: r[14] if len(r) > 14 and isinstance(r[14], (int, float)) else 1
    hc_tot = sum(WH(r) for r in hc)
    tab("hcaksi", "High/Critical per tindakan", ["Tindakan", "Jumlah event", "% dari total"],
        [[a, c, f"{p1(c / hc_tot)}%" if hc_tot else "–"] for a in cfg.p("soc.hc_actions") for c in [sum(WH(r) for r in hc if s(r[8]) == a)]],
        "Laporan sumber dibatasi 10.000 baris teratas.")
    tab("hcsumber", "High/Critical: sumber teratas", ["IP sumber", "Jumlah", "Zone sumber", "Hanya alert"],
        [[x["k"], x["sum"], s(x["first"][6]), sum(WH(r) for r in x["rows"] if s(r[8]) == "alert")] for x in top_by(hc, lambda r: s(r[0]), WH, 10)])
    tab("hcalert", "High/Critical yang hanya alert (tidak diblokir)", ["Sumber", "Tujuan", "Nama ancaman", "Aplikasi", "Severity", "Count"],
        [[s(r[0]), s(r[2]), s(r[11]), s(r[5]), s(r[9]), WH(r)] for r in sorted((r for r in hc if s(r[8]) == "alert"), key=lambda r: -WH(r))[:12]],
        "Ancaman serius yang dibiarkan lewat. Tiap baris perlu diputuskan: diblokir, atau dikecualikan bila aplikasinya sah.")
    tab("hcnama", "High/Critical: nama ancaman teratas", ["Nama ancaman", "Jumlah", "Kategori", "Severity"],
        [[x["k"], x["sum"], s(x["first"][12]), s(x["first"][9])] for x in top_by(hc, lambda r: s(r[11]), WH, 15)])
    ub = rep("url_blocked")
    WU = lambda r: r[12] if len(r) > 12 and isinstance(r[12], (int, float)) else 1
    tab("urlrule", "URL diblokir: rule yang paling sering dituju", ["Rule", "Jumlah", "Kategori terbanyak"], [[x["k"], x["sum"], s(x["first"][9])] for x in top_by(ub, lambda r: s(r[5]), WU, 10)])
    tab("urlsrc", "URL diblokir: sumber teratas", ["IP sumber", "Jumlah", "Zone sumber", "Rule"], [[x["k"], x["sum"], s(x["first"][6]), s(x["first"][5])] for x in top_by(ub, lambda r: s(r[0]), WU, 10)])
    tab("url", "URL diblokir: URL teratas", ["URL", "Jumlah", "Kategori"], [[x["k"][:90], x["sum"], s(x["first"][9])] for x in top_by(ub, lambda r: s(r[11]), WU, 10)])
    ap = rep("traffic_app")
    ap_tot = sum(num(r[2]) for r in ap)
    apS = sorted(ap, key=lambda r: -num(r[2]))
    pct = lambda v: f"{p1(v / ap_tot)}%" if ap_tot else "–"
    tab("app", "Aplikasi teratas menurut volume", ["Aplikasi", "Kategori", "Volume (GB)", "% dari total", "Dikirim (GB)", "Diterima (GB)"],
        [[s(r[0]), s(r[1]), g1(GB(num(r[2]))), pct(num(r[2])), g1(GB(num(r[3]))), g1(GB(num(r[4])))] for r in apS[:15]])
    tab("appcat", "Volume per kategori aplikasi", ["Kategori aplikasi", "Volume (GB)", "% dari total", "Jumlah aplikasi"],
        [[x["k"], g1(GB(x["sum"])), pct(x["sum"]), len(x["rows"])] for x in top_by(ap, lambda r: s(r[1]), lambda r: num(r[2]), 10)])
    wrows = []
    for a in cfg.p("soc.watch_apps"):
        L = [r for r in ap if s(r[0]) == a]
        wrows.append([a, g1(GB(sum(num(r[2]) for r in L))), g1(GB(sum(num(r[3]) for r in L))), g1(GB(sum(num(r[4]) for r in L))), "Ya" if L else "–"])
    tab("watch", "Aplikasi yang perlu diawasi", ["Aplikasi", "Volume (GB)", "Dikirim (GB)", "Diterima (GB)", "Terlihat?"], wrows,
        "Berbagi file, remote access, VPN/anonimizer, dan protokol tanpa enkripsi.")
    rz = rep("rule_zone")
    rz_tot = sum(num(r[3]) for r in rz)
    rzS = sorted(rz, key=lambda r: -num(r[3]))
    tab("rule", "Rule dan zone teratas menurut volume", ["Rule", "Zone sumber", "Zone tujuan", "Volume (GB)", "% dari total"],
        [[s(r[0]) or "(tanpa nama)", s(r[1]), s(r[2]), g1(GB(num(r[3]))), f"{p1(num(r[3]) / rz_tot)}%" if rz_tot else "–"] for r in rzS[:15]])
    tab("inbound", "Layanan yang terbuka dari internet", ["Rule", "Zone tujuan", "Volume (GB)", "Volume keluar dari dalam (GB)"],
        [[s(r[0]) or "(tanpa nama)", s(r[2]), g1(GB(num(r[3]))), g1(GB(num(r[5])))] for r in [r for r in rzS[:30] if s(r[1]) == zone and s(r[2]) != zone][:15]],
        "Trafik masuk dari zone internet ke dalam, dari 30 baris volume terbesar.")
    tt = rep("traffic_top")
    tab("talker", "Pasangan sumber–tujuan teratas", ["Sumber", "Tujuan", "Host tujuan", "Zone tujuan", "Negara tujuan", "Volume (GB)", "Sesi"],
        [[s(r[0]), s(r[2]), s(r[3]), s(r[5]), s(r[6]), g1(GB(num(r[7]))), num(r[8])] for r in sorted(tt, key=lambda r: -num(r[7]))[:15]])
    tab("trsrc", "Sumber trafik teratas", ["Sumber", "Volume (GB)", "Sesi", "Jumlah tujuan"],
        [[x["k"], g1(GB(x["sum"])), sum(num(r[8]) for r in x["rows"]), len(x["rows"])] for x in top_by(tt, lambda r: s(r[0]), lambda r: num(r[7]), 10)])
    dn = rep("denied")
    pr = lambda v: f"{p1(v / len(dn))}%" if dn else "–"
    tab("denaksi", "Trafik yang ditolak per tindakan", ["Tindakan", "Jumlah baris", "Jumlah sesi"],
        [[x["k"], x["sum"], sum(num(r[9]) for r in x["rows"])] for x in top_by(dn, lambda r: s(r[8]), lambda r: 1)],
        "Ukurannya jumlah kombinasi sumber–tujuan–aplikasi–rule, bukan jumlah sesi. Laporan sumber Top 500.")
    tab("denrule", "Trafik ditolak: rule teratas", ["Rule", "Jumlah baris", "% dari baris"], [[x["k"], x["sum"], pr(x["sum"])] for x in top_by(dn, lambda r: s(r[7]), lambda r: 1, 10)])
    tab("denapp", "Trafik ditolak: aplikasi teratas", ["Aplikasi", "Jumlah baris", "% dari baris", "Rule terbanyak"],
        [[x["k"], x["sum"], pr(x["sum"]), s(x["first"][7])] for x in top_by(dn, lambda r: s(r[6]), lambda r: 1, 10)])
    tab("densrc", "Trafik ditolak: sumber teratas", ["Sumber", "Jumlah baris", "Negara / jaringan", "Aplikasi (baris pertama)"],
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
        out.insert(0, {"k": "warn", "t": f"Validasi dengan data Panorama API: {bad} dari {len(rows)} hari yang tumpang tindih selisih lebih dari {tol * 100:.0f}%. CSV manual yang dipakai."})
    return out


def import_file(db: Session, cfg: Config, data: bytes, file_name: str, username: str, d_from: date | None = None, d_to: date | None = None,
                files: list[tuple[str, bytes]] | None = None) -> SocBatch:
    """Validasi lalu simpan. Batch gagal tetap tersimpan (untuk riwayat), tetapi tidak dipakai di KPI.
    `files` = CSV RAW Panorama (beberapa laporan sekaligus); tanpa itu, `data` dibaca sebagai workbook 3_Dashboard_SOC.xlsx."""
    P = parse_csv(files, cfg) if files is not None else parse(data, cfg)
    issues = [{"k": "warn", "t": "File dilewati: " + n} for n in P.get("notes", [])]
    if P["skipped"]:
        issues.append({"k": "crit", "t": f"{P['skipped']:,} baris ringkasan harian dilewati: kolom Time tidak terbaca sebagai tanggal ekspor Panorama.".replace(",", ".")})
    if not P["days"]:
        issues.append({"k": "crit", "t": "Tidak ada baris ringkasan harian yang tanggalnya terbaca."})
    missing = [k for k in cfg.sources["panorama"]["config"]["excel"]["top_reports"] if k not in P["top_present"]]
    if missing:
        issues.append({"k": "warn", "t": "Laporan Top tidak ikut diunggah: " + ", ".join(missing) + ". Tabel periode tidak tersedia."})
    f, t = P["from"], P["to"]
    f = date.fromisoformat(f) if f else d_from or date.today()
    t = date.fromisoformat(t) if t else d_to or f
    overlap = [iso(x.day) for x in db.scalars(select(SocDay).join(SocBatch).where(SocBatch.status != "failed", SocDay.day.in_([date.fromisoformat(k) for k in P["days"]])))]
    if overlap:
        issues.append({"k": "warn", "t": f"Tanggal {', '.join(sorted(set(overlap)))} juga ada di batch sebelumnya. Dipakai data batch terbaru supaya tidak terhitung dua kali."})
    issues += _compare_api(db, P)
    status = "failed" if any(i["k"] == "crit" for i in issues) else "warn" if issues else "valid"
    b = SocBatch(file_name=file_name, uploaded_by=username, uploaded_at=cfg.now(), date_from=f, date_to=t, rows_read=P["read"], rows_skipped=P["skipped"],
                 status=status, issues=issues, tables=P["tables"], kpi=P["K"])
    for k, v in P["days"].items():
        b.days.append(SocDay(day=date.fromisoformat(k), threats=v["th"], urls=v["url"], bytes=int(v["b"]), sessions=int(v["s"])))
    db.add(b)
    return b
