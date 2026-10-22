"""Insight otomatis: analisis statistik atas data yang sudah tersimpan di database (tanpa layanan luar dan tanpa AI).

Metode utama: bandingkan nilai terbaru dengan pola biasanya (median dan simpangan robust MAD dari data sebelumnya, pada hari yang sama bila ada pola mingguan),
dan hitung kemiringan tren untuk memperkirakan kapan target terlampaui. Tiap temuan memuat angka, pembandingnya, dan halaman rujukan.
Hasil disimpan di tabel insight dengan kunci unik; temuan yang tidak muncul lagi otomatis berstatus selesai."""
import statistics
from datetime import date, datetime, timedelta
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session
from . import models as M
from .store import Config

MIN_BASE = 5          # jumlah data pembanding minimal agar sebuah anomali dinilai
ZCUT = 3.0            # ambang z robust


def robust(base: list[float], x: float):
    """(median, simpangan, z). Simpangan = MAD x 1,4826; bila 0, pakai simpangan baku. None bila pembanding kurang."""
    if len(base) < MIN_BASE:
        return None
    med = statistics.median(base)
    sd = statistics.median([abs(v - med) for v in base]) * 1.4826 or (statistics.pstdev(base) if len(base) > 1 else 0.0)
    z = (x - med) / sd if sd else (0.0 if x == med else (99.0 if x > med else -99.0))
    return med, sd, max(-99.0, min(99.0, z))


def slope(ys: list[float]) -> float:
    """Kemiringan regresi linear terhadap indeks hari (per hari)."""
    n = len(ys)
    if n < 3:
        return 0.0
    mx, my = (n - 1) / 2, sum(ys) / n
    den = sum((i - mx) ** 2 for i in range(n))
    return sum((i - mx) * (y - my) for i, y in enumerate(ys)) / den if den else 0.0


def _ins(key, kind, sev, title, detail, tab, metric=None, site=None):
    return {"key": key, "kind": kind, "severity": sev, "title": title, "detail": detail, "tab": tab, "metric": metric or {}, "site": site}


WD = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
fmt = lambda v, d=0: f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ---------------- detektor ----------------
def d_tickets(db: Session, cfg: Config) -> list[dict]:
    """Tiket masuk pada hari lengkap terakhir dibanding hari yang sama dalam 8 minggu sebelumnya."""
    today = cfg.now().date()
    rows = db.execute(select(func.date(M.Ticket.created_at), func.count()).where(M.Ticket.created_at >= datetime.combine(today - timedelta(days=64), datetime.min.time())).group_by(func.date(M.Ticket.created_at))).all()
    by = {d: n for d, n in rows}
    last = today - timedelta(days=1)
    if last not in by and not by:
        return []
    x = by.get(last, 0)
    base = [by.get(last - timedelta(days=7 * k), 0) for k in range(1, 9) if (last - timedelta(days=7 * k)) >= min(by, default=last)]
    r = robust(base, x)
    if not r:
        return []
    med, sd, z = r
    if z >= ZCUT and x >= 1.5 * med and x - med >= 5:
        return [_ins(f"ticket_volume:{last}", "tiket", "warn", f"Tiket masuk melonjak pada {WD[last.weekday()]} {last:%d/%m}",
                     f"{x} tiket masuk, biasanya sekitar {fmt(med)} pada hari {WD[last.weekday()]} (8 minggu terakhir). Periksa kategori dan lokasi dengan tiket terbanyak.",
                     "servicedesk", {"nilai": x, "biasanya": round(med, 1), "z": round(z, 1)})]
    return []


def _sensor_names(db: Session) -> dict:
    sens = list(db.scalars(select(M.PrtgSensor)))
    per: dict = {}
    for x in sens:
        per[x.device] = per.get(x.device, 0) + 1
    return {x.id: ((x.device or x.name) + (f" ({x.name})" if per.get(x.device, 0) > 1 else "")) for x in sens}


def _daily_down(db: Session, start: date, end: date) -> dict:
    """{sensor: {hari: menit down}} dari data per jam, hari start sampai sebelum end."""
    rows = db.execute(select(M.PrtgHourly.sensor_id, func.date(M.PrtgHourly.ts), func.sum(M.PrtgHourly.down_s)).where(M.PrtgHourly.ts >= datetime.combine(start, datetime.min.time()), M.PrtgHourly.ts < datetime.combine(end, datetime.min.time())).group_by(M.PrtgHourly.sensor_id, func.date(M.PrtgHourly.ts))).all()
    out: dict = {}
    for sid, d, down in rows:
        out.setdefault(sid, {})[d] = (down or 0) / 60
    return out


