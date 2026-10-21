"""Penjadwal sinkron. Sumber, mode (api/impor), dan interval dibaca dari tabel data_source;
perubahan di Admin terbaca ulang tiap 5 menit. Advisory lock PostgreSQL mencegah dua worker sinkron bersamaan."""
import logging
import time
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import text
from .db import session_scope
from .models import DataSource, SyncLog
from .store import load_config, bump_data, bump_config
from .ingest import manageengine, prtg, zabbix, ruckus, panorama_sync

log = logging.getLogger("itoc.jobs")
SYNCERS = {"manageengine": manageengine.sync_api, "prtg": prtg.sync_api, "zabbix": zabbix.sync_api, "ruckus": ruckus.sync_api, "panorama": panorama_sync.sync_api}
_sched: BackgroundScheduler | None = None


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
    bump_data()
    bump_config()  # status sumber di header ikut segar
    return {"ok": ok, "rows": n, "msg": msg}


def _refresh():
    with session_scope() as db:
        wanted = {s.key: s.interval_min for s in db.query(DataSource).filter_by(enabled=True, mode="api") if s.key in SYNCERS}
    for job in _sched.get_jobs():
        if job.id.startswith("sync:") and job.id[5:] not in wanted:
            job.remove()
    for key, every in wanted.items():
        job = _sched.get_job("sync:" + key)
        if job is None or job.trigger.interval.total_seconds() != every * 60:
            _sched.add_job(run_source, "interval", minutes=every, args=[key], id="sync:" + key, replace_existing=True, max_instances=1, coalesce=True)


def start():
    global _sched
    _sched = BackgroundScheduler(timezone="UTC")
    _sched.add_job(_refresh, "interval", minutes=5, id="refresh")
    _sched.start()
    try:
        _refresh()
    except Exception:
        log.exception("refresh jadwal")


def stop():
    if _sched:
        _sched.shutdown(wait=False)
