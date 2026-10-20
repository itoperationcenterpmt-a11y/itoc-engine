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
function mapSvg(D) {
  if (!D.map.length) return empty("Belum ada lokasi berkoordinat. Isi lat dan lon di Admin → Master Data → Lokasi.");
  const P = Object.assign({lat_min: -11, lat_max: 7, lon_min: 94, lon_max: 142}, CFG.params["dev.map_bounds"] || {}), pad = 2;
  const la = D.map.map(p => p.lat), lo = D.map.map(p => p.lon);
  const B = {lat_min: Math.max(P.lat_min, Math.min(...la) - pad), lat_max: Math.min(P.lat_max, Math.max(...la) + pad), lon_min: Math.max(P.lon_min, Math.min(...lo) - pad), lon_max: Math.min(P.lon_max, Math.max(...lo) + pad)};
  const W = 960, H = Math.max(260, Math.min(620, Math.round(W * (B.lat_max - B.lat_min) / (B.lon_max - B.lon_min)))), X = v => (v - B.lon_min) / (B.lon_max - B.lon_min) * W, Y = v => (B.lat_max - v) / (B.lat_max - B.lat_min) * H;
  let g = BASEMAP ? `<path class="land" d="${basemapPath(B, X, Y)}"/>` : "";
  for (let v = Math.ceil(B.lon_min / 5) * 5; v <= B.lon_max; v += 5) g += `<line class="gl" x1="${X(v)}" x2="${X(v)}" y1="0" y2="${H}"/><text x="${X(v) + 4}" y="${H - 6}">${v}°E</text>`;
  for (let v = Math.ceil(B.lat_min / 5) * 5; v <= B.lat_max; v += 5) g += `<line class="gl" y1="${Y(v)}" y2="${Y(v)}" x1="0" x2="${W}"/><text x="4" y="${Y(v) - 4}">${Math.abs(v)}°${v < 0 ? "S" : v > 0 ? "N" : ""}</text>`;
  const pts = D.map.map(p => ({...p, cx: X(p.lon), cy: Y(p.lat), r: 7 + Math.sqrt(p.total) * 1.4})), boxes = [];
  const hit = (a, b) => a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
  const label = new Map();
  [...pts].sort((a, b) => b.down - a.down || b.total - a.total).forEach(p => {
    const t = p.k.replace(/^Branch /, ""), w = t.length * 7.2 + 6;
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, -1], [0, 1]]) {
      const bx = dx > 0 ? p.cx + p.r + 3 : dx < 0 ? p.cx - p.r - 3 - w : p.cx - w / 2, by = dy < 0 ? p.cy - p.r - 16 : dy > 0 ? p.cy + p.r + 2 : p.cy - 8, bb = {x: bx, y: by, w, h: 14};
      if (bx < 0 || bx + w > W || by < 0 || by + 14 > H) continue;
      if (boxes.some(o => hit(o, bb)) || pts.some(q => q !== p && hit(bb, {x: q.cx - q.r, y: q.cy - q.r, w: q.r * 2, h: q.r * 2}))) continue;
      boxes.push(bb); label.set(p.k, {x: bx + w / 2, y: by + 11, t, anchor: "middle"}); break;
    }
  });
  const dots = [...pts].sort((a, b) => b.total - a.total).map(p => { const cl = p.avail == null ? "n" : p.avail >= 0.99 ? "g" : p.avail >= 0.95 ? "w" : "c", cx = p.cx.toFixed(1), cy = p.cy.toFixed(1);
    const tip = esc(`${p.k}\n${p.total} perangkat · ${p.down} down · ${p.deg || 0} interface\navailability ${p.avail != null ? pc(p.avail, 1) : "-"}`);
    return (p.down ? `<circle class="ring" cx="${cx}" cy="${cy}" r="${(p.r + 4).toFixed(1)}"/>` : "") + `<circle class="pt ${cl}" cx="${cx}" cy="${cy}" r="${p.r.toFixed(1)}" data-tip="${tip}"/>`; }).join("");
  const txt = [...label.values()].map(l => `<text class="lb" x="${l.x.toFixed(1)}" y="${l.y.toFixed(1)}" text-anchor="${l.anchor}">${esc(l.t)}</text>`).join("");
  return `<svg class="dmap" viewBox="0 0 ${W} ${H}" role="img" aria-label="Peta lokasi perangkat">${g}${dots}${txt}</svg>` + (D.noCoord.length ? `<span class="sub">Belum punya koordinat: ${esc(D.noCoord.slice(0, 8).join(", "))}${D.noCoord.length > 8 ? ", …" : ""}</span>` : "");
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
  const rows = D.list.map(x => [x.name, x.kindLabel, x.loc, {h: devPill(x.status)}, x.since ? dtime(x.since) : "-", {h: `<span class="${x.ageH != null && x.ageH > 24 ? "crit-t" : ""}">${durTxt(x.ageH)}</span>`}, x.problem]);
  return (warns.length ? grid(`<section class="panel c12"><ul class="att">${warns.join("")}</ul></section>`) : "") + kp + grid(
    panel("c7", "Site Map", D.map.length + " lokasi", mapLegend() + mapSvg(D)) +
    panel("c5", "Status by Category", "Pembaruan " + dtime(D.updated), devLegend() + kinds) +
    panel("c4", "Down Duration", D.downN + " perangkat down", hbars(D.ageDist.map(x => [x.k, x.n, 0, fmt(x.n)]))) +
    panel("c8", "Down by Location", "perangkat down / total", hbars(downByLoc)) +
    panel("c12", "Per Location", D.byLoc.length + " lokasi", tbl(["Lokasi", "Perangkat", "Down", "Interface", "Maintenance", "Availability", "Status"], locs, {r: [1, 2, 3, 4, 5], tall: true, empty: "Belum ada data."})) +
    panel("c12", "Device List", D.listN + " perangkat" + (D.listN > D.list.length ? ", menampilkan " + D.list.length : ""), `<div class="dtool"><input type="search" id="dq" class="msearch" placeholder="Cari nama, lokasi, atau masalah" aria-label="Cari perangkat"><span class="sub">Filter lokasi, kategori, dan status di bar filter atas</span></div><div id="dlist">${tbl(["Perangkat", "Kategori", "Lokasi", "Status", "Down sejak", "Lama", "Masalah"], rows, {tall: true, empty: "Tidak ada perangkat untuk filter ini."})}</div>`));
}