/* CCTV menu (Milestone XProtect): camera and hardware inventory from the RESTful API, stored in the dashboard database. Real-time online status is in the Devices menu (Zabbix). */
"use strict";
function cctvPanels(C) {
  const off = C.total - C.camEnabled, norec = C.camEnabled - C.recording;
  return {
    kpi: () => `<section class="panel c4 dom"><header><h2>Milestone</h2></header><div class="mini">${kpi("Cameras", fmt(C.total), fmt(C.nHw) + " hardware")}${kpi("Enabled", fmt(C.camEnabled), fmt(off) + " disabled", {cls: off ? "warnv" : ""})}${kpi("Recording Centrally", fmt(C.recording), "recording active on this server")}${kpi("Recording On Site", fmt(norec), "not recording on the central server")}</div>${go("cctv")}</section>`,
    hw: () => panel("c8", "Cameras per Hardware", fmt(C.nHw) + " hardware (NVR/interconnect) · most at the top", tbl(["Server", "Hardware", "Address", "Model", "Cameras", "Enabled", "Recording Centrally", "Offline (Zabbix)", "Status"],
      C.hw.map(h => [h.server, h.name, h.host, h.model, h.cameras, h.camEnabled, h.rec, h.zdown ? {h: `<b class="crit-t">${h.zdown}</b>`} : "0", {h: h.enabled ? pill("good", "Active") : pill("idle", "Inactive")}]), {r: [4, 5, 6, 7], empty: "No hardware yet."})),
    srv: () => panel("c12", "Server Milestone", fmt(C.servers.length) + " server", tbl(["Server", "Hardware", "Cameras", "Enabled", "Recording Centrally", "Updated"], C.servers.map(s => [s.name, s.hw, s.cameras, s.enabled, s.rec, s.updated ? dtime(s.updated) : "-"]), {r: [1, 2, 3, 4], empty: "No servers yet."})),
    rec: () => panel("c4", "Central Recording per Hardware", "cameras recording on the central server (Interconnect hardware records on its site)", hbars(C.hw.filter(h => h.camEnabled).slice(0, 10).map(h => [h.name, h.rec, 0, fmt(h.rec) + " / " + fmt(h.camEnabled)])))
  };
}
function vCctv() {
  const C = V.cctv, grid = h => `<div class="grid">${h}</div>`;
  if (!C) return grid(`<section class="panel c12">${empty()}</section>`);
  if (!C.configured || !C.total) return grid(panel("c12", "Milestone", "", `<div class="empty"><b>No CCTV data yet</b><span>${C.error ? "Last sync failed: " + esc(C.error) : "Enter the Milestone Basic user account in Admin → Integrations → Milestone XProtect (CCTV), enable it, then click Sync now."}</span></div>`));
  const warns = [], off = C.total - C.camEnabled, norec = C.camEnabled - C.recording;
  if (C.error) warns.push(`<li class="crit"><span><b>Milestone sync failed:</b> ${esc(C.error)}</span></li>`);
  else if (C.stale) warns.push(`<li class="warn"><span><b>Data not updated</b> since ${esc(dtime(C.updated))}. Check the Milestone connector.</span></li>`);
  if (C.hwOff) warns.push(`<li class="warn"><span><b>${fmt(C.hwOff)} hardware disabled</b> in Milestone.</span></li>`);
  const kp = `<div class="kpis k6">${kpi("Cameras", fmt(C.total), "registered in Milestone")}${kpi("Hardware", fmt(C.nHw), "NVR / interconnect")}${kpi("Enabled", fmt(C.camEnabled), fmt(off) + " disabled", {cls: off ? "warnv" : ""})}${kpi("Recording Centrally", fmt(C.recording), "recording active on this server")}${kpi("Recording On Site", fmt(norec), "not recording on the central server")}${kpi("Online (Zabbix)", C.zbx.matched ? fmt(C.zbx.up) + " / " + fmt(C.zbx.matched) : "-", C.zbx.matched ? fmt(C.zbx.down) + " offline · " + fmt(C.zbx.none) + " not in Zabbix" : "no IP match yet", {cls: C.zbx.down ? "warnv" : ""})}</div>`
    + `<p class="sub msnote">Enabled and Recording come from the Milestone configuration (its API does not report live camera state). Online and Offline come from Zabbix, matched by IP address${C.zbx.matched ? ": " + fmt(C.zbx.matched) + " of " + fmt(C.total) + " cameras matched" : ". Matching starts after the next Zabbix sync"}. Last Milestone sync: ${C.updated ? dtime(C.updated) : "-"}.</p>`;
  const P = cctvPanels(C);
  const rows = C.list.map(x => [x.server, x.name, x.hw, x.ip || "-", x.ch == null ? "-" : x.ch, {h: x.enabled ? pill("good", "Active") : pill("idle", "Inactive")}, {h: x.zbx === "up" ? pill("good", "Online") : x.zbx === "down" ? pill("crit", "Offline") : x.zbx === "degraded" ? pill("warn", "Interface") : x.zbx ? pill("idle", x.zbx === "maintenance" ? "Maintenance" : "Disabled") : "–"}, {h: x.rec ? pill("good", "Yes") : pill("idle", "No")}, x.fps || "-", x.mod ? dtime(x.mod) : "-"]);
  return (warns.length ? grid(`<section class="panel c12"><ul class="att">${warns.join("")}</ul></section>`) : "") + kp + grid(
    (C.servers.length > 1 ? P.srv() : "") + P.hw() + P.rec() +
    panel("c12", "Camera List", C.total + " cameras", `<div class="dtool"><input type="search" id="dq" class="msearch" placeholder="Search server, camera name, hardware, or IP" aria-label="Search cameras"><span class="sub">Milestone configuration data; per-device online status is in the Devices menu</span></div><div id="dlist">${tbl(["Server", "Camera", "Hardware", "IP", "Ch", "Status", "Zabbix", "Recording Centrally", "FPS", "Changed"], rows, {tall: true, empty: "No cameras yet."})}</div>`));
}
