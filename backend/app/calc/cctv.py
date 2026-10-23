"""Inventaris CCTV dari Milestone XProtect (tabel cctv_hardware dan cctv_camera): kamera per hardware/lokasi, yang dinonaktifkan, dan yang tidak merekam.
REST XProtect 2022 R2 hanya memberi konfigurasi, jadi 'aktif' berarti diaktifkan di Milestone, bukan online real-time (status online ada di menu Devices dari Zabbix)."""
from datetime import datetime
from ..models import CctvCamera, CctvHardware, DataSource, ZbxHost
from ..timeutil import ms


def build(db, cfg, server: str = "", hw_name: str = "", state: str = "") -> dict:
    """Camera inventory. Filters: server, hardware name, and state (rec = recording centrally, norec = enabled but not recording, off = disabled)."""
    all_cams = db.query(CctvCamera).order_by(CctvCamera.server, CctvCamera.hardware, CctvCamera.channel, CctvCamera.name).all()
    all_hws = db.query(CctvHardware).order_by(CctvHardware.cameras.desc(), CctvHardware.name).all()
    opts = {"servers": sorted({c.server for c in all_cams} | {h.server for h in all_hws}), "hardware": sorted({(h.server, h.name) for h in all_hws})}
    opts["hardware"] = [{"server": s, "name": n} for s, n in opts["hardware"]]
    zmap = {ip: st for ip, st in db.query(ZbxHost.ip, ZbxHost.status).filter(ZbxHost.ip != "")}      # online status comes from Zabbix, matched by IP
    z = lambda c: zmap.get(c.ip or "", "")
    ok = {"": lambda c: True, "rec": lambda c: c.recording, "norec": lambda c: c.enabled and not c.recording, "off": lambda c: not c.enabled,
          "down": lambda c: z(c) in ("down", "degraded"), "nozbx": lambda c: not z(c)}.get(state, lambda c: True)
    cams = [c for c in all_cams if (not server or c.server == server) and (not hw_name or c.hardware == hw_name) and ok(c)]
    hws = [h for h in all_hws if (not server or h.server == server) and (not hw_name or h.name == hw_name)]
    src = db.get(DataSource, "milestone")
    last = max((c.fetched_at for c in cams), default=None)
    every = (src.interval_min if src else 10) or 10
    per: dict = {}
    for c in cams:
        x = per.setdefault(c.hardware_id, {"rec": 0, "off": 0, "zdown": 0})
        x["zdown"] += 1 if z(c) in ("down", "degraded") else 0
        x["rec"] += 1 if c.recording else 0
        x["off"] += 0 if c.enabled else 1
    hw = [{"id": h.id, "server": h.server, "name": h.name, "host": h.host or "-", "model": h.model or "-", "enabled": h.enabled, "cameras": h.cameras, "camEnabled": h.cameras_enabled,
           "rec": per.get(h.id, {}).get("rec", 0), "off": per.get(h.id, {}).get("off", 0), "zdown": per.get(h.id, {}).get("zdown", 0)} for h in hws]
    sv: dict = {}
    for c in cams:
        s = sv.setdefault(c.server, {"name": c.server, "cameras": 0, "hw": 0, "enabled": 0, "rec": 0, "updated": None})
        s["cameras"] += 1
        s["enabled"] += 1 if c.enabled else 0
        s["rec"] += 1 if c.recording else 0
        s["updated"] = max(s["updated"] or c.fetched_at, c.fetched_at)
    for h in hws:
        sv.setdefault(h.server, {"name": h.server, "cameras": 0, "hw": 0, "enabled": 0, "rec": 0, "updated": None})["hw"] += 1
    now = cfg.now()
    return {"configured": bool(src and (src.config or {}).get("base_url")), "enabled": bool(src and src.enabled), "error": src.last_error if src else None,
            "total": len(cams), "camEnabled": sum(1 for c in cams if c.enabled), "recording": sum(1 for c in cams if c.recording), "noIp": sum(1 for c in cams if not c.ip),
            "opts": opts, "zbx": {"matched": sum(1 for c in cams if z(c)), "up": sum(1 for c in cams if z(c) == "up"), "down": sum(1 for c in cams if z(c) in ("down", "degraded")), "other": sum(1 for c in cams if z(c) in ("maintenance", "disabled")), "none": sum(1 for c in cams if not z(c))},
            "nHw": len(hws), "servers": [{**s, "updated": ms(s["updated"] + (now - datetime.utcnow())) if s["updated"] else None} for s in sv.values()], "hwOff": sum(1 for h in hws if not h.enabled), "hw": hw,
            "list": [{"name": c.name, "server": c.server, "hw": c.hardware or "-", "ip": c.ip or "", "ch": c.channel, "enabled": c.enabled, "rec": c.recording, "fps": c.fps or "", "zbx": z(c), "mod": ms(c.modified_at)} for c in cams],
            "updated": ms(last + (now - datetime.utcnow())) if last else None, "stale": bool(last) and (datetime.utcnow() - last).total_seconds() > every * 60 * 3}
