"""Model laporan: satu struktur data untuk Excel, PDF, dan PowerPoint (angka dari perhitungan server yang sama dengan dashboard).
Isi mengikuti dashboard Excel filtered: 12 KPI dan 8-10 grafik per bidang. Bagian laporan mengikuti izin role dan lokasi yang dikunci.

Bentuk model (aman untuk JSON):
  {"title", "kind", "subtitle", "tagline", "period", "filters", "generated", "by", "sections": [section], "kinds": [..]}
  section = {"key", "title", "prefix", "kpis": [{"label","value","kind","sub"}], "charts": [chart], "tables": [table], "notes": [..], "attention": [..]}
  chart = {"title", "kind": bar | stack | hbar | donut | line, "labels": [..], "series": [{"name","values"}]}; charts[0] = grafik utama (dipakai di Summary)
  table = {"title","heads","kinds","rows"}
  kind angka: n = bulat, f0/f1/f2 = desimal, p0/p1/p2 = persen dari pecahan, t = teks."""
from datetime import timedelta
from . import views as VW
from .calc import soc as SOC
from .security import can_see

SECTIONS = [("servicedesk", "Ticketing"), ("noc", "Networking"), ("soc", "Cyber Security")]
WEEKLY_AFTER = 31  # rentang harian lebih panjang dari ini diringkas per minggu (sama dengan dashboard Excel)
_UK = {"type": "Tipe ancaman", "action": "Tindakan", "severity": "Severity"}


def fmt_n(x):
    return f"{round(x or 0):,}".replace(",", ".")


def fmt_f(x, d=1):
    return f"{x:,.{d}f}".replace(",", "§").replace(".", ",").replace("§", ".")


def fmt_p(x, d=1):
    return fmt_f(x * 100, d) + "%"


def fmt(v, kind="t"):
    """Teks tampil untuk PDF/PPT. Excel memakai nilai asli + number_format."""
    if v is None or v == "":
        return "–"
    try:
        if kind == "n":
            return fmt_n(v)
        if kind[0] == "f":
            return fmt_f(v, int(kind[1]))
        if kind[0] == "p":
            return fmt_p(v, int(kind[1]))
    except (TypeError, ValueError):
        pass
    return str(v)


def _short(d: str) -> str:
    return d[8:10] + "/" + d[5:7]


def _kpi(label, value, kind="t", sub=""):
    return {"label": label, "value": value, "kind": kind, "sub": sub}


def _table(title, heads, kinds, rows):
    return {"title": title, "heads": heads, "kinds": kinds, "rows": rows}


def _chart(title, labels, series, kind="bar"):
    return {"title": title, "kind": kind, "labels": [str(x) for x in labels], "series": series}


def _daily(title, dates, series, kind="bar", mean=False):
    """Grafik harian; rentang panjang diringkas per minggu (jumlah, atau rata-rata bila mean)."""
    if len(dates) <= WEEKLY_AFTER:
        return _chart(title + " per hari", [_short(d) for d in dates], series, kind)
    out = []
    for se in series:
        vals = []
        for i in range(0, len(dates), 7):
            part = [v or 0 for v in se["values"][i:i + 7]]
            vals.append(round(sum(part) / len(part), 2) if mean else sum(part))
        out.append({"name": se["name"], "values": vals})
    return _chart(title + " per minggu", [_short(dates[i]) for i in range(0, len(dates), 7)], out, kind)


def _top(title, rows, name="Jumlah", n=10):
    """Grafik batang horizontal dari [(label, nilai), ...], terbesar lebih dulu."""
    rows = [r for r in rows if r[1]][:n]
    return _chart(title, [r[0] for r in rows], [{"name": name, "values": [r[1] for r in rows]}], "hbar") if rows else None


