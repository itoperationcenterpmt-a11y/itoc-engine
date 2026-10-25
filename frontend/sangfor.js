/* Internet Usage (Network menu): bandwidth, applications, and users from the Sangfor IAG Report Center export of each site. Choose the report period in the top filter bar. */
"use strict";
const sgVol = g => g == null ? "–" : g >= 1000 ? fx(g / 1000, 2) + " TB" : fx(g, 1) + " GB";
function sgUpload(G) {
  const sites = [...new Set([...CFG.sites])], def = S.site && sites.includes(S.site) ? S.site : (G.sites[0] && sites.includes(G.sites[0]) ? G.sites[0] : sites[0]);
  return panel("c12", "Upload a Report Center export", "one site and one period per upload",
    `<div class="sgup"><label class="fld"><span class="lbl">Location of the Sangfor device</span><select id="upsgSite">${sites.map(s => `<option ${s === def ? "selected" : ""}>${esc(s)}</option>`).join("")}</select></label>
      <div class="drop"><span class="sub">The .xlsx reports exported from the Report Center, or the .tar.gz / .zip that holds them. Per-person reports (Work Efficiency, Employee Turnover Risk) are not read.</span>
      <label class="btn upbtn" for="upsg">Choose files</label><input type="file" id="upsg" accept=".xlsx,.zip,.gz,.tgz" multiple class="vh"><div id="upsgmsg"></div></div></div>`);
}
function vSangfor() {
  const G = V.sangfor, grid = h => `<div class="grid">${h}</div>`, up = canUp("sangfor");
  if (!G) return grid(`<section class="panel c12">${empty()}</section>`);
  const cur = G.cur, bt = G.batches;
  const batches = bt.length ? panel("c12", "Uploaded reports", fmt(bt.length) + " reports", tbl(["Location", "Period", "Uploaded", "By", ...(up ? [""] : [])], bt.map(b => [b.site, dmon(b.from) + " – " + dfull(b.to), b.at ? dtime(Date.parse(b.at.endsWith("Z") ? b.at : b.at + "Z")) : "–", b.by || "–", ...(up ? [{h: `<button type="button" class="btn ghost sm" data-sgdel="${b.id}">Delete</button>`}] : [])]), {empty: "Nothing uploaded yet."})) : "";
  if (!cur) {
    const sum = G.summary.length > 1 ? panel("c12", "Latest report per location", "choose a location in the top bar for the details", tbl(["Location", "Period", "Traffic", "Average", "Peak", "Users"], G.summary.map(x => [x.site, dmon(x.from) + " – " + dfull(x.to), sgVol(x.gb), x.avg == null ? "–" : fx(x.avg, 1) + " Mb/s", x.max == null ? "–" : fx(x.max, 1) + " Mb/s", x.users == null ? "–" : x.users]), {r: [2, 3, 4, 5]})) : "";
    return grid((up ? sgUpload(G) : "") + (sum || panel("c12", "Internet Usage", "", `<div class="empty"><b>No Sangfor report yet</b><span>${up ? "Upload the Report Center export of a site above." : "Ask an administrator to upload the Sangfor Report Center export."}</span></div>`)) + batches);
  }
  const b = cur.batch, T = cur.totalGb, bars_ = rows => rows.length ? hbars(rows) : `<div class="empty sm">No data in this export.</div>`;
  const kp = `<div class="kpis k6">${kpi("Total Traffic", sgVol(T), dmon(b.from) + " – " + dfull(b.to))}${kpi("Average Bandwidth", cur.avg == null ? "–" : fx(cur.avg, 1) + " Mb/s", "")}${kpi("Peak Bandwidth", cur.max == null ? "–" : fx(cur.max, 1) + " Mb/s", "")}${kpi("Inbound Share", cur.inPct == null ? "–" : pc(cur.inPct, 1), cur.inGb != null ? sgVol(cur.inGb) + " in · " + sgVol(cur.outGb) + " out" : "")}${kpi("Users Seen", cur.users == null ? "–" : fmt(cur.users), "distinct IP addresses")}${kpi("Rejected Requests", fmt(cur.reject), "blocked by access rules", {cls: cur.reject ? "warnv" : ""})}</div>`;
  const dd = cur.sharing.map(x => ({label: dmon(x[0]), full: dlong(x[0])}));
  return `<p class="sub msnote">${esc(b.site)} · Report Center export of ${dmon(b.from)} – ${dfull(b.to)} · uploaded by ${esc(b.by || "–")}</p>` + kp + grid(
    panel("c6", "Traffic by Application Category", "", bars_(cur.cats.map(x => [x.k, x.gb, 0, sgVol(x.gb)]))) +
    panel("c6", "Top Applications", "", bars_(cur.apps.map(x => [x.k, x.gb, 0, sgVol(x.gb)]))) +
    panel("c6", "Top Users by Traffic", "IP address", tbl(["User (IP)", "Traffic"], cur.topUsers.map(x => [x.k, {h: `<span class="nw">${sgVol(x.gb)}</span>`}]), {r: [1], empty: "No data in this export."})) +
    panel("c6", "Heaviest Users at Peak Bandwidth", "share of the peak", tbl(["User (IP)", "Peak", "Share"], cur.peakUsers.map(x => [x.k, x.mbps == null ? "–" : fx(x.mbps, 1) + " Mb/s", x.pct == null ? "–" : fx(x.pct, 1) + "%"]), {r: [1, 2], empty: "No data in this export."})) +
    panel("c6", "Users per Application Category", "", bars_(cur.access.map(x => [x.k, x.users, 0, fmt(x.users)]))) +
    panel("c6", "Inbound and Outbound", "", cur.dirs.length ? vzDonut(cur.dirs.map(x => ({k: x.k, v: x.gb, c: x.k === "Inbound" ? VZC.s1 : VZC.warn})), {center: sgVol(T), sub: "total", label: "Direction"}) : `<div class="empty sm">No data in this export.</div>`) +
    (cur.sharing.length ? panel("c12", "Users Sharing a Connection per Day", "at least two endpoints behind one user", bars(dd, [{name: "Users", c: "--s1", v: cur.sharing.map(x => x[1] || 0)}], {label: "Users sharing a connection"})) : "") +
    panel("c12", "Application Categories", "", tbl(["Category", "Traffic", "Share", "Top user", "Top application"], cur.rankRows.map(x => [x.k, {h: `<span class="nw">${sgVol(x.gb)}</span>`}, x.pct == null ? "–" : fx(x.pct, 1) + "%", x.topUser, x.topApp]), {r: [1, 2], empty: "No data in this export."})) +
    (up ? sgUpload(G) : "") + batches);
}
