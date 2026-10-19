from datetime import datetime, timedelta, timezone
import secrets
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


def make_token(user: User) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings().jwt_minutes)
    return jwt.encode({"sub": user.username, "role": user.role_key, "exp": exp}, settings().jwt_secret, algorithm="HS256")


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
        raise HTTPException(401, "API key tidak valid atau sudah dicabut")
    if request.method != "GET":
        raise HTTPException(403, "API key hanya boleh membaca (GET)")
    role = db.get(Role, k.role_key)
    if not role or role.is_admin:
        raise HTTPException(403, "Role API key tidak valid")
    if not k.last_used_at or (now - k.last_used_at).total_seconds() > 60:
        k.last_used_at = now
        db.commit()
    return ApiUser(k, role)


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    raw = request.headers.get("X-API-Key", "")
    if raw:
        return _api_key_user(request, db, raw)
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Belum login")
    try:
        data = jwt.decode(auth[7:], settings().jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Sesi berakhir, silakan login ulang")
    u = db.query(User).filter_by(username=data["sub"]).one_or_none()
    if not u or not u.active:
        raise HTTPException(401, "Akun tidak aktif")
    return u


def effective_site(user: User, db: Session) -> str:
    """Lokasi yang dikunci untuk user ("" = semua lokasi). Role scope: own = lokasi di akun (wajib diisi), ho = kantor pusat, all = bebas
    (kecuali akun diberi lokasi)."""
    from .models import Site
    sc = user.role.scope or "all"
    if sc == "own":
        if not user.site:
            raise HTTPException(403, "Akun ini belum diberi lokasi kerja. Hubungi admin.")
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
            raise HTTPException(403, f"Role {user.role.label} tidak punya akses ke {module}")
        return user
    return dep


def require_admin_area(request: Request, user: User = Depends(current_user)) -> User:
    """Area /api/admin: admin penuh boleh semuanya; role dengan admin_view hanya boleh membaca (GET)."""
    if getattr(user, "is_api", False):
        raise HTTPException(403, "API key tidak boleh mengakses area admin")
    if user.role.is_admin or (request.method == "GET" and user.role.admin_view):
        return user
    raise HTTPException(403, "Hanya admin")


def require_admin(user: User = Depends(current_user)) -> User:
    if not user.role.is_admin:
        raise HTTPException(403, "Hanya admin")
    return user


def require_upload(source: str):
    """Hak unggah RAW per sumber (soc | tickets | prtg) menurut kolom role.uploads; admin boleh semua."""
    def dep(user: User = Depends(current_user)) -> User:
        up = user.role.uploads or []
        if not (user.role.is_admin or "*" in up or source in up):
            raise HTTPException(403, f"Role {user.role.label} tidak punya izin mengunggah data ini")
        return user
    return dep


def require_write(user: User = Depends(current_user)) -> User:
    if not user.role.can_write:
        raise HTTPException(403, "Role ini hanya bisa melihat")
    return user