PRESETS = ("ringkas", "standar", "lengkap")
SD_IDS = ["sd_status", "sd_daily", "sd_category", "sd_location", "sd_duration", "sd_hour", "sd_tech", "sd_sla", "sd_mode", "sd_weekday"]
NOC_IDS = ["noc_status", "noc_downtime_daily", "noc_top_link_down", "noc_top_loc_down", "noc_availability", "noc_isp_status", "noc_top_traffic", "noc_top_util", "noc_traffic_daily"]
SOC_IDS = ["soc_severity", "soc_daily_sev", "soc_action", "soc_category", "soc_country", "soc_ip", "soc_host", "soc_url_cat", "soc_app", "soc_app_cat", "soc_traffic_daily"]


def _pick(cfg, section, ids, preset, charts):
    """Pilih dan atur grafik menurut widget di database (Admin → Master data → Widget grafik): aktif, preset, judul, jenis, jumlah baris, urutan.
    Kode hanya menyediakan data tiap grafik (kunci widget). Tanpa widget terdaftar, semua grafik bawaan dipakai."""
    pool = {i: c for i, c in zip(ids, charts) if c and c["labels"] and any(any(v for v in s["values"]) for s in c["series"])}
    ws = [w for w in cfg.widgets if w["section"] == section]
    if not ws:
        return list(pool.values())
    out = []
    for w in sorted(ws, key=lambda w: (not w["hero"], w["sort"])):
        c = pool.get(w["key"])
        if c is None or (preset in PRESETS and preset not in (w["presets"] or [])):
            continue
        c = dict(c)
        if w["title"]:
            c["title"] = w["title"]
        k = w["kind"]
        if k in ("bar", "stack", "hbar", "donut", "line") and k != c["kind"] and (len(c["series"]) == 1 or k in ("bar", "stack", "line")):
            c["kind"] = k
        n = w.get("top_n") or 0
        if c["kind"] == "hbar" and n and len(c["labels"]) > n:
            c["labels"] = c["labels"][:n]
            c["series"] = [{**se, "values": se["values"][:n]} for se in c["series"]]
        out.append(c)
    return out


