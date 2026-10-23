/* Milestone menu (XProtect): camera, public announcer, and hardware inventory from the RESTful API, stored in the dashboard database. Online status comes from Zabbix (matched by IP or name). */
"use strict";
const frac = (a, b) => a === b ? fmt(a) : fmt(a) + "/" + fmt(b);          /* whole number when complete, fraction when something is missing */
const MS_T = {fix: "FIX", ptz: "PTZ", pa: "Public Announcer", mixed: "Mixed"};
const msDot = (z, n) => { const [c, t, g] = z === "up" ? ["good", "Online", "●"] : z === "down" ? ["crit", "Offline", "●"] : z === "degraded" ? ["warn", "Online, interface issue", "●"] : z ? ["idle", z === "maintenance" ? "Maintenance" : "Disabled", "◐"] : ["idle", "Not in Zabbix", "○"]; return `<span class="ost ${c}" title="${t}">${g}</span>${n != null ? " " + n : ""}`; };
const msType = t => t === "pa" ? pill("idle", MS_T.pa) : MS_T[t] || t;
function cctvPanels(C) {
  const off = C.total - C.camEnabled, norec = C.camEnabled - C.recording;
  return {
    kpi: () => `<section class="panel c4 dom"><header><h2>Milestone</h2></header><div class="mini">${kpi("Cameras", fmt(C.total), fmt(C.nHw) + " hardware")}${kpi("Enabled", frac(C.camEnabled, C.total), off ? fmt(off) + " disabled" : "", {cls: off ? "warnv" : ""})}${kpi("Recording Centrally", frac(C.recording, C.camEnabled), "")}${kpi("Recording On Site", fmt(norec), "")}</div>${go("cctv")}</section>`,
    hw: () => panel("c12", "Hardware", fmt(C.nHw), tbl(["Server", "Hardware", "Address", "Model", "Type", "Devices", "Enabled", "Recording Centrally", "Online", "Status"],
      C.hw.map(h => [h.server, h.name, h.host, h.model, {h: msType(h.type)}, h.cameras, frac(h.camEnabled, h.cameras), frac(h.rec, h.camEnabled), {h: !h.zn ? msDot("") : h.zdown ? msDot("down", h.zdown) : msDot("up")}, {h: h.enabled ? pill("good", "Active") : pill("idle", "Inactive")}]), {r: [5, 6, 7], empty: "No hardware yet."})),
    srv: () => panel("c12", "Milestone Servers", fmt(C.servers.length), 
      tbl(["Server", "Hardware", "Cameras", "Public Announcers", "Enabled", "Recording Centrally", "Licence", "Updated"],
        C.servers.map(s => [s.name, s.hw, s.cameras, s.pa, frac(s.enabled, s.cameras + s.pa), frac(s.rec, s.enabled),
          {h: s.licTotal != null ? `<span class="${s.licUsed > s.licTotal ? "crit-t" : s.licUsed >= s.licTotal * 0.9 ? "warn-t" : ""}"><b>${fmt(s.licUsed)}</b>/${fmt(s.licTotal)}</span>` : fmt(s.licUsed)}, s.updated ? {h: `<span class="nw">${dtime(s.updated)}</span>`} : "-"]), {r: [1, 2, 3, 4, 5, 6], empty: "No servers yet."})),
    rec: () => panel("c12", "Central Recording per Hardware", "", hbars(C.hw.filter(h => h.camEnabled).slice(0, 10).map(h => [h.name, h.rec, 0, frac(h.rec, h.camEnabled)])))
  };
}
function vCctv() {
  const C = V.cctv, grid = h => `<div class="grid">${h}</div>`;
  if (!C) return grid(`<section class="panel c12">${empty()}</section>`);
  if (!C.configured || !(C.total || C.pa.total)) return grid(panel("c12", "Milestone", "", `<div class="empty"><b>No Milestone data yet</b><span>${C.error ? "Last sync failed: " + esc(C.error) : "Enter the Milestone Basic user account in Admin → Integrations → Milestone XProtect (CCTV), enable it, then click Sync now."}</span></div>`));
  const warns = [], off = C.total - C.camEnabled, norec = C.camEnabled - C.recording, over = C.servers.filter(s => s.licTotal != null && s.licUsed > s.licTotal);
  if (C.error) warns.push(`<li class="crit"><span><b>Milestone sync failed:</b> ${esc(C.error)}</span></li>`);
  else if (C.stale) warns.push(`<li class="warn"><span><b>Data not updated</b> since ${esc(dtime(C.updated))}. Check the Milestone connector.</span></li>`);
  Object.entries(C.serverErrors || {}).forEach(([n, m]) => warns.push(`<li class="warn"><span><b>${esc(n)} did not sync:</b> ${esc(String(m).slice(0, 160))}</span></li>`));
  if (C.hwOff) warns.push(`<li class="warn"><span><b>${fmt(C.hwOff)} hardware disabled</b> in Milestone.</span></li>`);
  over.forEach(s => warns.push(`<li class="crit"><span><b>${esc(s.name)} uses ${fmt(s.licUsed)} licences</b>, more than the ${fmt(s.licTotal)} licensed.</span></li>`));
  const kp = `<div class="kpis k6">${kpi("Cameras", fmt(C.total), fmt(C.fix) + " FIX · " + fmt(C.ptz) + " PTZ")}${kpi("Enabled", frac(C.camEnabled, C.total), off ? fmt(off) + " disabled" : "", {cls: off ? "warnv" : ""})}${kpi("Recording Centrally", frac(C.recording, C.camEnabled), "")}${kpi("Recording On Site", fmt(norec), "")}${kpi("Zabbix Status", `<span class="ostv">${msDot("up", fmt(C.zbx.up + C.zbx.other))}${msDot("down", fmt(C.zbx.down))}${msDot("", fmt(C.zbx.none))}</span>`, "", {cls: C.zbx.down ? "warnv" : ""})}${kpi("Public Announcers", fmt(C.pa.total), C.pa.total ? frac(C.pa.enabled, C.pa.total) + " enabled" : "")}</div>`
    + `<p class="sub msnote">Status dots come from Zabbix: ${msDot("up")} online ${msDot("down")} offline ${msDot("")} not in Zabbix · last sync ${C.updated ? dtime(C.updated) : "-"}</p>`;
  const P = cctvPanels(C);
  const rows = C.list.map(x => [x.server, x.name, x.hw, x.ip || "-", {h: msType(x.type)}, x.ch == null ? "-" : x.ch, {h: x.enabled ? pill("good", "Active") : pill("idle", "Inactive")}, {h: msDot(x.zbx)}, x.zprob ? x.zprob + (x.zsince ? " · since " + dtime(x.zsince) : "") : "–", {h: x.rec ? pill("good", "Yes") : pill("idle", "No")}, x.fps || "-", x.mod ? dtime(x.mod) : "-"]);
  return (warns.length ? grid(`<section class="panel c12"><ul class="att">${warns.join("")}</ul></section>`) : "") + kp + grid(
    P.srv() + P.hw() + P.rec() +
    panel("c12", "Device List", fmt(C.total) + " cameras" + (C.pa.total ? " · " + fmt(C.pa.total) + " public announcers" : ""), `<div class="dtool"><input type="search" id="dq" class="msearch" placeholder="Search server, name, hardware, or IP" aria-label="Search devices"></div><div id="dlist">${tbl(["Server", "Name", "Hardware", "IP", "Type", "Ch", "Status", "Zabbix", "Zabbix problem", "Recording Centrally", "FPS", "Changed"], rows, {tall: true, empty: "No devices yet."})}</div>`));
}
