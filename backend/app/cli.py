"""python -m app.cli <perintah>
  migrate                    jalankan migrasi Alembic
  seed-config [--overwrite] [--only=modules,roles]  isi master & parameter dari seed/defaults.json (tanpa --overwrite: hanya yang belum ada; --only membatasi tabel yang ditimpa)
  create-user USER NAMA ROLE buat akun (password awal dicetak)
  seed-demo                  isi data dummy untuk mencoba (JANGAN di produksi)
  seed-demo-itcare           tambah 4 personel dummy IT Care bila belum ada (aman diulang)
  clear-demo                 hapus data demo (tiket, sensor PRTG, batch SOC, serah terima, log); data nyata tidak disentuh
  seed-users [--reset]       buat satu akun per role (password123, tanpa wajib ganti password); --reset menimpa akun yang sudah ada. Hanya untuk uji/demo!
  sync SUMBER                jalankan sinkron sekali (manageengine | prtg)
"""
import os
import json
import sys
from pathlib import Path
from sqlalchemy.dialects.postgresql import insert
from .db import session_scope
from . import models as M
from .security import hash_pw, random_pw

SEED = Path(__file__).resolve().parent.parent / "seed" / "defaults.json"
TABLES = [("parameters", M.Parameter, ["key"]), ("modules", M.Module, ["key"]), ("widgets", M.Widget, ["key"]), ("roles", M.Role, ["key"]), ("shifts", M.Shift, ["no"]), ("teams", M.Team, ["code"]),
          ("isps", M.Isp, ["keyword"]), ("sla_targets", M.SlaTarget, ["name"]), ("formulas", M.Formula, ["key"]), ("data_sources", M.DataSource, ["key"])]


def seed_config(overwrite=False, only=None):
    data = json.loads(SEED.read_text(encoding="utf-8"))
    with session_scope() as db:
        for name, model, keys in TABLES:
            if only and name not in only:
                continue
            for row in data.get(name, []):
                if model is M.Isp:
                    if db.query(M.Isp).filter_by(keyword=row["keyword"]).first():
                        continue
                    db.add(M.Isp(**row)); continue
                st = insert(model).values(**row)
                st = st.on_conflict_do_update(index_elements=keys, set_={k: st.excluded[k] for k in row if k not in keys}) if overwrite else st.on_conflict_do_nothing(index_elements=keys)
                db.execute(st)
        for i, s in enumerate([] if only else data.get("sites", [])):
            db.execute(insert(M.Site).values(name=s, kind="ho" if i == 0 else "branch", sort=i).on_conflict_do_nothing(index_elements=["name"]))
    print("Konfigurasi terisi dari", SEED)


# satu akun contoh per role; username = nama role. EOS dikunci ke branch pertama, IT Care otomatis ke kantor pusat (scope role).
DEMO_USERS = [("superadmin", "Super Admin", "superadmin"), ("admin", "Admin Koordinator ITOC", "admin"), ("itoc", "ITOC Shift Analyst", "itoc"),
              ("itcare", "IT Care", "itcare"), ("eos", "EOS Branch", "eos"), ("management", "Management", "manajemen")]


def seed_users(pw="password123", reset=False):
    with session_scope() as db:
        branch = db.query(M.Site).filter_by(kind="branch", active=True).order_by(M.Site.sort).first()
        for username, name, role in DEMO_USERS:
            if not db.get(M.Role, role):
                print(f"- {username}: role {role} belum ada, dilewati"); continue
            site = branch.name if role == "eos" and branch else None
            u = db.query(M.User).filter_by(username=username).first()
            if u is None:
                db.add(M.User(username=username, full_name=name, role_key=role, site=site, password_hash=hash_pw(pw), must_change_pw=False))
                print(f"+ {username} ({role}) dibuat" + (f", lokasi {site}" if site else ""))
            elif reset:
                u.full_name, u.role_key, u.site, u.password_hash, u.must_change_pw, u.active = name, role, site, hash_pw(pw), False, True
                print(f"~ {username} ({role}) direset")
            else:
                print(f"= {username} sudah ada (pakai --reset untuk menimpa)")
    print(f"Password semua akun yang dibuat/direset: {pw}")


def create_user(username, name, role, pw=None):
    pw = pw or random_pw()
    with session_scope() as db:
        db.add(M.User(username=username.lower(), full_name=name, role_key=role, password_hash=hash_pw(pw), must_change_pw=True))
    print(f"Akun {username} dibuat. Password awal: {pw}")


def main(argv):
    if not argv:
        print(__doc__); return
    cmd, args = argv[0], argv[1:]
    if cmd in ("seed-demo", "seed-demo-itcare", "seed-users") and os.environ.get("ITOC_ENV", "").lower() == "production":
        print("Perintah ini hanya untuk uji/demo dan diblokir saat ITOC_ENV=production."); return
    if cmd == "migrate":
        from alembic.config import main as alembic
        alembic(argv=["-c", str(Path(__file__).resolve().parent.parent / "alembic.ini"), "upgrade", "head"])
    elif cmd == "seed-config":
        only = next((a.split("=", 1)[1].split(",") for a in args if a.startswith("--only=")), None)
        seed_config("--overwrite" in args, only)
    elif cmd == "create-user":
        create_user(*args[:4])
    elif cmd == "seed-demo":
        from . import demo
        with session_scope() as db:
            print(demo.run(db))
    elif cmd == "clear-demo":
        from . import demo
        with session_scope() as db:
            print(demo.clear(db))
    elif cmd == "seed-users":
        seed_users(reset="--reset" in args)
    elif cmd == "seed-demo-itcare":
        from . import demo
        with session_scope() as db:
            print(f"{demo.seed_itcare(db)} personel dummy IT Care ditambahkan")
    elif cmd == "sync":
        from .jobs import run_source
        print(run_source(args[0]))
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
