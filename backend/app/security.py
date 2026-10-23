from datetime import datetime, timedelta, timezone
import hashlib
import secrets
import threading
import time
import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from .config import settings
from .db import get_db
from .models import User


def hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def check_pw(pw: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), h.encode())
    except ValueError:
        return False


def random_pw() -> str:
    return secrets.token_urlsafe(9)


COOKIE = "itoc_session"
SAFE_METHODS = ("GET", "HEAD", "OPTIONS")


def _pv(user: User) -> str:
    """Sidik jari password: token lama otomatis tidak berlaku setelah password diganti atau direset."""
    return hashlib.sha256(user.password_hash.encode()).hexdigest()[:16]


def make_token(user: User) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings().jwt_minutes)
    return jwt.encode({"sub": user.username, "role": user.role_key, "pv": _pv(user), "exp": exp}, settings().jwt_secret, algorithm="HS256")


def is_https(request: Request) -> bool:
    return request.url.scheme == "https" or request.headers.get("x-forwarded-proto", "").lower() == "https"


def set_session(response, request: Request, token: str) -> None:
    """Sesi browser = cookie HttpOnly + SameSite=Strict (tidak bisa dibaca JavaScript); Secure otomatis bila diakses lewat HTTPS."""
    response.set_cookie(COOKIE, token, max_age=settings().jwt_minutes * 60, httponly=True, samesite="strict", secure=is_https(request), path="/")


_RATE: dict[str, list[float]] = {}
_RATE_LOCK = threading.Lock()


def rate_limit(name: str, n: int, secs: int):
    """Dependensi pembatas laju per pengguna (atau alamat bila belum login), per proses. Dipakai untuk aksi sensitif."""
    def dep(request: Request) -> None:
        who = request.headers.get("X-API-Key", "")[:12] or request.cookies.get(COOKIE, "")[-16:] or (request.client.host if request.client else "?")
        key, now = f"{name}:{who}", time.time()
        with _RATE_LOCK:
            hits = [t for t in _RATE.get(key, []) if now - t < secs]
            if len(hits) >= n:
                _RATE[key] = hits
                raise HTTPException(429, "Terlalu sering. Coba lagi sebentar lagi.")
            hits.append(now)
            _RATE[key] = hits
            if len(_RATE) > 5000:
                for k in [k for k, v in _RATE.items() if not v or now - v[-1] > secs]:
                    _RATE.pop(k, None)
    return dep


class ApiUser:
    """Pemanggil dengan API key: berperan sebagai role pada kunci, hanya membaca (GET), tanpa akses /api/admin."""
    is_api = True
    must_change_pw = False
    active = True

    def __init__(self, key, role):
        self.username, self.full_name, self.role_key, self.role, self.site = "key:" + key.name, "API key " + key.name, key.role_key, role, key.site


def _api_key_user(request: Request, db: Session, raw: str):
    import hashlib
    from .models import ApiKey, Role
    k = db.query(ApiKey).filter_by(key_hash=hashlib.sha256(raw.encode()).hexdigest()).one_or_none()
    now = datetime.now()
    if not k or k.revoked_at or (k.expires_at and k.expires_at < now):
        raise HTTPException(401, "API key is invalid or has been revoked")
    if request.method != "GET":
        raise HTTPException(403, "API keys are read-only (GET)")
    role = db.get(Role, k.role_key)
    if not role or role.is_admin:
        raise HTTPException(403, "The API key role is invalid")
    if not k.last_used_at or (now - k.last_used_at).total_seconds() > 60:
        k.last_used_at = now
        db.commit()
    return ApiUser(k, role)


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    raw = request.headers.get("X-API-Key", "")
    if raw:
        return _api_key_user(request, db, raw)
    auth = request.headers.get("Authorization", "")
    via_cookie = not auth.startswith("Bearer ")
    token = request.cookies.get(COOKIE, "") if via_cookie else auth[7:]
    if not token:
        raise HTTPException(401, "Not signed in")
    if via_cookie and request.method not in SAFE_METHODS and request.headers.get("X-Requested-With") != "itoc":
        raise HTTPException(403, "Request rejected (security header missing)")      # perlindungan CSRF untuk sesi berbasis cookie
    try:
        data = jwt.decode(token, settings().jwt_secret, algorithms=["HS256"], options={"require": ["exp", "sub"]})
    except jwt.PyJWTError:
        raise HTTPException(401, "Session expired, please sign in again")
    u = db.query(User).filter_by(username=data["sub"]).one_or_none()
    if not u or not u.active or not secrets.compare_digest(str(data.get("pv", "")), _pv(u)):
        raise HTTPException(401, "Session is not valid, please sign in again")
    return u


