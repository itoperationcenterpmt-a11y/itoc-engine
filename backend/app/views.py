"""Satu bundel data per halaman. Frontend hanya merender; semua angka dihitung di sini."""
from datetime import date, datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from . import models as M
from .store import Config, cached
from .timeutil import ms
from .calc import servicedesk as SD, network as NET, soc as SOC, devices as DEV, wifi as WIFI, xdr as XDR, cctv as CCTV, soc_fw as SOCFW, insight as INSIGHT, viz as VIZ
from .calc.common import iso
from .security import can_see, locked_pages


class Filt:
    def __init__(self, d_from: date, d_to: date, shift: int, site: str, cmp: bool, sensor: str = "", kind: str = "", dstat: str = "", grp: str = "", dtype: str = ""):
        self.d_from, self.d_to, self.shift, self.site, self.cmp, self.sensor = d_from, d_to, shift, site, cmp, sensor
        self.kind, self.dstat, self.grp, self.dtype = kind, dstat, grp, dtype       # filter kategori dan status (menu Devices)

    @property
    def prev(self):
        n = (self.d_to - self.d_from).days + 1
        return self.d_from - timedelta(days=n), self.d_from - timedelta(days=1)


# ---------------- perhitungan bersama (di-cache per kombinasi filter) ----------------
def _tsite(db, site: str):
    """Tiket milik lokasi: nama Group di ManageEngine cocok dengan nama lokasi atau aliasnya (tanpa beda huruf besar/kecil)."""
    return func.lower(M.Ticket.site).in_(NET.device_names(db, site))


def _canon_counts(db, counts: dict) -> dict:
    """Gabungkan hitungan per nama Group ke nama lokasi di master (mis. "Pelindo Tower" -> "Kantor Perwakilan")."""
    amap = {}
    for s in db.query(M.Site).filter_by(active=True):
        for n in NET.device_names(db, s.name):
            amap.setdefault(n, s.name)
    out = {}
    for k, v in counts.items():
        c = amap.get((k or "").lower(), k)
        out[c] = out.get(c, 0) + v
    return out

def _tk(db, cfg: Config, a: date, b: date, shift: int, site: str):
    def run():
        q = select(M.Ticket).where(M.Ticket.created_at >= datetime.combine(a, datetime.min.time()),
                                   M.Ticket.created_at < datetime.combine(b, datetime.min.time()) + timedelta(days=1))
        if site:
            q = q.where(_tsite(db, site))
        rows = SD.as_rows(db.scalars(q.order_by(M.Ticket.created_at)))
        ppl = [p for p in cfg.people if not site or not p["branch"] or p["branch"] == site]
        return SD.calc(rows, cfg, a, b, shift, ppl)
    return cached(("tk", a, b, shift, site), run)


def _net_base(db, cfg, a, b, shift, site):
    return cached(("nb", a, b, shift, site), lambda: NET.build(db, cfg, a, b, shift, site))


def _net(db, cfg, a, b, shift, site):
    return cached(("nr", a, b, shift, site), lambda: NET.calc(_net_base(db, cfg, a, b, shift, site)["N"], cfg))


def _soc(db, cfg, a, b):
    def run():
        m = SOC.merged(db, a, b)
        return {"R": SOC.calc(m[0], cfg, a, b), "chk": SOC.check(db, cfg, a, b, m), "dup": {k: v for k, v in m[2].items() if a.isoformat() <= k <= b.isoformat()},
                "batches": m[3]}
    return cached(("soc", a, b), run)


def ho_json(h: M.Handover) -> dict:
    return {"id": h.id, "at": ms(h.created_at), "date": iso(h.shift_date), "shift": h.shift_no, "cat": h.category, "prio": h.priority, "site": h.site,
            "ticket": h.ticket_id or "", "title": h.title, "body": h.body, "next": h.next_action or "", "by": h.created_by, "open": h.is_open,
            "closedBy": h.closed_by, "closedAt": ms(h.closed_at), "closeNote": h.close_note}


