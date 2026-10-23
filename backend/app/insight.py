"""Automatic insights: statistical analysis of data already stored in the database (no external service, no AI).

Methods: compare the latest value with what is normal (median and robust MAD deviation of earlier data, same weekday when there is a weekly pattern),
trend slopes with a forecast against targets, repeat counts, SLA risk from ticket age, cross-source correlation at the same location, incident grouping,
and a location health score. Every finding carries its numbers and comparison. Findings are stored in the insight table with a unique key; a finding that no
longer appears is closed automatically. A dismissed finding stays hidden for the chosen number of days."""
import statistics
from datetime import date, datetime, timedelta
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session
from . import models as M
from .store import Config

MIN_BASE = 5          # minimum comparison points before something is judged anomalous
ZCUT = 3.0            # robust z threshold
WD = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
CLOSED = ("closed", "resolved", "cancelled", "canceled")


def robust(base: list[float], x: float):
    """(median, deviation, z). Deviation = MAD x 1.4826, or the standard deviation when MAD is 0. None when there is too little comparison data."""
    if len(base) < MIN_BASE:
        return None
    med = statistics.median(base)
    sd = statistics.median([abs(v - med) for v in base]) * 1.4826 or (statistics.pstdev(base) if len(base) > 1 else 0.0)
    z = (x - med) / sd if sd else (0.0 if x == med else (99.0 if x > med else -99.0))
    return med, sd, max(-99.0, min(99.0, z))


def slope(ys: list[float]) -> float:
    """Slope of the linear regression against the day index (per day)."""
    n = len(ys)
    if n < 3:
        return 0.0
    mx, my = (n - 1) / 2, sum(ys) / n
    den = sum((i - mx) ** 2 for i in range(n))
    return sum((i - mx) * (y - my) for i, y in enumerate(ys)) / den if den else 0.0


def fmt(v, d=0) -> str:
    return f"{v:,.{d}f}"


def _ins(key, kind, sev, title, detail, tab, metric=None, site=None):
    return {"key": key, "kind": kind, "severity": sev, "title": title, "detail": detail, "tab": tab, "metric": metric or {}, "site": site}


def _midnight(d: date) -> datetime:
    return datetime.combine(d, datetime.min.time())


def _site_of(db: Session):
    """code -> location name, using the same mapping as the Devices page."""
    from .calc.devices import _alias_map
    amap = _alias_map(db)
    cmap = {m.code.lower(): m.site for m in db.query(M.ZbxLocMap) if m.site}
    return lambda code: cmap.get((code or "").lower()) or amap.get((code or "").lower())


def _sensor_names(db: Session) -> dict:
    sens = list(db.scalars(select(M.PrtgSensor)))
    per: dict = {}
    for x in sens:
        per[x.device] = per.get(x.device, 0) + 1
    return {x.id: ((x.device or x.name) + (f" ({x.name})" if per.get(x.device, 0) > 1 else "")) for x in sens}


def _daily_down(db: Session, start: date, end: date) -> dict:
    """{sensor: {day: minutes down}} from hourly data, days start up to but excluding end."""
    rows = db.execute(select(M.PrtgHourly.sensor_id, func.date(M.PrtgHourly.ts), func.sum(M.PrtgHourly.down_s)).where(M.PrtgHourly.ts >= _midnight(start), M.PrtgHourly.ts < _midnight(end)).group_by(M.PrtgHourly.sensor_id, func.date(M.PrtgHourly.ts))).all()
    out: dict = {}
    for sid, d, down in rows:
        out.setdefault(sid, {})[d] = (down or 0) / 60
    return out


# ---------------- detectors: tickets ----------------
def d_tickets(db: Session, cfg: Config) -> list[dict]:
    """Tickets in on the last full day against the same weekday over the previous 8 weeks."""
    today = cfg.now().date()
    rows = db.execute(select(func.date(M.Ticket.created_at), func.count()).where(M.Ticket.created_at >= _midnight(today - timedelta(days=64))).group_by(func.date(M.Ticket.created_at))).all()
    by = {d: n for d, n in rows}
    last = today - timedelta(days=1)
    if not by:
        return []
    x = by.get(last, 0)
    base = [by.get(last - timedelta(days=7 * k), 0) for k in range(1, 9) if (last - timedelta(days=7 * k)) >= min(by)]
    r = robust(base, x)
    if r and r[2] >= ZCUT and x >= 1.5 * r[0] and x - r[0] >= 5:
        return [_ins(f"ticket_volume:{last}", "tickets", "warn", f"Ticket volume spiked on {WD[last.weekday()]} {last:%d/%m}",
                     f"{x} tickets came in, normally about {fmt(r[0])} on a {WD[last.weekday()]} (last 8 weeks). Check the categories and locations with the most tickets.", "servicedesk",
                     {"value": x, "normal": round(r[0], 1), "z": round(r[2], 1)})]
    return []


