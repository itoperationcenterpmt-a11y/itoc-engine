"""Ruckus SmartZone (vSZ) lewat Public REST API: client WiFi yang sedang terhubung -> tabel wifi_client.
Login memakai akun API khusus (Admin -> Integrations, terenkripsi). Versi API dideteksi dari apiInfo; bentuk field dipetakan longgar karena beda versi."""
import re
from datetime import datetime, timedelta
from urllib.parse import urlsplit
import httpx
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from .. import vault
from ..models import DataSource, WifiClient
from ..store import Config

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
    err = "tidak ada versi API yang cocok"
    for ver in versions(cl, rt):
        try:
            r = cl.post(f"{rt}/{ver}/serviceTicket", json={"username": user, "password": pw})
        except httpx.HTTPError as e:
            raise RuntimeError("Tidak bisa terhubung ke vSZ: " + str(e)[:150])
        if r.status_code == 404:
            err = f"{ver} tidak didukung"
            continue
        if r.status_code in (401, 403):
            raise RuntimeError("Login vSZ ditolak (username/password salah atau akun tidak punya hak API)")
        r.raise_for_status()
        return ver, r.json()["serviceTicket"]
    raise RuntimeError("API vSZ tidak ditemukan: " + err)


def logout(cl, rt, ver, ticket):
    try:
        cl.delete(f"{rt}/{ver}/serviceTicket", params={"serviceTicket": ticket})
    except Exception:
        pass


def fetch_clients(cl: httpx.Client, rt: str, ver: str, ticket: str, limit: int = 1000, max_rows: int = 20000) -> tuple[list[dict], int]:
    out, page, total = [], 1, 0
    while len(out) < max_rows:
        r = cl.post(f"{rt}/{ver}/query/client", params={"serviceTicket": ticket},
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


def to_row(d: dict, tz: float) -> dict | None:
    mac = (pick(d, "clientMac", "mac", "macAddress") or "").upper()
    if not mac:
        return None
    st = _int(pick(d, "sessionStartTime", "firstConnectTime", "connectedTime", "startTime"))
    return {"mac": mac, "ip": pick(d, "ipAddress", "ip", "clientIp"), "username": pick(d, "userName", "username", "user"),
            "hostname": pick(d, "hostname", "hostName", "deviceName"), "ssid": pick(d, "ssid", "wlanName", "wlan"),
            "ap_name": pick(d, "apName", "ap"), "ap_mac": pick(d, "apMac", "apMacAddress"), "zone": pick(d, "zoneName", "zone"),
            "os": pick(d, "osType", "deviceType", "os", "osVendorType"), "rssi": _int(pick(d, "rssi", "receivedSignalStrength")),
            "vlan": _int(pick(d, "vlan", "vlanId")),
            "started_at": datetime.utcfromtimestamp(st / 1000 if st > 1e11 else st) + timedelta(hours=tz) if st else None,
            "rx_bytes": _int(pick(d, "rxBytes", "trafficRx", "rxTotalBytes")), "tx_bytes": _int(pick(d, "txBytes", "trafficTx", "txTotalBytes")), "raw": d}


def sync_api(db: Session, cfg: Config, src: DataSource) -> tuple[int, str]:
    c = src.config or {}
    user, pw = vault.cred(db, "vsz.user", c.get("user_env", "VSZ_USER")), vault.cred(db, "vsz.pass", c.get("pass_env", "VSZ_PASS"))
    if not c.get("base_url") or not user or not pw:
        raise RuntimeError("Base URL / akun vSZ belum diatur (Admin -> Integrations)")
    rt, tz = root(c["base_url"]), cfg.p("tz_offset_hours", 7)
    with httpx.Client(timeout=c.get("timeout_s", 60), verify=c.get("verify_tls", True)) as cl:
        ver, ticket = login(cl, rt, user, pw)
        try:
            raw, total = fetch_clients(cl, rt, ver, ticket)
        finally:
            logout(cl, rt, ver, ticket)
    rows = {r["mac"]: r for r in (to_row(d, tz) for d in raw) if r}
    if rows:
        ins = insert(WifiClient).values(list(rows.values()))
        db.execute(ins.on_conflict_do_update(index_elements=["mac"], set_={k: getattr(ins.excluded, k) for k in next(iter(rows.values())) if k != "mac"} | {"updated_at": datetime.utcnow()}))
    db.query(WifiClient).filter(~WifiClient.mac.in_(list(rows))).delete(synchronize_session=False)
    return len(rows), f"{len(rows)} client WiFi (vSZ API {ver})"