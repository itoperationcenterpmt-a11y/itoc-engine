from datetime import datetime, date, timedelta


def total(a):
    return sum(a)


def avg(a):
    return sum(a) / len(a) if a else None


def pctl(a, p):
    if not a:
        return None
    s = sorted(a)
    k = (len(s) - 1) * p
    f = int(k)
    return s[f] + (k - f) * (s[f + 1] - s[f]) if f + 1 < len(s) else s[f]


def median(a):
    return pctl(a, .5)


def r4(x):
    return round(x * 1e4) / 1e4


def iso(x: date | datetime) -> str:
    return (x.date() if isinstance(x, datetime) else x).isoformat()


def top_by(rows, key, w, n=None):
    """Kelompokkan rows menurut key, jumlahkan bobot w; urut menurun (stabil). Sama dengan topBy di Excel/JS."""
    m = {}
    for i, r in enumerate(rows):
        k = key(r)
        if k == "" or k is None:
            continue
        o = m.get(k)
        if o is None:
            o = m[k] = {"k": k, "sum": 0, "first": r, "i": i, "rows": []}
        o["sum"] += w(r)
        o["rows"].append(r)
    a = sorted(m.values(), key=lambda x: (-x["sum"], x["i"]))
    return a[:n] if n else a


def days_between(a: date, b: date):
    return [a + timedelta(days=i) for i in range((b - a).days + 1)]
