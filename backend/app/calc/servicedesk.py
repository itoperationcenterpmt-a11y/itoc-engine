"""Service Desk — port dari tkCalc (sheet Perhitungan, 1_Dashboard_Service_Desk).
Semua ambang, daftar status, kelompok durasi, dimensi, dan pemeriksaan kualitas diambil dari Config."""
from datetime import datetime, timedelta, date
from ..store import Config
from ..timeutil import ms
from .common import avg, median, pctl, r4, iso, top_by, total

# indeks kolom tiket ringkas (sama dengan versi Excel/JS)
F = {"id": 0, "mode": 1, "requester": 2, "site": 3, "category": 4, "subcategory": 5, "subject": 6, "technician": 7, "sla_name": 8,
     "impact": 9, "priority": 10, "urgency": 11, "created_at": 12, "resolved_at": 13, "onhold_h": 14, "status": 15, "desc_empty": 16}


def as_rows(tickets) -> list[list]:
    return [[t.id, t.mode, t.requester, t.site, t.category, t.subcategory, t.subject, t.technician, t.sla_name, t.impact, t.priority,
             t.urgency, t.created_at, t.resolved_at, t.onhold_h or 0, t.status, 1 if t.desc_empty else 0] for t in tickets]


def derive(t, cfg: Config):
    S, T = t[12], t[13]
    dur = None if (S is None or T is None or T < S) else max(0, r4((T - S).total_seconds() / 3600 - t[14]))
    grp = None
    if dur is not None:
        for i, b in enumerate(cfg.p("sd.duration_buckets")):
            if b["max"] is None or dur <= b["max"]:
                grp = i
                break
    target = cfg.sla.get(t[8])
    sla = "none" if target is None else "na" if dur is None else "in" if dur <= target else "out"
    if T is None:
        pola = "open"
    elif T < S:
        pola = "neg"
    elif T == S:
        pola = "zero"
    else:
        pola = "x24" if round((T - S).total_seconds() / 60) % 1440 == 0 else "ok"
    open_ = t[15] not in cfg.p("sd.closed_statuses")
    na = cfg.p("sd.unassigned")
    miss = sum(1 for f in cfg.p("sd.required_fields") if t[F[f]] == na)
    return {"t": t, "dur": dur, "grp": grp, "sla": sla, "pola": pola, "open": open_, "miss": miss}


def group(D, key, n_total):
    m = {}
    for d in D:
        k = key(d) or "(blank)"
        o = m.setdefault(k, {"k": k, "n": 0, "done": 0, "open": 0, "du": [], "zero": 0, "in": 0, "out": 0})
        o["n"] += 1
        o["open" if d["open"] else "done"] += 1
        if d["dur"] is not None:
            o["du"].append(d["dur"])
        if d["pola"] == "zero":
            o["zero"] += 1
        if d["sla"] == "in":
            o["in"] += 1
        elif d["sla"] == "out":
            o["out"] += 1
    out = [{"k": o["k"], "n": o["n"], "pct": o["n"] / n_total if n_total else 0, "done": o["done"], "open": o["open"], "avg": avg(o["du"]),
            "med": median(o["du"]), "zero": o["zero"], "zeroPct": o["zero"] / o["n"] if o["n"] else None, "in": o["in"], "out": o["out"],
            "inPct": o["in"] / (o["in"] + o["out"]) if o["in"] + o["out"] else None} for o in m.values()]
    return sorted(out, key=lambda x: (-x["n"], x["k"]))


