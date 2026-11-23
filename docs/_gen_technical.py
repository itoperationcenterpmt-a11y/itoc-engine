"""Generate 03-Detail-Teknis-TERA-Dashboard.docx and 03-Detail-Teknis-TERA-Dashboard.pptx."""
from _docgen_lib import (
    DOCS_DIR, DocBuilder, PelindoDeck,
    NAVY, BLUE, CYAN, INK, MUTED, PALE, AMBER, RED, GREEN, WHITE, W, M,
)


def build_technical_docx():
    d = DocBuilder(
        doc_type="Dokumen Detail Teknis (Technical Specification)",
        title="TERA Dashboard — Detail Teknis Aplikasi",
        subtitle="Arsitektur Sistem, Stack Teknologi, Skema Database, Konektor Integrasi, REST API, Keamanan, dan Panduan Operasional Deployment",
        doc_code="ITOC-TECH-TERA-003",
        version="2.0",
        date_str="November 2026",
    )

    # 1. Arsitektur Sistem & Topologi Container
    d.h1("1. Arsitektur Sistem & Topologi Container")
    d.p(
        "TERA Dashboard dirancang dengan arsitektur microservices ringan berbasis Docker Compose (on-premise) yang memisahkan "
        "lapisan penyimpanan (PostgreSQL 16), layanan API & penyaji antarmuka web (FastAPI/Uvicorn), serta layanan penjadwal "
        "latar belakang (APScheduler Worker) agar proses sinkronisasi data tidak pernah memengaruhi responsivitas antarmuka pengguna."
    )
    d.table(
        ["Layanan (Container)", "Image / Runtime", "Port & Jaringan", "Peran Utama"],
        [
            ("db", "postgres:16-alpine", "Internal 5432 (volume pgdata)", "Penyimpanan data master, telemetri operasional, secret terenkripsi, insight, dan audit log."),
            ("api", "python:3.12-slim (FastAPI + Uvicorn)", "Internal 9000 → Host 8000 / Reverse Proxy", "Menyajikan SPA frontend statis, seluruh REST API (/api/*), autentikasi, kalkulasi KPI, ekspor report, dan bot API."),
            ("worker", "python:3.12-slim (APScheduler)", "Internal only (no exposed port)", "Menjalankan sinkronisasi terjadwal 8 konektor API, evaluasi Insight Engine setiap 30 menit, dan push webhook."),
            ("proxy (opsional)", "Caddy / Nginx (TLS 1.2/1.3)", "Host 80 / 443 → api:9000", "Terminasi HTTPS, HTTP/2, HSTS, dan penerusan real client IP (X-Forwarded-For)."),
        ],
        col_widths=[2.8, 4.0, 3.8, 6.0],
    )

    # 2. Stack Teknologi & Struktur Kode
    d.h1("2. Stack Teknologi & Struktur Direktori")
    d.table(
        ["Lapisan", "Teknologi", "Catatan Implementasi"],
        [
            ("Backend API", "Python 3.12, FastAPI, Uvicorn, Pydantic v2", "Modular per router di backend/app/routers/ (10 modul router)."),
            ("ORM & Migrasi", "SQLAlchemy 2.0, Alembic (82 migrasi: 0001–0082)", "Migrasi idempoten, koneksi pooled, query terparametrisasi (bebas SQL injection)."),
            ("Konektor HTTP", "httpx (timeout & TLS verify configurable)", "Dilindungi SSRF guard (netguard.py) untuk seluruh URL keluar."),
            ("Ekspor Dokumen", "openpyxl (Excel), ReportLab (PDF), python-pptx (PPTX)", "Template resmi Pelindo di backend/assets/template_pelindo.pptx."),
            ("Keamanan & Kripto", "cryptography (MultiFernet), bcrypt/PBKDF2, secrets", "Enkripsi secret di DB, dukungan rotasi kunci tanpa downtime (rotate-key CLI)."),
            ("Frontend SPA", "Vanilla JavaScript (ES2020), HTML5, CSS3 Fluid", "Zero build step, lazy-loaded per halaman (ensurePage), self-hosted fonts & Leaflet basemap Indonesia."),
        ],
        col_widths=[2.8, 5.4, 8.4],
    )
    d.code(
        "itoc-engine/\n"
        "├── Dockerfile                  # Optimized multi-layer cache (Python 3.12 + pg_dump 16)\n"
        "├── docker-compose.yaml         # Services: db, api, worker (+ optional proxy/backup)\n"
        "├── backend/\n"
        "│   ├── alembic.ini & migrations/versions/ (0001 .. 0082_chat_commands_isp.py)\n"
        "│   └── app/\n"
        "│       ├── main.py, db.py, models.py, store.py, security.py, vault.py, netguard.py\n"
        "│       ├── insight.py, commands.py, notify.py, jobs.py, views.py, report*.py\n"
        "│       ├── routers/   (auth, dashboard, insight, report, share, admin, integrations, ingest, wifi, system)\n"
        "│       ├── calc/      (servicedesk, network, zbx_isp, devices, wifi, soc, xdr, cctv, kuma, insight, viz)\n"
        "│       └── ingest/    (manageengine, zabbix, prtg, prtg_pdf, ruckus, panorama*, trendmicro, milestone, uptimekuma)\n"
        "└── frontend/\n"
        "    ├── index.html (SPA shell + Fluid CSS + Dark/Light + TV/Wall Mode)\n"
        "    ├── core.js, common.js, widgets.js, viz.js, main.js\n"
        "    └── page-*.js, devices.js, wifi.js, xdr.js, cctv.js, kuma.js, internet.js, insight.js, admin.js, integrations.js"
    )

    # 3. Skema Database & Model Data
    d.h1("3. Skema Database Utama (PostgreSQL 16)")
    d.table(
        ["Kelompok Tabel", "Nama Tabel Utama", "Deskripsi Data"],
        [
            ("Akses & Keamanan", "app_user, role, api_key, secret, audit_log, share_link", "Akun pengguna, RBAC & module/scope, API key hash + expiry, vault terenkripsi MultiFernet, audit log, dan token share link."),
            ("Konfigurasi & Master", "app_parameter, module, widget, layout, profile, site, zbx_loc_map, dev_code, prtg_sensor, isp, person, team, shift, sla_target, formula", "Parameter dinamis (termasuk ui.wall_* & chat.commands), tata letak widget per profil/role, pemetaan cabang/ISP/sensor, dan master shift."),
            ("Service Desk", "ticket, ingest_batch", "Tiket ManageEngine (SLA, durasi, teknisi, grup, lokasi, status) & riwayat batch upload/sync."),
            ("Network & ISP", "prtg_hourly, prtg_daily, zbx_host, zbx_event, zbx_stat, wifi_ap, wifi_session, kuma_monitor, kuma_stat", "Data SLA/trafik PRTG, host & event Zabbix (termasuk host ISP-* untuk dual-link redundancy), AP & client Ruckus, monitor Uptime Kuma."),
            ("Cyber Security & CCTV", "soc_day, soc_top, xdr_alert, cctv_server, cctv_camera, cctv_hardware", "Ringkasan harian & top threat Panorama NDR, alert Workbench XDR (termasuk full payload), dan status kamera/server Milestone."),
            ("Operasional & Notifikasi", "handover, insight, webhook, data_source, sync_log", "Catatan serah terima shift, temuan anomali otomatis, tujuan webhook (WA/Telegram/Teams/Slack), status konektor & log sync."),
        ],
        col_widths=[3.2, 5.4, 8.0],
    )

    # 4. Integrasi Konektor & Engine Analitik
    d.h1("4. Integrasi Konektor, Insight Engine & Bot API")
    d.h2("4.1 Konektor Data (backend/app/ingest/)")
    d.bullets([
        ("ManageEngine ServiceDesk Plus: ", "REST API (inkremental + tiket tanpa last_updated_time) dan fallback upload Excel (.xls/.xlsx)."),
        ("Zabbix: ", "JSON-RPC API untuk seluruh host (Network, CCTV, Operasional) dan host berawalan ISP-* (reachability ICMP, provider dari zone/nama host, lokasi dari subzone/ZbxLocMap, riwayat event zbx_event)."),
        ("PRTG Network Monitor: ", "API sensor availability/traffic per jam & fallback parsing laporan PDF harian."),
        ("Ruckus vSZ (WiFi): ", "Read-only API untuk status Access Point, zona, SSID, client aktif, dan kekuatan sinyal."),
        ("Palo Alto Panorama & Trend Micro XDR: ", "XML/REST API harian + Top report (Panorama) dan Workbench Alert API dengan auto-detect region (Trend Micro)."),
        ("Milestone XProtect & Uptime Kuma: ", "REST API multi-server dengan IDP login (Milestone) dan API/metrics monitor web (Uptime Kuma)."),
    ])

    d.h2("4.2 Insight Engine & Perhitungan ISP (zbx_isp.py)")
    d.p(
        "Insight Engine (backend/app/insight.py) berjalan setiap 30 menit secara deterministik (tanpa AI eksternal): "
        "membandingkan nilai terbaru terhadap baseline median dan deviasi 4–8 minggu sebelumnya (z-score), menghitung tren "
        "kemiringan 21 hari untuk memprediksi pelanggaran target SLA, mengecualikan perangkat dalam status maintenance, "
        "serta menutup temuan secara otomatis saat kondisi kembali normal."
    )
    d.p(
        "Modul zbx_isp.py memfilter seluruh host Zabbix dengan nama berawalan ISP- (atau dev_code='ISP'), menilai status "
        "online (up + degraded SNMP saat ICMP tetap aktif) vs down (ICMP unreachable), mengelompokkan per provider & lokasi, "
        "dan menghitung redundansi cabang (Dual OK, Single-Link Risk, Site Down, Single Link) beserta MTTR dari zbx_event."
    )

    # 5. Daftar Endpoint REST API Utama
    d.h1("5. Daftar Endpoint REST API Utama")
    d.table(
        ["Prefix / Endpoint", "Method", "Autentikasi", "Fungsi"],
        [
            ("/api/public", "GET", "Publik", "Metadata brand, login info, dan build stamp untuk deteksi versi baru."),
            ("/api/auth/login, /logout, /me, /password", "POST / GET", "Cookie / Session", "Autentikasi cookie HttpOnly, cek sesi, dan ubah kata sandi mandiri."),
            ("/api/config", "GET", "Session / API Key", "Master data, parameter, role, profil, layout, dan modul sesuai hak akses."),
            ("/api/view/{tab}", "GET", "Session / API Key", "Bundle data terhitung untuk halaman (ringkasan, servicedesk, noc, wifi, soc, xdr, devices, cctv, insight, dll.)."),
            ("/api/insights/commands", "GET", "Session / API Key", "Katalog seluruh slash command aktif (nama, alias, kind, scope, branch_arg, help)."),
            ("/api/insights/command?text=...&format=text|json", "GET", "Session / API Key", "Eksekusi perintah bot WA/Telegram (/isp, /fullday, /eos-belawan, /help)."),
            ("/api/insights/summary?scope=...&kind=...&site=...", "GET", "Session / API Key", "Tarik teks 9 template Shift Summary untuk notifier terjadwal mandiri."),
            ("/api/report/{xlsx|pdf|pptx} & /api/report-share", "GET / POST", "Session / API Key", "Generate file laporan resmi & pembuatan Share Link sementara (maks. 72 jam)."),
            ("/api/admin/{users|roles|apikeys|integrations|webhooks|smtp|params|master|audit|system}", "CRUD", "Admin / Super Admin", "Pengelolaan penuh seluruh 19 sub-menu Admin, test webhook/SMTP, dan backup/restore .sql."),
        ],
        col_widths=[5.2, 2.0, 2.8, 6.6],
    )

    # 6. Arsitektur Keamanan
    d.h1("6. Arsitektur Keamanan & Kepatuhan")
    d.bullets([
        ("Autentikasi & Sesi: ", "Token sesi disimpan dalam cookie HttpOnly + SameSite, proteksi CSRF melalui header wajib X-Requested-With: itoc untuk seluruh mutasi, serta lockout akun berbasis database setelah percobaan gagal berulang."),
        ("Enkripsi Kredensial (Vault): ", "Seluruh password integrasi, API token pihak ketiga, SMTP password, dan URL webhook dienkripsi menggunakan MultiFernet sebelum disimpan ke PostgreSQL (write-only di UI, tidak pernah dikembalikan ke browser)."),
        ("SSRF Protection (netguard.py): ", "Memvalidasi setiap URL keluar (konektor & webhook) saat disimpan maupun saat dieksekusi agar memblokir loopback (127.0.0.0/8), link-local/cloud metadata (169.254.169.254), dan multicast, namun tetap mengizinkan IP RFC 1918 internal."),
        ("RBAC, Location Scope & Page Lock: ", "Otorisasi ditegakkan di sisi server (can_see, effective_site, require_admin, admin.locked_pages). API Key mewarisi hak akses role dan batasan cabang."),
        ("Audit & Hardening: ", "Audit trail untuk login, mutasi konfigurasi, ekspor CSV (formula-safe), dan perintah bot; container berjalan sebagai non-root user (uid 10001); CSP ketat tanpa ketergantungan CDN eksternal."),
    ])

    # 7. Deployment, Backup & Pemeliharaan
    d.h1("7. Panduan Deployment, Migrasi & Backup")
    d.code(
        "# 1. Build & jalankan seluruh container\n"
        "docker compose up -d --build\n\n"
        "# 2. Jalankan migrasi skema database terbaru (Alembic 0082)\n"
        "docker compose exec -T api alembic upgrade head\n\n"
        "# 3. Cek kesehatan container & log\n"
        "docker compose ps\n"
        "docker compose logs --tail=100 api worker\n\n"
        "# 4. Backup manual PostgreSQL (atau lewat Admin > System > Backup & Restore)\n"
        "docker compose exec -T db pg_dump -U itoc itoc > backup-$(date +%Y%m%d).sql"
    )
    d.callout(
        "Catatan Operasional Penting",
        "Simpan kunci enkripsi (.env SECRET_KEY / FERNET_KEY) terpisah dari file backup .sql. Tanpa kunci enkripsi yang sama, "
        "kredensial integrasi dan URL webhook yang tersimpan terenkripsi di database tidak dapat didekripsi setelah restore.",
    )

    out = DOCS_DIR / "03-Detail-Teknis-TERA-Dashboard.docx"
    d.save(out)
    return out