def d_ticket_sites(db: Session, cfg: Config) -> list[dict]:
    """Tickets per location on the last full day against the same weekday over the previous 8 weeks."""
    today = cfg.now().date()
    rows = db.execute(select(M.Ticket.site, func.date(M.Ticket.created_at), func.count()).where(M.Ticket.created_at >= _midnight(today - timedelta(days=64)), M.Ticket.site != "").group_by(M.Ticket.site, func.date(M.Ticket.created_at))).all()
    ser: dict = {}
    for s, d, n in rows:
        ser.setdefault(s, {})[d] = n
    last, out = today - timedelta(days=1), []
    for s, by in ser.items():
        x = by.get(last, 0)
        base = [by.get(last - timedelta(days=7 * k), 0) for k in range(1, 9)]
        r = robust(base, x)
        if r and r[2] >= ZCUT and x >= 3 and x >= 2 * r[0] + 2:
            out.append((x, s, r))
    return [_ins(f"ticket_site:{s}:{last}", "tickets", "warn", f"Tickets at {s} are {fmt(x / max(r[0], 0.5), 1)}x the usual", f"{x} tickets on {last:%d/%m}, normally about {fmt(r[0], 1)} on a {WD[last.weekday()]}.",
                  "servicedesk", {"value": x, "normal": round(r[0], 1), "z": round(r[2], 1)}, s) for x, s, r in sorted(out, key=lambda t: -t[0])[:3]]


def d_ticket_trends(db: Session, cfg: Config) -> list[dict]:
    """Week over week volume, and weekly median resolution time and SLA rate (rolling 7 day windows ending yesterday)."""
    today, out = cfg.now().date(), []
    ends = [today - timedelta(days=1 + 7 * k) for k in range(6)][::-1]          # oldest first
    since = _midnight(ends[0] - timedelta(days=6))
    n_in = {e: db.scalar(select(func.count()).select_from(M.Ticket).where(M.Ticket.created_at >= _midnight(e - timedelta(days=6)), M.Ticket.created_at < _midnight(e + timedelta(days=1)))) or 0 for e in ends[-2:]}
    prev, cur = n_in[ends[-2]], n_in[ends[-1]]
    if prev >= 20 and cur >= 1.4 * prev:
        out.append(_ins("ticket_wow", "tickets", "warn", f"Tickets are up {fmt((cur / prev - 1) * 100)}% on the previous week", f"{cur} tickets in the last 7 days against {prev} in the 7 days before. Look for a common cause such as one location or category.", "servicedesk",
                        {"last_7_days": cur, "previous_7_days": prev}))
    rows = db.execute(select(M.Ticket.resolved_at, M.Ticket.created_at, M.Ticket.onhold_h, M.Ticket.sla_name).where(M.Ticket.resolved_at.is_not(None), M.Ticket.resolved_at >= since)).all()
    med, sla = [], []
    for e in ends:
        a, b = _midnight(e - timedelta(days=6)), _midnight(e + timedelta(days=1))
        hrs, ok, tot = [], 0, 0
        for res, cre, hold, sn in rows:
            if a <= res < b:
                h = max(0.0, (res - cre).total_seconds() / 3600 - (hold or 0))
                hrs.append(h)
                if sn in cfg.sla:
                    tot += 1
                    ok += 1 if h <= cfg.sla[sn] else 0
        med.append(statistics.median(hrs) if len(hrs) >= 5 else None)
        sla.append(ok / tot if tot >= 5 else None)
    m = med[-4:]
    if None not in m and m[0] and all(m[i + 1] > m[i] for i in range(3)) and m[3] >= 1.2 * m[0]:
        out.append(_ins("resolution_trend", "tickets", "warn", "Resolution time has worsened for 3 weeks in a row", f"Median resolution time went from {fmt(m[0], 1)} h to {fmt(m[3], 1)} h (weekly windows). Check technician workload and long-running tickets.", "servicedesk",
                        {"weekly_median_hours": [round(v, 1) for v in m]}))
    s = sla[-4:]
    low = float(cfg.p("sd.sla_warn", 0.9) or 0.9)
    if None not in s and s[3] < low and s[0] - s[3] >= 0.05 and s[3] < s[2] <= s[1] + 0.02:
        out.append(_ins("sla_trend", "tickets", "warn", "Ticket SLA compliance is falling", f"Within SLA fell from {fmt(s[0] * 100, 1)}% to {fmt(s[3] * 100, 1)}% over 4 weeks (target {fmt(low * 100)}%).", "servicedesk", {"weekly_sla": [round(v, 3) for v in s]}))
    return out


def d_sla_risk(db: Session, cfg: Config) -> list[dict]:
    """Open tickets that will pass their SLA target within 2 hours, and the count already past it."""
    now, out, soon, over = cfg.now(), [], [], 0
    rows = db.execute(select(M.Ticket.id, M.Ticket.site, M.Ticket.sla_name, M.Ticket.created_at, M.Ticket.onhold_h).where(M.Ticket.resolved_at.is_(None), func.lower(func.coalesce(M.Ticket.status, "")).not_in(CLOSED))).all()
    for tid, site, sn, cre, hold in rows:
        tgt = cfg.sla.get(sn)
        if not tgt:
            continue
        remain = tgt - ((now - cre).total_seconds() / 3600 - (hold or 0))
        if remain < 0:
            over += 1
        elif remain <= 2:
            soon.append((remain, tid, site))
    if soon:
        soon.sort()
        out.append(_ins("sla_risk", "tickets", "crit" if len(soon) >= 5 else "warn", f"{len(soon)} open tickets will pass their SLA within 2 hours",
                        "Closest: " + ", ".join(f"#{t} ({s or 'no location'}, {fmt(r * 60)} min left)" for r, t, s in soon[:3]) + ".", "servicedesk", {"count": len(soon), "already_past_sla": over}))
    return out


