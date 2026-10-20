/* Katalog widget: blok tambahan yang bisa dipasang admin lewat Customize -> Add widget.
   Setiap widget membaca data yang sudah dimuat halaman (V.tk, V.net, V.soc, V.dev) dan baru muncul bila datanya ada dan role boleh melihat modulnya. */
"use strict";
const hrs24 = () => [...Array(24).keys()].map(h => ({label: pad(h), full: "Pukul " + pad(h) + ".00-" + pad(h) + ".59 · shift " + SN[shiftOf(h)]}));
const WIDGETS = [
  {key: "tk-groups", mod: "servicedesk", need: "tk", title: "Group Ranking", desc: "Peringkat Team 1 sampai 4 dan Head Office", size: "c12",
    html: () => panel("c12", "Group Ranking", "", tbl(["#", "Group", "Anggota", "Tiket", "% daftar", "Close", "Open", "Rata-rata (jam)", "% dalam target"], (V.tk.groupRanking || []).map(x => [x.rank, x.name, x.members, x.n, pc(x.share), x.done, x.open, x.avg, pc(x.inPct)]), {r: [2, 3, 4, 5, 6, 7, 8]}))},
  {key: "tk-tech", mod: "servicedesk", need: "tk", title: "Top 10 Technicians", desc: "Teknisi dengan tiket terbanyak", size: "c6",
    html: () => panel("c6", "Top 10 Technicians", ctxTxt(), tbl(["#", "Nama", "Tiket", "% dalam target"], V.tk.ranking.filter(x => x.n > 0).slice(0, 10).map(x => [x.rank, x.name, x.n, pc(x.inPct)]), {r: [2, 3], empty: "Belum ada data."}))},
  {key: "tk-open", mod: "servicedesk", need: "tk", title: "Open Tickets", desc: "Tiket open terlama beserta umurnya", size: "c6",
    html: () => panel("c6", "Open Tickets", V.tk.open + " masih open", tbl(["Subjek", "Lokasi", "Teknisi", "Umur (hari)"], V.tk.openList.slice(0, 10).map(x => [x.subj, x.loc, x.tech, {h: `<span class="${x.age > 3 ? "crit-t" : ""}">${fx(x.age, 1)}</span>`}]), {r: [3], empty: "Tidak ada tiket open."}))},
  {key: "tk-duration", mod: "servicedesk", need: "tk", title: "Resolution Duration Distribution", desc: "Sebaran durasi penyelesaian tiket", size: "c4",
    html: () => panel("c4", "Resolution Duration Distribution", "", hbars(V.tk.durasi.map(x => [x.k, x.n, 0, fmt(x.n) + " · " + pc(x.pct, 0)])))},
  {key: "tk-hours", mod: "servicedesk", need: "tk", title: "Tickets per Hour", desc: "Tiket masuk menurut jam dibuat", size: "c8",
    html: () => panel("c8", "Tickets per Hour", V.tk.peakHour != null ? "Jam tersibuk " + pad(V.tk.peakHour) + ".00" : "", bars(hrs24(), [{name: "Tickets In", c: "--s1", v: V.tk.hours}], {label: "Tiket per jam"}))},
  {key: "tk-quality", mod: "servicedesk", need: "tk", title: "Data Quality Notes", desc: "Pemeriksaan kualitas input tiket", size: "c6",
    html: () => panel("c6", "Data Quality Notes", "", tbl(["Pemeriksaan", "Tiket", "% total"], V.tk.quality.map(x => [x.k, x.n, pc(x.pct)]), {r: [1, 2]}))},
  {key: "net-rank", mod: "noc", need: "net", title: "Link Ranking by Downtime", desc: "10 link dengan availability terendah", size: "c6",
    html: () => panel("c6", "Link Ranking by Downtime", ctxTxt(), tbl(["Link", "Availability", "Down (mnt)", "Status"], V.net.rank.slice(0, 10).map(x => [x.link, pc(x.av, 2), fx(x.downMin, 0), x.status]), {r: [1, 2], empty: "Belum ada data."}))},
  {key: "net-isp", mod: "noc", need: "net", title: "Summary per ISP", desc: "Availability dan downtime per ISP", size: "c6",
    html: () => panel("c6", "Summary per ISP", ctxTxt(), tbl(["ISP", "Link", "Availability", "Downtime (jam)"], (V.net.isp || []).map(x => [x.k, x.n, pc(x.av, 2), fx(x.downH, 1)]), {r: [1, 2, 3], empty: "Belum ada data."}))},
  {key: "soc-sev", mod: "soc", need: "soc", title: "Events by Severity", desc: "Jumlah event ancaman per severity", size: "c6",
    html: () => panel("c6", "Events by Severity", ctxTxt(APPLY.soc), tbl(["Severity", "Event", "% total", "Diblokir"], (V.soc.sev || []).map(x => [x.k, fmt(x.n), pc(x.pct), x.blkPct != null ? pc(x.blkPct, 0) : "-"]), {r: [1, 2, 3], empty: "Belum ada data."}))},
  {key: "soc-action", mod: "soc", need: "soc", title: "Events by Firewall Action", desc: "Tindakan firewall terhadap event", size: "c6",
    html: () => panel("c6", "Events by Firewall Action", ctxTxt(APPLY.soc), tbl(["Tindakan", "Event", "% total"], (V.soc.action || []).map(x => [x.k, fmt(x.n), pc(x.pct)]), {r: [1, 2], empty: "Belum ada data."}))},
  {key: "dev-category", mod: "devices", need: "dev", title: "Devices Status by Category", desc: "Status CCTV dan Gate System", size: "c5",
    html: () => panel("c5", "Devices Status by Category", "", V.dev.byKind.map(r => `<div class="strow"><b>${esc(r.k)}</b>${stBar(r)}<span class="num">${fmt(r.up)} / ${fmt(r.total)} · <span class="${availTone(r.avail)}">${r.avail != null ? pc(r.avail, 1) : "-"}</span></span></div>`).join(""))},
  {key: "dev-location", mod: "devices", need: "dev", title: "Devices per Location", desc: "8 lokasi dengan perangkat down terbanyak", size: "c7",
    html: () => panel("c7", "Devices per Location", "", tbl(["Lokasi", "Perangkat", "Down", "Availability"], V.dev.byLoc.slice(0, 8).map(r => [r.k, r.total, {h: r.down ? `<b class="crit-t">${r.down}</b>` : "0"}, {h: `<span class="${availTone(r.avail)}">${r.avail != null ? pc(r.avail, 1) : "-"}</span>`}]), {r: [1, 2, 3]}))},
  {key: "dev-down", mod: "devices", need: "dev", title: "Devices Down (top 10)", desc: "Perangkat down terlama", size: "c12",
    html: () => panel("c12", "Devices Down (top 10)", V.dev.downN + " perangkat", tbl(["Perangkat", "Lokasi", "Down sejak", "Lama"], V.dev.down.slice(0, 10).map(x => [x.name, x.loc, x.since ? dtime(x.since) : "-", {h: `<span class="${x.ageH != null && x.ageH > 24 ? "crit-t" : ""}">${durTxt(x.ageH)}</span>`}]), {empty: "Semua perangkat online."}))},
];
/* Widget Devices dibuat dinamis dari kategori yang ada (prefix host group Zabbix): satu set per kategori, selain widget gabungan di atas. */
function widgetList() {
  const extra = [], D = V.dev;
  if (D && D.byKind) {
    extra.push({key: "dev-map", mod: "devices", need: "dev", title: "Devices Map", desc: "Peta lokasi: warna = availability, ukuran = jumlah perangkat", size: "c8",
      html: () => panel("c8", "Devices Map", V.dev.map.length + " lokasi", mapLegend() + mapSvg(V.dev))});
    extra.push({key: "dev-type", mod: "devices", need: "dev", title: "Devices by Type", desc: "Ringkasan per tipe perangkat (AP, CCTV, switch, dan lain-lain)", size: "c6",
      html: () => panel("c6", "Devices by Type", V.dev.byType.length + " tipe", tbl(["Tipe", "Perangkat", "Down", "Availability"], V.dev.byType.slice(0, 10).map(r => [r.k, r.total, {h: r.down ? `<b class="crit-t">${r.down}</b>` : "0"}, {h: `<span class="${availTone(r.avail)}">${r.avail != null ? pc(r.avail, 1) : "-"}</span>`}]), {r: [1, 2, 3], empty: "Belum ada data."}))});
    extra.push({key: "dev-age", mod: "devices", need: "dev", title: "Devices Down Duration", desc: "Sebaran lama perangkat down", size: "c4",
      html: () => panel("c4", "Down Duration", V.dev.downN + " perangkat down", hbars(V.dev.ageDist.map(x => [x.k, x.n, 0, fmt(x.n)])))});
    D.byKind.forEach(k => {
      const s = slug(k.key) || "x", get = () => V.dev.byKind.find(x => x.key === k.key) || k;
      extra.push({key: "dev-k-" + s, mod: "devices", need: "dev", title: "Devices · " + k.k, desc: "Ringkasan " + k.k + " (perangkat, availability, down)", size: "c4",
        html: () => { const q = get(); return `<section class="panel c4 dom"><header><h2>Devices · ${esc(q.k)}</h2></header><div class="mini">${kpi("Devices", fmt(q.total), "")}${kpi("Availability", q.avail != null ? pc(q.avail, 1) : "-", "online ÷ (online + down)", {cls: q.avail != null && q.avail < 0.95 ? "warnv" : ""})}${kpi("Down", fmt(q.down), "", {cls: q.down ? "warnv" : ""})}${kpi("Interface Issue", fmt(q.deg || 0), "")}</div>${go("devices")}</section>`; }});
      extra.push({key: "dev-kl-" + s, mod: "devices", need: "dev", title: "Per Location · " + k.k, desc: "Lokasi dengan perangkat " + k.k + " down terbanyak", size: "c6",
        html: () => panel("c6", "Per Location · " + k.k, "", tbl(["Lokasi", "Perangkat", "Down", "Availability"], (V.dev.kindLoc[k.key] || []).map(r => [r.k, r.total, {h: r.down ? `<b class="crit-t">${r.down}</b>` : "0"}, {h: `<span class="${availTone(r.avail)}">${r.avail != null ? pc(r.avail, 1) : "-"}</span>`}]), {r: [1, 2, 3], empty: "Belum ada data."}))});
      extra.push({key: "dev-kd-" + s, mod: "devices", need: "dev", title: "Devices Down · " + k.k, desc: "Perangkat " + k.k + " yang down terlama", size: "c6",
        html: () => panel("c6", "Devices Down · " + k.k, "", tbl(["Perangkat", "Lokasi", "Lama"], (V.dev.kindDown[k.key] || []).map(x => [x.name, x.loc, {h: `<span class="${x.ageH != null && x.ageH > 24 ? "crit-t" : ""}">${durTxt(x.ageH)}</span>`}]), {empty: "Semua perangkat online."}))});
    });
  }
  return WIDGETS.concat(extra);
}
/* Widget berparameter: "dev-map:<group>" = peta khusus satu host group Zabbix (mis. Network-SDWAN). Boleh dipasang lebih dari satu. */
const mapWidget = g => ({key: "dev-map:" + encodeURIComponent(g), mod: "devices", need: "dev", title: "Devices Map · " + g, desc: "Peta group " + g, size: "c8",
  html: () => panel("c8", "Devices Map · " + g, "group " + g, mapLegend() + mapSvg({map: (V.dev.groupMaps || {})[g] || [], noCoord: []}))});
