"""Report model: one data structure for Excel, PDF, and PowerPoint (figures from the same server calculation as the dashboard).
Isi mengikuti dashboard Excel filtered: 12 KPI dan 8-10 grafik per bidang. Bagian laporan mengikuti izin role dan lokasi yang dikunci.

Bentuk model (aman untuk JSON):
  {"title", "kind", "subtitle", "tagline", "period", "filters", "generated", "by", "sections": [section], "kinds": [..]}
  section = {"key", "title", "prefix", "kpis": [{"label","value","kind","sub"}], "charts": [chart], "tables": [table], "notes": [..], "attention": [..]}
  chart = {"title", "kind": bar | stack | hbar | donut | line, "labels": [..], "series": [{"name","values"}]}; charts[0] = grafik utama (dipakai di Summary)
  table = {"title","heads","kinds","rows"}
  kind angka: n = bulat, f0/f1/f2 = desimal, p0/p1/p2 = persen dari pecahan, t = teks."""
from datetime import datetime, timedelta
from . import views as VW
from .calc import soc as SOC, soc_fw as SOCFW, servicedesk as SD
from .security import can_see

SECTIONS = [("servicedesk", "Ticketing"), ("noc", "Networking (PRTG)"), ("soc", "NDR (Palo Alto)"), ("xdr", "XDR (Trend Micro)"), ("devices", "Devices"), ("wifi", "WiFi (Ruckus)"), ("internet", "Internet Usage")]
WEEKLY_AFTER = 31  # rentang harian lebih panjang dari ini diringkas per minggu (sama dengan dashboard Excel)
_UK = {"type": "Threat type", "action": "Action", "severity": "Severity"}


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
    """Grafik harian; long ranges are summed per week (jumlah, atau rata-rata bila mean)."""
    if len(dates) <= WEEKLY_AFTER:
        return _chart(title + " per day", [_short(d) for d in dates], series, kind)
    out = []
    for se in series:
        vals = []
        for i in range(0, len(dates), 7):
            part = [v or 0 for v in se["values"][i:i + 7]]
            vals.append(round(sum(part) / len(part), 2) if mean else sum(part))
        out.append({**se, "values": vals})
    return _chart(title + " per week", [_short(dates[i]) for i in range(0, len(dates), 7)], out, kind)


def _top(title, rows, name="Count", n=10):
    """Grafik batang horizontal dari [(label, nilai), ...], terbesar lebih dulu."""
    rows = [r for r in rows if r[1]][:n]
    return _chart(title, [r[0] for r in rows], [{"name": name, "values": [r[1] for r in rows]}], "hbar") if rows else None


PRESETS = ("ringkas", "standar", "lengkap")
SD_IDS = ["sd_status", "sd_daily", "sd_category", "sd_location", "sd_duration", "sd_hour", "sd_tech", "sd_sla", "sd_mode", "sd_weekday"]
NOC_IDS = ["noc_status", "noc_downtime_daily", "noc_top_link_down", "noc_top_loc_down", "noc_availability", "noc_isp_status", "noc_top_traffic", "noc_top_util", "noc_traffic_daily"]
SOC_IDS = ["soc_severity", "soc_daily_sev", "soc_action", "soc_category", "soc_country", "soc_ip", "soc_host", "soc_url_cat", "soc_app", "soc_app_cat", "soc_traffic_daily"]


def _pick(cfg, section, ids, preset, charts):
    """Pilih dan atur grafik menurut widget di database (Admin → Sistem → Menu dan Widget): aktif, preset, judul, jenis, jumlah baris, urutan.
    Kode hanya menyediakan data tiap grafik (kunci widget). Tanpa widget terdaftar, semua grafik bawaan dipakai."""
    pool = {i: c for i, c in zip(ids, charts) if c and c["labels"] and any(any(v for v in s["values"]) for s in c["series"])}
    ws = [w for w in cfg.widgets if w["section"] == section]
    if not ws:
        return list(pool.values())[:{"ringkas": 2, "standar": 4}.get(preset, 99)]
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
    T = VW._tk(db, cfg, f.d_from, f.d_to, f.shift, f.site, getattr(f, "rgrp", ""), getattr(f, "rtech", ""))
    s = {"key": "servicedesk", "title": "Ticketing", "kpis": [], "charts": [], "tables": [], "notes": [], "attention": []}
    if not T["n"]:
        s["notes"].append("No tickets in this period and filter.")
        return s
    d, n = T["daily"], T["n"]
    tc, tl, bz = T.get("topCat"), T.get("topLoc"), T.get("busiest")
    s["kpis"] = [
        _kpi("Tickets received", n, "n", fmt_f(T["perDay"], 1) + " per day"),
        _kpi("Completion rate", T["doneRate"], "p1", fmt_n(T["open"]) + " still open"),
        _kpi("Within SLA target", T["slaPct"], "p1", fmt_n(T["slaOut"]) + " melewati target"),
        _kpi("Median duration (minutes)", T["medMin"], "f0", "P90 " + fmt_f(T["p90"], 1) + " h"),
        _kpi("Average duration (hours)", T["avgH"], "f1", ""),
        _kpi("Tickets closed", sum(x["done"] for x in d), "n", "in the period"),
        _kpi("0-minute duration", T["zero"], "n", fmt_p(T["zero"] / n, 1) + " of tickets"),
        _kpi("Incomplete input", T["incomplete"], "n", fmt_p(T["incomplete"] / n, 1) + " of tickets"),
        _kpi("Backlog at period end", d[-1]["backlog"] if d else 0, "n", ""),
        _kpi("Top category", tc["k"] if tc else None, "t", fmt_n(tc["n"]) + " tickets" if tc else ""),
        _kpi("Top location", tl["k"] if tl else None, "t", fmt_n(tl["n"]) + " tickets" if tl else ""),
        _kpi("Busiest day", _short(bz["date"]) if bz else None, "t", fmt_n(bz["in"]) + " tickets" if bz else "")]
    dim = lambda key: [(r["k"], r["n"]) for r in (T["dims"].get(key) or [])]
    sla = T["dims"].get("sla") or []
    s["charts"] = _pick(cfg, "servicedesk", SD_IDS, preset, [
        _chart("Ticket status", ["Done", "Open"], [{"name": "Tickets", "values": [n - T["open"], T["open"]]}], "donut"),
        _daily("Tickets received and done", [x["date"] for x in d], [{"name": "Received", "values": [x["in"] for x in d]}, {"name": "Close", "values": [x["done"] for x in d]}]),
        _top("Top 10 categories by tickets", dim("kategori"), "Tickets"),
        None if f.site else _top("Top 10 locations by tickets", dim("lokasi"), "Tickets"),
        _chart("Distribution of resolution time", [x["k"] for x in T["durasi"]], [{"name": "Tickets", "values": [x["n"] for x in T["durasi"]]}]),
        _chart("Tickets received per hour", [f"{h:02d}" for h in range(24)], [{"name": "Tickets", "values": T["hours"]}]),
        _top("Top 10 technicians", [(r["name"], r["n"]) for r in T["ranking"]], "Tickets"),
        _chart("SLA compliance per level", [r["k"] for r in sla], [{"name": "Within target", "values": [r["in"] for r in sla]}, {"name": "Melewati target", "values": [r["out"] for r in sla]}], "stack"),
        _top("Tickets per request mode", dim("mode"), "Tickets"),
        _chart("Average tickets per weekday", [x["k"] for x in T["weekday"]], [{"name": "Average", "values": [round(x["avg"], 1) for x in T["weekday"]]}])])
    heads = ["", "Tickets", "% of total", "Done", "Open", "Within SLA"]
    kinds = ["t", "n", "p1", "n", "n", "p1"]
    for key, label in (("kategori", "Category"), ("lokasi", "Location / Group")):
        rows = (T["dims"].get(key) or [])[:10]
        if rows and not (key == "lokasi" and f.site):
            s["tables"].append(_table("Tickets per " + label.lower(), [label] + heads[1:], kinds, [[r["k"], r["n"], r["pct"], r["done"], r["open"], r["inPct"]] for r in rows]))
    gr = T.get("groupRanking") or []
    if any(r["n"] for r in gr):
        s["tables"].append(_table("Group ranking", ["#", "Group", "Members", "Tickets", "Done", "Open", "Average (h)", "Within SLA"], ["n", "t", "n", "n", "n", "n", "f1", "p1"],
                                  [[r["rank"], r["name"], r["members"], r["n"], r["done"], r["open"], r["avg"], r["inPct"]] for r in gr]))
    rk = list(T["ranking"])   # semua teknisi di roster, termasuk yang belum punya tiket
    if rk:
        s["tables"].append(_table("Technician ranking", ["#", "Name", "Unit", "Tickets", "Done", "Open", "Average (h)", "Within SLA"], ["n", "t", "t", "n", "n", "n", "f1", "p1"],
                                  [[r["rank"], r["name"], r["unit"], r["n"], r["done"], r["open"], r["avg"], r["inPct"]] for r in rk]))
    if T["openList"]:
        s["tables"].append(_table("Open tickets (latest)", ["ID", "Subject", "Location", "Technician", "Priority", "Status", "Age (days)"], ["t", "t", "t", "t", "t", "t", "f1"],
                                  [[r["id"], r["subj"], r["loc"], r["tech"], r["prio"], r["status"], r["age"]] for r in T["openList"][:10]]))
    if T["incomplete"]:
        s["attention"].append(f"{fmt_n(T['incomplete'])} tickets ({fmt_p(T['incomplete'] / n, 0)}) have incomplete required fields")
    if T["noSla"]:
        s["attention"].append(f"{fmt_n(T['noSla'])} tickets without SLA")
    if T["open"]:
        s["attention"].append(f"{fmt_n(T['open'])} tickets still open")
    return s