# ---------------- bagian ----------------
def _servicedesk(db, cfg, f, preset="standar"):
    T = VW._tk(db, cfg, f.d_from, f.d_to, f.shift, f.site)
    s = {"key": "servicedesk", "title": "Ticketing", "kpis": [], "charts": [], "tables": [], "notes": [], "attention": []}
    if not T["n"]:
        s["notes"].append("Tidak ada tiket pada periode dan filter ini.")
        return s
    d, n = T["daily"], T["n"]
    tc, tl, bz = T.get("topCat"), T.get("topLoc"), T.get("busiest")
    s["kpis"] = [
        _kpi("Tiket masuk", n, "n", fmt_f(T["perDay"], 1) + " per hari"),
        _kpi("Tingkat penyelesaian", T["doneRate"], "p1", fmt_n(T["open"]) + " masih open"),
        _kpi("Dalam target SLA", T["slaPct"], "p1", fmt_n(T["slaOut"]) + " melewati target"),
        _kpi("Median durasi (menit)", T["medMin"], "f0", "P90 " + fmt_f(T["p90"], 1) + " jam"),
        _kpi("Rata-rata durasi (jam)", T["avgH"], "f1", ""),
        _kpi("Tiket close", sum(x["done"] for x in d), "n", "dalam periode"),
        _kpi("Durasi 0 menit", T["zero"], "n", fmt_p(T["zero"] / n, 1) + " dari tiket"),
        _kpi("Input tidak lengkap", T["incomplete"], "n", fmt_p(T["incomplete"] / n, 1) + " dari tiket"),
        _kpi("Backlog akhir periode", d[-1]["backlog"] if d else 0, "n", ""),
        _kpi("Kategori terbanyak", tc["k"] if tc else None, "t", fmt_n(tc["n"]) + " tiket" if tc else ""),
        _kpi("Lokasi terbanyak", tl["k"] if tl else None, "t", fmt_n(tl["n"]) + " tiket" if tl else ""),
        _kpi("Hari tersibuk", _short(bz["date"]) if bz else None, "t", fmt_n(bz["in"]) + " tiket" if bz else "")]
    dim = lambda key: [(r["k"], r["n"]) for r in (T["dims"].get(key) or [])]
    sla = T["dims"].get("sla") or []
    s["charts"] = _pick(cfg, "servicedesk", SD_IDS, preset, [
        _chart("Status tiket", ["Close", "Open"], [{"name": "Tiket", "values": [n - T["open"], T["open"]]}], "donut"),
        _daily("Tiket masuk dan close", [x["date"] for x in d], [{"name": "Masuk", "values": [x["in"] for x in d]}, {"name": "Close", "values": [x["done"] for x in d]}]),
        _top("10 kategori dengan tiket terbanyak", dim("kategori"), "Tiket"),
        None if f.site else _top("10 lokasi dengan tiket terbanyak", dim("lokasi"), "Tiket"),
        _chart("Sebaran durasi penyelesaian", [x["k"] for x in T["durasi"]], [{"name": "Tiket", "values": [x["n"] for x in T["durasi"]]}]),
        _chart("Tiket masuk per jam dibuat", [f"{h:02d}" for h in range(24)], [{"name": "Tiket", "values": T["hours"]}]),
        _top("10 teknisi teratas", [(r["name"], r["n"]) for r in T["ranking"]], "Tiket"),
        _chart("Kepatuhan SLA per level", [r["k"] for r in sla], [{"name": "Dalam target", "values": [r["in"] for r in sla]}, {"name": "Melewati target", "values": [r["out"] for r in sla]}], "stack"),
        _top("Tiket per mode request", dim("mode"), "Tiket"),
        _chart("Rata-rata tiket per hari menurut hari", [x["k"] for x in T["weekday"]], [{"name": "Rata-rata", "values": [round(x["avg"], 1) for x in T["weekday"]]}])])
    heads = ["", "Tiket", "% dari total", "Close", "Open", "Dalam SLA"]
    kinds = ["t", "n", "p1", "n", "n", "p1"]
    for key, label in (("kategori", "Kategori"), ("lokasi", "Lokasi / Group")):
        rows = (T["dims"].get(key) or [])[:10]
        if rows and not (key == "lokasi" and f.site):
            s["tables"].append(_table("Tiket per " + label.lower(), [label] + heads[1:], kinds, [[r["k"], r["n"], r["pct"], r["done"], r["open"], r["inPct"]] for r in rows]))
    gr = T.get("groupRanking") or []
    if any(r["n"] for r in gr):
        s["tables"].append(_table("Peringkat grup", ["#", "Grup", "Anggota", "Tiket", "Close", "Open", "Rata-rata (jam)", "Dalam SLA"], ["n", "t", "n", "n", "n", "n", "f1", "p1"],
                                  [[r["rank"], r["name"], r["members"], r["n"], r["done"], r["open"], r["avg"], r["inPct"]] for r in gr]))
    rk = [r for r in T["ranking"] if r["n"]][:15]
    if rk:
        s["tables"].append(_table("Peringkat teknisi", ["#", "Nama", "Unit", "Tiket", "Close", "Open", "Rata-rata (jam)", "Dalam SLA"], ["n", "t", "t", "n", "n", "n", "f1", "p1"],
                                  [[r["rank"], r["name"], r["unit"], r["n"], r["done"], r["open"], r["avg"], r["inPct"]] for r in rk]))
    if T["openList"]:
        s["tables"].append(_table("Tiket open (terbaru)", ["ID", "Subjek", "Lokasi", "Teknisi", "Prioritas", "Status", "Umur (hari)"], ["t", "t", "t", "t", "t", "t", "f1"],
                                  [[r["id"], r["subj"], r["loc"], r["tech"], r["prio"], r["status"], r["age"]] for r in T["openList"][:10]]))
    if T["incomplete"]:
        s["attention"].append(f"{fmt_n(T['incomplete'])} tiket ({fmt_p(T['incomplete'] / n, 0)}) punya input wajib tidak lengkap")
    if T["noSla"]:
        s["attention"].append(f"{fmt_n(T['noSla'])} tiket tanpa SLA")
    if T["open"]:
        s["attention"].append(f"{fmt_n(T['open'])} tiket masih open")
    return s


