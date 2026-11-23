"""Generate 02-User-Manual-TERA-Dashboard.docx and 02-User-Manual-TERA-Dashboard.pptx."""
from _docgen_lib import (
    DOCS_DIR, DocBuilder, PelindoDeck,
    NAVY, BLUE, CYAN, INK, MUTED, PALE, AMBER, RED, GREEN, WHITE, W, M,
)


def build_manual_docx():
    d = DocBuilder(
        doc_type="Panduan Pengguna (User Manual)",
        title="TERA Dashboard — User Manual",
        subtitle="Panduan Operasional Lengkap Penggunaan Portal, Monitoring, TV/Wall Mode, Pelaporan, Shift Summary, Bot WA/Telegram, dan Administrasi",
        doc_code="ITOC-UM-TERA-002",
        version="2.0",
        date_str="November 2026",
    )

    # 1. Pendahuluan & Akses Awal
    d.h1("1. Pendahuluan & Login Aplikasi")
    d.p(
        "TERA Dashboard dapat diakses melalui browser modern (Chrome, Edge, Firefox, Safari) di Desktop, Laptop, Tablet, "
        "Smartphone, maupun layar TV Ruang Kendali ITOC. Tampilan otomatis menyesuaikan resolusi dan optimal pada zoom 100%."
    )
    d.h2("1.1 Cara Masuk (Sign In) & Ubah Kata Sandi")
    d.bullets([
        ("Langkah 1: ", "Buka URL TERA Dashboard (mis. https://tera.pelindomultiterminal.co.id)."),
        ("Langkah 2: ", "Masukkan Username dan Password yang diberikan oleh Admin ITOC, lalu klik Sign in."),
        ("Login Pertama: ", "Jika akun baru dibuat atau baru di-reset, sistem akan mewajibkan penggantian password (minimal 10 karakter, tidak mudah ditebak)."),
        ("Ubah Password Mandiri: ", "Klik User Pill (avatar & nama Anda) di pojok kanan atas → pilih Change password."),
        ("Keluar (Sign Out): ", "Klik User Pill di pojok kanan atas → pilih Sign out."),
    ])

    # 2. Navigasi Utama & Kontrol Header
    d.h1("2. Navigasi, Filter Global & Mode Tampilan")
    d.h2("2.1 Sidebar & Header Kanan Atas")
    d.table(
        ["Elemen UI", "Lokasi", "Fungsi"],
        [
            ("Sidebar Menu & Rail Toggle (‹)", "Kiri layar", "Navigasi antar modul utama & sub-menu. Klik tombol ‹ untuk mengecilkan sidebar menjadi icon rail."),
            ("On Duty Chip", "Header kanan atas", "Menampilkan tim & shift yang sedang bertugas beserta jam WIB real-time."),
            ("TV / Wall Slideshow Mode", "Ikon monitor (kanan atas)", "Masuk mode layar penuh ruang kendali dengan slideshow otomatis antar baris widget & lintas menu."),
            ("Theme Switcher", "Ikon bulan (kanan atas)", "Beralih cepat antara Light Mode dan Dark Mode (tersimpan otomatis di browser)."),
            ("Profile Switcher", "Ikon grid 2×2 (kanan atas)", "Beralih preset tata letak dashboard: Default, NOC Wall, atau Branch / EOS."),
            ("Customize Layout", "Ikon slider (Super Admin)", "Mengubah urutan (drag-and-drop), ukuran (S/M/L/XL/Full), judul, dan menambah/menyembunyikan widget."),
            ("User Pill", "Pojok kanan atas", "Menampilkan nama & role akun aktif, akses cepat Change password dan Sign out."),
        ],
        col_widths=[4.0, 3.6, 9.0],
    )

    d.h2("2.2 Filter Bar Seragam")
    d.p(
        "Seluruh halaman analitik berbagi filter global yang konsisten: Preset Periode (Today, Yesterday, 7 days, 30 days, "
        "This month, Last month), rentang tanggal kustom, Shift (All/Pagi/Sore/Malam), Lokasi/Cabang, checkbox Compare "
        "(perbandingan dengan periode sebelumnya), dan tombol Reset. Pada menu non-Devices, filter diringkas menjadi 1 baris "
        "ramping; pada menu Devices, filter lengkap (Category, Group, Type, Status) tetap tampil penuh."
    )

    d.h2("2.3 Menggunakan TV / Wall Slideshow Mode")
    d.bullets([
        ("Aktivasi: ", "Klik ikon monitor (TV / Wall Slideshow Mode) di pojok kanan atas dari halaman mana saja."),
        ("Auto-Chunking: ", "Halaman panjang otomatis dipecah menjadi beberapa slide tanpa memotong baris widget yang sejajar."),
        ("Kontrol Dark Command Bar: ", "Navigasi slide (‹ / ›), Pause/Resume (⏸/▶), ubah durasi slide cepat (10s–60s), toggle Rotate menus / Loop this page, countdown auto-refresh, dan tombol Exit (Esc)."),
        ("Shortcut Keyboard: ", "Panah Kiri (←) = slide sebelumnya, Panah Kanan (→) = slide berikutnya, Spasi (Space) = jeda/lanjut, Escape (Esc) = keluar dari TV Mode."),
        ("Pengaturan Default Admin: ", "Durasi slide, interval refresh data, dan daftar menu rotasi dapat diatur permanen di Admin → Operations → Targets & Parameters (bagian Appearance)."),
    ])

    # 3. Panduan Modul Operasional
    d.h1("3. Panduan Penggunaan per Modul")
    d.h2("3.1 Overview")
    d.p("Menampilkan ringkasan eksekutif 4 gauge utama (Ticket SLA, Link availability, Device availability, Milestone servers), panel Needs Attention (temuan prioritas yang dapat diklik langsung ke modul terkait), tim On Duty saat ini, serta kartu ringkasan tiap domain.")

    d.h2("3.2 Ticketing (Service Desk)")
    d.p("Memantau performa tiket ManageEngine: volume tiket, tingkat kepatuhan SLA, tren harian, distribusi durasi penyelesaian, pola per jam/hari, ranking grup & teknisi, daftar Open Tickets, serta 25 tiket berdurasi terlama.")

    d.h2("3.3 Network (Summary, ISP, WiFi, Internet, Web)")
    d.bullets([
        ("Network · Summary: ", "Ringkasan terpadu link ISP (Zabbix & PRTG), WiFi Access Points, utilisasi internet, dan status web."),
        ("Network → ISP: ", "Menggabungkan monitoring live Zabbix host ISP-* (status reachability per provider Astinet/Lintasarta/JLM/NEUVIZ, matriks dual-link redundancy cabang, riwayat gangguan & MTTR, tabel perangkat ISP) dengan data SLA & utilisasi PRTG."),
        ("Network → WiFi: ", "Status Access Point online/offline per lokasi/zona, jumlah client aktif, sinyal lemah, dan pencarian AP/client."),
        ("Network → Internet & Web: ", "Utilisasi trafik firewall/bandwidth dan ketersediaan monitor web (Uptime Kuma)."),
    ])

    d.h2("3.4 Cyber Security (Summary, NDR, XDR)")
    d.p("Memantau postur keamanan siber: event ancaman harian Palo Alto Panorama (NDR) beserta rasio alert-only vs blocked, serta Workbench Alert Trend Micro Vision One (XDR) lengkap dengan rincian payload dan alert critical/high yang belum ditutup.")

    d.h2("3.5 Devices (Summary, Network, CCTV, Operational, Milestone)")
    d.p("Memantau seluruh perangkat Zabbix dengan peta sebaran Indonesia interaktif (tahan Ctrl + scroll untuk zoom), komposisi per kategori, durasi downtime, perangkat bermasalah berulang, serta sub-menu Milestone untuk status kamera merekam, server sinkronisasi, dan Public Announcer.")

    d.h2("3.6 Personnel (Schedule & Handover)")
    d.p("Menampilkan kalender rotasi shift tim ITOC, direktori kontak personel & EOS cabang, serta fitur Handover untuk mencatat dan menutup kasus pending antar shift (terintegrasi notifikasi webhook untuk prioritas tinggi).")

    # 4. Report, Insight & Shift Summary
    d.h1("4. Report, Insight & Shift Summary")
    d.h2("4.1 Ekspor Laporan & Share Link (Report)")
    d.p("Pilih jenis laporan (Full, Summary, Performance, atau Custom sections), pilih periode/lokasi, lalu klik unduh dalam format Excel (.xlsx), PDF (.pdf), atau PowerPoint (.pptx). Gunakan tombol Share Link untuk membuat tautan unduhan tanpa login yang berlaku maksimal 72 jam.")

    d.h2("4.2 Insight & 9 Template Shift Summary (Report → Insights)")
    d.bullets([
        ("Findings: ", "Daftar temuan anomali otomatis (Critical/Warning/Info) lengkap dengan aksi Mark read, Add to Handover, atau Dismiss sementara."),
        ("Rankings & Location Health: ", "Peringkat problem links, repeat offender devices, dan Health Score (0–100) setiap cabang."),
        ("Shift Summary: ", "Tersedia 9 template siap-salin ke WhatsApp/Telegram: Full, NOC, SOC, EOS, ISP (Zabbix ISP-* & PRTG), CCTV, WiFi, Devices, dan Links/Web. Semua template mendukung pemilihan periode, filter per cabang (untuk 6 tipe area), catatan tambahan, dan selalu menyertakan Link Pendukung ke TERA."),
    ])

    # 5. Bot & Notifier WhatsApp / Telegram
    d.h1("5. Penggunaan Bot & Notifier (WhatsApp & Telegram)")
    d.p("Operator dan manajemen dapat menarik laporan langsung dari chat WhatsApp atau Telegram menggunakan slash command berikut:")
    d.table(
        ["Command", "Contoh Penggunaan", "Keterangan"],
        [
            ("/fullday", "/fullday · /fullday-20261123", "Laporan shift lengkap hari tugas ini (atau tanggal/rentang tertentu)."),
            ("/pagi, /sore, /malam", "/pagi · /sore · /malam", "Laporan satu shift spesifik pada hari tugas berjalan."),
            ("/noc, /soc", "/noc · /soc", "Ringkasan khusus operasional NOC atau keamanan siber SOC."),
            ("/isp", "/isp · /isp-belawan", "Status live ISP Zabbix (ISP-*) per provider, dual-link redundancy, MTTR & PRTG."),
            ("/eos", "/eos · /eos-janirah", "Laporan khusus EOS cabang (tiket, jaringan + ISP Zabbix, perangkat)."),
            ("/cctv, /wifi, /devices, /link", "/cctv-belawan · /wifi-tanjungpinang", "Status spesifik per bidang; bisa difilter untuk satu cabang."),
            ("/7hari, /thismonth, /lastmonth", "/7hari · /thismonth · /month-202610", "Ringkasan 7 hari terakhir, bulan berjalan, bulan lalu, atau bulan tertentu."),
            ("/cabang, /help", "/cabang · /help", "Daftar nama cabang yang valid dan daftar seluruh perintah aktif."),
        ],
        col_widths=[4.0, 5.0, 7.6],
    )

    # 6. Panduan Menu Admin
    d.h1("6. Panduan Administrasi (Menu Admin)")
    d.p("Menu Admin dikelompokkan menjadi 5 grup utama dan 19 sub-menu dengan tampilan yang seragam:")
    d.table(
        ["Grup Admin", "Sub-Menu", "Fungsi Utama"],
        [
            ("Access", "Users, Roles, API Keys", "Kelola akun pengguna & reset password, matriks hak akses per role, dan pembuatan API Key untuk bot/integrasi."),
            ("Data Sources", "Integrations, Mapping, Needs Completion", "Konfigurasi URL/kredensial & jadwal sync 8+ sumber data, pemetaan kode lokasi/ISP/sensor, dan daftar data yang perlu dilengkapi."),
            ("Operations", "Personnel, Teams & Shifts, Targets & Parameters, Formulas", "Master personel & jadwal rotasi, target SLA, parameter Wall Slideshow & chat.commands, serta penjelasan rumus."),
            ("Notifications", "Email, Webhooks, Bot & Notifier API", "Pengaturan SMTP + test email, webhook push otomatis (WhatsApp, Telegram, Teams, Slack, JSON), serta halaman Bot & Notifier API (live tester & snippet integrasi)."),
            ("System", "Audit Log, Share Links, Source Status, Menus & Widgets, Page Access, Backup & Restore", "Log aktivitas + ekspor CSV, cabut Share Link, status sync terakhir, katalog menu/widget, kunci halaman Super Admin, serta backup/restore database .sql."),
        ],
        col_widths=[2.6, 4.8, 9.2],
    )

    # 7. Troubleshooting Singkat
    d.h1("7. Pemecahan Masalah Umum (FAQ)")
    d.bullets([
        ("Tampilan terasa terlalu besar/kecil: ", "Pastikan zoom browser di angka 100% lalu tekan Ctrl+Shift+R (hard refresh). TERA sudah dikalibrasi optimal di 100% zoom."),
        ("Data terbaru belum muncul: ", "Cek Admin → System → Source Status untuk melihat waktu sync terakhir, atau jalankan Sync now di Admin → Data Sources → Integrations."),
        ("Tidak bisa masuk halaman Admin tertentu: ", "Beberapa halaman dikunci khusus Super Admin di Admin → System → Page Access."),
        ("Lupa password: ", "Hubungi Admin ITOC untuk melakukan Reset password melalui Admin → Access → Users."),
    ])

    out = DOCS_DIR / "02-User-Manual-TERA-Dashboard.docx"
    d.save(out)
    return out


