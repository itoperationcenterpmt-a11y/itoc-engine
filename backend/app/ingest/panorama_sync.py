"""Sinkron SOC dari Panorama lewat dynamic report API (tanpa custom report): ringkasan harian (ancaman, URL, aplikasi) menjadi satu batch per hari,
dan laporan Top (sumber, host internal, high/critical, URL diblokir, trafik, ditolak) menjadi satu batch periode yang diperbarui berkala.
Isinya sama dengan CSV custom report, dibentuk dari Panorama langsung, lalu masuk ke jalur impor yang sama (panorama._build). Impor CSV tetap bisa dipakai."""
from datetime import date, datetime, timedelta
import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session
from .. import vault
from ..models import DataSource, SocBatch, SocDay
from ..store import Config
from . import panorama, panorama_api as PA

BLOCK_URL = "( action eq block-url ) or ( action eq block-continue ) or ( action eq block-override )"
DENIED = "( action eq deny ) or ( action eq drop ) or ( action eq reset-both ) or ( action eq reset-client ) or ( action eq reset-server )"
PERIODS = [(7, "last-7-days"), (30, "last-30-days"), (60, "last-60-days"), (90, "last-90-days")]
g = lambda r, k: r.get(k, "")
PARTIAL = "Panorama API · today (provisional)"

# (kunci laporan, jenis, kelompok, nilai, filter, bentuk baris sesuai urutan kolom CSV)
DAILY = [
    ("threat_summary", "threat", ["severity", "threat-type", "thr_category", "action", "app", "srcloc", "dstloc"], ["repeatcnt"], "", 5000,
     lambda r, d: [d, g(r, "severity"), g(r, "threat-type"), g(r, "thr_category"), g(r, "action"), g(r, "app"), g(r, "srcloc"), g(r, "dstloc"), g(r, "repeatcnt")]),
    ("url_summary", "urlsum", ["category", "action", "app"], ["repeatcnt"], "", 5000, lambda r, d: [d, g(r, "category"), g(r, "action"), g(r, "app"), g(r, "repeatcnt")]),
    ("appstats", "trsum", ["app"], ["bytes", "sessions"], "", 2000, lambda r, d: [d, g(r, "app"), g(r, "bytes"), g(r, "sessions")]),
]
TOP = [
    ("top_source", "threat", ["src", "srcloc", "severity"], ["repeatcnt"], "( srcloc neq '{internal}' )", 500, lambda r: [g(r, "src"), "", g(r, "srcloc"), g(r, "severity"), g(r, "repeatcnt")]),
    ("internal_host", "threat", ["src", "srcuser", "threatid", "threat-type", "severity", "action", "dst"], ["repeatcnt"], "( srcloc eq '{internal}' )", 500,
     lambda r: [g(r, "src"), "", g(r, "srcuser"), g(r, "threatid"), g(r, "severity"), g(r, "action"), g(r, "dst"), "", g(r, "repeatcnt")]),
    ("high_critical", "threat", ["src", "dst", "srcuser", "app", "from", "to", "action", "severity", "threat-type", "threatid", "thr_category"], ["repeatcnt"], "( severity geq high )", 1000,
     lambda r: [g(r, "src"), "", g(r, "dst"), "", g(r, "srcuser"), g(r, "app"), g(r, "from"), g(r, "to"), g(r, "action"), g(r, "severity"), g(r, "threat-type"), g(r, "threatid"), g(r, "thr_category"), "", g(r, "repeatcnt")]),
    ("url_blocked", "url", ["src", "dst", "app", "rule", "from", "to", "action", "category", "srcuser", "url"], ["repeatcnt"], BLOCK_URL, 500,
     lambda r: [g(r, "src"), "", g(r, "dst"), "", g(r, "app"), g(r, "rule"), g(r, "from"), g(r, "to"), g(r, "action"), g(r, "category"), g(r, "srcuser"), g(r, "url"), g(r, "repeatcnt")]),
    ("denied", "trsum", ["src", "srcloc", "dst", "to", "app", "rule", "action"], ["sessions", "bytes"], DENIED, 500,
     lambda r: [g(r, "src"), "", g(r, "srcloc"), g(r, "dst"), "", g(r, "to"), g(r, "app"), g(r, "rule"), g(r, "action"), g(r, "sessions"), g(r, "bytes")]),
    ("traffic_top", "trsum", ["src", "dst", "from", "to", "dstloc"], ["bytes", "sessions"], "", 500,
     lambda r: [g(r, "src"), "", g(r, "dst"), "", g(r, "from"), g(r, "to"), g(r, "dstloc"), g(r, "bytes"), g(r, "sessions")]),
    ("traffic_app", "trsum", ["app", "category-of-app"], ["bytes", "bytes_sent", "bytes_received"], "", 500,
     lambda r: [g(r, "app"), g(r, "category-of-app"), g(r, "bytes"), g(r, "bytes_sent"), g(r, "bytes_received")]),
    ("rule_zone", "trsum", ["rule", "from", "to"], ["bytes", "bytes_sent", "bytes_received"], "", 500,
     lambda r: [g(r, "rule"), g(r, "from"), g(r, "to"), g(r, "bytes"), g(r, "bytes_sent"), g(r, "bytes_received")]),
]
NUMERIC = {"count", "bytes", "bytes sent", "bytes received", "sessions"}


