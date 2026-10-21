/* Devices: CCTV, Gate System, dan kategori lain dari Zabbix. Filter lokasi, kategori, dan status ada di bar filter global (sama seperti halaman lain). */
"use strict";
const durTxt = h => h == null ? "-" : h < 1 ? Math.max(1, Math.round(h * 60)) + " mnt" : h < 48 ? fx(h, 1) + " jam" : fx(h / 24, 1) + " hari";
const stBar = r => { const t = r.total || 1, w = n => (n / t * 100).toFixed(2) + "%"; return `<div class="stbar" title="${esc(`${r.up} up · ${r.down} down · ${r.deg || 0} interface · ${r.maint} maintenance · ${r.off} nonaktif`)}"><i class="u" style="width:${w(r.up)}"></i><i class="g" style="width:${w(r.deg || 0)}"></i><i class="m" style="width:${w(r.maint)}"></i><i class="d" style="width:${w(r.down)}"></i></div>`; };
const availTone = a => a == null ? "" : a >= 0.99 ? "good-t" : a >= 0.95 ? "warn-t" : "crit-t";
const DEV_STAT = {up: ["good", "Online"], down: ["crit", "Down"], degraded: ["warn", "Interface"], maintenance: ["idle", "Maintenance"], disabled: ["idle", "Disabled"]};
const devPill = s => { const x = DEV_STAT[s] || ["idle", s]; return pill(x[0], x[1]); };
const devLegend = () => `<div class="legend"><span><b style="background:var(--good)"></b>Online</span><span><b style="background:var(--serious)"></b>Interface</span><span><b style="background:var(--warn)"></b>Maintenance</span><span><b style="background:var(--crit)"></b>Down</span></div>`;
const mapLegend = () => `<div class="legend"><span><b style="background:var(--good)"></b>Availability 99% atau lebih</span><span><b style="background:var(--warn)"></b>95 sampai 99%</span><span><b style="background:var(--crit)"></b>di bawah 95%</span><span>Ukuran = jumlah perangkat, cincin merah = ada yang down</span></div>`;

/* Lapisan peta dasar (garis pantai): berkas GeoJSON atau {"rings": [[[lon, lat], ...]]} di alamat parameter dev.basemap_url (mis. assets/id-map.json). Kosong = titik di atas grid saja. */
let BASEMAP = null;
async function loadBasemap() {
  const u = (CFG.params["dev.basemap_url"] || "").trim(); if (!u || BASEMAP) return;
  try {
    const j = await (await fetch(u)).json(), rings = [];
    const poly = c => c.forEach((r, i) => rings.push(r));
    (j.features || [j]).forEach(f => { const g = f.geometry || f; if (g.type === "Polygon") poly(g.coordinates); else if (g.type === "MultiPolygon") g.coordinates.forEach(poly); else if (f.rings) f.rings.forEach(r => rings.push(r)); });
    BASEMAP = rings.length ? rings : null;
  } catch (_) { BASEMAP = null; }
}
const basemapPath = (B, X, Y) => (BASEMAP || []).filter(r => r.some(([lo, la]) => lo >= B.lon_min - 5 && lo <= B.lon_max + 5 && la >= B.lat_min - 5 && la <= B.lat_max + 5))
  .map(r => "M" + r.map(([lo, la]) => X(lo).toFixed(1) + " " + Y(la).toFixed(1)).join("L") + "Z").join("");

/* Peta lokasi (SVG mandiri, tanpa server peta): titik = lokasi dengan koordinat di master Lokasi; ukuran = jumlah perangkat; warna = availability.
   Batas peta menyesuaikan sebaran lokasi (dibatasi parameter dev.map_bounds); label hanya untuk titik yang tidak bertumpuk. */
