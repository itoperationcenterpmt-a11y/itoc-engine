"""Ruckus SmartZone (vSZ) lewat Public REST API: client WiFi yang sedang terhubung -> tabel wifi_client.
Login memakai akun API khusus (Admin → Sumber Data → Integrasi, terenkripsi). Versi API dideteksi dari apiInfo; bentuk field dipetakan longgar karena beda versi."""
import re
from datetime import datetime, timedelta
from urllib.parse import urlsplit
import httpx
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from .. import vault
from ..models import DataSource, WifiAp, WifiClient, WifiSession, WifiStat, ZbxLocMap
from ..store import Config
from ..calc.network import site_resolver

FALLBACK = ["v9_1", "v9_0", "v8_2", "v8_1", "v8_0", "v7_1"]


def root(base: str) -> str:
    """IP/host saja boleh: https dan port 8443 ditambahkan bila tidak ditulis."""
    b = (base or "").strip().rstrip("/")
    if not re.match(r"^https?://", b, re.I):
        b = "https://" + b
    p = urlsplit(b)
    host = p.netloc if ":" in p.netloc else p.netloc + ":8443"
    return f"{p.scheme}://{host}/wsg/api/public"


def versions(cl: httpx.Client, rt: str) -> list[str]:
    try:
        r = cl.get(rt + "/apiInfo")
        r.raise_for_status()
        v = r.json().get("apiSupportVersions") or []
        v = sorted((x for x in v if re.match(r"^v\d+_\d+$", x)), key=lambda x: tuple(int(n) for n in x[1:].split("_")), reverse=True)
        return v + [x for x in FALLBACK if x not in v]
    except Exception:
        return FALLBACK


def login(cl: httpx.Client, rt: str, user: str, pw: str) -> tuple[str, str]:
    err = "no matching API version"
    for ver in versions(cl, rt):
        try:
            r = cl.post(f"{rt}/{ver}/serviceTicket", json={"username": user, "password": pw})
        except httpx.HTTPError as e:
            raise RuntimeError("Cannot connect to vSZ: " + str(e)[:150])
        if r.status_code == 404:
            err = f"{ver} is not supported"
            continue
        if r.status_code in (401, 403):
            raise RuntimeError("vSZ login rejected (wrong username/password or the account has no API rights)")
        r.raise_for_status()
        return ver, r.json()["serviceTicket"]
    raise RuntimeError("vSZ API not found: " + err)


def logout(cl, rt, ver, ticket):
    try:
        cl.delete(f"{rt}/{ver}/serviceTicket", params={"serviceTicket": ticket})
    except Exception:
        pass


def fetch_clients(cl: httpx.Client, rt: str, ver: str, ticket: str, limit: int = 1000, max_rows: int = 20000, path: str = "query/client") -> tuple[list[dict], int]:
    out, page, total = [], 1, 0
    while len(out) < max_rows:
        r = cl.post(f"{rt}/{ver}/{path}", params={"serviceTicket": ticket},
                    json={"filters": [], "fullTextSearch": {"type": "AND", "value": ""}, "attributes": ["*"], "limit": limit, "page": page})
        r.raise_for_status()
        j = r.json()
        out += j.get("list") or []
        total = j.get("totalCount", len(out))
        if not j.get("hasMore") or not j.get("list"):
            break
        page += 1
    return out, total


def pick(d: dict, *names):
    for n in names:
        if d.get(n) not in (None, ""):
            return d[n]
    return None


def _int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _local(ms_, tz):
    return datetime.utcfromtimestamp(ms_ / 1000 if ms_ > 1e11 else ms_) + timedelta(hours=tz) if ms_ else None


def to_ap(d: dict, tz: float) -> dict | None:
    mac = (pick(d, "apMac", "mac") or "").upper()
    if not mac:
        return None
    return {"mac": mac, "name": pick(d, "deviceName", "name"), "zone": pick(d, "zoneName"), "ap_group": pick(d, "apGroupName"), "status": pick(d, "status", "connectionStatus"),
            "model": pick(d, "model"), "ip": pick(d, "ip"), "clients": _int(pick(d, "numClients")), "firmware": pick(d, "firmwareVersion"),
            "location": pick(d, "location"), "last_seen": _local(_int(pick(d, "lastSeen")), tz)}


def to_row(d: dict, tz: float, ap_zone: dict | None = None) -> dict | None:
    mac = (pick(d, "clientMac", "mac", "macAddress") or "").upper()
    if not mac:
        return None
    st = _int(pick(d, "sessionStartTime", "firstConnectTime", "connectedTime", "startTime"))
    user = pick(d, "userName", "username", "user")
    ap_mac = (pick(d, "apMac", "apMacAddress") or "").upper() or None
    return {"mac": mac, "ip": pick(d, "ipAddress", "ip", "clientIp"), "username": None if str(user).strip().upper() in ("N/A", "NA", "-") else user,
            "hostname": pick(d, "hostname", "hostName", "deviceName"), "ssid": pick(d, "ssid", "wlanName", "wlan"),
            "ap_name": pick(d, "apName", "ap"), "ap_mac": ap_mac, "zone": pick(d, "zoneName", "zone") or (ap_zone or {}).get(ap_mac),
            "os": " · ".join(dict.fromkeys(x for x in (pick(d, "deviceType"), pick(d, "osVendorType")) if x and x != "Unknown")) or pick(d, "osType", "os"), "rssi": _int(pick(d, "rssi", "receivedSignalStrength")),
            "vlan": _int(pick(d, "vlan", "vlanId")),
            "started_at": _local(st, tz),
            "rx_bytes": _int(pick(d, "rxBytes", "trafficRx", "rxTotalBytes")), "tx_bytes": _int(pick(d, "txBytes", "trafficTx", "txTotalBytes")), "raw": d}


