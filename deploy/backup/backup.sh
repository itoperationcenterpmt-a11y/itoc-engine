#!/bin/sh
# Backup PostgreSQL harian, dienkripsi dengan kunci PUBLIK age. Kunci privat tidak pernah ada di server, jadi backup yang bocor tidak bisa dibuka.
# Jalankan terus (jadwal BACKUP_AT) atau sekali: backup.sh once
set -eu
(set -o pipefail) 2>/dev/null && set -o pipefail
: "${BACKUP_AGE_RECIPIENT:?Isi BACKUP_AGE_RECIPIENT (kunci publik age, diawali age1) di .env}"
DIR=/backups; KEEP="${BACKUP_KEEP:-14}"; AT="${BACKUP_AT:-02:00}"; export PGPASSWORD="${DB_PASSWORD:-}"

run() {
  ts=$(date +%Y%m%d-%H%M); f="$DIR/itoc-$ts.dump.age"
  if pg_dump -h "${DB_HOST:-db}" -U "${DB_USER:-itoc}" -d "${DB_NAME:-itoc}" -Fc --no-owner | age -r "$BACKUP_AGE_RECIPIENT" -o "$f.part"; then
    mv "$f.part" "$f"
    (cd "$DIR" && sha256sum "itoc-$ts.dump.age" > "itoc-$ts.dump.age.sha256")
    echo "$(date '+%F %T') backup selesai: $f ($(wc -c < "$f") byte)"
    ls -1t "$DIR"/itoc-*.dump.age 2>/dev/null | tail -n +"$((KEEP + 1))" | while read -r old; do rm -f "$old" "$old.sha256"; done
  else
    rm -f "$f.part"; echo "$(date '+%F %T') BACKUP GAGAL" >&2; return 1
  fi
}

if [ "${1:-}" = "once" ]; then run; exit $?; fi
echo "Backup terjadwal setiap hari pukul $AT ($(date +%Z)), simpan $KEEP berkas terakhir di $DIR"
while true; do
  now=$(date +%s); next=$(date -d "$(date +%F) $AT:00" +%s)
  [ "$next" -le "$now" ] && next=$((next + 86400))
  sleep "$((next - now))"
  run || true
done
