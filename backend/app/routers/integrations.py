"""Admin -> Integrations, API Keys, Email (SMTP), Webhooks. Rahasia disimpan terenkripsi (app/vault.py) dan tidak pernah dikirim balik."""
import hashlib
import secrets
from datetime import datetime, timedelta
from urllib.parse import urlsplit
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from .. import mailer, notify, vault
from ..db import get_db
from ..ingest import zabbix, ruckus, panorama_api
from ..models import ApiKey, DataSource, Role, User, Webhook, ZbxHost
from ..security import require_admin, require_admin_area
from ..store import audit, bump_config

router = APIRouter(prefix="/api/admin", tags=["integrations"], dependencies=[Depends(require_admin_area)])

# kredensial per konektor: (nama di vault, label, kunci config berisi nama env cadangan, nama env bawaan)
CREDS = {
    "manageengine": [("me.token", "API token", "token_env", "ME_AUTHTOKEN")],
    "prtg": [("prtg.user", "Username", "user_env", "PRTG_USER"), ("prtg.passhash", "Passhash", "passhash_env", "PRTG_PASSHASH")],
    "zabbix": [("zabbix.token", "API token", "token_env", "ZABBIX_TOKEN")],
    "panorama": [("pano.user", "Username akun API Panorama", "user_env", "PANO_USER"), ("pano.pass", "Password akun API Panorama", "pass_env", "PANO_PASS")],
    "ruckus": [("vsz.user", "Username API vSZ", "user_env", "VSZ_USER"), ("vsz.pass", "Password API vSZ", "pass_env", "VSZ_PASS"),
              ("vsz.kill_user", "Username akun putus-sesi (opsional, role dengan hak disconnect)", "kill_user_env", "VSZ_KILL_USER"), ("vsz.kill_pass", "Password akun putus-sesi", "kill_pass_env", "VSZ_KILL_PASS")],
}
# isian daftar tambahan per konektor (disimpan di config sumber data): (kunci, label)
EXTRA = {"panorama": [("test_reports", "Nama report Panorama untuk uji (satu per baris, persis seperti di Monitor > Manage Custom Reports)")], "zabbix": [("group_prefixes", "Prefix host group (satu per baris)"), ("down_patterns", "Nama trigger yang berarti perangkat down (satu per baris, cocok sebagian)")]}


def _cred_state(db: Session, src: DataSource):
    import os
    out = []
    for name, label, envkey, envdef in CREDS.get(src.key, []):
        env = (src.config or {}).get(envkey, envdef)
        out.append({"name": name, "label": label, "set": vault.get(db, name) is not None, "env": env, "env_set": bool(os.environ.get(env))})
    return out


def _zbx_stats(db: Session):
    from sqlalchemy import func
    rows = dict(db.query(ZbxHost.status, func.count()).group_by(ZbxHost.status).all())
    return {"total": sum(rows.values()), **{k: rows.get(k, 0) for k in ("up", "down", "maintenance", "disabled")}}


@router.get("/integrations")
def integrations(db: Session = Depends(get_db)):
    rows = []
    for s in db.query(DataSource).order_by(DataSource.key):
        rows.append({"key": s.key, "label": s.label, "mode": s.mode, "enabled": s.enabled, "interval_min": s.interval_min, "tip": s.tip,
                     "base_url": (s.config or {}).get("base_url", ""), "verify_tls": (s.config or {}).get("verify_tls", True),
                     "last_ok_at": s.last_ok_at.isoformat() if s.last_ok_at else None, "last_error": s.last_error,
                     "api_capable": s.key in CREDS, "creds": _cred_state(db, s),
                     "extra": [{"key": k, "label": lb, "value": (s.config or {}).get(k) or []} for k, lb in EXTRA.get(s.key, [])],
                     "stats": _zbx_stats(db) if s.key == "zabbix" else None})
    return {"rows": rows}


class IntegrationIn(BaseModel):
    enabled: bool | None = None
    mode: str | None = None
    interval_min: int | None = None
    base_url: str | None = None
    verify_tls: bool | None = None
    secrets: dict[str, str] = {}
    clear: list[str] = []
    config_lists: dict[str, list[str]] = {}


