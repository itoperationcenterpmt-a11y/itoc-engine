# Dashboard IT PMT — Python + PostgreSQL

Versi engine dari mockup `ITOC Dashboard Revisi`. Perhitungan pindah ke server (FastAPI), data dan seluruh konfigurasi di PostgreSQL. Frontend tetap tampilan yang sama, tetapi hanya merender hasil dari API.

## Menjalankan

```bash
cp .env.example .env          # isi DB_PASSWORD, ITOC_JWT_SECRET, kredensial konektor
docker compose up -d --build  # db + api (migrasi & seed konfigurasi otomatis) + worker sinkron
docker compose exec api python -m app.cli create-user superadmin1 "Super Admin 1" superadmin
docker compose exec api python -m app.cli seed-demo     # opsional, data dummy untuk mencoba
```
Dengan Caddy/proxy yang sudah ada di server: aplikasi listen di 127.0.0.1:8000 dan Caddy yang memberi HTTPS (contoh: `deploy/Caddyfile.example`). Tanpa proxy lain: buat sertifikat uji `sh deploy/gen-cert.sh <nama-host-atau-IP>` lalu `docker compose --profile proxy up -d`, dan buka https://localhost (peringatan browser muncul sampai sertifikat resmi dipasang). Login dengan password awal yang dicetak, lalu ganti password.

Setelah memperbarui kode dari versi sebelumnya (jalankan `docker compose up -d --build`; tabel `prtg_daily` dibuat otomatis oleh migrasi) (label menu, filter Jadwal, badge SOC), terapkan sekali ke database yang sudah ada. Perintah ini hanya menimpa tabel menu dan role, parameter yang sudah Anda ubah di Admin tidak disentuh:
```bash
docker compose exec api python -m app.cli seed-config --overwrite --only=modules,roles
```

## Unggah data mentah (RAW)

Menu **Kelengkapan Data → Unggah data mentah** menerima file apa adanya dari sumber, sebagai cadangan bila API bermasalah:

| Sumber | File | Catatan |
|---|---|---|
| SOC · Panorama | CSV custom report (11 laporan), banyak file sekaligus atau satu `.zip` | Jenis laporan dikenali dari header; file identik tidak dihitung dua kali |
| Service Desk · ManageEngine | Ekspor request `.xls` / `.xlsx` | Upsert per Request ID, aman diunggah ulang |
| NOC · PRTG | PDF laporan sensor (satu laporan = satu hari, semua Part), banyak file atau `.zip` | Tanggal dari Report Time Span; tersimpan per sensor per hari; tidak bisa dipilah per shift; hari yang sudah punya data per jam dari API tidak ditimpa |

## Role dan hak akses

Semua dari database (Admin → Master data → Role), tidak ada yang tertanam di kode: `modules` (menu yang terlihat; dicek juga di server), `can_write` (isi/tutup Handover), `uploads` (sumber RAW: `soc`, `tickets`, `prtg`, `*`), `is_admin` (boleh mengubah menu Admin), `admin_view` (boleh membuka menu Admin, hanya baca), dan `scope` (`all` semua lokasi, `ho` hanya kantor pusat, `own` hanya lokasi di akun user).

| Role | Menu | Data | Menulis |
|---|---|---|---|
| Super Admin | semua + Admin | semua lokasi | semuanya |
| Admin (koordinator ITOC Shift) | semua, Admin hanya baca | semua lokasi | Handover, unggah SOC/tiket/PRTG |
| ITOC Shift | Ringkasan, Service Desk, NOC, SOC, Personel, Report | semua lokasi | hanya lihat |
| IT Care | Ringkasan, Service Desk, NOC, Personel, Report (tanpa SOC) | Head Office saja | hanya lihat |
| EOS Branch | sama dengan IT Care | lokasi di akun (`user.site` wajib diisi) | hanya lihat |
| Management | Ringkasan, Service Desk, NOC, SOC, Personel, Report (tanpa Handover, Data, Admin) | semua lokasi | hanya lihat; boleh unduh Report |

Lokasi NOC dicocokkan ke nama device PRTG lewat nama site, alias di Master data → Lokasi, atau nama tanpa awalan "Branch ".

## Report

Menu **Report** mengunduh laporan Excel, PDF, atau PowerPoint dari angka yang sama dengan dashboard. Jenis laporan dipecah: **Summary** (high level), **Ticketing**, **Network SLA**, **SOC**, dan **Lengkap**; yang tampil mengikuti izin role. Judul dan subjudul tiap jenis bisa diubah di parameter `report.kinds`.

Grafik laporan adalah **widget** (Admin → Master data → Widget grafik): kode hanya menyediakan data tiap grafik (kolom `key`), sedangkan judul, jenis (`bar`, `stack`, `hbar`, `donut`, `line`), jumlah baris, urutan, aktif/tidak, grafik utama (`hero`, dipakai di Summary), dan preset (`ringkas`, `standar`, `lengkap`) diatur di database. Widget baru dari pembaruan aplikasi ditambahkan otomatis saat start tanpa menimpa pengaturan Anda. Judul kosong = memakai judul bawaan (judul grafik harian otomatis "per hari" atau "per minggu").

