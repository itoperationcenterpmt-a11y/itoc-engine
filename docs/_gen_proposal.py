"""Generate 01-Proposal-TERA-Dashboard.docx and 01-Proposal-TERA-Dashboard.pptx."""
from _docgen_lib import (
    DOCS_DIR, DocBuilder, PelindoDeck,
    NAVY, BLUE, CYAN, INK, MUTED, PALE, AMBER, RED, GREEN, WHITE, W, M,
)


def build_proposal_docx():
    d = DocBuilder(
        doc_type="Proposal Implementasi Aplikasi",
        title="TERA Dashboard",
        subtitle="Platform Terpadu Telemetry, Evaluation, Reporting & Analytics untuk IT Operation Center (ITOC) PT Pelindo Multi Terminal",
        doc_code="ITOC-PROP-TERA-001",
        version="2.0",
        date_str="November 2026",
    )

    # 1. Ringkasan Eksekutif
    d.h1("1. Ringkasan Eksekutif")
    d.p(
        "Operasional Teknologi Informasi PT Pelindo Multi Terminal (SPMT) melayani lebih dari 30 lokasi terminal dan cabang "
        "di seluruh Indonesia selama 24 jam sehari, 7 hari seminggu. Saat ini, informasi operasional tersebar di berbagai "
        "perangkat pemantauan terpisah (ManageEngine ServiceDesk, PRTG, Zabbix, Ruckus vSZ, Palo Alto Panorama, Trend Micro "
        "Vision One XDR, Milestone XProtect CCTV, dan Uptime Kuma), sehingga tim ITOC (NOC, SOC, Service Desk, EOS cabang) "
        "maupun Manajemen memerlukan waktu tambahan untuk menyatukan data, menilai SLA, dan menyusun laporan rutin."
    )
    d.p(
        "TERA Dashboard (Telemetry, Evaluation, Reporting & Analytics) hadir sebagai pusat kendali operasional tunggal "
        "(Single Pane of Glass) yang dibangun secara mandiri, ringan, aman, dan sepenuhnya berada di infrastruktur internal "
        "PT Pelindo Multi Terminal (on-premise, tanpa ketergantungan layanan AI atau cloud pihak ketiga)."
    )
    d.callout(
        "Nilai Utama TERA Dashboard",
        "Menyatukan 8+ sumber data operasional ke dalam satu portal real-time, dilengkapi deteksi anomali statistik otomatis "
        "setiap 30 menit, TV/Wall Slideshow Mode untuk ruang kendali ITOC, laporan siap-kirim Excel/PDF/PPTX, serta integrasi "
        "Bot & Notifier WhatsApp/Telegram (baik interaktif dua arah maupun terjadwal mandiri).",
    )

    # 2. Latar Belakang & Permasalahan
    d.h1("2. Latar Belakang & Tantangan Operasional")
    d.table(
        ["Tantangan Saat Ini", "Dampak Operasional", "Solusi TERA Dashboard"],
        [
            ("Data tersebar di 8+ aplikasi", "Operator harus membuka banyak tab; visibilitas lintas domain terputus.", "Agregasi otomatis terpusat di 1 portal web responsif (Desktop, Mobile, TV Wall)."),
            ("Pemantauan ISP & redundansi manual", "Sulit melihat cabang yang kehilangan dual-link atau provider bermasalah.", "Monitoring live Zabbix ISP-* (54 link, 4 provider, 21 cabang dual-link) + SLA PRTG."),
            ("Laporan shift & manajemen lambat", "Rekap manual rawan salah ketik dan menyita waktu pergantian shift.", "9 template Shift Summary siap-salin WA/Telegram + ekspor 1-klik Excel/PDF/PPTX."),
            ("Deteksi gangguan bersifat reaktif", "Lonjakan tiket, alert XDR lama, atau AP offline baru disadari terlambat.", "Insight Engine statistik otomatis (baseline 4–8 minggu, deteksi lonjakan & forecast)."),
            ("Kebutuhan visibilitas per peran", "Manajemen, NOC, SOC, dan EOS cabang butuh sudut pandang berbeda.", "RBAC granular, Location Scope, dan Profile Switcher (Default, NOC Wall, Branch/EOS)."),
        ],
        col_widths=[4.4, 5.5, 6.7],
    )

    # 3. Konsep & Pilar TERA
    d.h1("3. Konsep Solusi: Empat Pilar TERA")
    d.bullets([
        ("T — Telemetry: ", "Penarikan data real-time dan terjadwal dari 8+ sistem pemantauan (API & fallback RAW upload) secara konsisten dan tervalidasi."),
        ("E — Evaluation: ", "Evaluasi SLA tiket, ketersediaan link & perangkat, kesehatan setiap cabang (Health Score 0–100), serta deteksi anomali statistik tanpa AI eksternal."),
        ("R — Reporting: ", "Pembuatan laporan profesional format Excel, PDF, dan PowerPoint (template resmi Pelindo), dilengkapi Share Link sementara (maks. 3 hari) tanpa perlu login."),
        ("A — Analytics: ", "Analisis tren harian/mingguan, peta sebaran perangkat Indonesia (Leaflet offline), matriks redundansi dual-link ISP, dan korelasi lintas sumber data."),
    ])

    # 4. Ruang Lingkup Integrasi & Modul
    d.h1("4. Ruang Lingkup Sumber Data & Modul Fungsional")
    d.table(
        ["Domain", "Sumber Data", "Metrik & Kapabilitas Utama"],
        [
            ("Overview & Wall Mode", "Lintas seluruh sumber", "4 gauge utama (Ticket SLA, Link, Device, Milestone), Needs Attention, On Duty shift, TV/Wall Slideshow Mode lintas menu."),
            ("Ticketing (Service Desk)", "ManageEngine ServiceDesk Plus", "Volume tiket, pencapaian SLA, distribusi durasi penyelesaian, ranking grup & teknisi, tiket open & overdue."),
            ("Network & ISP", "Zabbix (ISP-*), PRTG, Ruckus vSZ, Uptime Kuma", "Reachability live 54 link ISP per provider & cabang, matriks dual-link redundancy, SLA & utilisasi PRTG, status 186+ AP WiFi & client, monitor web."),
            ("Cyber Security (SOC)", "Palo Alto Panorama (NDR) & Trend Micro Vision One (XDR)", "Event ancaman harian, rasio alert-only vs blocked, Workbench XDR alert open >72 jam, detail payload & model deteksi."),
            ("Devices & CCTV", "Zabbix Infrastructure & Milestone XProtect", "Status 1.800+ perangkat (Network, CCTV, Operasional), peta lokasi interaktif, status kamera merekam & sinkronisasi 12 server Milestone + PA."),
            ("Personnel & Handover", "Master Internal TERA", "Jadwal rotasi shift tim ITOC otomatis, direktori personel, catatan serah terima shift (Handover) terintegrasi alert."),
            ("Insight & Notifier", "Engine Internal + API WA/Telegram", "Temuan otomatis (Critical/Warning/Info), Location Health, 9 template Shift Summary (Full, NOC, SOC, EOS, ISP, CCTV, WiFi, Device, Link), 17 slash command bot."),
            ("Admin & Tata Kelola", "Konfigurasi Terpusat (5 Grup / 19 Sub-Menu)", "Users, Roles, API Keys, Integrations, Mapping, Parameters, Email SMTP, Webhooks (WA/Telegram/Teams/Slack), Bot & Notifier API, Audit Log, Backup/Restore."),
        ],
        col_widths=[3.2, 4.4, 9.0],
    )

    # 5. Fitur Unggulan Terbaru (Versi 2.0)
    d.h1("5. Fitur Unggulan & Keunggulan Kompetitif")
    d.bullets([
        ("TV / Wall Slideshow Mode: ", "Tampilan layar kendali ITOC full-screen dengan rotasi slide otomatis (memecah halaman panjang secara cerdas tanpa memotong baris), rotasi lintas menu, kontrol keyboard (←/→/Space/Esc), dan pengaturan interval langsung dari Admin."),
        ("Monitoring ISP Live & Dual-Link Redundancy: ", "Deteksi otomatis seluruh host Zabbix berawalan ISP-* yang dikelompokkan per provider (Astinet, Lintasarta, JLM, NEUVIZ) dan cabang, lengkap dengan status Site Down / Single-Link Risk / Dual OK dan riwayat gangguan + MTTR."),
        ("Bot & Notifier API (WhatsApp & Telegram): ", "Mendukung 3 pola operasional: (1) Bot interaktif dua arah (/isp, /isp-belawan, /fullday, /noc, /eos, dll.), (2) Notifier terjadwal mandiri via API Key, dan (3) Push webhook otomatis saat terjadi insiden/handover."),
        ("Profil Tampilan Adaptif & Responsif: ", "Profile Switcher (Default, NOC Wall, Branch/EOS) + Customize Layout drag-and-drop; responsif penuh dari Mobile (390px), Tablet (768px), Laptop (1366px), Desktop (1440px) hingga Full HD / 4K Wall TV."),
        ("Keamanan Standar Enterprise (On-Premise): ", "Cookie HttpOnly + proteksi CSRF, enkripsi kredensial MultiFernet di database, proteksi SSRF (netguard), rate-limiting, lockout akun, audit log lengkap, serta backup/restore PostgreSQL terenkripsi."),
    ])

    # 6. Manfaat Bisnis & Indikator Keberhasilan
    d.h1("6. Manfaat Bisnis & Indikator Keberhasilan (KPI)")
    d.table(
        ["Aspek", "Indikator Keberhasilan", "Target Dampak"],
        [
            ("Kecepatan Deteksi (MTTD)", "Waktu identifikasi link ISP down, perangkat down massal, atau alert XDR kritis", "Turun > 60% berkat TV Wall Mode & push alert otomatis."),
            ("Efisiensi Pelaporan", "Waktu penyusunan laporan shift harian dan laporan bulanan manajemen", "Dari 30–60 menit manual menjadi < 1 menit (otomatis)."),
            ("Kepatuhan SLA", "Visibilitas tiket mendekati batas SLA (warning < 2 jam) & pemantauan link", "Meningkatkan kepatuhan SLA tiket >= 85% dan link >= 99,5%."),
            ("Kemandirian & Biaya", "Lisensi pihak ketiga & ketergantungan vendor eksternal", "Rp 0 biaya lisensi tambahan (100% open-source stack on-premise)."),
        ],
        col_widths=[3.6, 6.8, 6.2],
    )

    # 7. Roadmap Implementasi
    d.h1("7. Tahapan Implementasi & Operasionalisasi")
    d.table(
        ["Fase", "Aktivitas Utama", "Keluaran (Deliverable)"],
        [
            ("Fase 1 — Persiapan & Deployment", "Provisioning server Docker (DB, API, Worker), HTTPS reverse proxy (Caddy/Nginx), konfigurasi vault & SMTP.", "Aplikasi TERA live di jaringan internal dengan HTTPS aktif."),
            ("Fase 2 — Integrasi Sumber Data", "Aktivasi konektor API (ManageEngine, Zabbix, PRTG, Ruckus, Panorama, XDR, Milestone, Kuma) & pemetaan lokasi.", "Seluruh 8 sumber data tersinkronisasi terjadwal & tervalidasi."),
            ("Fase 3 — Operasionalisasi ITOC & Cabang", "Setup akun & role (Super Admin, ITOC, IT Care, EOS Cabang, Manajemen), TV Wall NOC, dan integrasi Bot WA/Telegram.", "Tim ITOC & EOS aktif menggunakan TERA untuk shift & pelaporan."),
            ("Fase 4 — Evaluasi & Optimalisasi", "Penyesuaian threshold Insight, jadwal backup otomatis harian, audit keamanan berkala, dan pelatihan lanjutan.", "Operasional stabil, terdokumentasi, dan terukur."),
        ],
        col_widths=[3.8, 7.2, 5.6],
    )

    # 8. Penutup
    d.h1("8. Penutup")
    d.p(
        "Implementasi TERA Dashboard merupakan langkah strategis Divisi Teknologi Informasi PT Pelindo Multi Terminal "
        "dalam mewujudkan operasi TI yang proaktif, transparan, terukur, dan terintegrasi di seluruh cabang pelabuhan. "
        "Dengan arsitektur on-premise yang matang, aman, serta dukungan pelaporan dan notifikasi instan, TERA Dashboard "
        "siap dioperasikan penuh sebagai tulang punggung pemantauan IT Operation Center (ITOC)."
    )

    out = DOCS_DIR / "01-Proposal-TERA-Dashboard.docx"
    d.save(out)
    return out