@router.put("/integrations/{key}")
def integration_set(key: str, body: IntegrationIn, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    s = db.get(DataSource, key)
    if not s:
        raise HTTPException(404, "Sumber tidak ditemukan")
    if body.mode is not None:
        if body.mode not in ("api", "import") or (body.mode == "api" and key not in CREDS):
            raise HTTPException(422, "Mode tidak valid untuk sumber ini")
        s.mode = body.mode
    if body.enabled is not None:
        s.enabled = body.enabled
    if body.interval_min is not None:
        s.interval_min = max(1, min(body.interval_min, 1440))
    cfg = dict(s.config or {})
    if body.base_url is not None:
        cfg["base_url"] = body.base_url.strip().rstrip("/")      # IP/host saja boleh; skema dan /zabbix dicari otomatis saat Test (Zabbix)
    if body.verify_tls is not None:
        cfg["verify_tls"] = body.verify_tls
    for k, vals in body.config_lists.items():
        if k in {e[0] for e in EXTRA.get(key, [])}:
            cfg[k] = [x.strip() for x in vals if x.strip()]
    s.config = cfg
    allowed = {c[0] for c in CREDS.get(key, [])}
    for name, val in body.secrets.items():
        if name in allowed and val.strip():
            vault.put(db, name, val.strip())
    for name in body.clear:
        if name in allowed:
            vault.delete(db, name)
    audit(db, user.username, f"Mengubah integrasi {s.label}" + (" (kredensial diperbarui)" if body.secrets or body.clear else ""))
    db.commit()
    bump_config()
    return {"ok": True}


@router.post("/integrations/{key}/test")
def integration_test(key: str, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    s = db.get(DataSource, key)
    if not s or key not in CREDS:
        raise HTTPException(404, "Sumber ini tidak punya koneksi API")
    c = s.config or {}
    if not c.get("base_url"):
        raise HTTPException(422, "Base URL belum diisi")
    try:
        if key == "zabbix":
            tok = vault.cred(db, "zabbix.token", c.get("token_env", "ZABBIX_TOKEN"))
            if not tok:
                raise HTTPException(422, "API token belum diisi")
            with httpx.Client(timeout=15, verify=c.get("verify_tls", True)) as cl:
                url = zabbix.resolve(cl, c["base_url"])
                ver = zabbix.rpc(cl, url, "apiinfo.version", {})                      # method ini wajib tanpa token
                g = zabbix.rpc(cl, url, "hostgroup.get", {"output": ["groupid"], "search": {"name": c.get("group_prefixes") or ["CCTV-"]}, "searchByAny": True, "startSearch": True}, tok)
            s.config = {**c, "base_url": url[: -len("/api_jsonrpc.php")]}                  # simpan alamat yang terbukti benar
            db.commit()
            return {"ok": True, "msg": f"Terhubung ke Zabbix {ver} di {s.config['base_url']}, token valid, {len(g)} host group cocok prefix"}
        if key == "panorama":
            u, pw = vault.cred(db, "pano.user", c.get("user_env", "PANO_USER")), vault.cred(db, "pano.pass", c.get("pass_env", "PANO_PASS"))
            if not u or not pw:
                raise HTTPException(422, "Username/password API Panorama belum diisi")
            names = c.get("test_reports") or list(((c.get("excel") or {}).get("reports") or {}).values())[:3]
            out = []
            with httpx.Client(timeout=40, verify=c.get("verify_tls", False)) as cl:
                k = panorama_api.keygen(cl, c["base_url"], u, pw)
                out.append("Login berhasil dan key valid.")
                try:
                    lc, lr = panorama_api.run_log(cl, c["base_url"], k, "threat", 3)
                    out.append(f"Log threat: OK ({len(lr)} baris contoh, kolom: {', '.join(lc[:8]) or '-'}).")
                except RuntimeError as e:
                    out.append(f"Log threat: gagal ({e}).")
                for name in names:
                    try:
                        cols, rows = panorama_api.run_report(cl, c["base_url"], k, name, wait_s=60)
                        out.append(f"Report {name}: OK, {len(rows)} baris, kolom: {', '.join(cols[:10]) or '-'}.")
                    except RuntimeError as e:
                        out.append(f"Report {name}: gagal ({e}).")
            return {"ok": True, "msg": " ".join(out)}
        if key == "ruckus":
            u, pw = vault.cred(db, "vsz.user", c.get("user_env", "VSZ_USER")), vault.cred(db, "vsz.pass", c.get("pass_env", "VSZ_PASS"))
            if not u or not pw:
                raise HTTPException(422, "Username/password API vSZ belum diisi")
            with httpx.Client(timeout=20, verify=c.get("verify_tls", True)) as cl:
                rt = ruckus.root(c["base_url"])
                ver, tk = ruckus.login(cl, rt, u, pw)
                try:
                    lst, total = ruckus.fetch_clients(cl, rt, ver, tk, limit=1, max_rows=1)
                finally:
                    ruckus.logout(cl, rt, ver, tk)
            return {"ok": True, "msg": f"Terhubung ke vSZ (API {ver}), login valid, {total} client WiFi aktif"}
        if key == "manageengine":
            tok = vault.cred(db, "me.token", c.get("token_env", "ME_AUTHTOKEN"))
            if not tok:
                raise HTTPException(422, "API token belum diisi")
            r = httpx.get(c["base_url"] + "/api/v3/requests", params={"input_data": '{"list_info":{"row_count":1}}'},
                          headers={"authtoken": tok, "Accept": "application/vnd.manageengine.sdp.v3+json"}, timeout=15, verify=c.get("verify_tls", True))
        else:
            u, p = vault.cred(db, "prtg.user", c.get("user_env", "PRTG_USER")), vault.cred(db, "prtg.passhash", c.get("passhash_env", "PRTG_PASSHASH"))
            if not u:
                raise HTTPException(422, "Username PRTG belum diisi")
            r = httpx.get(c["base_url"] + "/api/table.json", params={"content": "sensors", "columns": "objid", "count": 1, "username": u, "passhash": p},
                          timeout=15, verify=c.get("verify_tls", True))
        r.raise_for_status()
        return {"ok": True, "msg": f"Terhubung (HTTP {r.status_code})"}
    except HTTPException:
        raise
    except httpx.HTTPStatusError as e:
        raise HTTPException(502, f"Server menjawab HTTP {e.response.status_code}")
    except RuntimeError as e:
        raise HTTPException(502, str(e)[:200])
    except Exception as e:
        raise HTTPException(502, "Tidak bisa terhubung: " + str(e)[:160])


# ---------------- API keys ----------------
class KeyIn(BaseModel):
    name: str
    role_key: str
    site: str | None = None
    days: int | None = None


@router.get("/apikeys")
def apikeys(db: Session = Depends(get_db)):
    return {"rows": [{"id": k.id, "name": k.name, "prefix": k.prefix, "role_key": k.role_key, "site": k.site, "by": k.created_by,
                      "created_at": k.created_at.isoformat(), "expires_at": k.expires_at.isoformat() if k.expires_at else None,
                      "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None, "revoked": bool(k.revoked_at)}
                     for k in db.query(ApiKey).order_by(ApiKey.id.desc())]}


@router.post("/apikeys")
def apikey_create(body: KeyIn, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    r = db.get(Role, body.role_key)
    if not body.name.strip() or not r or r.is_admin:
        raise HTTPException(422, "Nama wajib diisi dan role tidak boleh admin")
    raw = "itoc_" + secrets.token_urlsafe(32)
    k = ApiKey(name=body.name.strip(), prefix=raw[:10], key_hash=hashlib.sha256(raw.encode()).hexdigest(), role_key=body.role_key,
               site=body.site or None, created_by=user.username, expires_at=datetime.now() + timedelta(days=body.days) if body.days else None)
    db.add(k)
    audit(db, user.username, f"Membuat API key {k.name} (role {k.role_key})")
    db.commit()
    return {"ok": True, "key": raw}


@router.delete("/apikeys/{kid}")
def apikey_revoke(kid: int, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    k = db.get(ApiKey, kid)
    if not k:
        raise HTTPException(404, "Tidak ditemukan")
    k.revoked_at = datetime.now()
    audit(db, user.username, "Mencabut API key " + k.name)
    db.commit()
    return {"ok": True}


# ---------------- SMTP ----------------
class SmtpIn(BaseModel):
    host: str = ""
    port: int = 587
    security: str = "starttls"
    user: str = ""
    password: str | None = None      # None/"" = tidak diubah
    sender: str = ""
    from_name: str = ""


@router.get("/smtp")
def smtp_get(db: Session = Depends(get_db)):
    c = mailer.config(db)
    return {"host": c.get("host", ""), "port": c.get("port", 587), "security": c.get("security", "starttls"), "user": c.get("user", ""),
            "sender": c.get("from", ""), "from_name": c.get("from_name", ""), "password_set": bool(c.get("password"))}


@router.put("/smtp")
def smtp_set(body: SmtpIn, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    if body.security not in ("starttls", "ssl", "none"):
        raise HTTPException(422, "Keamanan harus starttls, ssl, atau none")
    old = mailer.config(db)
    c = {"host": body.host.strip(), "port": body.port, "security": body.security, "user": body.user.strip(), "from": body.sender.strip(),
         "from_name": body.from_name.strip(), "password": body.password if body.password else old.get("password", "")}
    vault.put_json(db, "smtp", c)
    audit(db, user.username, "Mengubah pengaturan SMTP")
    db.commit()
    return {"ok": True}


class TestMail(BaseModel):
    to: str


@router.post("/smtp/test")
def smtp_test(body: TestMail, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    if "@" not in body.to:
        raise HTTPException(422, "Alamat email tidak valid")
    try:
        mailer.send(db, [body.to.strip()], "Uji email - Dashboard IT Pelindo Multi Terminal", "Pengaturan SMTP berfungsi.")
    except Exception as e:
        raise HTTPException(502, "Gagal mengirim: " + str(e)[:200])
    return {"ok": True, "msg": "Email uji terkirim ke " + body.to}


# ---------------- webhooks ----------------
class HookIn(BaseModel):
    name: str
    kind: str = "generic"
    url: str | None = None           # None/"" saat edit = URL tidak diubah
    events: list[str] = []
    enabled: bool = True


def _mask(db: Session, w: Webhook) -> str:
    u = vault.dec(w.url_enc) or ""
    p = urlsplit(u)
    return f"{p.scheme}://{p.netloc}/…" if p.netloc else "(tidak terbaca)"


def _hook_json(db, w):
    return {"id": w.id, "name": w.name, "kind": w.kind, "url": _mask(db, w), "events": w.events or [], "enabled": w.enabled,
            "last_at": w.last_at.isoformat() if w.last_at else None, "last_status": w.last_status}


@router.get("/webhooks")
def hooks(db: Session = Depends(get_db)):
    return {"rows": [_hook_json(db, w) for w in db.query(Webhook).order_by(Webhook.id)], "events": notify.EVENTS, "kinds": notify.KINDS}


def _check_hook(body: HookIn, new: bool):
    if not body.name.strip() or body.kind not in notify.KINDS:
        raise HTTPException(422, "Nama wajib diisi dan jenis harus dikenal")
    if any(e not in notify.EVENTS or e == "test" for e in body.events):
        raise HTTPException(422, "Peristiwa tidak dikenal")
    if (new or body.url) and not (body.url or "").startswith(("http://", "https://")):
        raise HTTPException(422, "URL harus diawali http:// atau https://")


@router.post("/webhooks")
def hook_create(body: HookIn, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    _check_hook(body, True)
    w = Webhook(name=body.name.strip(), kind=body.kind, url_enc=vault.enc(body.url.strip()), events=body.events, enabled=body.enabled)
    db.add(w)
    audit(db, user.username, "Menambah webhook " + w.name)
    db.commit()
    return {"ok": True}


@router.put("/webhooks/{wid}")
def hook_update(wid: int, body: HookIn, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    w = db.get(Webhook, wid)
    if not w:
        raise HTTPException(404, "Tidak ditemukan")
    _check_hook(body, False)
    w.name, w.kind, w.events, w.enabled = body.name.strip(), body.kind, body.events, body.enabled
    if body.url:
        w.url_enc = vault.enc(body.url.strip())
    audit(db, user.username, "Mengubah webhook " + w.name)
    db.commit()
    return {"ok": True}


@router.delete("/webhooks/{wid}")
def hook_delete(wid: int, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    w = db.get(Webhook, wid)
    if not w:
        raise HTTPException(404, "Tidak ditemukan")
    audit(db, user.username, "Menghapus webhook " + w.name)
    db.delete(w)
    db.commit()
    return {"ok": True}


@router.post("/webhooks/{wid}/test")
def hook_test(wid: int, db: Session = Depends(get_db), user: User = Depends(require_admin)):
    w = db.get(Webhook, wid)
    url = vault.dec(w.url_enc) if w else None
    if not w or not url:
        raise HTTPException(404, "Webhook tidak ditemukan atau URL tidak terbaca")
    try:
        st = notify.post(w.kind, url, "test", "Pesan uji dari Dashboard IT Pelindo Multi Terminal")
    except Exception as e:
        w.last_status, w.last_at = ("Gagal: " + str(e))[:190], datetime.utcnow()
        db.commit()
        raise HTTPException(502, "Gagal mengirim: " + str(e)[:160])
    w.last_status, w.last_at = st, datetime.utcnow()
    db.commit()
    return {"ok": True, "msg": "Terkirim (" + st + ")"}