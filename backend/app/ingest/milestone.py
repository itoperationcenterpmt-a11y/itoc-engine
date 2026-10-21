"""Milestone XProtect lewat RESTful API (API Gateway) dengan login OAuth2 dari IDP bawaan Milestone.
Kredensial: akun Basic user (hanya baca), disimpan terenkripsi di Admin -> Integrations. Base URL = alamat server, mis. https://10.181.3.1"""
import re
from datetime import datetime, timedelta
import httpx
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from .. import vault
from ..models import DataSource, CctvCamera, CctvHardware
from ..store import Config

# daftar yang dicoba saat Test: path REST -> nama tampilan (tidak semua ada di semua versi XProtect)
PROBES = [("cameras", "Kamera"), ("recordingServers", "Recording server"), ("hardware", "Hardware"), ("sites", "Site"), ("cameraGroups", "Grup kamera"), ("alarms", "Alarm"), ("events", "Event")]


def root(base: str) -> str:
    b = (base or "").strip().rstrip("/")
    return b if re.match(r"^https?://", b, re.I) else "https://" + b


def login(cl: httpx.Client, base: str, user: str, pw: str) -> str:
    r = cl.post(root(base) + "/IDP/connect/token", data={"grant_type": "password", "username": user, "password": pw, "client_id": "GrantValidatorClient"},
                headers={"Accept": "application/json"})
    if r.status_code in (400, 401):
        try:
            d = r.json().get("error_description") or r.json().get("error") or ""
        except ValueError:
            d = ""
        raise RuntimeError("Milestone menolak login (HTTP %d): username/password salah atau akun bukan Basic user. %s" % (r.status_code, str(d)[:80]))
    if r.status_code >= 400:
        raise RuntimeError("IDP Milestone HTTP %d" % r.status_code)
    tok = r.json().get("access_token")
    if not tok:
        raise RuntimeError("IDP Milestone tidak mengembalikan access_token")
    return tok


def get(cl: httpx.Client, base: str, token: str, path: str, params: dict | None = None):
    r = cl.get(root(base) + "/API/rest/v1/" + path.lstrip("/"), params=params, headers={"Authorization": "Bearer " + token, "Accept": "application/json"})
    if r.status_code in (401, 403):
        raise RuntimeError("HTTP %d (token ditolak atau akun tidak punya izin)" % r.status_code)
    if r.status_code >= 400:
        raise RuntimeError("HTTP %d" % r.status_code)
    return r.json()


def items(j) -> list:
    """Bentuk jawaban Milestone: {"array": [...]} atau {"data": [...]} atau list langsung."""
    if isinstance(j, list):
        return j
    if isinstance(j, dict):
        for k in ("array", "data", "items", "value"):
            if isinstance(j.get(k), list):
                return j[k]
    return []


def probe(cl: httpx.Client, base: str, token: str) -> list[str]:
    out = []
    for path, label in PROBES:
        try:
            j = get(cl, base, token, path)
            rows = items(j)
            keys = sorted(rows[0].keys())[:16] if rows and isinstance(rows[0], dict) else (sorted(j.keys())[:10] if isinstance(j, dict) else [])
            out.append("%s (/%s): %d data, field: %s." % (label, path, len(rows), ", ".join(keys) or "-"))
        except (RuntimeError, httpx.HTTPError, ValueError) as e:
            out.append("%s (/%s): tidak tersedia (%s)." % (label, path, str(e)[:60]))
    return out


def _ts(s, tz: float = 7):
    """'2026-10-19T10:42:00.717Z' (UTC) -> waktu lokal naif."""
    try:
        return (datetime.fromisoformat(str(s).rstrip("Z")[:19]) + timedelta(hours=tz)) if s and not str(s).startswith("0001") else None
    except ValueError:
        return None


def sync_api(db: Session, cfg: Config, src: DataSource) -> tuple[int, str]:
    """Inventaris hardware dan kamera -> cctv_hardware, cctv_camera. REST XProtect 2022 R2 hanya menyediakan konfigurasi (bukan status online real-time)."""
    c = src.config or {}
    user, pw = vault.cred(db, "ms.user", c.get("user_env", "MS_USER")), vault.cred(db, "ms.pass", c.get("pass_env", "MS_PASS"))
    if not c.get("base_url") or not user or not pw:
        raise RuntimeError("Base URL / akun Milestone belum diatur (Admin -> Integrations)")
    tz = cfg.p("tz_offset_hours", 7)
    with httpx.Client(timeout=c.get("timeout_s", 60), verify=c.get("verify_tls", False), follow_redirects=False) as cl:
        tk = login(cl, c["base_url"], user, pw)
        cams, hws, recs = (items(get(cl, c["base_url"], tk, p)) for p in ("cameras", "hardware", "recordingServers"))
    rec = {r["id"]: r.get("displayName") or r.get("name") for r in recs}
    cnt: dict[str, list[int]] = {}
    crow = []
    for a in cams:
        hid = ((a.get("relations") or {}).get("parent") or {}).get("id")
        n = a.get("displayName") or a.get("name") or ""
        m = re.search(r"\((\d{1,3}(?:\.\d{1,3}){3})\)", n)
        loc = n.split(" - ", 1)[0].strip()[:160] if " - " in n else None
        k = cnt.setdefault(hid or "", [0, 0])
        k[0] += 1
        k[1] += 1 if a.get("enabled", True) else 0
        crow.append({"id": a["id"], "name": n[:300], "location": loc, "ip": m.group(1) if m else None, "channel": a.get("channel"), "hardware_id": hid, "enabled": bool(a.get("enabled", True)),
                     "recording": bool(a.get("recordingEnabled")), "fps": str(a.get("recordingFramerate") or "")[:10] or None, "modified_at": _ts(a.get("lastModified"), tz)})
    hname = {h["id"]: h.get("displayName") or h.get("name") for h in hws}
    for r in crow:
        r["hardware"] = (hname.get(r["hardware_id"]) or "")[:200] or None
    hrow = []
    for h in hws:
        addr = h.get("address") or ""
        hm = re.search(r"//([^/:]+)", addr)
        hrow.append({"id": h["id"], "name": (h.get("displayName") or h.get("name") or "")[:200], "address": addr[:300], "host": hm.group(1)[:120] if hm else None, "model": (h.get("model") or "")[:80],
                     "enabled": bool(h.get("enabled", True)), "recorder": (rec.get(((h.get("relations") or {}).get("parent") or {}).get("id")) or "")[:120] or None,
                     "cameras": cnt.get(h["id"], [0, 0])[0], "cameras_enabled": cnt.get(h["id"], [0, 0])[1], "modified_at": _ts(h.get("lastModified"), tz)})
    now = datetime.utcnow()
    for model, rows in ((CctvHardware, hrow), (CctvCamera, crow)):
        for i in range(0, len(rows), 500):
            ins = insert(model).values(rows[i:i + 500])
            db.execute(ins.on_conflict_do_update(index_elements=["id"], set_={k: getattr(ins.excluded, k) for k in rows[0] if k != "id"} | {"fetched_at": now}))
        db.query(model).filter(model.fetched_at < now - timedelta(seconds=1)).delete(synchronize_session=False)   # yang sudah dihapus di Milestone ikut hilang
    return len(crow), f"{len(crow)} kamera, {len(hrow)} hardware, {len(recs)} recording server"
