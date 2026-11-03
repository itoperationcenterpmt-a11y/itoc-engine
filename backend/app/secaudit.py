"""Pemeriksaan konfigurasi keamanan (tanpa menampilkan rahasia): dipakai CLI `python -m app.cli security-check` dan GET /api/admin/security-check.
Tiap temuan: {level: critical|high|medium|low|info, title, detail}."""
import os
from sqlalchemy.orm import Session
from . import vault
from .config import settings
from .models import ApiKey, DataSource, Secret, User, Webhook
from .security import check_pw

WEAK = ["password123", "password", "admin", "itoc", "12345678", "admin123", "itoc1234", "pelindo123", "123456789", "qwerty123"]


def findings(db: Session) -> list[dict]:
    out, add = [], lambda lv, t, d="": out.append({"level": lv, "title": t, "detail": d})
    s = settings()
    weak_users = []
    for u in db.query(User).filter_by(active=True):
        if any(check_pw(p, u.password_hash) for p in WEAK + [u.username, u.username + "123"]):
            weak_users.append(u.username)
    if weak_users:
        add("critical", "Active accounts use weak/default passwords", ", ".join(weak_users) + ". Reset through Admin > Users or deactivate before VAPT and go-live.")
    if s.jwt_secret in ("ganti-di-produksi", "ganti-dengan-string-acak-panjang") or len(s.jwt_secret) < 32:
        add("critical", "ITOC_JWT_SECRET lemah", "Login tokens can be forged. Set a random string of at least 32 characters in .env.")
    if ":itoc@" in s.database_url:
        add("high", "Database password is still the default", "Change DB_PASSWORD in .env and recreate the database volume, or change the password in PostgreSQL.")
    if os.environ.get("ITOC_ENV", "").lower() != "production":
        add("medium", "ITOC_ENV is not production", "The seed-users/seed-demo/seed-demo-itcare commands can still be run. Set ITOC_ENV=production on the server.")
    if s.docs:
        add("medium", "Dokumentasi API (/docs) aktif", "Matikan ITOC_DOCS di server produksi.")
    if s.jwt_minutes > 720:
        add("low", "Session lifetime is over 12 hours", f"ITOC_JWT_MINUTES={s.jwt_minutes}.")
    if not os.environ.get("ITOC_SECRET_KEY"):
        add("low", "ITOC_SECRET_KEY is empty", "The secret-encryption key uses ITOC_JWT_SECRET; rotating either one makes stored secrets unreadable. Set a separate key.")
    notls, plain = [], []
    for d in db.query(DataSource):
        c = d.config or {}
        if d.enabled and c.get("base_url"):
            if c.get("verify_tls") is False:
                notls.append(d.label)
            if str(c["base_url"]).lower().startswith("http://"):
                plain.append(d.label)
    if notls:
        add("medium", "TLS verification is off on connectors", ", ".join(notls) + ". Rentan penyadapan di jaringan internal; pasang sertifikat CA internal lalu aktifkan verifikasi bila memungkinkan.")
    if plain:
        add("medium", "Connectors use http:// (no encryption)", ", ".join(plain))
    keys = db.query(ApiKey).filter(ApiKey.revoked_at.is_(None), ApiKey.expires_at.is_(None)).all()
    if keys:
        add("low", "API keys without an expiry date", ", ".join(k.name for k in keys))
    hooks = [w.name for w in db.query(Webhook).filter_by(enabled=True) if (vault.dec(w.url_enc) or "").lower().startswith("http://")]
    if hooks:
        add("low", "Webhook memakai http://", ", ".join(hooks))
    smtp = vault.get_json(db, "smtp")
    if smtp.get("host") and smtp.get("security") == "none":
        add("medium", "SMTP without encryption", "Choose starttls or ssl in Admin > Email.")
    admins = [u.username for u in db.query(User).filter_by(active=True) if u.role.is_admin]
    add("info", f"{len(admins)} akun Super Admin aktif", ", ".join(admins))
    add("info", f"{db.query(Secret).count()} rahasia terenkripsi tersimpan di database", "The value is never sent to the browser.")
    return out