def _isp_of(cfg, name):
    hit = next((i for i in cfg.isps if i["keyword"].lower() in name.lower()), None)
    return hit["name"] if hit else cfg.p("net.other_isp_label")


def _link_options(db, cfg, f):
    """Active PRTG links (id, name, ISP) within the chosen location, for the report's ISP and Link filters."""
    from sqlalchemy import select
    M = VW.M
    q = select(M.PrtgSensor.id, M.PrtgSensor.name).where(M.PrtgSensor.active.is_(True)).order_by(M.PrtgSensor.name)
    if f.site:
        q = q.where(VW.NET.site_cond(db, f.site))
    return [(i, n, _isp_of(cfg, n)) for i, n in db.execute(q)]


HOURLY_UP_TO = 62          # days: longer periods are drawn per day


def _noc_links(db, cfg, f):
    """Per-link graphs in the PRTG style: one wide graph per link (traffic total, in and out, downtime as red lines on the right axis) with the channel table under it."""
    from sqlalchemy import func, select
    M = VW.M
    q = select(M.PrtgSensor.id, M.PrtgSensor.name, M.PrtgSensor.device, M.PrtgSensor.capacity_mbps).where(M.PrtgSensor.active.is_(True))
    if f.site:
        q = q.where(VW.NET.site_cond(db, f.site))
    if getattr(f, "rlink", ""):
        q = q.where(M.PrtgSensor.id == f.rlink)
    isp = getattr(f, "risp", "")
    sensors = {i: (n, dv, c) for i, n, dv, c in db.execute(q) if not isp or _isp_of(cfg, n) == isp}
    s = {"key": "noc_links", "title": "Links · Detail", "prefix": "Links", "kpis": [], "charts": [], "tables": [], "notes": [], "attention": []}
    if not sensors:
        return None
    a, b = datetime.combine(f.d_from, datetime.min.time()), datetime.combine(f.d_to + timedelta(days=1), datetime.min.time())
    H = M.PrtgHourly
    hourly = (f.d_to - f.d_from).days + 1 <= HOURLY_UP_TO
    unit = H.ts if hourly else func.date(H.ts)
    rows = db.execute(select(H.sensor_id, unit, func.avg(H.in_mbps), func.avg(H.out_mbps), func.max(H.in_mbps), func.max(H.out_mbps), func.sum(H.down_s), func.count())
                      .where(H.sensor_id.in_(list(sensors)), H.ts >= a, H.ts < b).group_by(H.sensor_id, unit).order_by(H.sensor_id, unit)).all()
    by: dict = {}
    for sid, t, ai, ao, mi, mo, dn, hrs in rows:
        by.setdefault(sid, []).append((t, ai or 0, ao or 0, max(mi or 0, mo or 0), dn or 0, hrs or 0))
    order = sorted(by, key=lambda i: (-sum(x[4] for x in by[i]), -sum(x[1] + x[2] for x in by[i])))
    step = 3600 if hourly else 86400
    res = "1 h Average" if hourly else "1 d Average"
    summary = []
    for sid in order:
        name, dev, cap = sensors[sid]
        pts = by[sid]
        label = lambda t: t.strftime("%Y-%m-%d %H") if hourly else t.isoformat()
        tin, tout = [round(x[1], 2) for x in pts], [round(x[2], 2) for x in pts]
        tot = [round(x[1] + x[2], 2) for x in pts]
        down_s, seen_s = sum(x[4] for x in pts), sum(x[5] for x in pts) * 3600
        n = max(len(pts), 1)
        mb = lambda v: sum(v) * step / 8                                    # Mbit/s over the step -> megabytes
        events = sum(1 for x in pts if x[4] > 0)
        s["charts"].append({"title": name, "sub": dev, "kind": "prtg", "labels": [label(x[0]) for x in pts], "res": res, "sid": sid, "unit": "Mbit/s",
                            "series": [{"name": "Traffic Total", "color": "1F2A5C", "values": tot}, {"name": "Traffic In", "color": "5AA3A0", "values": tin}, {"name": "Traffic Out", "color": "D6558F", "values": tout}],
                            "down": [round(x[4] / step * 100, 3) for x in pts],
                            "rows": [["Traffic Total", f"{fmt_n(round(sum(tot) / n))} Mbit/s", f"{fmt_n(round(mb(tot)))} MB"], ["Traffic In", f"{fmt_n(round(sum(tin) / n))} Mbit/s", f"{fmt_n(round(mb(tin)))} MB"],
                                     ["Traffic Out", f"{fmt_n(round(sum(tout) / n))} Mbit/s", f"{fmt_n(round(mb(tout)))} MB"],
                                     ["Downtime", f"{fmt_p(1 - down_s / seen_s, 2) if seen_s else '–'} available", f"{fmt_n(round(down_s / 60))} min in {fmt_n(events)} " + ("hour" if hourly else "day") + ("" if events == 1 else "s")]]})
        summary.append([name, 1 - down_s / seen_s if seen_s else None, down_s / 60, sum(x[1] for x in pts) / n, sum(x[2] for x in pts) / n, max(x[3] for x in pts), cap, max(x[3] for x in pts) / cap if cap else None])
    if summary:
        s["tables"].append(_table("Link summary", ["Link", "Availability", "Downtime (min)", "Avg in (Mbit/s)", "Avg out (Mbit/s)", "Peak (Mbit/s)", "Capacity (Mbit/s)", "Peak utilization"], ["t", "p2", "f0", "f1", "f1", "f1", "f0", "p1"], summary))
    return s if s["charts"] else None


