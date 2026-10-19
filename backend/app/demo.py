"""Data demo (dummy) supaya dashboard bisa langsung dicoba. Jangan dijalankan di database produksi."""
import random
from datetime import datetime, timedelta, date
from sqlalchemy import insert, delete, text
from sqlalchemy.orm import Session
from . import models as M
from .store import load_config
from .calc.common import iso

FN = "Adi Bayu Citra Dimas Eka Fajar Gilang Hendra Indah Joko Kirana Lukman Maya Nanda Okta Putri Rizky Sari Teguh Umar Vina Wahyu Yoga Zahra Arif Bima Dewi Erik Fitri Galih Hana Ilham Jihan Kevin Laras Miko Nia Oscar Prita Rama Sinta Tomi Ulfa Vero Wulan Yusuf Zaki Ayu Bagas Cahya Dian Elang Fikri".split()
LN = "Pratama Saputra Wijaya Nugroho Lestari Hidayat Permana Santoso Kusuma Ramadhan Maharani Setiawan Anggraini".split()
CATS = {"Network": ["LAN", "Wireless", "WAN", "Firewall"], "Desktop Hardware": ["Printer", "Desktop PC", "Laptop", "Monitor"], "Hardware": ["CCTV", "Gate System"],
        "Software": ["Ms Office", "Zoom", "PDF Reader"], "Application": ["PTOS M", "SAP", "Portalsi", "Email"], "General": ["Standby & Monitoring", "Standby Event", "General"],
        "User Administration": ["Password Reset"]}
CW = [30, 22, 8, 9, 12, 10, 4]
HW = [1, 1, 0, 0, 0, 0, 1, 3, 9, 12, 12, 10, 6, 10, 13, 11, 8, 5, 3, 3, 2, 2, 2, 1]
PROF = [.32, .28, .26, .25, .25, .28, .4, .62, .9, 1, 1, .97, .82, .95, 1, .98, .9, .75, .6, .52, .47, .42, .38, .35]


def clear(db: Session) -> dict:
    """Hapus HANYA data demo: tiket bertanda source=demo, sensor PRTG demo (nama "Eth 1/n - ISP Traffic", beserta data jam/harian/kejadiannya),
    batch SOC demo (tabel bercatatan "Data demo."), dua serah terima contoh, dan log sinkron "Demo". Data nyata tidak disentuh."""
    q = lambda sql: db.execute(text(sql)).rowcount
    return {
        "tickets": q("DELETE FROM ticket WHERE source = 'demo'"),
        "sensors": q("DELETE FROM prtg_sensor WHERE name LIKE 'Eth 1/% Traffic'"),
        "soc_batches": q("DELETE FROM soc_batch WHERE EXISTS (SELECT 1 FROM jsonb_array_elements(tables) t WHERE t ->> 'note' = 'Data demo.')"),
        "handover": q("DELETE FROM handover WHERE title LIKE 'Link % masih down, menunggu teknisi ISP' OR title = 'Printer gudang menunggu sparepart'"),
        "sync_log": q("DELETE FROM sync_log WHERE message = 'Demo'"),
    }


ITCARE_JOBS = ["IT Care"] * 4


def itcare_people(unit: str, start: int = 300) -> list:
    """Empat personel dummy IT Care (office hour). Nama diberi tanda (Dummy) supaya mudah diganti dengan data asli di Admin."""
    return [M.Person(name=f"{FN[(start + k * 7) % len(FN)]} {LN[(k * 3) % len(LN)]} (Dummy)", unit=unit, job=job, phone=f"0813-0000-{k + 1:02d}0", is_coordinator=k == 0)
            for k, job in enumerate(ITCARE_JOBS)]


def seed_itcare(db: Session) -> int:
    """Idempotent: menambah 4 personel dummy hanya bila unit IT Care belum punya anggota. Nama unit dari parameter personel (grup kind=office)."""
    cfg = load_config(db)
    grp = next((g for g in (cfg.p("personel") or {}).get("groups", []) if g.get("kind") == "office"), {"unit": "IT Care"})
    if db.query(M.Person).filter_by(unit=grp["unit"]).count():
        return 0
    db.add_all(itcare_people(grp["unit"]))
    return 4