/* Peta lokasi perangkat memakai Leaflet + OpenStreetMap. Markup hanya menyiapkan wadah; peta dibuat oleh initDevMaps() setelah halaman dirender. */
const DMAPS = {};
function mapSvg(D) {
  if (!D.map.length) return empty("Belum ada lokasi berkoordinat. Isi lat dan lon di Admin → Master Data → Lokasi.");
  const id = "dmap" + Object.keys(DMAPS).length + "x" + Math.random().toString(36).slice(2, 8);
  DMAPS[id] = D.map;
  return `<div class="dmapbox" id="${id}" role="img" aria-label="Peta lokasi perangkat"></div>` + (D.noCoord.length ? `<span class="sub">Belum punya koordinat: ${esc(D.noCoord.slice(0, 8).join(", "))}${D.noCoord.length > 8 ? ", …" : ""}</span>` : "");
}
function initDevMaps() {
  if (typeof L === "undefined") return;
  const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim() || "#888";
  const colour = {g: css("--good"), w: css("--warn"), c: css("--crit"), n: css("--low")};
  document.querySelectorAll(".dmapbox:not([data-ready])").forEach(el => {
    const pts = DMAPS[el.id] || []; el.dataset.ready = "1";
    const map = L.map(el, {scrollWheelZoom: false, worldCopyJump: true, minZoom: 3, maxZoom: 18}).setView([-2.5, 118], 5);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {subdomains: "abc", maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}).addTo(map);
    const bounds = [];
    [...pts].sort((a, b) => b.total - a.total).forEach(p => {
      const cl = p.avail == null ? "n" : p.avail >= 0.99 ? "g" : p.avail >= 0.95 ? "w" : "c";
      const m = L.circleMarker([p.lat, p.lon], {radius: 6 + Math.sqrt(p.total) * 1.2, color: p.down ? colour.c : "#ffffff", weight: p.down ? 3 : 1, fillColor: colour[cl], fillOpacity: 0.85}).addTo(map);
      m.bindTooltip(`<b>${esc(p.k)}</b><br>${p.total} perangkat · ${p.down} down · ${p.deg || 0} interface<br>availability ${p.avail != null ? pc(p.avail, 1) : "-"}`);
      bounds.push([p.lat, p.lon]);
    });
    if (bounds.length) map.fitBounds(bounds, {padding: [30, 30], maxZoom: 9});
    // Ctrl + scroll (atau pinch di trackpad) zoom peta, bukan halaman; scroll biasa tetap menggulir halaman
    let hint;
    el.addEventListener("wheel", ev => {
      if (ev.ctrlKey || ev.metaKey) {
        ev.preventDefault();
        const d = ev.deltaY < 0 ? 1 : -1;
        map.setZoomAround(map.mouseEventToContainerPoint(ev), map.getZoom() + d * (ev.deltaMode ? 1 : Math.min(1, Math.abs(ev.deltaY) / 40 || 1)), {animate: true});
      } else {
        el.classList.add("hint"); clearTimeout(hint); hint = setTimeout(() => el.classList.remove("hint"), 1200);
      }
    }, {passive: false});
    new ResizeObserver(() => map.invalidateSize()).observe(el);
  });
}
/* Riwayat down pada rentang periode filter (dari kejadian Zabbix yang tersimpan): kejadian, downtime, MTTR, per hari, lokasi, tipe, perangkat, dan masalah dominan. */
function devHist(H) {
  const days = H.daily.map(x => ({label: dmon(x.date), full: dlong(x.date)}));
  const kp = `<div class="kpis k6">${kpi("Kejadian Down", fmt(H.events), "pada periode")}${kpi("Downtime", fmt(Math.round(H.hours)) + " jam", "total semua perangkat")}${kpi("Perangkat Terdampak", fmt(H.hosts), "dari " + fmt(H.devices) + " perangkat")}${kpi("Rata-rata Pulih", H.mttr != null ? fx(H.mttr, 1) + " jam" : "-", "kejadian yang sudah selesai")}${kpi("Availability Periode", H.avail != null ? pc(H.avail, 2) : "-", "1 − downtime ÷ (perangkat × lama periode)")}</div>`;
  const tb = (a, nm) => tbl([nm, "Kejadian", "Downtime (jam)", "Availability"], a.map(r => [r.k, r.events, fx(r.hours, 1), r.avail != null ? {h: `<span class="${availTone(r.avail)}">${pc(r.avail, 1)}</span>`} : "-"]), {r: [1, 2, 3], empty: "Belum ada riwayat down pada periode ini."});
  return panel("c12", "Riwayat Down", dmon(H.from) + " – " + dmon(H.to) + (H.since ? " · data sejak " + dmon(H.since.slice(0, 10)) : ""), kp) +
    panel("c6", "Kejadian Down per Hari", "kejadian yang dimulai pada hari itu", bars(days, [{name: "Kejadian", c: "--crit", v: H.daily.map(x => x.events)}], {label: "Kejadian down per hari"})) +
    panel("c6", "Downtime per Hari", "jam downtime semua perangkat", bars(days, [{name: "Downtime (jam)", c: "--warn", v: H.daily.map(x => x.hours)}], {dec: 0, unit: " jam", label: "Downtime per hari"})) +
    panel("c6", "Downtime per Lokasi", "10 teratas", tb(H.byLoc, "Lokasi")) +
    panel("c6", "Downtime per Tipe Perangkat", "10 teratas", tb(H.byType, "Tipe")) +
    panel("c6", "Perangkat Paling Sering Down", "menurut total downtime", tbl(["Perangkat", "Kejadian", "Downtime (jam)"], H.byHost.map(r => [r.k, r.events, fx(r.hours, 1)]), {r: [1, 2], empty: "Belum ada riwayat down pada periode ini."})) +
    panel("c6", "Masalah Dominan", "menurut jumlah kejadian", hbars(H.byProb.map(r => [r.k, r.events, 0, fmt(r.events) + " · " + fx(r.hours, 0) + " jam"])));
}
function vDevices() {
  const D = V.dev, grid = h => `<div class="grid">${h}</div>`;
  if (!D) return grid(`<section class="panel c12">${empty()}</section>`);
  const A = D.all;
  if (!D.configured || !(A.total || D.byKind.length)) return grid(panel("c12", "Devices", "", `<div class="empty"><b>Belum ada data perangkat</b><span>${D.error ? "Sinkron terakhir gagal: " + esc(D.error) : "Isi URL dan token Zabbix di Admin → Integrations → Zabbix, aktifkan, lalu klik Sync now."}</span></div>`));
  const warns = [];
  if (D.error) warns.push(`<li class="crit"><span><b>Sinkron Zabbix gagal:</b> ${esc(D.error)}</span></li>`);
  else if (D.stale) warns.push(`<li class="warn"><span><b>Data belum diperbarui</b> sejak ${esc(dtime(D.updated))}. Cek konektor Zabbix.</span></li>`);
  if (D.unmapped.length) warns.push(`<li class="warn"><span><b>${D.unmapped.length} kode lokasi Zabbix belum dipetakan</b> (${esc(D.unmapped.slice(0, 6).map(u => u.code + " " + u.n).join(", "))}${D.unmapped.length > 6 ? ", …" : ""}). Isi lokasinya di Admin → Master Data → Zabbix: kode ke lokasi.</span></li>`);
  const oldest = D.down.find(x => x.ageH != null);
  const kp = `<div class="kpis k6">${kpi("Devices", fmt(A.total), "dipantau dari Zabbix")}${kpi("Online", fmt(A.up), A.avail != null ? pc(A.avail, 1) + " dari yang aktif" : "")}${kpi("Down", fmt(A.down), oldest ? "tertua " + durTxt(oldest.ageH) + " · " + fmt(D.chronic) + " lebih dari " + D.chronicDays + " hari" : "tidak ada", {cls: A.down ? "warnv" : ""})}${kpi("Availability Now", A.avail != null ? pc(A.avail, 2) : "-", "online ÷ (online + down)")}${kpi("Interface Issue", fmt(A.deg || 0), "ping normal, SNMP/agent tidak tersedia")}${kpi("Maintenance", fmt(A.maint), "nonaktif di Zabbix: " + fmt(A.off))}</div>`;
  const kinds = D.byKind.map(r => `<div class="strow"><b>${esc(r.k)}</b>${stBar(r)}<span class="num">${fmt(r.up)} / ${fmt(r.total)} · <span class="${availTone(r.avail)}">${r.avail != null ? pc(r.avail, 1) : "-"}</span></span></div>`).join("");
  const locs = D.byLoc.map(r => [r.k, r.total, {h: r.down ? `<b class="crit-t">${r.down}</b>` : "0"}, r.deg || 0, r.maint, {h: `<span class="${availTone(r.avail)}">${r.avail != null ? pc(r.avail, 1) : "-"}</span>`}, {h: stBar(r)}]);
  const downByLoc = D.byLoc.filter(r => r.down).slice(0, 12).map(r => [r.k, r.down, 0, r.down + " / " + r.total]);
  const rows = D.list.map(x => [x.name, x.typeLabel, x.loc, {h: devPill(x.status)}, x.since ? dtime(x.since) : "-", {h: `<span class="${x.ageH != null && x.ageH > 24 ? "crit-t" : ""}">${durTxt(x.ageH)}</span>`}, x.problem]);
  return (warns.length ? grid(`<section class="panel c12"><ul class="att">${warns.join("")}</ul></section>`) : "") + kp + grid(
    panel("c7", "Site Map", D.map.length + " lokasi", mapLegend() + mapSvg(D)) +
    panel("c5", "Status by Category", "Pembaruan " + dtime(D.updated), devLegend() + kinds) +
    panel("c4", "Down Duration", D.downN + " perangkat down", hbars(D.ageDist.map(x => [x.k, x.n, 0, fmt(x.n)]))) +
    panel("c8", "Down by Location", "perangkat down / total", hbars(downByLoc)) +
    panel("c12", "By Device Type", D.byType.length + " tipe", tbl(["Tipe", "Kode", "Perangkat", "Down", "Interface", "Availability", "Status"], D.byType.map(r => [r.k, r.code === "-" ? "-" : r.code, r.total, {h: r.down ? `<b class="crit-t">${r.down}</b>` : "0"}, r.deg || 0, {h: `<span class="${availTone(r.avail)}">${r.avail != null ? pc(r.avail, 1) : "-"}</span>`}, {h: stBar(r)}]), {r: [2, 3, 4, 5], tall: true, empty: "Belum ada data."})) +
    panel("c12", "Per Location", D.byLoc.length + " lokasi", tbl(["Lokasi", "Perangkat", "Down", "Interface", "Maintenance", "Availability", "Status"], locs, {r: [1, 2, 3, 4, 5], tall: true, empty: "Belum ada data."})) +
    panel("c12", "Device List", D.listN + " perangkat" + (D.listN > D.list.length ? ", menampilkan " + D.list.length : ""), `<div class="dtool"><input type="search" id="dq" class="msearch" placeholder="Cari nama, lokasi, atau masalah" aria-label="Cari perangkat"><span class="sub">Filter lokasi, kategori, dan status di bar filter atas</span></div><div id="dlist">${tbl(["Perangkat", "Tipe", "Lokasi", "Status", "Down sejak", "Lama", "Masalah"], rows, {tall: true, empty: "Tidak ada perangkat untuk filter ini."})}</div>`)) + (D.hist ? grid(devHist(D.hist)) : "");
}