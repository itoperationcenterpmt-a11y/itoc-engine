"""Pengaturan level infrastruktur (koneksi, rahasia). Semua parameter bisnis ada di database."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="ITOC_", extra="ignore")

    database_url: str = "postgresql+psycopg://itoc:itoc@localhost:5432/itoc"
    jwt_secret: str = "ganti-di-produksi"
    jwt_minutes: int = 720
    cors_origins: str = ""            # frontend disajikan satu origin; isi daftar origin eksplisit bila perlu, "*" diabaikan
    docs: bool = False                 # /docs, /redoc, /openapi.json mati secara bawaan
    frontend_dir: str = "../frontend"
    run_scheduler: bool = True
    upload_max_mb: int = 40
    restore_max_mb: int = 1024         # batas ukuran file .sql untuk Restore (Admin → System)
    backup_dir: str = "/srv/backups"   # cadangan pengaman sebelum restore disimpan di sini


@lru_cache
def settings() -> Settings:
    return Settings()