def _numeric(key: str, rows: list[list]) -> list[list]:
    """Kolom angka diubah ke float seperti pada jalur CSV (panorama.read_csv_reports)."""
    head = [h.strip().lower() for h in panorama.CSV_HEADERS[key]]
    idx = [i for i, h in enumerate(head) if h in NUMERIC] + ([12] if key == "url_blocked" else [14] if key == "high_critical" else [])
    for r in rows:
        for i in idx:
            if i < len(r):
                r[i] = panorama.num(r[i])
    return rows


def _period_for(day: date, today: date) -> str | None:
    age = (today - day).days
    return next((p for n, p in PERIODS if age < n), None)


def _day_query(day: date) -> str:
    d = day.strftime("%Y/%m/%d")
    return f"( receive_time geq '{d} 00:00:00' ) and ( receive_time leq '{d} 23:59:59' )"


def _model(db: Session, cfg: Config, d: date, reports: dict, label: str, with_days: bool) -> SocBatch | None:
    xc = cfg.sources["panorama"]["config"]["excel"]
    by = {xc["reports"].get(k, k): rows for k, rows in reports.items()}
    P = panorama._build(by, cfg, xc, cfg.p("soc.internal_range"), cfg.p("soc.internet_zone"))
    if with_days and not P["days"]:
        return None
    b = SocBatch(file_name=label, uploaded_by="Panorama API", uploaded_at=cfg.now(), date_from=date.fromisoformat(P["from"]) if P["from"] else d, date_to=date.fromisoformat(P["to"]) if P["to"] else d,
                 rows_read=P["read"], rows_skipped=P["skipped"], status="valid", issues=[], tables=P["tables"], kpi=P["K"])
    for k, v in P["days"].items():
        b.days.append(SocDay(day=date.fromisoformat(k), threats=v["th"], urls=v["url"], bytes=int(v["b"]), sessions=int(v["s"])))
    db.add(b)
    return b


def _month_end(d: date) -> date:
    return (d.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)


def _top_jobs(c: dict, cfg: Config, cur: dict, now: datetime, yesterday: date, lower: date) -> list[tuple[str, date, date, str]]:
    """Batch Top yang perlu dibuat atau diperbarui: 30 hari dan 7 hari terakhir serta bulan berjalan (diperbarui tiap top_refresh_h jam), dan tiap bulan penuh
    sejak batas riwayat (sekali saja). Filter periode di halaman memilih batch yang paling cocok."""
    every = float(c.get("top_refresh_h", 12)) * 3600
    age = lambda label: (now - datetime.fromisoformat(cur["top_at_k"][label])).total_seconds() if label in cur.get("top_at_k", {}) else 1e12
    jobs = []
    for label, n in (("Top 30 days", 30), ("Top 7 days", 7)):
        if age(label) > every:
            jobs.append((label, yesterday - timedelta(days=n - 1), yesterday, "roll"))
    first = yesterday.replace(day=1)
    if first <= yesterday and age(f"Top {first:%Y-%m} berjalan") > every:
        jobs.insert(1, (f"Top {first:%Y-%m} berjalan", first, yesterday, "roll"))
    done, m = set(cur.get("top_months", [])), first
    while True:
        m = (m - timedelta(days=1)).replace(day=1)
        if _month_end(m) < lower:
            break
        if f"Top {m:%Y-%m}" not in done:
            jobs.append((f"Top {m:%Y-%m}", max(m, lower), _month_end(m), "month"))
    return jobs

