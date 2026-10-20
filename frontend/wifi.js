/* Menu WiFi Users: client WiFi aktif dari Ruckus vSZ (mode baca). Pencarian memakai kotak #dq yang sama dengan Devices. */
"use strict";
const wBytes = n => n == null ? "-" : n >= 1073741824 ? (n / 1073741824).toFixed(2) + " GB" : n >= 1048576 ? (n / 1048576).toFixed(1) + " MB" : Math.round(n / 1024) + " KB";
function vWifi() {
  const W = V.wifi, grid = h => `<div class="grid">${h}</div>`;
  if (!W) return grid(`<section class="panel c12">${empty()}</section>`);
  if (!W.configured || !(W.total || W.enabled)) return grid(panel("c12", "WiFi Users", "", `<div class="empty"><b>Belum ada data WiFi</b><span>${W.error ? "Sinkron terakhir gagal: " + esc(W.error) : "Isi alamat dan akun API Ruckus vSZ di Admin → Integrations → Ruckus vSZ, aktifkan, lalu klik Sync now."}</span></div>`));
  const warns = [];
  if (W.error) warns.push(`<li class="crit"><span><b>Sinkron vSZ gagal:</b> ${esc(W.error)}</span></li>`);
  else if (W.stale) warns.push(`<li class="warn"><span><b>Data belum diperbarui</b> sejak ${esc(dtime(W.updated))}. Cek konektor Ruckus vSZ.</span></li>`);
  const kp = `<div class="kpis k6">${kpi("Client Aktif", fmt(W.total), "terhubung saat ini")}${kpi("User", fmt(W.users), "username berbeda")}${kpi("SSID", fmt(W.bySsid.length), "yang sedang dipakai")}${kpi("Access Point", fmt(W.byAp.length), "dengan client (10 teratas)")}</div>`;
  const rows = W.list.map(x => [x.user || "-", x.host || "-", x.mac, x.ip || "-", x.ssid || "-", x.ap || "-", x.zone || "-", x.rssi != null ? x.rssi + " dBm" : "-", x.since ? dtime(x.since) : "-", wBytes((x.rx || 0) + (x.tx || 0))]);
  return (warns.length ? grid(`<section class="panel c12"><ul class="att">${warns.join("")}</ul></section>`) : "") + kp + grid(
    panel("c4", "Client per SSID", "Pembaruan " + dtime(W.updated), hbars(W.bySsid.map(x => [x.k, x.n, 0, fmt(x.n)]))) +
    panel("c4", "Client per AP", "10 teratas", hbars(W.byAp.map(x => [x.k, x.n, 0, fmt(x.n)]))) +
    panel("c4", "Client per Zone", "", hbars(W.byZone.map(x => [x.k, x.n, 0, fmt(x.n)]))) +
    panel("c12", "Client List", W.total + " client" + (W.total > W.list.length ? ", menampilkan " + W.list.length : ""), `<div class="dtool"><input type="search" id="dq" class="msearch" placeholder="Cari username, MAC, IP, SSID, atau AP" aria-label="Cari client"><span class="sub">Mode baca: tombol putus sesi belum diaktifkan</span></div><div id="dlist">${tbl(["Username", "Host", "MAC", "IP", "SSID", "AP", "Zone", "Sinyal", "Terhubung sejak", "Trafik"], rows, {tall: true, empty: "Tidak ada client aktif."})}</div>`));
}