from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User
from ..security import require_module, effective_site, rate_limit
from ..store import load_config, audit
from .. import report, report_export, views

router = APIRouter(prefix="/api/report", tags=["report"])


@router.get("/{fmt}", dependencies=[Depends(rate_limit("report", 20, 60))])
def export(fmt: str, d_from: date = Query(alias="from"), d_to: date = Query(alias="to"), shift: int = 0, site: str = "", kind: str = "full", preset: str = "standar",
           user: User = Depends(require_module("report")), db: Session = Depends(get_db)):
    """Unduh laporan (xlsx | pdf | pptx). Filter sama dengan dashboard; bagian di luar izin role dibuang; lokasi terkunci menurut role."""
    if fmt not in report_export.RENDER:
        raise HTTPException(404, "Unknown format (xlsx, pdf, pptx)")
    cfg = load_config(db)
    if d_from > d_to:
        d_from, d_to = d_to, d_from
    max_days = cfg.p("ui.max_range_days", 400)
    if (d_to - d_from).days > max_days:
        raise HTTPException(400, f"Rentang maksimal {max_days} hari")
    site = effective_site(user, db) or site
    if kind not in report.DEFAULT_KINDS:
        raise HTTPException(404, "Unknown report type")
    model = report.build(db, cfg, user, views.Filt(d_from, d_to, shift, site, False), kind, preset)
    if kind not in [k["key"] for k in model["kinds"]] or not model["sections"]:
        raise HTTPException(403, "This role may not access any report section")
    try:
        data = report_export.RENDER[fmt](model)
    except ImportError as e:
        raise HTTPException(500, f"A report library is not installed on the server ({e.name}). Rebuild the image.")
    audit(db, user.username, f"Mengunduh laporan {kind} {fmt.upper()} {d_from} – {d_to}" + (f" ({site})" if site else ""))
    db.commit()
    name = f"Laporan_{kind}_{d_from}_{d_to}.{fmt}"
    return Response(content=data, media_type=report_export.MIME[fmt], headers={"Content-Disposition": f'attachment; filename="{name}"'})