def sync_api(db: Session, cfg: Config, src: DataSource) -> tuple[int, str]:
    c = src.config or {}
    user, pw = vault.cred(db, "vsz.user", c.get("user_env", "VSZ_USER")), vault.cred(db, "vsz.pass", c.get("pass_env", "VSZ_PASS"))
    if not c.get("base_url") or not user or not pw:
        raise RuntimeError("vSZ Base URL / account is not set (Admin → Data Sources → Integrations)")
    rt, tz = root(c["base_url"]), cfg.p("tz_offset_hours", 7)
    with httpx.Client(timeout=c.get("timeout_s", 60), verify=c.get("verify_tls", True)) as cl:
        ver, ticket = login(cl, rt, user, pw)
        try:
            raw, total = fetch_clients(cl, rt, ver, ticket)
            try:
                aps_raw, _ = fetch_clients(cl, rt, ver, ticket, limit=500, path="query/ap")
            except Exception:                      # akun tanpa hak melihat AP: client tetap disinkron, zone dan status AP kosong
                aps_raw = []
            try:                                   # sesi yang sudah selesai (riwayat vSZ, retensinya pendek): disimpan sendiri supaya laporan punya sejarah panjang
                hist_raw, _ = fetch_clients(cl, rt, ver, ticket, limit=1000, max_rows=20000, path="query/historicalclient")
            except Exception:
                hist_raw = []
        finally:
            logout(cl, rt, ver, ticket)
    aps = {a["mac"]: a for a in (to_ap(d, tz) for d in aps_raw) if a}
    rows = {r["mac"]: r for r in (to_row(d, tz, {m: a["zone"] for m, a in aps.items()}) for d in raw) if r}
    if aps:
        ia = insert(WifiAp).values(list(aps.values()))
        db.execute(ia.on_conflict_do_update(index_elements=["mac"], set_={k: getattr(ia.excluded, k) for k in next(iter(aps.values())) if k != "mac"} | {"updated_at": datetime.utcnow()}))
        db.query(WifiAp).filter(~WifiAp.mac.in_(list(aps))).delete(synchronize_session=False)
    now = cfg.now()
    db.merge(WifiStat(at=now, clients=len(rows), users=len({r["username"] for r in rows.values() if r["username"]}), rx_bytes=sum(r["rx_bytes"] or 0 for r in rows.values()),
                      tx_bytes=sum(r["tx_bytes"] or 0 for r in rows.values()), ap_online=sum(1 for a in aps.values() if str(a["status"] or "").lower().startswith("online")), ap_total=len(aps)))
    db.query(WifiStat).filter(WifiStat.at < now - timedelta(days=int(cfg.p("wifi.history_days", 30)))).delete(synchronize_session=False)
    if rows:
        ins = insert(WifiClient).values(list(rows.values()))
        db.execute(ins.on_conflict_do_update(index_elements=["mac"], set_={k: getattr(ins.excluded, k) for k in next(iter(rows.values())) if k != "mac"} | {"updated_at": datetime.utcnow()}))
    db.query(WifiClient).filter(~WifiClient.mac.in_(list(rows))).delete(synchronize_session=False)
    n_ses = save_sessions(db, cfg, rows, aps, hist_raw)
    return len(rows), f"{len(rows)} client WiFi, {len(aps)} AP, {n_ses} sesi tercatat (vSZ API {ver})"


def loc_of(ap_name, zone, to_site):
    """Lokasi dari kode di awal nama AP (mis. SRG-RUANG IT), lalu nama zone, lewat pemetaan kode lokasi dan alias master Lokasi; selain itu nama zone."""
    return to_site((ap_name or "").split("-")[0], zone) or zone


