"""Chat commands for the shift summary (/fullday, /fullday-261101, /pagi, /noc, /eos-parepare, ...), so a WhatsApp or Telegram bridge only has to forward the text it received.
A command always answers with a message: a wrong one answers with the list of commands, so the chat never stays silent."""
import re
from datetime import date

from .insight import shift_summary
from .store import Config

HELP = """*Perintah TERA*
/fullday : laporan hari tugas ini
/fullday-261101 : hari tugas 1 Nov 2026 (yymmdd)
/pagi /sore /malam : satu shift hari tugas ini
/malam-261101 : satu shift pada tanggal lain
/noc /soc : laporan NOC atau SOC
/eos : semua cabang
/eos-parepare : satu cabang
/eos-parepare-261101 : satu cabang pada tanggal tertentu
/7hari : 7 hari terakhir
/help : daftar ini
Hari tugas dimulai pukul 08.00 dan berakhir 08.00 keesokan harinya."""
DATE_RE = re.compile(r"^(\d{6}|\d{8})$")


def _date(tok: str) -> date:
    y = int(tok[:2]) + 2000 if len(tok) == 6 else int(tok[:4])
    return date(y, int(tok[-4:-2]), int(tok[-2:]))


def _site(cfg: Config, words: list[str]) -> tuple[str | None, str]:
    """Branch from the words after the command: the master name with or without 'Branch', or a part of it when only one name matches."""
    q = " ".join(w for w in words if w != "branch").strip()
    if not q:
        return "", ""
    low = {s: s.lower().replace("branch ", "") for s in cfg.sites}
    exact = [s for s, k in low.items() if k == q or s.lower() == q]
    part = exact or [s for s, k in low.items() if q in k]
    if len(part) == 1:
        return part[0], ""
    if not part:
        return None, f"Cabang '{q}' tidak ditemukan."
    return None, "Cabang '" + q + "' cocok dengan lebih dari satu: " + ", ".join(k for s, k in low.items() if s in part[:8]) + "."


MAX_CHARS = 3000                                                  # a chat message limit: the summary shortens its lists to stay within it


def run(db, cfg: Config, text: str, locked_site: str = "") -> str:
    toks = [t for t in re.split(r"[\s\-_]+", (text or "").strip().lower().lstrip("/")) if t]
    if not toks or toks[0] in ("help", "bantuan", "start", "?"):
        return HELP
    cmd, rest = toks[0], toks[1:]
    day, words = None, []
    for t in rest:
        if DATE_RE.match(t):
            try:
                day = _date(t)
            except ValueError:
                return f"Tanggal '{t}' tidak valid. Pakai format yymmdd, contoh 261101.\n\n" + HELP
        else:
            words.append(t)
    shifts = {s["name"].lower(): s["no"] for s in cfg.shifts}
    kind, scope, site = "full", "duty", ""
    if cmd in ("fullday", "full", "harian"):
        pass
    elif cmd in ("noc", "soc"):
        kind = cmd
    elif cmd == "eos":
        kind = "eos"
        site, err = _site(cfg, words)
        if site is None:
            return err + "\n\n" + HELP
    elif cmd in shifts:
        scope = f"s{shifts[cmd]}"
    elif cmd in ("7hari", "7d", "minggu"):
        scope, day = "7d", None
    else:
        return f"Perintah '/{cmd}' tidak dikenal.\n\n" + HELP
    if day and day > cfg.now().date():
        return "Tanggal itu belum terjadi.\n\n" + HELP
    return shift_summary(db, cfg, None, scope, day, kind, locked_site or site if kind == "eos" else "", MAX_CHARS)