def sync_api(db: Session, cfg: Config, src: DataSource) -> tuple[int, str]:
    c = src.config or {}
    user, pw = vault.cred(db, "pano.user", c.get("user_env", "PANO_USER")), vault.cred(db, "pano.pass", c.get("pass_env", "PANO_PASS"))
    if not c.get("base_url") or not user or not pw:
        raise RuntimeError("Panorama Base URL / API account is not set (Admin → Data Sources → Integrations)")
    cur = dict(src.cursor or {})
    now = cfg.now()
    today, yesterday = now.date(), now.date() - timedelta(days=1)
    lower = date.fromisoformat(c["backfill_from"]) if c.get("backfill_from") else yesterday - timedelta(days=int(c.get("backfill_days", 14)) - 1)
    have = {x for (x,) in db.execute(select(SocDay.day).join(SocBatch).where(SocBatch.status != "failed", SocBatch.file_name != PARTIAL))}   # hari yang sudah ada (impor CSV) tidak ditimpa; data sementara hari ini tidak dihitung
    for old in db.scalars(select(SocBatch).where(SocBatch.file_name == PARTIAL, SocBatch.date_to < today)):
        db.delete(old)                                                                                         # hari sementara yang sudah lewat digantikan data harian lengkap
    tried = set(cur.get("tried", []))                                                                          # hari yang sudah dicoba tetapi kosong di Panorama
    pending, d = [], lower
    while d <= yesterday and len(pending) < int(c.get("max_days_per_run", 4)):
        if d not in have and d.isoformat() not in tried:
            pending.append(d)
        d += timedelta(days=1)
    top_jobs = _top_jobs(c, cfg, cur, now, yesterday, lower)
    partial = bool(c.get("today_partial", True))
    if not pending and not top_jobs and not partial:
        return 0, "No new days and the Top report is still fresh"
    notes, n_days, n_rows, n_top, n_part = [], 0, 0, 0, 0
    with httpx.Client(timeout=60, verify=c.get("verify_tls", False)) as cl:
        key = PA.keygen(cl, c["base_url"], user, pw)
        for d in pending:
            try:
                reports = {}
                rng = (d.strftime("%Y/%m/%d 00:00:00"), d.strftime("%Y/%m/%d 23:59:59"))
                for k, typ, aggs, vals, q, topn, fmt in DAILY:
                    recs = PA.run_dynamic(cl, c["base_url"], key, typ, aggs, vals, "", "", topn, rng=rng)
                    reports[k] = _numeric(k, [fmt(r, d.strftime("%Y-%m-%d 00:00:00")) for r in recs])
                b = _model(db, cfg, d, reports, f"Panorama API · {d.isoformat()}", True)
                if b is not None:
                    n_days += 1
                    n_rows += b.rows_read
                tried.add(d.isoformat())
            except (RuntimeError, httpx.HTTPError) as e:
                notes.append(f"day {d.isoformat()} failed: {str(e)[:120]}")
                break
        if partial:
            try:                                                      # hari ini sampai saat ini (sementara): diganti tiap sinkron, lalu digantikan data harian lengkap esok hari
                reports, rng = {}, (today.strftime("%Y/%m/%d 00:00:00"), now.strftime("%Y/%m/%d %H:%M:%S"))
                for k, typ, aggs, vals, q, topn, fmt in DAILY:
                    recs = PA.run_dynamic(cl, c["base_url"], key, typ, aggs, vals, "", "", topn, rng=rng)
                    reports[k] = _numeric(k, [fmt(r, today.strftime("%Y-%m-%d 00:00:00")) for r in recs])
                if any(reports.values()):
                    for old in db.scalars(select(SocBatch).where(SocBatch.file_name == PARTIAL)):
                        db.delete(old)
                    db.flush()
                    b = _model(db, cfg, today, reports, PARTIAL, True)
                    n_part = 1 if b is not None else 0
            except (RuntimeError, httpx.HTTPError) as e:
                notes.append(f"today's data failed: {str(e)[:100]}")
        for label, d0, d1, kind in top_jobs[:int(c.get("max_top_per_run", 3))]:
            try:
                rng = (d0.strftime("%Y/%m/%d 00:00:00"), d1.strftime("%Y/%m/%d 23:59:59"))
                reports = {}
                for k, typ, aggs, vals, q, topn, fmt in TOP:
                    q = q.replace("{internal}", str(cfg.p("soc.internal_range") or ""))
                    recs = PA.run_dynamic(cl, c["base_url"], key, typ, aggs, vals, "", q, int(c.get("top_n", topn)) if topn <= 500 else topn, rng=rng, wait_s=int(c.get("top_wait_s", 600)))
                    reports[k] = _numeric(k, [fmt(r) for r in recs])
                for old in db.scalars(select(SocBatch).where(SocBatch.file_name == "Panorama API · " + label)):
                    db.delete(old)                                   # hanya batch API dengan label yang sama; impor manual tidak pernah dihapus
                db.flush()
                b = _model(db, cfg, d1, reports, "Panorama API · " + label, False)
                b.date_from, b.date_to = d0, d1
                if kind == "month":
                    cur["top_months"] = sorted(set(cur.get("top_months", [])) | {label})
                else:
                    cur.setdefault("top_at_k", {})[label] = now.isoformat()
                n_top += 1
                n_rows += sum(len(v) for v in reports.values())
            except (RuntimeError, httpx.HTTPError) as e:
                notes.append(f"{label} failed: {str(e)[:100]}")
                continue                                              # batch Top lain tetap dicoba; yang gagal diulang pada sinkron berikutnya
    cur["tried"] = sorted(tried)[-800:]
    src.cursor = cur
    if notes and not n_days and not n_top and not n_part:
        raise RuntimeError("; ".join(notes))
    return n_rows, f"{n_days} hari ringkasan baru, {n_top} laporan Top diperbarui" + (", today's data updated" if n_part else "") + ("; " + "; ".join(notes) if notes else "")