def _noc(db, cfg, f, preset="standar"):
    N = VW._net(db, cfg, f.d_from, f.d_to, f.shift, f.site)
    s = {"key": "noc", "title": "Networking", "kpis": [], "charts": [], "tables": [], "notes": [], "attention": []}
    if not N or not N.get("links"):
        s["notes"].append("Belum ada data PRTG untuk periode dan filter ini.")
        return s
    P, st = N["P"], cfg.p("net.status_labels")
    w, lt = N.get("worst"), (N.get("lokasiTop") or [None])[0]
    s["kpis"] = [
        _kpi("Link dipantau", N["links"], "n", f"di {N['locations']} lokasi"),
        _kpi("Availability rata-rata", N["avail"], "p2", "target " + fmt_p(P["target"], 1)),
        _kpi("Link capai SLA", N["ok"], "n", fmt_p(N["okPct"], 0) + " dari link yang dinilai"),
        _kpi("Link tidak capai SLA", N["bad"], "n", ""),
        _kpi("Link data kurang", N["nodata"], "n", "cakupan di bawah batas"),
        _kpi("Total downtime (jam)", N["downH"], "f1", f"{N['events']} kejadian"),
        _kpi("Link tanpa downtime", N["noDown"], "n", ""),
        _kpi("Cakupan data", N["cov"], "p1", "waktu terpantau"),
        _kpi("Volume total (TB)", N["volTB"], "f1", fmt_f(N["mbps"], 0) + " Mbit/s rata-rata"),
        _kpi("Utilisasi puncak tinggi", N["utilHigh"], "n", "link di atas " + fmt_p(P["utilPeak"], 0)),
        _kpi("Link downtime terbesar", w["link"] if w else None, "t", fmt_f(w["down"] / 3600, 1) + " jam" if w else ""),
        _kpi("Lokasi downtime terbesar", lt["k"] if lt else None, "t", fmt_f(lt["downH"], 1) + " jam (semua link)" if lt else "")]
    d, isp = N["daily"], N["isp"]
    s["charts"] = _pick(cfg, "noc", NOC_IDS, preset, [
        _chart("Status SLA link", [st["ok"], st["bad"], st["nodata"]], [{"name": "Link", "values": [N["ok"], N["bad"], N["nodata"]]}], "donut"),
        _daily("Total downtime semua link (menit)", [x["date"] for x in d], [{"name": "Downtime (menit)", "values": [round(x["down"], 1) for x in d]}]),
        _top("10 link dengan downtime terbesar (jam)", [(x["link"], round(x["down"] / 3600, 2)) for x in N["rank"]], "Jam"),
        _top("10 lokasi dengan downtime terbesar (jam)", [(x["k"], round(x["downH"], 2)) for x in sorted(N["lokasi"], key=lambda r: -r["downH"])], "Jam"),
        _chart("Sebaran link menurut availability", [x["k"] for x in N["buckets"]], [{"name": "Link", "values": [x["n"] for x in N["buckets"]]}]),
        _chart("Status SLA per ISP", [x["k"] for x in isp], [{"name": st["ok"], "values": [x["ok"] for x in isp]}, {"name": st["bad"], "values": [x["bad"] for x in isp]},
                                                              {"name": st["nodata"], "values": [x["nodata"] for x in isp]}], "stack"),
        _top("10 link dengan trafik rata-rata tertinggi (Mbit/s)", [(x["link"], round(x["avg"], 1)) for x in N["traffic"]], "Mbit/s"),
        _top("10 link dengan utilisasi puncak tertinggi (%)", [(x["link"], round(x["uP"] * 100, 1)) for x in N["util"]], "% kapasitas"),
        _daily("Trafik gabungan semua link (Mbit/s)", [x["date"] for x in d], [{"name": "Mbit/s", "values": [round(x["mbps"], 1) for x in d]}], "line", mean=True)])
    if isp:
        s["tables"].append(_table("Rekap per ISP", ["ISP", "Link", "Availability", "Downtime (jam)", "Tercapai", "Tidak", "Data kurang"], ["t", "n", "p2", "f1", "n", "n", "n"],
                                  [[r["k"], r["n"], r["av"], r["downH"], r["ok"], r["bad"], r["nodata"]] for r in isp]))
    s["tables"].append(_table("Link dengan downtime terbanyak", ["Link", "Availability", "Downtime (menit)", "Status", "Rata-rata (Mbit/s)"], ["t", "p2", "f1", "t", "f1"],
                              [[r["link"], r["av"], r["downMin"], r["status"], r["avg"]] for r in N["rank"][:15]]))
    if N["util"]:
        s["tables"].append(_table("Utilisasi tertinggi", ["Link", "Rata-rata (Mbit/s)", "Puncak (Mbit/s)", "Kapasitas (Mbit/s)", "Utilisasi puncak", "Status"], ["t", "f1", "f1", "f0", "p1", "t"],
                                  [[r["link"], r["avg"], r["max"], r["cap"], r["uP"], r["ust"]] for r in N["util"][:10]]))
    if N["bad"]:
        s["attention"].append(f"{N['bad']} link di bawah target availability")
    if N["nodata"]:
        s["attention"].append(f"{N['nodata']} link data kurang (cakupan di bawah batas)")
    if N.get("unmappedIsp"):
        s["attention"].append(f"{len(N['unmappedIsp'])} link belum cocok dengan ISP mana pun")
    return s


