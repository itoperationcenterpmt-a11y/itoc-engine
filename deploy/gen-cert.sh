#!/bin/sh
# Sertifikat self-signed untuk uji: sh deploy/gen-cert.sh [nama-host-atau-IP ...]
# Produksi: ganti certs/tls.crt (fullchain) dan certs/tls.key dengan sertifikat dari CA perusahaan, lalu: docker compose restart proxy
set -e
export MSYS_NO_PATHCONV=1   # Git Bash di Windows tidak boleh mengubah path di dalam container
cd "$(dirname "$0")/.."
mkdir -p certs
SAN="DNS:localhost,IP:127.0.0.1"
for h in "$@"; do
  case "$h" in *[!0-9.]*) SAN="$SAN,DNS:$h" ;; *) SAN="$SAN,IP:$h" ;; esac
done
docker run --rm -v "$(pwd)/certs:/certs" alpine/openssl req -x509 -nodes -newkey rsa:2048 -days 825 \
  -keyout /certs/tls.key -out /certs/tls.crt -subj "/O=Pelindo Multi Terminal/CN=${1:-localhost}" -addext "subjectAltName=$SAN"
echo "Sertifikat dibuat di certs/ (SAN: $SAN)"
