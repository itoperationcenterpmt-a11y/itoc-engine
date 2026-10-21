# Panduan Keamanan dan Persiapan VAPT

Dokumen ini merangkum kontrol keamanan aplikasi, hasil audit terakhir, dan daftar yang harus dibereskan sebelum VAPT dan go-live.
Pemeriksaan otomatis konfigurasi: `docker compose exec api python -m app.cli security-check` (atau GET `/api/admin/security-check`, role admin). Hasilnya tidak memuat rahasia.

## 1. Kontrol yang sudah ada

| Area | Kontrol |
|---|---|
| Autentikasi | bcrypt, pesan galat sama untuk akun salah/tidak ada, waktu proses disamakan (anti enumerasi), kunci akun 5 gagal/10 menit dan 40 per alamat (dihitung dari audit_log, berlaku lintas worker), password minimal 10 karakter, maksimal 72 byte, tolak password lemah |
| Sesi | Cookie `itoc_session`: HttpOnly, SameSite=Strict, Secure otomatis lewat HTTPS. Tidak ada token di localStorage. Token memuat sidik jari password: ganti atau reset password membatalkan semua sesi lama. Masa berlaku `ITOC_JWT_MINUTES` |
| CSRF | SameSite=Strict ditambah header wajib `X-Requested-With: itoc` untuk semua perubahan data pada sesi cookie |
| Otorisasi | Seluruh rute `/api/*` wajib login kecuali login, `/api/public` (hanya teks tampilan), dan `/api/health`. Modul per role, `/api/admin` hanya admin (role admin_view hanya GET), unggah per sumber, putus sesi WiFi hanya role/username yang diizinkan, kunci lokasi per role (own/ho) |
| API key | Disimpan sebagai hash SHA-256, hanya GET, tanpa akses admin, bisa dicabut dan kedaluwarsa |
| Rahasia | Token dan password konektor, SMTP, URL webhook: terenkripsi Fernet di database, tidak pernah dikirim balik ke browser. `.env` tidak masuk git maupun image |
| Input | ORM dengan parameter terikat (tidak ada SQL dari string), validasi tipe oleh Pydantic, unggahan dibatasi ukuran (dibaca bertahap), ekstensi, jumlah dan total isi zip |
| Output | Seluruh data dari luar (nama host, SSID, hostname client, username) di-escape sebelum masuk HTML. Tidak ada handler inline. CSP: `script-src 'self'`, `object-src 'none'`, `frame-ancestors 'none'`, `base-uri 'self'` |
| Header | CSP, X-Frame-Options DENY, nosniff, Referrer-Policy, Permissions-Policy, COOP/CORP same-origin, HSTS (bila lewat HTTPS), `Cache-Control: no-store` untuk API, header Server dimatikan |
| SSRF | URL webhook dan Base URL konektor tidak boleh ke loopback, link-local (termasuk 169.254.169.254), multicast. Dicek saat simpan dan saat kirim, tanpa mengikuti redirect |
| Laju | Pembatas untuk ganti password, uji integrasi, putus sesi WiFi, unduh laporan |
| Log | audit_log: login berhasil dan gagal (dengan alamat), perubahan master/parameter/pengguna/integrasi, unggahan, unduhan laporan, putus sesi WiFi (siapa, client mana, alasan) |
| Container | Berjalan sebagai pengguna non-root, healthcheck, database hanya di 127.0.0.1 |
| Dependensi | pip-audit bersih untuk versi yang dipin di `backend/requirements.txt` |
| Produksi | Dengan `ITOC_ENV=production`: perintah seed-users/seed-demo diblokir dan server menolak start bila `ITOC_JWT_SECRET` lemah |

## 2. Perbaikan pada audit ini
1. Sesi dipindah dari localStorage ke cookie HttpOnly dengan perlindungan CSRF.
2. Token dibatalkan otomatis saat password diganti atau direset.
3. Penguncian akun dipindah ke database (sebelumnya per proses, sehingga dengan 2 worker batasnya longgar). Login gagal kini tercatat.
4. Aturan password: batas atas 72 byte (batas bcrypt), tolak password umum, sama dengan yang lama, atau mengandung username.
5. Penjaga SSRF untuk webhook dan konektor.
6. Unggahan dibaca bertahap dengan batas ukuran, sebelumnya dimuat penuh ke memori.
7. Pembatas laju untuk aksi sensitif.
8. Header tambahan (HSTS, COOP, CORP, object-src none), `Pragma: no-cache` untuk API.
9. Container non-root dan healthcheck.
10. Dependensi diperbarui: PyJWT 2.15.0, python-multipart 0.0.31, pypdf 6.19.0, cryptography 49.0.0, FastAPI 0.156.7 dan Starlette 1.9.0 (sebelumnya 4 paket dengan kerentanan yang diketahui).
11. Perintah `security-check` dan endpoint admin untuk memeriksa konfigurasi.

