/* Devices: status CCTV dan Gate System dari Zabbix (snapshot terkini). */
"use strict";
const durTxt = h => h == null ? "-" : h < 1 ? Math.max(1, Math.round(h * 60)) + " mnt" : h < 48 ? fx(h, 1) + " jam" : fx(h / 24, 1) + " hari";
const stBar = r => { const t = r.total || 1, w = n => (n / t * 100).toFixed(2) + "%"; return `<div class="stbar" title="${esc(`${r.up} up · ${r.down} down · ${r.deg || 0} interface · ${r.maint} maintenance · ${r.off} nonaktif`)}"><i class="u" style="width:${w(r.up)}"></i><i class="g" style="width:${w(r.deg || 0)}"></i><i class="m" style="width:${w(r.maint)}"></i><i class="d" style="width:${w(r.down)}"></i></div>`; };
const availTone = a => a == null ? "" : a >= 0.99 ? "good-t" : a >= 0.95 ? "warn-t" : "crit-t";

function vDevices() {
  const D = V.dev, grid = h => `<div class="grid">${h}</div>`;
  if (!D) return grid(`<section class="panel c12">${empty()}</section>`);
  const A = D.all;
  if (!D.configured || !A.total) return grid(panel("c12", "Devices", "", `<div class="empty"><b>Belum ada data perangkat</b><span>${D.error ? "Sinkron terakhir gagal: " + esc(D.error) : "Isi URL dan token Zabbix di Admin → Integrations → Zabbix, aktifkan, lalu klik Sync now."}</span></div>`));
  const warn = D.error ? `<li class="crit"><span><b>Sinkron Zabbix gagal:</b> ${esc(D.error)}</span></li>` : D.stale ? `<li class="warn"><span><b>Data belum diperbarui</b> sejak ${esc(dtime(D.updated))}. Cek konektor Zabbix.</span></li>` : "";
  const oldest = D.down.find(x => x.ageH != null);
  const kp = `<div class="kpis k6">${kpi("Devices", fmt(A.total), "dipantau dari Zabbix")}${kpi("Online", fmt(A.up), A.avail != null ? pc(A.avail, 1) + " dari yang aktif" : "")}${kpi("Down", fmt(A.down), oldest ? "tertua " + durTxt(oldest.ageH) + " · " + fmt(D.chronic) + " lebih dari 30 hari" : "tidak ada", {cls: A.down ? "warnv" : ""})}${kpi("Availability Now", A.avail != null ? pc(A.avail, 2) : "-", "online ÷ (online + down)")}${kpi("Interface Issue", fmt(A.deg || 0), "ping normal, SNMP/agent tidak tersedia")}${kpi("Maintenance", fmt(A.maint), "nonaktif di Zabbix: " + fmt(A.off))}</div>`;
  const kinds = D.byKind.map(r => `<div class="strow"><b>${esc(r.k)}</b>${stBar(r)}<span class="num">${fmt(r.up)} / ${fmt(r.total)} · <span class="${availTone(r.avail)}">${r.avail != null ? pc(r.avail, 1) : "-"}</span></span></div>`).join("");
  const legend = `<div class="legend"><span><b style="background:var(--good)"></b>Online</span><span><b style="background:var(--serious)"></b>Interface</span><span><b style="background:var(--warn)"></b>Maintenance</span><span><b style="background:var(--crit)"></b>Down</span></div>`;
  const locs = D.byLoc.map(r => [r.k, r.total, {h: r.down ? `<b class="crit-t">${r.down}</b>` : "0"}, r.maint, {h: `<span class="${availTone(r.avail)}">${r.avail != null ? pc(r.avail, 1) : "-"}</span>`}, {h: stBar(r)}]);
  const downRows = D.down.map(x => [x.name, x.kind, x.loc, x.since ? dtime(x.since) : "-", {h: `<span class="${x.ageH != null && x.ageH > 24 ? "crit-t" : ""}">${durTxt(x.ageH)}</span>`}, x.problem]);
  return (warn ? `<div class="grid"><section class="panel c12"><ul class="att">${warn}</ul></section></div>` : "") + kp + grid(
    panel("c5", "Status by Category", "Pembaruan " + dtime(D.updated), legend + kinds) +
    panel("c7", "Per Location", D.byLoc.length + " lokasi", tbl(["Lokasi", "Perangkat", "Down", "Maintenance", "Availability", "Status"], locs, {r: [1, 2, 3, 4], tall: true, empty: "Belum ada data."})) +
    panel("c12", "Devices Down", D.downN > D.down.length ? "menampilkan " + D.down.length + " dari " + D.downN : D.downN + " perangkat", tbl(["Perangkat", "Kategori", "Lokasi", "Down sejak", "Lama", "Masalah"], downRows, {tall: true, empty: "Semua perangkat online."})));
}