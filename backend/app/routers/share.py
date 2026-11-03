"""Share links for downloaded reports: a random token (only its hash is stored) that opens one report file without signing in, for at most 3 days.
The file is built when the link is opened, with the rights of the account that created it, so a link never shows more than that account may see."""
import hashlib
import secrets
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import ShareLink, User
from ..security import rate_limit, require_admin, require_admin_area, require_module
from ..store import audit, load_config
from .report import make_file

MAX_HOURS = 72
router = APIRouter(prefix="/api", tags=["share"])
admin = APIRouter(prefix="/api/admin", tags=["share"], dependencies=[Depends(require_admin_area)])


class ShareIn(BaseModel):
    fmt: str
    d_from: date = Field(alias="from")
    d_to: date = Field(alias="to")
    shift: int = 0
    site: str = ""
    kind: str = "full"
    preset: str = "standar"
    rgrp: str = ""
    rtech: str = ""
    risp: str = ""
    hours: int = MAX_HOURS


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@router.post("/report-share", dependencies=[Depends(rate_limit("share", 20, 60))])
def create(body: ShareIn, request: Request, user: User = Depends(require_module("report")), db: Session = Depends(get_db)):
    cfg = load_config(db)
    make_file(db, cfg, user, body.fmt, body.d_from, body.d_to, body.shift, body.site, body.kind, body.preset, body.rgrp, body.rtech, body.risp, dry=True)      # fails now, not when the link is opened
    token = secrets.token_urlsafe(32)
    hours = max(1, min(body.hours, MAX_HOURS))
    spec = {"fmt": body.fmt, "from": body.d_from.isoformat(), "to": body.d_to.isoformat(), "shift": body.shift, "site": body.site, "kind": body.kind, "preset": body.preset, "rgrp": body.rgrp, "rtech": body.rtech, "risp": body.risp}
    row = ShareLink(token_hash=_hash(token), created_by=user.username, spec=spec, created_at=cfg.now(), expires_at=cfg.now() + timedelta(hours=hours))
    db.add(row)
    audit(db, user.username, f"Created a report link ({body.kind} {body.fmt.upper()} {body.d_from} – {body.d_to}), valid {hours} hours")
    db.commit()
    base = (cfg.p("ui.public_url", "") or "").strip().rstrip("/") or str(request.base_url).rstrip("/")
    return {"url": f"{base}/api/share/{token}", "expires_at": row.expires_at.isoformat(), "hours": hours}


@router.get("/share/{token}", dependencies=[Depends(rate_limit("shareget", 30, 60))])
def open_link(token: str, db: Session = Depends(get_db)):
    cfg = load_config(db)
    row = db.query(ShareLink).filter_by(token_hash=_hash(token)).first()
    if not row or row.revoked_at or row.expires_at < cfg.now():
        raise HTTPException(404, "This link is not valid or has expired")
    user = db.query(User).filter_by(username=row.created_by, active=True).first()
    if not user:
        raise HTTPException(404, "This link is not valid or has expired")
    s = row.spec
    data, name, mime, _ = make_file(db, cfg, user, s["fmt"], date.fromisoformat(s["from"]), date.fromisoformat(s["to"]), s["shift"], s["site"], s["kind"], s["preset"], s["rgrp"], s["rtech"], s["risp"])
    row.downloads, row.last_used_at = (row.downloads or 0) + 1, cfg.now()
    db.commit()
    return Response(content=data, media_type=mime, headers={"Content-Disposition": f'attachment; filename="{name}"', "Cache-Control": "no-store", "X-Robots-Tag": "noindex"})


@admin.get("/sharelinks")
def listing(db: Session = Depends(get_db)):
    now = load_config(db).now()
    rows = db.query(ShareLink).order_by(ShareLink.created_at.desc()).limit(200).all()
    return {"rows": [{"id": r.id, "by": r.created_by, "kind": r.spec.get("kind"), "fmt": r.spec.get("fmt"), "from": r.spec.get("from"), "to": r.spec.get("to"), "site": r.spec.get("site"), "created": r.created_at.isoformat(),
                      "expires": r.expires_at.isoformat(), "downloads": r.downloads or 0, "last": r.last_used_at.isoformat() if r.last_used_at else None,
                      "state": "revoked" if r.revoked_at else "expired" if r.expires_at < now else "active"} for r in rows]}


@admin.post("/sharelinks/{lid}/revoke")
def revoke(lid: int, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    r = db.get(ShareLink, lid)
    if not r:
        raise HTTPException(404, "Link not found")
    r.revoked_at = load_config(db).now()
    audit(db, user.username, f"Revoked report link #{lid} of {r.created_by}")
    db.commit()
    return {"ok": True}
