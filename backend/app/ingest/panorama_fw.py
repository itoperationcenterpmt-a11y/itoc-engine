"""Panorama per firewall: one row per day and firewall (events by severity and action, traffic), taken from the same dynamic reports as the all-site summary but grouped by device name.
The location of each firewall is looked up in calc/soc_fw.py (name match with an admin override)."""
from datetime import date, datetime, timedelta
import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import SocFwDay
from . import panorama_api as PA

SEV = ("critical", "high", "medium", "low", "informational")


def day_rows(cl: httpx.Client, base: str, key: str, d: date, end: datetime | None = None) -> list[SocFwDay]:
    rng = (d.strftime("%Y/%m/%d 00:00:00"), (end or datetime.combine(d, datetime.max.time())).strftime("%Y/%m/%d %H:%M:%S"))
    th = PA.run_dynamic(cl, base, key, "threat", ["device_name", "severity", "action"], ["repeatcnt"], "", "", 5000, rng=rng)
    tr = PA.run_dynamic(cl, base, key, "trsum", ["device_name"], ["bytes", "sessions"], "", "", 500, rng=rng)
    by: dict = {}
    for r in th:
        x = by.setdefault(r.get("device_name") or "-", {"sev": {}, "act": {}, "b": 0, "s": 0})
        n = int(float(r.get("repeatcnt") or 0))
        x["sev"][r.get("severity") or "-"] = x["sev"].get(r.get("severity") or "-", 0) + n
        x["act"][r.get("action") or "-"] = x["act"].get(r.get("action") or "-", 0) + n
    for r in tr:
        x = by.setdefault(r.get("device_name") or "-", {"sev": {}, "act": {}, "b": 0, "s": 0})
        x["b"] += int(float(r.get("bytes") or 0))
        x["s"] += int(float(r.get("sessions") or 0))
    return [SocFwDay(day=d, fw=fw, sev=x["sev"], act=x["act"], bytes=x["b"], sessions=x["s"]) for fw, x in by.items()]


def sync(db: Session, cl: httpx.Client, c: dict, key: str, cur: dict, now: datetime, lower: date, notes: list) -> int:
    """Today so far (replaced on every sync) and the oldest missing days, a few per run. Returns the number of days written."""
    today, yesterday = now.date(), now.date() - timedelta(days=1)
    base = c["base_url"]
    have = {d for (d,) in db.execute(select(SocFwDay.day).distinct())}
    tried = set(cur.get("fw_tried", []))
    lower = max(lower, today - timedelta(days=int(c.get("fw_days", 60))))
    db.query(SocFwDay).filter(SocFwDay.day < lower).delete()
    pending, d = [], yesterday                                             # newest days first, so recent data is complete before the older history
    while d >= lower and len(pending) < int(c.get("max_fw_days_per_run", 8)):
        if d not in have and d.isoformat() not in tried:
            pending.append(d)
        d -= timedelta(days=1)
    n = 0
    for d, end in [(x, None) for x in pending] + [(today, now)]:
        try:
            rows = day_rows(cl, base, key, d, end)
            db.query(SocFwDay).filter(SocFwDay.day == d).delete()
            db.add_all(rows)
            db.flush()
            n += 1
            if d != today:
                tried.add(d.isoformat())
        except (RuntimeError, httpx.HTTPError) as e:
            notes.append(f"firewall data {d.isoformat()} failed: {str(e)[:100]}")
            break
    cur["fw_tried"] = sorted(tried)[-800:]
    return n
