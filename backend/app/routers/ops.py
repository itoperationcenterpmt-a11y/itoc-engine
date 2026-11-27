"""Command Center Operations API:
1. Live Alert Center & Notification Bell (/api/alerts)
2. Global Quick Search (/api/search)
3. SLA Breach Countdown (/api/sla-risk)
4. Major Incident War Room & Timeline (/api/incidents)
5. Scheduled Automated Reports & Auto-Digest (/api/admin/schedules + worker runner)
"""
from datetime import datetime, timedelta
from types import SimpleNamespace
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from .. import mailer, notify, report as REP, report_export as EXP
from ..db import get_db, session_scope
from ..insight import shift_summary
from ..models import (
    DataSource, Handover, IncidentUpdate, Insight, MajorIncident,
    Person, PrtgSensor, ReportSchedule, Role, Site, Ticket, User, ZbxHost,
)
from ..security import can_see, current_user, effective_site, require_admin, require_admin_area, require_write
from ..store import audit, bump_data, load_config

router = APIRouter(prefix="/api", tags=["ops"])
sched_admin = APIRouter(prefix="/api/admin/schedules", tags=["admin-schedules"], dependencies=[Depends(require_admin_area)])


# ==================== 1. LIVE ALERT CENTER ====================
@router.get("/alerts")
def alerts_list(db: Session = Depends(get_db), user: User = Depends(current_user)):
    cfg = load_config(db)
    site_lock = effective_site(user, db)
    items = []
    # Active Insights (warn / crit)
    q = select(Insight).where(Insight.status.in_(["new", "read"]), Insight.severity.in_(["crit", "warn"])).order_by(Insight.status.asc(), Insight.severity.asc(), Insight.last_seen.desc()).limit(30)
    if site_lock:
        q = q.where(or_(Insight.site == site_lock, Insight.site.is_(None)))
    for r in db.scalars(q):
        items.append({
            "id": f"ins:{r.id}", "ins_id": r.id, "sev": r.severity, "unread": r.status == "new",
            "title": r.title, "detail": (r.detail or "")[:180], "tab": r.tab or "insight", "site": r.site or "",
            "at": int(r.last_seen.timestamp() * 1000) if r.last_seen else None, "ack_by": r.ack_by or "",
        })
    # Open Major Incidents
    iq = select(MajorIncident).where(MajorIncident.status != "resolved").order_by(MajorIncident.started_at.desc()).limit(10)
    if site_lock:
        iq = iq.where(or_(MajorIncident.site == site_lock, MajorIncident.site.is_(None)))
    for inc in db.scalars(iq):
        items.append({
            "id": f"inc:{inc.id}", "inc_id": inc.id, "sev": "crit" if inc.severity == "sev1" else "warn", "unread": True,
            "title": f"[{inc.severity.upper()}] {inc.title}", "detail": (inc.summary or inc.site or "Active major incident")[:160],
            "tab": "incidents", "site": inc.site or "",
            "at": int(inc.started_at.timestamp() * 1000) if inc.started_at else None, "ack_by": "",
        })
    # Failing data sources (visible to admins)
    if user.role.is_admin or user.role.admin_view:
        for ds in db.scalars(select(DataSource).where(DataSource.enabled.is_(True), DataSource.last_error.isnot(None))):
            items.append({
                "id": f"src:{ds.key}", "sev": "crit", "unread": True,
                "title": f"Data source sync failed: {ds.label}", "detail": str(ds.last_error)[:150],
                "tab": "admin", "site": "", "at": int(ds.last_ok_at.timestamp() * 1000) if ds.last_ok_at else None, "ack_by": "",
            })
    unread = sum(1 for x in items if x["unread"])
    return {"unread": unread, "total": len(items), "items": items[:35]}


