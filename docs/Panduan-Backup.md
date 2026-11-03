# Backup dan Rotasi Kunci

Dokumen ini menjelaskan backup database harian yang terenkripsi, cara memulihkannya, dan cara mengganti kunci enkripsi rahasia.

## 1. Backup harian terenkripsi

Layanan `backup` menjalankan `pg_dump` setiap hari (bawaan pukul 02:00 WIB) dan mengenkripsinya dengan **kunci publik** age. Kunci privatnya tidak pernah ada di server, sehingga berkas backup yang bocor tidak bisa dibuka.

### Persiapan satu kali

1. Buat pasangan kunci di komputer yang aman (bukan server aplikasi):

   ```bash
   docker run --rm alpine:3.20 sh -c "apk add -q age && age-keygen"
   ```

   Hasilnya dua baris: `Public key: age1...` dan `AGE-SECRET-KEY-...`.
2. Simpan kunci **privat** (`AGE-SECRET-KEY-...`) di tempat terpisah dan terlindungi (misalnya brankas password tim). Tanpa kunci ini backup tidak bisa dipulihkan.
3. Isi kunci **publik** di `.env` server:

   ```
   BACKUP_AGE_RECIPIENT=age1...
   BACKUP_KEEP=14
   BACKUP_AT=02:00
   ```
4. Jalankan layanan:

   ```bash
   docker compose --profile backup up -d --build backup
   ```

Berkas tersimpan di folder `backups/` (tidak masuk git) dengan nama `itoc-AAAAMMHH-JJMM.dump.age` dan berkas `.sha256`. Hanya `BACKUP_KEEP` berkas terakhir yang disimpan. Status layanan menjadi *unhealthy* bila tidak ada backup dalam 26 jam terakhir.

Backup sekali jalan (misalnya sebelum upgrade):

```bash
docker compose --profile backup run --rm backup once
```

Salin folder `backups/` secara berkala ke penyimpanan lain (server lain atau NAS). Backup di disk yang sama tidak melindungi dari kerusakan disk.

### Memulihkan

Lakukan di mesin yang memiliki kunci privat (simpan sementara sebagai `kunci.txt`, hapus setelah selesai):

```bash
age -d -i kunci.txt itoc-20261022-0200.dump.age | pg_restore -h localhost -U itoc -d itoc --clean --if-exists --no-owner
```

Periksa dulu integritas berkas dengan `sha256sum -c itoc-20261022-0200.dump.age.sha256`. Pemulihan menimpa isi tabel yang ada, jadi jangan dijalankan di database yang sedang dipakai tanpa backup terbaru.

**Uji pemulihan minimal sekali per kuartal** ke database kosong, dan pastikan aplikasi bisa login dan menampilkan data.

## 2. Mengganti kunci enkripsi rahasia

`ITOC_SECRET_KEY` mengenkripsi kredensial konektor, pengaturan email, dan URL webhook di database. Ganti kunci ini bila dicurigai bocor, atau berkala setahun sekali.

1. Buat kunci baru (minimal 32 karakter acak).
2. Di `.env`: pindahkan nilai lama ke `ITOC_SECRET_KEY_OLD`, isi `ITOC_SECRET_KEY` dengan kunci baru.
3. Restart: `docker compose up -d api worker`. Rahasia lama tetap terbaca lewat kunci lama.
4. Enkripsi ulang semuanya:

   ```bash
   docker compose exec api python -m app.cli rotate-key
   ```

   Hasilnya jumlah nilai yang dienkripsi ulang. Bila ada yang tercantum *tidak terbaca*, kunci lama yang diisi belum benar.
5. Kosongkan `ITOC_SECRET_KEY_OLD` dan restart lagi.

Simpan salinan `.env` (dan kunci) di tempat terpisah dari backup database. Bila kunci hilang, rahasia tersimpan tidak bisa dibaca dan harus diisi ulang lewat menu Admin.

Bila `ITOC_SECRET_KEY` sebelumnya kosong (memakai `ITOC_JWT_SECRET`), isi `ITOC_SECRET_KEY_OLD` dengan nilai `ITOC_JWT_SECRET` saat ini.