def build_proposal_pptx():
    dk = PelindoDeck(
        "PROPOSAL IMPLEMENTASI\nTERA DASHBOARD",
        "Telemetry, Evaluation, Reporting & Analytics\nIT Operation Center (ITOC) · Divisi Teknologi Informasi · PT Pelindo Multi Terminal",
    )

    # Slide 2: Ringkasan Eksekutif
    s = dk.slide("Ringkasan Eksekutif", "Menyatukan seluruh pemantauan operasional TI PT Pelindo Multi Terminal dalam satu kendali terpadu")
    dk.kpi_strip(s, 1.85, [
        ("8+ Sumber", "Integrasi Terpusat", "Ticketing, Network, SOC, CCTV, WiFi", NAVY),
        ("30+ Lokasi", "Cabang & Terminal", "Peta sebaran & Health Score", BLUE),
        ("24/7 Live", "TV Wall & Slideshow", "Auto-rotate & refresh otomatis", CYAN),
        ("9 Template", "Shift Summary & Bot", "WhatsApp, Telegram, Excel/PDF/PPTX", GREEN),
    ])
    dk.card(s, M, 3.35, 5.95, 3.55, "Latar Belakang", [
        ("Fragmentasi Tools: ", "Data operasional tersebar di ManageEngine, PRTG, Zabbix, Ruckus, Panorama, XDR, Milestone, dan Kuma."),
        ("Pelaporan Manual: ", "Rekap shift dan laporan manajemen menyita waktu serta rawan inkonsistensi."),
        ("Visibilitas Cabang: ", "Manajemen & EOS membutuhkan status kesehatan lokasi dan redundansi ISP secara instan."),
    ], accent=NAVY, body_size=12.5)
    dk.card(s, M + 6.25, 3.35, 5.95, 3.55, "Solusi TERA Dashboard", [
        ("Single Pane of Glass: ", "Portal web internal responsif (Desktop, Mobile, TV Wall) berbasis on-premise."),
        ("Insight Otomatis: ", "Deteksi anomali statistik (baseline 4–8 minggu) setiap 30 menit tanpa AI eksternal."),
        ("Siap Kirim: ", "Ekspor Excel/PDF/PPTX, Share Link 72 jam, serta Bot & Notifier WA/Telegram."),
    ], accent=BLUE, body_size=12.5)

    # Slide 3: Empat Pilar TERA
    s = dk.slide("Konsep Solusi: Empat Pilar TERA", "Fondasi operasional ITOC dari pengumpulan data hingga pengambilan keputusan cepat")
    cw = (W - 2 * M - 0.6) / 4
    pillars = [
        ("T · Telemetry", NAVY, ["Integrasi API 8+ sistem", "Sinkronisasi terjadwal otomatis", "Fallback RAW upload tervalidasi", "Monitoring live Zabbix ISP-*"]),
        ("E · Evaluation", BLUE, ["Evaluasi SLA tiket & link", "Location Health Score 0–100", "Deteksi anomali z-score", "Matriks redundansi dual-link"]),
        ("R · Reporting", CYAN, ["Ekspor Excel, PDF & PPTX", "Template resmi Pelindo", "9 template Shift Summary", "Share Link aman (maks. 72 jam)"]),
        ("A · Analytics", GREEN, ["Tren harian & perbandingan", "Peta perangkat Indonesia", "Ranking problem link & host", "Korelasi gangguan lintas sumber"]),
    ]
    for i, (t, acc, items) in enumerate(pillars):
        dk.card(s, M + i * (cw + 0.2), 1.9, cw, 4.95, t, items, accent=acc, title_size=15, body_size=12)

    # Slide 4: Ruang Lingkup Integrasi
    s = dk.slide("Ruang Lingkup Sumber Data & Modul", "Cakupan menyeluruh seluruh domain layanan TI ITOC PT Pelindo Multi Terminal")
    dk.table(s, M, 1.8, W - 2 * M, 5.1, ["Domain", "Sumber Data", "Kapabilitas Utama"], [
        ["Service Desk", "ManageEngine ServiceDesk Plus", "Volume tiket, kepatuhan SLA, durasi resolusi, ranking teknisi & grup, tiket overdue"],
        ["Network & ISP", "Zabbix (ISP-*), PRTG, Ruckus, Kuma", "Reachability 54 link ISP & dual-link redundancy, SLA PRTG, 186+ AP WiFi, monitor web"],
        ["Cyber Security", "Palo Alto Panorama & Trend Micro XDR", "Ancaman harian NDR, rasio alert-only vs blocked, alert XDR kritis/open >72 jam"],
        ["Devices & CCTV", "Zabbix Infra & Milestone XProtect", "1.800+ perangkat (Network/CCTV/Ops), peta Indonesia, 1.200+ kamera & 12 server Milestone"],
        ["Personnel & Shift", "Master Internal TERA", "Jadwal rotasi shift otomatis, direktori tim, Handover antar shift terintegrasi"],
        ["Insight & Admin", "Engine Internal & Bot API", "Deteksi anomali otomatis, 9 Shift Summary, Bot WA/Telegram, 19 sub-menu Admin"],
    ], col_ratios=[2.0, 3.4, 6.8], font_size=11)

    # Slide 5: Fitur Unggulan Operasional
    s = dk.slide("Fitur Unggulan Operasional (Versi 2.0)", "Dirancang khusus untuk kebutuhan ruang kendali NOC/SOC, EOS cabang, dan Manajemen")
    dk.card(s, M, 1.85, 5.95, 2.4, "TV / Wall Slideshow Mode", [
        ("Auto-Chunk Slides: ", "Memecah halaman panjang otomatis tanpa memotong baris widget."),
        ("Rotasi Lintas Menu: ", "Berpindah otomatis antar halaman & refresh data terjadwal."),
        ("Kendali Penuh: ", "Shortcut keyboard (←/→/Space/Esc) & interval diatur di Admin."),
    ], accent=NAVY, body_size=11.5)
    dk.card(s, M + 6.25, 1.85, 5.95, 2.4, "Monitoring ISP Live & Dual-Link", [
        ("Zabbix ISP-* Inline: ", "Terintegrasi di Network → ISP, Overview, NOC Wall, Insight, Report."),
        ("Grouping Provider & Cabang: ", "Astinet, Lintasarta, JLM, NEUVIZ + deteksi Single-Link Risk."),
        ("Histori & MTTR: ", "Riwayat gangguan, durasi downtime, dan top link bermasalah."),
    ], accent=BLUE, body_size=11.5)
    dk.card(s, M, 4.45, 5.95, 2.4, "Bot & Notifier WA / Telegram", [
        ("17 Slash Command: ", "/fullday, /isp, /isp-belawan, /noc, /soc, /eos, /cabang, /help."),
        ("Integrasi & Mandiri: ", "API Key untuk bot dua arah, cron terjadwal, & webhook push."),
        ("Admin Tester: ", "Uji command & salin snippet integrasi langsung di menu Admin."),
    ], accent=CYAN, body_size=11.5)
    dk.card(s, M + 6.25, 4.45, 5.95, 2.4, "Multi-Role & Multi-Device UX", [
        ("Profile Switcher: ", "Default, NOC Wall, dan Branch/EOS + kustomisasi drag-and-drop."),
        ("Responsif Penuh: ", "Optimal di 100% zoom (Laptop, Desktop, Tablet, Mobile, 4K TV)."),
        ("Dark & Light Theme: ", "Nyaman untuk shift pagi maupun ruang kendali malam hari."),
    ], accent=GREEN, body_size=11.5)

    # Slide 6: Arsitektur Ringkas & Keamanan
    s = dk.slide("Arsitektur On-Premise & Standar Keamanan", "100% berjalan di infrastruktur internal Pelindo tanpa ketergantungan cloud/AI eksternal")
    dk.card(s, M, 1.85, 5.95, 5.0, "Arsitektur Ringkas & Andal", [
        ("Containerized Stack: ", "3 container Docker utama: PostgreSQL 16, FastAPI/Uvicorn, dan Worker APScheduler."),
        ("Zero Build Frontend: ", "SPA ringan (Vanilla JS/CSS), aset font & peta Indonesia self-hosted (offline-ready)."),
        ("Reverse Proxy HTTPS: ", "Siap dipasang di belakang Caddy atau Nginx dengan TLS 1.2/1.3."),
        ("Backup & Restore Terpadu: ", "Ekspor/impor .sql langsung dari Super Admin + dukungan backup terenkripsi harian."),
    ], accent=NAVY, body_size=12.5)
    dk.card(s, M + 6.25, 1.85, 5.95, 5.0, "Keamanan Berlapis (Enterprise-Grade)", [
        ("Autentikasi Aman: ", "HttpOnly Cookie + CSRF header, lockout akun berbasis DB, rate-limiting API."),
        ("Vault Enkripsi Secret: ", "Semua token API, password integrasi, & URL webhook dienkripsi MultiFernet."),
        ("Proteksi SSRF (Netguard): ", "Mencegah akses keluar ke loopback/metadata cloud sambil mengizinkan LAN internal."),
        ("RBAC & Audit Trail: ", "Hak akses per menu & cabang, API Key terbatas role, serta log audit ekspor CSV."),
    ], accent=RED, body_size=12.5)

    # Slide 7: Manfaat Bisnis & KPI
    s = dk.slide("Manfaat Bisnis & Target Dampak (KPI)", "Dampak langsung terhadap kecepatan respon, efisiensi pelaporan, dan kepatuhan SLA")
    dk.table(s, M, 1.85, W - 2 * M, 4.95, ["Dimensi", "Kondisi Sebelumnya", "Dengan TERA Dashboard", "Target Dampak"], [
        ["Deteksi Insiden", "Manual cek banyak aplikasi", "TV Wall + Insight otomatis 30 menit + push alert", "MTTD turun > 60%"],
        ["Laporan Shift", "Rekap manual 30–60 menit", "9 template Shift Summary & bot WA/Telegram", "Selesai < 1 menit"],
        ["Laporan Manajemen", "Kompilasi manual bulanan", "1-klik Excel, PDF, PPTX + Share Link 72 jam", "Hemat > 80% waktu"],
        ["Kepatuhan SLA", "Terlambat tahu tiket overdue", "Peringatan < 2 jam + Health Score cabang", "SLA >= 85%, Link >= 99,5%"],
        ["Biaya Lisensi", "Potensi biaya tools BI mahal", "100% open-source on-premise internal", "Rp 0 lisensi tambahan"],
    ], col_ratios=[2.1, 3.0, 4.2, 2.9], font_size=11)

    # Slide 8: Roadmap Implementasi
    s = dk.slide("Tahapan Implementasi & Operasionalisasi", "Rencana penerapan terstruktur menuju operasional penuh ITOC & seluruh cabang")
    steps = [
        ("Fase 1", "Deployment", NAVY, ["Setup Docker host & DB", "Aktifkan HTTPS (Caddy/Nginx)", "Konfigurasi vault & SMTP", "Uji akses internal"]),
        ("Fase 2", "Integrasi", BLUE, ["Hubungkan 8 konektor API", "Validasi data & pemetaan", "Verifikasi ISP-* & Milestone", "Aktifkan jadwal sync"]),
        ("Fase 3", "Go-Live", CYAN, ["Setup user, role & EOS cabang", "Pasang TV/Wall Mode NOC", "Aktifkan Bot WA/Telegram", "Sosialisasi & serah terima"]),
        ("Fase 4", "Optimasi", GREEN, ["Tuning threshold Insight", "Jadwal backup harian", "Audit keamanan berkala", "Review KPI & feedback"]),
    ]
    for i, (f, sub, acc, items) in enumerate(steps):
        dk.card(s, M + i * (cw + 0.2), 1.9, cw, 4.95, f"{f} · {sub}", items, accent=acc, title_size=14, body_size=11.5)

    out = DOCS_DIR / "01-Proposal-TERA-Dashboard.pptx"
    n = dk.save(out)
    return out, n


if __name__ == "__main__":
    p1 = build_proposal_docx()
    p2, n = build_proposal_pptx()
    print(f"OK Proposal: {p1.name} & {p2.name} ({n} slides)")
