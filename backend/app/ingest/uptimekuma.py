"""Uptime Kuma through its Prometheus page (/metrics): the status and response time of every monitor, sampled on each sync and kept per hour (tables kuma_monitor, kuma_hourly).
Credentials: an API key from Uptime Kuma (Settings > API Keys) as the password, with an empty username, or a username and password. Both are stored encrypted in Admin > Data Sources > Integrations."""
import re
from datetime import datetime, timedelta
import httpx
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from .. import vault
from ..models import DataSource, KumaHourly, KumaMonitor
from ..store import Config

SAMPLE = re.compile(r"^(monitor_status|monitor_response_time|monitor_cert_days_remaining)\{(.*)\}\s+(\S+)\s*$")
LABEL = re.compile(r'(\w+)="((?:[^"\\]|\\.)*)"')
STATUS = {0: "Down", 1: "Up", 2: "Pending", 3: "Maintenance"}
KEEP_DAYS = 400


def _unescape(v: str) -> str:
    return v.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")


def parse(text: str) -> dict[str, dict]:
    """Prometheus text -> {name|type: {name, type, url, hostname, port, status, response_ms, cert_days}}."""
    out: dict[str, dict] = {}
    for line in text.splitlines():
        m = SAMPLE.match(line.strip())
        if not m:
            continue
        metric, labels, raw = m.groups()
        lab = {k: _unescape(v) for k, v in LABEL.findall(labels)}
        name = lab.get("monitor_name")
        if not name:
            continue
        try:
            val = float(raw)
        except ValueError:
            continue
        if val != val:                                                  # NaN: Kuma has no value yet
            continue
        clean = lambda k: "" if lab.get(k) in (None, "null", "undefined") else lab[k]
        key = f"{name}|{clean('monitor_type')}"
        o = out.setdefault(key, {"name": name, "type": clean("monitor_type"), "url": clean("monitor_url"), "hostname": clean("monitor_hostname"), "port": clean("monitor_port"), "status": None, "response_ms": None, "cert_days": None})
        if metric == "monitor_status":
            o["status"] = int(val)
        elif metric == "monitor_response_time":
            o["response_ms"] = val if val >= 0 else None
        else:
            o["cert_days"] = int(val)
    return {k: v for k, v in out.items() if v["status"] is not None}


def fetch(base: str, user: str, pw: str, verify: bool = True, timeout: int = 30) -> dict[str, dict]:
    url = base.strip().rstrip("/")
    if not re.match(r"^https?://", url, re.I):
        url = "http://" + url
    with httpx.Client(timeout=timeout, verify=verify, follow_redirects=False) as cl:
        r = cl.get(url + "/metrics", auth=(user or "", pw) if pw else None)
    if r.status_code in (401, 403):
        raise RuntimeError(f"Uptime Kuma rejected the credentials (HTTP {r.status_code}): use an API key as the password with an empty username, or a valid username and password")
    if r.status_code == 404:
        raise RuntimeError("Uptime Kuma has no /metrics page at this address: check the Base URL (no path, for example http://10.1.1.5:3001)")
    r.raise_for_status()
    mons = parse(r.text)
    if not mons:
        raise RuntimeError("The /metrics page has no monitor_status lines: check that the Base URL points to Uptime Kuma")
    return mons


def sync_api(db: Session, cfg: Config, src: DataSource):
    c = src.config or {}
    if not c.get("base_url"):
        raise RuntimeError("Base URL is not filled in (Admin > Data Sources > Integrations > Uptime Kuma)")
    user, pw = vault.cred(db, "kuma.user", c.get("user_env", "KUMA_USER")), vault.cred(db, "kuma.pass", c.get("pass_env", "KUMA_PASS"))
    mons = fetch(c["base_url"], user, pw, c.get("verify_tls", True), int(c.get("timeout_s", 30)))
    now = cfg.now()
    hour = now.replace(minute=0, second=0, microsecond=0)
    for key, m in mons.items():
        row = {"key": key[:240], "name": m["name"][:200], "type": m["type"][:30], "url": m["url"][:300], "hostname": m["hostname"][:200], "port": m["port"][:10], "status": m["status"], "response_ms": m["response_ms"], "cert_days": m["cert_days"], "updated_at": now}
        st = insert(KumaMonitor).values(**row)
        db.execute(st.on_conflict_do_update(index_elements=["key"], set_={k: st.excluded[k] for k in row if k != "key"}))
        if m["status"] == 3:                                            # maintenance: not counted in availability
            continue
        ms_ = m["response_ms"]
        h = insert(KumaHourly).values(monitor_key=key[:240], ts=hour, samples=1, down=int(m["status"] == 0), sum_ms=ms_ or 0, n_ms=1 if ms_ is not None else 0, max_ms=ms_)
        db.execute(h.on_conflict_do_update(index_elements=["monitor_key", "ts"], set_={"samples": KumaHourly.samples + 1, "down": KumaHourly.down + h.excluded.down, "sum_ms": KumaHourly.sum_ms + h.excluded.sum_ms,
                                                                                    "n_ms": KumaHourly.n_ms + h.excluded.n_ms, "max_ms": func.greatest(KumaHourly.max_ms, h.excluded.max_ms)}))
    db.query(KumaMonitor).filter(KumaMonitor.key.not_in(list(mons))).delete(synchronize_session=False)    # removed in Uptime Kuma: the snapshot goes, the hourly history stays
    db.query(KumaHourly).filter(KumaHourly.ts < hour - timedelta(days=KEEP_DAYS)).delete(synchronize_session=False)
    down = sum(1 for m in mons.values() if m["status"] == 0)
    return len(mons), f"{len(mons)} monitors, {down} down"