# ---------------- detectors: network ----------------
def d_links(db: Session, cfg: Config) -> list[dict]:
    """Link downtime on the last full day (and today so far) against the previous 28 days, and links that drop repeatedly in 7 days."""
    out, today = [], cfg.now().date()
    name = _sensor_names(db)
    ser = _daily_down(db, today - timedelta(days=29), today + timedelta(days=1))
    flagged = []
    for sid, s in ser.items():
        for day, label in ((today - timedelta(days=1), "yesterday"), (today, "today")):
            x = s.get(day)
            if x is None:
                continue
            r = robust([v for d, v in s.items() if d < today - timedelta(days=1)], x)
            if r and x >= (90 if day == today else 30) and r[2] >= ZCUT and x >= 2 * r[0] + 15:
                flagged.append((x, sid, day, label, r))
    latest: dict = {}
    for f in flagged:                                   # one finding per link: the latest affected day
        if f[1] not in latest or f[2] > latest[f[1]][2]:
            latest[f[1]] = f
    device = {x.id: x.device for x in db.scalars(select(M.PrtgSensor))}
    groups: dict = {}
    for f in latest.values():
        groups.setdefault((device.get(f[1]) or f[1], f[2]), []).append(f)
    shown = 0
    for (dev, day), fs in sorted(groups.items(), key=lambda g: -max(f[0] for f in g[1])):
        if shown >= 6:
            break
        if len(fs) >= 2:                                # several links at one location affected together
            names = ", ".join(sorted(name.get(f[1], f[1]) for f in fs))
            worst = max(f[0] for f in fs)
            out.append(_ins(f"link_site:{dev}:{day}", "links", "crit", f"{len(fs)} links at {dev} are affected together",
                            f"{names}: longest downtime {fmt(worst)} min {'today' if day == today else 'yesterday'} ({day:%d/%m}), normally close to 0. Links from different ISPs failing together points to the site (power, equipment, or cabling) rather than the ISP.",
                            "noc", {"links": len(fs), "longest_downtime_min": round(worst, 1)}, dev))
        else:
            x, sid, day, label, (med, sd, z) = fs[0]
            loc = name.get(sid, sid)
            out.append(_ins(f"link_down:{sid}:{day}", "links", "crit" if x >= 240 else "warn", f"Link {loc} downtime is far above normal",
                            f"{fmt(x)} min down {label} ({day:%d/%m}{', so far' if day == today else ''}), normally {fmt(med)} min per day (previous 28 days).", "noc", {"value": round(x, 1), "normal": round(med, 1), "z": round(z, 1)}, loc))
        shown += 1
    since = _midnight(today - timedelta(days=6))
    cnt = db.execute(select(M.PrtgEvent.sensor_id, func.count()).where(M.PrtgEvent.start_at >= since).group_by(M.PrtgEvent.sensor_id).having(func.count() >= 5).order_by(func.count().desc()).limit(5)).all()
    for sid, n in cnt:
        loc = name.get(sid, sid)
        out.append(_ins(f"link_flap:{sid}:{today}", "links", "warn", f"Link {loc} keeps dropping", f"{n} outages in the last 7 days. Check the equipment, cabling, or ISP at this location.", "noc", {"value": n, "window_days": 7}, loc))
    return out


def d_availability(db: Session, cfg: Config) -> list[dict]:
    """Network availability trend over the last 21 full days and a 14 day forecast against the target."""
    today = cfg.now().date()
    rows = db.execute(select(func.date(M.PrtgHourly.ts), func.sum(M.PrtgHourly.down_s), func.count()).where(M.PrtgHourly.seen.is_(True), M.PrtgHourly.ts >= _midnight(today - timedelta(days=21)), M.PrtgHourly.ts < _midnight(today)).group_by(func.date(M.PrtgHourly.ts)).order_by(func.date(M.PrtgHourly.ts))).all()
    ys = [1 - (down or 0) / (n * 3600) for _, down, n in rows if n >= 24]
    if len(ys) < 10:
        return []
    target = float(cfg.p("net.target", 0.995) or 0.995)
    b = slope(ys)
    now_v = sum(ys[-3:]) / 3
    if b <= -0.0004 and now_v >= target and now_v + b * 14 < target:
        days = int((now_v - target) / -b)
        return [_ins("avail_trend", "links", "warn", "Network availability is falling toward the target",
                     f"Average availability is {fmt(now_v * 100, 2)}% and dropping {fmt(-b * 100, 3)} points per day. At this rate it crosses the {fmt(target * 100, 1)}% target in about {days} days.", "noc",
                     {"now": round(now_v, 5), "slope_per_day": round(b, 6), "target": target, "days_to_target": days})]
    return []


