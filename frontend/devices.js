/* Devices: CCTV, Gate System, and other categories from Zabbix. Location, category, and status filters are in the global filter bar (same as other pages). */
"use strict";
const durTxt = h => h == null ? "-" : h < 1 ? Math.max(1, Math.round(h * 60)) + " min" : h < 48 ? fx(h, 1) + " h" : fx(h / 24, 1) + " d";
const stBar = r => { const t = r.total || 1, w = n => (n / t * 100).toFixed(2) + "%"; return `<div class="stbar" title="${esc(`${r.up} up · ${r.down} down · ${r.deg || 0} interface · ${r.maint} maintenance · ${r.off} disabled`)}"><i class="u" style="width:${w(r.up)}"></i><i class="g" style="width:${w(r.deg || 0)}"></i><i class="m" style="width:${w(r.maint)}"></i><i class="d" style="width:${w(r.down)}"></i></div>`; };
const availTone = a => a == null ? "" : a >= 0.99 ? "good-t" : a >= 0.95 ? "warn-t" : "crit-t";
const DEV_STAT = {up: ["good", "Online"], down: ["crit", "Down"], degraded: ["warn", "Interface"], maintenance: ["idle", "Maintenance"], disabled: ["idle", "Disabled"]};
const devPill = s => { const x = DEV_STAT[s] || ["idle", s]; return pill(x[0], x[1]); };
const devLegend = () => `<div class="legend"><span><b style="background:var(--good)"></b>Online</span><span><b style="background:var(--serious)"></b>Interface</span><span><b style="background:var(--warn)"></b>Maintenance</span><span><b style="background:var(--crit)"></b>Down</span></div>`;
const mapLegend = () => `<div class="legend"><span><b style="background:var(--good)"></b>Availability 99% or higher</span><span><b style="background:var(--warn)"></b>95 to 99%</span><span><b style="background:var(--crit)"></b>below 95%</span><span>Size = number of devices, red ring = some are down</span></div>`;

/* Base map layer (coastline): GeoJSON file or {"rings": [[[lon, lat], ...]]} at the address in parameter dev.basemap_url (e.g. assets/id-map.json). Empty = dots over the grid only. */
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

/* Location map (standalone SVG, no map server): dot = location with coordinates in the Locations master; size = number of devices; colour = availability.
   Map bounds follow the spread of locations (limited by parameter dev.map_bounds); labels only for points that do not overlap. */
