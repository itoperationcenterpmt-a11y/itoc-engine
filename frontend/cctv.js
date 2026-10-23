/* Milestone menu (XProtect): camera, public announcer, and hardware inventory from the RESTful API, stored in the dashboard database. Online status comes from Zabbix (matched by IP or name). */
"use strict";
const frac = (a, b) => a === b ? fmt(a) : fmt(a) + "/" + fmt(b);          /* whole number when complete, fraction when something is missing */
const msZ = z => z === "up" ? pill("good", "Online") : z === "down" ? pill("crit", "Offline") : z === "degraded" ? pill("warn", "Interface issue") : z ? pill("idle", z === "maintenance" ? "Maintenance" : "Disabled") : "–";
function cctvPanels(C) {
  const off = C.total - C.camEnabled, norec = C.camEnabled - C.recording;
  return {
    kpi: () => `<section class="panel c4 dom"><header><h2>Milestone</h2></header><div class="mini">${kpi("Cameras", fmt(C.total), fmt(C.nHw) + " hardware")}${kpi("Enabled", frac(C.camEnabled, C.total), off ? fmt(off) + " disabled" : "all enabled", {cls: off ? "warnv" : ""})}${kpi("Recording Centrally", frac(C.recording, C.camEnabled), "recording active on this server")}${kpi("Recording On Site", fmt(norec), "not recording on the central server")}</div>${go("cctv")}</section>`,
    hw: () => panel("c8", "Hardware", fmt(C.nHw) + " hardware (NVR / interconnect / IP speaker) · most devices at the top", tbl(["Server", "Hardware", "Address", "Model", "Type", "Devices", "Enabled", "Recording Centrally", "Offline", "Status"],
      C.hw.map(h => [h.server, h.name, h.host, h.model, {h: h.type === "pa" ? pill("idle", "Public Announcer") : "Camera"}, h.cameras, frac(h.camEnabled, h.cameras), frac(h.rec, h.camEnabled), h.zdown ? {h: `<b class="crit-t">${h.zdown}</b>`} : "0", {h: h.enabled ? pill("good", "Active") : pill("idle", "Inactive")}]), {r: [5, 6, 7, 8], empty: "No hardware yet."})),
    srv: () => panel("c12", "Milestone Servers", fmt(C.servers.length) + " servers · licence = enabled devices that use a licence ÷ licensed devices (set per server in Admin → Integrations)",
      tbl(["Server", "Hardware", "Cameras", "Public Announcers", "Enabled", "Recording Centrally", "Licence", "Updated"],
        C.servers.map(s => [s.name, s.hw, s.cameras, s.pa, frac(s.enabled, s.cameras + s.pa), frac(s.rec, s.enabled),
          {h: s.licTotal != null ? `<span class="${s.licUsed > s.licTotal ? "crit-t" : s.licUsed >= s.licTotal * 0.9 ? "warn-t" : ""}"><b>${fmt(s.licUsed)}</b>/${fmt(s.licTotal)}</span>` : fmt(s.licUsed)}, s.updated ? dtime(s.updated) : "-"]), {r: [1, 2, 3, 4, 5, 6], empty: "No servers yet."})),
    rec: () => panel("c4", "Central Recording per Hardware", "devices recording on the central server (Interconnect hardware records on its site)", hbars(C.hw.filter(h => h.camEnabled).slice(0, 10).map(h => [h.name, h.rec, 0, frac(h.rec, h.camEnabled)])))
  };
}
function vCctv() {
  const C = V.cctv, grid = h => `<div class="grid">${h}</div>`;
  if (!C) return grid(`<section class="panel c12">${empty()}</section>`);
  if (!C.configured || !(C.total || C.pa.total)) return grid(panel("c12", "Milestone", "", `<div class="empty"><b>No Milestone data yet</b><span>${C.error ? "Last sync failed: " + esc(C.error) : "Enter the Milestone Basic user account in Admin → Integrations → Milestone XProtect (CCTV), enable it, then click Sync now."}</span></div>`));
  const warns = [], off = C.total - C.camEnabled, norec = C.camEnabled - C.recording, over = C.servers.filter(s => s.licTotal != null && s.licUsed > s.licTotal);
  if (C.error) warns.push(`<li class="crit"><span><b>Milestone sync failed:</b> ${esc(C.error)}</span></li>`);
  else if (C.stale) warns.push(`<li class="warn"><span><b>Data not updated</b> since ${esc(dtime(C.updated))}. Check the Milestone connector.</span></li>`);
  if (C.hwOff) warns.push(`<li class="warn"><span><b>${fmt(C.hwOff)} hardware disabled</b> in Milestone.</span></li>`);
  over.forEach(s => warns.push(`<li class="crit"><span><b>${esc(s.name)} uses ${fmt(s.licUsed)} licences</b>, more than the ${fmt(s.licTotal)} licensed.</span></li>`));
  const kp = `<div class="kpis k6">${kpi("Cameras", fmt(C.total), fmt(C.nHw) + " hardware")}${kpi("Enabled", frac(C.camEnabled, C.total), off ? fmt(off) + " disabled" : "all enabled", {cls: off ? "warnv" : ""})}${kpi("Recording Centrally", frac(C.recording, C.camEnabled), "recording active on this server")}${kpi("Recording On Site", fmt(norec), "not recording on the central server")}${kpi("Online", C.zbx.matched ? frac(C.zbx.up + C.zbx.other, C.zbx.matched) : "-", C.zbx.matched ? fmt(C.zbx.down) + " offline · " + fmt(C.zbx.none) + " no status" : "no match yet", {cls: C.zbx.down ? "warnv" : ""})}${kpi("Public Announcers", C.pa.total ? frac(C.pa.enabled, C.pa.total) : "0", C.pa.total ? "IP speakers, not counted as cameras" + (C.pa.down ? " · " + fmt(C.pa.down) + " offline" : "") : "none found")}</div>`
    + `<p class="sub msnote">Enabled and Recording come from the Milestone configuration (its API does not report live device state). Online and Offline come from Zabbix, matched by IP address or by name${C.zbx.matched ? ": " + fmt(C.zbx.matched) + " of " + fmt(C.total) + " cameras matched" : ". Matching starts after the next Zabbix sync"}. Last Milestone sync: ${C.updated ? dtime(C.updated) : "-"}.</p>`;
  const P = cctvPanels(C);
  const rows = C.list.map(x => [x.server, x.name, x.hw, x.ip || "-", {h: x.type === "pa" ? pill("idle", "Public Announcer") : "Camera"}, x.ch == null ? "-" : x.ch, {h: x.enabled ? pill("good", "Active") : pill("idle", "Inactive")}, {h: msZ(x.zbx)}, x.zprob ? x.zprob + (x.zsince ? " · since " + dtime(x.zsince) : "") : "–", {h: x.rec ? pill("good", "Yes") : pill("idle", "No")}, x.fps || "-", x.mod ? dtime(x.mod) : "-"]);
  return (warns.length ? grid(`<section class="panel c12"><ul class="att">${warns.join("")}</ul></section>`) : "") + kp + grid(
    P.srv() + P.hw() + P.rec() +
    panel("c12", "Device List", fmt(C.total) + " cameras" + (C.pa.total ? " · " + fmt(C.pa.total) + " public announcers" : ""), `<div class="dtool"><input type="search" id="dq" class="msearch" placeholder="Search server, name, hardware, or IP" aria-label="Search devices"><span class="sub">Filter by server, hardware, type, and status in the filter bar above</span></div><div id="dlist">${tbl(["Server", "Name", "Hardware", "IP", "Type", "Ch", "Status", "Online", "Zabbix problem", "Recording Centrally", "FPS", "Changed"], rows, {tall: true, empty: "No devices yet."})}</div>`));
}
