from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User, Handover, MASTER
from ..security import current_user, can_see, require_write, effective_site
from ..store import load_config, audit, bump_data
from .. import views

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/public")
def public(db: Session = Depends(get_db)):
    """Tanpa login: hanya teks tampilan halaman login (nama, footer, kalimat, poin, keterangan lokasi). Nilainya dari parameter ui.* (Admin → Parameter)."""
    c = load_config(db)
    return {"brand": c.p("ui.brand_name", ""), "brand_split": c.p("ui.brand_split", 2), "footer": c.p("ui.footer", ""), "tagline": c.p("ui.login_tagline", ""), "points": c.p("ui.login_points", []), "place": c.p("ui.login_place", ""), "eyebrow": c.p("ui.login_eyebrow", "")}


PARAM_MODULE = (("soc.", "soc"), ("net.", "noc"), ("sd.", "servicedesk"))


def _hidden_param(user, key: str) -> bool:
    """Parameter modul (mis. rentang IP internal SOC) hanya dikirim ke role yang boleh membuka modul itu."""
    return any(key.startswith(p) and not can_see(user, m) for p, m in PARAM_MODULE)


@router.get("/config")
def config(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Semua yang dulu tertanam di app.js: menu, filter, preset, shift, rotasi, lokasi, personel, parameter, rumus."""
    c = load_config(db)
    P = c.params
    return {
        "me": {"username": user.username, "name": user.full_name, "role": user.role_key, "site": effective_site(user, db), "is_admin": user.role.is_admin, "admin_view": user.role.admin_view,
               "can_write": user.role.can_write, "must_change_pw": user.must_change_pw,
               "uploads": ["*"] if user.role.is_admin else (user.role.uploads or [])},
        "modules": [m for m in c.modules if can_see(user, m["key"])],
        "roles": c.roles if (user.role.is_admin or user.role.admin_view) else {user.role_key: c.roles.get(user.role_key)},
        "shifts": c.shifts, "teams": c.teams, "rotation": P.get("rotation"), "sites": c.sites, "people": c.people,
        "layouts": c.layouts,
        "formulas": c.formulas, "sla": c.sla, "isps": c.isps,
        "par": {"slaH": c.sla, "target": P["net.target"], "minCov": P["net.min_cov"], "utilPeak": P["net.util_peak"], "utilAvg": P["net.util_avg"]},
        "params": {k: v for k, v in P.items() if user.role.is_admin or user.role.admin_view or not _hidden_param(user, k)},  # tanpa rahasia; parameter modul yang tidak boleh dilihat role ini ikut disembunyikan
        "master": [{"key": k, "label": v[1]} for k, v in MASTER.items()] if (user.role.is_admin or user.role.admin_view) else [],
    }


@router.get("/view/{tab}")
def view(tab: str, d_from: date = Query(alias="from"), d_to: date = Query(alias="to"), shift: int = 0, site: str = "", cmp: bool = False,
         sensor: str = "", preset: str = "standar", kind: str = "", dstat: str = "", grp: str = "", user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not can_see(user, tab):
        raise HTTPException(403, "Tidak punya akses ke halaman ini")
    c = load_config(db)
    if d_from > d_to:
        d_from, d_to = d_to, d_from
    max_days = c.p("ui.max_range_days", 400)
    if (d_to - d_from).days > max_days:
        raise HTTPException(400, f"Rentang maksimal {max_days} hari")
    site = effective_site(user, db) or site  # IT Care (kantor pusat) dan EOS (lokasi sendiri) dikunci ke lokasinya
    flt = views.Filt(d_from, d_to, shift, site, cmp, sensor, kind, dstat, grp)
    flt.preset = preset
    return views.bundle(db, c, tab, flt, user)


class HoIn(BaseModel):
    category: str
    priority: str
    site: str
    ticket_id: str | None = None
    title: str
    body: str
    next_action: str | None = None


class HoClose(BaseModel):
    note: str


@router.post("/handover")
def ho_create(body: HoIn, user: User = Depends(require_write), db: Session = Depends(get_db)):
    c = load_config(db)
    H = c.p("ho.rules")
    errs = []
    if body.category not in c.p("ho.categories"): errs.append("kategori")
    if body.priority not in [p["value"] for p in c.p("ho.priorities")]: errs.append("prioritas")
    if body.site not in c.sites: errs.append("lokasi")
    if len(body.title.strip()) < H["min_title"]: errs.append(f"judul (min. {H['min_title']} karakter)")
    if len(body.body.strip()) < H["min_body"]: errs.append(f"kondisi (min. {H['min_body']} karakter)")
    if errs:
        raise HTTPException(422, "Lengkapi: " + ", ".join(errs) + ".")
    now = c.now()
    h = Handover(created_at=now, shift_date=c.clock.duty_date(now), shift_no=c.clock.shift_of(now.hour), category=body.category, priority=body.priority,
                 site=body.site, ticket_id=body.ticket_id or None, title=body.title.strip(), body=body.body.strip(), next_action=(body.next_action or "").strip(),
                 created_by=user.full_name, is_open=True)
    db.add(h)
    audit(db, user.username, "Membuat serah terima: " + h.title, tz=c.p("tz_offset_hours"))
    db.commit()
    bump_data()
    from .. import notify
    tone = next((p.get("tone") for p in c.p("ho.priorities") if p["value"] == h.priority), "")
    txt = f"Handover {h.priority}: {h.title}" + (f" ({h.site})" if h.site else "") + f" · oleh {h.created_by}"
    notify.fire("handover_new", txt)
    if tone == "crit":
        notify.fire("handover_high", txt)
    return views.ho_json(h)


@router.post("/handover/{hid}/close")
def ho_close(hid: int, body: HoClose, user: User = Depends(require_write), db: Session = Depends(get_db)):
    c = load_config(db)
    h = db.get(Handover, hid)
    if not h or not h.is_open:
        raise HTTPException(404, "Serah terima tidak ditemukan atau sudah ditutup")
    if len(body.note.strip()) < c.p("ho.rules")["min_close"]:
        raise HTTPException(422, f"Isi catatan penutupan minimal {c.p('ho.rules')['min_close']} karakter.")
    h.is_open, h.closed_by, h.closed_at, h.close_note = False, user.full_name, c.now(), body.note.strip()
    audit(db, user.username, "Menutup serah terima: " + h.title, tz=c.p("tz_offset_hours"))
    db.commit()
    bump_data()
    from .. import notify
    tone = next((p.get("tone") for p in c.p("ho.priorities") if p["value"] == h.priority), "")
    txt = f"Handover {h.priority}: {h.title}" + (f" ({h.site})" if h.site else "") + f" · oleh {h.created_by}"
    notify.fire("handover_new", txt)
    if tone == "crit":
        notify.fire("handover_high", txt)
    return views.ho_json(h)