def _noc(db, cfg, f, preset="standar"):
    N = VW._net(db, cfg, f.d_from, f.d_to, f.shift, f.site)
    s = {"key": "noc", "title": "Networking (PRTG)", "kpis": [], "charts": [], "tables": [], "notes": [], "attention": []}
    if not N or not N.get("links"):
        s["notes"].append("No PRTG data for this period and filter.")
        return s
    P, st = N["P"], cfg.p("net.status_labels")
    w, lt = N.get("worst"), (N.get("lokasiTop") or [None])[0]
    s["kpis"] = [
        _kpi("Links monitored", N["links"], "n", f"in {N['locations']} locations"),
        _kpi("Average availability", N["avail"], "p2", "target " + fmt_p(P["target"], 1)),
        _kpi("Links meeting SLA", N["ok"], "n", fmt_p(N["okPct"], 0) + " of rated links"),
        _kpi("Links not meeting SLA", N["bad"], "n", ""),
        _kpi("Links with insufficient data", N["nodata"], "n", "cakupan di bawah batas"),
        _kpi("Total downtime (hours)", N["downH"], "f1", f"{N['events']} incidents"),
        _kpi("Links without downtime", N["noDown"], "n", ""),
        _kpi("Data coverage", N["cov"], "p1", "monitored time"),
        _kpi("Total volume (TB)", N["volTB"], "f1", fmt_f(N["mbps"], 0) + " Mbit/s average"),
        _kpi("High peak utilization", N["utilHigh"], "n", "link di atas " + fmt_p(P["utilPeak"], 0)),
        _kpi("Link with most downtime", w["link"] if w else None, "t", fmt_f(w["down"] / 3600, 1) + " h" if w else ""),
        _kpi("Location with most downtime", lt["k"] if lt else None, "t", fmt_f(lt["downH"], 1) + " h (all links)" if lt else "")]
    d, isp = N["daily"], N["isp"]
    s["charts"] = _pick(cfg, "noc", NOC_IDS, preset, [
        _chart("Link SLA status", [st["ok"], st["bad"], st["nodata"]], [{"name": "Link", "values": [N["ok"], N["bad"], N["nodata"]]}], "donut"),
        _daily("Total downtime of all links (minutes)", [x["date"] for x in d], [{"name": "Downtime (minutes)", "values": [round(x["down"], 1) for x in d]}]),
        _top("Top 10 links by downtime (hours)", [(x["link"], round(x["down"] / 3600, 2)) for x in N["rank"]], "Hours"),
        _top("Top 10 locations by downtime (hours)", [(x["k"], round(x["downH"], 2)) for x in sorted(N["lokasi"], key=lambda r: -r["downH"])], "Hours"),
        _chart("Link distribution by availability", [x["k"] for x in N["buckets"]], [{"name": "Link", "values": [x["n"] for x in N["buckets"]]}]),
        _chart("SLA status per ISP", [x["k"] for x in isp], [{"name": st["ok"], "values": [x["ok"] for x in isp]}, {"name": st["bad"], "values": [x["bad"] for x in isp]},
                                                              {"name": st["nodata"], "values": [x["nodata"] for x in isp]}], "stack"),
        _top("Top 10 links by average traffic (Mbit/s)", [(x["link"], round(x["avg"], 1)) for x in N["traffic"]], "Mbit/s"),
        _top("Top 10 links by peak utilization (%)", [(x["link"], round(x["uP"] * 100, 1)) for x in N["util"]], "% kapasitas"),
        _daily("Combined traffic of all links (Mbit/s)", [x["date"] for x in d], [{"name": "Mbit/s", "values": [round(x["mbps"], 1) for x in d]}], "line", mean=True)])
    if isp:
        s["tables"].append(_table("Summary per ISP", ["ISP", "Links", "Availability", "Downtime (h)", "Met", "Not met", "Insufficient data"], ["t", "n", "p2", "f1", "n", "n", "n"],
                                  [[r["k"], r["n"], r["av"], r["downH"], r["ok"], r["bad"], r["nodata"]] for r in isp]))
    s["tables"].append(_table("Links with the most downtime", ["Link", "Availability", "Downtime (min)", "Status", "Average (Mbit/s)"], ["t", "p2", "f1", "t", "f1"],
                              [[r["link"], r["av"], r["downMin"], r["status"], r["avg"]] for r in N["rank"][:15]]))
    if N["util"]:
        s["tables"].append(_table("Highest utilization", ["Link", "Average (Mbit/s)", "Peak (Mbit/s)", "Capacity (Mbit/s)", "Peak utilization", "Status"], ["t", "f1", "f1", "f0", "p1", "t"],
                                  [[r["link"], r["avg"], r["max"], r["cap"], r["uP"], r["ust"]] for r in N["util"][:10]]))
    if N["bad"]:
        s["attention"].append(f"{N['bad']} link{'s' if N['bad'] != 1 else ''} below the availability target")
    if N["nodata"]:
        s["attention"].append(f"{N['nodata']} link{'s' if N['nodata'] != 1 else ''} with too little data (coverage below the limit)")
    if N.get("unmappedIsp"):
        s["attention"].append(f"{len(N['unmappedIsp'])} links do not match any ISP")
    return s


