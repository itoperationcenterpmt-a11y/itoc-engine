"""Zabbix 7.x lewat JSON-RPC: host group CCTV-* dan OPERASIONAL-* -> status terkini per perangkat (tabel zbx_host).
Kredensial: API token (Admin -> Integrations, terenkripsi). Nama grup, prefix, dan nama trigger "down" semuanya parameter, bukan kode."""
import re
from datetime import datetime, timedelta
from urllib.parse import urlsplit
import httpx
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from .. import vault
from ..models import DataSource, ZbxHost, ZbxLocMap
from ..store import Config

LABEL = {"CCTV-": "CCTV", "OPERASIONAL-": "OPERASIONAL"}


def endpoint(base: str) -> str:
    u = (base or "").strip().rstrip("/")
    return u if u.endswith("api_jsonrpc.php") else u + "/api_jsonrpc.php"


def candidates(base: str) -> list[str]:
    """Alamat API yang dicoba untuk isian Base URL: boleh IP/host saja, dengan atau tanpa skema dan /zabbix."""
    b = (base or "").strip().rstrip("/")
    if b.endswith("api_jsonrpc.php"):
        return [b]
    schemes = [""] if re.match(r"^https?://", b, re.I) else ["https://", "http://"]
    out = []
    for sch in schemes:
        root = sch + b
        paths = [""] if urlsplit(root).path not in ("", "/") else ["/zabbix", ""]
        out += [root + p + "/api_jsonrpc.php" for p in paths]
    return out


def resolve(cl: httpx.Client, base: str) -> str:
    """Pilih alamat pertama yang menjawab apiinfo.version (tanpa token)."""
    errs = []
    for u in candidates(base):
        try:
            rpc(cl, u, "apiinfo.version", {})
            return u
        except Exception as e:
            errs.append(f"{type(e).__name__}: {e}")
    if any("CERTIFICATE_VERIFY_FAILED" in x or "certificate verify" in x.lower() for x in errs):
        raise RuntimeError("Sertifikat HTTPS tidak dipercaya (sertifikat internal). Set Verifikasi TLS = Tidak lalu coba lagi.")
    last = errs[-1][:120] if errs else ""
    raise RuntimeError("API Zabbix tidak ditemukan di " + ", ".join(candidates(base)) + f" ({last})")


def rpc(cl: httpx.Client, url: str, method: str, params, token: str | None = None):
    headers = {"Content-Type": "application/json-rpc"}
    if token:
        headers["Authorization"] = "Bearer " + token
    r = cl.post(url, json={"jsonrpc": "2.0", "method": method, "params": params, "id": 1}, headers=headers)
    r.raise_for_status()
    j = r.json()
    if "error" in j:
        e = j["error"]
        raise RuntimeError(f"Zabbix {method}: {e.get('data') or e.get('message')}")
    return j["result"]


def parse_group(name: str, prefixes: list[str]) -> tuple[str, str]:
    """"CCTV-JNR" -> (CCTV, JNR); "OPERASIONAL-LBR (LEMBAR)" -> (OPERASIONAL, LBR)."""
    for p in prefixes:
        if name.upper().startswith(p.upper()):
            rest = name[len(p):].strip()
            return LABEL.get(p, p.rstrip("-").upper()), re.split(r"[\s(]", rest, maxsplit=1)[0].upper()
    return "", ""