def d_capacity(db: Session, cfg: Config) -> list[dict]:
    """Daily peak utilization per link over 28 days: forecast when it reaches 90% of capacity, and links already above the peak threshold."""
    today, out = cfg.now().date(), []
    cap = {s.id: s.capacity_mbps for s in db.scalars(select(M.PrtgSensor).where(M.PrtgSensor.capacity_mbps.is_not(None), M.PrtgSensor.active.is_(True)))}
    if not cap:
        return out
    name = _sensor_names(db)
    peak = float(cfg.p("net.util_peak", 0.85) or 0.85)
    rows = db.execute(select(M.PrtgHourly.sensor_id, func.date(M.PrtgHourly.ts), func.max(func.greatest(M.PrtgHourly.in_mbps, M.PrtgHourly.out_mbps))).where(M.PrtgHourly.ts >= _midnight(today - timedelta(days=28)), M.PrtgHourly.ts < _midnight(today)).group_by(M.PrtgHourly.sensor_id, func.date(M.PrtgHourly.ts))).all()
    ser: dict = {}
    for sid, d, v in rows:
        if sid in cap and v is not None:
            ser.setdefault(sid, {})[d] = v / cap[sid]
    found = []
    for sid, s in ser.items():
        ys = [s[d] for d in sorted(s)]
        if len(ys) < 14:
            continue
        cur, b = sum(ys[-3:]) / 3, slope(ys)
        if cur >= peak:
            found.append((cur, sid, f"link_cap_now:{sid}", "warn", f"Link {name.get(sid, sid)} peak utilization is {fmt(cur * 100)}% of capacity",
                          f"Daily peak averaged {fmt(cur * 100)}% over the last 3 days (threshold {fmt(peak * 100)}%, capacity {fmt(cap[sid])} Mbps). Consider more capacity or traffic shaping.", {"peak_pct": round(cur * 100, 1), "capacity_mbps": cap[sid]}))
        elif cur >= 0.6 and b >= 0.004:
            days = int((0.9 - cur) / b)
            if days <= 60:
                found.append((cur, sid, f"link_cap_trend:{sid}", "warn" if days <= 30 else "info", f"Link {name.get(sid, sid)} may reach 90% capacity in about {days} days",
                              f"Daily peak is {fmt(cur * 100)}% of capacity and rising {fmt(b * 100, 2)} points per day (capacity {fmt(cap[sid])} Mbps).", {"peak_pct": round(cur * 100, 1), "days_to_90pct": days, "capacity_mbps": cap[sid]}))
    for cur, sid, key, sev, title, detail, metric in sorted(found, key=lambda t: -t[0])[:5]:
        out.append(_ins(key, "capacity", sev, title, detail, "noc", metric, name.get(sid, sid)))
    return out


# ---------------- detectors: security ----------------
def d_ndr(db: Session, cfg: Config) -> list[dict]:
    """Critical and high events per full day against the previous 30 days."""
    today = cfg.now().date()
    rows = db.execute(text("SELECT DISTINCT ON (day) day, threats FROM soc_day WHERE day >= :a AND day < :b ORDER BY day, batch_id DESC"), {"a": today - timedelta(days=35), "b": today}).all()
    if len(rows) < MIN_BASE + 1:
        return []
    ch = {d: sum(v for k, v in (t or {}).items() if k.split("|")[0] in ("critical", "high")) for d, t in rows}
    last = max(ch)
    r = robust([v for d, v in ch.items() if d < last], ch[last])
    if r and r[2] >= ZCUT and ch[last] >= 1.5 * r[0] and ch[last] - r[0] >= 20:
        return [_ins(f"ndr_spike:{last}", "security", "warn", f"NDR critical and high events spiked on {last:%d/%m}", f"{fmt(ch[last])} critical + high events, normally about {fmt(r[0])} per day (last 30 days). Review the sources and firewall actions.",
                     "soc", {"value": ch[last], "normal": round(r[0], 1), "z": round(r[2], 1)})]
    return []


def d_xdr(db: Session, cfg: Config) -> list[dict]:
    out, now = [], cfg.now()
    old = db.execute(select(func.count(), func.min(M.XdrAlert.created_at)).where(M.XdrAlert.severity.in_(["critical", "high"]), func.lower(func.coalesce(M.XdrAlert.status, "")) != "closed",
                                                                                 func.lower(func.coalesce(M.XdrAlert.investigation_status, "")) != "closed", M.XdrAlert.created_at < now - timedelta(hours=72))).one()
    if old[0]:
        age = (now - old[1]).days
        out.append(_ins("xdr_backlog", "security", "crit" if old[0] >= 5 else "warn", f"{old[0]} critical or high XDR alerts have been open for more than 72 hours", f"The oldest is {age} days old. Close or follow up in Trend Micro Vision One.", "xdr", {"count": old[0], "oldest_days": age}))
    cnt: dict = {}
    for ents in db.scalars(select(M.XdrAlert.entities).where(M.XdrAlert.created_at >= now - timedelta(days=7))):
        for n in {e.get("name") for e in (ents or []) if e.get("type") == "host" and e.get("name")}:
            cnt[n] = cnt.get(n, 0) + 1
    for h, n in sorted(cnt.items(), key=lambda x: -x[1])[:3]:
        if n >= 3:
            out.append(_ins(f"xdr_repeat:{h}", "security", "warn", f"Host {h} keeps appearing in XDR alerts", f"{n} alerts in the last 7 days. Check whether the host needs to be isolated or cleaned.", "xdr", {"alerts_7_days": n}))
    return out