def _soc_site(db, cfg, f):
    """NDR for one location: the firewalls that belong to it (Panorama device names), from the per-firewall data."""
    F = SOCFW.build(db, cfg, f.d_from, f.d_to, f.site)
    s = {"key": "soc", "title": "NDR (Palo Alto)", "kpis": [], "charts": [], "tables": [], "notes": [], "attention": []}
    if not F["nFw"]:
        s["notes"].append(f"No firewall data for {f.site} in this period. The location needs a firewall matched to it, and per-firewall data is collected from the first Panorama sync after the update.")
        return s
    T = F["total"]
    s["kpis"] = [_kpi("Threat events", T["events"], "n", fmt_n(F["nFw"]) + " firewall" + ("s" if F["nFw"] > 1 else "")), _kpi("Critical + High", T["ch"], "n", fmt_n(T["crit"]) + " critical"),
                 _kpi("Blocked", T["blocked"] / T["events"] if T["events"] else None, "p1", "actions other than alert"), _kpi("Traffic (TB)", T["bytes"] / 1e12, "f2", ""), _kpi("Sessions", T["sessions"], "n", "")]
    d = F["days"]
    s["kpis"].append(_kpi("Top threat category", F["cat"][0]["k"] if F["cat"] else None, "t", fmt_n(F["cat"][0]["n"]) + " events" if F["cat"] else ""))
    s["charts"] = [_daily("Threat events by severity", [x["date"] for x in d], [{"name": n, "values": [x[k] for x in d]} for n, k in (("Critical", "critical"), ("High", "high"), ("Other", "other"))], "stack"),
                   _chart("Events per severity", [x["k"] for x in F["sev"]], [{"name": "Events", "values": [x["n"] for x in F["sev"]]}], "donut"),
                   _top("Firewall actions", [(x["k"], x["n"]) for x in F["act"]], "Events"),
                   _daily("Blocked events", [x["date"] for x in d], [{"name": "Blocked", "values": [x["blocked"] for x in d]}]),
                   _daily("Traffic (GB)", [x["date"] for x in d], [{"name": "GB", "values": [round(x["bytes"] / 1e9, 2) for x in d]}]),
                   _top("Top threat categories", [(x["k"], x["n"]) for x in F["cat"]], "Events"),
                   _top("Top threat types", [(x["k"], x["n"]) for x in F["typ"]], "Events"),
                   _top("Top applications by volume (GB)", [(x["k"], round(x["n"] / 1e9, 1)) for x in F["app"]], "GB"),
                   _top("Top source IPs by traffic (GB)", [(x["k"], round(x["n"] / 1e9, 1)) for x in F["src"]], "GB")]
    s["charts"] = [c for c in s["charts"] if c]
    s["tables"].append(_table("Firewalls", ["Firewall", "Events", "Critical", "High", "Blocked", "Traffic (GB)", "Sessions"], ["t", "n", "n", "n", "n", "f1", "n"],
                              [[x["fw"], x["events"], x["crit"], x["high"], x["blocked"], x["bytes"] / 1e9, x["sessions"]] for x in F["fw"]]))
    if F["from"] and F["from"] > f.d_from.isoformat():
        s["notes"].append(f"Per-firewall data starts on {F['from']}; earlier days of the period are not included.")
    return s


def _soc(db, cfg, f, preset="standar"):
    if f.site:
        return _soc_site(db, cfg, f)
    S = VW._soc(db, cfg, f.d_from, f.d_to)
    R = S["R"]
    s = {"key": "soc", "title": "NDR (Palo Alto)", "kpis": [], "charts": [], "tables": [], "notes": [], "attention": []}
    if not R["hasData"]:
        s["notes"].append("No validated SOC data in this period.")
        return s
    bt = SOC.batch_for(S["batches"], f.d_from, f.d_to)
    tabs = {t["id"]: t["r"] for t in (bt.tables if bt and bt.tables else [])}
    K = (bt.kpi if bt and bt.kpi else None) or {}
    first = lambda tid, i: (tabs.get(tid) or [[None] * (i + 1)])[0][i]
    top = lambda tid, li, vi, name: _top(name, [(r[li], r[vi]) for r in tabs.get(tid, [])], "Count")
    SEV = cfg.p("soc.severities")
    d = R["daily"]
    s["kpis"] = [
        _kpi("Total threat events", R["total"], "n", fmt_n(R["perDay"]) + " per day"),
        _kpi("Critical + High", R["ch"], "n", fmt_n(R["crit"]) + " critical"),
        _kpi("Critical + High blocked", R["chBlkPct"], "p1", "actions other than alert"),
        _kpi("Critical + High alert only", R["chAlert"], "n", "logged, not stopped"),
        _kpi("Internal-source events", R["internalPct"], "p1", "of total events"),
        _kpi("Internal hosts detected", K.get("hosts"), "n", fmt_n(K.get("hostsCH")) + " with critical/high" if K.get("hostsCH") is not None else ""),
        _kpi("Top source countries", first("negara", 0), "t", fmt_n(first("negara", 1)) + " event" if tabs.get("negara") else ""),
        _kpi("Top source IPs", first("ip", 0), "t", fmt_n(first("ip", 3)) + " event" if tabs.get("ip") else ""),
        _kpi("URLs blocked", R["urlBlk"], "n", "of " + fmt_n(R["url"]) + " URL events"),
        _kpi("Total traffic (TB)", R["tb"], "f1", ""),
        _kpi("Top application", K.get("topApp"), "t", fmt_p(K["topAppPct"], 0) + " of volume" if K.get("topAppPct") is not None else ""),
        _kpi("Risky applications seen", K.get("watchSeen"), "n", "from the watch list")]
    s["charts"] = _pick(cfg, "soc", SOC_IDS, preset, [
        _chart("Events per severity", [x["k"] for x in R["sev"]], [{"name": "Event", "values": [x["n"] for x in R["sev"]]}], "hbar"),
        _daily("Threat events by severity", [x["date"] for x in d], [{"name": sv, "values": [x.get(sv, 0) for x in d]} for sv in SEV], "stack"),
        _top("Firewall actions", [(x["k"], x["n"]) for x in R["action"]], "Event"),
        _top("Top 10 threat categories", [(x["k"], x["n"]) for x in R["cat"]], "Event"),
        top("negara", 0, 1, "Top 10 attack source countries"),
        top("ip", 0, 3, "Top 10 attack source IPs"),
        top("host", 0, 1, "Top 10 internal hosts by detections"),
        _top("Blocked URL categories", [(x["k"], x["blk"]) for x in R["urlCat"]], "Blocked"),
        top("app", 0, 2, "Top 10 applications by volume (GB)"),
        top("appcat", 0, 1, "Volume per application category (GB)"),
        _daily("Traffic (TB)", [x["date"] for x in d], [{"name": "TB", "values": [round(x["tb"], 2) for x in d]}])])
    heads = ["", "Events", "% of total", "Blocked", "Alert only", "% blocked"]
    kinds = ["t", "n", "p1", "n", "n", "p1"]
    for title, key, first_col in (("Events per severity", "sev", "Severity"), ("Event per tipe ancaman", "type", "Tipe"), ("Event per tindakan firewall", "action", "Action")):
        rows = R.get(key) or []
        if rows:
            s["tables"].append(_table(title, [first_col] + heads[1:], kinds, [[r["k"], r["n"], r["pct"], r["blk"], r["alert"], r["blkPct"]] for r in rows]))
    if R["urlCat"]:
        s["tables"].append(_table("URLs by category", ["Category", "Access", "% of total", "Blocked", "Alert only"], ["t", "n", "p1", "n", "n"],
                                  [[r["k"], r["n"], r["pct"], r["blk"], r["alert"]] for r in R["urlCat"][:10]]))
    if R["chAlert"]:
        s["attention"].append(f"{fmt_n(R['chAlert'])} critical/high events alert only, not blocked")
    for kind, rows in (R.get("unknown") or {}).items():
        s["attention"].append(_UK[kind] + " not in the parameter list: " + ", ".join(x[0] for x in rows))
    return s


