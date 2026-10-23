"""Alert XDR (Trend Micro Vision One) dari tabel xdr_alert: ringkasan menurut periode dan severity, termasuk host/akun terdampak, teknik MITRE, insiden, dan umur backlog."""
from datetime import datetime, time as dtime, timedelta
from sqlalchemy import func
from ..models import DataSource, XdrAlert
from ..store import Config
from ..timeutil import ms

SEV = ["critical", "high", "medium", "low"]
RANK = {s: i for i, s in enumerate(SEV)}
MITRE = {"T1003": "OS Credential Dumping", "T1018": "Remote System Discovery", "T1021": "Remote Services", "T1027": "Obfuscated Files or Information", "T1036": "Masquerading",
         "T1053": "Scheduled Task/Job", "T1055": "Process Injection", "T1059": "Command and Scripting Interpreter", "T1070": "Indicator Removal", "T1071": "Application Layer Protocol",
         "T1078": "Valid Accounts", "T1082": "System Information Discovery", "T1105": "Ingress Tool Transfer", "T1110": "Brute Force", "T1112": "Modify Registry",
         "T1190": "Exploit Public-Facing Application", "T1204": "User Execution", "T1204.001": "User Execution: Malicious Link", "T1204.002": "User Execution: Malicious File",
         "T1216": "System Script Proxy Execution", "T1218": "System Binary Proxy Execution", "T1486": "Data Encrypted for Impact", "T1490": "Inhibit System Recovery",
         "T1547": "Boot or Logon Autostart Execution", "T1562": "Impair Defenses", "T1566": "Phishing", "T1569": "System Services", "T1574": "Hijack Execution Flow"}


def _open(r) -> bool:
    return (r.status or "").lower() != "closed" and (r.investigation_status or "").lower() != "closed"


def _top(items, n=10):
    c: dict = {}
    for k in items:
        c[k or "-"] = c.get(k or "-", 0) + 1
    return [{"k": k, "n": v} for k, v in sorted(c.items(), key=lambda x: -x[1])[:n]]


