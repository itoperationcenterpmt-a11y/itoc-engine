"""Trend Micro Vision One (XDR) lewat REST API v3: alert Workbench -> tabel xdr_alert (disimpan di database dashboard, tidak dibaca langsung saat halaman dibuka).
Kredensial: API key (Authorization: Bearer), disimpan terenkripsi di Admin -> Integrations. Base URL = alamat regional Vision One."""
import re
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit
import httpx
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from .. import vault
from ..models import DataSource, XdrAlert
from ..store import Config

REGIONS = {"us": "https://api.xdr.trendmicro.com", "eu": "https://api.eu.xdr.trendmicro.com", "jp": "https://api.xdr.trendmicro.co.jp", "sg": "https://api.sg.xdr.trendmicro.com",
           "au": "https://api.au.xdr.trendmicro.com", "in": "https://api.in.xdr.trendmicro.com", "mea": "https://api.mea.xdr.trendmicro.com"}


def root(base: str) -> str:
    b = (base or "").strip().rstrip("/")
    return b if re.match(r"^https?://", b, re.I) else "https://" + b


def get(cl: httpx.Client, url: str, token: str, params: dict | None = None, tries: int = 3) -> dict:
    for i in range(tries):
        r = cl.get(url, params=params, headers={"Authorization": "Bearer " + token, "Accept": "application/json"})
        if r.status_code == 429 and i < tries - 1:
            time.sleep(min(int(r.headers.get("Retry-After", "5") or 5), 30))
            continue
        if r.status_code in (401, 403):
            raise RuntimeError(f"Vision One menolak (HTTP {r.status_code}): API key salah/kedaluwarsa atau role-nya tidak punya izin Workbench")
        if r.status_code >= 400:
            msg = ""
            try:
                e = r.json().get("error") or {}
                msg = f"{e.get('code', '')} {e.get('message', '')}".strip()
            except ValueError:
                msg = r.text[:120]
            raise RuntimeError(f"Vision One HTTP {r.status_code}: {msg[:160]}")
        return r.json()
    raise RuntimeError("Vision One membatasi laju permintaan (429)")


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def pdt(s, tz: float):
    """'2026-10-21T04:35:27Z' (UTC) -> waktu lokal naif."""
    if not s:
        return None
    try:
        d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None
    return (d.astimezone(timezone.utc) + timedelta(hours=tz)).replace(tzinfo=None, microsecond=0)


def fetch_alerts(cl: httpx.Client, base: str, token: str, since: datetime, until: datetime, top: int = 100, max_pages: int = 60) -> list[dict]:
    """Alert yang diperbarui antara since dan until, urut naik. Halaman berikutnya hanya diikuti bila nextLink ada di host yang sama (API key tidak dikirim ke host lain)."""
    host, items = urlsplit(root(base)).netloc, []
    url, params = root(base) + "/v3.0/workbench/alerts", {"startDateTime": iso(since), "endDateTime": iso(until), "dateTimeTarget": "updatedDateTime", "orderBy": "updatedDateTime asc", "top": top}
    for _ in range(max_pages):
        j = get(cl, url, token, params)
        items += j.get("items") or []
        nxt = j.get("nextLink")
        if not nxt or urlsplit(nxt).netloc != host:
            break
        url, params = nxt, None
    return items


def to_row(a: dict, tz: float) -> dict | None:
    if not a.get("id") or not pdt(a.get("createdDateTime"), tz):
        return None
    ind = [{"type": i.get("type"), "value": str(i.get("value") if not isinstance(i.get("value"), (dict, list)) else i.get("value"))[:200]} for i in (a.get("indicators") or [])[:30] if isinstance(i, dict)]
    return {"id": str(a["id"])[:80], "incident_id": a.get("incidentId"), "model": (a.get("model") or "")[:300], "model_type": a.get("modelType"), "severity": (a.get("severity") or "").lower(),
            "score": a.get("score"), "status": a.get("status"), "investigation_status": a.get("investigationStatus"), "provider": a.get("alertProvider"),
            "created_at": pdt(a.get("createdDateTime"), tz), "updated_at": pdt(a.get("updatedDateTime"), tz), "owners": a.get("ownerIds") or [], "impact": a.get("impactScope") or {},
            "indicators": ind, "link": (a.get("workbenchLink") or "")[:600]}


def sync_api(db: Session, cfg: Config, src: DataSource) -> tuple[int, str]:
    c = src.config or {}
    token = vault.cred(db, "tm.token", c.get("token_env", "TMV1_TOKEN"))
    if not c.get("base_url") or not token:
        raise RuntimeError("Base URL / API key Trend Micro belum diatur (Admin -> Integrations)")
    tz, cur = cfg.p("tz_offset_hours", 7), dict(src.cursor or {})
    now = datetime.now(timezone.utc)
    since = datetime.fromisoformat(cur["last_update"]) if cur.get("last_update") else now - timedelta(days=min(int(c.get("backfill_days", 30)), 365))
    with httpx.Client(timeout=c.get("timeout_s", 60), verify=c.get("verify_tls", True), follow_redirects=False) as cl:
        items = fetch_alerts(cl, c["base_url"], token, since, now, int(c.get("page_size", 100)))
    rows = [r for r in (to_row(a, tz) for a in items) if r]
    for i in range(0, len(rows), 500):
        ins = insert(XdrAlert).values(rows[i:i + 500])
        db.execute(ins.on_conflict_do_update(index_elements=["id"], set_={k: getattr(ins.excluded, k) for k in rows[0] if k != "id"} | {"fetched_at": datetime.utcnow()}))
    newest = max((pdt(a.get("updatedDateTime"), 0) for a in items if a.get("updatedDateTime")), default=None)
    cur["last_update"] = ((newest.replace(tzinfo=timezone.utc) if newest else now) - timedelta(minutes=5)).isoformat()
    src.cursor = cur
    return len(rows), f"{len(rows)} alert Workbench baru/berubah"