DEV_IDS = ["dev_status", "dev_kind", "dev_down_loc", "dev_age", "dev_type", "dev_h_daily", "dev_h_events", "dev_h_loc", "dev_h_type"]
WIFI_IDS = ["wifi_ssid", "wifi_ssid_gb", "wifi_ap", "wifi_zone", "wifi_band", "wifi_trend", "wifi_h_daily", "wifi_h_sessions", "wifi_h_zone", "wifi_h_ssid", "wifi_h_loc", "wifi_h_hours", "wifi_h_device"]
_GB = 1073741824


def _devices(db, cfg, f, preset="standar"):
    """Status perangkat adalah kondisi terkini dari Zabbix saat laporan dibuat; periode tidak berlaku."""
    from .calc import devices as DEV
    D = DEV.build(db, cfg, f.site, "", "", full=False)
    H = DEV.history(db, cfg, f.d_from, f.d_to, f.site)
    s = {"key": "devices", "title": "Devices", "kpis": [], "charts": [], "tables": [], "notes": [], "attention": []}
    A = D["all"]
    if not D["configured"] or not A["total"]:
        s["notes"].append("No device data from Zabbix yet." + (" Last sync failed: " + D["error"] if D["error"] else ""))
        return s
    s["notes"].append("Device status is a Zabbix snapshot at report time; incidents and downtime follow the report period" + (" (recorded since " + H["since"][:10] + ")" if H.get("since") else "") + ".")
    s["kpis"] = [_kpi("Devices", A["total"], "n", "monitored from Zabbix"), _kpi("Online", A["up"], "n", fmt_p(A["avail"], 1) + " of the active ones" if A["avail"] is not None else ""),
                 _kpi("Down", A["down"], "n", f"{D['chronic']} over {D['chronicDays']} days"), _kpi("Availability Now", A["avail"], "p2", "online ÷ (online + down)"),
                 _kpi("Interface Issue", A["deg"], "n", "ping OK, SNMP/agent unavailable"), _kpi("Maintenance", A["maint"], "n", "disabled in Zabbix: " + fmt_n(A["off"]))]
    bk, bl, bt = D["byKind"], sorted(D["byLoc"], key=lambda r: -r["down"]), D["byType"]
    s["charts"] = _pick(cfg, "devices", DEV_IDS, preset, [
        _chart("Device status", ["Online", "Down", "Interface", "Maintenance"], [{"name": "Devices", "values": [A["up"], A["down"], A["deg"], A["maint"]]}], "donut"),
        _chart("Status per category", [r["k"] for r in bk], [{"name": "Online", "values": [r["up"] for r in bk]}, {"name": "Down", "values": [r["down"] for r in bk]}], "stack"),
        _top("Top 10 locations by devices down", [(r["k"], r["down"]) for r in bl], "Down"),
        _chart("Distribution of device down time", [x["k"] for x in D["ageDist"]], [{"name": "Devices", "values": [x["n"] for x in D["ageDist"]]}]),
        _top("Top 10 device types", [(r["k"], r["total"]) for r in sorted(bt, key=lambda r: -r["total"])], "Devices"),
        _daily("Downtime of all devices (hours)", [x["date"] for x in H["daily"]], [{"name": "Hours", "values": [x["hours"] for x in H["daily"]]}]),
        _daily("Down incidents", [x["date"] for x in H["daily"]], [{"name": "Incidents", "values": [x["events"] for x in H["daily"]]}]),
        _top("Top 10 locations by downtime in the period (hours)", [(r["k"], r["hours"]) for r in H["byLoc"]], "Hours"),
        _top("Top 10 device types by downtime in the period (hours)", [(r["k"], r["hours"]) for r in H["byType"]], "Hours")])
    s["kpis"] += [_kpi("Down incidents (period)", H["events"], "n", "incidents from Zabbix"), _kpi("Period downtime (hours)", H["hours"], "f0", fmt_n(H["hosts"]) + " devices affected"),
                  _kpi("Average recovery (hours)", H["mttr"], "f1", "resolved incidents"), _kpi("Period availability", H["avail"], "p2", "1 − downtime ÷ (devices × period)")]
    s["tables"].append(_table("Downtime per location (period)", ["Location", "Incidents", "Downtime (h)", "Devices", "Availability"], ["t", "n", "f1", "n", "p1"], [[r["k"], r["events"], r["hours"], r["hosts"], r["avail"]] for r in H["byLoc"]]))
    s["tables"].append(_table("Downtime per device type (period)", ["Type", "Incidents", "Downtime (h)", "Devices"], ["t", "n", "f1", "n"], [[r["k"], r["events"], r["hours"], r["hosts"]] for r in H["byType"]]))
    s["tables"].append(_table("Most frequently down devices (period)", ["Device", "Incidents", "Downtime (h)"], ["t", "n", "f1"], [[r["k"], r["events"], r["hours"]] for r in H["byHost"]]))
    s["tables"].append(_table("Dominant problems (period)", ["Problem", "Incidents", "Downtime (h)"], ["t", "n", "f1"], [[r["k"], r["events"], r["hours"]] for r in H["byProb"]]))
    s["tables"].append(_table("Per category", ["Category", "Devices", "Online", "Down", "Interface", "Availability"], ["t", "n", "n", "n", "n", "p1"], [[r["k"], r["total"], r["up"], r["down"], r["deg"], r["avail"]] for r in bk]))
    s["tables"].append(_table("Per device type", ["Type", "Code", "Devices", "Down", "Availability"], ["t", "t", "n", "n", "p1"], [[r["k"], r["code"], r["total"], r["down"], r["avail"]] for r in bt]))
    s["tables"].append(_table("Per location", ["Location", "Devices", "Down", "Interface", "Availability"], ["t", "n", "n", "n", "p1"], [[r["k"], r["total"], r["down"], r["deg"], r["avail"]] for r in bl[:40]]))
    s["tables"].append(_table("Longest-down devices", ["Device", "Type", "Location", "Duration (h)", "Problem"], ["t", "t", "t", "f1", "t"],
                              [[x["name"], x.get("typeLabel"), x["loc"], x["ageH"], x.get("problem")] for x in D["down"][:30]]))
    if A["down"]:
        s["attention"].append(f"{A['down']} devices down, {D['chronic']} of them over {D['chronicDays']} days")
    if D["unmapped"]:
        s["attention"].append(f"{len(D['unmapped'])} Zabbix location codes are not mapped to a location")
    return s


