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
        add("critical", "Akun aktif memakai password lemah/bawaan", ", ".join(weak_users) + ". Reset lewat Admin > Pengguna atau nonaktifkan sebelum VAPT dan go-live.")
    if s.jwt_secret in ("ganti-di-produksi", "ganti-dengan-string-acak-panjang") or len(s.jwt_secret) < 32:
        add("critical", "ITOC_JWT_SECRET lemah", "Token login bisa dipalsukan. Isi string acak minimal 32 karakter di .env.")
    if ":itoc@" in s.database_url:
        add("high", "Password database masih bawaan", "Ganti DB_PASSWORD di .env dan buat ulang volume database atau ubah password di PostgreSQL.")
    if os.environ.get("ITOC_ENV", "").lower() != "production":
        add("medium", "ITOC_ENV belum production", "Perintah seed-users/seed-demo/seed-demo-itcare masih bisa dijalankan. Set ITOC_ENV=production di server.")
    if s.docs:
        add("medium", "Dokumentasi API (/docs) aktif", "Matikan ITOC_DOCS di server produksi.")
    if s.jwt_minutes > 720:
        add("low", "Masa berlaku sesi lebih dari 12 jam", f"ITOC_JWT_MINUTES={s.jwt_minutes}.")
    if not os.environ.get("ITOC_SECRET_KEY"):
        add("low", "ITOC_SECRET_KEY kosong", "Kunci enkripsi rahasia memakai ITOC_JWT_SECRET; memutar salah satu membuat rahasia tersimpan tak terbaca. Isi kunci terpisah.")
    notls, plain = [], []
    for d in db.query(DataSource):
        c = d.config or {}
        if d.enabled and c.get("base_url"):
            if c.get("verify_tls") is False:
                notls.append(d.label)
            if str(c["base_url"]).lower().startswith("http://"):
                plain.append(d.label)
    if notls:
        add("medium", "Verifikasi TLS dimatikan pada konektor", ", ".join(notls) + ". Rentan penyadapan di jaringan internal; pasang sertifikat CA internal lalu aktifkan verifikasi bila memungkinkan.")
    if plain:
        add("medium", "Konektor memakai http:// (tanpa enkripsi)", ", ".join(plain))
    keys = db.query(ApiKey).filter(ApiKey.revoked_at.is_(None), ApiKey.expires_at.is_(None)).all()
    if keys:
        add("low", "API key tanpa tanggal kedaluwarsa", ", ".join(k.name for k in keys))
    hooks = [w.name for w in db.query(Webhook).filter_by(enabled=True) if (vault.dec(w.url_enc) or "").lower().startswith("http://")]
    if hooks:
        add("low", "Webhook memakai http://", ", ".join(hooks))
    smtp = vault.get_json(db, "smtp")
    if smtp.get("host") and smtp.get("security") == "none":
        add("medium", "SMTP tanpa enkripsi", "Pilih starttls atau ssl di Admin > Email.")
    admins = [u.username for u in db.query(User).filter_by(active=True) if u.role.is_admin]
    add("info", f"{len(admins)} akun Super Admin aktif", ", ".join(admins))
    add("info", f"{db.query(Secret).count()} rahasia terenkripsi tersimpan di database", "Nilai tidak pernah dikirim ke browser.")
    return out