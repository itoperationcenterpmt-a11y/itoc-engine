"""WiFi: putus sesi client lewat Ruckus vSZ. Hanya role/username yang diizinkan (calc.wifi.can_kill), setiap aksi dicatat di audit log."""
import re
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..calc import wifi as WIFI
from ..db import get_db
from ..ingest import ruckus
from ..models import User, WifiClient
from ..security import current_user, can_see, rate_limit
from ..store import audit, load_config, bump_data

router = APIRouter(prefix="/api/wifi", tags=["wifi"])
MAC = re.compile(r"^([0-9A-F]{2}:){5}[0-9A-F]{2}$")


class KillIn(BaseModel):
    mac: str
    mode: str = "disconnect"
    reason: str = ""


@router.post("/disconnect", dependencies=[Depends(rate_limit("wifikill", 20, 60))])
def disconnect(body: KillIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    cfg = load_config(db)
    if not can_see(user, "wifi") or not WIFI.can_kill(user, cfg):
        raise HTTPException(403, "This account may not disconnect WiFi clients")
    mac = body.mac.strip().upper()
    if body.mode not in ("disconnect", "deauth") or not MAC.match(mac):
        raise HTTPException(422, "Invalid request")
    c = db.get(WifiClient, mac)
    if not c or not c.ap_mac:
        raise HTTPException(404, "The client is not in the latest data (it may already be disconnected)")
    try:
        ruckus.disconnect(db, body.mode, c.mac, c.ap_mac)
    except Exception as e:
        audit(db, user.username, f"Gagal {body.mode} client WiFi {c.mac}", {"error": str(e)[:200]}, cfg.p("tz_offset_hours", 7))
        db.commit()
        raise HTTPException(502, str(e)[:240])
    audit(db, user.username, f"{body.mode} client WiFi {c.mac}", {"user": c.username, "host": c.hostname, "ssid": c.ssid, "ap": c.ap_name, "ip": c.ip, "reason": body.reason.strip()[:200]}, cfg.p("tz_offset_hours", 7))
    db.delete(c)
    db.commit()
    bump_data()
    return {"ok": True}