def _wifi(db, cfg, f, preset="standar"):
    """Client WiFi aktif dan Access Point dari Ruckus vSZ: kondisi terkini saat laporan dibuat; usage = trafik sesi yang sedang berjalan."""
    from .calc import wifi as WIFI
    W = WIFI.build(db, cfg)
    Hh = WIFI.history(db, cfg, f.d_from, f.d_to, site=f.site)
    s = {"key": "wifi", "title": "WiFi (Ruckus)", "kpis": [], "charts": [], "tables": [], "notes": [], "attention": []}
    if not W["configured"] or not (W["total"] or W["apTotal"]):
        s["notes"].append("No WiFi data from Ruckus vSZ yet." + (" Last sync failed: " + W["error"] if W["error"] else ""))
        return s
    s["notes"].append("Status figures are a Ruckus vSZ snapshot at report time; usage, clients, and sessions follow the report period" + (" (recorded since " + Hh["since"][:10] + ")" if Hh.get("since") else "") + ".")
    s["kpis"] = [_kpi("Active clients", W["total"], "n", "connected now"), _kpi("Logged-in users", W["users"], "n", f"{fmt_n(W['named'])} clients with a username"),
                 _kpi("Access Points online", W["apOnline"], "n", f"of {fmt_n(W['apTotal'])} APs"), _kpi("Weak signal", W["weak"], "n", f"below {W['weakAt']} dBm"),
                 _kpi("Download (GB)", W["tx"] / _GB, "f1", "sesi berjalan"), _kpi("Upload (GB)", W["rx"] / _GB, "f1", "sesi berjalan")]
    tr = W["trend"]
    s["charts"] = _pick(cfg, "wifi", WIFI_IDS, preset, [
        _top("Clients per SSID", [(x["k"], x["n"]) for x in W["bySsid"]], "Client"),
        _top("Usage per SSID (GB)", [(x["k"], round(x["n"] / _GB, 2)) for x in W["bySsidBytes"]], "GB"),
        _top("Clients per Access Point", [(x["k"], x["n"]) for x in W["byAp"]], "Client"),
        _top("Clients per zone", [(x["k"], x["n"]) for x in W["byZone"]], "Client"),
        _chart("Clients per band", [x["k"] for x in W["byBand"]], [{"name": "Client", "values": [x["n"] for x in W["byBand"]]}], "donut"),
        _chart("Clients over the last 24 hours", [f"{(x['t'] // 3600000) % 24:02d}.{(x['t'] // 60000) % 60:02d}" for x in tr], [{"name": "Client", "values": [x["c"] for x in tr]}], "line") if len(tr) > 1 else None,
        _daily("WiFi usage (GB)", [x["date"] for x in Hh["daily"]], [{"name": "GB", "values": [round(x["bytes"] / _GB, 2) for x in Hh["daily"]]}]),
        _daily("Unique clients and sessions", [x["date"] for x in Hh["daily"]], [{"name": "Client unik", "values": [x["clients"] for x in Hh["daily"]]}, {"name": "Sesi", "values": [x["sessions"] for x in Hh["daily"]]}]),
        _top("Usage per zone in the period (GB)", [(x["k"], round(x["bytes"] / _GB, 2)) for x in Hh["byZone"]], "GB"),
        _top("Usage per SSID in the period (GB)", [(x["k"], round(x["bytes"] / _GB, 2)) for x in Hh["bySsid"]], "GB"),
        _top("Usage per location in the period (GB)", [(x["k"], round(x["bytes"] / _GB, 2)) for x in Hh["byLoc"]], "GB"),
        _chart("Session start hour", [f"{h:02d}" for h in range(24)], [{"name": "Sesi", "values": Hh["hours"]}]),
        _top("Dominant devices in the period (GB)", [(x["k"], round(x["bytes"] / _GB, 2)) for x in Hh["byDevice"]], "GB")])
    s["kpis"] += [_kpi("Sessions (period)", Hh["sessions"], "n", ""), _kpi("Unique clients (period)", Hh["clients"], "n", "distinct MACs"), _kpi("Total usage (GB)", (Hh["rx"] + Hh["tx"]) / _GB, "f1", "report period"),
                  _kpi("Average usage per client (GB)", (Hh["rx"] + Hh["tx"]) / _GB / Hh["clients"] if Hh["clients"] else None, "f2", "")]
    for ttl, key, nm in (("Usage per zone (period)", "byZone", "Zone"), ("Usage per SSID (period)", "bySsid", "SSID"), ("Usage per location (period)", "byLoc", "Location"), ("Usage per AP (period)", "byAp", "AP")):
        s["tables"].append(_table(ttl, [nm, "Client unik", "Sesi", "Penggunaan (GB)"], ["t", "n", "n", "f2"], [[x["k"], x["clients"], x["sessions"], x["bytes"] / _GB] for x in Hh[key]]))
    s["tables"].append(_table("Clients with the most usage (period)", ["User / Host", "MAC", "SSID", "Sessions", "Usage (GB)"], ["t", "t", "t", "n", "f2"],
                              [[x["user"] or x["host"], x["mac"], x["ssid"], x["sessions"], x["bytes"] / _GB] for x in Hh["top"]]))
    s["tables"].append(_table("Per SSID", ["SSID", "Client", "Penggunaan (GB)"], ["t", "n", "f2"], [[x["k"], x["n"], 0] for x in W["bySsid"]]))
    gb = dict((x["k"], x["n"]) for x in W["bySsidBytes"])
    s["tables"][-1]["rows"] = [[x["k"], x["n"], gb.get(x["k"], 0) / _GB] for x in W["bySsid"]]
    s["tables"].append(_table("Clients with the most usage", ["User / Host", "MAC", "SSID", "AP", "Download (GB)", "Upload (GB)"], ["t", "t", "t", "t", "f2", "f2"],
                              [[x["user"] or x["host"], x["mac"], x["ssid"], x["ap"], (x["tx"] or 0) / _GB, (x["rx"] or 0) / _GB] for x in W["top"]]))
    if W["apDown"]:
        s["tables"].append(_table("Access Points not online", ["AP", "Zone", "Status", "Model"], ["t", "t", "t", "t"], [[x["name"], x["zone"], x["status"], x["model"]] for x in W["apDown"][:30]]))
        s["attention"].append(f"{len(W['apDown'])} Access Points not online of {W['apTotal']}")
    if W["weak"]:
        s["attention"].append(f"{W['weak']} clients with weak signal (below {W['weakAt']} dBm)")
    return s

XDR_IDS = ["xdr_sev", "xdr_daily", "xdr_models", "xdr_status"]


