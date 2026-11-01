from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User
from ..security import require_module, effective_site, rate_limit
from ..store import load_config, audit
from .. import report, report_export, views

router = APIRouter(prefix="/api/report", tags=["report"])


def make_file(db: Session, cfg, user: User, fmt: str, d_from: date, d_to: date, shift: int, site: str, kind: str, preset: str, rgrp: str, rtech: str, risp: str, dry: bool = False):
    """Build one report file for this account: sections outside the role are dropped and the location is locked by the role. Returns (bytes, file name, media type, audit text); dry = check only, no file."""
    if fmt not in report_export.RENDER:
        raise HTTPException(404, "Unknown format (xlsx, pdf, pptx)")
    if d_from > d_to:
        d_from, d_to = d_to, d_from
    max_days = cfg.p("ui.max_range_days", 400)
    if (d_to - d_from).days > max_days:
        raise HTTPException(400, f"The range is at most {max_days} days")
    site = effective_site(user, db) or site
    if kind not in report.DEFAULT_KINDS and not kind.startswith("custom:"):
        raise HTTPException(404, "Unknown report type")
    model = report.build(db, cfg, user, views.Filt(d_from, d_to, shift, site, False, rgrp=rgrp, rtech=rtech, risp=risp), kind, preset)
    if (not kind.startswith("custom:") and kind not in [k["key"] for k in model["kinds"]]) or not model["sections"]:
        raise HTTPException(403, "This role may not access any report section")
    note = f"{kind} {fmt.upper()} {d_from} – {d_to}" + (f" ({site})" if site else "") + (f" [group {rgrp}]" if rgrp else "") + (f" [technician {rtech}]" if rtech else "") + (f" [ISP {risp}]" if risp else "")
    if dry:
        return None, "", "", note
    try:
        data = report_export.RENDER[fmt](model)
    except ImportError as e:
        raise HTTPException(500, f"A report library is not installed on the server ({e.name}). Rebuild the image.")
    tag = ("_" + rgrp.replace(" ", "") if rgrp else "") + ("_" + rtech.replace(" ", "") if rtech else "") + ("_" + risp.replace(" ", "") if risp else "")
    return data, f"Report_{kind.split(':')[0]}{tag}_{d_from}_{d_to}.{fmt}", report_export.MIME[fmt], note


@router.get("/{fmt}", dependencies=[Depends(rate_limit("report", 20, 60))])
def export(fmt: str, d_from: date = Query(alias="from"), d_to: date = Query(alias="to"), shift: int = 0, site: str = "", kind: str = "full", preset: str = "standar", rgrp: str = "", rtech: str = "", risp: str = "",
           user: User = Depends(require_module("report")), db: Session = Depends(get_db)):
    """Download a report (xlsx | pdf | pptx). Same filters as the dashboard; sections outside the role are dropped; the location is locked by the role."""
    data, name, mime, note = make_file(db, load_config(db), user, fmt, d_from, d_to, shift, site, kind, preset, rgrp, rtech, risp)
    audit(db, user.username, "Downloaded report " + note)
    db.commit()
    return Response(content=data, media_type=mime, headers={"Content-Disposition": f'attachment; filename="{name}"'})
