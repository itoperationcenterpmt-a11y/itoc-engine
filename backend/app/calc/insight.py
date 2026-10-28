"""Insights for the Insights page (under Report) and the Overview panel."""
import re
from datetime import timedelta
from sqlalchemy import select
from .. import insight as ENG
from .. import models as M
from ..timeutil import ms
from .network import device_names, shared_isp

SEV = {"crit": 0, "warn": 1, "info": 2}


def _site_names(db, site: str) -> list[str]:
    """Names that identify a location in findings: site name, its aliases, and the locations that share its ISP links."""
    return sorted({n for x in shared_isp(db, site) for n in device_names(db, x)})


def _at_site(r, names: list[str]) -> bool:
    """A finding belongs to a location when its site field matches, or the location name appears in its title or detail (link findings name the link, e.g. "Mekarputih – Astinet")."""
    if (r.site or "").lower() in names:
        return True
    text = f"{r.title} {r.detail}".lower()
    return any(len(n) >= 3 and re.search(r"\b" + re.escape(n) + r"\b", text) for n in names)


def _j(r) -> dict:
    return {"id": r.id, "kind": r.kind, "sev": r.severity, "title": r.title, "detail": r.detail, "tab": r.tab, "site": r.site, "metric": r.metric or {}, "status": r.status,
            "first": ms(r.first_seen), "last": ms(r.last_seen), "resolved": ms(r.resolved_at) if r.resolved_at else None, "ackBy": r.ack_by, "reason": r.reason,
            "until": ms(r.suppress_until) if r.suppress_until else None, "handover": r.handover_id}


def build(db, cfg, full: bool = False, site: str = "") -> dict:
    """Light version (counts and open findings) for the Overview; full version adds rankings, location health, shift summary, and history.
    site (Location filter on the Network page) keeps only the findings of that location and adds its health row."""
    now = cfg.now()
    live = sorted(db.scalars(select(M.Insight).where(M.Insight.status.in_(["new", "read"]))), key=lambda r: (SEV.get(r.severity, 9), -r.last_seen.timestamp()))
    if site:
        names = _site_names(db, site)
        live = [r for r in live if _at_site(r, names)]
    last = db.scalar(select(M.SyncLog).where(M.SyncLog.source == "Insight").order_by(M.SyncLog.id.desc()).limit(1))
    out = {"open": [_j(r) for r in live], "counts": {k: sum(1 for r in live if r.severity == k) for k in SEV}, "new": sum(1 for r in live if r.status == "new"),
           "updated": ms(last.at) if last else None, "lastMsg": last.message if last else ""}
    if site:
        out["site"] = site
        out["siteHealth"] = next((h for h in ENG.site_health(db, cfg) if h["site"] == site), None)
    if not full:
        return out
    done = db.scalars(select(M.Insight).where(M.Insight.status == "resolved", M.Insight.resolved_at >= now - timedelta(days=14)).order_by(M.Insight.resolved_at.desc()).limit(30))
    dis = db.scalars(select(M.Insight).where(M.Insight.status == "dismissed").order_by(M.Insight.ack_at.desc()).limit(30))
    kinds: dict = {}
    for kind, status in db.execute(select(M.Insight.kind, M.Insight.status).where(M.Insight.first_seen >= now - timedelta(days=30))):
        s = kinds.setdefault(kind, {"total": 0, "dismissed": 0})
        s["total"] += 1
        s["dismissed"] += 1 if status == "dismissed" else 0
    out.update({"done": [_j(r) for r in done], "dismissed": [_j(r) for r in dis], "rank": ENG.rankings(db, cfg), "stats": kinds,
                "summary": ENG.shift_summary(db, cfg), "windows": ENG.summary_windows(cfg)})
    return out