def sources(db: Session, cfg: Config) -> list[dict]:
    out = []
    for s in sorted(cfg.sources.values(), key=lambda x: x["key"]):
        if not s["enabled"]:
            continue
        if s["mode"] == "api":
            at = s["last_ok_at"]
            stale = at is None or (cfg.now() - at).total_seconds() > s["interval_min"] * 60 * 3
            out.append({"state": "warn" if stale or s["last_error"] else "ok", "label": f"{s['label']} {at.strftime('%H.%M') if at else '–'}",
                        "tip": (s["tip"] or "") + (f"\nError terakhir: {s['last_error']}" if s["last_error"] else "")})
        else:
            b = db.scalars(select(M.SocBatch).order_by(M.SocBatch.uploaded_at.desc()).limit(1)).first()
            if b:
                bad = b.status == "failed"
                out.append({"state": "warn", "label": f"{s['label']}: impor {b.uploaded_at.day} {cfg.p('ui.months')[b.uploaded_at.month - 1]}",
                            "tip": (s["tip"] or "") + (f" Impor terakhir {b.file_name} gagal validasi." if bad else f" Impor terakhir {b.file_name}.")})
            else:
                out.append({"state": "warn", "label": f"{s['label']}: belum ada impor", "tip": s["tip"] or ""})
    return out


def _open_tickets(db, cfg, site, limit=None, older_than_days=None):
    q = select(M.Ticket).where(M.Ticket.resolved_at.is_(None), M.Ticket.status.not_in(cfg.p("sd.closed_statuses")))
    if site:
        q = q.where(_tsite(db, site))
    if older_than_days is not None:
        q = q.where(M.Ticket.created_at < cfg.now() - timedelta(days=older_than_days))
        if cfg.p("sd.onhold_pauses_sla", True):                      # an On hold ticket is waiting on someone else, so it is not "old" in the SLA sense
            q = q.where(func.lower(func.coalesce(M.Ticket.status, "")).not_in([x.lower() for x in (cfg.p("sd.onhold_statuses", ["Onhold", "On Hold"]) or [])]))
    q = q.order_by(M.Ticket.created_at.desc() if limit else M.Ticket.created_at)
    if limit:
        q = q.limit(limit)
    now = cfg.now()
    return [{"id": t.id, "subject": t.subject, "site": t.site, "age": (now - t.created_at).total_seconds() / 86400} for t in db.scalars(q)]


