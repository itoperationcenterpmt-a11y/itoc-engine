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
from ..models import MASTER, Parameter, User, Role, Layout, LayoutProfile
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
        raise HTTPException(404, "Unknown table")
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
        raise HTTPException(422, f"Value of {col.key} is not valid")
    return v


ICONS = ["dashboard", "ticket", "activity", "wifi", "cctv", "xdr", "camera", "server", "shield", "users", "handover", "database", "sliders", "report", "calendar"]
FILTERS = [("p", "Period"), ("s", "Shift"), ("l", "Location"), ("c", "Compare with previous period"), ("k", "Category / type buttons"), ("t", "Status buttons"), ("g", "Group list"), ("y", "Type list")]
SECTIONS_ = [("servicedesk", "Ticketing"), ("noc", "Networking (PRTG)"), ("soc", "NDR (Palo Alto)"), ("xdr", "XDR (Trend Micro)"), ("devices", "Devices"), ("wifi", "WiFi (Ruckus)")]


def _distinct(db, col):
    return [v for (v,) in db.execute(select(col).where(col.isnot(None), col != "").distinct().order_by(col)) if v]


def _choices(key: str, db: Session) -> dict:
    """Pick lists for master-data columns, read live from the data they refer to, so a field never needs to be typed from memory.
    opts = [{v, l}], multi = several values (list), flags = several on/off switches (object), free = suggestions only (any text allowed)."""
    from .. import models as M
    o = lambda vs: [{"v": v, "l": l} for v, l in vs]
    same = lambda vs: o((v, v) for v in vs)
    if key == "widget":
        from .. import report as R
        ids = {"servicedesk": R.SD_IDS, "noc": R.NOC_IDS, "soc": R.SOC_IDS, "xdr": R.XDR_IDS, "devices": R.DEV_IDS, "wifi": R.WIFI_IDS}
        have = {w for (w,) in db.execute(select(M.Widget.key))}
        return {"section": {"opts": o(SECTIONS_)}, "kind": {"opts": o([("bar", "Bars"), ("stack", "Stacked bars"), ("hbar", "Horizontal bars (ranking)"), ("donut", "Donut"), ("line", "Line")])},
                "presets": {"opts": o([("ringkas", "Short"), ("standar", "Standard"), ("lengkap", "Complete")]), "multi": True},
                "key": {"opts": [{"v": i, "l": i, "s": s} for s, l in ids.items() for i in l if i not in have], "sets": "section"}}
    if key == "module":
        return {"parent": {"opts": o((m.key, m.label) for m in db.scalars(select(M.Module).order_by(M.Module.sort))), "empty": "None (top-level menu)"}, "icon": {"opts": same(ICONS), "icons": True},
                "filters": {"opts": o(FILTERS), "flags": True}}
    if key == "person":
        return {"team_code": {"opts": o((t.code, f"{t.code} · {t.label}") for t in db.scalars(select(M.Team).order_by(M.Team.sort))), "empty": "No team"},
                "unit": {"opts": same(sorted({*_distinct(db, M.Person.unit), "ITOC", "EOS", "IT Care"})), "free": True}, "job": {"opts": same(_distinct(db, M.Person.job)), "free": True}}
    if key == "site":
        return {"kind": {"opts": same(sorted({*_distinct(db, M.Site.kind), "branch", "head office", "representative office"})), "free": True}}
    if key == "prtg_sensor":
        return {"device": {"opts": same(_distinct(db, M.PrtgSensor.device)), "free": True}}
    if key == "sla_target":
        return {"name": {"opts": same(_distinct(db, M.Ticket.sla_name)), "free": True}}
    return {}


@router.get("/master/{key}")
def master_list(key: str, db: Session = Depends(get_db)):
    model, label, cols = _meta(key)
    pk = [c.key for c in inspect(model).primary_key]
    rows = db.scalars(select(model)).all()
    return {"key": key, "label": label, "pk": pk, "choices": _choices(key, db),
            "columns": [{"name": c.key, "kind": _kind(c), "default": (c.default.arg if c.default is not None and not callable(c.default.arg) and not isinstance(c.default.arg, (list, dict)) else None), "nullable": c.nullable, "pk": c.primary_key, "auto": c.primary_key and c.autoincrement is True and _kind(c) == "int"} for c in cols],
            "rows": [{c.key: _ser(getattr(r, c.key)) for c in cols} for r in rows]}


