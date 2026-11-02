"""Chat commands for the shift summary (/fullday, /fullday-20261101, /pagi, /noc, /eos-parepare, /thismonth, ...), so a WhatsApp or Telegram bridge only has to forward the text it received.
The commands are the parameter chat.commands (Admin > Operations > Targets & Parameters > Reports); DEFAULT below is used when that parameter is missing or broken.
A command always answers with a message: a wrong one answers with the list of commands, so the chat never stays silent."""
import re
from datetime import date

from .insight import shift_summary
from .store import Config

# One entry per command. name: what is typed after the slash. aliases: other names for it. kind: full | noc | soc | eos.
# scope: duty (the duty day) | day (00:00-24:00) | half1 | half2 | s1, s2, s3 (a shift by number) | shift:Pagi (a shift by name) | 24h | 7d | 30d | thismonth | lastmonth | month (the month is typed: /month-202610).
# site: a fixed branch for the command (for example "Branch Parepare"). branch_arg: the branch is typed after the command (eos only). hidden: leave it out of /help.
# group: commands with the same group share one line of /help, written with the "line" of the first of them ("help" is the text of the slash menu in the chat app).
DEFAULT = {
    "commands": [
        {"name": "fullday", "aliases": ["full", "harian"], "kind": "full", "scope": "duty", "help": "laporan hari tugas ini"},
        {"name": "pagi", "kind": "full", "scope": "shift:Pagi", "group": "shift", "line": "satu shift hari tugas ini", "help": "laporan shift Pagi"},
        {"name": "sore", "kind": "full", "scope": "shift:Sore", "group": "shift", "help": "laporan shift Sore"},
        {"name": "malam", "kind": "full", "scope": "shift:Malam", "group": "shift", "help": "laporan shift Malam"},
        {"name": "noc", "kind": "noc", "scope": "duty", "group": "report", "line": "laporan NOC / SOC", "help": "laporan NOC hari tugas ini"},
        {"name": "soc", "kind": "soc", "scope": "duty", "group": "report", "help": "laporan SOC hari tugas ini"},
        {"name": "eos", "kind": "eos", "scope": "duty", "branch_arg": True, "help": "laporan EOS semua cabang, atau satu cabang: /eos-parepare"},
        {"name": "7hari", "aliases": ["7d", "minggu"], "kind": "full", "scope": "7d", "help": "7 hari terakhir"},
        {"name": "thismonth", "aliases": ["bulanini"], "kind": "full", "scope": "thismonth", "group": "month", "line": "bulan ini / bulan lalu", "help": "laporan bulan ini"},
        {"name": "lastmonth", "aliases": ["bulanlalu"], "kind": "full", "scope": "lastmonth", "group": "month", "help": "laporan bulan lalu"},
        {"name": "month", "aliases": ["bulan"], "kind": "full", "scope": "month", "hidden": True, "help": "laporan satu bulan: /month-202610"},
    ],
    "footer": ["Tanggal: tambah -20261101. Rentang: -20261101-20261107. Bulan lain: /month-202610", "Cabang: /eos-belawan. Daftar cabang: /cabang"],
}
DATE_RE = re.compile(r"^(\d{8}|\d{6})$")            # YYYYMMDD; the short yymmdd form still works
NAME_RE = re.compile(r"^[a-z0-9]{1,20}$")
KINDS = ("full", "noc", "soc", "eos")
FIXED = ("duty", "day", "half1", "half2", "24h", "7d", "30d", "thismonth", "lastmonth", "month")
DATED = ("duty", "day", "half1", "half2")                         # scopes that follow a typed date (two dates on "duty" make a range)
MAX_RANGE_DAYS = 62
HINT = "Ketik / untuk daftar perintah."                      # a wrong command gets a short pointer, not the whole list
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
    """Short on purpose: one line per command or per group of commands, without aliases."""
    c = _config(cfg)
    rows, by_group = [], {}
    for x in (y for y in c["commands"] if not y.get("hidden")):
        g = str(x.get("group") or "")
        if g in by_group:
            by_group[g][0].append("/" + x["name"])
            continue
        row = (["/" + x["name"]], str(x.get("line") or x.get("help") or x["name"]))
        rows.append(row)
        if g:
            by_group[g] = row
    return "\n".join(["*Perintah TERA*"] + [f"{' '.join(names)} : {line}" for names, line in rows] + ["/ atau /help : daftar ini"] + [str(f) for f in c["footer"]])


