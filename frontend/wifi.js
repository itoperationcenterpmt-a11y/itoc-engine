/* Menu WiFi Users: client WiFi aktif, Access Point, usage, dan tren dari Ruckus vSZ. Filter daftar client berjalan di browser (data sudah termuat). */
"use strict";
const wBytes = n => n == null ? "-" : n >= 1099511627776 ? (n / 1099511627776).toFixed(2) + " TB" : n >= 1073741824 ? (n / 1073741824).toFixed(2) + " GB" : n >= 1048576 ? (n / 1048576).toFixed(1) + " MB" : Math.round(n / 1024) + " KB";
const wSel = (id, label, items) => `<select id="${id}" data-wf aria-label="${label}"><option value="">${label}</option>${[...new Set(items.filter(x => x && x !== "-"))].sort().map(x => `<option>${esc(x)}</option>`).join("")}</select>`;
function applyWF() {
  const q = (($("dq") || {}).value || "").trim().toLowerCase(), f = {4: $("wfSsid"), 5: $("wfAp"), 6: $("wfZone"), 7: $("wfBand")};
  document.querySelectorAll("#dlist tbody tr").forEach(r => { r.hidden = (q && !r.textContent.toLowerCase().includes(q)) || Object.entries(f).some(([i, s]) => s && s.value && r.children[i].textContent.trim() !== s.value); });
}
async function wifiKill(mac, mode) {
  const x = V.wifi.list.find(r => r.mac === mac); if (!x) return;
  const lbl = mode === "deauth" ? "Deauth" : "Disconnect";
  if (!confirm(`${lbl} client ini?\n\n${x.user || x.host || "-"} · ${x.mac}\nSSID: ${x.ssid || "-"} · AP: ${x.ap || "-"}\n\nClient bisa terhubung lagi bila aksesnya masih diizinkan. Aksi ini dicatat di audit log.`)) return;
  const reason = prompt("Alasan (opsional, tercatat di audit log):", ""); if (reason === null) return;
  await send("/api/wifi/disconnect", {mac, mode, reason});
  refresh({msg: `${lbl} terkirim untuk ${x.user || x.host || x.mac}.`}, true);
}
/* Panel WiFi yang dipakai halaman WiFi Users, Overview (katalog widget), dan widget katalog. */
function wifiPanels(W) {
  const hh = t => { const d = new Date(t); return {label: pad(d.getUTCHours()) + "." + pad(d.getUTCMinutes()), full: dtime(t)}; };
  const hb = (a, f) => hbars(a.map(x => [x.k, x.n, 0, f ? f(x) : fmt(x.n)]));
  return {
    kpi: () => `<section class="panel c4 dom"><header><h2>WiFi Users</h2></header><div class="mini">${kpi("Client Aktif", fmt(W.total), "terhubung saat ini")}${kpi("Access Point", W.apTotal ? fmt(W.apOnline) + " / " + fmt(W.apTotal) : "-", "online", {cls: W.apTotal && W.apOnline < W.apTotal ? "warnv" : ""})}${kpi("Sinyal Lemah", fmt(W.weak), "di bawah " + W.weakAt + " dBm", {cls: W.weak ? "warnv" : ""})}${kpi("Usage", wBytes(W.tx + W.rx), "sesi berjalan")}</div>${go("wifi")}</section>`,
    trend: () => panel("c8", "Client Trend 24 Jam", "Pembaruan " + dtime(W.updated), W.trend.length > 1 ? legend([{name: "Client", c: "--s1"}, {name: "User login", c: "--s2"}]) + lines(W.trend.map(x => hh(x.t)), [{name: "Client", c: "--s1", v: W.trend.map(x => x.c)}, {name: "User login", c: "--s2", v: W.trend.map(x => x.u)}], {dec: 0, label: "Client WiFi 24 jam"}) : empty("Tren terisi setelah beberapa kali sinkron.")),
    band: () => panel("c4", "Band dan Tipe Perangkat", "", `<span class="lbl">Band</span>` + hb(W.byBand) + `<span class="lbl">Tipe perangkat</span>` + hb(W.byType)),
    ssid: () => panel("c4", "Client per SSID", "", hb(W.bySsid)),
    usage: () => panel("c4", "Usage per SSID", "total trafik sesi berjalan", hb(W.bySsidBytes, x => wBytes(x.n))),
    ap: () => panel("c4", "Client per AP", "10 teratas", hb(W.byAp, x => fmt(x.n) + " · " + wBytes(x.bytes))),
    zone: () => panel("c4", "Client per Zone", "", hb(W.byZone)),
    top: () => panel("c8", "Top Usage", "10 client dengan trafik terbesar (sesi berjalan)", tbl(["User / Host", "MAC", "SSID", "AP", "Download", "Upload", "Total"], W.top.map(x => [x.user || x.host || "-", x.mac, x.ssid || "-", x.ap || "-", wBytes(x.tx), wBytes(x.rx), wBytes(x.bytes)]), {r: [4, 5, 6], empty: "Belum ada data."})),
    apdown: () => panel("c4", "Access Point Tidak Online", fmt(W.apTotal - W.apOnline) + " dari " + fmt(W.apTotal), tbl(["AP", "Zone", "Status", "Terakhir terlihat"], W.apDown.slice(0, 10).map(x => [x.name || "-", x.zone || "-", x.status || "-", x.since ? dtime(x.since) : "-"]), {empty: "Semua AP online."}))
  };
}
function vWifi() {
  const W = V.wifi, grid = h => `<div class="grid">${h}</div>`;
  if (!W) return grid(`<section class="panel c12">${empty()}</section>`);
  if (!W.configured || !(W.total || W.enabled)) return grid(panel("c12", "WiFi Users", "", `<div class="empty"><b>Belum ada data WiFi</b><span>${W.error ? "Sinkron terakhir gagal: " + esc(W.error) : "Isi alamat dan akun API Ruckus vSZ di Admin → Integrations → Ruckus vSZ, aktifkan, lalu klik Sync now."}</span></div>`));
  const warns = [];
  if (W.error) warns.push(`<li class="crit"><span><b>Sinkron vSZ gagal:</b> ${esc(W.error)}</span></li>`);
  else if (W.stale) warns.push(`<li class="warn"><span><b>Data belum diperbarui</b> sejak ${esc(dtime(W.updated))}. Cek konektor Ruckus vSZ.</span></li>`);
  if (W.apTotal && W.apTotal - W.apOnline) warns.push(`<li class="warn"><span><b>${W.apTotal - W.apOnline} Access Point tidak online</b> dari ${W.apTotal}.</span></li>`);
  const kp = `<div class="kpis k6">${kpi("Client Aktif", fmt(W.total), "terhubung saat ini")}${kpi("User Login", fmt(W.users), fmt(W.named) + " client dengan username")}${kpi("Access Point", W.apTotal ? fmt(W.apOnline) + " / " + fmt(W.apTotal) : "-", "online", {cls: W.apTotal && W.apOnline < W.apTotal ? "warnv" : ""})}${kpi("Sinyal Lemah", fmt(W.weak), "di bawah " + W.weakAt + " dBm", {cls: W.weak ? "warnv" : ""})}${kpi("Download", wBytes(W.tx), "sesi berjalan, semua client")}${kpi("Upload", wBytes(W.rx), "sesi berjalan, semua client")}</div>`;
  const P = wifiPanels(W);
  const rows = W.list.map(x => [x.user || "-", x.host || "-", x.mac, x.ip || "-", x.ssid || "-", x.ap || "-", x.zone || "-", x.band, {h: x.rssi == null ? "-" : `<span class="${x.rssi < W.weakAt ? "crit-t" : ""}">${x.rssi} dBm</span>`}, x.since ? dtime(x.since) : "-", wBytes(x.tx), wBytes(x.rx)]
    .concat(W.canKill ? [{h: `<button type="button" class="btn ghost sm" data-wkill="${esc(x.mac)}" data-mode="disconnect" title="Putus sesi client ini">Disconnect</button> <button type="button" class="btn ghost sm" data-wkill="${esc(x.mac)}" data-mode="deauth" title="Deauth: hapus status otorisasi (portal minta login ulang)">Deauth</button>`}] : []));
  const heads = ["Username", "Host", "MAC", "IP", "SSID", "AP", "Zone", "Band", "Sinyal", "Terhubung sejak", "Download", "Upload"].concat(W.canKill ? ["Aksi"] : []);
  const L = W.list;
  return (warns.length ? grid(`<section class="panel c12"><ul class="att">${warns.join("")}</ul></section>`) : "") + kp + grid(
    P.trend() + P.band() + P.ssid() + P.usage() + P.ap() + P.zone() + P.top() + P.apdown() +
    panel("c12", "Client List", W.total + " client" + (W.total > L.length ? ", menampilkan " + L.length : ""), `<div class="dtool"><input type="search" id="dq" class="msearch" placeholder="Cari username, host, MAC, IP, SSID, atau AP" aria-label="Cari client">${wSel("wfSsid", "Semua SSID", L.map(x => x.ssid))}${wSel("wfAp", "Semua AP", L.map(x => x.ap))}${wSel("wfZone", "Semua zone", L.map(x => x.zone))}${wSel("wfBand", "Semua band", L.map(x => x.band))}<span class="sub">${W.canKill ? "Disconnect memutus sesi; Deauth meminta client login ulang" : "Akun Anda hanya bisa melihat"}</span></div><div id="dlist">${tbl(heads, rows, {tall: true, empty: "Tidak ada client aktif."})}</div>`));
}