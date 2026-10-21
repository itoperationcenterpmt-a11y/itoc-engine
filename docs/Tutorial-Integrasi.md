# Tutorial Integrasi Dashboard IT Pelindo Multi Terminal

Semua pengaturan ada di **Admin → Integrations**. Setiap kartu punya: Base URL, kredensial (disimpan terenkripsi, tidak pernah ditampilkan lagi), Verifikasi TLS, interval, tombol **Test**, dan **Sync now**.
Urutan umum: isi Base URL dan kredensial → **Test** → aktifkan (Enabled) → **Sync now** → cek hasilnya di menu terkait.

> Verifikasi TLS: untuk sertifikat internal (self-signed) set **Tidak**. Untuk sertifikat resmi biarkan **Ya**.
> Dashboard hanya membaca data. Satu-satunya aksi tulis adalah Disconnect/Deauth client WiFi (butuh akun vSZ khusus, lihat bagian Ruckus).

---

## 1. Ruckus vSZ (WiFi)

**Akun API di vSZ**
1. Login UI vSZ (`https://IP-vSZ:8443`) sebagai Super Admin.
2. Administration → Admins and Roles → Administrators → Create. Isi username (mis. `itoc-dashboard`), password kuat, role baca saja.
3. Login sekali dengan akun itu agar tidak diminta ganti password.
4. (Untuk Disconnect) buat akun kedua dengan role yang boleh memutus client, isi di kolom "akun putus-sesi".

**Di dashboard**: Base URL cukup IP vSZ (https dan port 8443 ditambahkan otomatis). Isi username dan password, Test, aktifkan, Sync now. Interval disarankan 5 menit.
Dokumentasi API versi Anda: `https://IP-vSZ:8443/wsg/apiDoc/` (di server dashboard harus bisa dibuka).

**Data yang diambil**: client aktif, Access Point, dan sesi yang sudah selesai (`query/historicalclient`). Dashboard menyimpan sendiri setiap sesi (tabel `wifi_session`, lama simpan parameter `wifi.history_days`, bawaan 90 hari), karena riwayat di vSZ hanya sekitar beberapa minggu.
**Catatan**: vSZ tidak memberi data aplikasi/website yang diakses lewat API. "Dominan" di dashboard = SSID, zone, lokasi, AP, tipe perangkat, dan client dengan usage terbesar. Data per aplikasi/website hanya ada di firewall (Panorama), lihat bagian 5.
**Username portal**: terisi hanya bila login portal dicatat vSZ (WLAN Hotspot WISPr/802.1x yang diotentikasi lewat vSZ). Kalau terisi `N/A`, otentikasi terjadi di luar vSZ.

---

## 2. Zabbix 7.x (Devices)

1. Zabbix → Users → User groups → buat grup `dashboard-ro` dengan permission **Read** pada host group yang dipantau (CCTV-*, OPERASIONAL-*, NETWORK-*, dst).
2. Users → Users → buat user `dashboard` (role **User**), masukkan ke grup di atas.
3. Users → API tokens → Create API token untuk user itu. Salin token (hanya tampil sekali).
4. Dashboard: Base URL = IP atau `https://host/zabbix`, token, Prefix host group (satu per baris), Nama trigger "down". Test, aktifkan, Sync now.

**Riwayat**: sinkron pertama menarik kejadian down 60 hari ke belakang lewat `event.get` (parameter `dev.history_days`), sinkron berikutnya menambah yang baru dan melengkapi waktu pulih. Disimpan di `zbx_event`; cuplikan per jam di `zbx_stat`. Pilih rentang di filter Period pada menu Devices atau Report.

---

## 3. ManageEngine ServiceDesk Plus (Ticketing)

Konektor memakai API v3 dengan header `authtoken` (SDP on-premise).
1. SDP → Admin → Developer Space → **API Keys** (SDP versi lama: Admin → Technicians → edit teknisi → Generate API Key).
2. Buat key untuk akun teknisi khusus dengan hak **melihat semua request** (mis. role SDAdmin atau role baca yang boleh View All Requests).
3. Uji dari server dashboard:
   `curl -k -H "authtoken: KEY" -H "Accept: application/vnd.manageengine.sdp.v3+json" "https://HOST:PORT/api/v3/requests?input_data={\"list_info\":{\"row_count\":1}}"`
   Hasilnya harus JSON dengan `response_status` sukses.
4. Dashboard: Base URL = `https://HOST:PORT` (tanpa `/api`), API token, Test, aktifkan, interval 15 menit.
5. Sinkron pertama menarik 90 hari ke belakang (`backfill_days`), berikutnya hanya tiket yang berubah.

