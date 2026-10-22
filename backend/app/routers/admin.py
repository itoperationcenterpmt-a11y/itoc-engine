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
    seen, rows = set(), []
    for b in body.blocks:
        if b.key in seen or b.size not in ("", "c3", "c4", "c6", "c8", "c12"):
            continue
        seen.add(b.key)
        r = {"page": body.page, "role": body.role, "key": b.key[:80], "title": b.title.strip()[:120], "size": b.size, "enabled": b.enabled, "sort": len(seen)}
        rows.append(r)
        db.add(Layout(**r))
    audit(db, user.username, f"Mengatur tata letak {body.page}" + (f" untuk role {body.role}" if body.role else " (semua role)"))
    db.commit()
    bump_config()
    return {"ok": True, "n": len(seen), "rows": rows}


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


@router.get("/security-check")
def security_check(db: Session = Depends(get_db)):
    """Temuan konfigurasi keamanan (tanpa rahasia). Bisa dibaca role admin_view; hanya membaca."""
    from ..secaudit import findings
    return {"rows": findings(db)}


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


# ---------------- audit log: daftar bertahap dan ekspor CSV ----------------
AUDIT_MAX_EXPORT = 200000
_SECRET_KEY = ("pass", "token", "secret", "key", "hash", "url")


def _audit_where(frm: date | None, to: date | None, who: str, q: str):
    from datetime import time, timedelta
    from sqlalchemy import or_
    from ..models import AuditLog
    w = []
    if frm:
        w.append(AuditLog.at >= datetime.combine(frm, time.min))
    if to:
        w.append(AuditLog.at < datetime.combine(to + timedelta(days=1), time.min))
    if who:
        w.append(AuditLog.username == who)
    if q.strip():
        like = "%" + q.strip().replace("\\", "\\\\").replace("%", "\%").replace("_", "\_") + "%"
        w.append(or_(AuditLog.action.ilike(like, escape="\\"), AuditLog.username.ilike(like, escape="\\")))
    return w


def _mask(d):
    """Detail audit tidak boleh membawa rahasia: nilai pada kunci yang berbau rahasia disamarkan."""
    if isinstance(d, dict):
        return {k: ("***" if any(s in str(k).lower() for s in _SECRET_KEY) else _mask(v)) for k, v in d.items()}
    if isinstance(d, list):
        return [_mask(x) for x in d]
    return d


@router.get("/audit")
def audit_list(frm: date | None = None, to: date | None = None, who: str = "", q: str = "", limit: int = 100, offset: int = 0, db: Session = Depends(get_db)):
    from sqlalchemy import func
    from ..models import AuditLog
    w = _audit_where(frm, to, who, q)
    total = db.scalar(select(func.count()).select_from(AuditLog).where(*w)) or 0
    rows = db.scalars(select(AuditLog).where(*w).order_by(AuditLog.at.desc(), AuditLog.id.desc()).limit(max(1, min(limit, 500))).offset(max(0, offset)))
    users = [u for (u,) in db.execute(select(AuditLog.username).distinct().order_by(AuditLog.username))]
    return {"total": total, "users": users, "rows": [{"id": r.id, "at": r.at.isoformat(), "by": r.username, "t": r.action, "ip": (r.detail or {}).get("ip") if isinstance(r.detail, dict) else None} for r in rows]}


