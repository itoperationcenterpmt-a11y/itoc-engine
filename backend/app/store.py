"""Memuat seluruh konfigurasi dari database ke satu objek, dengan cache yang dibatalkan
setiap kali Admin mengubah master/parameter atau ada data baru masuk."""
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from sqlalchemy.orm import Session
from . import models as M
from .timeutil import ShiftClock, now_local

_lock = threading.Lock()
_state = {"cfg_ver": 0, "data_ver": 0, "cfg": None, "cfg_at": 0.0}
_results: dict = {}
CFG_TTL = 3   # detik; konfigurasi (layout, menu, parameter) di worker lain ikut tersegarkan paling lambat selama ini
RES_TTL = 60  # detik; hasil hitungan view dihitung ulang paling lambat selama ini bila data berubah di proses lain


def bump_config():
    with _lock:
        _state["cfg_ver"] += 1
        _state["cfg"] = None
        _results.clear()


def bump_data():
    with _lock:
        _state["data_ver"] += 1
        _results.clear()


def cached(key: tuple, fn):
    # ember waktu 60 dtk: data baru dari proses worker ikut terbaca walau bump_data terjadi di proses lain
    k = (_state["cfg_ver"], _state["data_ver"], int(time.time() // RES_TTL)) + key
    if k in _results:
        return _results[k]
    v = fn()
    if len(_results) > 400:
        _results.clear()
    _results[k] = v
    return v


@dataclass
class Config:
    params: dict
    shifts: list[dict]
    teams: list[dict]
    sites: list[str]
    people: list[dict]
    isps: list[dict]
    sla: dict
    modules: list[dict]
    roles: dict
    formulas: list[dict]
    sources: dict
    clock: ShiftClock = field(repr=False)
    widgets: list = field(default_factory=list)
    layouts: list = field(default_factory=list)

    def p(self, key, default=None):
        return self.params.get(key, default)

    def now(self) -> datetime:
        return now_local(self.p("tz_offset_hours", 7))

    def net_params(self) -> dict:
        t = self.p("net.target")
        return {"target": t, "minCov": self.p("net.min_cov"), "utilPeak": self.p("net.util_peak"), "utilAvg": self.p("net.util_avg"),
                "isps": [{"kw": i["keyword"], "name": i["name"], "target": i["target"] if i["target"] is not None else t} for i in self.isps]}


def _row(o, cols):
    return {c: getattr(o, c) for c in cols}


def load_config(db: Session) -> Config:
    with _lock:
        c = _state["cfg"]
        if c is not None and time.time() - _state["cfg_at"] < CFG_TTL:
            return c
    params = {p.key: p.value for p in db.query(M.Parameter)}
    shifts = [{"no": s.no, "code": s.code, "name": s.name, "start": s.start_hour} for s in db.query(M.Shift).order_by(M.Shift.no)]
    teams = [{"code": t.code, "label": t.label, "offset": t.rotation_offset, "sort": t.sort} for t in db.query(M.Team).order_by(M.Team.sort)]
    people = [_row(p, ["id", "name", "sys_name", "unit", "job", "team_code", "branch", "phone", "is_coordinator", "is_shared", "exclude_rank"])
              for p in db.query(M.Person).filter_by(active=True).order_by(M.Person.id)]
    for p in people:  # bentuk yang dipakai frontend
        p["group"] = p["team_code"] or ""
        p["sys"] = p["sys_name"] or p["name"]
    cfg = Config(
        params=params, shifts=shifts, teams=teams,
        sites=[s.name for s in db.query(M.Site).filter_by(active=True).order_by(M.Site.sort, M.Site.name)],
        people=people,
        isps=[_row(i, ["keyword", "name", "target"]) for i in db.query(M.Isp).order_by(M.Isp.sort)],
        sla={s.name: s.hours for s in db.query(M.SlaTarget)},
        modules=[_row(m, ["key", "label", "sort", "icon", "parent", "filters", "note", "why", "badge", "notice"]) for m in db.query(M.Module).filter_by(enabled=True).order_by(M.Module.sort)],
        roles={r.key: _row(r, ["key", "label", "modules", "can_write", "is_admin", "admin_view", "scope", "uploads"]) for r in db.query(M.Role).order_by(M.Role.sort)},
        formulas=[_row(f, ["key", "label", "text", "source"]) for f in db.query(M.Formula).order_by(M.Formula.sort)],
        sources={s.key: _row(s, ["key", "label", "mode", "enabled", "interval_min", "tip", "last_ok_at", "last_error", "config"]) for s in db.query(M.DataSource)},
        clock=ShiftClock(shifts, teams, params.get("rotation", {})),
        layouts=[_row(l, ["page", "role", "key", "title", "size", "enabled", "sort"]) for l in db.query(M.Layout).order_by(M.Layout.page, M.Layout.role, M.Layout.sort)],
        widgets=[_row(w, ["key", "section", "title", "kind", "top_n", "hero", "presets", "sort"]) for w in db.query(M.Widget).filter_by(enabled=True).order_by(M.Widget.section, M.Widget.sort)],
    )
    with _lock:
        _state["cfg"], _state["cfg_at"] = cfg, time.time()
    return cfg


def audit(db: Session, username: str, action: str, detail: dict | None = None, tz: float = 7):
    db.add(M.AuditLog(at=now_local(tz), username=username, action=action, detail=detail))