# ---------------- detectors: devices and WiFi ----------------
def d_devices(db: Session, cfg: Config) -> list[dict]:
    """Devices down now against the last 7 days (per kind), and long-running down devices."""
    out, now = [], cfg.now()
    for kind in [k for (k,) in db.execute(select(M.ZbxStat.kind).distinct())]:
        rows = db.execute(select(M.ZbxStat.hour, M.ZbxStat.down).where(M.ZbxStat.kind == kind, M.ZbxStat.hour >= now - timedelta(days=7)).order_by(M.ZbxStat.hour)).all()
        if len(rows) < MIN_BASE + 1:
            continue
        x = rows[-1][1]
        r = robust([d for _, d in rows[:-1]], x)
        if r and r[2] >= ZCUT and x - r[0] >= 10:
            out.append(_ins(f"dev_down:{kind}", "devices", "warn", f"Devices down ({kind}) are far above normal", f"{x} devices are down now, normally about {fmt(r[0])}. This often means a network or power problem in one area.", "devices",
                            {"value": x, "normal": round(r[0], 1), "z": round(r[2], 1)}))
    chronic = db.scalar(select(func.count()).select_from(M.ZbxHost).where(M.ZbxHost.status == "down", M.ZbxHost.down_since < now - timedelta(days=30)))
    if chronic:
        out.append(_ins("dev_chronic", "devices", "info", f"{chronic} devices have been down for more than 30 days", "Devices that stay down hurt availability. Decide whether to repair, replace, or stop monitoring them.", "devices", {"count": chronic}))
    return out


def d_flapping_devices(db: Session, cfg: Config) -> list[dict]:
    """Hosts with many down events in 7 days (maintenance hosts excluded)."""
    now = cfg.now()
    maint = {h for (h,) in db.execute(select(M.ZbxHost.hostid).where(M.ZbxHost.status == "maintenance"))}
    rows = db.execute(select(M.ZbxEvent.hostid, M.ZbxEvent.host_name, func.count()).where(M.ZbxEvent.start_at >= now - timedelta(days=7)).group_by(M.ZbxEvent.hostid, M.ZbxEvent.host_name).having(func.count() >= 6).order_by(func.count().desc()).limit(8)).all()
    return [_ins(f"dev_flap:{hid}", "devices", "warn", f"Device {nm} keeps going down", f"{n} down events in the last 7 days. Check power, cabling, and the uplink.", "devices", {"events_7_days": n}) for hid, nm, n in rows if hid not in maint][:5]


def d_incidents(db: Session, cfg: Config) -> list[dict]:
    """Group device down events that start together at one location (within 10 minutes) into a single incident."""
    now, out = cfg.now(), []
    site_of = _site_of(db)
    rows = db.execute(select(M.ZbxEvent.code, M.ZbxEvent.hostid, M.ZbxEvent.start_at).where(M.ZbxEvent.start_at >= now - timedelta(hours=24)).order_by(M.ZbxEvent.code, M.ZbxEvent.start_at)).all()
    by: dict = {}
    for code, hid, at in rows:
        by.setdefault(site_of(code) or code or "-", []).append((at, hid))
    for site, ev in by.items():
        ev.sort()
        cur = [ev[0]]
        for e in ev[1:] + [None]:
            if e and (e[0] - cur[-1][0]).total_seconds() <= 600:
                cur.append(e)
                continue
            hosts = {h for _, h in cur}
            if len(hosts) >= 5:
                start = cur[0][0]
                out.append(_ins(f"incident:{site}:{start:%Y%m%d%H}", "devices", "crit" if len(hosts) >= 20 else "warn", f"{len(hosts)} devices went down together at {site}",
                                f"All started within {max(1, int((cur[-1][0] - start).total_seconds() / 60))} min from {start:%H:%M} on {start:%d/%m}. Treated as one incident, likely a shared cause such as power or an uplink.", "devices", {"devices": len(hosts)}, site))
            cur = [e] if e else []
    return sorted(out, key=lambda i: -i["metric"]["devices"])[:4]


def d_wifi(db: Session, cfg: Config) -> list[dict]:
    """WiFi clients against the same hour on earlier days, and Access Points that are offline."""
    out = []
    last = db.scalar(select(M.WifiStat).order_by(M.WifiStat.at.desc()).limit(1))
    if not last:
        return out
    if last.ap_total and last.ap_total - last.ap_online >= max(3, int(last.ap_total * 0.1)):
        out.append(_ins("wifi_ap_off", "wifi", "warn", f"{last.ap_total - last.ap_online} of {last.ap_total} Access Points are offline", "More than 10% of Access Points are offline. Check the zones and locations on the WiFi page.", "wifi", {"offline": last.ap_total - last.ap_online, "total": last.ap_total}))
    same = [r for (r,) in db.execute(select(M.WifiStat.clients).where(func.extract("hour", M.WifiStat.at) == last.at.hour, M.WifiStat.at < last.at - timedelta(hours=3), M.WifiStat.at >= last.at - timedelta(days=14)))]
    r = robust(same, last.clients)
    if r and r[0] >= 30 and last.clients <= 0.6 * r[0] and r[2] <= -ZCUT:
        out.append(_ins("wifi_drop", "wifi", "warn", "WiFi clients dropped sharply", f"{last.clients} clients now, normally about {fmt(r[0])} at this hour. This may be a controller, ISP, or power problem.", "wifi", {"value": last.clients, "normal": round(r[0], 1), "z": round(r[2], 1)}))
    return out


