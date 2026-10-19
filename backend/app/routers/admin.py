"""Admin: CRUD generik untuk semua tabel master, parameter, pengguna, audit. Setiap perubahan tercatat di audit_log
dan langsung membatalkan cache konfigurasi sehingga semua halaman dihitung ulang."""
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import inspect, select, String, Integer, SmallInteger, Float, Boolean, BigInteger, Text, Date, DateTime
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import MASTER, Parameter, User, Role, Layout
from ..security import require_admin, require_admin_area, hash_pw, random_pw
from ..store import load_config, audit, bump_config, bump_data

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin_area)])
HIDDEN = {"data_source": {"cursor", "last_ok_at", "last_error"}}


def _kind(col) -> str:
    t = col.type
    if isinstance(t, (JSONB, ARRAY)): return "json"
    if isinstance(t, Boolean): return "bool"
    if isinstance(t, (Integer, SmallInteger, BigInteger)): return "int"
    if isinstance(t, Float): return "float"
    if isinstance(t, Date): return "date"
    if isinstance(t, DateTime): return "datetime"
    if isinstance(t, Text): return "text"
    return "str"


def _meta(key):
    if key not in MASTER:
        raise HTTPException(404, "Tabel tidak dikenal")
    model, label = MASTER[key]
    cols = [c for c in inspect(model).columns if c.key not in HIDDEN.get(key, set())]
    return model, label, cols


def _ser(v):
    return v.isoformat() if isinstance(v, (date, datetime)) else v


def _coerce(col, v):
    if v is None or v == "":
        return None if col.nullable else v
    k = _kind(col)
    try:
        if k == "int": return int(v)
        if k == "float": return float(v)
        if k == "bool": return v if isinstance(v, bool) else str(v).lower() in ("1", "true", "ya", "on")
        if k == "date": return date.fromisoformat(v)
    except (TypeError, ValueError):
        raise HTTPException(422, f"Nilai {col.key} tidak valid")
    return v


@router.get("/master/{key}")
def master_list(key: str, db: Session = Depends(get_db)):
    model, label, cols = _meta(key)
    pk = [c.key for c in inspect(model).primary_key]
    rows = db.scalars(select(model)).all()
    return {"key": key, "label": label, "pk": pk,
            "columns": [{"name": c.key, "kind": _kind(c), "nullable": c.nullable, "pk": c.primary_key, "auto": c.primary_key and c.autoincrement is True and _kind(c) == "int"} for c in cols],
            "rows": [{c.key: _ser(getattr(r, c.key)) for c in cols} for r in rows]}


def _save(key, data: dict, db: Session, user: User, obj=None):
    model, label, cols = _meta(key)
    new = obj is None
    obj = obj or model()
    for c in cols:
        if c.key in data and not (c.primary_key and not new):
            setattr(obj, c.key, _coerce(c, data[c.key]))
    if new:
        db.add(obj)
    try:
        db.flush()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(409, "Data bentrok atau referensi tidak valid: " + str(e.orig).split("\n")[0])
    audit(db, user.username, f"{'Menambah' if new else 'Mengubah'} {label}", {"table": key, "data": {k: _ser(v) for k, v in data.items()}})
    db.commit()
    bump_config()
    return {"ok": True}


def _get(key, pkval, db):
    model, _, _ = _meta(key)
    pkcol = inspect(model).primary_key[0]
    obj = db.get(model, _coerce(pkcol, pkval))
    if obj is None:
        raise HTTPException(404, "Baris tidak ditemukan")
    return obj