def _xdr(db, cfg, f, preset="standar"):
    """Alert Workbench Trend Micro Vision One pada periode laporan (menurut waktu alert dibuat)."""
    from .calc import xdr as XDR
    X = XDR.build(db, cfg, f.d_from, f.d_to)
    s = {"key": "xdr", "title": "XDR (Trend Micro)", "kpis": [], "charts": [], "tables": [], "notes": [], "attention": []}
    if f.site:
        s["notes"].append("XDR alerts are not split by location (Vision One reports the host, not the branch); the figures below cover all locations.")
    if not X["configured"] or not X["total"]:
        s["notes"].append("No XDR alerts in this period." + (" Last sync failed: " + X["error"] if X["error"] else ""))
        return s
    sev = {x["k"]: x["n"] for x in X["bySev"]}
    s["kpis"] = [_kpi("Alerts", X["total"], "n", "in the period"), _kpi("Still open", X["open"], "n", "not Closed yet"), _kpi("Critical", sev.get("critical", 0), "n", ""), _kpi("High", sev.get("high", 0), "n", ""),
                 _kpi("Average score", X["avgScore"], "f1", "0 to 100"), _kpi("Backlog critical/high", X["backlogCH"], "n", "open now, all periods")]
    d = X["daily"]
    s["charts"] = _pick(cfg, "xdr", XDR_IDS, preset, [
        _chart("Alerts per severity", [x["k"].capitalize() for x in X["bySev"]], [{"name": "Alert", "values": [x["n"] for x in X["bySev"]]}], "donut"),
        _daily("Alerts", [x["date"] for x in d], [{"name": k.capitalize(), "values": [x[k] for x in d]} for k in XDR.SEV], "stack"),
        _top("Top 10 detection models", [(x["k"], x["n"]) for x in X["byModel"]], "Alert"),
        _chart("Investigation status", [x["k"] for x in X["byStatus"]], [{"name": "Alert", "values": [x["n"] for x in X["byStatus"]]}])])
    s["tables"].append(_table("Top detection models", ["Model", "Alert"], ["t", "n"], [[x["k"], x["n"]] for x in X["byModel"]]))
    s["tables"].append(_table("Latest critical and high alerts", ["Time", "Severity", "Model", "Skor", "Status"], ["t", "t", "t", "n", "t"],
                              [[datetime.utcfromtimestamp(x["created"] / 1000).strftime("%d/%m %H.%M"), x["severity"], x["model"], x["score"], x["status"]] for x in X["list"] if x["severity"] in ("critical", "high")][:25]))
    i = X["impact"]
    if X["backlogCH"]:
        s["attention"].append(f"{X['backlogCH']} critical/high alerts still open")
    return s

def _internet(db, cfg, f, preset="standar"):
    """Internet usage from Palo Alto (Panorama): traffic, applications, web categories, and top users per location, taken from the per-firewall daily data."""
    F = SOCFW.build(db, cfg, f.d_from, f.d_to, f.site)
    s = {"key": "internet", "title": "Internet Usage", "kpis": [], "charts": [], "tables": [], "notes": [], "attention": []}
    if not F["nFw"] or not F["total"]["bytes"]:
        s["notes"].append("No Palo Alto traffic data" + (f" for {f.site}" if f.site else "") + " in this period.")
        return s
    T, d = F["total"], F["days"]
    busy = max(d, key=lambda x: x["bytes"])
    secs = F["dayN"] * 86400
    s["kpis"] = [_kpi("Total traffic (TB)", T["bytes"] / 1e12, "f2", fmt_n(F["nFw"]) + " firewall" + ("s" if F["nFw"] > 1 else "")), _kpi("Average bandwidth (Mb/s)", T["bytes"] * 8 / secs / 1e6 if secs else None, "f1", "over the days with data"),
                 _kpi("Busiest day", busy["bytes"] / 1e9, "f1", _short(busy["date"]) + " (GB)"), _kpi("Sessions", T["sessions"], "n", ""), _kpi("Web requests", F["webTotal"] or None, "n", "all URL categories")]
    s["charts"] = [c for c in (_daily("Traffic (GB)", [x["date"] for x in d], [{"name": "GB", "values": [round(x["bytes"] / 1e9, 1) for x in d]}]),
                               None if f.site else _top("Traffic per location (GB)", [(x["site"], round(x["bytes"] / 1e9, 1)) for x in sorted(F["bySite"], key=lambda x: -x["bytes"])], "GB"),
                               _top("Top applications by volume (GB)", [(x["k"], round(x["n"] / 1e9, 1)) for x in F["app"]], "GB"), _top("Traffic by application category (GB)", [(x["k"], round(x["n"] / 1e9, 1)) for x in F["acat"]], "GB"),
                               _top("Top source networks by traffic (GB)", [(x["k"], round(x["n"] / 1e9, 1)) for x in F["src"]], "GB"), _top("Top source networks by web requests", [(x["k"], x["n"]) for x in F["webu"]], "Requests"),
                               _top("Web categories logged (requests)", [(x["k"], x["n"]) for x in F["urlc"]], "Requests")) if c]
    if not f.site:
        s["tables"].append(_table("Traffic per location", ["Location", "Traffic (GB)", "Share", "Firewalls"], ["t", "f1", "p1", "n"], [[x["site"], x["bytes"] / 1e9, x["bytes"] / T["bytes"], x["fw"]] for x in sorted(F["bySite"], key=lambda x: -x["bytes"])]))
    s["tables"].append(_table("Top source networks by traffic", ["Network (/24)", "Traffic (GB)"], ["t", "f1"], [[x["k"], x["n"] / 1e9] for x in F["src"]]))
    if F["detailFrom"] and F["detailFrom"] > f.d_from.isoformat():
        s["notes"].append(f"Application categories and web data are collected since {F['detailFrom']}; earlier days of the period are not included in them.")
    return s


_BUILD = {"servicedesk": _servicedesk, "internet": _internet, "noc": _noc, "soc": _soc, "devices": _devices, "wifi": _wifi, "xdr": _xdr}

# Jenis laporan (bisa diubah di Admin → Operasional → Target dan Parameter → report.kinds). sections: None = semua bagian yang boleh dilihat role.
DEFAULT_KINDS = {
    "summary": {"label": "Summary", "desc": "Management summary: key figures and main charts of all areas", "title": "IT Operation Center - Summary Report", "subtitle": "Management overview of all areas", "prefix": "Management", "sections": None, "summary": True},
    "noc": {"label": "Links (PRTG)", "desc": "Availability, downtime, problem links, utilization", "title": "IT Operation Center - Links (PRTG) Report", "subtitle": "Availability, downtime, and traffic of ISP links", "prefix": "Links", "sections": ["noc"]},
    "soc": {"label": "NDR (Palo Alto)", "desc": "Threat events, severity, firewall actions, URLs", "title": "IT Operation Center - NDR (Palo Alto) Report", "subtitle": "Threats, firewall actions, and high/critical triage", "prefix": "NDR", "sections": ["soc"]},
    "servicedesk": {"label": "Ticketing", "desc": "Tickets received, SLA, categories, technician ranking, open tickets", "title": "IT Operation Center - Ticketing Report", "subtitle": "ManageEngine service desk performance", "prefix": "Ticketing", "sections": ["servicedesk"]},
    "xdr": {"label": "XDR (Trend Micro)", "desc": "Vision One alerts: severity, detection models, status, backlog", "title": "IT Operation Center - XDR (Trend Micro) Report", "subtitle": "Vision One Workbench alerts", "prefix": "XDR", "sections": ["xdr"]},
    "devices": {"label": "Devices", "desc": "Zabbix device status: category, type, location, devices down", "title": "IT Operation Center - Devices Report", "subtitle": "Device status from Zabbix", "prefix": "Devices", "sections": ["devices"]},
    "wifi": {"label": "WiFi (Ruckus)", "desc": "Active clients, Access Points, usage per SSID and AP", "title": "IT Operation Center - WiFi (Ruckus) Report", "subtitle": "Clients and Access Points from Ruckus vSZ", "prefix": "WiFi", "sections": ["wifi"]},
    "network": {"label": "Network (PRTG + WiFi)", "desc": "PRTG links and Ruckus WiFi together", "title": "IT Operation Center - Network Report", "subtitle": "ISP links, WiFi, and internet usage", "prefix": "Network", "sections": ["noc", "wifi", "internet"]},
    "cyber": {"label": "Cyber Security (NDR + XDR)", "desc": "Palo Alto NDR and Trend Micro XDR together", "title": "IT Operation Center - Cyber Security Report", "subtitle": "Palo Alto NDR and Trend Micro XDR", "prefix": "Cyber", "sections": ["soc", "xdr"]},
    "internet": {"label": "Internet Usage", "desc": "Traffic, applications, web categories, and top users per location (Palo Alto)", "title": "IT Operation Center - Internet Usage Report", "subtitle": "Traffic, applications, and users per location", "prefix": "Internet Usage", "sections": ["internet"]},
    "full": {"label": "Full", "desc": "Summary and details of all areas in one file", "title": "IT Operation Center - Full Report", "subtitle": "Summary and details of all areas", "prefix": "", "sections": None},
}