## Customize halaman

Di halaman Overview, Service Desk, NOC, dan SOC, Super Admin punya tombol **Customize**: urutan blok (▲ ▼), ukuran (S/M/L/XL/Full), judul, dan tampil/sembunyi. Pilih "Apply to": semua role, atau satu role tertentu (role yang punya pengaturan sendiri memakai itu; selain itu memakai pengaturan semua role; bila tidak ada, tampilan bawaan). Tersimpan di tabel `layout`; **Reset** mengembalikan ke bawaan. Blok baru dari pembaruan aplikasi otomatis muncul di akhir halaman.

Handover adalah sub-menu di dalam **Report** (kolom `parent` pada Master data → Modul / menu); hak aksesnya tetap lewat role (`modules` berisi `serahterima`). Filter periode, shift, dan lokasi sama dengan halaman lain. Bagian laporan (Service Desk, NOC, SOC) mengikuti izin role dan lokasi yang dikunci. Setiap unduhan tercatat di audit log.

Laporan PowerPoint dibuat dari template Pelindo di `backend/assets/template_pelindo.pptx` (diambil dari deck Ticketing: sampul, header gradien, logo Danantara dan Pelindo, slide Thank You dengan kartu kontak); slide contoh di template dibuang dan diganti isi laporan. Teks sampul dan kontak penutup diatur di Admin → Parameter → `report.company`, `report.subtitle`, `report.contact`. Untuk mengganti gaya, ganti file template itu (slide 1 = sampul, slide 2 = header isi, slide terakhir = penutup) lalu build ulang.
Menu Personel dibentuk dari parameter `personel` (Admin → Parameter → jadwal): tiap grup punya `kind` = `shift` (jadwal rotasi + lead), `office` (jam kantor, mis. IT Care) atau `branch` (daftar per branch). Anggota diisi di Master data → Personel dengan kolom `unit` yang sama. Nama dashboard dan footer ada di parameter `ui.brand_name` dan `ui.footer`.

Akun contoh per role, password `password123`, tanpa wajib ganti password (HANYA untuk uji/demo; ganti atau hapus sebelum produksi): `docker compose exec api python -m app.cli seed-users` (`--reset` untuk menimpa akun yang sudah ada). Username: superadmin, admin, itoc, itcare, eos, management.

Dummy anggota IT Care (aman diulang): `docker compose exec api python -m app.cli seed-demo-itcare`
## Struktur

```
backend/app/
  models.py          skema PostgreSQL (master/konfigurasi + data operasional)
  store.py           memuat konfigurasi dari DB + cache yang batal otomatis saat Admin/data berubah
  timeutil.py        shift & rotasi tim dari tabel shift/team + parameter rotation
  calc/              port rumus Excel: servicedesk.py, network.py, soc.py
  ingest/            manageengine.py (API v3 + Excel), prtg.py (historicdata API), panorama.py (impor + validasi)
  views.py           bundel data per halaman (/api/view/<halaman>)
  routers/           auth, dashboard (config, view, serah terima), admin (CRUD generik), ingest (unggah, sinkron)
  jobs.py, worker.py penjadwal sinkron (interval dari tabel data_source)
  cli.py, demo.py    migrasi, seed, akun, data dummy
backend/seed/defaults.json   nilai awal semua konfigurasi
frontend/            index.html + core.js (state, API) + views.js (tampilan) + main.js (event, Admin, login)
```

## Apa yang dulu hardcode, sekarang di mana

| Dulu di kode | Sekarang |
|---|---|
| Daftar menu, urutan, filter yang berlaku, catatan, badge "impor" | tabel `module` |
| Role dan akses menu | tabel `role` (+ `can_write`, `is_admin`), dicek di server |
| Lokasi (HO + branch) | tabel `site` |
| Personel, tim, koordinator, EOS, akun bersama | tabel `person`, `team` |
| Jam shift Pagi/Sore/Malam | tabel `shift` |
| Pola rotasi PP SS MM OO, tanggal anchor | parameter `rotation` |
| ISP dan target per ISP | tabel `isp` |
| Target SLA High/Medium/Low | tabel `sla_target` |
| Kapasitas link | tabel `prtg_sensor` |
| Target availability, cakupan, ambang utilisasi | parameter `net.*` |
| Status selesai, "Not Assigned", field wajib, kelompok durasi, dimensi, pemeriksaan kualitas | parameter `sd.*` |
| Rentang IP internal, zone internet, aplikasi diawasi, severity, tindakan | parameter `soc.*` |
| Kategori & prioritas serah terima, panjang minimal isian | parameter `ho.*` |
| Preset periode, nama hari/bulan, footer | parameter `ui.*` |
| Definisi rumus (tooltip i) | tabel `formula` |
| URL, interval, pemetaan field/kolom, nama channel PRTG, alamat sel Excel | tabel `data_source.config` (kredensial lewat env) |

