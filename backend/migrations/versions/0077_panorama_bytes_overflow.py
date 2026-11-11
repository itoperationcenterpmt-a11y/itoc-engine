"""Panorama byte counts with 2^48 (281.5 TB) added, one DNS source network per day: the whole multiples are removed from soc_fw_day and soc_day.
Only rows that hold such a value are touched, and each one is first copied to byte_fix_backup (table, key, the row as it was), so nothing is lost. To undo a row, copy its values back from that table.

Revision ID: 0077
Revises: 0076
"""
import json

from alembic import op
from sqlalchemy import text

revision = "0077"
down_revision = "0076"
branch_labels = None
depends_on = None

P = 2 ** 48


def _fix(d):
    return {k: (int(v) % P if isinstance(v, (int, float)) and v >= P else v) for k, v in (d or {}).items()}


def upgrade():
    c = op.get_bind()
    c.execute(text("CREATE TABLE IF NOT EXISTS byte_fix_backup (tbl text NOT NULL, pk jsonb NOT NULL, before jsonb NOT NULL, fixed_at timestamp NOT NULL DEFAULT now())"))
    bk = text("INSERT INTO byte_fix_backup (tbl, pk, before) VALUES (:t, CAST(:pk AS jsonb), CAST(:b AS jsonb))")
    for r in c.execute(text("SELECT day, fw, bytes, app, src, acat FROM soc_fw_day WHERE bytes >= :p"), {"p": P}).mappings().all():
        c.execute(bk, {"t": "soc_fw_day", "pk": json.dumps({"day": str(r["day"]), "fw": r["fw"]}), "b": json.dumps({"bytes": int(r["bytes"]), "app": r["app"], "src": r["src"], "acat": r["acat"]})})
        c.execute(text("UPDATE soc_fw_day SET bytes = :b, app = CAST(:a AS jsonb), src = CAST(:s AS jsonb), acat = CAST(:c AS jsonb) WHERE day = :d AND fw = :f"),
                  {"b": int(r["bytes"]) % P, "a": json.dumps(_fix(r["app"])), "s": json.dumps(_fix(r["src"])), "c": json.dumps(_fix(r["acat"])), "d": r["day"], "f": r["fw"]})
    for r in c.execute(text("SELECT batch_id, day, bytes FROM soc_day WHERE bytes >= :p"), {"p": P}).mappings().all():
        c.execute(bk, {"t": "soc_day", "pk": json.dumps({"batch_id": r["batch_id"], "day": str(r["day"])}), "b": json.dumps({"bytes": int(r["bytes"])})})
        c.execute(text("UPDATE soc_day SET bytes = :b WHERE batch_id = :i AND day = :d"), {"b": int(r["bytes"]) % P, "i": r["batch_id"], "d": r["day"]})


def downgrade():
    pass
