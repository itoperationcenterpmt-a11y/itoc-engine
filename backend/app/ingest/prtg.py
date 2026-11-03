"""PRTG historicdata API → prtg_hourly + prtg_event. Nama channel, satuan, kredensial (nama env),
dan tag sensor dari data_source.config."""
import os
import re
from datetime import datetime, timedelta
import httpx
from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from ..models import PrtgSensor, PrtgHourly, PrtgEvent, DataSource
from ..store import Config


def _num(v):
    if v in (None, ""):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    m = re.search(r"-?[\d.,]+", str(v))
    return float(m[0].replace(",", "")) if m else None


def _dt(v: str) -> datetime | None:
    # "10/14/2026 9:00:00 AM - 10:00:00 AM" → awal jam
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4}) (\d{1,2}):(\d{2}):\d{2}\s*([AP]M)?", v or "")
    if not m:
        return None
    h = int(m[4])
    if m[6]:
        h = h % 12 + (12 if m[6] == "PM" else 0)
    return datetime(int(m[3]), int(m[1]), int(m[2]), h, int(m[5]))


def discover(cl: httpx.Client, db: Session, c: dict, auth: dict) -> int:
    """Daftar sensor dari PRTG (berdasarkan tag). Kapasitas tetap diisi di Admin → Sumber Data → Pemetaan → Sensor dan Kapasitas."""
    if not c.get("sensor_tag"):
        return 0
    r = cl.get("/api/table.json", params={"content": "sensors", "columns": "objid,sensor,device", "filter_tags": c["sensor_tag"], "count": 5000, **auth})
    r.raise_for_status()
    n = 0
    for x in r.json().get("sensors", []):
        st = insert(PrtgSensor).values(id=str(x["objid"]), name=x["sensor"], device=x["device"], active=True)
        db.execute(st.on_conflict_do_update(index_elements=["id"], set_={"name": st.excluded.name, "device": st.excluded.device}))
        n += 1
    return n


def rebuild_events(db: Session, sensor_id: str, a: datetime, b: datetime, min_down_s: float):
    """Kejadian = jam berurutan dengan downtime. Mulai/akhir diperkirakan dari porsi downtime di jam pertama/terakhir."""
    db.execute(delete(PrtgEvent).where(PrtgEvent.sensor_id == sensor_id, PrtgEvent.start_at >= a, PrtgEvent.start_at < b))
    rows = list(db.scalars(select(PrtgHourly).where(PrtgHourly.sensor_id == sensor_id, PrtgHourly.ts >= a, PrtgHourly.ts < b).order_by(PrtgHourly.ts)))
    cur = None
    for r in rows + [None]:
        if r is not None and r.down_s >= min_down_s:
            if cur and r.ts == cur["last"] + timedelta(hours=1):
                cur["last"], cur["end"] = r.ts, r.ts + timedelta(seconds=r.down_s)
            else:
                if cur:
                    db.add(PrtgEvent(sensor_id=sensor_id, start_at=cur["start"], end_at=cur["end"]))
                cur = {"start": r.ts + timedelta(seconds=3600 - r.down_s), "end": r.ts + timedelta(hours=1), "last": r.ts}
        elif cur:
            db.add(PrtgEvent(sensor_id=sensor_id, start_at=cur["start"], end_at=cur["end"]))
            cur = None


def sync_api(db: Session, cfg: Config, src: DataSource) -> tuple[int, str]:
    c = src.config
    from .. import vault
    user, ph = vault.cred(db, "prtg.user", c.get("user_env", "PRTG_USER")), vault.cred(db, "prtg.passhash", c.get("passhash_env", "PRTG_PASSHASH"))
    if not c.get("base_url") or not user:
        raise RuntimeError("PRTG base_url / credentials are not set")
    auth = {"username": user, "passhash": ph}
    ch, factor = c["channels"], float(c.get("mbps_factor", 0.001))  # kbit/s → Mbit/s
    now = cfg.now().replace(minute=0, second=0)
    last = src.cursor.get("last_hour")
    a = datetime.fromisoformat(last) - timedelta(hours=int(c.get("overlap_hours", 2))) if last else now - timedelta(days=int(c.get("backfill_days", 30)))
    fmt = lambda t: t.strftime("%Y-%m-%d-%H-%M-%S")
    n = 0
    with httpx.Client(base_url=c["base_url"], timeout=c.get("timeout_s", 60), verify=c.get("verify_tls", True)) as cl:
        discover(cl, db, c, auth)
        for sen in db.scalars(select(PrtgSensor).where(PrtgSensor.active.is_(True))):
            r = cl.get("/api/historicdata.json", params={"id": sen.id, "avg": 3600, "sdate": fmt(a), "edate": fmt(now), "usecaption": 1, **auth})
            r.raise_for_status()
            vals = []
            for h in r.json().get("histdata", []):
                ts = _dt(h.get("datetime", ""))
                if ts is None or ts >= now:
                    continue
                down_pct = _num(h.get(ch["downtime"])) or 0
                cov = _num(h.get(ch.get("coverage", "coverage")))
                seen = cov is None or cov > 0
                vals.append({"sensor_id": sen.id, "ts": ts, "in_mbps": (_num(h.get(ch["in"])) or 0) * factor if seen else None,
                             "out_mbps": (_num(h.get(ch["out"])) or 0) * factor if seen else None, "down_s": down_pct / 100 * 3600, "seen": seen})
            if vals:
                st = insert(PrtgHourly).values(vals)
                db.execute(st.on_conflict_do_update(index_elements=["sensor_id", "ts"],
                                                    set_={k: st.excluded[k] for k in ["in_mbps", "out_mbps", "down_s", "seen"]}))
                rebuild_events(db, sen.id, a, now, float(c.get("event_min_down_s", 60)))
                n += 1
    src.cursor = {**src.cursor, "last_hour": now.isoformat()}
    return n, "historicdata.json per sensor, 60-minute average"