def build_manual_pptx():
    dk = PelindoDeck(
        "USER MANUAL\nTERA DASHBOARD",
        "Panduan Operasional Pengguna & Administrator\nIT Operation Center (ITOC) · Divisi Teknologi Informasi · PT Pelindo Multi Terminal",
    )

    # Slide 2: Login & Navigasi Utama
    s = dk.slide("Akses Awal, Navigasi & Header Kontrol", "Antarmuka seragam, responsif di 100% zoom, dengan akses cepat di pojok kanan atas")
    dk.card(s, M, 1.85, 5.95, 4.95, "1. Login & Akun Pengguna", [
        ("Sign In: ", "Masukkan Username & Password di portal TERA; login pertama wajib mengganti kata sandi (min. 10 karakter)."),
        ("User Pill (Kanan Atas): ", "Menampilkan nama & role aktif, tombol Change password, dan Sign out."),
        ("Sidebar & Rail Mode: ", "Klik tombol ‹ pada tepi sidebar untuk mengecilkan menu menjadi icon rail."),
        ("Filter Bar 1-Baris: ", "Preset periode, tanggal, shift, lokasi, Compare, dan Reset dalam 1 baris rapi (Devices tetap penuh)."),
    ], accent=NAVY, body_size=12)
    dk.card(s, M + 6.25, 1.85, 5.95, 4.95, "2. Kontrol Cepat di Header Kanan", [
        ("On Duty Chip: ", "Menampilkan tim & shift bertugas + jam WIB real-time."),
        ("TV / Wall Mode (Monitor): ", "Aktifkan slideshow layar penuh ruang kendali ITOC."),
        ("Theme (Bulan): ", "Beralih instan Light Mode ↔ Dark Mode."),
        ("Profile Switcher (Grid): ", "Pilih tata letak Default, NOC Wall, atau Branch / EOS."),
        ("Customize (Slider): ", "Super Admin dapat drag-and-drop, ubah ukuran, dan tambah widget."),
    ], accent=BLUE, body_size=12)

    # Slide 3: TV / Wall Slideshow Mode
    s = dk.slide("Panduan TV / Wall Slideshow Mode", "Dirancang untuk layar monitor ruang kendali ITOC 24/7 — berlaku di seluruh menu")
    dk.kpi_strip(s, 1.85, [
        ("Auto-Slide", "Pecah Baris Cerdas", "Widget sejajar tidak pernah terpotong", NAVY),
        ("Rotate Menu", "Lintas Halaman", "Overview → ISP → Devices → Cyber", BLUE),
        ("Auto-Refresh", "Data Selalu Segar", "Countdown refresh di command bar", CYAN),
        ("Keyboard", "← · → · Space · Esc", "Kendali cepat tanpa mouse", GREEN),
    ])
    dk.card(s, M, 3.35, 12.2, 3.45, "Langkah Operasional & Pengaturan", [
        ("1. Masuk Wall Mode: ", "Klik ikon monitor di pojok kanan atas pada menu mana pun; browser otomatis masuk layar penuh."),
        ("2. Dark Command Bar: ", "Gunakan tombol ‹ / › untuk pindah slide, ⏸/▶ untuk jeda, dropdown durasi (10s–60s), dan tombol Rotate menus / Loop this page."),
        ("3. Pengaturan Permanen: ", "Buka Admin → Operations → Targets & Parameters (bagian Appearance) untuk mengatur durasi default slide, interval refresh data, dan daftar menu rotasi."),
    ], accent=NAVY, body_size=12.5)

    # Slide 4: Modul Operasional Utama
    s = dk.slide("Panduan Modul Pemantauan Operasional", "6 modul utama untuk NOC, SOC, Service Desk, EOS Cabang, dan Manajemen")
    mods = [
        ("Overview & Ticketing", NAVY, ["4 gauge utama + Needs Attention", "Volume tiket & pencapaian SLA", "Ranking teknisi & tiket overdue"]),
        ("Network & ISP Live", BLUE, ["Zabbix ISP-* per provider & cabang", "Matriks dual-link redundancy + MTTR", "SLA PRTG, 186+ AP WiFi & Web Kuma"]),
        ("Cyber Security (SOC)", RED, ["Event NDR Palo Alto & alert-only", "Alert XDR Trend Micro open >72 jam", "Detail payload & model deteksi"]),
        ("Devices & Milestone", CYAN, ["1.800+ perangkat Zabbix + peta RI", "Kamera merekam & 12 server Milestone", "Public Announcer & repeat offenders"]),
        ("Personnel & Handover", GREEN, ["Jadwal rotasi shift otomatis", "Direktori kontak ITOC & EOS cabang", "Serah terima kasus pending antar shift"]),
        ("Report & Insights", AMBER, ["Ekspor Excel, PDF, PPTX + Share Link", "Temuan anomali otomatis & Health Score", "9 template Shift Summary WA/Telegram"]),
    ]
    cw = (W - 2 * M - 0.4) / 3
    for i, (t, acc, items) in enumerate(mods):
        row, col = divmod(i, 3)
        dk.card(s, M + col * (cw + 0.2), 1.85 + row * 2.55, cw, 2.35, t, items, accent=acc, title_size=13.5, body_size=11)

    # Slide 5: Insight & 9 Template Shift Summary
    s = dk.slide("Insight Otomatis & 9 Template Shift Summary", "Tarik ringkasan shift siap-tempel ke WhatsApp/Telegram lengkap dengan URL TERA")
    dk.table(s, M, 1.8, W - 2 * M, 5.05, ["Template", "Filter Cabang", "Cakupan Isi Ringkasan"], [
        ["Full", "Semua cabang", "Status NOC & SOC, total & daftar tiket, Handover pending, monitoring lengkap, temuan otomatis, URL"],
        ["NOC / SOC", "Semua cabang", "Fokus khusus infrastruktur jaringan/perangkat/ISP (NOC) atau NDR/XDR (SOC)"],
        ["ISP (Baru)", "Semua / 1 cabang", "Status live Zabbix ISP-* per provider, dual-link redundancy, MTTR, top gangguan, SLA PRTG, URL"],
        ["EOS", "Semua / 1 cabang", "Tiket cabang, status jaringan + ISP Zabbix, perangkat down, temuan cabang, URL"],
        ["CCTV / WiFi / Devices", "Semua / 1 cabang", "Kamera Milestone & Zabbix / status AP & client WiFi / perangkat down terbanyak"],
        ["Links & Web", "Semua / 1 cabang", "PRTG link availability, Zabbix ISP-* down, dan status monitor web Uptime Kuma"],
    ], col_ratios=[2.3, 2.2, 7.7], font_size=11)

    # Slide 6: Panduan Bot WA & Telegram
    s = dk.slide("Panduan Perintah Bot WhatsApp & Telegram", "17 slash command aktif — dapat digunakan langsung via bot interaktif maupun scheduler mandiri")
    dk.card(s, M, 1.85, 6.4, 4.95, "Perintah Populer (Ketik di Chat)", [
        ("/fullday · /fullday-20261123 : ", "Laporan shift lengkap hari ini atau tanggal tertentu."),
        ("/pagi · /sore · /malam : ", "Laporan per shift pada hari tugas berjalan."),
        ("/isp · /isp-belawan : ", "Status live ISP Zabbix & PRTG (semua / 1 cabang)."),
        ("/eos · /eos-janirah : ", "Laporan EOS semua cabang atau cabang spesifik."),
        ("/noc · /soc · /cctv · /wifi · /devices · /link : ", "Ringkasan per bidang."),
        ("/7hari · /thismonth · /lastmonth : ", "Rekap mingguan & bulanan."),
        ("/cabang · /help : ", "Daftar nama cabang & seluruh perintah aktif."),
    ], accent=NAVY, body_size=11.5)
    dk.card(s, M + 6.65, 1.85, 5.55, 4.95, "3 Mode Integrasi Notifier", [
        ("1. Bot Interaktif (Dua Arah): ", "Bridge WA/Telegram meneruskan pesan user ke GET /api/insights/command?text=... dengan header X-API-Key."),
        ("2. Notifier Mandiri (Terjadwal): ", "Cron/n8n menarik GET /api/insights/summary?kind=isp&format=text lalu kirim ke Telegram/WA Gateway."),
        ("3. Push Otomatis (Webhook): ", "TERA otomatis mengirim alert ke WA/Telegram/Teams saat ada Handover prioritas tinggi, Insight baru, atau Sync gagal."),
    ], accent=BLUE, body_size=11.5)

    # Slide 7: Panduan Menu Admin (5 Grup / 19 Sub-Menu)
    s = dk.slide("Panduan Menu Admin (5 Grup · 19 Sub-Menu)", "Antarmuka Admin seragam dengan navigasi grup pill dan sub-tab underline")
    dk.table(s, M, 1.8, W - 2 * M, 5.05, ["Grup", "Sub-Menu", "Fungsi Administrasi"], [
        ["Access", "Users · Roles · API Keys", "Kelola akun & reset password, matriks hak akses per role, buat/cabut API Key"],
        ["Data Sources", "Integrations · Mapping · Needs Completion", "Konfigurasi API & jadwal sync 8 sumber data, pemetaan kode lokasi/ISP, data belum lengkap"],
        ["Operations", "Personnel · Teams & Shifts · Targets & Parameters · Formulas", "Master personel & shift, target SLA, setting Wall Slideshow & chat.commands, rumus KPI"],
        ["Notifications", "Email · Webhooks · Bot & Notifier API", "SMTP & test email, webhook push WA/Telegram/Teams/Slack, live command tester & template API"],
        ["System", "Audit Log · Share Links · Source Status · Menus & Widgets · Page Access · Backup & Restore", "Log audit CSV, cabut share link, status sync, katalog widget, kunci halaman Super Admin, backup/restore .sql"],
    ], col_ratios=[1.8, 4.5, 5.9], font_size=10.8)

    out = DOCS_DIR / "02-User-Manual-TERA-Dashboard.pptx"
    n = dk.save(out)
    return out, n


if __name__ == "__main__":
    p1 = build_manual_docx()
    p2, n = build_manual_pptx()
    print(f"OK User Manual: {p1.name} & {p2.name} ({n} slides)")