@router.get("/audit/export")
def audit_export(frm: date | None = None, to: date | None = None, who: str = "", q: str = "", db: Session = Depends(get_db), user: User = Depends(require_admin_area)):
    """CSV UTF-8 (dengan BOM agar Excel membaca dengan benar). Sel yang diawali = + - @ diberi tanda petik supaya tidak dibaca sebagai rumus."""
    import csv
    import io
    import json
    from fastapi.responses import StreamingResponse
    from sqlalchemy import func
    from ..models import AuditLog
    cfg = load_config(db)
    w = _audit_where(frm, to, who, q)
    cell = lambda v: ("'" + v) if isinstance(v, str) and v[:1] in ("=", "+", "-", "@", "\t", "\r") else v
    n = db.scalar(select(func.count()).select_from(AuditLog).where(*w)) or 0
    audit(db, user.username, f"Mengekspor audit log ({min(n, AUDIT_MAX_EXPORT)} baris)", {"from": str(frm or ""), "to": str(to or ""), "user": who, "q": q}, cfg.p("tz_offset_hours", 7))
    db.commit()

    def gen():
        buf = io.StringIO()
        wr = csv.writer(buf)
        wr.writerow(["Waktu (WIB)", "Pengguna", "Aktivitas", "IP", "Detail"])
        yield "﻿" + buf.getvalue()
        for r in db.scalars(select(AuditLog).where(*w).order_by(AuditLog.at.desc(), AuditLog.id.desc()).limit(AUDIT_MAX_EXPORT).execution_options(yield_per=1000)):
            d = _mask(r.detail) if isinstance(r.detail, dict) else r.detail
            buf = io.StringIO()
            csv.writer(buf).writerow([r.at.strftime("%Y-%m-%d %H:%M:%S"), cell(r.username), cell(r.action), (d or {}).get("ip", "") if isinstance(d, dict) else "", cell(json.dumps(d, ensure_ascii=False)) if d else ""])
            yield buf.getvalue()

    name = f"audit-log-{cfg.now():%Y%m%d-%H%M}.csv"
    return StreamingResponse(gen(), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{name}"', "Cache-Control": "no-store"})


# ---------------- Perlu dilengkapi dan status sumber data ----------------
@router.get("/todo")
def admin_todo(db: Session = Depends(get_db)):
    """Data yang masuk otomatis dari API tetapi masih perlu dilengkapi admin (pemetaan lokasi, label, kapasitas, koordinat)."""
    from datetime import timedelta
    from sqlalchemy import func
    from ..models import Site, ZbxLocMap, DevCode, PrtgSensor, Ticket, DataSource
    cfg = load_config(db)
    out = []

    def add(key, title, rows, hint, go, show=lambda x: str(x)):
        if rows:
            out.append({"key": key, "title": title, "count": len(rows), "hint": hint, "go": go, "examples": [show(x) for x in rows[:8]]})

    add("zbx_loc", "Kode lokasi Zabbix belum dipetakan ke lokasi", db.scalars(select(ZbxLocMap.code).where(ZbxLocMap.site.is_(None)).order_by(ZbxLocMap.code)).all(),
        "Perangkat dengan kode ini belum masuk hitungan per lokasi. Pilih lokasinya di Pemetaan.", ["pemetaan", "zbx_loc"])
    add("dev_code", "Kode perangkat belum punya label", db.scalars(select(DevCode.code).where((DevCode.label.is_(None)) | (DevCode.label == "")).order_by(DevCode.code)).all(),
        "Label dipakai sebagai nama kategori di halaman Devices.", ["pemetaan", "dev_code"])
    add("prtg_cap", "Sensor PRTG aktif tanpa kapasitas", db.execute(select(PrtgSensor.device, PrtgSensor.name).where(PrtgSensor.active.is_(True), PrtgSensor.capacity_mbps.is_(None)).order_by(PrtgSensor.device)).all(),
        "Tanpa kapasitas, persentase utilisasi link tidak bisa dihitung.", ["pemetaan", "prtg_sensor"], lambda r: f"{r[0]} / {r[1]}")
    add("site_geo", "Lokasi aktif belum berkoordinat", db.scalars(select(Site.name).where(Site.active.is_(True), (Site.lat.is_(None)) | (Site.lon.is_(None))).order_by(Site.name)).all(),
        "Lokasi tanpa koordinat tidak tampil di peta Devices. Isi lat dan lon.", ["pemetaan", "site"])
    known = set()
    for s in db.scalars(select(Site)):
        known.add(s.name.strip().lower())
        known.update(a.strip().lower() for a in (s.aliases or []))
    since = cfg.now() - timedelta(days=90)
    unk = [(n, c) for n, c in db.execute(select(Ticket.site, func.count()).where(Ticket.created_at >= since, Ticket.site != "").group_by(Ticket.site).order_by(func.count().desc())).all() if n.strip().lower() not in known]
    add("ticket_site", "Lokasi pada tiket tidak dikenal (90 hari terakhir)", unk, "Tambahkan sebagai lokasi atau alias lokasi supaya tiketnya ikut dihitung per lokasi.", ["pemetaan", "site"], lambda r: f"{r[0]} ({r[1]} tiket)")
    stale = []
    for s in db.scalars(select(DataSource).where(DataSource.enabled.is_(True), DataSource.mode == "api")):
        age = (cfg.now() - s.last_ok_at).total_seconds() / 60 if s.last_ok_at else None
        sched = bool((s.config or {}).get("schedule"))
        if s.last_error or age is None or age > (13 * 60 if sched else s.interval_min * 3 + 5):
            stale.append(s.label)
    add("source", "Sumber data aktif yang gagal atau belum segar", stale, "Cek pesan galat di Status Sumber.", ["status", ""])
    return {"items": out, "total": sum(i["count"] for i in out)}


@router.get("/status")
def admin_status(db: Session = Depends(get_db)):
    from ..models import DataSource, SyncLog
    cfg = load_config(db)
    now, rows = cfg.now(), []
    for s in db.scalars(select(DataSource).order_by(DataSource.label)):
        age = int((now - s.last_ok_at).total_seconds() / 60) if s.last_ok_at else None
        sched = bool((s.config or {}).get("schedule"))
        limit = 13 * 60 if sched else (s.interval_min or 60) * 3 + 5
        state = "off" if not s.enabled or s.mode != "api" else "crit" if s.last_error else "warn" if age is None or age > limit else "ok"
        last = db.scalar(select(SyncLog).where(SyncLog.source == s.label).order_by(SyncLog.id.desc()).limit(1))
        rows.append({"key": s.key, "label": s.label, "mode": s.mode, "enabled": s.enabled, "interval": s.interval_min, "schedule": (s.config or {}).get("schedule") or [], "last_ok": s.last_ok_at.isoformat() if s.last_ok_at else None,
                     "age_min": age, "error": s.last_error, "state": state, "last_msg": last.message[:200] if last else "", "last_rows": last.rows if last else 0})
    logs = [{"at": x.at.isoformat(), "source": x.source, "ok": x.ok, "rows": x.rows, "ms": x.ms, "msg": x.message[:160]} for x in db.scalars(select(SyncLog).order_by(SyncLog.id.desc()).limit(30))]
    return {"sources": rows, "log": logs}
