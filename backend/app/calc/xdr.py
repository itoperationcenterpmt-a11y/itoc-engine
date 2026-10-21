"""Alert XDR (Trend Micro Vision One) dari tabel xdr_alert: ringkasan menurut periode dan severity."""
from datetime import datetime, time as dtime, timedelta
from sqlalchemy import func
from ..models import DataSource, XdrAlert
from ..store import Config
from ..timeutil import ms

SEV = ["critical", "high", "medium", "low"]


def _open(r) -> bool:
    return (r.status or "").lower() != "closed" and (r.investigation_status or "").lower() != "closed"


def _top(items, n=10):
    c: dict = {}
    for k in items:
        c[k or "-"] = c.get(k or "-", 0) + 1
    return [{"k": k, "n": v} for k, v in sorted(c.items(), key=lambda x: -x[1])[:n]]


def build(db, cfg: Config, a, b, severity: str = "") -> dict:
    t0, t1 = datetime.combine(a, dtime.min), datetime.combine(b + timedelta(days=1), dtime.min)
    q = db.query(XdrAlert).filter(XdrAlert.created_at >= t0, XdrAlert.created_at < t1)
    if severity:
        q = q.filter(XdrAlert.severity == severity)
    rows = q.order_by(XdrAlert.created_at.desc()).all()
    src = db.get(DataSource, "trendmicro")
    last = db.query(func.max(XdrAlert.fetched_at)).scalar()
    every = (src.interval_min if src else 15) or 15
    now = cfg.now()
    daily, d = {}, a
    while d <= b:
        daily[d] = {x: 0 for x in SEV}
        d += timedelta(days=1)
    imp = {"desktop": 0, "server": 0, "account": 0, "email": 0}
    for r in rows:
        if r.severity in SEV and r.created_at.date() in daily:
            daily[r.created_at.date()][r.severity] += 1
        i = r.impact or {}
        imp["desktop"] += int(i.get("desktopCount") or 0)
        imp["server"] += int(i.get("serverCount") or 0)
        imp["account"] += int(i.get("accountCount") or 0)
        imp["email"] += int(i.get("emailAddressCount") or 0)
    scores = [r.score for r in rows if r.score is not None]
    backlog = db.query(XdrAlert).filter(XdrAlert.status.isnot(None)).all()
    bl = [r for r in backlog if _open(r) and r.severity in ("critical", "high")]
    return {"total": len(rows), "open": sum(1 for r in rows if _open(r)), "backlogCH": len(bl), "avgScore": round(sum(scores) / len(scores), 1) if scores else None,
            "bySev": [{"k": s, "n": sum(1 for r in rows if r.severity == s)} for s in SEV], "byStatus": _top([r.investigation_status or r.status for r in rows]),
            "byModel": _top([r.model for r in rows], 10), "byProvider": _top([r.provider for r in rows], 6), "impact": imp,
            "daily": [{"date": k.isoformat(), **v} for k, v in daily.items()],
            "list": [{"id": r.id, "model": r.model, "severity": r.severity, "score": r.score, "status": r.investigation_status or r.status, "provider": r.provider,
                      "created": ms(r.created_at), "updated": ms(r.updated_at), "link": r.link, "open": _open(r), "impact": r.impact or {}} for r in rows[:300]],
            "listN": len(rows), "updated": ms(last + (now - datetime.utcnow())) if last else None,
            "stale": bool(last) and (datetime.utcnow() - last).total_seconds() > every * 60 * 3,
            "configured": bool(src and (src.config or {}).get("base_url")), "enabled": bool(src and src.enabled), "error": src.last_error if src else None}