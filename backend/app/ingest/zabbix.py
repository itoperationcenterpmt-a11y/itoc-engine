"""Zabbix 7.x lewat JSON-RPC: host group CCTV-* dan OPERASIONAL-* -> status terkini per perangkat (tabel zbx_host).
Kredensial: API token (Admin → Sumber Data → Integrasi, terenkripsi). Nama grup, prefix, dan nama trigger "down" semuanya parameter, bukan kode."""
import re
import time
from datetime import datetime, timedelta
from urllib.parse import urlsplit
import httpx
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from .. import vault
from ..models import DataSource, DevCode, ZbxEvent, ZbxHost, ZbxLocMap, ZbxStat
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
        raise RuntimeError("The HTTPS certificate is not trusted (internal certificate). Set Verify TLS = No and try again.")
    last = errs[-1][:120] if errs else ""
    raise RuntimeError("Zabbix API not found at " + ", ".join(candidates(base)) + f" ({last})")


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


def parse_name(name: str) -> tuple[str, str, str]:
    """Entitas-Cabang-Zona-SubZona-KodePerangkat-Urut, mis. PMT-MDN-LT5-RSVR-NGWF-001 -> (LT5, RSVR, NGWF). Sub zona dan nomor urut boleh tidak ada;
    nama yang tidak berawalan PMT- tidak diuraikan (kode kosong = tidak terklasifikasi)."""
    t = name.strip().split("-")
    if len(t) < 4 or t[0].upper() != "PMT":
        return "", "", ""
    body = t[1:-1] if t[-1].isdigit() else t[1:]
    if len(body) < 2:
        return "", "", ""
    mid = body[1:-1]
    return (mid[0].upper() if mid else ""), "-".join(mid[1:]).upper(), body[-1].upper()


def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def fetch_events(cl, url, token, gids, pats, since_ts, open_ids):
    """Riwayat kejadian down dari Zabbix sendiri (event.get): kejadian baru sejak since_ts, ditambah kejadian yang masih terbuka di database (untuk mengisi waktu pulih)."""
    fields = ["eventid", "objectid", "clock", "r_eventid", "name", "severity"]
    evs = rpc(cl, url, "event.get", {"output": fields, "groupids": gids, "source": 0, "object": 0, "value": 1, "time_from": int(since_ts), "selectHosts": ["hostid"],
                                     "sortfield": ["eventid"], "sortorder": "ASC", "limit": 50000}, token)
    for part in _chunks(open_ids, 400):
        evs += rpc(cl, url, "event.get", {"output": fields, "eventids": part, "source": 0, "object": 0, "selectHosts": ["hostid"]}, token)
    evs = list({e["eventid"]: e for e in evs if not pats or any(x in e["name"].lower() for x in pats)}.values())
    rids = sorted({e["r_eventid"] for e in evs if e.get("r_eventid") not in (None, "", "0")})
    rclock = {}
    for part in _chunks(rids, 500):
        for r in rpc(cl, url, "event.get", {"output": ["eventid", "clock"], "eventids": part}, token):
            rclock[r["eventid"]] = int(r["clock"])
    return evs, rclock


def save_history(db: Session, cfg: Config, src: DataSource, rows: list, evs: list, rclock: dict) -> int:
    tz, now = cfg.p("tz_offset_hours", 7), cfg.now()
    loc = lambda ts: datetime.utcfromtimestamp(int(ts)) + timedelta(hours=tz)
    info = {r["hostid"]: r for r in rows}
    out = []
    for e in evs:
        hid = next((h["hostid"] for h in e.get("hosts", []) if h["hostid"] in info), None)
        if not hid:
            continue
        r = info[hid]
        rc = rclock.get(e.get("r_eventid"))
        out.append({"eventid": e["eventid"], "hostid": hid, "host_name": r["name"], "kind": r["kind"], "code": r["code"], "dev_code": r["dev_code"], "name": e["name"][:255],
                    "start_at": loc(e["clock"]), "end_at": loc(rc) if rc else None})
    for part in _chunks(out, 1000):
        ins = insert(ZbxEvent).values(part)
        db.execute(ins.on_conflict_do_update(index_elements=["eventid"], set_={"end_at": ins.excluded.end_at, "name": ins.excluded.name, "host_name": ins.excluded.host_name,
                                                                              "kind": ins.excluded.kind, "code": ins.excluded.code, "dev_code": ins.excluded.dev_code}))
    hour, cnt = now.replace(minute=0, second=0, microsecond=0), {}
    for r in rows:
        c = cnt.setdefault(r["kind"] or "-", {"total": 0, "up": 0, "down": 0, "degraded": 0, "maintenance": 0})
        c["total"] += 1
        if r["status"] in c:
            c[r["status"]] += 1
    if cnt:
        ins = insert(ZbxStat).values([{"hour": hour, "kind": k, **v} for k, v in cnt.items()])
        db.execute(ins.on_conflict_do_update(index_elements=["hour", "kind"], set_={k: getattr(ins.excluded, k) for k in ("total", "up", "down", "degraded", "maintenance")}))
    db.query(ZbxStat).filter(ZbxStat.hour < now - timedelta(days=400)).delete(synchronize_session=False)
    src.cursor = {**(src.cursor or {}), "ev_from": int(time.time()) - 86400}
    return len(out)