## 3. Yang harus dibereskan sebelum VAPT (butuh tindakan Anda)
1. **Password akun uji.** Akun bawaan seed (`superadmin`, `admin`, `itoc`, `itcare`, `eos`, `management`, `superadmin1`) memakai `password123`. Ini temuan Critical. Reset lewat Admin → Pengguna (Reset password) atau nonaktifkan, dan jangan jalankan `seed-users` lagi.
2. **`ITOC_ENV=production`** di `.env` server.
3. **HTTPS di depan aplikasi** (lihat contoh Nginx di bawah). Tanpa HTTPS, cookie tidak bertanda Secure dan HSTS tidak terkirim. Port 8000 jangan dibuka langsung ke jaringan; ubah pemetaan port menjadi `127.0.0.1:8000:8000` bila proxy ada di mesin yang sama.
4. **Rahasia**: `ITOC_JWT_SECRET` (min. 32 karakter acak), `ITOC_SECRET_KEY` terpisah, `DB_PASSWORD` kuat. Simpan `.env` dengan izin 600.
5. **Verifikasi TLS konektor** saat ini Tidak (sertifikat internal). Pasang sertifikat CA internal di server lalu aktifkan verifikasi bila memungkinkan; bila tidak, catat sebagai risiko yang diterima (jaringan internal).
6. **Jumlah Super Admin** dibatasi seperlunya, dan beri akun terpisah per orang.
7. Aktifkan **backup database terenkripsi** dan simpan di luar server.

## 4. Catatan dan risiko yang diterima
- CSP masih mengizinkan `style-src 'unsafe-inline'` karena antarmuka memakai atribut style. Skrip tetap hanya dari `'self'`, jadi risiko XSS berbasis skrip rendah.
- Pembatas laju bersifat per proses. Untuk perlindungan DoS yang sebenarnya, pasang pembatas di Nginx (contoh di bawah).
- Penguncian akun bisa dipakai penyerang untuk mengunci akun korban selama 10 menit (trade-off standar).
- Daftar personel (nama dan nomor telepon) dikirim ke semua role yang boleh login karena dipakai halaman Personnel dan Overview. Batasi bila kebijakan data pribadi mengharuskan.
- Data hasil tarik API disimpan di database; lindungi akses ke server dan backup.

## 5. Contoh Nginx (TLS)
```nginx
limit_req_zone $binary_remote_addr zone=itoc_login:10m rate=10r/m;
limit_req_zone $binary_remote_addr zone=itoc_api:10m rate=20r/s;

server {
    listen 80;
    server_name itoc.contoh.co.id;
    return 301 https://$host$request_uri;
}
server {
    listen 443 ssl http2;
    server_name itoc.contoh.co.id;
    ssl_certificate     /etc/ssl/itoc/fullchain.pem;
    ssl_certificate_key /etc/ssl/itoc/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;
    client_max_body_size 45m;

    location = /api/auth/login { limit_req zone=itoc_login burst=5 nodelay; proxy_pass http://127.0.0.1:8000; include /etc/nginx/itoc_proxy.conf; }
    location /api/ { limit_req zone=itoc_api burst=60 nodelay; proxy_pass http://127.0.0.1:8000; include /etc/nginx/itoc_proxy.conf; }
    location / { proxy_pass http://127.0.0.1:8000; include /etc/nginx/itoc_proxy.conf; }
}
# /etc/nginx/itoc_proxy.conf
#   proxy_set_header Host $host;
#   proxy_set_header X-Real-IP $remote_addr;
#   proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
#   proxy_set_header X-Forwarded-Proto $scheme;
```
Catatan: alamat klien yang dipakai penguncian login adalah alamat peer. Di belakang proxy, jalankan uvicorn dengan `--proxy-headers --forwarded-allow-ips=<IP proxy>` agar alamat asli tercatat.

## 6. Pemeliharaan
- Jalankan tiap bulan: `docker compose run --rm --no-deps --user root api sh -c "pip install -q pip-audit && pip-audit"` lalu perbarui `backend/requirements.txt` bila ada temuan, uji, dan build ulang.
- Perbarui image dasar (`python:3.12-slim`, `postgres:16-alpine`) secara berkala.
- Tinjau audit_log (login gagal, perubahan admin, putus sesi WiFi) secara rutin.