def d_links(db: Session, cfg: Config) -> list[dict]:
    """Downtime link hari lengkap terakhir (dan hari ini sementara) dibanding 28 hari sebelumnya, serta link yang putus berulang dalam 7 hari."""
    out, today = [], cfg.now().date()
    name = _sensor_names(db)
    ser = _daily_down(db, today - timedelta(days=29), today + timedelta(days=1))
    flagged = []
    for sid, s in ser.items():
        for day, label in ((today - timedelta(days=1), "kemarin"), (today, "hari ini")):
            x = s.get(day)
            if x is None:
                continue
            r = robust([v for d, v in s.items() if d < today - timedelta(days=1)], x)
            if r and x >= (90 if day == today else 30) and r[2] >= ZCUT and x >= 2 * r[0] + 15:
                flagged.append((x, sid, day, label, r))
    latest: dict = {}
    for f in flagged:                                   # satu temuan per link: hari terbaru yang bermasalah
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
        if len(fs) >= 2:                                # beberapa link di lokasi yang sama bermasalah bersamaan
            names = ", ".join(sorted(name.get(f[1], f[1]) for f in fs))
            worst = max(f[0] for f in fs)
            out.append(_ins(f"link_site:{dev}:{day}", "link", "crit", f"{len(fs)} link di {dev} bermasalah bersamaan",
                            f"{names}: downtime terlama {fmt(worst)} menit {'hari ini' if day == today else 'kemarin'} ({day:%d/%m}), biasanya mendekati 0. Link dari ISP berbeda turun bersamaan, jadi penyebab kemungkinan di lokasi (listrik, perangkat, atau kabel), bukan di ISP.",
                            "noc", {"jumlah_link": len(fs), "downtime_terlama_menit": round(worst, 1)}, dev))
        else:
            x, sid, day, label, (med, sd, z) = fs[0]
            loc = name.get(sid, sid)
            out.append(_ins(f"link_down:{sid}:{day}", "link", "crit" if x >= 240 else "warn", f"Downtime link {loc} jauh di atas biasanya",
                            f"{fmt(x)} menit down {label} ({day:%d/%m}{', sampai saat ini' if day == today else ''}), biasanya {fmt(med)} menit per hari (28 hari sebelumnya).", "noc", {"nilai": round(x, 1), "biasanya": round(med, 1), "z": round(z, 1)}, loc))
        shown += 1
    since = datetime.combine(today - timedelta(days=6), datetime.min.time())
    cnt = db.execute(select(M.PrtgEvent.sensor_id, func.count()).where(M.PrtgEvent.start_at >= since).group_by(M.PrtgEvent.sensor_id).having(func.count() >= 5).order_by(func.count().desc()).limit(5)).all()
    for sid, n in cnt:
        loc = name.get(sid, sid)
        out.append(_ins(f"link_flap:{sid}:{today}", "link", "warn", f"Link {loc} putus berulang", f"{n} kali putus dalam 7 hari terakhir. Periksa kondisi perangkat, kabel, atau ISP di lokasi ini.", "noc", {"nilai": n, "periode_hari": 7}, loc))
    return out


def d_availability(db: Session, cfg: Config) -> list[dict]:
    """Tren availability seluruh link 21 hari lengkap terakhir dan perkiraan 14 hari ke depan terhadap target."""
    today = cfg.now().date()
    rows = db.execute(select(func.date(M.PrtgHourly.ts), func.sum(M.PrtgHourly.down_s), func.count()).where(M.PrtgHourly.seen.is_(True), M.PrtgHourly.ts >= datetime.combine(today - timedelta(days=21), datetime.min.time()), M.PrtgHourly.ts < datetime.combine(today, datetime.min.time())).group_by(func.date(M.PrtgHourly.ts)).order_by(func.date(M.PrtgHourly.ts))).all()
    ys = [1 - (down or 0) / (n * 3600) for _, down, n in rows if n >= 24]
    if len(ys) < 10:
        return []
    target = float(cfg.p("net.target", 0.995) or 0.995)
    b = slope(ys)
    now_v = sum(ys[-3:]) / 3
    proj = now_v + b * 14
    if b <= -0.0004 and now_v >= target and proj < target:
        days = int((now_v - target) / -b)
        return [_ins("avail_trend", "link", "warn", "Availability link menurun dan mendekati target",
                     f"Availability rata-rata {fmt(now_v * 100, 2)}% turun {fmt(-b * 100, 3)} poin per hari. Pada laju ini target {fmt(target * 100, 1)}% terlewati sekitar {days} hari lagi.", "noc",
                     {"sekarang": round(now_v, 5), "kemiringan_per_hari": round(b, 6), "target": target, "hari_menuju_target": days})]
    return []