def sync_api(db: Session, cfg: Config, src: DataSource) -> tuple[int, str]:
    c = src.config or {}
    token = vault.cred(db, "zabbix.token", c.get("token_env", "ZABBIX_TOKEN"))
    if not c.get("base_url") or not token:
        raise RuntimeError("Zabbix Base URL / API token is not set (Admin → Data Sources → Integrations)")
    prefixes = c.get("group_prefixes") or list(LABEL)
    pats = [p.lower() for p in (c.get("down_patterns") or [])]
    tz = cfg.p("tz_offset_hours", 7)
    iface_down = bool(cfg.p("dev.interface_as_down", False))   # false: interface SNMP/agent tidak tersedia = "degraded", bukan down
    with httpx.Client(timeout=c.get("timeout_s", 60), verify=c.get("verify_tls", True)) as cl:
        url = resolve(cl, c["base_url"])
        groups = rpc(cl, url, "hostgroup.get", {"output": ["groupid", "name"], "search": {"name": prefixes}, "searchByAny": True, "startSearch": True}, token)
        gids = [g["groupid"] for g in groups]
        if not gids:
            raise RuntimeError("No host group starting with " + ", ".join(prefixes))
        hosts = rpc(cl, url, "host.get", {"output": ["hostid", "host", "name", "status", "maintenance_status"], "groupids": gids,
                                          "selectHostGroups": ["groupid", "name"], "selectInterfaces": ["type", "available", "ip"]}, token)
        probs = rpc(cl, url, "problem.get", {"output": ["eventid", "name", "severity", "clock", "objectid", "suppressed"], "groupids": gids}, token)
        trig_host: dict[str, set] = {}
        tids = sorted({p["objectid"] for p in probs})
        for part in _chunks(tids, 400):
            for t in rpc(cl, url, "trigger.get", {"output": ["triggerid"], "triggerids": part, "selectHosts": ["hostid"]}, token):
                trig_host[t["triggerid"]] = {h["hostid"] for h in t.get("hosts", [])}
        ev_from = int((src.cursor or {}).get("ev_from") or (time.time() - int(cfg.p("dev.history_days", 60)) * 86400))
        try:
            evs, rclock = fetch_events(cl, url, token, gids, pats, ev_from, [e for (e,) in db.query(ZbxEvent.eventid).filter(ZbxEvent.end_at.is_(None))])
        except Exception:                      # riwayat gagal tidak boleh menggagalkan status terkini
            evs, rclock = None, {}
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
            st, since, prob = ("down" if iface_down else "degraded"), None, "Interface unavailable"
        else:
            st, since, prob = "up", None, None
        zone, sub, dcode = parse_name(h["name"] or h["host"])
        rows.append({"hostid": h["hostid"], "host": h["host"][:255], "name": (h["name"] or h["host"])[:255], "kind": kind, "code": code, "zone": zone[:40], "subzone": sub[:80], "dev_code": dcode[:20],
                     "ip": next((i.get("ip") for i in ifaces if i.get("ip")), "")[:45], "group_name": (gnames[0] if gnames else "")[:255], "groups": gnames, "status": st, "down_since": since, "problem": prob, "updated_at": now})
    for part in _chunks(rows, 500):
        st_ = insert(ZbxHost).values(part)
        db.execute(st_.on_conflict_do_update(index_elements=["hostid"], set_={k: st_.excluded[k] for k in part[0] if k != "hostid"}))
    codes = sorted({r["code"] for r in rows if r["code"]})        # kode lokasi baru muncul di Admin > Master Data > Zabbix: kode ke lokasi
    if codes:
        from ..calc.devices import _alias_map                    # isi awal dari alias lokasi bila sudah cocok; yang diisi Admin tidak ditimpa
        amap = _alias_map(db)
        st_ = insert(ZbxLocMap).values([{"code": c, "site": amap.get(c.lower())} for c in codes])
        db.execute(st_.on_conflict_do_update(index_elements=["code"], set_={"site": func.coalesce(ZbxLocMap.site, st_.excluded.site)}))
    dcodes = sorted({r["dev_code"] for r in rows if r["dev_code"]})   # kode perangkat baru muncul di Admin > Master Data > Zabbix: kode perangkat
    if dcodes:
        db.execute(insert(DevCode).values([{"code": c} for c in dcodes]).on_conflict_do_nothing(index_elements=["code"]))
    ids = [r["hostid"] for r in rows]
    db.query(ZbxHost).filter(~ZbxHost.hostid.in_(ids)).delete(synchronize_session=False) if ids else db.query(ZbxHost).delete()
    down = sum(1 for r in rows if r["status"] == "down")
    if evs is not None:                        # problem yang sudah berjalan lebih lama dari jendela riwayat tetap dicatat sebagai kejadian terbuka
        have = {e["eventid"] for e in evs}
        evs = evs + [{"eventid": p["eventid"], "clock": p["clock"], "name": p["name"], "r_eventid": None, "hosts": [{"hostid": h} for h in trig_host.get(p["objectid"], ())]}
                     for p in probs if p["eventid"] not in have and str(p.get("suppressed")) == "0" and (not pats or any(x in p["name"].lower() for x in pats))]
    n_ev = save_history(db, cfg, src, rows, evs, rclock) if evs is not None else None
    return len(rows), f"{len(rows)} devices from {len(gids)} groups, {down} down" + (f", {n_ev} history events" if n_ev is not None else ", history could not be fetched")