"""ManageEngine ServiceDesk Plus: sinkron API v3 (inkremental) + impor Excel ekspor/1_Dashboard_Service_Desk.
URL, token (nama env), pemetaan field, dan ukuran halaman dari data_source.config."""
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
import httpx
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from ..models import Ticket, DataSource, SyncLog
from ..store import Config
from .excel import Workbook, pdt, s, num

COLS = ["id", "mode", "requester", "site", "category", "subcategory", "subject", "technician", "sla_name", "impact", "priority", "urgency",
        "created_at", "resolved_at", "onhold_h", "status", "desc_empty"]


def upsert(db: Session, rows: list[dict], source: str) -> int:
    if not rows:
        return 0
    for i in range(0, len(rows), 1000):
        chunk = [{**r, "source": source} for r in rows[i:i + 1000]]
        st = insert(Ticket).values(chunk)
        st = st.on_conflict_do_update(index_elements=["id"], set_={c: st.excluded[c] for c in COLS[1:] + ["source"]})
        db.execute(st)
    return len(rows)


def desc_empty(text, patterns: list[str]) -> bool:
    t = re.sub(r"[\n\r ]", "", s(text))
    for p in patterns:
        t = t.replace(p, "")
    return t.replace(".", "") == ""


def onhold(v) -> float:
    if isinstance(v, (int, float)):
        return float(v) * 24
    m = re.match(r"^(\d+):(\d{2})", s(v))
    return int(m[1]) + int(m[2]) / 60 if m else 0.0


# ---------------- impor Excel ----------------
def parse_excel(data: bytes, cfg: Config) -> dict:
    xc = cfg.sources["manageengine"]["config"].get("excel", {})
    head_map: dict = xc["columns"]            # nama kolom ekspor → field
    sheet_pref = xc.get("sheet", "Impor Tiket")
    wb = Workbook(data)
    names = [sheet_pref] if wb.has(sheet_pref) else wb.names
    key_col = xc.get("key_column", "Request ID")
    rows, hi = None, -1
    for n in names:
        r = wb.rows(n)
        hi = next((i for i, x in enumerate(r) if any(s(c) == key_col for c in x)), -1)
        if hi >= 0:
            rows = r
            break
    if rows is None:
        raise ValueError(f"Kolom '{key_col}' tidak ditemukan. Unggah ekspor ManageEngine.")
    head = [s(c) for c in rows[hi]]
    ix = {f: head.index(col) if col in head else -1 for col, f in head_map.items()}
    miss = [col for col, f in head_map.items() if ix[f] < 0 and f not in xc.get("optional", [])]
    if miss:
        raise ValueError("Kolom tidak ditemukan: " + ", ".join(miss))
    pats = cfg.p("sd.description_template")
    out = []
    for r in rows[hi + 1:]:
        g = lambda f: r[ix[f]] if ix.get(f, -1) >= 0 and ix[f] < len(r) else None
        tid = s(g("id"))
        if not tid:
            continue
        out.append({"id": tid, "mode": s(g("mode")), "requester": s(g("requester")), "site": s(g("site")), "category": s(g("category")),
                    "subcategory": s(g("subcategory")), "subject": s(g("subject"))[:200], "technician": s(g("technician")), "sla_name": s(g("sla_name")),
                    "impact": s(g("impact")), "priority": s(g("priority")), "urgency": s(g("urgency")), "created_at": pdt(g("created_at")),
                    "resolved_at": pdt(g("resolved_at")), "onhold_h": round(onhold(g("onhold_h")), 4), "status": s(g("status")),
                    "desc_empty": desc_empty(g("description"), pats) if ix.get("description", -1) >= 0 else False})
    return {"tickets": [t for t in out if t["created_at"] is not None], "skipped": sum(1 for t in out if t["created_at"] is None)}


# ---------------- API v3 ----------------
def _get(obj, path):
    for p in path.split("."):
        if obj is None:
            return None
        obj = obj.get(p) if isinstance(obj, dict) else None
    return obj


def _epoch_local(v, tz):
    if v in (None, "", "-1"):
        return None
    return (datetime.fromtimestamp(int(v) / 1000, tz=timezone.utc) + timedelta(hours=tz)).replace(tzinfo=None)


def sync_api(db: Session, cfg: Config, src: DataSource) -> tuple[int, str]:
    c = src.config
    from .. import vault
    token = vault.cred(db, "me.token", c.get("token_env", "ME_AUTHTOKEN"))
    if not c.get("base_url") or not token:
        raise RuntimeError("base_url / token ManageEngine belum diatur (data_source.config + env)")
    tz = cfg.p("tz_offset_hours", 7)
    fm: dict = c["api_fields"]
    na = cfg.p("sd.unassigned")
    since = int(src.cursor.get("last_updated_ms", 0)) or int((time.time() - c.get("backfill_days", 90) * 86400) * 1000)
    start, size, newest, rows = 1, int(c.get("page_size", 100)), since, []
    headers = {"authtoken": token, "Accept": "application/vnd.manageengine.sdp.v3+json"}
    with httpx.Client(base_url=c["base_url"], headers=headers, timeout=c.get("timeout_s", 30), verify=c.get("verify_tls", True)) as cl:
        while True:
            li = {"list_info": {"row_count": size, "start_index": start, "sort_field": "last_updated_time", "sort_order": "asc",
                                "search_criteria": [{"field": "last_updated_time", "condition": "greater than", "value": str(since)}]}}
            r = cl.get("/api/v3/requests", params={"input_data": json.dumps(li)})
            r.raise_for_status()
            body = r.json()
            for q in body.get("requests", []):
                # daftar tidak memuat kategori, subkategori, urgensi, dampak, mode, dan SLA: ambil detail per request
                d = cl.get(f"/api/v3/requests/{q['id']}")
                d.raise_for_status()
                q = d.json().get("request", q)
                g = lambda f: _get(q, fm[f]) if f in fm else None
                rows.append({"id": str(q["id"]), "mode": s(g("mode")) or na, "requester": s(g("requester")), "site": s(g("site")) or na,
                             "category": s(g("category")) or na, "subcategory": s(g("subcategory")) or na, "subject": s(g("subject"))[:200],
                             "technician": s(g("technician")) or na, "sla_name": s(g("sla_name")) or na, "impact": s(g("impact")) or na,
                             "priority": s(g("priority")) or na, "urgency": s(g("urgency")) or na, "created_at": _epoch_local(g("created_at"), tz),
                             "resolved_at": _epoch_local(g("resolved_at"), tz), "onhold_h": num(g("onhold_ms")) / 36e5 if "onhold_ms" in fm else 0,
                             "status": s(g("status")), "desc_empty": desc_empty(g("description"), cfg.p("sd.description_template"))})
                newest = max(newest, int(_get(q, "last_updated_time.value") or 0))
            if not body.get("list_info", {}).get("has_more_rows"):
                break
            start += size
    n = upsert(db, [x for x in rows if x["created_at"]], "api")
    src.cursor = {**src.cursor, "last_updated_ms": newest}
    return n, "Tiket baru/berubah sejak sinkron sebelumnya"
