# Insight Otomatis

Menu **Insight** menampilkan temuan yang dihitung otomatis dari data yang sudah tersimpan di database. Tidak ada layanan luar dan tidak ada AI: semuanya statistik yang bisa dijelaskan angkanya.

## Kapan berjalan

Worker menjalankan analisis tiap 30 menit (dan satu menit setelah worker mulai). Admin bisa menjalankannya sendiri lewat tombol **Analisis sekarang** di halaman Insight. Hasil dan waktu analisis terakhir tercatat di Admin → Sistem → Status Sumber (sumber "Insight").

## Cara menilai

- **Anomali:** nilai terbaru dibandingkan dengan pola biasanya, yaitu median dan simpangan robust (MAD) dari data pembanding. Temuan muncul bila skor z di atas 3 dan selisih mutlaknya cukup besar, supaya fluktuasi kecil tidak ikut.
- **Pola mingguan:** tiket masuk dibandingkan dengan hari yang sama selama 8 minggu sebelumnya.
- **Tren:** kemiringan regresi linear 21 hari untuk availability, lalu perkiraan 14 hari ke depan terhadap target (`net.target`).
- **Berulang:** jumlah kejadian dalam 7 hari (link putus, host yang sama di banyak alert XDR).
- **Lintas sumber:** beberapa link di satu lokasi bermasalah bersamaan menandakan penyebab di lokasi, bukan di ISP.

## Daftar pemeriksaan

| Pemeriksaan | Sumber data | Syarat temuan |
|---|---|---|
| Tiket masuk melonjak | Tiket | z ≥ 3, minimal 1,5 kali biasanya dan selisih ≥ 5 |
| Downtime link melonjak | PRTG per jam | ≥ 30 menit (kemarin) atau ≥ 90 menit (hari ini), z ≥ 3, dan lebih dari 2 kali biasanya |
| Beberapa link satu lokasi bersamaan | PRTG per jam | 2 link atau lebih bermasalah pada hari yang sama |
| Link putus berulang | Kejadian PRTG | 5 kali atau lebih dalam 7 hari |
| Availability menurun | PRTG per jam | Kemiringan ≤ −0,04 poin per hari dan perkiraan 14 hari di bawah target |
| Critical dan high NDR melonjak | SOC harian | z ≥ 3, minimal 1,5 kali biasanya dan selisih ≥ 20 |
| Alert XDR lama belum selesai | Trend Micro | Critical atau high terbuka lebih dari 72 jam |
| Host berulang di XDR | Trend Micro | 3 alert atau lebih dalam 7 hari |
| Perangkat down melonjak | Zabbix per jam | z ≥ 3 dan selisih ≥ 10 |
| Perangkat down kronis | Zabbix | Down lebih dari 30 hari |
| AP WiFi offline banyak | Ruckus | Lebih dari 10% AP |
| Client WiFi turun tajam | Ruckus | ≤ 60% dari biasanya pada jam yang sama |

Pemeriksaan dilewati bila data pembanding kurang dari 5 titik. Karena itu temuan WiFi dan perangkat baru muncul setelah riwayat cukup terkumpul.

## Status temuan

- **Baru:** baru terdeteksi dan belum dibaca. Klik **Tandai dibaca** setelah dilihat.
- **Dibaca:** sudah dilihat, masih aktif.
- **Selesai:** tidak terdeteksi lagi pada analisis berikutnya. Temuan selesai ditampilkan 14 hari.

Temuan peringatan dan kritis yang baru dikirim sekali lewat webhook bila peristiwa **Insight baru** dipilih di Admin → Notifikasi → Webhook.

## Mengubah ambang

Ambang ada di `backend/app/insight.py` (`ZCUT`, `MIN_BASE`, dan syarat di tiap fungsi `d_*`). Menambah pemeriksaan baru berarti menambah satu fungsi yang mengembalikan daftar temuan dan mendaftarkannya di `DETECTORS`.