# ---------------- page bundles ----------------
INSIGHT_TABS = ("ringkasan", "servicedesk", "network", "noc", "wifi", "cyber", "soc", "xdr", "devices", "devnet", "devcctv", "devops", "cctv")   # pages that show an Insights panel for their own area
def bundle(db: Session, cfg: Config, tab: str, f: Filt, user: M.User) -> dict:
    V: dict = {}
    ok = lambda k: tab == k or can_see(user, k)  # Ringkasan hanya memuat bagian yang boleh dilihat role ini (mis. IT Care/EOS tanpa SOC)
    a, b, sh, st = f.d_from, f.d_to, f.shift, f.site
    pa, pb = f.prev
    if tab in ("ringkasan", "servicedesk") and ok("servicedesk"):
        V["tk"] = _tk(db, cfg, a, b, sh, st)
        V["tk_prev"] = _tk(db, cfg, pa, pb, sh, st) if f.cmp else None
    if tab in ("ringkasan", "noc", "network") and ok("noc"):
        V["net"] = _net(db, cfg, a, b, sh, st)
        V["net_prev"] = _net(db, cfg, pa, pb, sh, st) if f.cmp else None
    if tab in ("ringkasan", "soc", "cyber") and ok("soc"):
        S = _soc(db, cfg, a, b)
        V["soc"], V["soc_check"] = S["R"], S["chk"]
        V["soc_prev"] = _soc(db, cfg, pa, pb)["R"] if f.cmp else None
    if tab in ("internet", "ringkasan", "network") and ok("internet"):
        V["inet"] = SOCFW.build(db, cfg, a, b, st)
        V["inet_prev"] = SOCFW.build(db, cfg, pa, pb, st) if f.cmp and tab == "internet" else None
    if tab == "soc" and ok("soc"):
        V["socfw"] = SOCFW.build(db, cfg, a, b, st)
    if tab == "ringkasan":
        if ok("servicedesk"):
            V["open_old"] = _open_tickets(db, cfg, st, older_than_days=cfg.p("sd.open_alert_days"))
        if ok("serahterima"):
            q = select(M.Handover).where(M.Handover.is_open.is_(True))
            if st:
                q = q.where(M.Handover.site == st)
            V["ho_open"] = [ho_json(h) for h in db.scalars(q.order_by(M.Handover.created_at.desc()))]
    tab_kinds = cfg.p("dev.tab_kinds", {}) or {}
    dev_tab = tab == "devices" or tab in tab_kinds                      # Summary plus the Network / CCTV / Operational sub-menus (one Zabbix category each)
    dkind = tab_kinds.get(tab) or f.kind
    if dev_tab or (tab == "ringkasan" and ok("devices")):
        V["dev"] = DEV.build(db, cfg, st, dkind, f.dstat, full=dev_tab, grp=f.grp, dtype=f.dtype)
        if dev_tab:
            V["dev"]["hist"] = DEV.history(db, cfg, f.d_from, f.d_to, st, dkind, f.dtype)
    if tab == "xdr" or (tab in ("ringkasan", "cyber") and ok("xdr")):
        V["xdr"] = XDR.build(db, cfg, a, b, f.kind if tab == "xdr" and f.kind in XDR.SEV else "")
    if tab in ("ringkasan", "servicedesk", "noc", "network", "cyber", "devices"):
        V["viz"] = VIZ.build(db, cfg, a, b, _tsite(db, st) if st else None)
    if tab == "insight" or (tab in INSIGHT_TABS and ok("insight")):
        V["insight"] = INSIGHT.build(db, cfg, full=tab == "insight")
    if tab == "cctv" or (tab == "ringkasan" and ok("cctv")):
        V["cctv"] = CCTV.build(db, cfg, f.grp, f.dtype, f.dstat, f.kind) if tab == "cctv" else CCTV.build(db, cfg, full=False)
    if tab == "wifi":
        V["wifi"] = WIFI.build(db, cfg, user, zone=f.dtype, ssid=f.grp, band=f.kind, site=st, a=f.d_from, b=f.d_to)
    if tab in ("ringkasan", "network") and ok("wifi"):
        V["wifi"] = WIFI.build(db, cfg, user)
    if tab == "noc":
        nb = _net_base(db, cfg, a, b, sh, st)
        sens = nb["N"]["sensors"]
        V["net_base"] = {"N": {"sensors": sens}, "hourly": nb["hourly"]}
        top = sorted(sens, key=lambda s: -s["avgIn"])
        sid = f.sensor if any(s["id"] == f.sensor for s in sens) else (top[0]["id"] if top else "")
        V["sensor_id"], V["sensor_series"] = sid, NET.series(db, cfg, sid, a, b, sh)
    if tab in ("soc", "kelengkapan"):
        S = _soc(db, cfg, a, b)
        V["batches"] = [SOC.batch_json(x) for x in S["batches"]]
        V["soc_dup"] = S["dup"]
        bt = SOC.batch_for(S["batches"], a, b)
        V["soc_batch"] = SOC.batch_json(bt) if bt else None
    if tab == "jadwal":
        qs = select(M.Ticket.site, func.count()).where(M.Ticket.resolved_at.is_(None), M.Ticket.status.not_in(cfg.p("sd.closed_statuses")))
        if st:
            qs = qs.where(_tsite(db, st))
        V["open_by_site"] = _canon_counts(db, dict(db.execute(qs.group_by(M.Ticket.site)).all()))
    if tab == "serahterima":
        q = select(M.Handover).where(M.Handover.shift_date >= a, M.Handover.shift_date <= b)
        if sh:
            q = q.where(M.Handover.shift_no == sh)
        if st:
            q = q.where(M.Handover.site == st)
        V["handover"] = [ho_json(h) for h in db.scalars(q.order_by(M.Handover.created_at.desc()))]
        V["open_tickets"] = _open_tickets(db, cfg, st, limit=40)
    if tab == "kelengkapan":
        V["coverage"] = coverage(db, cfg, f)
        V["sync_log"] = [{"at": ms(x.at), "src": x.source, "ok": x.ok, "rows": x.rows, "msg": x.message}
                         for x in db.scalars(select(M.SyncLog).order_by(M.SyncLog.at.desc()).limit(30))]
    if tab == "report":
        from . import report
        V["report"] = report.build(db, cfg, user, f, "full", getattr(f, "preset", "standar"))
    if tab == "admin" and (user.role.is_admin or user.role.admin_view):
        V["users"] = [] if not user.role.is_admin and "pengguna" in locked_pages(db) else [{"u": u.username, "name": u.full_name, "role": u.role_key, "last": ms(u.last_login), "active": u.active, "site": u.site}
                      for u in db.scalars(select(M.User).order_by(M.User.id))]
    return V


