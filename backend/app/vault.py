"""Rahasia terenkripsi di database. Kunci diturunkan dari ITOC_SECRET_KEY (atau ITOC_JWT_SECRET bila kosong), jadi kunci hanya ada di .env.
Mengganti kunci membuat rahasia lama tidak terbaca; isi ulang lewat menu Admin."""
import base64
import hashlib
import json
import os
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session
from .config import settings
from .models import Secret


def _f() -> Fernet:
    seed = os.environ.get("ITOC_SECRET_KEY") or settings().jwt_secret
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(seed.encode()).digest()))


def enc(text: str) -> str:
    return _f().encrypt(text.encode()).decode()


def dec(token: str) -> str | None:
    try:
        return _f().decrypt(token.encode()).decode()
    except InvalidToken:
        return None


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