def build_technical_pptx():
    dk = PelindoDeck(
        "DETAIL TEKNIS APLIKASI\nTERA DASHBOARD",
        "Arsitektur Sistem, Database, Integrasi API, Keamanan & Deployment\nIT Operation Center (ITOC) · Divisi Teknologi Informasi · PT Pelindo Multi Terminal",
    )

    # Slide 2: Arsitektur Sistem & Container
    s = dk.slide("Arsitektur Sistem & Topologi Container", "Desain on-premise modular berbasis Docker Compose dengan pemisahan API, Worker, dan Database")
    dk.kpi_strip(s, 1.85, [
        ("PostgreSQL 16", "Database Utama", "82 migrasi Alembic (0001–0082)", NAVY),
        ("FastAPI", "Backend Python 3.12", "10 router API + 11 modul calc", BLUE),
        ("APScheduler", "Worker Terpisah", "Sync 8 sumber + Insight 30 mnt", CYAN),
        ("Vanilla SPA", "Zero-Build Frontend", "Lazy-load, offline fonts & map", GREEN),
    ])
    dk.card(s, M, 3.35, 5.95, 3.5, "Alur Data & Pemrosesan", [
        ("1. Ingest: ", "Worker menarik data via API (8 konektor) atau operator mengunggah RAW file tervalidasi."),
        ("2. Storage: ", "Data dinormalisasi ke PostgreSQL 16; kredensial & webhook dienkripsi MultiFernet."),
        ("3. Analytics: ", "Modul calc/ & insight.py menghitung KPI, SLA, dual-link ISP, dan z-score anomali."),
        ("4. Delivery: ", "Disajikan ke Web SPA, TV Wall Mode, Report (XLSX/PDF/PPTX), dan Bot WA/Telegram."),
    ], accent=NAVY, body_size=12)
    dk.card(s, M + 6.25, 3.35, 5.95, 3.5, "Keunggulan Teknis Arsitektur", [
        ("Non-Blocking UI: ", "Sinkronisasi berat berjalan di container worker terpisah."),
        ("Offline-Ready: ", "Font (Plus Jakarta Sans, Inter, IBM Plex Mono) & peta Indonesia self-hosted."),
        ("Fast Rebuild: ", "Dockerfile multi-layer cache (rebuild frontend/backend ~10 detik)."),
        ("Non-Root Runtime: ", "Container berjalan sebagai user app (UID 10001) demi keamanan."),
    ], accent=BLUE, body_size=12)

    # Slide 3: Stack Teknologi & Struktur Modul
    s = dk.slide("Stack Teknologi & Struktur Kode", "Komponen open-source teruji tanpa ketergantungan vendor atau cloud eksternal")
    dk.table(s, M, 1.8, W - 2 * M, 5.05, ["Lapisan", "Teknologi", "Direktori / Modul Utama"], [
        ["Backend API", "Python 3.12, FastAPI, Uvicorn, Pydantic v2", "backend/app/routers/ (auth, dashboard, insight, report, share, admin, integrations, ingest, wifi, system)"],
        ["ORM & Migrasi", "SQLAlchemy 2.0, Alembic (82 revisi)", "backend/app/models.py & backend/migrations/versions/0001..0082"],
        ["Calc & Insight", "Pure Python + SQL agregasi + z-score", "backend/app/calc/ (servicedesk, network, zbx_isp, devices, wifi, soc, xdr, cctv, kuma) & insight.py"],
        ["Konektor Ingest", "httpx, XML/JSON-RPC, pypdf, openpyxl", "backend/app/ingest/ (manageengine, zabbix, prtg, ruckus, panorama, trendmicro, milestone, uptimekuma)"],
        ["Report & Notifier", "openpyxl, ReportLab, python-pptx, SMTP", "report.py, report_pdf.py, report_pptx.py, commands.py, notify.py"],
        ["Frontend SPA", "Vanilla JS (ES2020), CSS3 Fluid, Leaflet", "frontend/ (index.html, core.js, common.js, widgets.js, viz.js, main.js, page-*.js, admin.js)"],
    ], col_ratios=[2.1, 3.9, 6.2], font_size=10.8)

    # Slide 4: Skema Database
    s = dk.slide("Skema Database Utama (PostgreSQL 16)", "Pemisahan jelas antara data master, konfigurasi dinamis, telemetri, dan audit keamanan")
    cw = (W - 2 * M - 0.4) / 3
    db_cards = [
        ("Akses & Keamanan", NAVY, ["app_user, role (RBAC & scope)", "api_key (hashed + expiry)", "secret (MultiFernet vault)", "audit_log & share_link"]),
        ("Master & Layout", BLUE, ["app_parameter (SLA, wall, chat)", "module, widget, layout, profile", "site, zbx_loc_map, dev_code", "prtg_sensor, isp, person, shift"]),
        ("Service Desk & Ops", CYAN, ["ticket (ManageEngine SLA)", "ingest_batch & sync_log", "handover (serah terima shift)", "insight (temuan & status)"]),
        ("Network & ISP", GREEN, ["zbx_host (incl. ISP-* hosts)", "zbx_event & zbx_stat (MTTR)", "prtg_hourly & prtg_daily", "wifi_ap, wifi_session, kuma_*"]),
        ("Cyber & CCTV", RED, ["soc_day & soc_top (Panorama)", "xdr_alert (+ full JSON payload)", "cctv_server & cctv_camera", "cctv_hardware (Milestone)"]),
        ("Notifikasi & Sumber", AMBER, ["data_source (jadwal & mode)", "webhook (WA/TG/Teams/Slack)", "Encrypted URL & last_status", "Audit trail semua push & bot"]),
    ]
    for i, (t, acc, items) in enumerate(db_cards):
        row, col = divmod(i, 3)
        dk.card(s, M + col * (cw + 0.2), 1.85 + row * 2.55, cw, 2.35, t, items, accent=acc, title_size=13.5, body_size=11)

    # Slide 5: REST API & Integrasi Notifier
    s = dk.slide("Antarmuka REST API & Integrasi Notifier", "Endpoint terstandarisasi untuk Web SPA, Bot WA/Telegram, dan sistem eksternal")
    dk.table(s, M, 1.8, W - 2 * M, 5.05, ["Endpoint", "Method", "Auth", "Fungsi"], [
        ["/api/auth/{login,logout,me,password}", "POST/GET", "Cookie", "Login sesi HttpOnly, cek sesi aktif, ubah password"],
        ["/api/config & /api/view/{tab}", "GET", "Cookie / Key", "Konfigurasi UI & bundle data terhitung per halaman"],
        ["/api/insights/commands", "GET", "Cookie / Key", "Katalog 17 slash command aktif + alias & parameter cabang"],
        ["/api/insights/command?text=...", "GET", "Cookie / Key", "Eksekusi perintah bot interaktif WA/Telegram (text/json)"],
        ["/api/insights/summary?kind=...", "GET", "Cookie / Key", "Tarik 9 template Shift Summary (full/noc/soc/eos/isp/dll.)"],
        ["/api/report/{xlsx,pdf,pptx}", "GET", "Cookie / Key", "Generate laporan resmi + /api/report-share (maks. 72 jam)"],
        ["/api/admin/*", "CRUD", "Admin", "Users, Roles, API Keys, Integrations, Webhooks, Audit, Backup"],
    ], col_ratios=[3.6, 1.4, 1.8, 5.4], font_size=10.8)

    # Slide 6: Arsitektur Keamanan
    s = dk.slide("Arsitektur Keamanan & Perlindungan Data", "Defense-in-depth sesuai standar operasional lingkungan korporasi Pelindo")
    dk.card(s, M, 1.85, 5.95, 5.0, "Autentikasi, Otorisasi & Enkripsi", [
        ("Session Hardening: ", "Cookie HttpOnly + SameSite; mutasi wajib header CSRF X-Requested-With: itoc."),
        ("Brute-Force Defense: ", "Rate-limiting per endpoint & lockout akun berbasis database."),
        ("MultiFernet Vault: ", "Enkripsi simetris untuk token API, password SMTP/konektor, & URL webhook (write-only)."),
        ("RBAC & Scope: ", "Validasi role, menu, lokasi cabang, dan kunci halaman Super Admin di level server."),
    ], accent=NAVY, body_size=12)
    dk.card(s, M + 6.25, 1.85, 5.95, 5.0, "Jaringan, Input & Auditabilitas", [
        ("SSRF Guard (netguard.py): ", "Blokir loopback, link-local, metadata cloud (169.254.169.254), dan multicast; izinkan LAN RFC 1918."),
        ("Upload & Query Safety: ", "Batas ukuran file, validasi ekstensi, ORM terparametrisasi, CSV formula-safe."),
        ("CSP & Self-Hosted Assets: ", "Tidak memuat font/script dari CDN publik; meminimalkan permukaan serangan."),
        ("Audit Trail Lengkap: ", "Mencatat login, perubahan setting, ekspor data, perintah bot, & aksi backup/restore."),
    ], accent=RED, body_size=12)

    # Slide 7: Deployment, Backup & Operasional
    s = dk.slide("Deployment, Backup & Pemeliharaan Sistem", "Prosedur operasional ringkas untuk tim infrastruktur & Super Admin")
    dk.card(s, M, 1.85, 5.95, 4.95, "Prosedur Deployment & Update", [
        ("1. Build & Start: ", "docker compose up -d --build (menjalankan db, api, worker)."),
        ("2. Migrasi Skema: ", "docker compose exec -T api alembic upgrade head (skema terbaru: 0082)."),
        ("3. HTTPS Reverse Proxy: ", "Pasang Caddy atau Nginx di depan port internal 9000/8000 dengan TLS 1.2/1.3."),
        ("4. Verifikasi: ", "Cek docker compose ps, Source Status di Admin, dan endpoint /api/public."),
    ], accent=NAVY, body_size=12)
    dk.card(s, M + 6.25, 1.85, 5.95, 4.95, "Backup, Restore & Rotasi Kunci", [
        ("Backup via UI: ", "Admin → System → Backup & Restore → Download backup .sql (pg_dump)."),
        ("Restore Aman: ", "Server otomatis membuat safety backup sebelum menimpa database; wajib konfirmasi RESTORE."),
        ("Backup Harian Terenkripsi: ", "Mendukung profil compose backup harian terenkripsi kunci publik (age)."),
        ("Penting (.env Keys): ", "Cadangkan SECRET_KEY / FERNET_KEY terpisah dari .sql; dukung rotasi kunci via CLI."),
    ], accent=GREEN, body_size=12)

    out = DOCS_DIR / "03-Detail-Teknis-TERA-Dashboard.pptx"
    n = dk.save(out)
    return out, n


if __name__ == "__main__":
    p1 = build_technical_docx()
    p2, n = build_technical_pptx()
    print(f"OK Technical: {p1.name} & {p2.name} ({n} slides)")