def _soc(db, cfg, f, preset="standar"):
    S = VW._soc(db, cfg, f.d_from, f.d_to)
    R = S["R"]
    s = {"key": "soc", "title": "Cyber Security", "kpis": [], "charts": [], "tables": [], "notes": [], "attention": []}
    if not R["hasData"]:
        s["notes"].append("Belum ada data SOC yang lolos validasi pada periode ini.")
        return s
    bt = SOC.batch_for(S["batches"], f.d_from, f.d_to)
    tabs = {t["id"]: t["r"] for t in (bt.tables if bt and bt.tables else [])}
    K = (bt.kpi if bt and bt.kpi else None) or {}
    first = lambda tid, i: (tabs.get(tid) or [[None] * (i + 1)])[0][i]
    top = lambda tid, li, vi, name: _top(name, [(r[li], r[vi]) for r in tabs.get(tid, [])], "Jumlah")
    SEV = cfg.p("soc.severities")
    d = R["daily"]
    s["kpis"] = [
        _kpi("Total event ancaman", R["total"], "n", fmt_n(R["perDay"]) + " per hari"),
        _kpi("Critical + High", R["ch"], "n", fmt_n(R["crit"]) + " critical"),
        _kpi("Critical + High diblokir", R["chBlkPct"], "p1", "tindakan selain alert"),
        _kpi("Critical + High hanya alert", R["chAlert"], "n", "tercatat, tidak dihentikan"),
        _kpi("Event bersumber internal", R["internalPct"], "p1", "dari total event"),
        _kpi("Host internal terdeteksi", K.get("hosts"), "n", fmt_n(K.get("hostsCH")) + " dengan critical/high" if K.get("hostsCH") is not None else ""),
        _kpi("Negara sumber teratas", first("negara", 0), "t", fmt_n(first("negara", 1)) + " event" if tabs.get("negara") else ""),
        _kpi("IP sumber teratas", first("ip", 0), "t", fmt_n(first("ip", 3)) + " event" if tabs.get("ip") else ""),
        _kpi("URL diblokir", R["urlBlk"], "n", "dari " + fmt_n(R["url"]) + " event URL"),
        _kpi("Total trafik (TB)", R["tb"], "f1", ""),
        _kpi("Aplikasi terbesar", K.get("topApp"), "t", fmt_p(K["topAppPct"], 0) + " dari volume" if K.get("topAppPct") is not None else ""),
        _kpi("Aplikasi berisiko terlihat", K.get("watchSeen"), "n", "dari daftar diawasi")]
    s["charts"] = _pick(cfg, "soc", SOC_IDS, preset, [
        _chart("Event per severity", [x["k"] for x in R["sev"]], [{"name": "Event", "values": [x["n"] for x in R["sev"]]}], "hbar"),
        _daily("Event ancaman menurut severity", [x["date"] for x in d], [{"name": sv, "values": [x.get(sv, 0) for x in d]} for sv in SEV], "stack"),
        _top("Tindakan firewall", [(x["k"], x["n"]) for x in R["action"]], "Event"),
        _top("10 kategori ancaman terbanyak", [(x["k"], x["n"]) for x in R["cat"]], "Event"),
        top("negara", 0, 1, "10 negara sumber serangan"),
        top("ip", 0, 3, "10 IP sumber serangan teratas"),
        top("host", 0, 1, "10 host internal dengan deteksi terbanyak"),
        _top("Kategori URL yang diblokir", [(x["k"], x["blk"]) for x in R["urlCat"]], "Diblokir"),
        top("app", 0, 2, "10 aplikasi terbesar menurut volume (GB)"),
        top("appcat", 0, 1, "Volume per kategori aplikasi (GB)"),
        _daily("Trafik (TB)", [x["date"] for x in d], [{"name": "TB", "values": [round(x["tb"], 2) for x in d]}])])
    heads = ["", "Event", "% dari total", "Diblokir", "Hanya alert", "% diblokir"]
    kinds = ["t", "n", "p1", "n", "n", "p1"]
    for title, key, first_col in (("Event per severity", "sev", "Severity"), ("Event per tipe ancaman", "type", "Tipe"), ("Event per tindakan firewall", "action", "Tindakan")):
        rows = R.get(key) or []
        if rows:
            s["tables"].append(_table(title, [first_col] + heads[1:], kinds, [[r["k"], r["n"], r["pct"], r["blk"], r["alert"], r["blkPct"]] for r in rows]))
    if R["urlCat"]:
        s["tables"].append(_table("URL berdasarkan kategori", ["Kategori", "Akses", "% dari total", "Diblokir", "Hanya alert"], ["t", "n", "p1", "n", "n"],
                                  [[r["k"], r["n"], r["pct"], r["blk"], r["alert"]] for r in R["urlCat"][:10]]))
    if R["chAlert"]:
        s["attention"].append(f"{fmt_n(R['chAlert'])} event critical/high hanya alert, tidak diblokir")
    for kind, rows in (R.get("unknown") or {}).items():
        s["attention"].append(_UK[kind] + " baru di luar daftar parameter: " + ", ".join(x[0] for x in rows))
    return s