def d_ndr(db: Session, cfg: Config) -> list[dict]:
    """Event critical + high per hari lengkap terakhir dibanding 30 hari sebelumnya."""
    today = cfg.now().date()
    rows = db.execute(text("SELECT DISTINCT ON (day) day, threats FROM soc_day WHERE day >= :a AND day < :b ORDER BY day, batch_id DESC"), {"a": today - timedelta(days=35), "b": today}).all()
    if len(rows) < MIN_BASE + 1:
        return []
    ch = {d: sum(v for k, v in (t or {}).items() if k.split("|")[0] in ("critical", "high")) for d, t in rows}
    last = max(ch)
    r = robust([v for d, v in ch.items() if d < last], ch[last])
    if r and r[2] >= ZCUT and ch[last] >= 1.5 * r[0] and ch[last] - r[0] >= 20:
        return [_ins(f"ndr_spike:{last}", "ndr", "warn", f"Event critical dan high NDR melonjak pada {last:%d/%m}", f"{fmt(ch[last])} event critical + high, biasanya sekitar {fmt(r[0])} per hari (30 hari terakhir). Lihat sumber dan tindakan firewall.",
                     "soc", {"nilai": ch[last], "biasanya": round(r[0], 1), "z": round(r[2], 1)})]
    return []


def d_xdr(db: Session, cfg: Config) -> list[dict]:
    out, now = [], cfg.now()
    old = db.execute(select(func.count(), func.min(M.XdrAlert.created_at)).where(M.XdrAlert.severity.in_(["critical", "high"]), func.lower(func.coalesce(M.XdrAlert.status, "")) != "closed",
                                                                                 func.lower(func.coalesce(M.XdrAlert.investigation_status, "")) != "closed", M.XdrAlert.created_at < now - timedelta(hours=72))).one()
    if old[0]:
        age = (now - old[1]).days
        out.append(_ins("xdr_backlog", "xdr", "crit" if old[0] >= 5 else "warn", f"{old[0]} alert XDR critical atau high belum selesai lebih dari 72 jam", f"Yang tertua berumur {age} hari. Tutup atau tindak lanjuti di Trend Micro Vision One.", "xdr", {"jumlah": old[0], "terlama_hari": age}))
    since = now - timedelta(days=7)
    cnt: dict = {}
    for ents in db.scalars(select(M.XdrAlert.entities).where(M.XdrAlert.created_at >= since)):
        for n in {e.get("name") for e in (ents or []) if e.get("type") == "host" and e.get("name")}:
            cnt[n] = cnt.get(n, 0) + 1
    for h, n in sorted(cnt.items(), key=lambda x: -x[1])[:3]:
        if n >= 3:
            out.append(_ins(f"xdr_repeat:{h}", "xdr", "warn", f"Host {h} muncul berulang di alert XDR", f"{n} alert dalam 7 hari terakhir. Periksa apakah host perlu diisolasi atau dibersihkan.", "xdr", {"alert_7_hari": n}, None))
    return out


