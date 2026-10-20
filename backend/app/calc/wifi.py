"""Client WiFi aktif dari snapshot Ruckus vSZ (tabel wifi_client)."""
from datetime import datetime
from sqlalchemy import func
from ..models import DataSource, WifiClient
from ..store import Config
from ..timeutil import ms


def _top(rows, key, n=12):
    c: dict = {}
    for r in rows:
        k = key(r) or "-"
        c[k] = c.get(k, 0) + 1
    return [{"k": k, "n": v} for k, v in sorted(c.items(), key=lambda x: -x[1])[:n]]


def build(db, cfg: Config) -> dict:
    rows = db.query(WifiClient).order_by(WifiClient.username, WifiClient.mac).all()
    src = db.get(DataSource, "ruckus")
    last = max((r.updated_at for r in rows), default=None)
    every = (src.interval_min if src else 5) or 5
    now = cfg.now()
    return {"total": len(rows), "users": len({r.username for r in rows if r.username}),
            "bySsid": _top(rows, lambda r: r.ssid), "byAp": _top(rows, lambda r: r.ap_name, 10), "byZone": _top(rows, lambda r: r.zone, 10),
            "list": [{"mac": r.mac, "ip": r.ip, "user": r.username, "host": r.hostname, "ssid": r.ssid, "ap": r.ap_name, "zone": r.zone, "os": r.os,
                      "rssi": r.rssi, "vlan": r.vlan, "since": ms(r.started_at), "rx": r.rx_bytes, "tx": r.tx_bytes} for r in rows[:3000]],
            "updated": ms(last + (now - datetime.utcnow())) if last else None,
            "stale": bool(last) and (datetime.utcnow() - last).total_seconds() > every * 60 * 3,
            "configured": bool(src and (src.config or {}).get("base_url")), "enabled": bool(src and src.enabled), "error": src.last_error if src else None}