# ---------------- detectors: cross-source and data quality ----------------
def d_site_multi(db: Session, cfg: Config) -> list[dict]:
    """A location with two or more signals at once: link downtime today, many devices down, and a ticket spike."""
    today = cfg.now().date()
    site_of = _site_of(db)
    sites = {s.name for s in db.scalars(select(M.Site).where(M.Site.active.is_(True)))}
    link_down: dict = {}
    sens_dev = {x.id: x.device for x in db.scalars(select(M.PrtgSensor))}
    for sid, s in _daily_down(db, today, today + timedelta(days=1)).items():
        dev = sens_dev.get(sid)
        if dev in sites and s.get(today, 0) >= 90:
            link_down[dev] = max(link_down.get(dev, 0), s[today])
    dev_tot: dict = {}
    dev_down: dict = {}
    for code, status in db.execute(select(M.ZbxHost.code, M.ZbxHost.status)):
        site = site_of(code)
        if site:
            if status in ("up", "down"):
                dev_tot[site] = dev_tot.get(site, 0) + 1
            if status == "down":
                dev_down[site] = dev_down.get(site, 0) + 1
    tk_today = {s: n for s, n in db.execute(select(M.Ticket.site, func.count()).where(M.Ticket.created_at >= _midnight(today)).group_by(M.Ticket.site))}
    base = db.execute(select(M.Ticket.site, func.count()).where(M.Ticket.created_at >= _midnight(today - timedelta(days=28)), M.Ticket.created_at < _midnight(today)).group_by(M.Ticket.site)).all()
    tk_avg = {s: n / 28 for s, n in base}
    out = []
    for name in sorted(sites):
        sig = []
        if name in link_down:
            sig.append(f"link down {fmt(link_down[name])} min today")
        if dev_tot.get(name, 0) >= 5 and dev_down.get(name, 0) / dev_tot[name] >= 0.2:
            sig.append(f"{dev_down[name]} of {dev_tot[name]} devices down")
        if tk_today.get(name, 0) >= 3 and tk_today[name] >= 2 * tk_avg.get(name, 0) + 1:
            sig.append(f"{tk_today[name]} tickets today (usual {fmt(tk_avg.get(name, 0), 1)})")
        if len(sig) >= 2:
            out.append(_ins(f"site_multi:{name}:{today}", "correlation", "crit", f"Several systems are affected at {name}", "; ".join(sig).capitalize() + ". Signals from different sources at the same location point to one underlying cause.", "ringkasan", {"signals": len(sig)}, name))
    return out[:4]


def d_data_quality(db: Session, cfg: Config) -> list[dict]:
    """Checks that the data behind the numbers is complete: SOC days, PRTG coverage, source failures, unmapped codes, empty tickets."""
    out, today = [], cfg.now().date()
    have = {d for (d,) in db.execute(text("SELECT DISTINCT day FROM soc_day WHERE day >= :a"), {"a": today - timedelta(days=8)})}
    miss = [today - timedelta(days=k) for k in range(1, 8) if (today - timedelta(days=k)) not in have]
    if have and miss:
        out.append(_ins("dq_soc", "data", "warn", f"SOC data is missing for {len(miss)} of the last 7 days", "Missing: " + ", ".join(f"{d:%d/%m}" for d in sorted(miss)[:5]) + ". NDR totals for these days are incomplete. Check the Panorama sync or import the CSV.", "kelengkapan", {"missing_days": len(miss)}))
    n_sensor = db.scalar(select(func.count()).select_from(M.PrtgSensor).where(M.PrtgSensor.active.is_(True))) or 0
    y = today - timedelta(days=1)
    got = db.scalar(select(func.count()).select_from(M.PrtgHourly).where(M.PrtgHourly.ts >= _midnight(y), M.PrtgHourly.ts < _midnight(today), M.PrtgHourly.seen.is_(True))) or 0
    if n_sensor and got < 0.9 * n_sensor * 24:
        out.append(_ins(f"dq_prtg:{y}", "data", "warn", "PRTG data for yesterday is incomplete", f"{got} of {n_sensor * 24} expected hourly readings ({fmt(got / (n_sensor * 24) * 100)}%). Link availability for that day may be misstated.", "kelengkapan", {"readings": got, "expected": n_sensor * 24}))
    bad = [s.label for s in db.scalars(select(M.DataSource).where(M.DataSource.enabled.is_(True), M.DataSource.mode == "api", M.DataSource.last_error.is_not(None)))]
    if bad:
        out.append(_ins("dq_sources", "data", "crit", f"{len(bad)} data sources are failing", ", ".join(bad[:5]) + ". Numbers from these sources are no longer updating. See Admin > System > Source Status.", "kelengkapan", {"sources": len(bad)}))
    unmapped = db.scalar(select(func.count()).select_from(M.ZbxLocMap).where(M.ZbxLocMap.site.is_(None)))
    if unmapped:
        out.append(_ins("dq_unmapped", "data", "info", f"{unmapped} Zabbix location codes are not mapped", "Devices with these codes are left out of per-location totals. Map them in Admin > Data Sources > Mapping.", "devices", {"codes": unmapped}))
    tot = db.scalar(select(func.count()).select_from(M.Ticket).where(M.Ticket.created_at >= _midnight(today - timedelta(days=7)))) or 0
    emp = db.scalar(select(func.count()).select_from(M.Ticket).where(M.Ticket.created_at >= _midnight(today - timedelta(days=7)), M.Ticket.desc_empty.is_(True))) or 0
    if tot >= 20 and emp / tot >= 0.3:
        out.append(_ins("dq_tickets", "data", "info", f"{fmt(emp / tot * 100)}% of recent tickets have no description", f"{emp} of {tot} tickets in the last 7 days. Empty descriptions make categories and reports less reliable.", "servicedesk", {"empty": emp, "total": tot}))
    return out