@router.post("/master/{key}")
def master_create(key: str, data: dict, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    return _save(key, data, db, user)


@router.put("/master/{key}/{pk}")
def master_update(key: str, pk: str, data: dict, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    return _save(key, data, db, user, _get(key, pk, db))


@router.delete("/master/{key}/{pk}")
def master_delete(key: str, pk: str, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    obj = _get(key, pk, db)
    db.delete(obj)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Masih dipakai data lain; nonaktifkan saja")
    audit(db, user.username, f"Menghapus {MASTER[key][1]} {pk}", {"table": key})
    db.commit()
    bump_config()
    return {"ok": True}


# ---------------- parameter ----------------
@router.get("/params")
def params(db: Session = Depends(get_db)):
    return [{"key": p.key, "label": p.label, "group": p.group, "editor": p.editor, "ui": p.ui, "description": p.description, "value": p.value,
             "updated_by": p.updated_by} for p in db.scalars(select(Parameter).order_by(Parameter.group, Parameter.sort, Parameter.key))]


class ParamIn(BaseModel):
    value: object


class LayoutBlock(BaseModel):
    key: str
    title: str = ""
    size: str = ""
    enabled: bool = True


class LayoutIn(BaseModel):
    page: str
    role: str = ""
    blocks: list[LayoutBlock]


@router.post("/clear-demo")
def clear_demo(db: Session = Depends(get_db), user: User = Depends(require_admin)):
    """Hapus data demo saja (lihat demo.clear). Hanya Super Admin."""
    from .. import demo
    r = demo.clear(db)
    audit(db, user.username, "Menghapus data demo: " + ", ".join(f"{k}={v}" for k, v in r.items()))
    db.commit()
    bump_config()
    bump_data()
    return r


@router.put("/layout")
def layout_set(body: LayoutIn, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    """Simpan tata letak satu halaman untuk satu role (role kosong = semua role). Menggantikan pengaturan lama halaman+role itu."""
    if body.role and not db.get(Role, body.role):
        raise HTTPException(404, "Role tidak dikenal")
    db.query(Layout).filter_by(page=body.page, role=body.role).delete()
    seen = set()
    for b in body.blocks:
        if b.key in seen or b.size not in ("", "c3", "c4", "c6", "c8", "c12"):
            continue
        seen.add(b.key)
        db.add(Layout(page=body.page, role=body.role, key=b.key[:80], title=b.title.strip()[:120], size=b.size, enabled=b.enabled, sort=len(seen)))
    audit(db, user.username, f"Mengatur tata letak {body.page}" + (f" untuk role {body.role}" if body.role else " (semua role)"))
    db.commit()
    bump_config()
    return {"ok": True, "n": len(seen)}


@router.delete("/layout/{page}")
def layout_reset(page: str, role: str = "", db: Session = Depends(get_db), user: User = Depends(require_admin)):
    db.query(Layout).filter_by(page=page, role=role).delete()
    audit(db, user.username, f"Mengembalikan tata letak {page} ke bawaan" + (f" untuk role {role}" if role else " (semua role)"))
    db.commit()
    bump_config()
    return {"ok": True}


@router.put("/params/{key}")
def param_set(key: str, body: ParamIn, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    p = db.get(Parameter, key)
    if not p:
        raise HTTPException(404, "Parameter tidak dikenal")
    v, ui = body.value, p.ui or {}
    if p.editor in ("number", "percent"):
        try:
            v = float(v)
        except (TypeError, ValueError):
            raise HTTPException(422, "Harus angka")
        if ("min" in ui and v < ui["min"]) or ("max" in ui and v > ui["max"]):
            raise HTTPException(422, f"Di luar batas {ui.get('min')}–{ui.get('max')}")
    old = p.value
    p.value, p.updated_by = v, user.username
    audit(db, user.username, f"Mengubah parameter {p.label}", {"key": key, "old": old, "new": v})
    db.commit()
    bump_config()
    return {"ok": True}


# ---------------- pengguna ----------------
class UserIn(BaseModel):
    username: str
    full_name: str
    role_key: str
    site: str | None = None


class UserPatch(BaseModel):
    full_name: str | None = None
    active: bool | None = None
    role_key: str | None = None
    site: str | None = None
    reset_password: bool = False


@router.post("/users")
def user_create(body: UserIn, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    import re
    u = body.username.strip().lower()
    if not re.fullmatch(r"[a-z0-9._-]{3,}", u) or not body.full_name.strip():
        raise HTTPException(422, "Username min. 3 karakter (huruf kecil, angka, titik) dan nama wajib diisi.")
    if db.query(User).filter_by(username=u).first():
        raise HTTPException(409, "Username sudah dipakai.")
    if not db.get(Role, body.role_key):
        raise HTTPException(422, "Role tidak dikenal")
    pw = random_pw()
    db.add(User(username=u, full_name=body.full_name.strip(), role_key=body.role_key, site=body.site or None, password_hash=hash_pw(pw), must_change_pw=True))
    audit(db, user.username, "Menambah akun " + u)
    db.commit()
    return {"ok": True, "initial_password": pw}


@router.patch("/users/{username}")
def user_patch(username: str, body: UserPatch, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    u = db.query(User).filter_by(username=username).one_or_none()
    if not u:
        raise HTTPException(404, "Akun tidak ditemukan")
    if u.username == user.username and body.active is False:
        raise HTTPException(400, "Tidak bisa menonaktifkan akun sendiri")
    out = {"ok": True}
    if body.active is not None:
        u.active = body.active
        audit(db, user.username, ("Mengaktifkan" if body.active else "Menonaktifkan") + " akun " + u.username)
    if body.full_name is not None:
        if not body.full_name.strip():
            raise HTTPException(422, "Nama wajib diisi.")
        u.full_name = body.full_name.strip()
        audit(db, user.username, f"Mengubah nama akun {u.username}")
    if body.role_key and body.role_key != u.role_key:
        if u.username == user.username:
            raise HTTPException(400, "Tidak bisa mengubah role akun sendiri")
        if not db.get(Role, body.role_key):
            raise HTTPException(422, "Role tidak dikenal")
        u.role_key = body.role_key
        audit(db, user.username, f"Mengubah role {u.username} menjadi {body.role_key}")
    if body.site is not None:
        u.site = body.site or None
    if body.reset_password:
        pw = random_pw()
        u.password_hash, u.must_change_pw = hash_pw(pw), True
        out["initial_password"] = pw
        audit(db, user.username, "Reset password " + u.username)
    db.commit()
    return out