def effective_site(user: User, db: Session) -> str:
    """Lokasi yang dikunci untuk user ("" = semua lokasi). Role scope: own = lokasi di akun (wajib diisi), ho = kantor pusat, all = bebas
    (kecuali akun diberi lokasi)."""
    from .models import Site
    sc = user.role.scope or "all"
    if sc == "own":
        if not user.site:
            raise HTTPException(403, "This account has no work location yet. Contact an admin.")
        return user.site
    if sc == "ho":
        if user.site:
            return user.site
        ho = db.query(Site).filter_by(kind="ho", active=True).order_by(Site.sort).first()
        return ho.name if ho else ""
    return user.site or ""


def can_see(user: User, module: str) -> bool:
    mods = user.role.modules or []
    return "*" in mods or module in mods


def require_module(module: str):
    def dep(user: User = Depends(current_user)) -> User:
        if not can_see(user, module):
            raise HTTPException(403, f"Role {user.role.label} has no access to {module}")
        return user
    return dep


# Halaman Admin yang bisa dikunci untuk Super Admin (parameter admin.locked_pages). Awalan path API -> kunci halaman.
ADMIN_PAGE_PATHS = {"integrasi": ("/api/admin/integrations",), "apikeys": ("/api/admin/apikeys",), "smtp": ("/api/admin/smtp",), "webhooks": ("/api/admin/webhooks",), "audit": ("/api/admin/audit",),
                    "pengguna": ("/api/admin/users",), "parameter": ("/api/admin/params",), "status": ("/api/admin/status",), "dilengkapi": ("/api/admin/todo",)}
ADMIN_MASTER_PAGE = {"role": "roles", "module": "menu", "widget": "menu", "data_source": "integrasi", "site": "pemetaan", "zbx_loc": "pemetaan", "dev_code": "pemetaan", "prtg_sensor": "pemetaan", "isp": "pemetaan",
                     "person": "personel", "team": "tim", "shift": "tim", "sla_target": "parameter", "formula": "rumus"}
DEFAULT_LOCKED = ["pengguna", "roles", "apikeys", "integrasi", "smtp", "webhooks", "menu", "audit", "akses"]


def admin_page_of(path: str) -> str | None:
    p = path.rstrip("/")
    for page, prefixes in ADMIN_PAGE_PATHS.items():
        if any(p == x or p.startswith(x + "/") for x in prefixes):
            return page
    if p.startswith("/api/admin/master/"):
        return ADMIN_MASTER_PAGE.get(p.split("/")[4] if len(p.split("/")) > 4 else "")
    return None


def locked_pages(db: Session) -> list[str]:
    from .store import load_config
    v = load_config(db).p("admin.locked_pages", DEFAULT_LOCKED)
    return v if isinstance(v, list) else DEFAULT_LOCKED


def require_admin_area(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)) -> User:
    """Area /api/admin: Super Admin boleh semuanya; role dengan admin_view hanya boleh membaca (GET) halaman yang tidak dikunci untuk Super Admin."""
    if getattr(user, "is_api", False):
        raise HTTPException(403, "API keys cannot access the admin area")
    if user.role.is_admin:
        return user
    if request.method == "GET" and user.role.admin_view:
        page = admin_page_of(request.url.path)
        if page is None or page in locked_pages(db) or page in ("akses",):
            raise HTTPException(403, "This page is restricted to Super Admin")
        return user
    raise HTTPException(403, "Super Admin only")


def require_admin(user: User = Depends(current_user)) -> User:
    if not user.role.is_admin:
        raise HTTPException(403, "Hanya admin")
    return user


def require_upload(source: str):
    """Hak unggah RAW per sumber (soc | tickets | prtg) menurut kolom role.uploads; admin boleh semua."""
    def dep(user: User = Depends(current_user)) -> User:
        up = user.role.uploads or []
        if not (user.role.is_admin or "*" in up or source in up):
            raise HTTPException(403, f"Role {user.role.label} may not upload this data")
        return user
    return dep


def require_write(user: User = Depends(current_user)) -> User:
    if not user.role.can_write:
        raise HTTPException(403, "This role is view-only")
    return user