function widgetFind(key) {
  const i = key.indexOf(":");
  if (i > 0 && key.slice(0, i) === "dev-map") return mapWidget(decodeURIComponent(key.slice(i + 1)));
  return widgetList().find(x => x.key === key);
}
const widgetOk = w => !!V[w.need] && (w.need !== "dev" || V.dev.all.total > 0) && (CFG.me.role === "superadmin" || (CFG.modules || []).some(m => m.key === w.mod));
const widgetEl = w => { const t = document.createElement("div"); t.innerHTML = w.html(); return t.firstElementChild; };
function widgetBlock(w) {
  const el = widgetEl(w), h2 = el.querySelector(":scope > header h2");
  el.classList.add("wblock"); el.dataset.wkey = "w-" + w.key; el.dataset.added = "1"; el.dataset.dsize = w.size; el.dataset.dtitle = h2 ? h2.textContent : "";
  return {el, h2};
}
function catalogHtml() {
  const present = new Set([...document.querySelectorAll(".grid.lay > .wblock")].map(b => b.dataset.wkey));
  const mods = Object.fromEntries((CFG.modules || []).map(m => [m.key, m.label]));
  const list = widgetList().filter(widgetOk);
  const own = [...document.querySelectorAll(".grid.lay > .wblock:not([data-added])")];
  const ownHtml = own.length ? `<div class="catg"><span class="lbl">Widget halaman ini</span><div class="catl">${own.map(b => { const k = esc(b.dataset.wkey), off = b.classList.contains("off"); return `<div class="catw"><div><b>${esc(b.dataset.title || b.dataset.dtitle || (k === "kpis" ? "KPI" : k))}</b><span class="sub">${off ? (b.dataset.gone ? "Dihapus dari dashboard" : "Disembunyikan") : "Tampil di dashboard"}</span></div>${off ? `<button class="btn ghost" type="button" data-lay-show="${k}">Add</button>` : `<button class="btn ghost" type="button" data-lay-hide="${k}">Hide</button>`}</div>`; }).join("")}</div></div>` : "";
  if (!list.length) return ownHtml || `<div class="empty sm">Tidak ada widget tambahan untuk halaman ini.</div>`;
  const groups = {};
  list.forEach(w => (groups[mods[w.mod] || w.mod] = groups[mods[w.mod] || w.mod] || []).push(w));
  return ownHtml + Object.entries(groups).map(([g, ws]) => `<div class="catg"><span class="lbl">${esc(g)}</span><div class="catl">${ws.map(w => `<div class="catw"><div><b>${esc(w.title)}</b><span class="sub">${esc(w.desc)}</span></div>${w.key === "dev-map" ? `<span class="catp"><select data-wparam aria-label="Group"><option value="">Semua group</option>${((V.dev && V.dev.groups) || []).map(g => `<option value="${esc(g.name)}">${esc(g.name)}</option>`).join("")}</select><button class="btn ghost" type="button" data-wadd="dev-map">Add</button></span>` : present.has("w-" + w.key) ? `<span class="tag">Ditambahkan</span>` : `<button class="btn ghost" type="button" data-wadd="${esc(w.key)}">Add</button>`}</div>`).join("")}</div></div>`).join("");
}