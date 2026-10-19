"""RAW PRTG: PDF laporan sensor (PDFium/Chrome, satu halaman = satu sensor, satu laporan = satu hari) → baris per sensor per hari.
Logika pembacaan sama dengan power_query_noc.txt di dashboard Excel (halaman yang memuat 'Uptime Stats' dan 'Report Time Span')."""
import hashlib
import re
from datetime import date, datetime
from io import BytesIO
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from ..models import PrtgSensor, PrtgDaily

_UNIT = {"d": 86400, "h": 3600, "m": 60, "s": 1}
_NUM = r"([\d][\d.,]*)"


def _num(s):
    try:
        return float(s.replace(",", "")) if s else None
    except ValueError:
        return None


def _secs(s: str):
    parts = re.findall(r"(\d+)\s*([dhms])", s or "")
    return float(sum(int(n) * _UNIT[u] for n, u in parts)) if parts else None


def _find(pat: str, t: str, flags=0):
    m = re.search(pat, t, flags)
    return m.group(1) if m else None


def page_row(text: str) -> dict | None:
    """Satu halaman PDF → baris sensor, atau None bila bukan halaman sensor. Kunci 'ok' False = ada angka wajib yang tidak terbaca."""
    t = re.sub(r"\s+", " ", text or "")
    if "Uptime Stats" not in t or "Report Time Span" not in t:
        return None
    head = t.split(" Report Time Span")[0]
    name = re.sub(r"^.*?Report[^:]*:\s*", "", head, count=1).strip() or None
    sid = _find(r"Average\s*-\s*ID\s*(\d+)", t)
    span = re.search(r"Report Time Span:\s*(\d{1,2})/(\d{1,2})/(\d{4})\s+[\d:]+\s*[AP]M\s*-\s*(\d{1,2})/(\d{1,2})/(\d{4})", t)
    day = end = None
    if span:
        mo, d, y, mo2, d2, y2 = map(int, span.groups())
        try:
            day, end = date(y, mo, d), date(y2, mo2, d2)
        except ValueError:
            pass
    dev = _find(r"Probe, Group, Device:\s*(.+?)\s*Uptime Stats", t)
    dev = dev.split(">")[-1].strip() if dev else None
    up_seg = t[t.index("Uptime Stats"):]
    up = _secs(_find(r"Up:\s*[\d.,]+\s*%\s*\[([^\]]*)\]", up_seg))
    down = _secs(_find(r"Down:\s*[\d.,]+\s*%\s*\[([^\]]*)\]", up_seg))
    tail = t.rsplit("Channel", 1)[-1] if "Channel" in t else ""
    ti = re.search(r"Traffic In\s*" + _NUM + r"\s*Mbit/s\s*" + _NUM + r"\s*MB", tail)
    to = re.search(r"Traffic Out\s*" + _NUM + r"\s*Mbit/s\s*" + _NUM + r"\s*MB", tail)
    made = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{1,2}):(\d{2}):(\d{2})\s*([AP]M)?\s*-\s*\d+\s*h\s*Average\s*-\s*ID", t)
    created = None
    if made:
        mo, d, y, h, mi, s, ap = made.groups()
        h = int(h) % 12 + (12 if ap == "PM" else 0) if ap else int(h)
        try:
            created = datetime(int(y), int(mo), int(d), h, int(mi), int(s))
        except ValueError:
            pass
    return {
        "sensor_id": sid, "name": name, "device": dev, "day": day, "end": end, "up_s": up, "down_s": down,
        "req_good": _num(_find(r"Good:\s*[\d.,]+\s*%\s*\[\s*" + _NUM + r"\s*\]", up_seg)), "req_fail": _num(_find(r"Failed:\s*[\d.,]+\s*%\s*\[\s*" + _NUM + r"\s*\]", up_seg)),
        "avg_total": _num(_find(r"Average \(Traffic Total\):\s*" + _NUM + r"\s*Mbit/s", t)), "vol_total_mb": _num(_find(r"Total \(Traffic Total\):\s*" + _NUM + r"\s*MB", t)),
        "avg_in": _num(ti.group(1)) if ti else None, "avg_out": _num(to.group(1)) if to else None,
        "max_mbps": _num(_find(r"Max:\s*" + _NUM + r"\s*Mbit/s", t)), "min_mbps": _num(_find(r"Min:\s*" + _NUM + r"\s*Mbit/s", t)),
        "created_pdf": created, "ok": bool(sid and day and up is not None and down is not None),
    }


