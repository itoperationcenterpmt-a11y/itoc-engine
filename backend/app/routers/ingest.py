import zipfile
from io import BytesIO
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from ..config import settings
from ..db import get_db
from ..models import User, SyncLog
from ..security import require_upload, require_admin, current_user, rate_limit
from ..store import load_config, audit, bump_data
from ..ingest import panorama, manageengine, prtg_pdf
from .. import jobs
from ..calc.soc import batch_json

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


async def _read(f: UploadFile, exts: tuple[str, ...] = (".xlsx",)) -> bytes:
    if not (f.filename or "").lower().endswith(exts):
        raise HTTPException(415, "Only files of type " + ", ".join(exts))
    cap, buf = settings().upload_max_mb * 1024 * 1024, bytearray()
    while chunk := await f.read(1024 * 1024):                   # baca bertahap: berkas raksasa ditolak sebelum memenuhi memori
        buf += chunk
        if len(buf) > cap:
            raise HTTPException(413, f"File is larger than {settings().upload_max_mb} MB")
    return bytes(buf)


async def _bundle(files: list[UploadFile], inner: str) -> list[tuple[str, bytes]]:
    """RAW: boleh banyak file `inner` (.csv / .pdf) sekaligus dan/atau .zip yang berisi file tersebut (mis. 'SOC 011026.zip')."""
    out, total, cap = [], 0, settings().upload_max_mb * 1024 * 1024 * 5
    for f in files:
        name = f.filename or "file"
        data = await _read(f, (inner, ".zip"))
        if name.lower().endswith(".zip"):
            try:
                with zipfile.ZipFile(BytesIO(data)) as z:
                    infos = [i for i in z.infolist() if i.filename.lower().endswith(inner) and not i.is_dir()]
                    if len(infos) > 200 or sum(i.file_size for i in infos) > cap:
                        raise HTTPException(413, f"The contents of {name} are too large or have too many files")
                    for i in infos:
                        out.append((f"{name}/{i.filename.split('/')[-1]}", z.read(i)))
            except zipfile.BadZipFile:
                raise HTTPException(422, f"{name} is not a valid zip file")
        else:
            out.append((name, data))
        total = sum(len(d) for _, d in out)
        if total > cap:
            raise HTTPException(413, "Total file size is too large")
    if not out:
        raise HTTPException(422, f"No {inner} file was found")
    return out


async def _csv_files(files: list[UploadFile]) -> list[tuple[str, bytes]]:
    return await _bundle(files, ".csv")


@router.post("/soc")
async def soc_upload(files: list[UploadFile] = File(...), user: User = Depends(require_upload("soc")), db: Session = Depends(get_db)):
    """Unggah RAW SOC: CSV custom report Panorama (sebelas laporan; dikenali dari header). Satu unggahan = satu batch."""
    cfg = load_config(db)
    csvs = await _csv_files(files)
    label = csvs[0][0] if len(csvs) == 1 else f"{len(csvs)} file CSV Panorama"
    try:
        b = panorama.import_file(db, cfg, b"", label, user.full_name, files=csvs)
    except ValueError as e:
        raise HTTPException(422, str(e))
    db.flush()
    db.add(SyncLog(source=cfg.sources["panorama"]["label"] + " (unggah RAW)", at=cfg.now(), ok=b.status != "failed", rows=b.rows_read, ms=0,
                   message=label + (f" · {b.rows_skipped} baris dilewati" if b.rows_skipped else "")))
    audit(db, user.username, f"Mengunggah RAW SOC {label} ({b.status})")
    db.commit()
    bump_data()
    return batch_json(b)


@router.post("/prtg")
async def prtg_upload(files: list[UploadFile] = File(...), user: User = Depends(require_upload("prtg")), db: Session = Depends(get_db)):
    """Unggah RAW PRTG: PDF laporan harian per sensor (semua Part), banyak file/hari sekaligus atau .zip. Satu baris per sensor per hari."""
    cfg = load_config(db)
    pdfs = await _bundle(files, ".pdf")
    try:
        rows, notes, st = prtg_pdf.read_pdfs(pdfs)
    except ImportError:
        raise HTTPException(500, "The pypdf library is not installed on the server (rebuild the image)")
    if not rows:
        raise HTTPException(422, "No PRTG sensor pages could be read. " + "; ".join(notes[:5]))
    n_sensor = prtg_pdf.save(db, rows)
    days = sorted({r["day"] for r in rows})
    msg = f"{st['files']} PDF · {len(rows)} data sensor-hari · {len(days)} hari ({days[0]} – {days[-1]})" + (f" · {len(notes)} catatan" if notes else "")
    db.add(SyncLog(source=cfg.sources["prtg"]["label"] + " (unggah RAW)", at=cfg.now(), ok=True, rows=len(rows), ms=0, message=msg))
    audit(db, user.username, f"Mengunggah RAW PRTG: {msg}")
    db.commit()
    bump_data()
    return {"files": st["files"], "pages": st["pages"], "rows": len(rows), "sensors": n_sensor, "days": [d.isoformat() for d in days], "notes": notes[:30]}


@router.post("/tickets")
async def tickets_upload(file: UploadFile = File(...), user: User = Depends(require_upload("tickets")), db: Session = Depends(get_db)):
    """Unggah RAW ManageEngine: ekspor daftar request (.xls/.xlsx) apa adanya. Upsert per Request ID, jadi aman diunggah ulang/tumpang-tindih."""
    cfg = load_config(db)
    data = await _read(file, (".xls", ".xlsx"))
    try:
        P = manageengine.parse_excel(data, cfg)
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception as e:  # file rusak / bukan Excel
        raise HTTPException(422, f"The file could not be read as Excel: {e}")
    n = manageengine.upsert(db, P["tickets"], "excel")
    db.add(SyncLog(source=cfg.sources["manageengine"]["label"] + " (unggah RAW)", at=cfg.now(), ok=True, rows=n, ms=0, message=file.filename))
    audit(db, user.username, f"Mengunggah RAW tiket {file.filename} ({n} baris)")
    db.commit()
    bump_data()
    return {"rows": n, "skipped": P["skipped"], "file": file.filename}

SYNC_PERM = {"panorama": "soc", "prtg": "prtg", "manageengine": "tickets"}


@router.post("/sync/{key}", dependencies=[Depends(rate_limit("sync", 10, 60))])
def sync_now(key: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Tarik data sekarang (force). Admin boleh semua sumber; role dengan hak unggah boleh menarik sumbernya (Panorama, PRTG, ManageEngine). Panorama berjalan di latar belakang karena bisa makan beberapa menit."""
    up = user.role.uploads or []
    if not (user.role.is_admin or "*" in up or SYNC_PERM.get(key) in up):
        raise HTTPException(403, "This role may not pull data from this source")
    if key not in jobs.SYNCERS:
        raise HTTPException(404, "Unknown source")
    cfg = load_config(db)
    audit(db, user.username, f"Tarik data sekarang: {key}", None, cfg.p("tz_offset_hours", 7))
    db.commit()
    if key == "panorama":
        import threading
        threading.Thread(target=lambda: jobs.run_source("panorama"), daemon=True).start()
        return {"ok": True, "started": True, "msg": "Panorama pull started in the background. Results appear on this page in a few minutes; new days and the Top report are updated gradually."}
    r = jobs.run_source(key)
    if not r["ok"]:
        raise HTTPException(502, r["msg"])
    return r
