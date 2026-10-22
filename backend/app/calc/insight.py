"""Daftar insight untuk halaman Insight dan panel Overview."""
from datetime import timedelta
from sqlalchemy import select
from .. import models as M
from ..timeutil import ms

SEV = {"crit": 0, "warn": 1, "info": 2}


def _j(r) -> dict:
    return {"id": r.id, "kind": r.kind, "sev": r.severity, "title": r.title, "detail": r.detail, "tab": r.tab, "site": r.site, "metric": r.metric or {}, "status": r.status,
            "first": ms(r.first_seen), "last": ms(r.last_seen), "resolved": ms(r.resolved_at) if r.resolved_at else None, "ackBy": r.ack_by}


def build(db, cfg) -> dict:
    now = cfg.now()
    openr = sorted(db.scalars(select(M.Insight).where(M.Insight.status != "selesai")), key=lambda r: (SEV.get(r.severity, 9), -r.last_seen.timestamp()))
    done = db.scalars(select(M.Insight).where(M.Insight.status == "selesai", M.Insight.resolved_at >= now - timedelta(days=14)).order_by(M.Insight.resolved_at.desc()).limit(30))
    last = db.scalar(select(M.SyncLog).where(M.SyncLog.source == "Insight").order_by(M.SyncLog.id.desc()).limit(1))
    return {"open": [_j(r) for r in openr], "done": [_j(r) for r in done], "counts": {k: sum(1 for r in openr if r.severity == k) for k in SEV},
            "new": sum(1 for r in openr if r.status == "baru"), "updated": ms(last.at) if last else None, "lastMsg": last.message if last else ""}