@router.post("/alerts/ack/{ins_id}")
def alert_ack(ins_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    r = db.get(Insight, ins_id)
    if not r:
        raise HTTPException(404, "Alert not found")
    cfg = load_config(db)
    r.status, r.ack_by, r.ack_at = "read", user.username, cfg.now()
    db.commit()
    bump_data()
    return {"ok": True}


@router.post("/alerts/ack-all")
def alert_ack_all(db: Session = Depends(get_db), user: User = Depends(current_user)):
    cfg = load_config(db)
    now = cfg.now()
    n = 0
    for r in db.scalars(select(Insight).where(Insight.status == "new", Insight.severity.in_(["crit", "warn"]))):
        r.status, r.ack_by, r.ack_at = "read", user.username, now
        n += 1
    db.commit()
    bump_data()
    return {"ok": True, "acked": n}


# ==================== 2. GLOBAL QUICK SEARCH ====================
@router.get("/search")
def global_search(q: str = Query("", min_length=0, max_length=100), db: Session = Depends(get_db), user: User = Depends(current_user)):
    term = q.strip()
    cfg = load_config(db)
    site_lock = effective_site(user, db)
    ql = term.lower()
    out = {"menus": [], "sites": [], "devices": [], "tickets": [], "people": [], "incidents": []}

    # Menus (always return matching accessible modules)
    for m in cfg.modules:
        if not can_see(user, m["key"]):
            continue
        if not ql or ql in m["label"].lower() or ql in m["key"].lower():
            out["menus"].append({"key": m["key"], "label": m["label"], "parent": m.get("parent") or "", "icon": m.get("icon") or ""})
    out["menus"] = out["menus"][:8]
    if len(term) < 2:
        return out

    like = "%" + term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"

    # Sites / Locations
    if not site_lock:
        for s in db.scalars(select(Site).where(Site.active.is_(True), Site.name.ilike(like, escape="\\")).order_by(Site.sort, Site.name).limit(6)):
            out["sites"].append({"name": s.name, "kind": s.kind or "branch"})

    # Devices & ISP hosts
    if can_see(user, "devices") or can_see(user, "noc"):
        dq = select(ZbxHost).where(or_(ZbxHost.name.ilike(like, escape="\\"), ZbxHost.ip.ilike(like, escape="\\"), ZbxHost.site.ilike(like, escape="\\"))).limit(8)
        if site_lock:
            dq = dq.where(ZbxHost.site == site_lock)
        for d in db.scalars(dq):
            is_isp = (d.name or "").upper().startswith("ISP-")
            out["devices"].append({"name": d.name, "ip": d.ip or "", "site": d.site or "", "status": d.status or "", "tab": "noc" if is_isp else "devices"})

    # Tickets
    if can_see(user, "servicedesk"):
        tq = select(Ticket).where(or_(Ticket.id.ilike(like, escape="\\"), Ticket.subject.ilike(like, escape="\\"), Ticket.site.ilike(like, escape="\\"), Ticket.technician.ilike(like, escape="\\"))).order_by(Ticket.created_at.desc()).limit(8)
        if site_lock:
            tq = tq.where(Ticket.site == site_lock)
        for t in db.scalars(tq):
            out["tickets"].append({"id": t.id, "subject": (t.subject or "")[:90], "site": t.site or "", "status": t.status or "", "tech": t.technician or ""})

    # Personnel
    if can_see(user, "jadwal"):
        pq = select(Person).where(or_(Person.name.ilike(like, escape="\\"), Person.unit.ilike(like, escape="\\"), Person.branch.ilike(like, escape="\\"), Person.phone.ilike(like, escape="\\"))).limit(6)
        for p in db.scalars(pq):
            out["people"].append({"name": p.name, "unit": p.unit or "", "job": p.job or "", "branch": p.branch or "", "phone": p.phone or ""})

    # Major Incidents
    iq = select(MajorIncident).where(or_(MajorIncident.title.ilike(like, escape="\\"), MajorIncident.site.ilike(like, escape="\\"))).order_by(MajorIncident.started_at.desc()).limit(5)
    if site_lock:
        iq = iq.where(or_(MajorIncident.site == site_lock, MajorIncident.site.is_(None)))
    for inc in db.scalars(iq):
        out["incidents"].append({"id": inc.id, "title": inc.title, "severity": inc.severity, "status": inc.status, "site": inc.site or ""})

    return out


# ==================== 3. SLA BREACH COUNTDOWN ====================
@router.get("/sla-risk")
def sla_risk(site: str = "", db: Session = Depends(get_db), user: User = Depends(current_user)):
    if not can_see(user, "servicedesk"):
        raise HTTPException(403, "No access to Ticketing")
    cfg = load_config(db)
    site_lock = effective_site(user, db) or site
    closed = set(cfg.p("sd.closed_statuses") or ["Closed", "Resolved"])
    onhold = set(cfg.p("sd.onhold_statuses") or ["Onhold", "On Hold"])
    sla_map = {str(k).lower(): float(v) for k, v in (cfg.sla or {}).items() if v}
    default_h = sla_map.get("normal") or sla_map.get("medium") or 24.0
    now = cfg.now()

    q = select(Ticket).where(Ticket.status.notin_(list(closed)), Ticket.created_at.isnot(None)).order_by(Ticket.created_at.asc()).limit(200)
    if site_lock:
        q = q.where(Ticket.site == site_lock)

    rows = []
    for t in db.scalars(q):
        if t.status in onhold:
            continue
        sla_h = sla_map.get(str(t.sla_name or "").lower()) or sla_map.get(str(t.priority or "").lower()) or default_h
        due = t.created_at + timedelta(hours=sla_h)
        rem_min = int((due - now).total_seconds() // 60)
        tone = "crit" if rem_min <= 0 else ("warn" if rem_min <= 120 else "good")
        rows.append({
            "id": t.id, "subject": (t.subject or "")[:100], "site": t.site or "–", "tech": t.technician or "Unassigned",
            "priority": t.priority or t.sla_name or "Standard", "status": t.status or "Open",
            "sla_h": round(sla_h, 1), "rem_min": rem_min, "tone": tone,
            "created": int(t.created_at.timestamp() * 1000), "due": int(due.timestamp() * 1000),
        })
    rows.sort(key=lambda x: x["rem_min"])
    breached = sum(1 for r in rows if r["rem_min"] <= 0)
    imminent = sum(1 for r in rows if 0 < r["rem_min"] <= 120)
    return {"total": len(rows), "breached": breached, "imminent": imminent, "rows": rows[:40]}


# ==================== 4. MAJOR INCIDENT WAR ROOM ====================
class IncidentIn(BaseModel):
    title: str
    severity: str = "sev2"
    site: str | None = None
    summary: str | None = None
    commander: str | None = None


class IncidentPatch(BaseModel):
    status: str | None = None
    severity: str | None = None
    commander: str | None = None
    root_cause: str | None = None
    summary: str | None = None


class UpdateIn(BaseModel):
    kind: str = "update"
    message: str


@router.get("/incidents")
def incidents_list(status: str = "all", site: str = "", db: Session = Depends(get_db), user: User = Depends(current_user)):
    cfg = load_config(db)
    site_lock = effective_site(user, db) or site
    q = select(MajorIncident).order_by(MajorIncident.status.asc(), MajorIncident.started_at.desc()).limit(60)
    if status == "open":
        q = q.where(MajorIncident.status != "resolved")
    elif status == "resolved":
        q = q.where(MajorIncident.status == "resolved")
    if site_lock:
        q = q.where(or_(MajorIncident.site == site_lock, MajorIncident.site.is_(None)))
    incs = list(db.scalars(q))
    ids = [x.id for x in incs]
    upd_map: dict[int, list] = {i: [] for i in ids}
    if ids:
        for u in db.scalars(select(IncidentUpdate).where(IncidentUpdate.incident_id.in_(ids)).order_by(IncidentUpdate.at.desc())):
            upd_map.setdefault(u.incident_id, []).append({
                "id": u.id, "at": int(u.at.timestamp() * 1000) if u.at else None, "author": u.author, "kind": u.kind, "message": u.message,
            })
    now = cfg.now()
    # Auto-detect suggested site outages (site with >=1 ISP down AND >=3 devices down, not already an open incident)
    open_sites = {x.site for x in incs if x.status != "resolved" and x.site}
    isp_down = dict(db.execute(select(ZbxHost.site, func.count()).where(ZbxHost.status == "down", ZbxHost.name.ilike("ISP-%"), ZbxHost.site.isnot(None)).group_by(ZbxHost.site)).all())
    dev_down = dict(db.execute(select(ZbxHost.site, func.count()).where(ZbxHost.status == "down", ZbxHost.site.isnot(None)).group_by(ZbxHost.site)).all())
    suggested = []
    for st_name, n_isp in isp_down.items():
        if st_name in open_sites or (site_lock and st_name != site_lock):
            continue
        n_dev = dev_down.get(st_name, 0)
        if n_isp >= 1 and n_dev >= 3:
            suggested.append({"site": st_name, "isp_down": n_isp, "dev_down": n_dev, "title": f"Multi-system outage at {st_name} ({n_isp} ISP & {n_dev} devices down)"})

    return {
        "open_count": sum(1 for x in incs if x.status != "resolved"),
        "suggested": suggested[:5],
        "rows": [{
            "id": x.id, "title": x.title, "severity": x.severity, "status": x.status, "site": x.site or "",
            "summary": x.summary or "", "root_cause": x.root_cause or "", "commander": x.commander or "",
            "started_at": int(x.started_at.timestamp() * 1000) if x.started_at else None,
            "resolved_at": int(x.resolved_at.timestamp() * 1000) if x.resolved_at else None,
            "elapsed_min": int(((x.resolved_at or now) - x.started_at).total_seconds() // 60) if x.started_at else 0,
            "created_by": x.created_by, "updates": upd_map.get(x.id, []),
        } for x in incs],
    }


@router.post("/incidents")
def incident_create(body: IncidentIn, db: Session = Depends(get_db), user: User = Depends(require_write)):
    if not body.title.strip():
        raise HTTPException(422, "Incident title is required")
    sev = body.severity if body.severity in ("sev1", "sev2", "sev3") else "sev2"
    cfg = load_config(db)
    now = cfg.now()
    inc = MajorIncident(
        title=body.title.strip()[:220], severity=sev, status="open", site=(body.site or "").strip() or None,
        summary=(body.summary or "").strip() or None, commander=(body.commander or user.full_name).strip()[:120],
        started_at=now, created_by=user.username,
    )
    db.add(inc)
    db.flush()
    db.add(IncidentUpdate(incident_id=inc.id, at=now, author=user.full_name, kind="update", message=f"Major incident declared ({sev.upper()})." + (f" {body.summary.strip()}" if body.summary else "")))
    audit(db, user.username, f"Declared major incident #{inc.id}: {inc.title[:100]}")
    db.commit()
    notify.fire("incident_new", f"[{sev.upper()} MAJOR INCIDENT] {inc.title}" + (f" · Site: {inc.site}" if inc.site else "") + f" · Commander: {inc.commander}", {"id": inc.id})
    bump_data()
    return {"ok": True, "id": inc.id}


@router.patch("/incidents/{iid}")
def incident_patch(iid: int, body: IncidentPatch, db: Session = Depends(get_db), user: User = Depends(require_write)):
    inc = db.get(MajorIncident, iid)
    if not inc:
        raise HTTPException(404, "Incident not found")
    cfg = load_config(db)
    now = cfg.now()
    if body.severity in ("sev1", "sev2", "sev3"):
        inc.severity = body.severity
    if body.commander is not None:
        inc.commander = body.commander.strip()[:120] or inc.commander
    if body.summary is not None:
        inc.summary = body.summary.strip() or None
    if body.root_cause is not None:
        inc.root_cause = body.root_cause.strip() or None
    if body.status in ("open", "monitoring", "resolved") and body.status != inc.status:
        inc.status = body.status
        if body.status == "resolved":
            inc.resolved_at = now
            db.add(IncidentUpdate(incident_id=inc.id, at=now, author=user.full_name, kind="resolved", message="Incident resolved." + (f" Root cause: {inc.root_cause}" if inc.root_cause else "")))
            notify.fire("incident_resolved", f"[RESOLVED] Major Incident #{inc.id}: {inc.title}" + (f" · Root cause: {inc.root_cause}" if inc.root_cause else ""), {"id": inc.id})
        else:
            inc.resolved_at = None
            db.add(IncidentUpdate(incident_id=inc.id, at=now, author=user.full_name, kind="update", message=f"Status changed to {body.status}."))
    audit(db, user.username, f"Updated major incident #{inc.id} ({inc.status})")
    db.commit()
    bump_data()
    return {"ok": True}


@router.post("/incidents/{iid}/updates")
def incident_add_update(iid: int, body: UpdateIn, db: Session = Depends(get_db), user: User = Depends(require_write)):
    inc = db.get(MajorIncident, iid)
    if not inc:
        raise HTTPException(404, "Incident not found")
    if not body.message.strip():
        raise HTTPException(422, "Update message is required")
    kind = body.kind if body.kind in ("update", "escalation", "mitigation", "resolved") else "update"
    now = load_config(db).now()
    db.add(IncidentUpdate(incident_id=inc.id, at=now, author=user.full_name, kind=kind, message=body.message.strip()))
    if kind == "resolved" and inc.status != "resolved":
        inc.status, inc.resolved_at = "resolved", now
    db.commit()
    bump_data()
    return {"ok": True}


# ==================== 5. SCHEDULED AUTOMATED REPORTS ====================
class SchedIn(BaseModel):
    name: str
    enabled: bool = True
    frequency: str = "daily"
    run_time: str = "08:00"
    day_of_week: int | None = None
    day_of_month: int | None = None
    report_kind: str = "shift_summary"
    fmt: str = "text"
    site: str | None = None
    channel: str = "webhook"
    recipients: str | None = None


def _run_schedule_obj(db: Session, s: ReportSchedule) -> str:
    cfg = load_config(db)
    now = cfg.now()
    today = now.date()
    d_from = today - timedelta(days=7 if s.frequency == "weekly" else (30 if s.frequency == "monthly" else 1))
    subject = f"[TERA Scheduled] {s.name} ({today.strftime('%d %b %Y')})"
    body_text = ""
    attachments = []

    if s.report_kind == "shift_summary" or s.fmt == "text":
        res = shift_summary(db, cfg, scope="24h" if s.frequency in ("daily", "shift") else ("7d" if s.frequency == "weekly" else "30d"), kind="full", site=s.site or "")
        body_text = res.get("text") or "No summary generated."
    else:
        admin_u = db.query(User).join(Role, User.role_key == Role.key).filter(Role.is_admin.is_(True), User.active.is_(True)).first()
        if not admin_u:
            raise RuntimeError("No active Super Admin account found for scheduled report generation")
        f = SimpleNamespace(d_from=d_from, d_to=today, shift=0, site=s.site or "", prev=(d_from - (today - d_from) - timedelta(days=1), d_from - timedelta(days=1)), risp="", rgrp="", rtech="")
        model = REP.build(db, cfg, admin_u, f, kind=s.report_kind, preset="standar")
        body_text = f"{model['subtitle']}\nPeriod: {model['period']}\nGenerated automatically by TERA Dashboard."
        if s.fmt == "pdf":
            attachments.append((f"tera-{s.report_kind}-{today.isoformat()}.pdf", EXP.to_pdf(model), "application/pdf"))
        elif s.fmt == "xlsx":
            attachments.append((f"tera-{s.report_kind}-{today.isoformat()}.xlsx", EXP.to_xlsx(model), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))

    sent = []
    if s.channel in ("webhook", "both"):
        notify.fire("scheduled_report", f"{subject}\n\n{body_text[:3500]}", {"schedule_id": s.id, "name": s.name})
        sent.append("webhook")
    if s.channel in ("email", "both"):
        rcpts = [x.strip() for x in (s.recipients or "").split(",") if "@" in x]
        if not rcpts:
            raise RuntimeError("No valid email recipients configured")
        mailer.send(db, rcpts, subject, body_text, attachments or None)
        sent.append(f"email({len(rcpts)})")
    s.last_run_at = now
    s.last_status = "Sent via " + " + ".join(sent)
    return s.last_status


def run_due_schedules() -> None:
    """Called every minute by worker scheduler; dispatches due schedules cleanly."""
    with session_scope() as db:
        cfg = load_config(db)
        now = cfg.now()
        hhmm = now.strftime("%H:%M")
        shift_hours = {f"{int(x['start']):02d}:00" for x in (cfg.shifts or [])} or {"08:00", "15:00", "22:00"}
        for s in db.scalars(select(ReportSchedule).where(ReportSchedule.enabled.is_(True))):
            if s.last_run_at and (now - s.last_run_at).total_seconds() < 300:
                continue
            due = False
            if s.frequency == "shift":
                due = hhmm in shift_hours
            elif s.frequency == "daily":
                due = hhmm == (s.run_time or "08:00")
            elif s.frequency == "weekly":
                due = hhmm == (s.run_time or "08:00") and now.weekday() == (s.day_of_week if s.day_of_week is not None else 0)
            elif s.frequency == "monthly":
                due = hhmm == (s.run_time or "08:00") and now.day == (s.day_of_month if s.day_of_month is not None else 1)
            if not due:
                continue
            try:
                _run_schedule_obj(db, s)
            except Exception as e:
                s.last_run_at = now
                s.last_status = ("Failed: " + str(e))[:210]


@sched_admin.get("")
def sched_list(db: Session = Depends(get_db)):
    rows = db.scalars(select(ReportSchedule).order_by(ReportSchedule.id.asc())).all()
    return {"rows": [{
        "id": s.id, "name": s.name, "enabled": s.enabled, "frequency": s.frequency, "run_time": s.run_time,
        "day_of_week": s.day_of_week, "day_of_month": s.day_of_month, "report_kind": s.report_kind, "fmt": s.fmt,
        "site": s.site or "", "channel": s.channel, "recipients": s.recipients or "",
        "last_run_at": int(s.last_run_at.timestamp() * 1000) if s.last_run_at else None, "last_status": s.last_status or "",
    } for s in rows]}


@sched_admin.post("")
def sched_create(body: SchedIn, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    if not body.name.strip():
        raise HTTPException(422, "Schedule name is required")
    s = ReportSchedule(**body.model_dump())
    db.add(s)
    audit(db, user.username, f"Created report schedule: {s.name}")
    db.commit()
    return {"ok": True, "id": s.id}


@sched_admin.put("/{sid}")
def sched_update(sid: int, body: SchedIn, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    s = db.get(ReportSchedule, sid)
    if not s:
        raise HTTPException(404, "Schedule not found")
    for k, v in body.model_dump().items():
        setattr(s, k, v)
    audit(db, user.username, f"Updated report schedule: {s.name}")
    db.commit()
    return {"ok": True}


@sched_admin.delete("/{sid}")
def sched_delete(sid: int, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    s = db.get(ReportSchedule, sid)
    if not s:
        raise HTTPException(404, "Schedule not found")
    db.delete(s)
    audit(db, user.username, f"Deleted report schedule: {s.name}")
    db.commit()
    return {"ok": True}


@sched_admin.post("/{sid}/run")
def sched_run_now(sid: int, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    s = db.get(ReportSchedule, sid)
    if not s:
        raise HTTPException(404, "Schedule not found")
    try:
        st = _run_schedule_obj(db, s)
        audit(db, user.username, f"Ran report schedule manually: {s.name}")
        db.commit()
        return {"ok": True, "status": st}
    except Exception as e:
        s.last_status = ("Failed: " + str(e))[:210]
        db.commit()
        raise HTTPException(400, str(e))