_BUILD = {"servicedesk": _servicedesk, "noc": _noc, "soc": _soc}

# Jenis laporan (bisa diubah di Admin → Parameter → report.kinds). sections: None = semua bagian yang boleh dilihat role.
DEFAULT_KINDS = {
    "summary": {"label": "Summary", "desc": "Ringkasan manajemen: KPI dan grafik utama semua bidang", "title": "Report ITOC : Summary", "subtitle": "Management Overview", "prefix": "Management", "sections": None, "summary": True},
    "noc": {"label": "Networking", "desc": "Availability, downtime, link bermasalah, utilisasi", "title": "Report ITOC Network SLA & Traffic ISP", "subtitle": "Evaluasi Availability, Coverage Monitoring, Traffic", "prefix": "Network SLA", "sections": ["noc"]},
    "soc": {"label": "Cyber Security", "desc": "Event ancaman, severity, tindakan firewall, URL", "title": "Report ITOC SOC Monitoring", "subtitle": "Ringkasan traffic security, threat, web security, dan triage high/critical", "prefix": "SOC", "sections": ["soc"]},
    "servicedesk": {"label": "Ticketing", "desc": "Tiket masuk, SLA, kategori, ranking teknisi, tiket open", "title": "Report ITOC Ticketing Servicedesk", "subtitle": "Ringkasan Performa Ticketing ManageEngine", "prefix": "Ticketing", "sections": ["servicedesk"]},
    "full": {"label": "Full", "desc": "Summary dan rincian semua bidang dalam satu berkas", "title": "Report ITOC : Summary & Rincian", "subtitle": "Management Overview", "prefix": "", "sections": None},
}


