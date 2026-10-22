"""Penjadwal sinkron. Sumber, mode (api/impor), dan interval dibaca dari tabel data_source;
perubahan di Admin terbaca ulang tiap 5 menit. Advisory lock PostgreSQL mencegah dua worker sinkron bersamaan."""
import logging
import re
import time
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import text
from .db import session_scope
from .models import DataSource, SyncLog
from .store import load_config, bump_data, bump_config
from .ingest import manageengine, prtg, zabbix, ruckus, panorama_sync, trendmicro, milestone

log = logging.getLogger("itoc.jobs")
SYNCERS = {"manageengine": manageengine.sync_api, "prtg": prtg.sync_api, "zabbix": zabbix.sync_api, "ruckus": ruckus.sync_api, "panorama": panorama_sync.sync_api, "trendmicro": trendmicro.sync_api, "milestone": milestone.sync_api}
_sched: BackgroundScheduler | None = None


_tries: dict[str, int] = {}


def _retry_later(key: str, scheduled) -> None:
    """Sumber berjadwal jam tetap (mis. 00:00 dan 12:00) yang gagal diulang 10 menit kemudian, maksimal 3 kali, supaya tidak menunggu 12 jam untuk jadwal berikutnya."""
    from datetime import datetime, timedelta, timezone
    if not scheduled or _sched is None or _tries.get(key, 0) >= 3:
        return
    _tries[key] = _tries.get(key, 0) + 1
    _sched.add_job(run_source, "date", run_date=datetime.now(timezone.utc) + timedelta(minutes=10), args=[key], id="retry:" + key, replace_existing=True)


def run_source(key: str) -> dict:
    t0 = time.time()
    with session_scope() as db:
        if not db.execute(text("select pg_try_advisory_xact_lock(hashtext(:k))"), {"k": "sync:" + key}).scalar():
            return {"ok": False, "msg": "Sinkron sedang berjalan"}
        cfg = load_config(db)
        src = db.get(DataSource, key)
        fn = SYNCERS.get(key)
        if not src or not fn:
            return {"ok": False, "msg": "Sumber tidak dikenal"}
        try:
            n, msg = fn(db, cfg, src)
            src.last_ok_at, src.last_error = cfg.now(), None
            db.add(SyncLog(source=src.label, at=cfg.now(), ok=True, rows=n, ms=int((time.time() - t0) * 1000), message=msg))
            ok = True
        except Exception as e:  # dicatat, tidak menghentikan penjadwal
            log.exception("sync %s", key)
            db.rollback()
            src = db.get(DataSource, key)
            src.last_error = str(e)[:500]
            db.add(SyncLog(source=src.label, at=cfg.now(), ok=False, rows=0, ms=int((time.time() - t0) * 1000), message=str(e)[:300]))
            ok, msg, n = False, str(e), 0
            from . import notify
            notify.fire("sync_failed", f"Sinkron {src.label} gagal: {str(e)[:200]}")
            _retry_later(key, (src.config or {}).get("schedule"))
    if ok:
        _tries.pop(key, None)
    bump_data()
    bump_config()  # status sumber di header ikut segar
    return {"ok": ok, "rows": n, "msg": msg}