Catatan: SDP Cloud (Zoho) memakai OAuth dan belum didukung. Bila nama field di SDP Anda berbeda, pemetaan ada di konfigurasi sumber (`api_fields`).

---

## 4. PRTG (Networking)

1. PRTG → Setup → Account Settings → User Accounts → buat user `dashboard` (tipe Read-only) pada grup dengan hak **Read** ke probe/grup yang berisi sensor trafik.
2. Ambil passhash: login sebagai user itu → My Account → **Show passhash**, atau buka `https://PRTG/api/getpasshash.htm?username=dashboard&password=PASSWORD`.
3. Beri **tag** `itoc_link` pada sensor trafik yang ingin dipantau (sesuai `sensor_tag`; ubah di konfigurasi bila memakai tag lain).
4. Dashboard: Base URL `https://PRTG`, username, **passhash** (bukan password), Test, aktifkan, interval 60 menit.
5. Isi kapasitas link di Admin → Master Data → Sensor & kapasitas.

Catatan: nama channel harus sama dengan konfigurasi (`Traffic In (speed)(RAW)`, `Traffic Out (speed)(RAW)`, `Downtime(RAW)`, `coverage(RAW)`) dan bahasa PRTG Inggris. Data jam-an diambil lewat `historicdata.json` (30 hari pada sinkron pertama), jadi riwayat selalu ada selama PRTG menyimpannya.

---

## 5. Panorama (Cyber Security)

Panorama punya API (PAN-OS XML API). Dashboard memakainya lewat **dynamic report**: Panorama menghitung agregat dari semua firewall terkelola, jadi **tidak perlu custom report**. (Custom report yang dibuat langsung di firewall tidak terlihat dari Panorama, dan tidak dibutuhkan.)

**Role dan akun API (hak minimum)**
1. Panorama → Device → Admin Roles → Add, Role = **Panorama**.
2. Tab **XML API**: aktifkan **Report** dan **Log**; lainnya **Disable**. Tab **Web UI**, **REST API**, **Plugins**: **Disable**. Tab **Command Line**: **None**.
3. Device → Administrators → Add `dashboard-api`, pakai role itu, password kuat.

**Di dashboard**: Admin → Integrations → Panorama: Base URL (IP Panorama), username dan password akun API, Verifikasi TLS = Tidak bila sertifikat internal, Mode = **API**, Status = Aktif. **Test connection** untuk menguji login dan log, lalu **Sync now**.

**Yang diambil dan disimpan** (di database dashboard, sama seperti impor CSV):
- **Ringkasan harian** (ancaman, URL, aplikasi): satu batch per hari, mulai `backfill_days` hari ke belakang (bawaan 14, maksimal 90) sampai kemarin. Tiap sinkron memproses maksimal `max_days_per_run` hari (bawaan 4), sisanya di sinkron berikutnya. Hari yang sudah ada dari impor CSV tidak ditimpa.
- **Laporan Top** (sumber serangan, host internal, high/critical, URL diblokir, aplikasi, rule/zone, trafik, ditolak): satu batch periode `top_period` (bawaan 30 hari terakhir), diperbarui tiap `top_refresh_h` jam (bawaan 12).
- **Jadwal**: interval kartu Panorama diset 720 menit (12 jam). Impor CSV manual (mis. tiap pukul 00.00) tetap dipakai sebagai validasi: bila hari yang sama sudah ada dari API, CSV yang dipakai, dan impor mencatat selisih dengan data API bila lebih dari 3% (kolom Catatan di riwayat batch).
- Batch dari API bernama "Panorama API · ...". Impor CSV (Admin → Upload RAW SOC) tetap berfungsi sebagai cadangan.

**Batasan yang perlu diketahui**
- Dynamic report meringkas alamat IP ke blok /24 (mis. `10.185.25.0/24`), tidak sampai IP host.
- Kolom "host name" dan beberapa nama ancaman DNS tidak tersedia di agregat (tampil sebagai ID). Kolom URL hanya ada di laporan URL diblokir.
- Riwayat harian dibatasi oleh retensi log di Panorama (praktisnya sekitar 90 hari).
- Hasil bisa sedikit berbeda dari custom report di firewall karena sumbernya log yang dikumpulkan Panorama.

**Alternatif Syslog** (bila API tidak diizinkan): Device → Server Profiles → Syslog, lalu Objects → Log Forwarding. Di server dashboard jalankan penerima (rsyslog atau syslog-ng) dan agregasi per hari. Cara ini memberi data per IP host, tetapi perlu pekerjaan tambahan.