def coverage(db: Session, cfg: Config, f: Filt) -> list[dict]:
    days = [f.d_from + timedelta(days=i) for i in range(min(62, (f.d_to - f.d_from).days + 1))]
    today = cfg.now().date()
    src = cfg.sources
    ok_hi, ok_lo = cfg.p("completeness.prtg_ok"), cfg.p("completeness.prtg_warn")
    a = datetime.combine(days[0], datetime.min.time())
    b = datetime.combine(days[-1], datetime.min.time()) + timedelta(days=1)
    q = select(func.date(M.Ticket.created_at), func.count()).where(M.Ticket.created_at >= a, M.Ticket.created_at < b)
    if f.site:
        q = q.where(_tsite(db, f.site))
    tk = {iso(d): n for d, n in db.execute(q.group_by(func.date(M.Ticket.created_at)))}
    me_label = src.get("manageengine", {}).get("label", "ManageEngine")
    fails = {}
    for x in db.scalars(select(M.SyncLog).where(M.SyncLog.source == me_label, M.SyncLog.ok.is_(False), M.SyncLog.at >= a, M.SyncLog.at < b)):
        fails.setdefault(iso(x.at), []).append(x.at.strftime("%H.%M"))
    chk = {x["d"]: x["s"] for x in _soc(db, cfg, f.d_from, f.d_to)["chk"]}
    cst = cfg.p("ui.soc_day_status")
    batches = _soc(db, cfg, f.d_from, f.d_to)["batches"]
    me, pr, so, tb = {}, {}, {}, {}
    for d in days:
        k = iso(d)
        if d > today:
            me[k] = pr[k] = ["wait", "–"]
        else:
            n = tk.get(k, 0)
            me[k] = ["dup", f"{n} tiket\n{len(fails[k])} sinkron gagal ({', '.join(fails[k])}), tersusul otomatis"] if k in fails else ["ok", f"{n} tiket tersinkron"]
            c = NET.coverage(db, cfg, d, f.site)
            if not c["exp"]:
                pr[k] = ["wait", "No complete hours yet"]
            else:
                p = c["seen"] / c["exp"]
                pr[k] = ["ok" if p >= ok_hi else "dup" if p >= ok_lo else "bad", f"{p * 100:.1f}% jam-sensor terpantau ({c['seen']}/{c['exp']})".replace(".", ",", 1)]
        s = chk.get(k, "miss")
        so[k] = [s, cst.get(s, s)]
        bt = next((x for x in batches if x.date_from <= d <= x.date_to and x.tables and x.status != "failed"), None)
        tb[k] = ["ok", "Top report from " + bt.file_name] if bt else ["miss", "Top report not available"]
    lab = lambda key, suffix: src.get(key, {}).get("label", key) + " · " + suffix
    return [{"label": lab("manageengine", "Tickets"), "cells": me}, {"label": lab("prtg", "Availability & traffic"), "cells": pr},
            {"label": lab("panorama", "Daily summary"), "cells": so}, {"label": lab("panorama", "Top report"), "cells": tb}]
