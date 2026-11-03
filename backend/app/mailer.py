"""Kirim email lewat SMTP. Konfigurasi (host, port, keamanan, akun, pengirim) tersimpan terenkripsi di secret "smtp"."""
import smtplib
import ssl
from email.message import EmailMessage
from sqlalchemy.orm import Session
from . import vault


def config(db: Session) -> dict:
    return vault.get_json(db, "smtp")


def send(db: Session, to: list[str], subject: str, body: str, attachments: list[tuple[str, bytes, str]] | None = None) -> None:
    c = config(db)
    if not c.get("host") or not c.get("from"):
        raise RuntimeError("SMTP is not set (host and sender are required)")
    msg = EmailMessage()
    msg["From"] = f'{c.get("from_name") or ""} <{c["from"]}>'.strip() if c.get("from_name") else c["from"]
    msg["To"] = ", ".join(to)
    msg["Subject"] = subject
    msg.set_content(body)
    for name, data, mime in attachments or []:
        main, _, sub = mime.partition("/")
        msg.add_attachment(data, maintype=main, subtype=sub or "octet-stream", filename=name)
    host, port, sec = c["host"], int(c.get("port") or 587), c.get("security", "starttls")
    ctx = ssl.create_default_context()
    if sec == "ssl":
        s = smtplib.SMTP_SSL(host, port, timeout=20, context=ctx)
    else:
        s = smtplib.SMTP(host, port, timeout=20)
    try:
        s.ehlo()
        if sec == "starttls":
            s.starttls(context=ctx)
            s.ehlo()
        if c.get("user"):
            s.login(c["user"], c.get("password", ""))
        s.send_message(msg)
    finally:
        try:
            s.quit()
        except Exception:
            pass