"""Insights: acknowledge, dismiss with a reason, reopen, add to handover, and run the analysis now."""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Handover, Insight, User
from ..security import current_user, can_see, rate_limit, require_admin
from ..store import audit, bump_data, load_config

router = APIRouter(prefix="/api/insights", tags=["insight"])


def _get(db: Session, user: User, iid: int) -> Insight:
    if not can_see(user, "insight"):
        raise HTTPException(403, "This account has no access to Insights")
    r = db.get(Insight, iid)
    if not r:
        raise HTTPException(404, "Insight not found")
    return r


class DismissIn(BaseModel):
    reason: str = ""
    days: int = 7


@router.post("/{iid}/ack", dependencies=[Depends(rate_limit("insack", 60, 60))])
def ack(iid: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    r = _get(db, user, iid)
    cfg = load_config(db)
    if r.status == "new":
        r.status, r.ack_by, r.ack_at = "read", user.username, cfg.now()
        audit(db, user.username, f"Marked insight as read: {r.title[:120]}", None, cfg.p("tz_offset_hours", 7))
        db.commit()
        bump_data()
    return {"ok": True}


@router.post("/{iid}/dismiss", dependencies=[Depends(rate_limit("insdis", 60, 60))])
def dismiss(iid: int, body: DismissIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    r = _get(db, user, iid)
    cfg = load_config(db)
    days = max(1, min(body.days, 90))
    r.status, r.ack_by, r.ack_at, r.reason, r.suppress_until = "dismissed", user.username, cfg.now(), body.reason.strip()[:200] or None, cfg.now() + timedelta(days=days)
    audit(db, user.username, f"Dismissed insight for {days} days: {r.title[:100]}", {"reason": r.reason}, cfg.p("tz_offset_hours", 7))
    db.commit()
    bump_data()
    return {"ok": True}


@router.post("/{iid}/reopen", dependencies=[Depends(rate_limit("insreo", 60, 60))])
def reopen(iid: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    r = _get(db, user, iid)
    if r.status == "dismissed":
        r.status, r.suppress_until = "new", None
        audit(db, user.username, f"Reopened insight: {r.title[:120]}", None, load_config(db).p("tz_offset_hours", 7))
        db.commit()
        bump_data()
    return {"ok": True}


@router.post("/{iid}/handover", dependencies=[Depends(rate_limit("inshand", 20, 60))])
def to_handover(iid: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Create an open handover from this insight so the next shift sees it."""
    r = _get(db, user, iid)
    if not user.role.can_write:
        raise HTTPException(403, "This role is read-only")
    if r.handover_id:
        raise HTTPException(409, "A handover already exists for this insight")
    cfg = load_config(db)
    cats = cfg.p("ho.categories") or ["General"]
    want = {"links": "NOC", "capacity": "NOC", "devices": "NOC", "security": "SOC", "tickets": "Service Desk"}.get(r.kind)
    pri = [p["value"] for p in (cfg.p("ho.priorities") or [])] or ["Medium"]
    site = r.site if r.site in cfg.sites else (cfg.sites[0] if cfg.sites else "")
    now = cfg.now()
    h = Handover(created_at=now, shift_date=cfg.clock.duty_date(now), shift_no=cfg.clock.shift_of(now.hour), category=want if want in cats else cats[-1],
                 priority=pri[0] if r.severity == "crit" else pri[min(1, len(pri) - 1)], site=site, ticket_id=None, title=r.title[:160], body=r.detail, next_action="Follow up on this insight.",
                 created_by=user.full_name, is_open=True)
    db.add(h)
    db.flush()
    r.handover_id = h.id
    audit(db, user.username, f"Created handover from insight: {r.title[:100]}", None, cfg.p("tz_offset_hours", 7))
    db.commit()
    bump_data()
    return {"ok": True, "id": h.id}


@router.post("/run", dependencies=[Depends(rate_limit("insrun", 6, 60))])
def run_now(db: Session = Depends(get_db), user: User = Depends(require_admin)):
    from ..jobs import run_insights
    r = run_insights()
    audit(db, user.username, "Ran the insight analysis", {"found": r.get("found")}, load_config(db).p("tz_offset_hours", 7))
    db.commit()
    return r