def calc(rows: list[list], cfg: Config, d_from: date, d_to: date, shift: int = 0, people: list[dict] | None = None, now: datetime | None = None) -> dict:
    a = datetime.combine(d_from, datetime.min.time())
    b = datetime.combine(d_to, datetime.min.time()) + timedelta(days=1)
    clk = cfg.clock
    D = [derive(t, cfg) for t in rows if t[12] is not None and a <= t[12] < b and (not shift or clk.shift_of(t[12].hour) == shift)]
    n, days = len(D), (b - a).days
    R = {"n": n, "days": days, "perDay": n / days if days else 0}
    daily, idx = [], {}
    for i in range(days):
        k = iso(a + timedelta(days=i))
        idx[k] = i
        daily.append({"date": k, "in": 0, "done": 0, "backlog": 0})
    after = 0
    for d in D:
        daily[idx[iso(d["t"][12])]]["in"] += 1
        if d["t"][13] is not None:
            k = idx.get(iso(d["t"][13]))
            if k is not None:
                daily[k]["done"] += 1
            elif d["t"][13] >= b:
                after += 1
    ci = cd = 0
    for x in daily:
        ci += x["in"]; cd += x["done"]; x["backlog"] = ci - cd
    R["daily"], R["doneAfter"] = daily, after
    busiest = max(daily, key=lambda x: x["in"], default=None)
    R["busiest"] = busiest if busiest and busiest["in"] else None
    wnames = cfg.p("ui.weekdays")
    wd = [{"n": 0, "days": 0} for _ in range(7)]
    for x in daily:
        wd[date.fromisoformat(x["date"]).weekday()]["days"] += 1
    hours = [0] * 24
    for d in D:
        wd[d["t"][12].weekday()]["n"] += 1
        hours[d["t"][12].hour] += 1
    R["weekday"] = [{"k": wnames[i], "n": x["n"], "days": x["days"], "avg": x["n"] / x["days"] if x["days"] else 0} for i, x in enumerate(wd)]
    wk, we = sum(x["days"] for x in wd[:5]), sum(x["days"] for x in wd[5:])
    R["perWorkday"] = sum(x["n"] for x in wd[:5]) / wk if wk else 0
    R["perWeekend"] = sum(x["n"] for x in wd[5:]) / we if we else 0
    R["hours"], R["peakHour"] = hours, (hours.index(max(hours)) if n else None)
    du = [d["dur"] for d in D if d["dur"] is not None]
    R["open"] = sum(1 for d in D if d["open"])
    R["doneRate"] = (n - R["open"]) / n if n else 0
    R["medMin"] = median(du) * 60 if du else 0
    R["avgH"] = avg(du) if du else 0
    R["p90"] = pctl(du, .9) if du else 0
    cin, cout = sum(1 for d in D if d["sla"] == "in"), sum(1 for d in D if d["sla"] == "out")
    R.update(slaIn=cin, slaOut=cout, slaPct=cin / (cin + cout) if cin + cout else None, noSla=sum(1 for d in D if d["sla"] == "none"),
             zero=sum(1 for d in D if d["pola"] == "zero"), x24=sum(1 for d in D if d["pola"] == "x24"), incomplete=sum(1 for d in D if d["miss"] > 0))
    cum, R["durasi"] = 0, []
    for i, bk in enumerate(cfg.p("sd.duration_buckets")):
        c = sum(1 for d in D if d["grp"] == i)
        cum += c
        R["durasi"].append({"k": bk["label"], "n": c, "pct": c / len(du) if du else 0, "cum": cum / len(du) if du else 0})
    R["over7"] = R["durasi"][-1]["n"] if R["durasi"] else 0
    dims = cfg.p("sd.dims")
    R["dims"] = {k: group(D, lambda d, f=F[v[1]]: d["t"][f], n) for k, v in dims.items()}
    R["topCat"] = (R["dims"].get("kategori") or [None])[0]  # kunci eksplisit: urutan kunci JSONB tidak dijamin sama dengan urutan input
    R["topLoc"] = (R["dims"].get("lokasi") or [None])[0]
    R["requesters"] = [{"k": x["k"], "n": x["sum"], "pct": x["sum"] / n if n else 0} for x in top_by(D, lambda d: d["t"][2], lambda d: 1, 10)]
    # ranking teknisi: roster dari tabel person
    ppl = people if people is not None else cfg.people
    na = cfg.p("sd.unassigned")
    shared = {p["sys"] for p in ppl if p["is_shared"]}
    skip = {na, "(blank)"} | {p["sys"] for p in ppl if p["exclude_rank"]}
    by_tech = {}
    for d in D:
        by_tech.setdefault(d["t"][7] or "(blank)", []).append(d)
    # akun bersama tim jaga (mis. IT Operation Center) diperlakukan sebagai akun personal: ikut ranking bila punya tiket
    roster = [p for p in ppl if not p["is_shared"] and not p["exclude_rank"] and (p["unit"] in cfg.p("sd.rank_units") or p["team_code"] or p["sys"] in by_tech)]
    names = {p["sys"]: p for p in roster}
    for k in by_tech:
        if k not in names and k not in shared and k not in skip:
            names[k] = None
    high = cfg.p("sd.high_priority")
    empty = {"n": 0, "done": 0, "open": 0, "avg": None, "med": None, "zero": 0, "zeroPct": None, "in": 0, "out": 0, "inPct": None}
    rk = []
    for sys, p in names.items():
        L = by_tech.get(sys, [])
        g = (group(L, lambda d: "x", n) or [empty])[0]
        inc = sum(1 for d in L if d["miss"] > 0)
        loc = (top_by(L, lambda d: d["t"][3], lambda d: 1, 1) or [None])[0]
        unit = "" if not p else (p["unit"] + " · " + (p["branch"] or "") if p["branch"] else "Team " + p["team_code"] if p["team_code"] else p["unit"])
        rk.append({"name": p["name"] if p else sys, "unit": unit, **{k: g[k] for k in empty}, "high": sum(1 for d in L if d["t"][10] == high),
                   "inc": inc, "okPct": 1 - inc / g["n"] if g["n"] else None, "loc": loc["k"] if loc else ""})
    # ranking grup: Team ITOC 1-4 dan Head Office. Tiket akun bersama tim jaga masuk ke tim yang bertugas saat tiket dibuat.
    clk, duty = cfg.clock, set(cfg.p("sd.duty_accounts") or [])
    team_by_sys = {p["sys"]: p["team_code"] for p in ppl if p["team_code"]}
    ho_sys = {p["sys"] for p in ppl if (p["branch"] or "").strip().lower() == "head office" and not p["is_shared"]}

    def grp_of(d):
        tech = d["t"][7]
        if tech in team_by_sys:
            return "Team " + team_by_sys[tech]
        if tech in duty:
            c = d["t"][12]
            tm = clk.team_on(clk.duty_date(c), clk.shift_of(c.hour))
            return "Team " + tm["code"] if tm else None
        return "Head Office" if tech in ho_sys else None
    gl = {}
    for d in D:
        k = grp_of(d)
        if k:
            gl.setdefault(k, []).append(d)
    order = ["Team " + t["code"] for t in clk.teams] + ["Head Office"]
    gk = []
    for k in order:
        L = gl.get(k, [])
        g = (group(L, lambda d: "x", n) or [empty])[0]
        mem = sum(1 for p in ppl if p["team_code"] and "Team " + p["team_code"] == k) if k != "Head Office" else len(ho_sys)
        gk.append({"name": k, "members": mem, **{c: g[c] for c in empty}, "high": sum(1 for d in L if d["t"][10] == high)})
    gt = sum(x["n"] for x in gk)
    for x in gk:
        x["rank"] = 1 + sum(1 for y in gk if y["n"] > x["n"])
        x["share"] = x["n"] / gt if gt else 0
    R["groupRanking"] = sorted(gk, key=lambda x: (-x["n"], order.index(x["name"])))
    tot = sum(x["n"] for x in rk)
    for x in rk:
        x["rank"] = 1 + sum(1 for y in rk if y["n"] > x["n"])
        x["share"] = x["n"] / tot if tot else 0
    R["ranking"] = sorted(rk, key=lambda x: (-x["n"], x["name"]))
    R["rankTotal"] = tot
    R["shared"] = sum(1 for d in D if d["t"][7] in shared)
    # kualitas data: definisi pemeriksaan ada di parameter sd.quality_checks
    R["routine"] = sum(1 for d in D if d["t"][5] in cfg.p("sd.routine_subcategories"))
    special = {"zero": R["zero"], "x24": R["x24"], "neg": sum(1 for d in D if d["pola"] == "neg"), "nosla": R["noSla"], "shared": R["shared"],
               "desc_empty": sum(1 for d in D if d["t"][16] == 1), "routine": R["routine"]}
    R["quality"] = []
    for q in cfg.p("sd.quality_checks"):
        c = special[q["rule"]] if q["rule"] in special else sum(1 for d in D if d["t"][F[q["field"]]] == na) if q["rule"] == "unassigned" else 0
        R["quality"].append({"k": q["label"], "n": c, "pct": c / n if n else 0})
    now = now or cfg.now()
    polas = cfg.p("sd.pattern_labels")

    def row(d):
        t = d["t"]
        return {"subj": t[6], "id": t[0], "loc": t[3], "cat": t[4], "tech": t[7], "prio": t[10], "status": t[15], "created": ms(t[12])}
    R["openList"] = [{**row(d), "age": round((now - d["t"][12]).total_seconds() / 8640) / 10} for d in D if d["open"]][:15]
    R["longest"] = [{**row(d), "days": d["dur"] / 24, "pola": polas.get(d["pola"], "")}
                    for d in sorted((d for d in D if d["dur"] is not None), key=lambda d: -d["dur"])[:25]]
    return R
