"""SOC — gabung batch impor Panorama per hari (batch terbaru menang) + perhitungan (socCalc,
sheet Perhitungan 3_Dashboard_SOC). Daftar severity, tipe, tindakan, dan tindakan non-blokir dari Config."""
from datetime import date, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from ..models import SocBatch, SocDay
from ..store import Config
from ..timeutil import ms
from .common import iso


def merged(db: Session, d_from: date | None = None, d_to: date | None = None):
    """Kembalikan (days, day_batch, dup, batches). Hari dari batch berstatus failed tidak dipakai."""
    batches = list(db.scalars(select(SocBatch).order_by(SocBatch.uploaded_at)))
    q = select(SocDay).join(SocBatch).where(SocBatch.status != "failed")
    if d_from:
        q = q.where(SocDay.day >= d_from - timedelta(days=1))
    if d_to:
        q = q.where(SocDay.day <= d_to)
    order = {b.id: i for i, b in enumerate(batches)}
    rows = sorted(db.scalars(q), key=lambda r: order.get(r.batch_id, 0))
    days, day_batch, dup = {}, {}, {}
    for r in rows:
        k = iso(r.day)
        if k in days:
            if days[k]["th"] and not r.threats:      # hari kosong dari laporan Top yang rentangnya melebar tidak boleh menimpa data nyata
                continue
            dup[k] = dup.get(k, 1) + 1
        days[k] = {"th": r.threats, "url": r.urls, "b": r.bytes, "s": r.sessions}
        day_batch[k] = r.batch_id
    return days, day_batch, dup, batches


def batch_json(b: SocBatch) -> dict:
    return {"id": b.id, "file": b.file_name, "by": b.uploaded_by, "at": ms(b.uploaded_at), "from": iso(b.date_from), "to": iso(b.date_to),
            "rows": b.rows_read, "skipped": b.rows_skipped, "status": b.status, "issues": b.issues or [], "tables": b.tables or [], "K": b.kpi}


def check(db: Session, cfg: Config, d_from: date, d_to: date, merged_=None):
    days, day_batch, dup, batches = merged_ or merged(db, d_from, d_to)
    today = cfg.now().date()
    out = []
    x = d_from
    while x <= d_to:
        k = iso(x)
        if k in days:
            s = "dup" if k in dup else "ok"
        elif any(b.date_from <= x <= b.date_to and b.rows_skipped for b in batches):
            s = "bad"
        elif x >= today:
            s = "wait"
        else:
            s = "miss"
        out.append({"d": k, "s": s, "b": day_batch.get(k)})
        x += timedelta(days=1)
    return out


def batch_for(batches: list[SocBatch], d_from: date, d_to: date):
    """Batch valid dengan tabel laporan Top yang paling banyak beririsan dengan periode."""
    best, bo = None, 0
    for b in batches:
        if not b.tables or b.status == "failed":
            continue
        o = (min(d_to, b.date_to) - max(d_from, b.date_from)).days + 1
        if o > bo:
            bo, best = o, b
    return best