_ORDER = ["summary", "network", "cyber", "servicedesk", "noc", "wifi", "internet", "soc", "xdr", "devices", "full"]
DEFAULT_KINDS = {k: DEFAULT_KINDS[k] for k in _ORDER}


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
    p = lambda d, y=True: f"{d.day} {cfg.p('ui.months')[d.month - 1]}" + (f" {d.year}" if y else "")
    if d1 == d2:
        return p(d1)
    return (p(d1, False) if d1.year == d2.year else p(d1)) + " – " + p(d2)


LIMITS = {"ringkas": (4, 2, 1, 5), "standar": (8, 4, 3, 10)}      # key figures, charts, tables, rows per table; "lengkap" is not limited


def _compact(s, preset):
    lim = LIMITS.get(preset)
    if not lim:
        return
    k, c, t, r = lim
    s["kpis"], s["charts"] = s["kpis"][:k], s["charts"][:c]
    out, used = [], 0
    for tb in s["tables"][:t]:
        keep = min(len(tb["rows"]), r)
        if out and used + keep > 24:                                 # a page holds about 24 table rows besides the figures: stop before a table spills over
            break
        used += keep
        out.append(tb)
    if len(out) == 1 and preset == "standar":                          # a single table may use the free space
        r = 15
    s["tables"] = [{**tb, "rows": tb["rows"][:r], "title": f"{tb['title']} (top {r} of {len(tb['rows'])})"} if len(tb["rows"]) > r else tb for tb in out]


def build(db, cfg, user, f, kind="full", preset="standar"):
    """kind = kunci jenis laporan. Bagian di luar izin role dibuang diam-diam."""
    ks = kinds_for(cfg, user)
    if kind.startswith("custom:"):                                  # custom: any combination of sections the role may see, e.g. custom:servicedesk,devices
        titles = dict(SECTIONS)
        keys = [x for x, _ in SECTIONS if x in kind[7:].split(",") and can_see(user, x)]
        spec = {"key": "custom", "label": "Custom", "desc": "", "title": "IT Operation Center - Custom Report", "subtitle": " + ".join(titles[x] for x in keys), "prefix": "", "sections": keys, "allowed": keys} if keys else None
    else:
        spec = ks.get(kind) or ks.get("full") or (next(iter(ks.values())) if ks else None)
    if spec is None:
        return {"title": cfg.p("ui.brand_name", "Dashboard"), "sections": [], "kinds": []}
    link_opts = _link_options(db, cfg, f)
    isps = sorted({x[2] for x in link_opts})
    if getattr(f, "risp", "") not in isps:
        f.risp = ""
    link_opts = [x for x in link_opts if not f.risp or x[2] == f.risp]
    if getattr(f, "rlink", "") not in [str(x[0]) for x in link_opts]:
        f.rlink = ""
    secs = [_BUILD[k](db, cfg, f, preset) for k in spec["allowed"]]
    for s_ in secs:
        _compact(s_, preset)
    single = len(spec["allowed"]) == 1 and spec.get("sections")
    for s in secs:
        s["prefix"] = spec["prefix"] if single and spec.get("prefix") else s["title"]
    overview = {"key": "ringkasan", "title": "Summary", "kpis": [], "charts": [], "tables": [], "notes": []}
    att = []
    for s in secs:
        for k in s["kpis"][:2]:
            overview["kpis"].append({**k, "label": s["title"] + " · " + k["label"], "sec": s["key"], "sec_title": s["title"]})
        if s["charts"]:
            overview["charts"].append({**s["charts"][0], "title": s["title"] + " · " + s["charts"][0]["title"]})
        att += [[s["title"], a] for a in s["attention"]]
    overview["charts"] = overview["charts"][:4]
    if att:
        overview["tables"].append(_table("Needs attention", ["Area", "Finding"], ["t", "t"], att))
    filt = []
    if f.shift:
        filt.append("Shift: " + next((x["name"] for x in cfg.shifts if x["no"] == f.shift), str(f.shift)))
    filt.append("Location: " + (f.site or "All locations"))
    if getattr(f, "rgrp", ""):
        filt.append("Group: " + f.rgrp)
    if getattr(f, "rtech", ""):
        filt.append("Technician: " + next((p["name"].strip() for p in cfg.people if p["sys"] == f.rtech), f.rtech))
    if f.risp:
        filt.append("ISP: " + f.risp)
    if f.rlink:
        filt.append("Link: " + next((n for i, n, _ in link_opts if str(i) == f.rlink), f.rlink))
    summary = bool(spec.get("summary"))
    if preset == "lengkap" or f.rlink or f.risp:              # per-link graphs follow the PRTG section; the overview does not use them
        secs = [x for s in secs for x in ([s] + [d for d in [_noc_links(db, cfg, f)] if d] if s["key"] == "noc" else [s])]
    body = [overview] if summary else ([overview] if overview["kpis"] and len(secs) > 1 else []) + secs
    return {"title": cfg.p("ui.brand_name", "Dashboard"), "kind": spec["key"], "subtitle": spec["title"], "tagline": spec["subtitle"], "prefix": spec.get("prefix", ""),
            "company": cfg.p("report.company", ""), "contact": cfg.p("report.contact", {}), "period": _period(cfg, f.d_from, f.d_to),
            "preset": preset, "filters": filt, "generated": cfg.now().strftime("%d/%m/%Y %H.%M") + " WIB", "by": user.full_name, "sections": body,
            "kinds": [{"key": k, "label": v["label"], "desc": v["desc"], "sections": v["allowed"]} for k, v in ks.items()],
            "avail": [{"key": x, "label": t} for x, t in SECTIONS if can_see(user, x)], "isps": isps, "links": [{"key": str(i), "label": n} for i, n, _ in link_opts], "groups": SD.group_names(cfg), "techs": [{"key": p["sys"], "label": p["name"].strip()} for p in sorted(cfg.people, key=lambda p: p["name"].strip()) if p["sys"] and not p["is_shared"] and not p["exclude_rank"]]}