def d_devices(db: Session, cfg: Config) -> list[dict]:
    """Jumlah perangkat down saat ini dibanding pola 7 hari terakhir (per jenis), dan perangkat down kronis (lebih dari 30 hari)."""
    out = []
    now = cfg.now()
    for kind in [k for (k,) in db.execute(select(M.ZbxStat.kind).distinct())]:
        rows = db.execute(select(M.ZbxStat.hour, M.ZbxStat.down).where(M.ZbxStat.kind == kind, M.ZbxStat.hour >= now - timedelta(days=7)).order_by(M.ZbxStat.hour)).all()
        if len(rows) < MIN_BASE + 1:
            continue
        x = rows[-1][1]
        r = robust([d for _, d in rows[:-1]], x)
        if r and r[2] >= ZCUT and x - r[0] >= 10:
            out.append(_ins(f"dev_down:{kind}", "perangkat", "warn", f"Perangkat {kind} yang down jauh di atas biasanya", f"{x} perangkat down saat ini, biasanya sekitar {fmt(r[0])}. Kemungkinan gangguan jaringan atau listrik di satu area.", "devices",
                            {"nilai": x, "biasanya": round(r[0], 1), "z": round(r[2], 1)}))
    chronic = db.scalar(select(func.count()).select_from(M.ZbxHost).where(M.ZbxHost.status == "down", M.ZbxHost.down_since < now - timedelta(days=30)))
    if chronic:
        out.append(_ins("dev_chronic", "perangkat", "info", f"{chronic} perangkat down lebih dari 30 hari", "Perangkat yang lama tidak pulih memengaruhi availability. Tentukan apakah perlu diperbaiki, diganti, atau dikeluarkan dari pemantauan.", "devices", {"jumlah": chronic}))
    return out


def d_wifi(db: Session, cfg: Config) -> list[dict]:
    """Penurunan jumlah client WiFi dibanding jam yang sama pada hari-hari sebelumnya, dan AP yang tidak online."""
    out = []
    last = db.scalar(select(M.WifiStat).order_by(M.WifiStat.at.desc()).limit(1))
    if not last:
        return out
    if last.ap_total and last.ap_total - last.ap_online >= max(3, int(last.ap_total * 0.1)):
        out.append(_ins("wifi_ap_off", "wifi", "warn", f"{last.ap_total - last.ap_online} dari {last.ap_total} Access Point tidak online", "Jumlah AP offline lebih dari 10%. Cek zone dan lokasi pada halaman WiFi.", "wifi", {"offline": last.ap_total - last.ap_online, "total": last.ap_total}))
    same = [r for (r,) in db.execute(select(M.WifiStat.clients).where(func.extract("hour", M.WifiStat.at) == last.at.hour, M.WifiStat.at < last.at - timedelta(hours=3), M.WifiStat.at >= last.at - timedelta(days=14)))]
    r = robust(same, last.clients)
    if r and r[0] >= 30 and last.clients <= 0.6 * r[0] and r[2] <= -ZCUT:
        out.append(_ins("wifi_drop", "wifi", "warn", "Client WiFi turun tajam dibanding biasanya", f"{last.clients} client sekarang, biasanya sekitar {fmt(r[0])} pada jam ini. Kemungkinan gangguan controller, ISP, atau listrik.", "wifi", {"nilai": last.clients, "biasanya": round(r[0], 1), "z": round(r[2], 1)}))
    return out


DETECTORS = [d_tickets, d_links, d_availability, d_ndr, d_xdr, d_devices, d_wifi]


# ---------------- penyimpanan ----------------
def run(db: Session, cfg: Config) -> dict:
    """Jalankan semua detektor, simpan temuan baru atau perbarui yang ada, dan tandai selesai temuan yang tidak muncul lagi. Mengembalikan ringkasan dan daftar temuan baru."""
    now, found, errors = cfg.now(), {}, []
    for fn in DETECTORS:
        try:
            for i in fn(db, cfg):
                found[i["key"]] = i
        except Exception as e:                       # satu detektor gagal tidak menghentikan yang lain
            errors.append(f"{fn.__name__}: {str(e)[:100]}")
            db.rollback()
    existing = {r.key: r for r in db.scalars(select(M.Insight).where(M.Insight.status != "selesai"))}
    new = []
    for k, i in found.items():
        row = existing.get(k)
        if row:
            row.last_seen, row.severity, row.title, row.detail, row.metric = now, i["severity"], i["title"], i["detail"], i["metric"]
        else:
            row = M.Insight(key=k, kind=i["kind"], severity=i["severity"], title=i["title"], detail=i["detail"], tab=i["tab"], metric=i["metric"], site=i["site"], first_seen=now, last_seen=now, status="baru")
            db.add(row)
            new.append(i)
    closed = 0
    for k, row in existing.items():
        if k not in found:
            row.status, row.resolved_at, closed = "selesai", now, closed + 1
    db.flush()
    return {"found": len(found), "new": new, "closed": closed, "errors": errors}
