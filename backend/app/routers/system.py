"""Admin → System → Backup & Restore: unduh cadangan database sebagai .sql dan pulihkan dari .sql. Hanya Super Admin.
Restore mengganti seluruh isi database. Sebelum restore, cadangan pengaman dibuat di server; restore berjalan dalam satu transaksi,
jadi bila ada galat seluruh perubahan dibatalkan."""
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from alembic.config import Config as AlembicConfig
from alembic.script import ScriptDirectory
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from ..config import settings
from ..db import get_db, SessionLocal
from ..models import User
from ..security import require_admin
from ..store import audit

router = APIRouter(prefix="/api/admin/system", tags=["system"], dependencies=[Depends(require_admin)])
BASE = Path(__file__).resolve().parents[2]          # folder backend/ (berisi migrations/)
PG_TIMEOUT = 1800


def _pg_env() -> dict:
    """Koneksi PostgreSQL untuk alat klien (pg_dump, psql). Kata sandi lewat variabel lingkungan, tidak di baris perintah."""
    u = make_url(settings().database_url)
    return {**os.environ, "PGHOST": u.host or "localhost", "PGPORT": str(u.port or 5432), "PGUSER": u.username or "",
            "PGPASSWORD": u.password or "", "PGDATABASE": u.database or ""}


def _pg_dump() -> bytes:
    r = subprocess.run(["pg_dump", "--clean", "--if-exists", "--no-owner", "--no-privileges"], env=_pg_env(), capture_output=True, timeout=PG_TIMEOUT)
    if r.returncode:
        raise HTTPException(500, "pg_dump gagal: " + r.stderr.decode(errors="replace")[:300])
    return r.stdout


def _psql_scalar(sql: str) -> str:
    r = subprocess.run(["psql", "-X", "-tA", "-c", sql], env=_pg_env(), capture_output=True, timeout=60)
    return r.stdout.decode().strip() if r.returncode == 0 else ""


def _code_head() -> str:
    cfg = AlembicConfig()
    cfg.set_main_option("script_location", str(BASE / "migrations"))
    return ScriptDirectory.from_config(cfg).get_current_head() or ""


@router.get("/backup")
def backup(user: User = Depends(require_admin), db: Session = Depends(get_db)):
    data = _pg_dump()
    audit(db, user.username, "Unduh cadangan database (.sql)")
    db.commit()
    name = f"itoc-{datetime.now():%Y%m%d-%H%M}.sql"
    return Response(content=data, media_type="application/sql", headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.post("/restore")
async def restore(file: UploadFile = File(...), confirm: str = Form(""), user: User = Depends(require_admin), db: Session = Depends(get_db)):
    if confirm.strip() != "RESTORE":
        raise HTTPException(422, "Ketik RESTORE untuk mengonfirmasi.")
    if not (file.filename or "").lower().endswith(".sql"):
        raise HTTPException(415, "Hanya file .sql")
    data = await file.read()
    if len(data) > settings().restore_max_mb * 1024 * 1024:
        raise HTTPException(413, f"File lebih dari {settings().restore_max_mb} MB")
    if b"PostgreSQL database dump" not in data[:4000]:
        raise HTTPException(422, "Bukan file dump SQL dari pg_dump")

    # cadangan pengaman dulu; tanpa itu restore tidak dijalankan
    bdir = Path(settings().backup_dir)
    try:
        bdir.mkdir(parents=True, exist_ok=True)
        pre = bdir / f"pre-restore-{datetime.now():%Y%m%d-%H%M%S}.sql"
        pre.write_bytes(_pg_dump())
    except OSError as e:
        raise HTTPException(500, f"Folder cadangan tidak bisa ditulis ({e}). Restore dibatalkan demi keamanan.")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".sql")
    tmp.write(data)
    tmp.close()
    db.close()                                    # lepaskan koneksi sesi ini agar DROP TABLE tidak menunggu kunci
    env = _pg_env()
    env["PGOPTIONS"] = "-c lock_timeout=20s"
    try:
        r = subprocess.run(["psql", "-X", "-q", "-v", "ON_ERROR_STOP=1", "--single-transaction", "-f", tmp.name], env=env, capture_output=True, timeout=PG_TIMEOUT)
    finally:
        os.unlink(tmp.name)
    if r.returncode:
        raise HTTPException(500, f"Restore gagal dan dibatalkan, data tidak berubah. Cadangan sebelum restore: {pre.name}. Galat: "
                                 + r.stderr.decode(errors="replace")[-400:])

    db_ver, code_ver = _psql_scalar("select version_num from alembic_version"), _code_head()
    with SessionLocal() as s2:
        audit(s2, user.username, f"Restore database dari {file.filename}")
        s2.commit()
    return {"ok": True, "pre_backup": pre.name, "db_version": db_ver, "code_version": code_ver,
            "warning": "" if db_ver == code_ver else f"Versi migrasi database ({db_ver}) berbeda dengan kode ({code_ver})."}
