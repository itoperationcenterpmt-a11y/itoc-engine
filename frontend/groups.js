/* Summary pages of the parent menus: Network (PRTG + WiFi) and Cyber Security (NDR Palo Alto + XDR Trend Micro). Each source keeps its own page (sub-menu). */
"use strict";
const attList = att => att.length ? `<ul class="att">${att.map(a => `<li class="${a[0]}"><span>${a[1]}</span>${go(a[2], "View")}</li>`).join("")}</ul>` : `<div class="empty sm">Nothing needs follow-up.</div>`;
const rowLbl = t => `<div class="rowlbl">${t}</div>`;
function vNetwork() {
  const N = V.net ? netR() : null, Wf = V.wifi, hasW = !!(Wf && (Wf.total || Wf.apTotal)), grid = h => `<div class="grid">${h}</div>`;
  if (!N && !hasW) return grid(`<section class="panel c12">${empty("No network data for this filter.")}</section>`);
  const att = [], P = N ? N.P : null, WP = hasW ? wifiPanels(Wf) : null, bad = N ? N.rank.filter(s => s.status === NST.bad) : [];
  if (bad.length) att.push(["crit", `<b>${bad.length} links below target ${pc(P.target, 1)}</b>: ${bad.slice(0, 3).map(s => esc(s.link) + " (" + pc(s.av, 2) + ")").join(", ")}${bad.length > 3 ? ", …" : ""}.`, "noc"]);
  if (N && N.nodata) att.push(["warn", `<b>${N.nodata} links with insufficient data</b> (monitoring coverage &lt; ${pc(P.minCov, 0)}), not rated for SLA.`, "noc"]);
  if (hasW && Wf.apTotal - Wf.apOnline > 0) att.push(["warn", `<b>${Wf.apTotal - Wf.apOnline} WiFi Access Points not online</b> of ${Wf.apTotal}.`, "wifi"]);
  if (hasW && Wf.weak) att.push(["warn", `<b>${Wf.weak} WiFi clients with weak signal</b> (below ${Wf.weakAt} dBm).`, "wifi"]);
  if (hasW && (Wf.error || Wf.stale)) att.push(["warn", `<b>Ruckus data ${Wf.error ? "failed to sync" : "not updated"}</b>, check the connector in Admin.`, "wifi"]);
  const nk = N ? `${rowLbl("Link · PRTG")}<div class="kpis k6">${kpi("Availability", pc(N.avail, 2), "target " + pc(P.target, 1), {tip: RUMUS.av, cls: N.avail < P.target ? "warnv" : ""})}${kpi("Links Meeting SLA", N.ok + " of " + (N.ok + N.bad), N.bad + " not, " + N.nodata + " insufficient data", {tip: RUMUS.link})}${kpi("Total Downtime", fx(N.downH, 1) + " h", N.events + " incidents · " + N.noDown + " links without down", {tip: RUMUS.down})}${kpi("Data Coverage", pc(N.cov), "monitored hours ÷ period hours")}${kpi("Volume", fx(N.volTB, 1) + " TB", fx(N.mbps, 0) + " Mbit/s average")}${kpi("High Peak Utilization", fmt(N.utilHigh), "link ≥ " + pc(P.utilPeak, 0) + " of capacity", {tip: RUMUS.util})}</div>` : "";
  const nw = hasW ? `${rowLbl("WiFi · Ruckus")}<div class="kpis k6">${kpi("Active Clients", fmt(Wf.total), "connected now")}${kpi("Access Point", Wf.apTotal ? fmt(Wf.apOnline) + " / " + fmt(Wf.apTotal) : "-", "online", {cls: Wf.apTotal && Wf.apOnline < Wf.apTotal ? "warnv" : ""})}${kpi("Weak Signal", fmt(Wf.weak), "below " + Wf.weakAt + " dBm", {cls: Wf.weak ? "warnv" : ""})}${kpi("Portal Login", fmt(Wf.portalLogin), "of " + fmt(Wf.portal.length) + " portal SSID clients")}${kpi("Download", wBytes(Wf.tx), "running sessions")}${kpi("Upload", wBytes(Wf.rx), "running sessions")}</div>` : "";
  const key = s => String(s || "").toLowerCase().replace(/^branch\s+/, "").trim(), rows = {};
  (N ? N.lokasi : []).forEach(x => { rows[key(x.k)] = {k: x.k, n: x.n, av: x.minAv, down: x.downMin, bad: x.bad}; });
  (hasW ? Wf.byLocAp : []).forEach(x => { const r = rows[key(x.k)] || (rows[key(x.k)] = {k: x.k}); Object.assign(r, {ap: x.apTotal, apOn: x.apOnline, cl: x.clients}); });
  const loc = Object.values(rows).sort((a, b) => ((b.bad || 0) - (a.bad || 0)) || (((b.ap || 0) - (b.apOn || 0)) - ((a.ap || 0) - (a.apOn || 0))) || String(a.k).localeCompare(String(b.k)));
  const st = r => (r.bad ? pill("crit", "Link problem") : (r.ap || 0) - (r.apOn || 0) > 0 ? pill("warn", "AP offline") : pill("good", "Normal"));
  const locP = panel("c12", "Summary per Location", "PRTG links and Ruckus WiFi combined by location name", tbl(["Location", "Links", "Lowest availability", "Downtime (min)", "AP online / total", "WiFi clients", "Status"],
    loc.map(r => [r.k, r.n == null ? "-" : r.n, r.av == null ? "-" : pc(r.av, 3), r.down == null ? "-" : r.down, r.ap == null ? "-" : r.apOn + " / " + r.ap, r.cl == null ? "-" : r.cl, {h: st(r)}]), {tall: true, r: [1, 2, 3, 5], empty: "No location data yet."}));
  return grid(panel("c12", "Attention", ctxTxt(APPLY.network), attList(att))) + insArea("network") + nk + nw + grid(
    (N ? panel("c8", "Link Downtime per Day", "Downtime minutes of all links in the filter", bars(dayB(N.daily), [{name: "Downtime (min)", c: "--crit", v: N.daily.map(x => x.down)}], {dec: 1, unit: " min", label: "Daily downtime"})) : "") +
    (N ? panel("c4", "Top 5 Links by Downtime", "Availability = Σ Up ÷ Σ (Up + Down)", tbl(["Link", "Availability", "Downtime (h)"], N.rank.slice(0, 5).map(s => [s.link, pc(s.av, 3), fx(s.down / 3600, 1)]), {r: [1, 2], empty: "No data yet."})) : "") +
    (hasW ? WP.trend() + WP.apdown() : "") + locP + (hasW ? WP.ssid() + WP.usage() + WP.loc() : ""));
}
function vCyber() {
  const R = V.soc && V.soc.hasData ? socR() : null, chk = socCheck(), okD = chk.filter(x => x.s === "ok" || x.s === "dup").length, X = V.xdr, hasX = !!(X && X.configured && (X.listN || X.enabled)), grid = h => `<div class="grid">${h}</div>`;
  if (!R && !hasX) return grid(`<section class="panel c12">${empty("No security data for this filter. Import Panorama RAW or enable API sync, and fill in the Trend Micro XDR connector.")}</section>`);
  const att = [], sv = hasX ? Object.fromEntries(X.bySev.map(x => [x.k, x.n])) : {};
  if (R && R.chAlert) att.push(["warn", `<b>NDR: ${fmt(R.chAlert)} critical/high events alert only</b>, not blocked by the firewall.`, "soc"]);
  if (R && okD < chk.length) att.push(["warn", `<b>NDR: daily data incomplete</b> (${okD} of ${chk.length} days validated).`, "kelengkapan"]);
  if (hasX && X.backlogCH) att.push(["warn", `<b>XDR: ${fmt(X.backlogCH)} critical/high alerts still open</b> (all periods).`, "xdr"]);
  if (hasX && (X.error || X.stale)) att.push(["warn", `<b>Trend Micro data ${X.error ? "failed to sync" : "not updated"}</b>, check the connector in Admin.`, "xdr"]);
  const B = R ? dayB(R.daily) : [], ch = R ? [{name: "Critical", c: "--crit", v: R.daily.map(x => x.critical)}, {name: "High", c: "--serious", v: R.daily.map(x => x.high)}] : [];
  const nk = R ? `${rowLbl("NDR · Palo Alto Panorama")}<div class="kpis k6">${kpi("Total Events", fmt(R.total), "average " + fmt(R.total / (okD || 1)) + " per validated day", {tip: RUMUS.socTot})}${kpi("Critical + High", fmt(R.ch), fmt(R.crit) + " critical")}${kpi("Critical + High Blocked", pc(R.chBlkPct), "actions other than alert", {tip: RUMUS.socCH})}${kpi("Alert Only", fmt(R.chAlert), "critical/high not stopped", {cls: R.chAlert ? "warnv" : ""})}${kpi("Internal Source", pc(R.internalPct), "of total events", {tip: RUMUS.socInt})}${kpi("URL Blocked", fmt(R.urlBlk), "of " + fmt(R.url) + " URL events")}</div>` : "";
  const nx = hasX ? `${rowLbl("XDR · Trend Micro Vision One")}<div class="kpis k6">${kpi("Alerts", fmt(X.total), "in the period")}${kpi("Still Open", fmt(X.open), "not Closed yet", {cls: X.open ? "warnv" : ""})}${kpi("Critical + High", fmt((sv.critical || 0) + (sv.high || 0)), fmt(sv.critical || 0) + " critical", {cls: sv.critical ? "warnv" : ""})}${kpi("Hosts Affected", fmt(X.nHosts), fmt(X.nAccounts) + " distinct accounts")}${kpi("Incidents", fmt(X.nIncidents), "")}${kpi("Backlog Critical/High", fmt(X.backlogCH), "open now, all periods", {cls: X.backlogCH ? "warnv" : ""})}</div>` : "";
  const XP = hasX ? xdrPanels(X) : null;
  return grid(panel("c12", "Attention", ctxTxt(APPLY.cyber), attList(att))) + insArea("cyber") + nk + nx + grid(
    (R ? panel("c6", "NDR · Critical and High per Day", "Palo Alto events", legend(ch) + bars(B, ch, {stack: true, label: "Critical and high"})) : "") +
    (hasX ? panel("c6", "XDR · Alerts per Day", "by severity", legend(["critical", "high", "medium", "low"].map(k => ({name: XSEV[k][0], c: XSEV[k][1]}))) + bars(X.daily.map(x => ({label: dmon(x.date), full: dlong(x.date)})), ["critical", "high", "medium", "low"].map(k => ({name: XSEV[k][0], c: XSEV[k][1], v: X.daily.map(x => x[k])})), {stack: true, label: "XDR alerts per day"})) : "") +
    (R ? panel("c6", "NDR · Severity and Action", "", tbl(["Severity", "Events", "% of total", "Blocked", "Alert only"], R.sev.concat(R.sevTotal).map(x => [x.k, x.n, pc(x.pct), x.blk, x.alert]), {r: [2]})) : "") +
    (hasX ? XP.sev().replace("panel c4", "panel c6") : "") +
    (R ? panel("c6", "NDR · Top Threat Categories", "", hbars(R.cat.slice(0, 8).map(x => [x.k, x.n, 0, fmt(x.n) + " · " + pc(x.pct, 0)]))) : "") +
    (hasX ? XP.models() : "") + (hasX ? XP.hosts() + XP.techniques() : ""));
}