def run(db: Session, seed: int = 20261018):
    R = random.Random(seed)
    cfg = load_config(db)
    for t in (M.PrtgHourly, M.PrtgEvent, M.PrtgSensor, M.Ticket, M.SocDay, M.SocBatch, M.Handover, M.SyncLog, M.Person):
        db.execute(delete(t))
    now = cfg.now()
    start = datetime.fromisoformat(cfg.p("data_start"))
    sites = cfg.sites
    branches = [s for s in sites if s != sites[0]]
    nm = lambda i: f"{FN[i % len(FN)]} {LN[(i * 5) % len(LN)]}"
    phone = lambda i: f"0812-0000-{i + 10:02d}0"
    people, i = [], 0
    for job in ["Supervisor ITOC", "L2 Lead Administrasi", "L1 NOC Lead", "L1 SOC Lead"]:
        people.append(M.Person(name=nm(i), unit="ITOC", job=job, phone=phone(i))); i += 1
    for t in cfg.teams:
        for j, job in enumerate(["ITOC Shift Coordinator", "ITOC NOC Analyst", "ITOC NOC Analyst", "ITOC SOC Analyst", "ITOC SOC Analyst"]):
            people.append(M.Person(name=nm(i), unit="ITOC", job=job, team_code=t["code"], is_coordinator=j == 0, phone=phone(i))); i += 1
    eos = {}
    for b in branches:
        p = M.Person(name=nm(i), unit="EOS", job="EOS", branch=b, phone=phone(i)); i += 1
        people.append(p); eos[b] = p.name
    shared = "IT Operation Center (akun bersama)"
    people.append(M.Person(name=shared, unit="Akun bersama", job="Akun bersama", is_shared=True))
    people += itcare_people(next((g["unit"] for g in (cfg.p("personel") or {}).get("groups", []) if g.get("kind") == "office"), "IT Care"))
    db.add_all(people)
    shifters = [p.name for p in people if p.team_code]
    reqs = [f"PENGGUNA {k + 1:02d} (DUMMY)" for k in range(60)]
    na = cfg.p("sd.unassigned")
    rows, tid = [], 70100
    d = start
    while d <= now:
        n = R.randint(5, 11) if d.weekday() >= 5 else R.randint(24, 44)
        for _ in range(n):
            cat = R.choices(list(CATS), CW)[0]
            sub = R.choice(CATS[cat])
            S = d + timedelta(hours=R.choices(range(24), HW)[0], minutes=R.randint(0, 59))
            if S > now:
                continue
            site = R.choices(sites, [34] + [1 + k % 4 for k in range(len(branches))])[0]
            prio = R.choices(["High", "Medium", "Normal", "Low", na], [8, 22, 30, 34, 6])[0]
            sla = na if R.random() < .18 else {"High": "High SLA", "Medium": "Medium SLA", "Normal": "Medium SLA"}.get(prio, "Low SLA")
            tech = na if R.random() < .03 else shared if R.random() < .12 else eos[site] if site in eos and R.random() < .6 else R.choice(shifters)
            q = R.random()
            T = S if q < .3 else S + timedelta(minutes=R.randint(4, 170)) if q < .72 else S + timedelta(hours=R.randint(3, 22)) if q < .9 else S + timedelta(days=R.randint(1, 6))
            if (now - S).days < 2 and R.random() < .22 or T > now:
                T = None
            st = R.choice(["Open", "In Progress", "Onhold"]) if T is None else "Closed"
            rows.append({"id": str(tid), "mode": R.choice(["On Site", "Chat", "Phone Call", "E-Mail"]), "requester": R.choice(reqs), "site": site, "category": cat,
                         "subcategory": sub, "subject": f"{sub}: permintaan layanan" + (f" — {site[7:]}" if site.startswith("Branch") else ""), "technician": tech,
                         "sla_name": sla, "impact": R.choice(["High", "Medium", "Low"]), "priority": prio, "urgency": R.choice(["Urgent", "High", "Normal", "Low"]),
                         "created_at": S, "resolved_at": T, "onhold_h": 0, "status": st, "desc_empty": R.random() < .15, "source": "demo"})
            tid += 1
        d += timedelta(days=1)
    db.execute(insert(M.Ticket), rows)
    # PRTG
    sid, sensors = 2100, []
    isps = [i["name"] for i in cfg.isps] or ["ISP"]
    for site in sites:
        links = [(isps[0], 500), (isps[1 % len(isps)], 250), (isps[2 % len(isps)], 100)] if site == sites[0] else [(isps[0], R.choice([30, 50, 70])), (isps[1 % len(isps)], R.choice([20, 30, 50]))]
        for li, (isp, cap) in enumerate(links):
            sensors.append(M.PrtgSensor(id=str(sid), name=f"Eth 1/{li + 1} - {isp} Traffic", device=site, capacity_mbps=cap)); sid += 1
    db.add_all(sensors)
    db.flush()
    end = now.replace(minute=0, second=0)
    H = int((end - start).total_seconds() // 3600)
    hourly, events = [], []
    for s in sensors:
        base, ratio = .12 + R.random() * .38, .25 + R.random() * .45
        down = [0.0] * H
        for day in range(H // 24):
            if R.random() < .028:
                st = day * 24 + R.randint(0, 23)
                mins = R.choice([R.randint(3, 15), R.randint(15, 60), R.randint(60, 240)])
                events.append({"sensor_id": s.id, "start_at": start + timedelta(hours=st), "end_at": start + timedelta(hours=st, minutes=mins)})
                left, k = mins * 60, st
                while left > 0 and k < H:
                    down[k] += min(3600, left); left -= 3600; k += 1
        for k in range(H):
            t = start + timedelta(hours=k)
            pf = PROF[t.hour] if t.weekday() < 5 else .35 + PROF[t.hour] * .25
            v = s.capacity_mbps * base * pf * (.82 + R.random() * .36) * (1 - down[k] / 3600)
            hourly.append({"sensor_id": s.id, "ts": t, "in_mbps": v, "out_mbps": v * ratio, "down_s": down[k], "seen": True})
        if len(hourly) > 20000:
            db.execute(insert(M.PrtgHourly), hourly); hourly = []
    if hourly:
        db.execute(insert(M.PrtgHourly), hourly)
    if events:
        db.execute(insert(M.PrtgEvent), events)
    # SOC: dua batch valid
    sev = cfg.p("soc.severities")
    combos = [(sev[4], "spyware", "dns-proxy", "alert", 1, 60000), (sev[3], "spyware", "dns-proxy", "drop", 1, 26000), (sev[2], "spyware", "dns-malware", "sinkhole", 1, 5200),
              (sev[1], "vulnerability", "brute-force", "reset-both", 0, 21000), (sev[0], "vulnerability", "code-execution", "reset-server", 0, 520),
              (sev[1], "vulnerability", "brute-force", "alert", 0, 800), (sev[0], "spyware", "dns-c2", "sinkhole", 1, 180)]
    ucat = [("medium-risk", 0, 21000), ("high-risk", 0, 2400), ("gambling", 1, 28), ("malware", 1, 11), ("phishing", 1, 6)]
    first = (now - timedelta(days=45)).date()
    mid = first + timedelta(days=30)
    for f, t in [(first, mid - timedelta(days=1)), (mid, now.date() - timedelta(days=2))]:
        b = M.SocBatch(file_name=f"SOC_{f:%d%b}-{t:%d%b}.xlsx", uploaded_by=nm(7), uploaded_at=datetime.combine(t + timedelta(days=1), datetime.min.time()) + timedelta(hours=9),
                       date_from=f, date_to=t, rows_read=4000, status="valid", issues=[], kpi={"hosts": R.randint(20, 60)},
                       tables=[{"id": "negara", "t": "Negara sumber serangan teratas", "h": ["Negara", "Total event", "Critical + High", "Jumlah IP"],
                                "r": [[c, R.randint(500, 9000), R.randint(10, 400), R.randint(5, 90)] for c in ["US", "CN", "RU", "NL", "SG"]], "note": "Data demo."}])
        x = f
        while x <= t:
            b.days.append(M.SocDay(day=x, threats={"|".join(map(str, c[:5])): int(c[5] * (.5 + R.random() * 1.1)) for c in combos},
                                   urls={f"{u[0]}|{u[1]}": int(u[2] * (.6 + R.random() * .8)) for u in ucat}, bytes=int(2.9e12 * (.75 + R.random() * .5)), sessions=int(2.3e7 * (.75 + R.random() * .5))))
            x += timedelta(days=1)
        db.add(b)
    # serah terima & log
    clk = cfg.clock
    db.add(M.Handover(created_at=now - timedelta(hours=2), shift_date=clk.duty_date(now), shift_no=clk.shift_of(now.hour), category="NOC", priority="Tinggi", site=branches[5],
                      title=f"Link {isps[0]} {branches[5][7:]} masih down, menunggu teknisi ISP", body="Down sejak pagi, sudah eskalasi ke NOC ISP. EOS sudah cek perangkat sisi site, power normal.",
                      next_action="Pantau 2 jam lagi; bila belum pulih, eskalasi ke account manager.", created_by=people[5].name))
    db.add(M.Handover(created_at=now - timedelta(days=1, hours=3), shift_date=clk.duty_date(now - timedelta(days=1, hours=3)), shift_no=2, category="Service Desk", priority="Rendah",
                      site=branches[-4], title="Printer gudang menunggu sparepart", body="Fuser rusak, sparepart dipesan vendor. Estimasi tiba 2 hari kerja.", created_by=people[10].name))
    for k in range(12):
        db.add(M.SyncLog(source="ManageEngine", at=now - timedelta(minutes=15 * k), ok=True, rows=R.randint(0, 9), ms=R.randint(900, 2400), message="Demo"))
    for key in ("manageengine", "prtg"):
        src = db.get(M.DataSource, key)
        if src:
            src.last_ok_at = now
    return {"tickets": len(rows), "sensors": len(sensors), "events": len(events)}
