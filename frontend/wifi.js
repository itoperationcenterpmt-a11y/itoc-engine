/* WiFi Users menu: active WiFi clients, Access Points, usage, and trends from Ruckus vSZ. The client list filter runs in the browser (data is already loaded). */
"use strict";
const wBytes = n => n == null ? "-" : n >= 1099511627776 ? (n / 1099511627776).toFixed(2) + " TB" : n >= 1073741824 ? (n / 1073741824).toFixed(2) + " GB" : n >= 1048576 ? (n / 1048576).toFixed(1) + " MB" : Math.round(n / 1024) + " KB";
const wSel = (id, label, items) => `<select id="${id}" data-wf aria-label="${label}"><option value="">${label}</option>${[...new Set(items.filter(x => x && x !== "-"))].sort().map(x => `<option>${esc(x)}</option>`).join("")}</select>`;
function applyWP() {
  const q = (($("wpq") || {}).value || "").trim().toLowerCase(), st = ($("wpSt") || {}).value || "";
  document.querySelectorAll("#plist tbody tr").forEach(r => { r.hidden = (q && !r.textContent.toLowerCase().includes(q)) || (st && r.children[1].textContent.trim() !== st); });
}
function applyWF() {
  const q = (($("dq") || {}).value || "").trim().toLowerCase(), f = {4: $("wfSsid"), 5: $("wfAp"), 6: $("wfZone"), 8: $("wfBand")};
  document.querySelectorAll("#dlist tbody tr").forEach(r => { r.hidden = (q && !r.textContent.toLowerCase().includes(q)) || Object.entries(f).some(([i, s]) => s && s.value && r.children[i].textContent.trim() !== s.value); });
}
async function wifiKill(mac, mode) {
  const x = V.wifi.list.find(r => r.mac === mac); if (!x) return;
  const lbl = mode === "deauth" ? "Deauth" : "Disconnect";
  if (!confirm(`${lbl} this client?\n\n${x.user || x.host || "-"} · ${x.mac}\nSSID: ${x.ssid || "-"} · AP: ${x.ap || "-"}\n\nThe client can reconnect if its access is still allowed. This action is recorded in the audit log.`)) return;
  const reason = prompt("Reason (optional, recorded in the audit log):", ""); if (reason === null) return;
  await send("/api/wifi/disconnect", {mac, mode, reason});
  refresh({msg: `${lbl} sent for ${x.user || x.host || x.mac}.`}, true);
}
/* WiFi panels used by the WiFi Users page, Overview (widget catalog), and catalog widgets. */
function wifiPanels(W) {
  const hh = t => { const d = new Date(t); return {label: pad(d.getUTCHours()) + ":" + pad(d.getUTCMinutes()), full: dtime(t)}; };
  const hb = (a, f) => hbars(a.map(x => [x.k, x.n, 0, f ? f(x) : fmt(x.n)]));
  return {
    kpi: () => `<section class="panel c4 dom"><header><h2>WiFi Users</h2></header><div class="mini">${kpi("Active Clients", fmt(W.total), "connected now")}${kpi("Access Point", W.apTotal ? fmt(W.apOnline) + " / " + fmt(W.apTotal) : "-", "online", {cls: W.apTotal && W.apOnline < W.apTotal ? "warnv" : ""})}${kpi("Weak Signal", fmt(W.weak), "below " + W.weakAt + " dBm", {cls: W.weak ? "warnv" : ""})}${kpi("Usage", wBytes(W.tx + W.rx), "running sessions")}</div>${go("wifi")}</section>`,
    trend: () => panel("c8", "Client Trend 24h", "Updated " + dtime(W.updated), W.trend.length > 1 ? legend([{name: "Client", c: "--s1"}, {name: "User login", c: "--s2"}]) + lines(W.trend.map(x => hh(x.t)), [{name: "Client", c: "--s1", v: W.trend.map(x => x.c)}, {name: "User login", c: "--s2", v: W.trend.map(x => x.u)}], {dec: 0, label: "WiFi clients 24 hours"}) : empty("The trend fills in after a few syncs.")),
    band: () => panel("c4", "Band and Device Type", "", `<span class="lbl">Band</span>` + hb(W.byBand) + `<span class="lbl">Device type</span>` + hb(W.byType)),
    ssid: () => panel("c4", "Clients per SSID", "", hb(W.bySsid)),
    usage: () => panel("c4", "Usage per SSID", "total traffic of running sessions", hb(W.bySsidBytes, x => wBytes(x.n))),
    ap: () => panel("c4", "Clients per AP", "top 10", hb(W.byAp, x => fmt(x.n) + " · " + wBytes(x.bytes))),
    zone: () => panel("c4", "Clients per Zone", "", hb(W.byZone)),
    loc: () => panel("c4", "Clients per Location", "by location code in the AP name", hb(W.byLoc)),
    portal: () => {
      const rows = W.portal.map(x => [x.user || "-", {h: x.status === "login" ? pill("good", "Login") : pill("idle", "Not logged in")}, x.loc || "-", x.zone || "-", x.ap || "-", x.ssid || "-", x.ip || "-", x.mac, {h: x.rssi == null ? "-" : `<span class="${x.rssi < W.weakAt ? "crit-t" : ""}">${x.rssi} dBm</span>`}, x.since ? dtime(x.since) : "-", wBytes(x.tx), wBytes(x.rx)]
        .concat(W.canKill ? [{h: `<button type="button" class="btn ghost sm" data-wkill="${esc(x.mac)}" data-mode="disconnect" title="Disconnect this user's session">Disconnect</button> <button type="button" class="btn ghost sm" data-wkill="${esc(x.mac)}" data-mode="deauth" title="Deauth: the portal asks for login again">Deauth</button>`}] : []));
      return panel("c12", "Portal Users", fmt(W.portalLogin) + " logged in of " + fmt(W.portal.length) + " portal clients", `<div class="dtool"><input type="search" id="wpq" class="msearch" placeholder="Search username, location, AP, IP, or MAC" aria-label="Search portal users"><select id="wpSt" data-wp aria-label="Status"><option value="">All statuses</option><option>Login</option><option>Not logged in</option></select><span class="sub">Clients on the portal SSID (Hotspot/Guest). Location follows the Location filter above</span></div><div id="plist">${tbl(["Username", "Status", "Location", "Zone", "AP", "SSID", "IP", "MAC", "Signal", "Connected since", "Download", "Upload"].concat(W.canKill ? ["Action"] : []), rows, {tall: true, empty: "No clients on the portal SSID yet."})}</div>`);
    },
    top: () => panel("c8", "Top Usage", "10 clients with the most traffic (running sessions)", tbl(["User / Host", "MAC", "SSID", "AP", "Download", "Upload", "Total"], W.top.map(x => [x.user || x.host || "-", x.mac, x.ssid || "-", x.ap || "-", wBytes(x.tx), wBytes(x.rx), wBytes(x.bytes)]), {r: [4, 5, 6], empty: "No data yet."})),
    apdown: () => panel("c4", "Access Points Not Online", fmt(W.apTotal - W.apOnline) + " of " + fmt(W.apTotal), tbl(["AP", "Zone", "Status", "Last seen"], W.apDown.slice(0, 10).map(x => [x.name || "-", x.zone || "-", x.status || "-", x.since ? dtime(x.since) : "-"]), {empty: "All APs are online."}))
  };
}
/* WiFi history over the filter period: usage per day, zone, SSID, location, AP, device, and top clients (from stored sessions). */
function wifiHist(W) {
  const H = W.hist, G = 1073741824, days = H.daily.map(x => ({label: dmon(x.date), full: dlong(x.date)}));
  const u = x => wBytes(x.bytes) + " · " + fmt(x.clients) + " clients";
  const hb = (a, f) => hbars(a.map(x => [x.k, x.bytes, 0, f ? f(x) : u(x)]));
  const note = H.since && H.since.slice(0, 10) > H.from ? "history available since " + dmon(H.since.slice(0, 10)) : "";
  const kp = `<div class="kpis k6">${kpi("Sessions", fmt(H.sessions), "in the period" + (note ? ", " + note : ""))}${kpi("Unique Clients", fmt(H.clients), "distinct MACs")}${kpi("Total Usage", wBytes(H.rx + H.tx), "download " + wBytes(H.tx) + " · upload " + wBytes(H.rx))}${kpi("Average per Client", H.clients ? wBytes((H.rx + H.tx) / H.clients) : "-", "usage per unique client")}</div>`;
  return `<div class="grid">${panel("c12", "WiFi History", dmon(H.from) + " – " + dmon(H.to), kp)}` +
    panel("c8", "Usage per Day", "total download + upload (GB)", bars(days, [{name: "Usage (GB)", c: "--s1", v: H.daily.map(x => +(x.bytes / G).toFixed(2))}], {dec: 1, unit: " GB", label: "WiFi usage per day"})) +
    panel("c4", "Session Start Hour", "sessions by hour", bars(hrs24(), [{name: "Sessions", c: "--s2", v: H.hours}], {label: "Sessions per hour"})) +
    panel("c6", "Clients and Sessions per Day", "", legend([{name: "Unique clients", c: "--s1"}, {name: "Sessions", c: "--s2"}]) + bars(days, [{name: "Unique clients", c: "--s1", v: H.daily.map(x => x.clients)}, {name: "Sessions", c: "--s2", v: H.daily.map(x => x.sessions)}], {label: "Clients and sessions per day"})) +
    panel("c6", "Dominant Devices", "device type by usage", hb(H.byDevice)) +
    panel("c4", "Usage per Zone", "top 10", hb(H.byZone)) + panel("c4", "Usage per SSID", "top 10", hb(H.bySsid)) + panel("c4", "Usage per Location", "top 10", hb(H.byLoc)) +
    panel("c4", "Usage per AP", "top 10", hb(H.byAp)) +
    panel("c8", "Top Clients of the Period", "by total usage", tbl(["User / Host", "MAC", "SSID", "Sessions", "Total usage"], H.top.map(x => [x.user || x.host || "-", x.mac, x.ssid || "-", x.sessions, wBytes(x.bytes)]), {r: [3, 4], empty: "No session history in this period."})) + `</div>`;
}function vWifi() {
  const W = V.wifi, grid = h => `<div class="grid">${h}</div>`;
  if (!W) return grid(`<section class="panel c12">${empty()}</section>`);
  if (!W.configured || !(W.total || W.enabled)) return grid(panel("c12", "WiFi Users", "", `<div class="empty"><b>No WiFi data yet</b><span>${W.error ? "Last sync failed: " + esc(W.error) : "Enter the Ruckus vSZ address and API account in Admin → Integrations → Ruckus vSZ, enable it, then click Sync now."}</span></div>`));
  const warns = [];
  if (W.error) warns.push(`<li class="crit"><span><b>vSZ sync failed:</b> ${esc(W.error)}</span></li>`);
  else if (W.stale) warns.push(`<li class="warn"><span><b>Data not updated</b> since ${esc(dtime(W.updated))}. Check the Ruckus vSZ connector.</span></li>`);
  if (W.apTotal && W.apTotal - W.apOnline) warns.push(`<li class="warn"><span><b>${W.apTotal - W.apOnline} Access Points not online</b> of ${W.apTotal}.</span></li>`);
  const kp = `<div class="kpis k6">${kpi("Active Clients", fmt(W.total), "connected now")}${kpi("Portal Login", fmt(W.portalLogin), "of " + fmt(W.portal.length) + " portal SSID clients")}${kpi("Access Point", W.apTotal ? fmt(W.apOnline) + " / " + fmt(W.apTotal) : "-", "online", {cls: W.apTotal && W.apOnline < W.apTotal ? "warnv" : ""})}${kpi("Weak Signal", fmt(W.weak), "below " + W.weakAt + " dBm", {cls: W.weak ? "warnv" : ""})}${kpi("Download", wBytes(W.tx), "running sessions, all clients")}${kpi("Upload", wBytes(W.rx), "running sessions, all clients")}</div>`;
  const P = wifiPanels(W);
  const rows = W.list.map(x => [x.user || "-", x.host || "-", x.mac, x.ip || "-", x.ssid || "-", x.ap || "-", x.zone || "-", x.loc || "-", x.band, {h: x.rssi == null ? "-" : `<span class="${x.rssi < W.weakAt ? "crit-t" : ""}">${x.rssi} dBm</span>`}, x.since ? dtime(x.since) : "-", wBytes(x.tx), wBytes(x.rx)]
    .concat(W.canKill ? [{h: `<button type="button" class="btn ghost sm" data-wkill="${esc(x.mac)}" data-mode="disconnect" title="Disconnect this client's session">Disconnect</button> <button type="button" class="btn ghost sm" data-wkill="${esc(x.mac)}" data-mode="deauth" title="Deauth: remove the authorization state (the portal asks for login again)">Deauth</button>`}] : []));
  const heads = ["Username", "Host", "MAC", "IP", "SSID", "AP", "Zone", "Location", "Band", "Signal", "Connected since", "Download", "Upload"].concat(W.canKill ? ["Action"] : []);
  const L = W.list;
  return insArea("wifi") + (warns.length ? grid(`<section class="panel c12"><ul class="att">${warns.join("")}</ul></section>`) : "") + kp + grid(
    P.portal() + P.trend() + P.band() + P.ssid() + P.usage() + P.ap() + P.zone() + P.loc() + P.top() + P.apdown() +
    panel("c12", "Client List", W.total + " clients" + (W.total > L.length ? ", showing " + L.length : ""), `<div class="dtool"><input type="search" id="dq" class="msearch" placeholder="Search username, host, MAC, IP, SSID, or AP" aria-label="Search clients">${wSel("wfSsid", "All SSIDs", L.map(x => x.ssid))}${wSel("wfAp", "All APs", L.map(x => x.ap))}${wSel("wfZone", "All zones", L.map(x => x.zone))}${wSel("wfBand", "All bands", L.map(x => x.band))}<span class="sub">${W.canKill ? "Disconnect ends the session; Deauth makes the client log in again" : "Your account can only view"}</span></div><div id="dlist">${tbl(heads, rows, {tall: true, empty: "No active clients."})}</div>`)) + (W.hist ? wifiHist(W) : "");
}