/* The device location map uses Leaflet + OpenStreetMap. The markup only prepares a container; initDevMaps() builds the map after the page renders. */
const DMAPS = {};
function mapSvg(D) {
  if (!D.map.length) return empty("No locations with coordinates yet. Fill in lat and lon in Admin → Master Data → Locations.");
  const id = "dmap" + Object.keys(DMAPS).length + "x" + Math.random().toString(36).slice(2, 8);
  DMAPS[id] = D.map;
  return `<div class="dmapbox" id="${id}" role="img" aria-label="Device location map"></div>` + (D.noCoord.length ? `<span class="sub">No coordinates yet: ${esc(D.noCoord.slice(0, 8).join(", "))}${D.noCoord.length > 8 ? ", …" : ""}</span>` : "");
}
function initDevMaps() {
  if (typeof L === "undefined") return;
  const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim() || "#888";
  const colour = {g: css("--good"), w: css("--warn"), c: css("--crit"), n: css("--low")};
  document.querySelectorAll(".dmapbox:not([data-ready])").forEach(el => {
    const pts = DMAPS[el.id] || []; el.dataset.ready = "1";
    const map = L.map(el, {scrollWheelZoom: false, worldCopyJump: true, minZoom: 3, maxZoom: 18}).setView([-2.5, 118], 5);
    const osm = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {subdomains: "abc", maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}).addTo(map);
    osm.once("tileerror", () => mapLand().then(rings => { if (rings) L.polygon(rings, {stroke: true, color: css("--axis"), weight: 1, fillColor: css("--surface"), fillOpacity: 1, interactive: false}).addTo(map).bringToBack(); }));   // offline: local coastline as a fallback
    const bounds = [];
    [...pts].sort((a, b) => b.total - a.total).forEach(p => {
      const cl = p.avail == null ? "n" : p.avail >= 0.99 ? "g" : p.avail >= 0.95 ? "w" : "c";
      const m = L.circleMarker([p.lat, p.lon], {radius: 6 + Math.sqrt(p.total) * 1.2, color: p.down ? colour.c : "#ffffff", weight: p.down ? 3 : 1, fillColor: colour[cl], fillOpacity: 0.85}).addTo(map);
      m.bindTooltip(`<b>${esc(p.k)}</b><br>${p.total} devices · ${p.down} down · ${p.deg || 0} interface<br>availability ${p.avail != null ? pc(p.avail, 1) : "-"}`);
      bounds.push([p.lat, p.lon]);
    });
    if (bounds.length) map.fitBounds(bounds, {padding: [30, 30], maxZoom: 9});
    // Ctrl + scroll (or trackpad pinch) zooms the map, not the page; plain scroll still scrolls the page
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
/* Down history over the filter period (from stored Zabbix events): incidents, downtime, MTTR, per day, location, type, device, and dominant problems. */
function devHist(H) {
  const days = H.daily.map(x => ({label: dmon(x.date), full: dlong(x.date)}));
  const kp = `<div class="kpis k6">${kpi("Down Incidents", fmt(H.events), "in the period")}${kpi("Downtime", fmt(Math.round(H.hours)) + " h", "total across all devices")}${kpi("Devices Affected", fmt(H.hosts), "of " + fmt(H.devices) + " devices")}${kpi("Average Recovery", H.mttr != null ? fx(H.mttr, 1) + " h" : "-", "resolved incidents")}${kpi("Period Availability", H.avail != null ? pc(H.avail, 2) : "-", "1 − downtime ÷ (devices × period length)")}</div>`;
  const tb = (a, nm) => tbl([nm, "Incidents", "Downtime (h)", "Availability"], a.map(r => [r.k, r.events, fx(r.hours, 1), r.avail != null ? {h: `<span class="${availTone(r.avail)}">${pc(r.avail, 1)}</span>`} : "-"]), {r: [1, 2, 3], empty: "No down history in this period."});
  return panel("c12", "Down History", dmon(H.from) + " – " + dmon(H.to) + (H.since ? " · data since " + dmon(H.since.slice(0, 10)) : ""), kp) +
    panel("c6", "Down Incidents per Day", "incidents that started that day", bars(days, [{name: "Incidents", c: "--crit", v: H.daily.map(x => x.events)}], {label: "Down incidents per day"})) +
    panel("c6", "Downtime per Day", "downtime hours of all devices", bars(days, [{name: "Downtime (h)", c: "--warn", v: H.daily.map(x => x.hours)}], {dec: 0, unit: " h", label: "Downtime per day"})) +
    panel("c6", "Downtime per Location", "top 10", tb(H.byLoc, "Location")) +
    panel("c6", "Downtime per Device Type", "top 10", tb(H.byType, "Type")) +
    panel("c6", "Most Frequently Down Devices", "by total downtime", tbl(["Device", "Incidents", "Downtime (h)"], H.byHost.map(r => [r.k, r.events, fx(r.hours, 1)]), {r: [1, 2], empty: "No down history in this period."})) +
    panel("c6", "Dominant Problems", "by number of incidents", hbars(H.byProb.map(r => [r.k, r.events, 0, fmt(r.events) + " · " + fx(r.hours, 0) + " h"])));
}
function vDevices() {
  const D = V.dev, grid = h => `<div class="grid">${h}</div>`;
  if (!D) return grid(`<section class="panel c12">${empty()}</section>`);
  const A = D.all, kt = S.tab !== "devices";
  if (!D.configured || !(A.total || D.byKind.length)) return grid(panel("c12", "Devices", "", `<div class="empty"><b>No device data yet</b><span>${D.error ? "Last sync failed: " + esc(D.error) : "Enter the Zabbix URL and token in Admin → Integrations → Zabbix, enable it, then click Sync now."}</span></div>`));
  const warns = [];
  if (D.error) warns.push(`<li class="crit"><span><b>Zabbix sync failed:</b> ${esc(D.error)}</span></li>`);
  else if (D.stale) warns.push(`<li class="warn"><span><b>Data not updated</b> since ${esc(dtime(D.updated))}. Check the Zabbix connector.</span></li>`);
  if (D.unmapped.length) warns.push(`<li class="warn"><span><b>${D.unmapped.length} Zabbix location codes not mapped</b> (${esc(D.unmapped.slice(0, 6).map(u => u.code + " " + u.n).join(", "))}${D.unmapped.length > 6 ? ", …" : ""}). Set their locations in Admin → Master Data → Zabbix: code to location.</span></li>`);
  const oldest = D.down.find(x => x.ageH != null);
  const kp = `<div class="kpis k6">${kpi("Devices", fmt(A.total), "monitored from Zabbix")}${kpi("Online", fmt(A.up), A.avail != null ? pc(A.avail, 1) + " of the active ones" : "")}${kpi("Down", fmt(A.down), oldest ? "oldest " + durTxt(oldest.ageH) + " · " + fmt(D.chronic) + " over " + D.chronicDays + " days" : "none", {cls: A.down ? "warnv" : ""})}${kpi("Availability Now", A.avail != null ? pc(A.avail, 2) : "-", "online ÷ (online + down)")}${kpi("Interface Issue", fmt(A.deg || 0), "ping OK, SNMP/agent unavailable")}${kpi("Maintenance", fmt(A.maint), "disabled in Zabbix: " + fmt(A.off))}</div>`;
  const kinds = D.byKind.map(r => `<div class="strow"><b>${esc(r.k)}</b>${stBar(r)}<span class="num">${fmt(r.up)} / ${fmt(r.total)} · <span class="${availTone(r.avail)}">${r.avail != null ? pc(r.avail, 1) : "-"}</span></span></div>`).join("");
  const locs = D.byLoc.map(r => [r.k, r.total, {h: r.down ? `<b class="crit-t">${r.down}</b>` : "0"}, r.deg || 0, r.maint, {h: `<span class="${availTone(r.avail)}">${r.avail != null ? pc(r.avail, 1) : "-"}</span>`}, {h: stBar(r)}]);
  const downByLoc = D.byLoc.filter(r => r.down).slice(0, 12).map(r => [r.k, r.down, 0, r.down + " / " + r.total]);
  const rows = D.list.map(x => [x.name, x.typeLabel, x.loc, {h: devPill(x.status)}, x.since ? dtime(x.since) : "-", {h: `<span class="${x.ageH != null && x.ageH > 24 ? "crit-t" : ""}">${durTxt(x.ageH)}</span>`}, x.problem]);
  return insArea() + (warns.length ? grid(`<section class="panel c12"><ul class="att">${warns.join("")}</ul></section>`) : "") + kp + grid(
    panel(kt ? "c8" : "c7", "Site Map", D.map.length + " locations", mapLegend() + mapSvg(D)) +
    (kt ? "" : panel("c5", "Status by Category", "Updated " + dtime(D.updated), devLegend() + kinds)) +
    panel("c4", "Down Duration", D.downN + " devices down", hbars(D.ageDist.map(x => [x.k, x.n, 0, fmt(x.n)]))) +
    panel(kt ? "c12" : "c8", "Down by Location", "devices down / total", hbars(downByLoc)) +
    panel("c12", "By Device Type", D.byType.length + " types", tbl(["Type", "Code", "Devices", "Down", "Interface", "Availability", "Status"], D.byType.map(r => [r.k, r.code === "-" ? "-" : r.code, r.total, {h: r.down ? `<b class="crit-t">${r.down}</b>` : "0"}, r.deg || 0, {h: `<span class="${availTone(r.avail)}">${r.avail != null ? pc(r.avail, 1) : "-"}</span>`}, {h: stBar(r)}]), {r: [2, 3, 4, 5], tall: true, empty: "No data yet."})) +
    panel("c12", "Per Location", D.byLoc.length + " locations", tbl(["Location", "Devices", "Down", "Interface", "Maintenance", "Availability", "Status"], locs, {r: [1, 2, 3, 4, 5], tall: true, empty: "No data yet."})) +
    panel("c12", "Device List", D.listN + " devices" + (D.listN > D.list.length ? ", showing " + D.list.length : ""), `<div class="dtool"><input type="search" id="dq" class="msearch" placeholder="Search name, location, or problem" aria-label="Search devices"><span class="sub">Location, category, and status filters are in the top filter bar</span></div><div id="dlist">${tbl(["Device", "Type", "Location", "Status", "Down since", "Duration", "Problem"], rows, {tall: true, empty: "No devices for this filter."})}</div>`)) + (D.hist ? grid(devHist(D.hist)) : "");
}
/* Base coastline for the map (Natural Earth, public domain), loaded once from a local file. */
let LAND = null;
const mapLand = () => LAND || (LAND = fetch("assets/id-map.json").then(r => r.ok ? r.json() : null).then(j => j && j.rings ? j.rings.map(r => r.map(p => [p[1], p[0]])) : null).catch(() => null));
