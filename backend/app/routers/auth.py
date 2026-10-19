import time
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User
from ..security import check_pw, make_token, current_user, hash_pw
from ..store import load_config, audit

router = APIRouter(prefix="/api/auth", tags=["auth"])


class Login(BaseModel):
    username: str
    password: str


class PwChange(BaseModel):
    old: str
    new: str


# Batas percobaan gagal (per proses): 5 per akun dan 40 per alamat dalam 10 menit.
_FAILS: dict[str, list[float]] = {}
_WINDOW, _MAX_USER, _MAX_IP = 600, 5, 40
_DUMMY = hash_pw("dummy-password-for-timing")


def _recent(key: str) -> list[float]:
    now = time.time()
    v = [t for t in _FAILS.get(key, []) if now - t < _WINDOW]
    if v:
        _FAILS[key] = v
    else:
        _FAILS.pop(key, None)
    return v


@router.post("/login")
def login(body: Login, request: Request, db: Session = Depends(get_db)):
    name = body.username.strip().lower()
    ip = request.client.host if request.client else "?"
    ku, ki = "u:" + name, "i:" + ip
    if len(_recent(ku)) >= _MAX_USER or len(_recent(ki)) >= _MAX_IP:
        raise HTTPException(429, "Terlalu banyak percobaan login. Coba lagi dalam beberapa menit.")
    u = db.query(User).filter_by(username=name).one_or_none()
    ok = check_pw(body.password, u.password_hash if u else _DUMMY)   # waktu proses sama untuk akun yang tidak ada
    if not u or not u.active or not ok:
        now = time.time()
        _FAILS.setdefault(ku, []).append(now)
        _FAILS.setdefault(ki, []).append(now)
        raise HTTPException(401, "Username atau password salah")
    _FAILS.pop(ku, None)
    cfg = load_config(db)
    u.last_login = cfg.now()
    audit(db, u.username, "Login")
    db.commit()
    return {"token": make_token(u), "must_change_pw": u.must_change_pw}


@router.post("/password")
def change_pw(body: PwChange, user: User = Depends(current_user), db: Session = Depends(get_db)):
    cfg = load_config(db)
    if not check_pw(body.old, user.password_hash):
        raise HTTPException(400, "Password lama salah")
    if len(body.new) < cfg.p("auth.min_password", 10):
        raise HTTPException(400, f"Password minimal {cfg.p('auth.min_password', 10)} karakter")
    user.password_hash, user.must_change_pw = hash_pw(body.new), False
    audit(db, user.username, "Mengganti password")
    db.commit()
    return {"ok": True}
