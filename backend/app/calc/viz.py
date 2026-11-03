"""Data for the visual widgets (heatmaps, link timeline, location wall). Everything is aggregated from stored data; nothing is invented."""
from datetime import timedelta
from sqlalchemy import extract, func, select
from .. import insight as ENG
from .. import models as M
from ..timeutil import ms


def _grid(rows) -> list[list[float]]:
    g = [[0.0] * 24 for _ in range(7)]
    for dow, hr, v in rows:
        g[int(dow) - 1][int(hr)] = round(float(v or 0), 1)
    return g


def build(db, cfg, a, b, tsite=None) -> dict:
    """a..b are dates (the page filter). Heatmaps cover that range; the timeline always covers the last 7 days."""
    from datetime import datetime
    lo, hi = datetime.combine(a, datetime.min.time()), datetime.combine(b, datetime.min.time()) + timedelta(days=1)
    d1, h1 = extract("isodow", M.Ticket.created_at), extract("hour", M.Ticket.created_at)
    q = select(d1, h1, func.count()).where(M.Ticket.created_at >= lo, M.Ticket.created_at < hi)
    if tsite is not None:
        q = q.where(tsite)
    tk = _grid(db.execute(q.group_by(d1, h1)))
    d2, h2 = extract("isodow", M.PrtgHourly.ts), extract("hour", M.PrtgHourly.ts)
    dn = _grid(db.execute(select(d2, h2, func.sum(M.PrtgHourly.down_s) / 60).where(M.PrtgHourly.ts >= lo, M.PrtgHourly.ts < hi).group_by(d2, h2)))

    now = cfg.now()
    since = now - timedelta(days=7)
    names = ENG._sensor_names(db)
    per: dict = {}
    for sid, s, e in db.execute(select(M.PrtgEvent.sensor_id, M.PrtgEvent.start_at, M.PrtgEvent.end_at).where(M.PrtgEvent.end_at >= since).order_by(M.PrtgEvent.start_at)):
        x = per.setdefault(sid, {"name": names.get(sid, sid), "events": [], "minutes": 0.0})
        s2, e2 = max(s, since), min(e, now)
        if e2 > s2:
            x["events"].append([ms(s2), ms(e2)])
            x["minutes"] += (e2 - s2).total_seconds() / 60
    links = sorted(per.values(), key=lambda r: -r["minutes"])[:10]
    for r in links:
        r["minutes"] = round(r["minutes"])
    wall = [{"site": h["site"], "score": h["score"], "link": h.get("link"), "devices": h.get("devices"), "overdue": h.get("overdue", 0), "devDown": h.get("devDown", 0), "devTotal": h.get("devTotal", 0)} for h in ENG.site_health(db, cfg)]
    return {"tkHeat": tk, "downHeat": dn, "linkEvents": links, "from": ms(since), "to": ms(now), "wall": wall}