def calc(days: dict, cfg: Config, d_from: date, d_to: date) -> dict:
    SEV, TTYPE, TACT = cfg.p("soc.severities"), cfg.p("soc.threat_types"), cfg.p("soc.actions")
    nonblk = set(cfg.p("soc.non_block_actions"))
    chs = set(cfg.p("soc.critical_high"))
    other = cfg.p("soc.other_label")
    nd = (d_to - d_from).days + 1
    R = {"days": nd, "daily": []}
    mk = lambda: {"n": 0, "ch": 0, "blk": 0}

    def put(m, k, c, ch, blk):
        o = m.setdefault(k, mk())
        o["n"] += c
        if ch: o["ch"] += c
        if blk: o["blk"] += c
    sev, typ, act, cat, ucat = {}, {}, {}, {}, {}
    unk = {"severity": {}, "type": {}, "action": {}}  # nilai yang muncul di data tetapi belum ada di daftar parameter
    dr = {"int": mk(), "ext": mk()}
    tot = uTot = uBlk = byt = sess = 0
    for i in range(nd):
        k = iso(d_from + timedelta(days=i))
        x = days.get(k) or {"th": {}, "url": {}, "b": 0, "s": 0}
        row = {"date": k, **{s: 0 for s in SEV}, "total": 0, "blk": 0, "url": 0, "urlBlk": 0, "tb": x["b"] / 1e12, "sess": x["s"]}
        for key, c in x["th"].items():
            p = key.split("|")
            ch, blk = p[0] in chs, p[3] not in nonblk
            for kind, val, known in (("severity", p[0], SEV), ("type", p[1], TTYPE), ("action", p[3], TACT)):
                if val and val not in known:
                    unk[kind][val] = unk[kind].get(val, 0) + c
            if p[0] in row: row[p[0]] += c
            row["total"] += c
            if blk: row["blk"] += c
            tot += c
            put(sev, p[0], c, ch, blk); put(typ, p[1], c, ch, blk); put(act, p[3], c, ch, blk); put(cat, p[2] or "(kosong)", c, ch, blk)
            put(dr, "int" if p[4] == "1" else "ext", c, ch, blk)
        for key, c in x["url"].items():
            p = key.split("|")
            o = ucat.setdefault(p[0], {"n": 0, "blk": 0})
            o["n"] += c; row["url"] += c; uTot += c
            if p[1] == "1":
                o["blk"] += c; row["urlBlk"] += c; uBlk += c
        byt += x["b"]; sess += x["s"]
        R["daily"].append(row)

    def line(k, o):
        return {"k": k, "n": o["n"], "pct": o["n"] / tot if tot else 0, "ch": o["ch"], "blk": o["blk"], "alert": o["n"] - o["blk"],
                "blkPct": o["blk"] / o["n"] if o["n"] else None}

    def fixed(lst, m):
        rows = [line(k, m.get(k, mk())) for k in lst]
        if tot - sum(r["n"] for r in rows) > 0:
            o = mk()
            for k, v in m.items():
                if k not in lst:
                    o["n"] += v["n"]; o["ch"] += v["ch"]; o["blk"] += v["blk"]
            rows.append(line(other, o))
        return rows
    R["total"], R["perDay"] = tot, tot / nd if nd else 0
    R["sev"] = [line(k, sev.get(k, mk())) for k in SEV]
    R["sevTotal"] = line("Total", {"n": tot, "ch": 0, "blk": sum(o["blk"] for o in sev.values())})
    chn = sum(sev.get(k, mk())["n"] for k in chs)
    chb = sum(sev.get(k, mk())["blk"] for k in chs)
    R["crit"] = sev.get(SEV[0], mk())["n"]
    R["ch"], R["chBlkPct"], R["chAlert"] = chn, chb / chn if chn else 0, chn - chb
    R["blkPct"] = R["sevTotal"]["blkPct"]
    keep = set(TTYPE[:3])
    R["type"] = [r for r in fixed(TTYPE, typ) if r["n"] > 0 or r["k"] in keep]
    R["action"] = [r for r in fixed(TACT, act) if r["n"] > 0]
    R["cat"] = sorted((line(k, v) for k, v in cat.items()), key=lambda r: -r["n"])
    dl = cfg.p("soc.direction_labels")
    R["dir"] = [line(dl["int"], dr["int"]), line(dl["ext"], dr["ext"])]
    R["internal"], R["internalPct"] = dr["int"]["n"], dr["int"]["n"] / tot if tot else 0
    top = max(R["daily"], key=lambda x: x["total"], default=None)
    R["topDay"] = top if top and top["total"] else None
    R["url"], R["urlBlk"] = uTot, uBlk
    R["urlCat"] = sorted(({"k": k, "n": v["n"], "pct": v["n"] / uTot if uTot else 0, "blk": v["blk"], "alert": v["n"] - v["blk"]} for k, v in ucat.items()),
                         key=lambda r: (-r["blk"], -r["n"]))
    R["tb"], R["sess"] = byt / 1e12, sess
    R["unknown"] = {k: sorted(v.items(), key=lambda kv: -kv[1])[:8] for k, v in unk.items() if v}
    R["hasData"] = any(x["total"] or x["url"] or x["tb"] for x in R["daily"])
    return R
