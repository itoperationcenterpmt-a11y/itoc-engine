"""Insight otomatis: tandai dibaca dan jalankan analisis sekarang."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import insight as INS
from ..db import get_db
from ..models import Insight, User
from ..security import current_user, can_see, rate_limit, require_admin
from ..store import audit, load_config, bump_data

router = APIRouter(prefix="/api/insights", tags=["insight"])


@router.post("/{iid}/ack", dependencies=[Depends(rate_limit("insack", 60, 60))])
def ack(iid: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if not can_see(user, "insight"):
        raise HTTPException(403, "Akun ini tidak punya akses ke Insight")
    r = db.get(Insight, iid)
    if not r:
        raise HTTPException(404, "Insight tidak ditemukan")
    cfg = load_config(db)
    if r.status == "baru":
        r.status, r.ack_by, r.ack_at = "dibaca", user.username, cfg.now()
        audit(db, user.username, f"Menandai insight dibaca: {r.title[:120]}", None, cfg.p("tz_offset_hours", 7))
        db.commit()
        bump_data()
    return {"ok": True}


@router.post("/run", dependencies=[Depends(rate_limit("insrun", 6, 60))])
def run_now(db: Session = Depends(get_db), user: User = Depends(require_admin)):
    from ..jobs import run_insights
    r = run_insights()
    audit(db, user.username, "Menjalankan analisis insight", {"found": r.get("found")}, load_config(db).p("tz_offset_hours", 7))
    db.commit()
    return r
