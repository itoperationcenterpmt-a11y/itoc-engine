"""Client WiFi aktif, Access Point, usage, dan tren dari snapshot Ruckus vSZ (tabel wifi_client, wifi_ap, wifi_stat)."""
from datetime import datetime, timedelta
from ..models import DataSource, WifiAp, WifiClient, WifiStat, ZbxLocMap
from ..store import Config
from ..timeutil import ms


def can_kill(user, cfg: Config) -> bool:
    """Memutus client hanya untuk role di wifi.kill_roles (bawaan Super Admin dan Admin) dan username di wifi.kill_users (mis. koordinator ITOC Shift)."""
    return bool(getattr(user, "is_api", False)) is False and (user.role.is_admin or user.role_key in cfg.p("wifi.kill_roles", ["superadmin", "admin"]) or user.username in cfg.p("wifi.kill_users", []))


def _band(r):
    t = ((r.raw or {}).get("radioType") or "").lower()
    ch = (r.raw or {}).get("channel") or 0
    if "ax" in t and isinstance(ch, int) and ch > 177 or t.startswith("6"):
        return "6 GHz"
    if t.startswith("a") or (isinstance(ch, int) and ch > 14):
        return "5 GHz"
    return "2.4 GHz" if t or ch else "-"


def _top(rows, key, n=12, val=lambda r: 1):
    c: dict = {}
    for r in rows:
        k = key(r) or "-"
        c[k] = c.get(k, 0) + val(r)
    return [{"k": k, "n": v} for k, v in sorted(c.items(), key=lambda x: -x[1])[:n]]


def build(db, cfg: Config, user=None, zone: str = "", ssid: str = "", band: str = "", site: str = "") -> dict:
    every_row = db.query(WifiClient).order_by(WifiClient.username, WifiClient.mac).all()
    cmap = {m.code.lower(): m.site for m in db.query(ZbxLocMap) if m.site}
    loc = lambda r: cmap.get((r.ap_name or "").split("-")[0].strip().lower()) or r.zone or "-"      # kode lokasi di awal nama AP (mis. SRG-RUANG IT) -> lokasi master
    pats = [p.lower() for p in (cfg.p("wifi.portal_auth", ["hotspot", "guest access"]) or [])]
    is_portal = lambda r: any(p in str((r.raw or {}).get("authMethod") or "").lower() for p in pats)
    opts = {"zones": sorted({r.zone for r in every_row if r.zone}), "ssids": sorted({r.ssid for r in every_row if r.ssid}), "locs": sorted({loc(r) for r in every_row if loc(r) != "-"})}
    rows = [r for r in every_row if (not zone or r.zone == zone) and (not ssid or r.ssid == ssid) and (not band or _band(r) == band) and (not site or loc(r) == site)]
    aps = [a for a in db.query(WifiAp).all() if not zone or a.zone == zone]
    src = db.get(DataSource, "ruckus")
    last = max((r.updated_at for r in rows), default=None) or max((a.updated_at for a in aps), default=None)
    every = (src.interval_min if src else 5) or 5
    now = cfg.now()
    weak = int(cfg.p("wifi.weak_rssi", -75))
    tot = lambda r: (r.rx_bytes or 0) + (r.tx_bytes or 0)
    isup = lambda a: str(a.status or "").lower().startswith("online")
    since = now - timedelta(hours=24)
    st = db.query(WifiStat).filter(WifiStat.at >= since).order_by(WifiStat.at).all()
    step = max(1, len(st) // 96)
    trend = [{"t": ms(s.at), "c": s.clients, "u": s.users, "rx": s.rx_bytes, "tx": s.tx_bytes, "ap": s.ap_online} for s in st[::step]]
    by_ap = {}
    for r in rows:
        x = by_ap.setdefault(r.ap_name or "-", {"k": r.ap_name or "-", "n": 0, "bytes": 0})
        x["n"] += 1
        x["bytes"] += tot(r)
    down = sorted(({"name": a.name, "zone": a.zone, "status": a.status, "model": a.model, "ip": a.ip, "since": ms(a.last_seen), "location": a.location} for a in aps if not isup(a)),
                  key=lambda x: (x["since"] is None, x["since"] or 0))
    portal = [{"mac": r.mac, "ip": r.ip, "user": r.username, "host": r.hostname, "status": "login" if (r.username or str((r.raw or {}).get("authStatus") or "").upper() == "AUTHORIZED") else "pending", "auth": (r.raw or {}).get("authMethod"),
               "ssid": r.ssid, "ap": r.ap_name, "zone": r.zone, "loc": loc(r), "band": _band(r), "rssi": r.rssi, "since": ms(r.started_at), "rx": r.rx_bytes, "tx": r.tx_bytes} for r in rows if is_portal(r)]
    portal.sort(key=lambda x: (x["status"] != "login", x["user"] or "", x["since"] or 0))
    return {"portal": portal, "portalLogin": sum(1 for x in portal if x["status"] == "login"), "byLoc": _top(rows, loc, 10), "total": len(rows), "users": len({r.username for r in rows if r.username}), "named": sum(1 for r in rows if r.username), "weak": sum(1 for r in rows if r.rssi is not None and r.rssi < weak), "weakAt": weak,
            "rx": sum(r.rx_bytes or 0 for r in rows), "tx": sum(r.tx_bytes or 0 for r in rows),
            "apTotal": len(aps), "apOnline": sum(1 for a in aps if isup(a)), "apDown": down[:50],
            "bySsid": _top(rows, lambda r: r.ssid), "bySsidBytes": _top(rows, lambda r: r.ssid, 10, tot), "byAp": sorted(by_ap.values(), key=lambda x: -x["n"])[:10],
            "byZone": _top(rows, lambda r: r.zone, 10), "byType": _top(rows, lambda r: (r.raw or {}).get("deviceType") or "-", 8), "byBand": _top(rows, _band, 4),
            "top": [{"user": r.username, "host": r.hostname, "mac": r.mac, "ssid": r.ssid, "ap": r.ap_name, "bytes": tot(r), "rx": r.rx_bytes, "tx": r.tx_bytes}
                    for r in sorted(rows, key=lambda r: -tot(r))[:10]],
            "trend": trend, "opts": opts, "canKill": bool(user and can_kill(user, cfg)),
            "list": [{"mac": r.mac, "ip": r.ip, "user": r.username, "host": r.hostname, "ssid": r.ssid, "ap": r.ap_name, "zone": r.zone, "loc": loc(r), "os": r.os, "band": _band(r),
                      "rssi": r.rssi, "vlan": r.vlan, "since": ms(r.started_at), "rx": r.rx_bytes, "tx": r.tx_bytes, "auth": (r.raw or {}).get("authMethod")} for r in rows[:3000]],
            "updated": ms(last + (now - datetime.utcnow())) if last else None,
            "stale": bool(last) and (datetime.utcnow() - last).total_seconds() > every * 60 * 3,
            "configured": bool(src and (src.config or {}).get("base_url")), "enabled": bool(src and src.enabled), "error": src.last_error if src else None}