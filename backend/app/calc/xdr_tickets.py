"""Which ManageEngine tickets belong to an XDR alert: a ticket counts when its subject names one of the alert's hosts (or the alert id) within a window after the alert."""
from datetime import timedelta
from sqlalchemy import select
from .. import models as M
from ..timeutil import ms


def _tokens(name) -> set:
    n = (name or "").strip().upper()
    out = {n} if len(n) >= 5 else set()
    for p in ("DESKTOP-", "LAPTOP-"):
        if n.startswith(p) and len(n) - len(p) >= 5:
            out.add(n[len(p):])
    return out


def refs(db, alerts, window_days: int = 30) -> dict:
    """alert id -> up to 4 tickets [{id, subject, status, created}] that mention one of its hosts or its id."""
    if not alerts:
        return {}
    lo = min(a.created_at for a in alerts) - timedelta(days=1)
    tks = [(i, s or "", st, c, (s or "").upper()) for i, s, st, c in db.execute(select(M.Ticket.id, M.Ticket.subject, M.Ticket.status, M.Ticket.created_at).where(M.Ticket.created_at >= lo))]
    out = {}
    for a in alerts:
        toks: set = set()
        for e in a.entities or []:
            if e.get("type") == "host":
                toks |= _tokens(e.get("name"))
        hits = []
        for i, s, st, c, su in tks:
            if not (a.created_at - timedelta(days=1) <= c <= a.created_at + timedelta(days=window_days)):
                continue
            if a.id.upper() in su or any(t in su for t in toks):
                hits.append({"id": i, "subject": s[:90], "status": st, "created": ms(c)})
        out[a.id] = hits[:4]
    return out
