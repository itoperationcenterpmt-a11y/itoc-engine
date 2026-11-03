"""Chat commands: a shorter /help, month and range commands. The stored list is replaced only while it is still the untouched previous default (8 commands, no groups).

Revision ID: 0074
Revises: 0073
"""
import json

from alembic import op
from sqlalchemy import text

revision = "0074"
down_revision = "0073"
branch_labels = None
depends_on = None

NEW = {
    "commands": [
        {
            "name": "fullday",
            "aliases": [
                "full",
                "harian"
            ],
            "kind": "full",
            "scope": "duty",
            "help": "laporan hari tugas ini"
        },
        {
            "name": "pagi",
            "kind": "full",
            "scope": "shift:Pagi",
            "group": "shift",
            "line": "satu shift hari tugas ini",
            "help": "laporan shift Pagi"
        },
        {
            "name": "sore",
            "kind": "full",
            "scope": "shift:Sore",
            "group": "shift",
            "help": "laporan shift Sore"
        },
        {
            "name": "malam",
            "kind": "full",
            "scope": "shift:Malam",
            "group": "shift",
            "help": "laporan shift Malam"
        },
        {
            "name": "noc",
            "kind": "noc",
            "scope": "duty",
            "group": "report",
            "line": "laporan NOC / SOC",
            "help": "laporan NOC hari tugas ini"
        },
        {
            "name": "soc",
            "kind": "soc",
            "scope": "duty",
            "group": "report",
            "help": "laporan SOC hari tugas ini"
        },
        {
            "name": "eos",
            "kind": "eos",
            "scope": "duty",
            "branch_arg": True,
            "help": "laporan EOS semua cabang, atau satu cabang: /eos-parepare"
        },
        {
            "name": "7hari",
            "aliases": [
                "7d",
                "minggu"
            ],
            "kind": "full",
            "scope": "7d",
            "help": "7 hari terakhir"
        },
        {
            "name": "thismonth",
            "aliases": [
                "bulanini"
            ],
            "kind": "full",
            "scope": "thismonth",
            "group": "month",
            "line": "bulan ini / bulan lalu",
            "help": "laporan bulan ini"
        },
        {
            "name": "lastmonth",
            "aliases": [
                "bulanlalu"
            ],
            "kind": "full",
            "scope": "lastmonth",
            "group": "month",
            "help": "laporan bulan lalu"
        },
        {
            "name": "month",
            "aliases": [
                "bulan"
            ],
            "kind": "full",
            "scope": "month",
            "hidden": True,
            "help": "laporan satu bulan: /month-202610"
        }
    ],
    "footer": [
        "Tanggal: tambah -20261101. Rentang: -20261101-20261107. Bulan lain: /month-202610",
        "Cabang: /eos-belawan. Daftar cabang: /cabang"
    ]
}


def upgrade():
    op.get_bind().execute(text("""UPDATE app_parameter SET value = CAST(:v AS jsonb), description = :d
                                  WHERE key = 'chat.commands' AND jsonb_array_length(value->'commands') = 8 AND value::text NOT LIKE '%"group"%'"""), {"v": json.dumps(NEW, ensure_ascii=False), "d": 'Commands typed in a WhatsApp or Telegram chat, for example /fullday or /eos-parepare-20261101. Per command: name (what is typed after the slash), aliases (other names), kind (full | noc | soc | eos), scope (duty = the duty day | day = 00:00-24:00 | half1 | half2 | s1, s2, s3 = a shift by number | shift:Pagi = a shift by name | 24h | 7d | 30d | thismonth | lastmonth | month = the month is typed, /month-202610), help (the text in the slash menu of the chat app), group and line (commands with the same group share one line of /help, written with the line of the first one), branch_arg (true: the branch is typed after the command, eos only), site (a fixed branch, for example Branch Parepare), hidden (true: leave it out of /help). footer = the lines under the list. A date YYYYMMDD can be added after a day or shift command (for example -20261101); two dates after a daily command give a range of duty days (at most 62). Broken entries are skipped; an empty list falls back to the built-in commands.'})


def downgrade():
    pass
