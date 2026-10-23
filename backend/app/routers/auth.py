from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import AuditLog, User
from ..security import COOKIE, check_pw, make_token, current_user, hash_pw, set_session, rate_limit
from ..store import load_config, audit

router = APIRouter(prefix="/api/auth", tags=["auth"])


class Login(BaseModel):
    username: str
    password: str


class PwChange(BaseModel):
    old: str
    new: str


# Batas percobaan gagal: 5 per akun dan 40 per alamat dalam 10 menit. Dihitung dari audit_log (satu sumber untuk semua proses), jadi berlaku walau ada banyak worker.
_WINDOW, _MAX_USER, _MAX_IP = 600, 5, 40
_DUMMY = hash_pw("dummy-password-for-timing")
_WEAK = {"password", "password1", "password123", "12345678", "123456789", "1234567890", "qwerty123", "admin123", "itoc1234", "welcome123", "pelindo123"}


def _locked(db: Session, cfg, name: str, ip: str) -> bool:
    since = cfg.now() - timedelta(seconds=_WINDOW)
    q = db.query(func.count(AuditLog.id)).filter(AuditLog.action == "Login failed", AuditLog.at >= since)
    return q.filter(AuditLog.username == name[:60]).scalar() >= _MAX_USER or q.filter(AuditLog.detail["ip"].astext == ip).scalar() >= _MAX_IP


@router.post("/login")
def login(body: Login, request: Request, response: Response, db: Session = Depends(get_db)):
    cfg = load_config(db)
    name = body.username.strip().lower()[:60]
    ip = request.client.host if request.client else "?"
    if _locked(db, cfg, name, ip):
        raise HTTPException(429, "Too many login attempts. Try again in a few minutes.")
    u = db.query(User).filter_by(username=name).one_or_none()
    ok = check_pw(body.password, u.password_hash if u else _DUMMY)   # waktu proses sama untuk akun yang tidak ada
    if not u or not u.active or not ok:
        audit(db, name, "Login failed", {"ip": ip}, cfg.p("tz_offset_hours", 7))
        db.commit()
        raise HTTPException(401, "Wrong username or password")
    u.last_login = cfg.now()
    audit(db, u.username, "Login", {"ip": ip}, cfg.p("tz_offset_hours", 7))
    db.commit()
    set_session(response, request, make_token(u))
    return {"must_change_pw": u.must_change_pw}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return {"username": user.username}


@router.post("/logout")
def logout(request: Request, response: Response):
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@router.post("/password", dependencies=[Depends(rate_limit("pw", 5, 600))])
def change_pw(body: PwChange, request: Request, response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)):
    cfg = load_config(db)
    if not check_pw(body.old, user.password_hash):
        raise HTTPException(400, "The old password is wrong")
    n = cfg.p("auth.min_password", 10)
    if len(body.new) < n:
        raise HTTPException(400, f"Password minimal {n} karakter")
    if len(body.new.encode()) > 72:
        raise HTTPException(400, "Password maksimal 72 byte")
    if body.new == body.old or body.new.lower() in _WEAK or user.username in body.new.lower():
        raise HTTPException(400, "The password is too easy to guess or the same as the old one")
    user.password_hash, user.must_change_pw = hash_pw(body.new), False
    audit(db, user.username, "Mengganti password", None, cfg.p("tz_offset_hours", 7))
    db.commit()
    set_session(response, request, make_token(user))                # token lama gugur; sesi ini tetap berjalan
    return {"ok": True}