def build(db, cfg: Config, a, b, severity: str = "") -> dict:
    t0, t1 = datetime.combine(a, dtime.min), datetime.combine(b + timedelta(days=1), dtime.min)
    q = db.query(XdrAlert).filter(XdrAlert.created_at >= t0, XdrAlert.created_at < t1)
    if severity:
        q = q.filter(XdrAlert.severity == severity)
    rows = q.order_by(XdrAlert.created_at.desc()).all()
    src = db.get(DataSource, "trendmicro")
    last = db.query(func.max(XdrAlert.fetched_at)).scalar()
    every = (src.interval_min if src else 15) or 15
    now = cfg.now()
    daily, d = {}, a
    while d <= b:
        daily[d] = {x: 0 for x in SEV}
        d += timedelta(days=1)
    imp = {"desktop": 0, "server": 0, "account": 0, "email": 0}
    hosts, accts, techs, incs = {}, {}, {}, {}
    for r in rows:
        if r.severity in SEV and r.created_at.date() in daily:
            daily[r.created_at.date()][r.severity] += 1
        i = r.impact or {}
        imp["desktop"] += int(i.get("desktopCount") or 0)
        imp["server"] += int(i.get("serverCount") or 0)
        imp["account"] += int(i.get("accountCount") or 0)
        imp["email"] += int(i.get("emailAddressCount") or 0)
        for e in r.entities or []:
            tgt = hosts if e.get("type") == "host" else accts if e.get("type") == "account" else None
            if tgt is None or not e.get("name"):
                continue
            x = tgt.setdefault(e["name"], {"k": e["name"], "n": 0, "sev": "low", "ips": [], "open": 0, "last": None})
            x["n"] += 1
            x["open"] += 1 if _open(r) else 0
            if RANK.get(r.severity, 9) < RANK.get(x["sev"], 9):
                x["sev"] = r.severity
            x["ips"] = (x["ips"] + [p for p in (e.get("ips") or []) if p not in x["ips"]])[:3]
            x["last"] = max(x["last"] or 0, ms(r.created_at))
        for t in r.techniques or []:
            techs[t] = techs.get(t, 0) + 1
        if r.incident_id:
            x = incs.setdefault(r.incident_id, {"id": r.incident_id, "n": 0, "sev": "low", "open": 0, "first": r.created_at, "last": r.created_at, "models": []})
            x["n"] += 1
            x["open"] += 1 if _open(r) else 0
            x["first"], x["last"] = min(x["first"], r.created_at), max(x["last"], r.created_at)
            if RANK.get(r.severity, 9) < RANK.get(x["sev"], 9):
                x["sev"] = r.severity
            if r.model and r.model not in x["models"]:
                x["models"].append(r.model)
    scores = [r.score for r in rows if r.score is not None]
    backlog = db.query(XdrAlert).filter(XdrAlert.status.isnot(None)).all()
    bl = [r for r in backlog if _open(r) and r.severity in ("critical", "high")]
    ages = [("< 1 day", 0, 1), ("1 to 3 days", 1, 3), ("3 to 7 days", 3, 7), ("> 7 days", 7, 1e9)]
    aging = [{"k": lb, "n": sum(1 for r in backlog if _open(r) and lo <= (now - r.created_at).total_seconds() / 86400 < hi)} for lb, lo, hi in ages]
    srt = lambda dct, key: sorted(dct.values(), key=key)
    return {"total": len(rows), "open": sum(1 for r in rows if _open(r)), "backlogCH": len(bl), "backlog": sum(1 for r in backlog if _open(r)), "avgScore": round(sum(scores) / len(scores), 1) if scores else None,
            "bySev": [{"k": s, "n": sum(1 for r in rows if r.severity == s)} for s in SEV], "byStatus": _top([r.investigation_status or r.status for r in rows]),
            "byResult": _top([r.investigation_result for r in rows], 6), "byModel": _top([r.model for r in rows], 10), "byProvider": _top([r.provider for r in rows], 6), "impact": imp,
            "hosts": srt(hosts, lambda x: (RANK.get(x["sev"], 9), -x["n"]))[:12], "accounts": srt(accts, lambda x: (RANK.get(x["sev"], 9), -x["n"]))[:12],
            "nHosts": len(hosts), "nAccounts": len(accts), "nIncidents": len(incs),
            "techniques": [{"id": t, "name": MITRE.get(t) or MITRE.get(t.split(".")[0]) or "", "n": n} for t, n in sorted(techs.items(), key=lambda x: -x[1])[:12]],
            "incidents": [{"id": x["id"], "n": x["n"], "sev": x["sev"], "open": x["open"], "first": ms(x["first"]), "last": ms(x["last"]), "models": x["models"][:3]}
                          for x in sorted(incs.values(), key=lambda x: (RANK.get(x["sev"], 9), -x["n"]))[:12]],
            "aging": aging, "daily": [{"date": k.isoformat(), **v} for k, v in daily.items()],
            "list": [{"id": r.id, "model": r.model, "description": r.description, "severity": r.severity, "score": r.score, "status": r.investigation_status or r.status, "result": r.investigation_result,
                      "provider": r.provider, "incident": r.incident_id, "created": ms(r.created_at), "updated": ms(r.updated_at), "link": r.link, "open": _open(r), "impact": r.impact or {},
                      "entities": [{"t": e.get("type"), "n": e.get("name")} for e in (r.entities or [])[:4]], "techniques": (r.techniques or [])[:4], "rules": (r.rules or [])[:2]} for r in rows[:300]],
            "listN": len(rows), "updated": ms(last + (now - datetime.utcnow())) if last else None,
            "stale": bool(last) and (datetime.utcnow() - last).total_seconds() > every * 60 * 3,
            "configured": bool(src and (src.config or {}).get("base_url")), "enabled": bool(src and src.enabled), "error": src.last_error if src else None}