DETECTORS = [d_tickets, d_ticket_sites, d_ticket_trends, d_sla_risk, d_links, d_availability, d_capacity, d_ndr, d_xdr, d_devices, d_flapping_devices, d_incidents, d_wifi, d_site_multi, d_data_quality]


# ---------------- rankings, health, summary (computed on request) ----------------
def rankings(db: Session, cfg: Config) -> dict:
    """Problem rankings for the last 30 days: links, repeat-offender devices, and location health (worst first)."""
    today = cfg.now().date()
    name = _sensor_names(db)
    ser = _daily_down(db, today - timedelta(days=30), today + timedelta(days=1))
    ev = {sid: n for sid, n in db.execute(select(M.PrtgEvent.sensor_id, func.count()).where(M.PrtgEvent.start_at >= _midnight(today - timedelta(days=30))).group_by(M.PrtgEvent.sensor_id))}
    links = []
    for sid, s in ser.items():
        mins, n = sum(s.values()), ev.get(sid, 0)
        if mins > 0 or n:
            links.append({"name": name.get(sid, sid), "downMin": round(mins), "events": n, "avail": round(1 - mins * 60 / (30 * 86400), 5), "score": round(mins * (1 + 0.1 * n))})
    links.sort(key=lambda r: -r["score"])
    maint = {h for (h,) in db.execute(select(M.ZbxHost.hostid).where(M.ZbxHost.status == "maintenance"))}
    now = cfg.now()
    rows = db.execute(select(M.ZbxEvent.hostid, M.ZbxEvent.host_name, M.ZbxEvent.code, func.count(), func.sum(func.extract("epoch", func.coalesce(M.ZbxEvent.end_at, now) - M.ZbxEvent.start_at))).where(M.ZbxEvent.start_at >= _midnight(today - timedelta(days=30))).group_by(M.ZbxEvent.hostid, M.ZbxEvent.host_name, M.ZbxEvent.code).order_by(func.count().desc()).limit(40)).all()
    site_of = _site_of(db)
    hosts = [{"name": nm, "site": site_of(code) or code or "-", "events": n, "downH": round((secs or 0) / 3600, 1)} for hid, nm, code, n, secs in rows if hid not in maint][:8]
    return {"links": links[:8], "hosts": hosts, "health": site_health(db, cfg)[:15]}


def site_health(db: Session, cfg: Config) -> list[dict]:
    """Health score 0 to 100 per location: link availability 45%, device availability 35%, ticket load 20% (open tickets past SLA). Worst first."""
    today, now = cfg.now().date(), cfg.now()
    site_of = _site_of(db)
    sites = [s.name for s in db.scalars(select(M.Site).where(M.Site.active.is_(True)))]
    dev = {s.id: s.device for s in db.scalars(select(M.PrtgSensor).where(M.PrtgSensor.active.is_(True)))}
    nsens: dict = {}
    for d in dev.values():
        nsens[d] = nsens.get(d, 0) + 1
    down: dict = {}
    for sid, s in _daily_down(db, today - timedelta(days=7), today + timedelta(days=1)).items():
        if sid in dev:
            down[dev[sid]] = down.get(dev[sid], 0) + sum(s.values())
    tot: dict = {}
    dn: dict = {}
    for code, status in db.execute(select(M.ZbxHost.code, M.ZbxHost.status)):
        s = site_of(code)
        if s and status in ("up", "down"):
            tot[s] = tot.get(s, 0) + 1
            dn[s] = dn.get(s, 0) + (1 if status == "down" else 0)
    over: dict = {}
    for site, sn, cre, hold in db.execute(select(M.Ticket.site, M.Ticket.sla_name, M.Ticket.created_at, M.Ticket.onhold_h).where(M.Ticket.resolved_at.is_(None), func.lower(func.coalesce(M.Ticket.status, "")).not_in(CLOSED))):
        t = cfg.sla.get(sn)
        if t and (now - cre).total_seconds() / 3600 - (hold or 0) > t:
            over[site] = over.get(site, 0) + 1
    clip = lambda v: max(0.0, min(100.0, v))
    out = []
    for s in sites:
        if s not in nsens and s not in tot and s not in over:
            continue
        la = 1 - down.get(s, 0) * 60 / (nsens[s] * 7 * 86400) if s in nsens else None
        da = 1 - dn.get(s, 0) / tot[s] if tot.get(s) else None
        parts = [(clip((la - 0.95) / 0.05 * 100) if la is not None else None, 45), (clip((da - 0.7) / 0.3 * 100) if da is not None else None, 35), (clip(100 - over.get(s, 0) * 10), 20)]
        w = sum(p[1] for p in parts if p[0] is not None)
        score = sum(p[0] * p[1] for p in parts if p[0] is not None) / w
        out.append({"site": s, "score": round(score), "link": None if la is None else round(la, 4), "devices": None if da is None else round(da, 3), "overdue": over.get(s, 0), "devDown": dn.get(s, 0), "devTotal": tot.get(s, 0)})
    return sorted(out, key=lambda r: r["score"])