def save_sessions(db: Session, cfg: Config, rows: dict, aps: dict, hist_raw: list) -> int:
    now, tz = cfg.now(), cfg.p("tz_offset_hours", 7)
    cmap = site_resolver(db)
    act = []
    for r in rows.values():
        if not r["started_at"]:
            continue
        raw = r.get("raw") or {}
        act.append({"mac": r["mac"], "started_at": r["started_at"], "ended_at": None, "last_seen": now, "ip": r["ip"], "username": r["username"], "hostname": r["hostname"],
                    "device": raw.get("deviceType"), "ssid": r["ssid"], "ap_mac": r["ap_mac"], "ap_name": r["ap_name"], "zone": r["zone"], "loc": loc_of(r["ap_name"], r["zone"], cmap),
                    "auth": raw.get("authMethod"), "rx_bytes": r["rx_bytes"], "tx_bytes": r["tx_bytes"]})
    done = []
    for d in hist_raw:
        mac, st, en = (pick(d, "clientMac", "mac") or "").upper(), _local(_int(pick(d, "sessionStartTime")), tz), _local(_int(pick(d, "sessionEndTime")), tz)
        if not mac or not st:
            continue
        ap = aps.get((pick(d, "apMac") or "").upper()) or {}
        done.append({"mac": mac, "started_at": st, "ended_at": en or st, "last_seen": en, "ip": pick(d, "ipAddress"), "username": None, "hostname": pick(d, "hostname"),
                     "device": pick(d, "modelName"), "ssid": pick(d, "ssid"), "ap_mac": (pick(d, "apMac") or "").upper() or None, "ap_name": ap.get("name"), "zone": ap.get("zone"),
                     "loc": loc_of(ap.get("name"), ap.get("zone"), cmap), "auth": None, "rx_bytes": _int(pick(d, "rxBytes")), "tx_bytes": _int(pick(d, "txBytes"))})
    done = list({(r["mac"], r["started_at"]): r for r in done}.values())       # satu perintah upsert tidak boleh memuat kunci yang sama dua kali
    act = list({(r["mac"], r["started_at"]): r for r in act}.values())
    keep = lambda ins, cols: {c: func.coalesce(getattr(ins.excluded, c), getattr(WifiSession, c)) for c in cols}
    for part in (done[i:i + 1000] for i in range(0, len(done), 1000)):
        ins = insert(WifiSession).values(part)
        db.execute(ins.on_conflict_do_update(index_elements=["mac", "started_at"], set_={"ended_at": ins.excluded.ended_at, "last_seen": ins.excluded.last_seen, "rx_bytes": ins.excluded.rx_bytes,
                                                                                     "tx_bytes": ins.excluded.tx_bytes, **keep(ins, ["ip", "hostname", "device", "ssid", "ap_mac", "ap_name", "zone", "loc"])}))
    for part in (act[i:i + 1000] for i in range(0, len(act), 1000)):
        ins = insert(WifiSession).values(part)
        db.execute(ins.on_conflict_do_update(index_elements=["mac", "started_at"], set_={"ended_at": None, "last_seen": ins.excluded.last_seen, "rx_bytes": ins.excluded.rx_bytes,
                                                                                     "tx_bytes": ins.excluded.tx_bytes, "ip": ins.excluded.ip, "ssid": ins.excluded.ssid, "ap_mac": ins.excluded.ap_mac,
                                                                                     "ap_name": ins.excluded.ap_name, "zone": ins.excluded.zone, "loc": ins.excluded.loc, "auth": ins.excluded.auth,
                                                                                     **keep(ins, ["username", "hostname", "device"])}))
    db.query(WifiSession).filter(WifiSession.ended_at.is_(None), WifiSession.last_seen < now - timedelta(seconds=30)).update({WifiSession.ended_at: WifiSession.last_seen}, synchronize_session=False)
    db.query(WifiSession).filter(WifiSession.started_at < now - timedelta(days=int(cfg.p("wifi.history_days", 90)))).delete(synchronize_session=False)
    return len(act) + len(done)


def disconnect(db: Session, mode: str, mac: str, ap_mac: str) -> None:
    """Putus sesi client (mode: disconnect | deauth). Memakai akun putus-sesi bila diisi, selain itu akun utama."""
    src = db.get(DataSource, "ruckus")
    c = (src.config if src else None) or {}
    user = vault.cred(db, "vsz.kill_user", c.get("kill_user_env", "VSZ_KILL_USER")) or vault.cred(db, "vsz.user", c.get("user_env", "VSZ_USER"))
    pw = vault.cred(db, "vsz.kill_pass", c.get("kill_pass_env", "VSZ_KILL_PASS")) if vault.cred(db, "vsz.kill_user", c.get("kill_user_env", "VSZ_KILL_USER")) else vault.cred(db, "vsz.pass", c.get("pass_env", "VSZ_PASS"))
    if not c.get("base_url") or not user or not pw:
        raise RuntimeError("vSZ account is not set")
    rt = root(c["base_url"])
    with httpx.Client(timeout=30, verify=c.get("verify_tls", True)) as cl:
        ver, ticket = login(cl, rt, user, pw)
        try:
            r = cl.post(f"{rt}/{ver}/clients/{mode}", params={"serviceTicket": ticket}, json={"mac": mac, "apMac": ap_mac})
        finally:
            logout(cl, rt, ver, ticket)
    if r.status_code == 403:
        raise RuntimeError("The vSZ account may not disconnect clients. Fill in the disconnect account with a role that is allowed to.")
    if r.status_code not in (200, 204):
        raise RuntimeError(f"vSZ menjawab HTTP {r.status_code}: {r.text[:160]}")