def kinds_for(cfg, user):
    """Jenis laporan yang bisa dibuat role ini (butuh minimal satu bagian yang boleh dilihat)."""
    kd = {k: {**v, **((cfg.p("report.kinds") or {}).get(k) or {})} for k, v in DEFAULT_KINDS.items()}
    out = {}
    for k, v in kd.items():
        keys = [x for x, _ in SECTIONS if (v.get("sections") is None or x in v["sections"]) and can_see(user, x)]
        if keys and (k != "full" or len(keys) > 1):
            out[k] = {**v, "key": k, "allowed": keys}
    return out


def _period(cfg, d1, d2):
    ml = cfg.p("ui.months_long") or cfg.p("ui.months")
    if d1.day == 1 and d1.year == d2.year and d1.month == d2.month and (d2 + timedelta(days=1)).month != d2.month:
        return f"{ml[d1.month - 1]} {d1.year}"
    p = lambda d: f"{d.day} {cfg.p('ui.months')[d.month - 1]} {d.year}"
    return p(d1) if d1 == d2 else p(d1) + " – " + p(d2)


def build(db, cfg, user, f, kind="full", preset="standar"):
    """kind = kunci jenis laporan. Bagian di luar izin role dibuang diam-diam."""
    ks = kinds_for(cfg, user)
    spec = ks.get(kind) or ks.get("full") or (next(iter(ks.values())) if ks else None)
    if spec is None:
        return {"title": cfg.p("ui.brand_name", "Dashboard"), "sections": [], "kinds": []}
    secs = [_BUILD[k](db, cfg, f, preset) for k in spec["allowed"]]
    single = len(spec["allowed"]) == 1 and spec.get("sections")
    for s in secs:
        s["prefix"] = spec["prefix"] if single and spec.get("prefix") else s["title"]
    overview = {"key": "ringkasan", "title": "Ringkasan", "kpis": [], "charts": [], "tables": [], "notes": []}
    att = []
    for s in secs:
        for k in s["kpis"][:2]:
            overview["kpis"].append({**k, "label": s["title"] + " · " + k["label"], "sec": s["key"], "sec_title": s["title"]})
        if s["charts"]:
            overview["charts"].append({**s["charts"][0], "title": s["title"] + " · " + s["charts"][0]["title"]})
        att += [[s["title"], a] for a in s["attention"]]
    if att:
        overview["tables"].append(_table("Perlu perhatian", ["Area", "Temuan"], ["t", "t"], att))
    filt = []
    if f.shift:
        filt.append("Shift: " + next((x["name"] for x in cfg.shifts if x["no"] == f.shift), str(f.shift)))
    filt.append("Lokasi: " + (f.site or "Semua lokasi"))
    summary = bool(spec.get("summary"))
    body = [overview] if summary else ([overview] if overview["kpis"] and len(secs) > 1 else []) + secs
    return {"title": cfg.p("ui.brand_name", "Dashboard"), "kind": spec["key"], "subtitle": spec["title"], "tagline": spec["subtitle"], "prefix": spec.get("prefix", ""),
            "company": cfg.p("report.company", ""), "contact": cfg.p("report.contact", {}), "period": _period(cfg, f.d_from, f.d_to),
            "preset": preset, "filters": filt, "generated": cfg.now().strftime("%d/%m/%Y %H.%M") + " WIB", "by": user.full_name, "sections": body,
            "kinds": [{"key": k, "label": v["label"], "desc": v["desc"]} for k, v in ks.items()]}