def shift_summary(db: Session, cfg: Config, top: list[dict]) -> str:
    """Plain text summary of the last 24 hours for the shift handover (WhatsApp friendly). Every number comes from stored data."""
    now = cfg.now()
    a = now - timedelta(hours=24)
    n_in = db.scalar(select(func.count()).select_from(M.Ticket).where(M.Ticket.created_at >= a)) or 0
    n_done = db.scalar(select(func.count()).select_from(M.Ticket).where(M.Ticket.resolved_at >= a)) or 0
    n_open = db.scalar(select(func.count()).select_from(M.Ticket).where(M.Ticket.resolved_at.is_(None), func.lower(func.coalesce(M.Ticket.status, "")).not_in(CLOSED))) or 0
    link_rows = db.execute(select(M.PrtgHourly.sensor_id, func.sum(M.PrtgHourly.down_s)).where(M.PrtgHourly.ts >= a).group_by(M.PrtgHourly.sensor_id).having(func.sum(M.PrtgHourly.down_s) >= 1800).order_by(func.sum(M.PrtgHourly.down_s).desc()).limit(5)).all()
    name = _sensor_names(db)
    tot_n, down_s = db.execute(select(func.count(), func.coalesce(func.sum(M.PrtgHourly.down_s), 0)).where(M.PrtgHourly.ts >= a, M.PrtgHourly.seen.is_(True))).one()
    avail = 1 - down_s / (tot_n * 3600) if tot_n else None
    xdr_open = db.scalar(select(func.count()).select_from(M.XdrAlert).where(M.XdrAlert.severity.in_(["critical", "high"]), func.lower(func.coalesce(M.XdrAlert.status, "")) != "closed", func.lower(func.coalesce(M.XdrAlert.investigation_status, "")) != "closed")) or 0
    xdr_new = db.scalar(select(func.count()).select_from(M.XdrAlert).where(M.XdrAlert.created_at >= a)) or 0
    dev_down = db.scalar(select(func.count()).select_from(M.ZbxHost).where(M.ZbxHost.status == "down")) or 0
    dev_new = db.scalar(select(func.count()).select_from(M.ZbxEvent).where(M.ZbxEvent.start_at >= a)) or 0
    L = [f"*TERA shift summary* ({now:%d %b %Y %H:%M}, last 24 hours)", "", f"*Tickets*: {n_in} in, {n_done} closed, {n_open} open now."]
    L.append(f"*Network*: availability {fmt(avail * 100, 2)}%." if avail is not None else "*Network*: no hourly data.")
    for sid, secs in link_rows:
        L.append(f"- {name.get(sid, sid)}: {fmt(secs / 60)} min down")
    L.append(f"*Security*: {xdr_open} critical/high XDR alerts open, {xdr_new} new alerts in 24 h.")
    L.append(f"*Devices*: {dev_down} down now, {dev_new} new down events in 24 h.")
    crit = [i for i in top if i["sev"] in ("crit", "warn")][:6]
    if crit:
        L += ["", "*Findings*"] + [f"- [{'CRITICAL' if i['sev'] == 'crit' else 'WARNING'}] {i['title']}" for i in crit]
    return "\n".join(L)


# ---------------- storage ----------------
def run(db: Session, cfg: Config) -> dict:
    """Run every detector, store new findings or refresh existing ones, close findings that no longer appear, and honour dismissals."""
    now, found, errors = cfg.now(), {}, []
    for fn in DETECTORS:
        try:
            for i in fn(db, cfg):
                found[i["key"]] = i
        except Exception as e:                       # one failing detector does not stop the others
            errors.append(f"{fn.__name__}: {str(e)[:100]}")
            db.rollback()
    existing = {r.key: r for r in db.scalars(select(M.Insight).where(M.Insight.status != "resolved"))}
    new = []
    for k, i in found.items():
        row = existing.get(k)
        if row:
            if row.status == "dismissed":
                if row.suppress_until and row.suppress_until > now:
                    continue                          # still dismissed: stay hidden
                row.status, row.ack_by = "new", None
            row.last_seen, row.kind, row.severity, row.title, row.detail, row.metric = now, i["kind"], i["severity"], i["title"], i["detail"], i["metric"]
        else:
            db.add(M.Insight(key=k, kind=i["kind"], severity=i["severity"], title=i["title"], detail=i["detail"], tab=i["tab"], metric=i["metric"], site=i["site"], first_seen=now, last_seen=now, status="new"))
            new.append(i)
    closed = 0
    for k, row in existing.items():
        if k in found or (row.status == "dismissed" and row.suppress_until and row.suppress_until > now):
            continue
        row.status, row.resolved_at, closed = "resolved", now, closed + 1
    db.flush()
    return {"found": len(found), "new": new, "closed": closed, "errors": errors}
