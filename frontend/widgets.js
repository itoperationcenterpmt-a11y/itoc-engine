/* Widget catalog: extra blocks Super Admin can install through Customize -> Add widget.
   Each widget reads data the page already loaded (V.tk, V.net, V.soc, V.dev) and only appears when its data exists and the role may see the module. */
"use strict";
const hrs24 = () => [...Array(24).keys()].map(h => ({label: pad(h), full: "Pukul " + pad(h) + ".00-" + pad(h) + ".59 · shift " + SN[shiftOf(h)]}));
const WIDGETS = [
  {key: "tk-groups", mod: "servicedesk", need: "tk", title: "Group Ranking", desc: "Ranking of Team 1 to 4 and Head Office", size: "c12",
    html: () => panel("c12", "Group Ranking", "", tbl(["#", "Group", "Members", "Tickets", "% daftar", "Close", "Open", "Average (hours)", "% within target"], (V.tk.groupRanking || []).map(x => [x.rank, x.name, x.members, x.n, pc(x.share), x.done, x.open, x.avg, pc(x.inPct)]), {r: [2, 3, 4, 5, 6, 7, 8]}))},
  {key: "tk-tech", mod: "servicedesk", need: "tk", title: "Top 10 Technicians", desc: "Technicians with the most tickets", size: "c6",
    html: () => panel("c6", "Top 10 Technicians", ctxTxt(), tbl(["#", "Name", "Tickets", "% within target"], V.tk.ranking.filter(x => x.n > 0).slice(0, 10).map(x => [x.rank, x.name, x.n, pc(x.inPct)]), {r: [2, 3], empty: "No data yet."}))},
  {key: "tk-open", mod: "servicedesk", need: "tk", title: "Open Tickets", desc: "Oldest open tickets and their age", size: "c6",
    html: () => panel("c6", "Open Tickets", V.tk.open + " still open", tbl(["Subject", "Location", "Technician", "Age (days)"], V.tk.openList.slice(0, 10).map(x => [x.subj, x.loc, x.tech, {h: `<span class="${x.age > 3 ? "crit-t" : ""}">${fx(x.age, 1)}</span>`}]), {r: [3], empty: "No open tickets."}))},
  {key: "tk-duration", mod: "servicedesk", need: "tk", title: "Resolution Duration Distribution", desc: "Distribution of ticket resolution time", size: "c4",
    html: () => panel("c4", "Resolution Duration Distribution", "", hbars(V.tk.durasi.map(x => [x.k, x.n, 0, fmt(x.n) + " · " + pc(x.pct, 0)])))},
  {key: "tk-hours", mod: "servicedesk", need: "tk", title: "Tickets per Hour", desc: "Tickets by hour created", size: "c8",
    html: () => panel("c8", "Tickets per Hour", V.tk.peakHour != null ? "Busiest hour " + pad(V.tk.peakHour) + ".00" : "", bars(hrs24(), [{name: "Tickets In", c: "--s1", v: V.tk.hours}], {label: "Tickets per hour"}))},
  {key: "tk-quality", mod: "servicedesk", need: "tk", title: "Data Quality Notes", desc: "Ticket input quality checks", size: "c6",
    html: () => panel("c6", "Data Quality Notes", "", tbl(["Pemeriksaan", "Tickets", "% total"], V.tk.quality.map(x => [x.k, x.n, pc(x.pct)]), {r: [1, 2]}))},
  {key: "net-rank", mod: "noc", need: "net", title: "Link Ranking by Downtime", desc: "10 links with the lowest availability", size: "c6",
    html: () => panel("c6", "Link Ranking by Downtime", ctxTxt(), tbl(["Link", "Availability", "Down (mnt)", "Status"], V.net.rank.slice(0, 10).map(x => [x.link, pc(x.av, 2), fx(x.downMin, 0), x.status]), {r: [1, 2], empty: "No data yet."}))},
  {key: "net-isp", mod: "noc", need: "net", title: "Summary per ISP", desc: "Availability and downtime per ISP", size: "c6",
    html: () => panel("c6", "Summary per ISP", ctxTxt(), tbl(["ISP", "Link", "Availability", "Downtime (hours)"], (V.net.isp || []).map(x => [x.k, x.n, pc(x.av, 2), fx(x.downH, 1)]), {r: [1, 2, 3], empty: "No data yet."}))},
  {key: "soc-sev", mod: "soc", need: "soc", title: "Events by Severity", desc: "Threat events per severity", size: "c6",
    html: () => panel("c6", "Events by Severity", ctxTxt(APPLY.soc), tbl(["Severity", "Event", "% total", "Blocked"], (V.soc.sev || []).map(x => [x.k, fmt(x.n), pc(x.pct), x.blkPct != null ? pc(x.blkPct, 0) : "-"]), {r: [1, 2, 3], empty: "No data yet."}))},
  {key: "soc-action", mod: "soc", need: "soc", title: "Events by Firewall Action", desc: "Firewall action per event", size: "c6",
    html: () => panel("c6", "Events by Firewall Action", ctxTxt(APPLY.soc), tbl(["Action", "Event", "% total"], (V.soc.action || []).map(x => [x.k, fmt(x.n), pc(x.pct)]), {r: [1, 2], empty: "No data yet."}))},
  {key: "dev-category", mod: "devices", need: "dev", title: "Devices Status by Category", desc: "CCTV and Gate System status", size: "c5",
    html: () => panel("c5", "Devices Status by Category", "", V.dev.byKind.map(r => `<div class="strow"><b>${esc(r.k)}</b>${stBar(r)}<span class="num">${fmt(r.up)} / ${fmt(r.total)} · <span class="${availTone(r.avail)}">${r.avail != null ? pc(r.avail, 1) : "-"}</span></span></div>`).join(""))},
  {key: "dev-location", mod: "devices", need: "dev", title: "Devices per Location", desc: "8 locations with the most devices down", size: "c7",
    html: () => panel("c7", "Devices per Location", "", tbl(["Location", "Devices", "Down", "Availability"], V.dev.byLoc.slice(0, 8).map(r => [r.k, r.total, {h: r.down ? `<b class="crit-t">${r.down}</b>` : "0"}, {h: `<span class="${availTone(r.avail)}">${r.avail != null ? pc(r.avail, 1) : "-"}</span>`}]), {r: [1, 2, 3]}))},
  {key: "dev-down", mod: "devices", need: "dev", title: "Devices Down (top 10)", desc: "Longest-down devices", size: "c12",
    html: () => panel("c12", "Devices Down (top 10)", V.dev.downN + " devices", tbl(["Device", "Location", "Down since", "Duration"], V.dev.down.slice(0, 10).map(x => [x.name, x.loc, x.since ? dtime(x.since) : "-", {h: `<span class="${x.ageH != null && x.ageH > 24 ? "crit-t" : ""}">${durTxt(x.ageH)}</span>`}]), {empty: "All devices are online."}))},
];
/* Devices widgets are generated from the existing categories (Zabbix host group prefix): one set per category, besides the combined widgets above. */
function widgetList() {
  const extra = [], D = V.dev;
  if (D && D.byKind) {
    extra.push({key: "dev-map", mod: "devices", need: "dev", title: "Devices Map", desc: "Location map: colour = availability, size = number of devices", size: "c8",
      html: () => panel("c8", "Devices Map", V.dev.map.length + " locations", mapLegend() + mapSvg(V.dev))});
    extra.push({key: "dev-type", mod: "devices", need: "dev", title: "Devices by Type", desc: "Summary per device type (AP, CCTV, switch, and others)", size: "c6",
      html: () => panel("c6", "Devices by Type", V.dev.byType.length + " types", tbl(["Type", "Devices", "Down", "Availability"], V.dev.byType.slice(0, 10).map(r => [r.k, r.total, {h: r.down ? `<b class="crit-t">${r.down}</b>` : "0"}, {h: `<span class="${availTone(r.avail)}">${r.avail != null ? pc(r.avail, 1) : "-"}</span>`}]), {r: [1, 2, 3], empty: "No data yet."}))});
    extra.push({key: "dev-age", mod: "devices", need: "dev", title: "Devices Down Duration", desc: "Distribution of device down time", size: "c4",
      html: () => panel("c4", "Down Duration", V.dev.downN + " devices down", hbars(V.dev.ageDist.map(x => [x.k, x.n, 0, fmt(x.n)])))});
    D.byKind.forEach(k => {
      const s = slug(k.key) || "x", get = () => V.dev.byKind.find(x => x.key === k.key) || k;
      extra.push({key: "dev-k-" + s, mod: "devices", need: "dev", title: "Devices · " + k.k, desc: "Summary of " + k.k + " (devices, availability, down)", size: "c4",
        html: () => { const q = get(); return `<section class="panel c4 dom"><header><h2>Devices · ${esc(q.k)}</h2></header><div class="mini">${kpi("Devices", fmt(q.total), "")}${kpi("Availability", q.avail != null ? pc(q.avail, 1) : "-", "online ÷ (online + down)", {cls: q.avail != null && q.avail < 0.95 ? "warnv" : ""})}${kpi("Down", fmt(q.down), "", {cls: q.down ? "warnv" : ""})}${kpi("Interface Issue", fmt(q.deg || 0), "")}</div>${go("devices")}</section>`; }});
      extra.push({key: "dev-kl-" + s, mod: "devices", need: "dev", title: "Per Location · " + k.k, desc: "Locations with the most " + k.k + " devices down", size: "c6",
        html: () => panel("c6", "Per Location · " + k.k, "", tbl(["Location", "Devices", "Down", "Availability"], (V.dev.kindLoc[k.key] || []).map(r => [r.k, r.total, {h: r.down ? `<b class="crit-t">${r.down}</b>` : "0"}, {h: `<span class="${availTone(r.avail)}">${r.avail != null ? pc(r.avail, 1) : "-"}</span>`}]), {r: [1, 2, 3], empty: "No data yet."}))});
      extra.push({key: "dev-kd-" + s, mod: "devices", need: "dev", title: "Devices Down · " + k.k, desc: "Longest-down " + k.k + " devices", size: "c6",
        html: () => panel("c6", "Devices Down · " + k.k, "", tbl(["Device", "Location", "Duration"], (V.dev.kindDown[k.key] || []).map(x => [x.name, x.loc, {h: `<span class="${x.ageH != null && x.ageH > 24 ? "crit-t" : ""}">${durTxt(x.ageH)}</span>`}]), {empty: "All devices are online."}))});
    });
  }
  const Xd = V.xdr;
  if (Xd && Xd.configured) {
    const XP = xdrPanels(Xd), addx = (key, title, desc, size, fn) => extra.push({key: "xdr-" + key, mod: "xdr", need: "xdr", title, desc, size, html: XP[fn]});
    addx("kpi", "XDR Summary", "Alerts, still open, critical, critical/high backlog", "c4", "kpi");
    addx("daily", "XDR Alerts per Day", "Alerts per day by severity", "c8", "daily");
    addx("sev", "XDR Severity and Status", "Distribution of severity and investigation status", "c4", "sev");
    addx("models", "XDR Top Detection Models", "Detection models with the most alerts", "c6", "models");
    addx("impact", "XDR Impact Scope", "Number of desktops, servers, accounts, and emails affected", "c6", "impact");
  }
  const Cc = V.cctv;
  if (Cc && Cc.configured) {
    const CP = cctvPanels(Cc), addc = (key, title, desc, size, fn) => extra.push({key: "cctv-" + key, mod: "cctv", need: "cctv", title, desc, size, html: CP[fn]});
    addc("kpi", "CCTV Summary", "Cameras, enabled, recording centrally, recording on site", "c4", "kpi");
    addc("hw", "CCTV per Hardware", "Cameras, enabled, and recording per Milestone hardware", "c8", "hw");
    addc("rec", "CCTV Recording per Hardware", "Recording cameras compared to enabled ones", "c4", "rec");
  }
  const Wf = V.wifi;
  if (Wf) {
    const WP = wifiPanels(Wf), add = (key, title, desc, size, fn) => extra.push({key: "wifi-" + key, mod: "wifi", need: "wifi", title, desc, size, html: WP[fn]});
    add("kpi", "WiFi Summary", "Active clients, online Access Points, weak signal, usage", "c4", "kpi");
    add("trend", "WiFi Client Trend", "WiFi clients over the last 24 hours", "c8", "trend");
    add("ssid", "WiFi Clients per SSID", "Active clients by SSID", "c4", "ssid");
    add("usage", "WiFi Usage per SSID", "Total traffic of running sessions per SSID", "c4", "usage");
    add("ap", "WiFi Clients per AP", "10 Access Points with the most clients", "c4", "ap");
    add("zone", "WiFi Clients per Zone", "Active clients by vSZ zone", "c4", "zone");
    add("band", "WiFi Band and Device Type", "Distribution of client band and device type", "c4", "band");
    add("portal", "WiFi Portal Users", "Users logged in through the WiFi portal, with location and AP", "c12", "portal");
    add("loc", "WiFi Clients per Location", "Active clients by location", "c4", "loc");
    add("top", "WiFi Top Usage", "Clients with the most traffic", "c8", "top");
    add("apdown", "WiFi APs Not Online", "Access Points that are not online", "c4", "apdown");
  }
  return WIDGETS.concat(extra);
}
/* Widget berparameter: "dev-map:<group>" = a map for one Zabbix host group (e.g. Network-SDWAN). More than one may be installed. */
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
  const ownHtml = own.length ? `<div class="catg"><span class="lbl">Widgets on this page</span><div class="catl">${own.map(b => { const k = esc(b.dataset.wkey), off = b.classList.contains("off"); return `<div class="catw"><div><b>${esc(b.dataset.title || b.dataset.dtitle || (k === "kpis" ? "KPI" : k))}</b><span class="sub">${off ? (b.dataset.gone ? "Removed from the dashboard" : "Hidden") : "Shown on the dashboard"}</span></div>${off ? `<button class="btn ghost" type="button" data-lay-show="${k}">Add</button>` : `<button class="btn ghost" type="button" data-lay-hide="${k}">Hide</button>`}</div>`; }).join("")}</div></div>` : "";
  if (!list.length) return ownHtml || `<div class="empty sm">There are no extra widgets for this page.</div>`;
  const groups = {};
  list.forEach(w => (groups[mods[w.mod] || w.mod] = groups[mods[w.mod] || w.mod] || []).push(w));
  return ownHtml + Object.entries(groups).map(([g, ws]) => `<div class="catg"><span class="lbl">${esc(g)}</span><div class="catl">${ws.map(w => `<div class="catw"><div><b>${esc(w.title)}</b><span class="sub">${esc(w.desc)}</span></div>${w.key === "dev-map" ? `<span class="catp"><select data-wparam aria-label="Group"><option value="">All groups</option>${((V.dev && V.dev.groups) || []).map(g => `<option value="${esc(g.name)}">${esc(g.name)}</option>`).join("")}</select><button class="btn ghost" type="button" data-wadd="dev-map">Add</button></span>` : present.has("w-" + w.key) ? `<span class="tag">Ditambahkan</span>` : `<button class="btn ghost" type="button" data-wadd="${esc(w.key)}">Add</button>`}</div>`).join("")}</div></div>`).join("");
}