def _save(key, data: dict, db: Session, user: User, obj=None):
    model, label, cols = _meta(key)
    new = obj is None
    obj = obj or model()
    old_name = getattr(obj, "name", None) if key == "site" and not new else None
    for c in cols:
        if c.key in data and not (c.primary_key and not new):
            setattr(obj, c.key, _coerce(c, data[c.key]))
    if new:
        db.add(obj)
    try:
        db.flush()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(409, "Conflicting data or invalid reference: " + str(e.orig).split("\n")[0])
    if key == "site" and old_name and obj.name != old_name:
        _site_renamed(db, old_name, obj.name)
    audit(db, user.username, f"{'Menambah' if new else 'Mengubah'} {label}", {"table": key, "data": {k: _ser(v) for k, v in data.items()}})
    db.commit()
    bump_config()
    return {"ok": True}


def _site_renamed(db, old: str, new: str | None):
    """A location that is renamed (or removed) is renamed everywhere a parameter or mapping names it, so nothing keeps pointing at the old name."""
    from ..models import SocFwMap
    for k in ("soc.shared_ndr", "net.shared_isp"):
        p = db.get(Parameter, k)
        if p and isinstance(p.value, list):
            p.value = [[(new if x == old else x) for x in g if not (x == old and new is None)] for g in p.value]
    for m in db.query(SocFwMap).filter(SocFwMap.site == old):
        m.site = new


def _get(key, pkval, db):
    model, _, _ = _meta(key)
    pkcol = inspect(model).primary_key[0]
    obj = db.get(model, _coerce(pkcol, pkval))
    if obj is None:
        raise HTTPException(404, "Row not found")
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
    if key == "site":
        _site_renamed(db, obj.name, None)
    db.delete(obj)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Still used by other data; deactivate it instead")
    audit(db, user.username, f"Menghapus {MASTER[key][1]} {pk}", {"table": key})
    db.commit()
    bump_config()
    return {"ok": True}


# ---------------- parameter ----------------
@router.get("/options")
def options(db: Session = Depends(get_db)):
    """Live pick lists for parameters: values that already exist in the data, so a parameter is chosen, not typed."""
    from .. import models as M
    d = lambda col: [v for (v,) in db.execute(select(col).where(col.isnot(None), col != "").distinct().order_by(col)) if v]
    return {"sites": [s.name for s in db.scalars(select(M.Site).where(M.Site.active.is_(True)).order_by(M.Site.sort, M.Site.name))],
            "roles": [r.key for r in db.scalars(select(Role).order_by(Role.key))], "users": [u.username for u in db.scalars(select(User).order_by(User.username))],
            "ticket_status": d(M.Ticket.status), "ticket_priority": d(M.Ticket.priority), "wifi_auth": d(M.WifiSession.auth), "units": sorted({*d(M.Person.unit), "ITOC", "EOS", "IT Care"}),
            "sd_fields": ["mode", "requester", "site", "category", "subcategory", "technician", "sla_name", "impact", "priority", "urgency"], "dev_kinds": d(M.ZbxHost.kind)}


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
    profile: str = "default"
    role: str = ""
    blocks: list[LayoutBlock]


@router.post("/clear-demo")
def clear_demo(db: Session = Depends(get_db), user: User = Depends(require_admin)):
    """Hapus data demo saja (lihat demo.clear). Hanya Super Admin."""
    from .. import demo
    r = demo.clear(db)
    audit(db, user.username, "Deleting demo data: " + ", ".join(f"{k}={v}" for k, v in r.items()))
    db.commit()
    bump_config()
    bump_data()
    return r


