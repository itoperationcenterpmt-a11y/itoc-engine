/* Menu CCTV (Milestone XProtect): inventaris kamera dan hardware dari RESTful API, tersimpan di database dashboard. Status online real-time ada di menu Devices (Zabbix). */
"use strict";
function cctvPanels(C) {
  const off = C.total - C.camEnabled, norec = C.camEnabled - C.recording;
  return {
    kpi: () => `<section class="panel c4 dom"><header><h2>CCTV</h2></header><div class="mini">${kpi("Kamera", fmt(C.total), fmt(C.nHw) + " hardware")}${kpi("Diaktifkan", fmt(C.camEnabled), fmt(off) + " dinonaktifkan", {cls: off ? "warnv" : ""})}${kpi("Merekam di Pusat", fmt(C.recording), "recording aktif di server ini")}${kpi("Rekam di Site", fmt(norec), "tidak merekam di server pusat")}</div>${go("cctv")}</section>`,
    hw: () => panel("c8", "Kamera per Hardware", fmt(C.nHw) + " hardware (NVR/interconnect) · terbanyak di atas", tbl(["Server", "Hardware", "Alamat", "Model", "Kamera", "Diaktifkan", "Merekam di Pusat", "Status"],
      C.hw.map(h => [h.server, h.name, h.host, h.model, h.cameras, h.camEnabled, h.rec, {h: h.enabled ? pill("good", "Aktif") : pill("idle", "Nonaktif")}]), {r: [4, 5, 6], empty: "Belum ada hardware."})),
    srv: () => panel("c12", "Server Milestone", fmt(C.servers.length) + " server", tbl(["Server", "Hardware", "Kamera", "Diaktifkan", "Merekam di Pusat", "Pembaruan"], C.servers.map(s => [s.name, s.hw, s.cameras, s.enabled, s.rec, s.updated ? dtime(s.updated) : "-"]), {r: [1, 2, 3, 4], empty: "Belum ada server."})),
    rec: () => panel("c4", "Rekaman di Pusat per Hardware", "kamera yang merekam di server pusat (hardware Interconnect merekam di site-nya)", hbars(C.hw.filter(h => h.camEnabled).slice(0, 10).map(h => [h.name, h.rec, 0, fmt(h.rec) + " / " + fmt(h.camEnabled)])))
  };
}
function vCctv() {
  const C = V.cctv, grid = h => `<div class="grid">${h}</div>`;
  if (!C) return grid(`<section class="panel c12">${empty()}</section>`);
  if (!C.configured || !C.total) return grid(panel("c12", "CCTV", "", `<div class="empty"><b>Belum ada data CCTV</b><span>${C.error ? "Sinkron terakhir gagal: " + esc(C.error) : "Isi akun Basic user Milestone di Admin → Integrations → Milestone XProtect (CCTV), aktifkan, lalu klik Sync now."}</span></div>`));
  const warns = [], off = C.total - C.camEnabled, norec = C.camEnabled - C.recording;
  if (C.error) warns.push(`<li class="crit"><span><b>Sinkron Milestone gagal:</b> ${esc(C.error)}</span></li>`);
  else if (C.stale) warns.push(`<li class="warn"><span><b>Data belum diperbarui</b> sejak ${esc(dtime(C.updated))}. Cek konektor Milestone.</span></li>`);
  if (C.hwOff) warns.push(`<li class="warn"><span><b>${fmt(C.hwOff)} hardware dinonaktifkan</b> di Milestone.</span></li>`);
  const kp = `<div class="kpis k6">${kpi("Kamera", fmt(C.total), "terdaftar di Milestone")}${kpi("Hardware", fmt(C.nHw), "NVR / interconnect")}${kpi("Diaktifkan", fmt(C.camEnabled), fmt(off) + " dinonaktifkan", {cls: off ? "warnv" : ""})}${kpi("Merekam di Pusat", fmt(C.recording), "recording aktif di server ini")}${kpi("Rekam di Site", fmt(norec), "tidak merekam di server pusat")}${kpi("Pembaruan", C.updated ? dtime(C.updated) : "-", "sinkron terakhir")}</div>`;
  const P = cctvPanels(C);
  const rows = C.list.map(x => [x.server, x.name, x.hw, x.ip || "-", x.ch == null ? "-" : x.ch, {h: x.enabled ? pill("good", "Aktif") : pill("idle", "Nonaktif")}, {h: x.rec ? pill("good", "Ya") : pill("idle", "Tidak")}, x.fps || "-", x.mod ? dtime(x.mod) : "-"]);
  return (warns.length ? grid(`<section class="panel c12"><ul class="att">${warns.join("")}</ul></section>`) : "") + kp + grid(
    (C.servers.length > 1 ? P.srv() : "") + P.hw() + P.rec() +
    panel("c12", "Camera List", C.total + " kamera", `<div class="dtool"><input type="search" id="dq" class="msearch" placeholder="Cari server, nama kamera, hardware, atau IP" aria-label="Cari kamera"><span class="sub">Data konfigurasi Milestone; status online per perangkat ada di menu Devices</span></div><div id="dlist">${tbl(["Server", "Kamera", "Hardware", "IP", "Ch", "Status", "Rekam di Pusat", "FPS", "Diubah"], rows, {tall: true, empty: "Belum ada kamera."})}</div>`));
}
