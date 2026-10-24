"""Milestone XProtect inventory (tables cctv_hardware and cctv_camera): cameras and public announcers per hardware / server, what is disabled, what is not recording, and licences in use.
The XProtect REST API only reports configuration, so 'enabled' means enabled in Milestone, not live online (online status comes from Zabbix, matched by IP or by name)."""
import re
from datetime import datetime
from ..ingest import milestone
from ..models import CctvCamera, CctvHardware, DataSource, ZbxHost
from ..timeutil import ms

_TAIL = re.compile(r"\s*\(\s*\d{1,3}(?:\.\d{1,3}){3}\s*\)|\s*-\s*camera\s*\d+\s*$", re.I)


def norm(name: str) -> str:
    """Comparable form of a device name: no '(ip)' or '- Camera 1' suffix, lower case, separators unified (so names that follow the Zabbix convention match)."""
    return re.sub(r"[\s_\-]+", "-", _TAIL.sub("", name or "").strip().lower()).strip("-")


def _has(words: list, *texts) -> bool:
    t = " ".join(x or "" for x in texts).lower()
    return any(w.lower() in t for w in words)


def build(db, cfg, server: str = "", hw_name: str = "", state: str = "", kind: str = "") -> dict:
    """Inventory with filters: server, hardware name, state (rec, norec, off, up, down, nozbx), and type (cam = cameras, pa = public announcers)."""
    all_cams = db.query(CctvCamera).order_by(CctvCamera.server, CctvCamera.hardware, CctvCamera.channel, CctvCamera.name).all()
    all_hws = db.query(CctvHardware).order_by(CctvHardware.cameras.desc(), CctvHardware.name).all()
    src = db.get(DataSource, "milestone")
    lic_total = milestone.server_licenses((src.config or {}) if src else {})
    pa_words, ptz_words, nolic_words = cfg.p("ms.pa_patterns", ["speaker"]) or [], cfg.p("ms.ptz_patterns", ["ptz"]) or [], cfg.p("ms.no_license_models", ["ICPDriver"]) or []
    model = {h.id: h.model or "" for h in all_hws}
    kind_of = lambda c: "pa" if _has(pa_words, model.get(c.hardware_id), c.hardware, c.name) else "ptz" if _has(ptz_words, model.get(c.hardware_id), c.hardware, c.name) else "fix"
    uses_lic = lambda c: c.enabled and not _has(nolic_words, model.get(c.hardware_id))
    opts = {"servers": sorted({c.server for c in all_cams} | {h.server for h in all_hws}), "hardware": [{"server": s, "name": n} for s, n in sorted({(h.server, h.name) for h in all_hws})]}

    zhosts = db.query(ZbxHost).all()
    by_ip, by_name = {h.ip: h for h in zhosts if h.ip}, {norm(h.name): h for h in zhosts}
    zrow = {}
    hw_ip = {h.id: h.host for h in all_hws if h.host and re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", h.host)}
    for c in all_cams:                                                  # online status comes from Zabbix: by the hardware's address first (the device that really answers, even after a replacement), then the IP in the name, then the name
        zrow[c.id] = by_ip.get(hw_ip.get(c.hardware_id, "")) or by_ip.get(c.ip or "") or by_name.get(norm(c.name))
    z = lambda c: zrow[c.id].status if zrow.get(c.id) else ""
    typ = {c.id: kind_of(c) for c in all_cams}
    okf = {"": lambda c: True, "rec": lambda c: c.recording, "norec": lambda c: c.enabled and not c.recording, "off": lambda c: not c.enabled, "up": lambda c: z(c) == "up",
           "down": lambda c: z(c) == "down", "nozbx": lambda c: not z(c)}.get(state, lambda c: True)
    okk = {"": lambda c: True, "cam": lambda c: typ[c.id] != "pa", "fix": lambda c: typ[c.id] == "fix", "ptz": lambda c: typ[c.id] == "ptz", "pa": lambda c: typ[c.id] == "pa"}.get(kind, lambda c: True)
    cams = [c for c in all_cams if (not server or c.server == server) and (not hw_name or c.hardware == hw_name) and okf(c) and okk(c)]
    hws = [h for h in all_hws if (not server or h.server == server) and (not hw_name or h.name == hw_name)]
    last = max((c.fetched_at for c in cams), default=None)
    every = (src.interval_min if src else 10) or 10

    per: dict = {}
    for c in cams:
        x = per.setdefault(c.hardware_id, {"n": 0, "en": 0, "rec": 0, "zdown": 0, "zn": 0, "types": set()})
        x["n"] += 1
        x["en"] += 1 if c.enabled else 0
        x["rec"] += 1 if c.recording else 0
        x["zdown"] += 1 if z(c) == "down" else 0
        x["zn"] += 1 if z(c) else 0
        x["types"].add(typ[c.id])
    hw = []
    for h in hws:
        x = per.get(h.id)
        if kind and not x:
            continue
        x = x or {"n": 0, "en": 0, "rec": 0, "zdown": 0, "zn": 0, "types": set()}
        hw.append({"id": h.id, "server": h.server, "name": h.name, "host": h.host or "-", "model": h.model or "-", "enabled": h.enabled, "type": next(iter(x["types"])) if len(x["types"]) == 1 else "mixed" if x["types"] else "fix",
                   "cameras": x["n"], "camEnabled": x["en"], "rec": x["rec"], "zdown": x["zdown"], "zn": x["zn"]})

    sv: dict = {}
    new_sv = lambda n: {"name": n, "cameras": 0, "pa": 0, "hw": 0, "enabled": 0, "rec": 0, "up": 0, "down": 0, "updated": None, "licUsed": 0, "licTotal": lic_total.get(n)}
    for c in all_cams:                                                  # licences are always counted on the full server, regardless of the filters
        if not server or c.server == server:
            s = sv.setdefault(c.server, new_sv(c.server))
            s["licUsed"] += 1 if uses_lic(c) else 0
    for c in cams:
        s = sv.setdefault(c.server, new_sv(c.server))
        s["pa" if typ[c.id] == "pa" else "cameras"] += 1
        s["enabled"] += 1 if c.enabled else 0
        s["rec"] += 1 if c.recording else 0
        if typ[c.id] != "pa":
            s["up"] += 1 if z(c) in ("up", "maintenance", "disabled", "degraded") else 0
            s["down"] += 1 if z(c) == "down" else 0
        s["updated"] = max(s["updated"] or c.fetched_at, c.fetched_at)
    for h in hws:
        sv.setdefault(h.server, new_sv(h.server))["hw"] += 1
    now = cfg.now()
    live = [n for n, _, on in milestone.servers_all((src.config or {}) if src else {}) if on]
    errs = ((src.cursor or {}).get("server_errors") or {}) if src else {}
    srv = {"total": len(live), "failed": sorted(n for n in live if n in errs), "ok": len([n for n in live if n not in errs])}
    cam_only = [c for c in cams if typ[c.id] != "pa"]
    pa_only = [c for c in cams if typ[c.id] == "pa"]
    return {"configured": bool(src and (src.config or {}).get("base_url")), "enabled": bool(src and src.enabled), "error": src.last_error if src else None,
            "total": len(cam_only), "ptz": sum(1 for c in cam_only if typ[c.id] == "ptz"), "fix": sum(1 for c in cam_only if typ[c.id] == "fix"), "camEnabled": sum(1 for c in cam_only if c.enabled), "recording": sum(1 for c in cam_only if c.recording), "noIp": sum(1 for c in cams if not c.ip),
            "pa": {"total": len(pa_only), "enabled": sum(1 for c in pa_only if c.enabled), "down": sum(1 for c in pa_only if z(c) == "down")},
            "srv": srv, "serverErrors": ((src.cursor or {}).get("server_errors") or {}) if src else {}, "opts": opts, "zbx": {"matched": sum(1 for c in cam_only if z(c)), "up": sum(1 for c in cam_only if z(c) == "up"), "down": sum(1 for c in cam_only if z(c) == "down"),
                                  "other": sum(1 for c in cam_only if z(c) in ("maintenance", "disabled", "degraded")), "none": sum(1 for c in cam_only if not z(c))},
            "nHw": len(hws), "servers": [{**s, "updated": ms(s["updated"] + (now - datetime.utcnow())) if s["updated"] else None} for s in sv.values()], "hwOff": sum(1 for h in hws if not h.enabled), "hw": hw,
            "list": [{"name": c.name, "server": c.server, "hw": c.hardware or "-", "ip": hw_ip.get(c.hardware_id) or c.ip or "", "ch": c.channel, "enabled": c.enabled, "rec": c.recording, "fps": c.fps or "", "type": typ[c.id],
                      "zbx": z(c), "zprob": (zrow[c.id].problem or "") if zrow.get(c.id) else "", "zsince": ms(zrow[c.id].down_since) if zrow.get(c.id) and zrow[c.id].down_since else None, "mod": ms(c.modified_at)} for c in cams],
            "updated": ms(last + (now - datetime.utcnow())) if last else None, "stale": bool(last) and (datetime.utcnow() - last).total_seconds() > every * 60 * 3}
