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

Panorama/PAN-OS **punya API**: XML API (dan REST API untuk konfigurasi). Log dan **custom report** bisa diambil lewat API. Karena data SOC saat ini berasal dari custom report (`SOC-Threat-Summary`, `SOC-URL-Summary`, `SOC-Traffic-Application`, dan seterusnya), kemungkinan besar laporan yang sama bisa ditarik otomatis tanpa impor Excel.
Konektornya belum dibangun. Uji dulu langkah berikut.

**Role dan akun API (hak minimum)**
1. Panorama → Device → Admin Roles → Add, Role = **Panorama**.
2. Tab **XML API**: aktifkan hanya **Report** dan **Log**; yang lain (Configuration, Operational Requests, Commit, User-ID Agent, IoT Agent, Export, Import) **Disable**.
3. Tab **Web UI**: set semua **Disable** (klik ikon pada item paling atas hingga berubah silang merah, anak-anaknya ikut). Tab **REST API**: semua **Disable**. Tab **Plugins**: **Disable**. Tab **Command Line**: **None**.
   Bila Test menjawab "Illegal value for parameter reportname" padahal nama report benar, report itu kemungkinan ada di lingkup Device Group. Set sementara tab **XML API → Configuration = Read Only** agar Test bisa menelusuri lokasi report di config.
   Bila nanti Panorama menjawab "permission denied" saat mengambil report, naikkan sementara Web UI → Monitor (Logs dan Reports) menjadi **Read Only**, tidak lebih.
4. Device → Administrators → Add `dashboard-api`, Role = profil di atas, password kuat. Akun ini hanya dipakai API, jadi tidak bisa membuka Web UI.

**Uji dari dashboard** (tanpa curl): Admin → Integrations → Panorama. Isi Base URL (IP atau nama Panorama), username dan password akun API, Verifikasi TLS = Tidak bila sertifikat internal, lalu klik **Test**. Test akan membuat key, menjalankan report `SOC-Threat-Summary`, dan menampilkan jumlah baris serta nama kolomnya.
Sinkron otomatis belum ada; data SOC masih lewat impor Excel sampai hasil Test terkonfirmasi.

**Uji manual (opsional)**
`curl -k "https://PANORAMA/api/?type=keygen" -d "user=dashboard-api" -d "password=PASSWORD"`
`curl -k -H "X-PAN-KEY: KEY" "https://PANORAMA/api/" -d type=report -d reporttype=custom -d reportname=SOC-Threat-Summary -d async=yes`
Ambil hasilnya dengan `-d type=report -d action=get -d job-id=ID`.
**Alternatif Syslog** (bila API tidak diizinkan): Device → Server Profiles → Syslog (alamat collector, format BSD/IETF), lalu Objects → Log Forwarding dan pasang di security rule. Di server dashboard jalankan penerima (rsyslog atau syslog-ng, UDP/TCP 514) yang menulis ke berkas atau database, lalu diagregasi per hari. Cara ini memberi data per sumber IP, aplikasi, dan kategori URL, sehingga "apa yang dominan diakses" per client WiFi bisa dihitung dengan menggabungkan IP dan waktu sesi WiFi.