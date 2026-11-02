"""Chat commands for the shift summary (/fullday, /fullday-261101, /pagi, /noc, /eos-parepare, ...), so a WhatsApp or Telegram bridge only has to forward the text it received.
The commands are the parameter chat.commands (Admin > Operations > Targets & Parameters > Reports); DEFAULT below is used when that parameter is missing or broken.
A command always answers with a message: a wrong one answers with the list of commands, so the chat never stays silent."""
import re
from datetime import date

from .insight import shift_summary
from .store import Config

# One entry per command. name: what is typed after the slash. aliases: other names for it. kind: full | noc | soc | eos.
# scope: duty (the duty day) | day (00:00-24:00) | half1 | half2 | s1, s2, s3 (a shift by number) | shift:Pagi (a shift by name) | 24h | 7d | 30d | month.
# site: a fixed branch for the command (for example "Branch Parepare"). branch_arg: the branch is typed after the command (eos only). hidden: leave it out of /help.
DEFAULT = {
    "commands": [
        {"name": "fullday", "aliases": ["full", "harian"], "kind": "full", "scope": "duty", "help": "laporan hari tugas ini"},
        {"name": "pagi", "kind": "full", "scope": "shift:Pagi", "help": "laporan shift Pagi"},
        {"name": "sore", "kind": "full", "scope": "shift:Sore", "help": "laporan shift Sore"},
        {"name": "malam", "kind": "full", "scope": "shift:Malam", "help": "laporan shift Malam"},
        {"name": "noc", "kind": "noc", "scope": "duty", "help": "laporan NOC hari tugas ini"},
        {"name": "soc", "kind": "soc", "scope": "duty", "help": "laporan SOC hari tugas ini"},
        {"name": "eos", "kind": "eos", "scope": "duty", "branch_arg": True, "help": "laporan EOS semua cabang, atau satu cabang: /eos-parepare"},
        {"name": "7hari", "aliases": ["7d", "minggu"], "kind": "full", "scope": "7d", "help": "7 hari terakhir"},
    ],
    "footer": ["Tambahkan tanggal YYYYMMDD untuk hari lain, contoh /fullday-20261101 atau /eos-parepare-20261101.", "Hari tugas dimulai pukul 08.00 dan berakhir 08.00 keesokan harinya."],
}
DATE_RE = re.compile(r"^(\d{8}|\d{6})$")            # YYYYMMDD; the short yymmdd form still works
NAME_RE = re.compile(r"^[a-z0-9]{1,20}$")
KINDS = ("full", "noc", "soc", "eos")
FIXED = ("duty", "day", "half1", "half2", "24h", "7d", "30d", "month")
DATED = ("duty", "day", "half1", "half2", "month")                # scopes that follow a date
MAX_CHARS = 3000                                                  # a chat message limit: the summary shortens its lists to stay within it


def _config(cfg: Config) -> dict:
    """The command list from the parameter, checked entry by entry; broken entries are skipped and a missing or empty list falls back to DEFAULT."""
    raw = cfg.p("chat.commands") or {}
    cmds = []
    for c in raw.get("commands", []) if isinstance(raw, dict) else []:
        if not isinstance(c, dict):
            continue
        name = str(c.get("name", "")).strip().lower().lstrip("/")
        scope = str(c.get("scope", "duty"))
        if NAME_RE.match(name) and c.get("kind") in KINDS and (scope in FIXED or re.match(r"^s\d{1,2}$", scope) or scope.lower().startswith("shift:")):
            cmds.append({**c, "name": name, "scope": scope})
    if not cmds:
        return DEFAULT
    return {"commands": cmds, "footer": raw.get("footer", DEFAULT["footer"]) if isinstance(raw.get("footer"), list) else DEFAULT["footer"]}


def catalog(cfg: Config) -> list[dict]:
    """The commands that /help lists, for a chat app that offers them while the user types a slash."""
    return [{"name": x["name"], "aliases": [str(a) for a in x.get("aliases", [])], "help": x.get("help") or x["name"]} for x in _config(cfg)["commands"] if not x.get("hidden")]


def help_text(cfg: Config) -> str:
    c = _config(cfg)
    shown = [x for x in c["commands"] if not x.get("hidden")]
    lines = ["*Perintah TERA*  (ketik / atau /help untuk daftar ini)"]
    for x in shown:
        alias = ", ".join("/" + str(a).strip().lstrip("/") for a in x.get("aliases", []) if str(a).strip())
        lines.append(f"/{x['name']}" + (f" ({alias})" if alias else "") + f" : {x.get('help') or x['name']}")
    lines.append("/help : daftar ini")
    lines += [str(f) for f in c["footer"]]
    if any(x["kind"] == "eos" and x.get("branch_arg") for x in shown):
        lines.append("Cabang untuk perintah EOS: " + ", ".join(s.lower().replace("branch ", "") for s in cfg.sites if s.lower().startswith("branch ")) + ".")
    return "\n".join(lines)


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


def _scope(cfg: Config, scope: str) -> str | None:
    if scope.lower().startswith("shift:"):
        want = scope.split(":", 1)[1].strip().lower()
        no = next((s["no"] for s in cfg.shifts if s["name"].lower() == want), None)
        return f"s{no}" if no else None
    return scope


def run(db, cfg: Config, text: str, locked_site: str = "") -> str:
    toks = [t for t in re.split(r"[\s\-_]+", (text or "").strip().lower().lstrip("/")) if t]
    help_ = help_text(cfg)
    if not toks or toks[0] in ("help", "bantuan", "start", "?"):
        return help_
    cmd, rest = toks[0], toks[1:]
    by_name = {}
    for c in _config(cfg)["commands"]:
        for n in [c["name"]] + [str(a).strip().lower().lstrip("/") for a in c.get("aliases", [])]:
            by_name.setdefault(n, c)
    c = by_name.get(cmd)
    if not c:
        return f"Perintah '/{cmd}' tidak dikenal.\n\n" + help_
    day, words = None, []
    for t in rest:
        if t.isdigit() and not DATE_RE.match(t):
            return f"Tanggal '{t}' tidak valid. Pakai format YYYYMMDD, contoh 20261101.\n\n" + help_
        if DATE_RE.match(t):
            try:
                day = _date(t)
            except ValueError:
                return f"Tanggal '{t}' tidak valid. Pakai format YYYYMMDD, contoh 20261101.\n\n" + help_
        else:
            words.append(t)
    scope = _scope(cfg, c["scope"])
    if scope is None:
        return f"Shift untuk perintah '/{cmd}' tidak ditemukan di pengaturan.\n\n" + help_
    dated = scope in DATED or re.match(r"^s\d+$", scope)
    if day and not dated:
        return f"Perintah '/{cmd}' tidak memakai tanggal.\n\n" + help_
    if day and day > cfg.now().date():
        return "Tanggal itu belum terjadi.\n\n" + help_
    site = ""
    if c["kind"] == "eos":
        site, err = _site(cfg, [str(c["site"]).lower().replace("branch ", "")] if c.get("site") else (words if c.get("branch_arg") else []))
        if site is None:
            return err + "\n\n" + help_
        site = locked_site or site
    return shift_summary(db, cfg, None, scope, day, c["kind"], site, MAX_CHARS)
