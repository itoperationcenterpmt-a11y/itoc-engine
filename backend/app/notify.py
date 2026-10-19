"""Notifikasi webhook. Tujuan, jenis, dan peristiwa diatur di Admin -> Webhooks. Kegagalan hanya dicatat, tidak mengganggu proses utama."""
import logging
import threading
from datetime import datetime
import httpx
from . import vault
from .db import session_scope
from .models import Webhook

log = logging.getLogger("itoc.notify")
EVENTS = {"handover_new": "Handover baru (semua prioritas)", "handover_high": "Handover prioritas tinggi",
          "sync_failed": "Sinkron sumber data gagal", "test": "Pesan uji"}
KINDS = {"generic": "JSON umum", "teams": "Microsoft Teams", "slack": "Slack", "telegram": "Telegram"}


def _payload(kind: str, event: str, text: str, data: dict | None) -> dict:
    if kind in ("teams", "slack", "telegram"):
        return {"text": text}
    return {"event": event, "text": text, "data": data or {}, "at": datetime.utcnow().isoformat() + "Z"}


def post(kind: str, url: str, event: str, text: str, data: dict | None = None) -> str:
    r = httpx.post(url, json=_payload(kind, event, text, data), timeout=10)
    r.raise_for_status()
    return f"HTTP {r.status_code}"


def _run(event: str, text: str, data: dict | None):
    with session_scope() as db:
        for w in db.query(Webhook).filter_by(enabled=True):
            if event not in (w.events or []):
                continue
            try:
                url = vault.dec(w.url_enc)
                w.last_status = post(w.kind, url, event, text, data) if url else "URL tidak terbaca (kunci enkripsi berubah?)"
            except Exception as e:
                log.warning("webhook %s: %s", w.name, e)
                w.last_status = ("Gagal: " + str(e))[:190]
            w.last_at = datetime.utcnow()


def fire(event: str, text: str, data: dict | None = None) -> None:
    """Kirim di thread terpisah supaya permintaan pengguna tidak menunggu jaringan."""
    threading.Thread(target=lambda: _safe(event, text, data), daemon=True).start()


def _safe(event, text, data):
    try:
        _run(event, text, data)
    except Exception:
        log.exception("notify %s", event)