def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def sync_api(db: Session, cfg: Config, src: DataSource) -> tuple[int, str]:
    c = src.config or {}
    token = vault.cred(db, "zabbix.token", c.get("token_env", "ZABBIX_TOKEN"))
    if not c.get("base_url") or not token:
        raise RuntimeError("Base URL / API token Zabbix belum diatur (Admin -> Integrations)")
    prefixes = c.get("group_prefixes") or list(LABEL)
    pats = [p.lower() for p in (c.get("down_patterns") or [])]
    tz = cfg.p("tz_offset_hours", 7)
    iface_down = bool(cfg.p("dev.interface_as_down", False))   # false: interface SNMP/agent tidak tersedia = "degraded", bukan down
    with httpx.Client(timeout=c.get("timeout_s", 60), verify=c.get("verify_tls", True)) as cl:
        url = resolve(cl, c["base_url"])
        groups = rpc(cl, url, "hostgroup.get", {"output": ["groupid", "name"], "search": {"name": prefixes}, "searchByAny": True, "startSearch": True}, token)
        gids = [g["groupid"] for g in groups]
        if not gids:
            raise RuntimeError("Tidak ada host group berawalan " + ", ".join(prefixes))
        hosts = rpc(cl, url, "host.get", {"output": ["hostid", "host", "name", "status", "maintenance_status"], "groupids": gids,
                                          "selectHostGroups": ["groupid", "name"], "selectInterfaces": ["type", "available"]}, token)
        probs = rpc(cl, url, "problem.get", {"output": ["eventid", "name", "severity", "clock", "objectid", "suppressed"], "groupids": gids}, token)
        trig_host: dict[str, set] = {}
        tids = sorted({p["objectid"] for p in probs})
        for part in _chunks(tids, 400):
            for t in rpc(cl, url, "trigger.get", {"output": ["triggerid"], "triggerids": part, "selectHosts": ["hostid"]}, token):
                trig_host[t["triggerid"]] = {h["hostid"] for h in t.get("hosts", [])}
    by_host: dict[str, list] = {}
    for p in probs:
        if pats and not any(x in p["name"].lower() for x in pats):
            continue
        for hid in trig_host.get(p["objectid"], ()):
            by_host.setdefault(hid, []).append(p)
    rows, now = [], datetime.utcnow()
    for h in hosts:
        gnames = sorted(g["name"] for g in h.get("hostgroups", []) if any(g["name"].upper().startswith(p.upper()) for p in prefixes))
        kind, code = parse_group(gnames[0], prefixes) if gnames else ("", "")
        ps = by_host.get(h["hostid"], [])
        live = [p for p in ps if str(p.get("suppressed")) == "0"]
        ifaces = h.get("interfaces", [])
        if h["status"] == "1":
            st, since, prob = "disabled", None, None
        elif live:
            first = min(live, key=lambda p: int(p["clock"]))
            st, since, prob = "down", datetime.utcfromtimestamp(int(first["clock"])) + timedelta(hours=tz), first["name"]
        elif ps or h.get("maintenance_status") == "1":
            st, since, prob = "maintenance", None, (ps[0]["name"] if ps else None)
        elif any(i.get("available") == "2" for i in ifaces):
            st, since, prob = ("down" if iface_down else "degraded"), None, "Interface tidak tersedia"
        else:
            st, since, prob = "up", None, None
        rows.append({"hostid": h["hostid"], "host": h["host"][:255], "name": (h["name"] or h["host"])[:255], "kind": kind, "code": code,
                     "group_name": (gnames[0] if gnames else "")[:255], "groups": gnames, "status": st, "down_since": since, "problem": prob, "updated_at": now})
    for part in _chunks(rows, 500):
        st_ = insert(ZbxHost).values(part)
        db.execute(st_.on_conflict_do_update(index_elements=["hostid"], set_={k: st_.excluded[k] for k in part[0] if k != "hostid"}))
    codes = sorted({r["code"] for r in rows if r["code"]})        # kode lokasi baru muncul di Admin > Master Data > Zabbix: kode ke lokasi
    if codes:
        from ..calc.devices import _alias_map                    # isi awal dari alias lokasi bila sudah cocok; yang diisi Admin tidak ditimpa
        amap = _alias_map(db)
        st_ = insert(ZbxLocMap).values([{"code": c, "site": amap.get(c.lower())} for c in codes])
        db.execute(st_.on_conflict_do_update(index_elements=["code"], set_={"site": func.coalesce(ZbxLocMap.site, st_.excluded.site)}))
    ids = [r["hostid"] for r in rows]
    db.query(ZbxHost).filter(~ZbxHost.hostid.in_(ids)).delete(synchronize_session=False) if ids else db.query(ZbxHost).delete()
    down = sum(1 for r in rows if r["status"] == "down")
    return len(rows), f"{len(rows)} perangkat dari {len(gids)} grup, {down} down"