@router.put("/layout")
def layout_set(body: LayoutIn, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    """Simpan tata letak satu halaman untuk satu role (role kosong = semua role). Menggantikan pengaturan lama halaman+role itu."""
    if body.role and not db.get(Role, body.role):
        raise HTTPException(404, "Unknown role")
    if not db.get(LayoutProfile, body.profile):
        raise HTTPException(404, "Unknown profile")
    db.query(Layout).filter_by(profile=body.profile, page=body.page, role=body.role).delete()
    seen, rows = set(), []
    for b in body.blocks:
        if b.key in seen or b.size not in ("", "c3", "c4", "c6", "c8", "c12"):
            continue
        seen.add(b.key)
        r = {"profile": body.profile, "page": body.page, "role": body.role, "key": b.key[:80], "title": b.title.strip()[:120], "size": b.size, "enabled": b.enabled, "sort": len(seen)}
        rows.append(r)
        db.add(Layout(**r))
    audit(db, user.username, f"Edited layout {body.page} in profile {body.profile}" + (f" for role {body.role}" if body.role else " (all roles)"))
    db.commit()
    bump_config()
    return {"ok": True, "n": len(seen), "rows": rows}


@router.delete("/layout/{page}")
def layout_reset(page: str, role: str = "", profile: str = "default", db: Session = Depends(get_db), user: User = Depends(require_admin)):
    db.query(Layout).filter_by(profile=profile, page=page, role=role).delete()
    audit(db, user.username, f"Reset layout {page} in profile {profile}" + (f" for role {role}" if role else " (all roles)"))
    db.commit()
    bump_config()
    return {"ok": True}


@router.put("/params/{key}")
def param_set(key: str, body: ParamIn, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    p = db.get(Parameter, key)
    if not p:
        raise HTTPException(404, "Unknown parameter")
    v, ui = body.value, p.ui or {}
    if p.editor in ("number", "percent"):
        try:
            v = float(v)
        except (TypeError, ValueError):
            raise HTTPException(422, "Must be a number")
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
        raise HTTPException(422, "Username needs at least 3 characters (lowercase letters, digits, dots) and a name is required.")
    if db.query(User).filter_by(username=u).first():
        raise HTTPException(409, "Username is already taken.")
    if not db.get(Role, body.role_key):
        raise HTTPException(422, "Unknown role")
    pw = random_pw()
    db.add(User(username=u, full_name=body.full_name.strip(), role_key=body.role_key, site=body.site or None, password_hash=hash_pw(pw), must_change_pw=True))
    audit(db, user.username, "Adding account " + u)
    db.commit()
    return {"ok": True, "initial_password": pw}


@router.patch("/users/{username}")
def user_patch(username: str, body: UserPatch, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    u = db.query(User).filter_by(username=username).one_or_none()
    if not u:
        raise HTTPException(404, "Account not found")
    if u.username == user.username and body.active is False:
        raise HTTPException(400, "You cannot deactivate your own account")
    out = {"ok": True}
    if body.active is not None:
        u.active = body.active
        audit(db, user.username, ("Mengaktifkan" if body.active else "Menonaktifkan") + " account " + u.username)
    if body.full_name is not None:
        if not body.full_name.strip():
            raise HTTPException(422, "Name is required.")
        u.full_name = body.full_name.strip()
        audit(db, user.username, f"Mengubah nama akun {u.username}")
    if body.role_key and body.role_key != u.role_key:
        if u.username == user.username:
            raise HTTPException(400, "You cannot change your own role")
        if not db.get(Role, body.role_key):
            raise HTTPException(422, "Unknown role")
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
        like = "%" + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
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
        wr.writerow(["Time (WIB)", "User", "Aktivitas", "IP", "Detail"])
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

    add("zbx_loc", "Zabbix location codes not mapped to a location", db.scalars(select(ZbxLocMap.code).where(ZbxLocMap.site.is_(None)).order_by(ZbxLocMap.code)).all(),
        "Devices with these codes are not counted per location. Choose their location in Mapping.", ["pemetaan", "zbx_loc"])
    add("dev_code", "Device codes without a label", db.scalars(select(DevCode.code).where((DevCode.label.is_(None)) | (DevCode.label == "")).order_by(DevCode.code)).all(),
        "The label is used as the category name on the Devices page.", ["pemetaan", "dev_code"])
    add("prtg_cap", "Active PRTG sensors without capacity", db.execute(select(PrtgSensor.device, PrtgSensor.name).where(PrtgSensor.active.is_(True), PrtgSensor.capacity_mbps.is_(None)).order_by(PrtgSensor.device)).all(),
        "Without capacity, link utilization percentage cannot be calculated.", ["pemetaan", "prtg_sensor"], lambda r: f"{r[0]} / {r[1]}")
    add("site_geo", "Active locations without coordinates", db.scalars(select(Site.name).where(Site.active.is_(True), (Site.lat.is_(None)) | (Site.lon.is_(None))).order_by(Site.name)).all(),
        "Locations without coordinates do not appear on the Devices map. Fill in lat and lon.", ["pemetaan", "site"])
    known = set()
    for s in db.scalars(select(Site)):
        known.add(s.name.strip().lower())
        known.update(a.strip().lower() for a in (s.aliases or []))
    since = cfg.now() - timedelta(days=90)
    unk = [(n, c) for n, c in db.execute(select(Ticket.site, func.count()).where(Ticket.created_at >= since, Ticket.site != "").group_by(Ticket.site).order_by(func.count().desc())).all() if n.strip().lower() not in known]
    add("ticket_site", "Unknown locations in tickets (last 90 days)", unk, "Add them as a location or location alias so the tickets are counted per location.", ["pemetaan", "site"], lambda r: f"{r[0]} ({r[1]} tiket)")
    stale = []
    for s in db.scalars(select(DataSource).where(DataSource.enabled.is_(True), DataSource.mode == "api")):
        age = (cfg.now() - s.last_ok_at).total_seconds() / 60 if s.last_ok_at else None
        sched = bool((s.config or {}).get("schedule"))
        if s.last_error or age is None or age > (13 * 60 if sched else s.interval_min * 3 + 5):
            stale.append(s.label)
    add("source", "Active data sources that failed or are stale", stale, "Check the error message in Source Status.", ["status", ""])
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


# ---------------- dashboard profiles ----------------
class ProfileNew(BaseModel):
    name: str
    description: str = ""
    clone_from: str = "default"


class ProfileEdit(BaseModel):
    name: str
    description: str = ""


def _pkey(name: str, db: Session) -> str:
    import re
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:30] or "profile"
    key, n = base, 2
    while db.get(LayoutProfile, key):
        key, n = f"{base}-{n}", n + 1
    return key


@router.post("/profiles")
def profile_create(body: ProfileNew, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    """New dashboard profile, copied from an existing one (all pages)."""
    if not body.name.strip():
        raise HTTPException(422, "A profile name is required")
    if not db.get(LayoutProfile, body.clone_from):
        raise HTTPException(404, "The profile to copy from does not exist")
    key = _pkey(body.name, db)
    db.add(LayoutProfile(key=key, name=body.name.strip()[:80], description=body.description.strip()[:200] or None, builtin=False, sort=(db.query(LayoutProfile).count() + 1) * 10))
    db.flush()
    for r in db.query(Layout).filter_by(profile=body.clone_from).all():
        db.add(Layout(profile=key, page=r.page, role=r.role, key=r.key, title=r.title, size=r.size, enabled=r.enabled, sort=r.sort))
    audit(db, user.username, f"Created dashboard profile {body.name.strip()} (copied from {body.clone_from})")
    db.commit()
    bump_config()
    return {"ok": True, "key": key}


@router.put("/profiles/{key}")
def profile_edit(key: str, body: ProfileEdit, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    p = db.get(LayoutProfile, key)
    if not p:
        raise HTTPException(404, "Unknown profile")
    if not body.name.strip():
        raise HTTPException(422, "A profile name is required")
    p.name, p.description = body.name.strip()[:80], body.description.strip()[:200] or None
    audit(db, user.username, f"Renamed dashboard profile {key} to {p.name}")
    db.commit()
    bump_config()
    return {"ok": True}


@router.delete("/profiles/{key}")
def profile_delete(key: str, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    p = db.get(LayoutProfile, key)
    if not p:
        raise HTTPException(404, "Unknown profile")
    if key == "default" or p.builtin:
        raise HTTPException(409, "Built-in profiles cannot be deleted; you can edit them instead")
    db.query(Layout).filter_by(profile=key).delete()
    db.query(User).filter_by(profile=key).update({"profile": "default"})
    db.delete(p)
    audit(db, user.username, f"Deleted dashboard profile {p.name}")
    db.commit()
    bump_config()
    return {"ok": True}


# ---------------- firewall locations (NDR per location) ----------------
class FwMapIn(BaseModel):
    fw: str
    site: str = ""          # empty = back to the automatic name match; "-" = no location


@router.put("/fw-map")
def fw_map(body: FwMapIn, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    from ..models import SocFwMap, Site
    fw, site = body.fw.strip()[:120], body.site.strip()
    if not fw:
        raise HTTPException(422, "A firewall name is required")
    if site not in ("", "-") and not db.query(Site).filter_by(name=site).first():
        raise HTTPException(422, "Unknown location")
    db.query(SocFwMap).filter_by(fw=fw).delete()
    if site:
        db.add(SocFwMap(fw=fw, site=None if site == "-" else site))
    audit(db, user.username, f"Firewall {fw} location set to {site or 'automatic'}")
    db.commit()
    bump_data()
    return {"ok": True}
