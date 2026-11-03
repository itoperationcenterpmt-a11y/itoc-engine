"""Rahasia terenkripsi di database. Kunci diturunkan dari ITOC_SECRET_KEY (atau ITOC_JWT_SECRET bila kosong), jadi kunci hanya ada di .env.
Rotasi kunci: isi kunci baru di ITOC_SECRET_KEY dan kunci lama di ITOC_SECRET_KEY_OLD (pisahkan dengan koma bila lebih dari satu), restart,
jalankan `python -m app.cli rotate-key`, lalu hapus ITOC_SECRET_KEY_OLD. Selama kunci lama masih ada, rahasia lama tetap terbaca."""
import base64
import hashlib
import json
import os
from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from sqlalchemy.orm import Session
from .config import settings
from .models import Secret


def _fernet(seed: str) -> Fernet:
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(seed.encode()).digest()))


def _f() -> MultiFernet:
    seed = os.environ.get("ITOC_SECRET_KEY") or settings().jwt_secret
    olds = [x.strip() for x in os.environ.get("ITOC_SECRET_KEY_OLD", "").split(",") if x.strip()]
    return MultiFernet([_fernet(seed)] + [_fernet(o) for o in olds])      # enkripsi memakai kunci pertama, dekripsi mencoba semuanya


def enc(text: str) -> str:
    return _f().encrypt(text.encode()).decode()


def dec(token: str) -> str | None:
    try:
        return _f().decrypt(token.encode()).decode()
    except InvalidToken:
        return None


def rotate_all(db: Session) -> dict:
    """Enkripsi ulang semua nilai terenkripsi (rahasia konektor/SMTP dan URL webhook) dengan kunci utama. Nilai yang tidak terbaca dilaporkan, tidak diubah."""
    from .models import Webhook
    f, done, bad = _f(), 0, []
    for row in db.query(Secret):
        try:
            row.value, done = f.rotate(row.value.encode()).decode(), done + 1
        except InvalidToken:
            bad.append("secret:" + row.name)
    for w in db.query(Webhook):
        try:
            w.url_enc, done = f.rotate(w.url_enc.encode()).decode(), done + 1
        except InvalidToken:
            bad.append("webhook:" + w.name)
    return {"rotated": done, "unreadable": bad}


def put(db: Session, name: str, value: str) -> None:
    row = db.get(Secret, name)
    if row:
        row.value = enc(value)
    else:
        db.add(Secret(name=name, value=enc(value)))


def get(db: Session, name: str) -> str | None:
    row = db.get(Secret, name)
    return dec(row.value) if row else None


def delete(db: Session, name: str) -> None:
    row = db.get(Secret, name)
    if row:
        db.delete(row)


def put_json(db: Session, name: str, obj: dict) -> None:
    put(db, name, json.dumps(obj))


def get_json(db: Session, name: str) -> dict:
    v = get(db, name)
    try:
        return json.loads(v) if v else {}
    except ValueError:
        return {}


def cred(db: Session, name: str, env_name: str) -> str:
    """Kredensial konektor: nilai dari Admin (terenkripsi) lebih dulu, lalu variabel lingkungan."""
    return get(db, name) or os.environ.get(env_name, "")