def run_insights() -> dict:
    """Analisis insight dari data yang sudah tersimpan; insight baru bertingkat warn atau crit dikirim lewat webhook (sekali per insight)."""
    from sqlalchemy import select
    from . import insight, notify
    from .models import Insight
    t0 = time.time()
    with session_scope() as db:
        if not db.execute(text("select pg_try_advisory_xact_lock(hashtext('insights'))")).scalar():
            return {"ok": False, "msg": "Analisis sedang berjalan"}
        cfg = load_config(db)
        try:
            r = insight.run(db, cfg)
            fresh = list(db.scalars(select(Insight).where(Insight.notified.is_(False), Insight.status != "selesai", Insight.severity.in_(["warn", "crit"]))))
            for x in fresh:
                x.notified = True
            msg = f"{r['found']} temuan, {len(r['new'])} baru, {r['closed']} selesai" + (f"; galat: {'; '.join(r['errors'])}" if r["errors"] else "")
            db.add(SyncLog(source="Insight", at=cfg.now(), ok=not r["errors"], rows=r["found"], ms=int((time.time() - t0) * 1000), message=msg[:300]))
            texts = [f"[{'KRITIS' if x.severity == 'crit' else 'PERINGATAN'}] {x.title}: {x.detail}" for x in fresh[:5]]
            if len(fresh) > 5:
                texts.append(f"dan {len(fresh) - 5} insight lain")
            out = {"ok": True, "found": r["found"], "new": len(r["new"]), "closed": r["closed"], "errors": r["errors"], "msg": msg}
        except Exception as e:
            log.exception("insight")
            return {"ok": False, "msg": str(e)[:200]}
    if texts:
        notify.fire("insight_new", "\n".join(texts), {"count": len(fresh)})
    bump_data()
    return out


def _refresh():
    """Jadwal dari data_source: config.schedule (daftar "HH:MM" waktu lokal, mis. ["00:00", "12:00"]) memakai jam tetap; selain itu interval_min."""
    with session_scope() as db:
        tz = float(load_config(db).p("tz_offset_hours", 7))
        wanted = {}
        for s in db.query(DataSource).filter_by(enabled=True, mode="api"):
            if s.key not in SYNCERS:
                continue
            times = [str(t) for t in ((s.config or {}).get("schedule") or []) if re.fullmatch(r"\d{1,2}:\d{2}", str(t))]
            if times:
                for t in times:
                    h, m = (int(x) for x in t.split(":"))
                    wanted[f"sync:{s.key}@{t}"] = ("cron", (int((h - tz) % 24), m), s.key)
            else:
                wanted[f"sync:{s.key}"] = ("int", s.interval_min, s.key)
    for job in _sched.get_jobs():
        if job.id.startswith("sync:") and job.id not in wanted:
            job.remove()
    for jid, (kind, spec, key) in wanted.items():
        job = _sched.get_job(jid)
        if kind == "int":
            if job is None or job.trigger.__class__.__name__ != "IntervalTrigger" or job.trigger.interval.total_seconds() != spec * 60:
                _sched.add_job(run_source, "interval", minutes=spec, args=[key], id=jid, replace_existing=True, max_instances=1, coalesce=True)
        elif job is None or job.name != str(spec):
            _sched.add_job(run_source, "cron", hour=spec[0], minute=spec[1], args=[key], id=jid, name=str(spec), replace_existing=True, max_instances=1, coalesce=True, misfire_grace_time=3600)


def _catch_up():
    """Sumber berjadwal jam tetap yang terlewat (server mati saat jamnya) ditarik sekali begitu server hidup lagi."""
    from datetime import datetime, timedelta
    with session_scope() as db:
        cfg = load_config(db)
        late = [s.key for s in db.query(DataSource).filter_by(enabled=True, mode="api")
                if s.key in SYNCERS and (s.config or {}).get("schedule") and (s.last_ok_at is None or cfg.now() - s.last_ok_at > timedelta(hours=12, minutes=30))]
    for key in late:
        _sched.add_job(run_source, args=[key], id="catchup:" + key, replace_existing=True)

def start():
    global _sched
    _sched = BackgroundScheduler(timezone="UTC")
    _sched.add_job(_refresh, "interval", minutes=5, id="refresh")
    from datetime import datetime, timedelta, timezone
    _sched.add_job(run_insights, "interval", minutes=30, id="insights", max_instances=1, coalesce=True, next_run_time=datetime.now(timezone.utc) + timedelta(minutes=1))
    _sched.start()
    try:
        _refresh()
        _catch_up()
    except Exception:
        log.exception("refresh jadwal")


def stop():
    if _sched:
        _sched.shutdown(wait=False)