Semua tabel di atas bisa diubah dari **Admin → Master data** dan **Admin → Parameter & target**. Setiap perubahan masuk `audit_log` dan langsung menghitung ulang semua halaman.

## API ringkas

- `POST /api/auth/login`, `POST /api/auth/password`
- `GET /api/config` — konfigurasi untuk frontend (sesuai role)
- `GET /api/view/{halaman}?from=&to=&shift=&site=&cmp=&sensor=` — angka halaman
- `POST /api/handover`, `POST /api/handover/{id}/close`
- `POST /api/ingest/soc` (xlsx Panorama), `POST /api/ingest/tickets` (xlsx ManageEngine), `POST /api/ingest/sync/{manageengine|prtg}`
- `GET|POST|PUT|DELETE /api/admin/master/{tabel}`, `GET|PUT /api/admin/params`, `POST|PATCH /api/admin/users`
- Dokumentasi interaktif: `/docs`

## Catatan

- Waktu disimpan sebagai jam lokal tanpa zona (sama seperti ekspor sumber); selisih zona di parameter `tz_offset_hours`.
- Kejadian downtime PRTG diturunkan dari jam berurutan yang ada downtime. Bila butuh menit persis, tambahkan pembacaan log sensor di `ingest/prtg.py`.
- Pemetaan field ManageEngine API (`api_fields`) dan nama channel PRTG (`channels`) perlu dicocokkan dengan instans Anda sebelum sinkron pertama.
- Cache hasil hitung ada di memori per proses (dibatalkan saat data/konfigurasi berubah, paling lambat 60 detik di proses lain). Untuk banyak server, ganti dengan Redis.
- Revisi skema berikutnya: `alembic revision --autogenerate -m "..."` lalu `python -m app.cli migrate`.
## Produksi (checklist sebelum naik server)
- **Rahasia:** salin `.env.example` ke `.env`, isi `ITOC_JWT_SECRET` dan `ITOC_SECRET_KEY` dengan string acak panjang (48+ karakter) dan `DB_PASSWORD` yang kuat. `.env` tidak ikut repository (`.gitignore`). Mengganti `ITOC_SECRET_KEY` setelah ada rahasia tersimpan membuat rahasia itu harus diisi ulang di Admin.
- **Mode produksi:** set `ITOC_ENV=production` agar `seed-demo`, `seed-demo-itcare`, dan `seed-users` (akun uji `password123`) diblokir. Buat akun asli dengan `python -m app.cli create-user`.
- **HTTPS:** dua pilihan. (1) Server sudah punya Caddy/proxy bersama: pakai `deploy/Caddyfile.example`, api hanya terbuka di 127.0.0.1:8000. (2) Tanpa proxy lain: container `proxy` (Nginx, profil `proxy`, `deploy/nginx.conf`) memegang port 80 dan 443; ganti `certs/tls.crt` dan `certs/tls.key` dengan sertifikat CA perusahaan lalu `docker compose restart proxy`. Port PostgreSQL hanya listen di `127.0.0.1`; di server, jangan dipublikasikan sama sekali (hapus bagian `ports` db di compose).
- **Dokumentasi API** (`/docs`) mati; nyalakan sementara dengan `ITOC_DOCS=true` hanya bila perlu.
- **Backup:** jadwalkan `pg_dump` harian dan uji restore. Volume `pgdata` adalah satu-satunya tempat data.
- **Akun uji:** nonaktifkan atau hapus semua akun `password123` sebelum dipakai pengguna sungguhan.
## Devices (Zabbix: CCTV dan Gate System)
- Konektor di Admin → Integrations → Zabbix: Base URL (IP atau host saja boleh), API token (terenkripsi), prefix host group, dan nama trigger yang berarti down. Sinkron tiap 5 menit.
- Kategori = prefix host group; labelnya di parameter `dev.kind_labels`. Kategori baru muncul otomatis di filter, grafik, dan katalog widget.
- Lokasi diambil dari kode di nama grup lewat Admin → Master Data → "Zabbix: kode ke lokasi" (kode baru terisi otomatis saat sinkron; isi lokasinya bila kosong).
- Peta memakai kolom `lat` dan `lon` di Master Data → Lokasi (nilai awal perkiraan, mohon dikoreksi). Peta berupa SVG mandiri tanpa server peta. Garis pantai dari `frontend/assets/id-map.json` (Natural Earth 1:50m Admin 0 Countries, domain publik, disederhanakan ke wilayah Indonesia, 58 KB); alamat berkasnya di parameter `dev.basemap_url` (kosongkan untuk peta tanpa garis pantai).
- Filter lokasi, kategori, dan status ada di bar filter halaman Devices. Widget Devices tersedia gabungan dan per kategori lewat Customize → Add widget.