def read_pdfs(files: list[tuple[str, bytes]]) -> tuple[list[dict], list[str], dict]:
    """Baca semua PDF → baris unik per (sensor, hari). Duplikat: dipakai laporan dengan waktu pembuatan terbaru."""
    from pypdf import PdfReader
    notes, seen, rows, stats = [], {}, [], {"files": 0, "pages": 0, "sensor_pages": 0}
    for name, data in files:
        digest = hashlib.sha256(data).hexdigest()
        if digest in seen:
            notes.append(f"{name}: isinya sama persis dengan {seen[digest]}, tidak dihitung dua kali")
            continue
        seen[digest] = name
        try:
            rd = PdfReader(BytesIO(data))
            pages = [p.extract_text() or "" for p in rd.pages]
        except Exception as e:
            notes.append(f"{name}: PDF tidak bisa dibaca ({e.__class__.__name__})")
            continue
        stats["files"] += 1
        stats["pages"] += len(pages)
        for i, tx in enumerate(pages, 1):
            r = page_row(tx)
            if r is None:
                continue
            stats["sensor_pages"] += 1
            r["file"] = name
            if not r["ok"]:
                notes.append(f"{name} hal. {i}: angka sensor tidak terbaca (ID/tanggal/Up/Down), halaman dilewati")
                continue
            if r["end"] is None or (r["end"] - r["day"]).days != 1:
                notes.append(f"{name} hal. {i}: periode laporan bukan 1 hari ({r['day']} – {r['end']}), dilewati. Gunakan laporan harian")
                continue
            rows.append(r)
    best = {}
    for r in rows:
        k = (r["sensor_id"], r["day"])
        o = best.get(k)
        if o is None or (r["created_pdf"] or datetime.min) >= (o["created_pdf"] or datetime.min):
            if o is not None:
                notes.append(f"Sensor {r['sensor_id']} tanggal {r['day']} ada di lebih dari satu PDF; dipakai yang terbaru ({r['file']})")
            best[k] = r
        else:
            notes.append(f"Sensor {r['sensor_id']} tanggal {r['day']} ada di lebih dari satu PDF; dipakai yang terbaru ({o['file']})")
    return list(best.values()), notes, stats


def save(db: Session, rows: list[dict]):
    """Upsert sensor (nama/lokasi saja; kapasitas & status aktif tetap milik Admin) lalu ringkasan harian."""
    sensors = {}
    for r in rows:
        sensors[r["sensor_id"]] = r
    for sid, r in sensors.items():
        st = insert(PrtgSensor).values(id=sid, name=(r["name"] or sid)[:160], device=(r["device"] or "–")[:120], active=True)
        db.execute(st.on_conflict_do_update(index_elements=["id"], set_={"name": st.excluded.name, "device": st.excluded.device}))
    cols = ["up_s", "down_s", "req_good", "req_fail", "avg_total", "avg_in", "avg_out", "vol_total_mb", "max_mbps", "min_mbps", "created_pdf"]
    for i in range(0, len(rows), 500):
        vals = [{"sensor_id": r["sensor_id"], "day": r["day"], "source_file": r["file"][:200], **{c: r[c] for c in cols}} for r in rows[i:i + 500]]
        st = insert(PrtgDaily).values(vals)
        db.execute(st.on_conflict_do_update(index_elements=["sensor_id", "day"], set_={c: st.excluded[c] for c in cols + ["source_file"]}))
    return len(sensors)
