"""Panorama per firewall: one row per day and firewall (events by severity and action, traffic), taken from the same dynamic reports as the all-site summary but grouped by device name.
The location of each firewall is looked up in calc/soc_fw.py (name match with an admin override)."""
from datetime import date, datetime, timedelta
import httpx
from sqlalchemy import Text, cast, select
from sqlalchemy.orm import Session
from ..models import Parameter, SocFwDay
from . import panorama_api as PA

SEV = ("critical", "high", "medium", "low", "informational")


def src_rows(cl: httpx.Client, base: str, key: str, d: date, end: datetime | None = None, query: str = "", notes: list | None = None) -> dict:
    """Top internal source networks per firewall for one day: {firewall: {"src": {network: bytes}, "webu": {network: web requests}}}. Panorama's summary logs hold sources per /24 network.
    query keeps only internal sources (the internal range of the SOC parameters)."""
    rng = (d.strftime("%Y/%m/%d 00:00:00"), (end or datetime.combine(d, datetime.max.time())).strftime("%Y/%m/%d %H:%M:%S"))
    out: dict = {}
    for field, typ, vals in (("src", "trsum", ["bytes"]), ("webu", "urlsum", ["repeatcnt"])):
        try:
            for r in PA.run_dynamic(cl, base, key, typ, ["device_name", "src"], vals, "", query, 10000, rng=rng):
                x = out.setdefault(r.get("device_name") or "-", {"src": {}, "webu": {}})[field]
                x[r.get("src") or "-"] = x.get(r.get("src") or "-", 0) + int(float(r.get(vals[0]) or 0))
        except (RuntimeError, httpx.HTTPError) as e:
            if field == "src":
                raise
            if notes is not None:
                notes.append(f"web users {d.isoformat()}: {str(e)[:80]}")
    return {fw: {k: dict(sorted(v.items(), key=lambda kv: -kv[1])[:25]) for k, v in x.items()} for fw, x in out.items()}


def extra_rows(cl: httpx.Client, base: str, key: str, d: date, end: datetime | None = None, notes: list | None = None) -> dict:
    """Internet usage detail per firewall for one day: application categories (bytes), web categories (requests), and the IPs with the most web requests."""
    rng = (d.strftime("%Y/%m/%d 00:00:00"), (end or datetime.combine(d, datetime.max.time())).strftime("%Y/%m/%d %H:%M:%S"))
    out: dict = {}
    top = lambda x, n: dict(sorted(x.items(), key=lambda kv: -kv[1])[:n])
    for field, typ, aggs, vals, dim in (("acat", "trsum", ["device_name", "category-of-app"], ["bytes"], "category-of-app"), ("urlc", "urlsum", ["device_name", "category"], ["repeatcnt"], "category")):
        try:
            for r in PA.run_dynamic(cl, base, key, typ, aggs, vals, "", "", 10000, rng=rng):
                x = out.setdefault(r.get("device_name") or "-", {"acat": {}, "urlc": {}})[field]
                k = r.get(dim) or "-"
                x[k] = x.get(k, 0) + int(float(r.get(vals[0]) or 0))
        except (RuntimeError, httpx.HTTPError) as e:
            if notes is not None:
                notes.append(f"{field} {d.isoformat()}: {str(e)[:80]}")
    return {fw: {k: top(v, 30) for k, v in x.items()} for fw, x in out.items()}


def day_rows(cl: httpx.Client, base: str, key: str, d: date, end: datetime | None = None, query: str = "") -> list[SocFwDay]:
    rng = (d.strftime("%Y/%m/%d 00:00:00"), (end or datetime.combine(d, datetime.max.time())).strftime("%Y/%m/%d %H:%M:%S"))
    th = PA.run_dynamic(cl, base, key, "threat", ["device_name", "severity", "action", "threat-type", "thr_category"], ["repeatcnt"], "", "", 10000, rng=rng)
    tr = PA.run_dynamic(cl, base, key, "trsum", ["device_name", "app"], ["bytes", "sessions"], "", "", 10000, rng=rng)
    new = lambda: {"sev": {}, "act": {}, "typ": {}, "cat": {}, "app": {}, "b": 0, "s": 0}
    by: dict = {}
    for r in th:
        x = by.setdefault(r.get("device_name") or "-", new())
        n = int(float(r.get("repeatcnt") or 0))
        for k, f in (("sev", "severity"), ("act", "action"), ("typ", "threat-type"), ("cat", "thr_category")):
            v = r.get(f) or "-"
            x[k][v] = x[k].get(v, 0) + n
    for r in tr:
        x = by.setdefault(r.get("device_name") or "-", new())
        b = int(float(r.get("bytes") or 0))
        x["b"] += b
        x["s"] += int(float(r.get("sessions") or 0))
        a = r.get("app") or "-"
        x["app"][a] = x["app"].get(a, 0) + b
    src = src_rows(cl, base, key, d, end, query)
    ex = extra_rows(cl, base, key, d, end)
    return [SocFwDay(day=d, fw=fw, src=src.get(fw, {}).get("src", {}), acat=ex.get(fw, {}).get("acat", {}), urlc=ex.get(fw, {}).get("urlc", {}), webu=src.get(fw, {}).get("webu", {}), sev=x["sev"], act=x["act"], typ=x["typ"], cat=x["cat"], app=dict(sorted(x["app"].items(), key=lambda kv: -kv[1])[:40]), bytes=x["b"], sessions=x["s"]) for fw, x in by.items()]


