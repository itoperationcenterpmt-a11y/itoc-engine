"""Inventaris CCTV dari Milestone XProtect (tabel cctv_hardware dan cctv_camera): kamera per hardware/lokasi, yang dinonaktifkan, dan yang tidak merekam.
REST XProtect 2022 R2 hanya memberi konfigurasi, jadi 'aktif' berarti diaktifkan di Milestone, bukan online real-time (status online ada di menu Devices dari Zabbix)."""
from datetime import datetime
from ..models import CctvCamera, CctvHardware, DataSource
from ..timeutil import ms


def build(db, cfg) -> dict:
    cams = db.query(CctvCamera).order_by(CctvCamera.hardware, CctvCamera.channel, CctvCamera.name).all()
    hws = db.query(CctvHardware).order_by(CctvHardware.cameras.desc(), CctvHardware.name).all()
    src = db.get(DataSource, "milestone")
    last = max((c.fetched_at for c in cams), default=None)
    every = (src.interval_min if src else 10) or 10
    per: dict = {}
    for c in cams:
        x = per.setdefault(c.hardware_id, {"rec": 0, "off": 0})
        x["rec"] += 1 if c.recording else 0
        x["off"] += 0 if c.enabled else 1
    hw = [{"id": h.id, "name": h.name, "host": h.host or "-", "model": h.model or "-", "enabled": h.enabled, "cameras": h.cameras, "camEnabled": h.cameras_enabled,
           "rec": per.get(h.id, {}).get("rec", 0), "off": per.get(h.id, {}).get("off", 0)} for h in hws]
    now = cfg.now()
    return {"configured": bool(src and (src.config or {}).get("base_url")), "enabled": bool(src and src.enabled), "error": src.last_error if src else None,
            "total": len(cams), "camEnabled": sum(1 for c in cams if c.enabled), "recording": sum(1 for c in cams if c.recording), "noIp": sum(1 for c in cams if not c.ip),
            "nHw": len(hws), "hwOff": sum(1 for h in hws if not h.enabled), "hw": hw,
            "list": [{"name": c.name, "hw": c.hardware or "-", "ip": c.ip or "", "ch": c.channel, "enabled": c.enabled, "rec": c.recording, "fps": c.fps or "", "mod": ms(c.modified_at)} for c in cams],
            "updated": ms(last + (now - datetime.utcnow())) if last else None, "stale": bool(last) and (datetime.utcnow() - last).total_seconds() > every * 60 * 3}