def _date(tok: str) -> date:
    y = int(tok[:2]) + 2000 if len(tok) == 6 else int(tok[:4])
    return date(y, int(tok[-4:-2]), int(tok[-2:]))


def _month(tok: str) -> date:
    """YYYYMM, or any YYYYMMDD inside the month -> the first day of that month."""
    return date(int(tok[:4]), int(tok[4:6]), 1) if len(tok) == 6 else _date(tok).replace(day=1)


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
        return None, f"Cabang '{q}' tidak ditemukan. Daftar cabang: /cabang"
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
    if toks == ["cabang"] or toks == ["branch"]:
        return "*Cabang untuk /eos-<nama>*\n" + ", ".join(s.lower().replace("branch ", "") for s in cfg.sites if s.lower().startswith("branch ")) + "."
    cmd, rest = toks[0], toks[1:]
    by_name = {}
    for c in _config(cfg)["commands"]:
        for n in [c["name"]] + [str(a).strip().lower().lstrip("/") for a in c.get("aliases", [])]:
            by_name.setdefault(n, c)
    c = by_name.get(cmd)
    if not c:
        return f"Perintah '/{cmd}' tidak dikenal.\n" + HINT
    is_month = c["scope"] == "month"
    dates, words = [], []
    for t in rest:
        if is_month and re.match(r"^(\d{6}|\d{8})$", t):                  # a month: YYYYMM, or any date inside it
            try:
                dates.append(_month(t))
            except ValueError:
                return f"Bulan '{t}' tidak valid. Pakai format YYYYMM, contoh 202610.\n" + HINT
        elif t.isdigit():
            if not DATE_RE.match(t):
                return f"Tanggal '{t}' tidak valid. Pakai format YYYYMMDD, contoh 20261101.\n" + HINT
            try:
                dates.append(_date(t))
            except ValueError:
                return f"Tanggal '{t}' tidak valid. Pakai format YYYYMMDD, contoh 20261101.\n" + HINT
        else:
            words.append(t)
    scope = _scope(cfg, c["scope"])
    if scope is None:
        return f"Shift untuk perintah '/{cmd}' tidak ditemukan di pengaturan.\n" + HINT
    today, day = cfg.now().date(), None
    if is_month:
        if len(dates) != 1:
            return "Sebutkan bulannya, contoh /month-202610.\n" + HINT
        day = dates[0]
        if day > today:
            return "Bulan itu belum terjadi.\n" + HINT
    elif dates:
        if scope not in DATED and not re.match(r"^s\d+$", scope):
            return f"Perintah '/{cmd}' tidak memakai tanggal.\n" + HINT
        if max(dates) > today:
            return "Tanggal itu belum terjadi.\n" + HINT
        if len(dates) == 1:
            day = dates[0]
        elif len(dates) == 2 and scope == "duty":
            d1, d2 = sorted(dates)
            if (d2 - d1).days + 1 > MAX_RANGE_DAYS:
                return f"Rentang terlalu panjang (maksimal {MAX_RANGE_DAYS} hari). Untuk satu bulan: /month-202610.\n" + HINT
            scope = f"range:{d1:%Y%m%d}:{d2:%Y%m%d}"
        else:
            return "Pakai satu tanggal, atau dua tanggal untuk rentang hari (hanya perintah harian).\n" + HINT
    site = ""
    if c["kind"] == "eos":
        site, err = _site(cfg, [str(c["site"]).lower().replace("branch ", "")] if c.get("site") else (words if c.get("branch_arg") else []))
        if site is None:
            return err + "\n" + HINT
        site = locked_site or site
    return shift_summary(db, cfg, None, scope, day, c["kind"], site, MAX_CHARS)