def sync(db: Session, cl: httpx.Client, c: dict, key: str, cur: dict, now: datetime, lower: date, notes: list) -> int:
    """Today so far (replaced on every sync) and the oldest missing days, a few per run. Returns the number of days written."""
    today, yesterday = now.date(), now.date() - timedelta(days=1)
    base = c["base_url"]
    rg = db.get(Parameter, "soc.internal_range")
    q = f"( srcloc eq '{rg.value}' )" if rg and isinstance(rg.value, str) and rg.value else ""      # only internal sources count as users
    have = {d for (d,) in db.execute(select(SocFwDay.day).distinct())}
    tried = set(cur.get("fw_tried", []))
    lower = max(lower, today - timedelta(days=int(c.get("fw_days", 210))))
    db.query(SocFwDay).filter(SocFwDay.day < lower).delete()
    pending, d = [], yesterday                                             # newest days first, so recent data is complete before the older history
    while d >= lower and len(pending) < int(c.get("max_fw_days_per_run", 8)):
        if d not in have and d.isoformat() not in tried:
            pending.append(d)
        d -= timedelta(days=1)
    n = 0
    for d, end in [(x, None) for x in pending] + [(today, now)]:
        try:
            rows = day_rows(cl, base, key, d, end, q)
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
    stried = set(cur.get("fw_src_tried", []))                              # days stored before source IPs were collected: fill only that part
    old = [d for (d,) in db.execute(select(SocFwDay.day).where(cast(SocFwDay.src, Text) == "{}", SocFwDay.bytes > 0, SocFwDay.day < today).distinct().order_by(SocFwDay.day.desc()))]
    for d in [x for x in old if x.isoformat() not in stried][:int(c.get("max_fw_days_per_run", 8))]:
        try:
            src = src_rows(cl, base, key, d, None, q, notes)
            for r in db.scalars(select(SocFwDay).where(SocFwDay.day == d)):
                r.src, r.webu = src.get(r.fw, {}).get("src", {}), src.get(r.fw, {}).get("webu", {})
            db.flush()
            stried.add(d.isoformat())
            n += 1
        except (RuntimeError, httpx.HTTPError) as e:
            notes.append(f"source IPs {d.isoformat()} failed: {str(e)[:100]}")
            break
    cur["fw_src_tried"] = sorted(stried)[-800:]
    dtried = set(cur.get("fw_detail_tried", []))                          # days stored before application and web categories were collected
    lim = today - timedelta(days=int(c.get("fw_detail_days", 45)))
    olds = [d for (d,) in db.execute(select(SocFwDay.day).where(cast(SocFwDay.urlc, Text) == "{}", cast(SocFwDay.acat, Text) == "{}", SocFwDay.bytes > 0, SocFwDay.day < today, SocFwDay.day >= lim).distinct().order_by(SocFwDay.day.desc()))]
    for d in [x for x in olds if x.isoformat() not in dtried][:int(c.get("max_fw_detail_per_run", 3))]:
        try:
            ex = extra_rows(cl, base, key, d, None, notes)
            for r in db.scalars(select(SocFwDay).where(SocFwDay.day == d)):
                e = ex.get(r.fw, {})
                r.acat, r.urlc = e.get("acat", {}), e.get("urlc", {})
            db.flush()
            if ex:                                                       # a day with no answer at all is tried again on a later sync
                dtried.add(d.isoformat())
                n += 1
        except (RuntimeError, httpx.HTTPError) as e:
            notes.append(f"internet detail {d.isoformat()} failed: {str(e)[:100]}")
            break
    cur["fw_detail_tried"] = sorted(dtried)[-800:]
    return n
