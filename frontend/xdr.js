/* XDR menu (Trend Micro Vision One): Workbench alerts stored in the dashboard database. Severity is chosen in the top filter; the period through Period. */
"use strict";
const XSEV = {critical: ["Critical", "--crit"], high: ["High", "--serious"], medium: ["Medium", "--warn"], low: ["Low", "--low"]};
const XTONE = s => s === "critical" ? "crit" : s === "high" ? "warn" : "idle";
const xLink = u => /^https:\/\//i.test(u || "") ? `<a href="${esc(u)}" target="_blank" rel="noopener noreferrer">Open</a>` : "-";
const xTk = (t, ids) => (t && t.length ? t.map(x => `<span class="tag" title="${esc((x.subject || "") + " · " + (x.status || ""))}">${esc(x.id)}</span>`).join(" ") : ids && ids.length ? ids.map(i => `<span class="tag">${esc(i)}</span>`).join(" ") : `<span class="sub">none</span>`);
const xSev = s => s ? pill(XTONE(s), (XSEV[s] || [s])[0]) : "-";
function xdrPanels(X) {
  const sv = Object.fromEntries(X.bySev.map(x => [x.k, x.n])), days = X.daily.map(x => ({label: dmon(x.date), full: dlong(x.date)})), SV = ["critical", "high", "medium", "low"];
  const hb = a => hbars(a.map(x => [x.k, x.n, 0, fmt(x.n)]));
  const ent = (rows, nm) => tbl([nm, "IP", "Alerts", "Open", "Highest", "Last", "Tickets"], rows.map(x => [x.k, (x.ips || []).join(", ") || "-", x.n, x.open, {h: xSev(x.sev)}, x.last ? dtime(x.last) : "-", {h: xTk(null, x.tk)}]), {r: [2, 3], empty: "No affected entities in this period."});
  return {
    kpi: () => `<section class="panel c4 dom"><header><h2>XDR</h2></header><div class="mini">${kpi("Alerts", fmt(X.total), "in the period")}${kpi("Still Open", fmt(X.open), "", {cls: X.open ? "warnv" : ""})}${kpi("Hosts Affected", fmt(X.nHosts), fmt(X.nIncidents) + " incidents")}${kpi("Backlog C/H", fmt(X.backlogCH), "open now", {cls: X.backlogCH ? "warnv" : ""})}</div>${go("xdr")}</section>`,
    daily: () => panel("c8", "Alerts per Day", "by severity", legend(SV.map(k => ({name: XSEV[k][0], c: XSEV[k][1]}))) + bars(days, SV.map(k => ({name: XSEV[k][0], c: XSEV[k][1], v: X.daily.map(x => x[k])})), {stack: true, label: "XDR alerts per day"})),
    sev: () => panel("c4", "Severity and Status", "", `<span class="lbl">Severity</span>` + hbars(X.bySev.map(x => [XSEV[x.k][0], x.n, 0, fmt(x.n)])) + `<span class="lbl">Investigation status</span>` + hb(X.byStatus)),
    models: () => panel("c6", "Top Detection Models", "top 10", hb(X.byModel)),
    impact: () => panel("c6", "Impact Scope", "", `<div class="mini">${kpi("Desktop", fmt(X.impact.desktop), "")}${kpi("Server", fmt(X.impact.server), "")}${kpi("Accounts", fmt(X.impact.account), "")}${kpi("Email", fmt(X.impact.email), "")}</div><span class="lbl">Investigation result</span>` + hb(X.byResult)),
    hosts: () => panel("c6", "Hosts Affected", fmt(X.nHosts) + " distinct hosts · by highest severity", ent(X.hosts, "Host")),
    accounts: () => panel("c6", "Accounts Affected", fmt(X.nAccounts) + " distinct accounts", ent(X.accounts, "Account")),
    techniques: () => panel("c6", "MITRE ATT&CK Techniques", "", tbl(["ID", "Technique", "Alerts"], X.techniques.map(t => [t.id, t.name || "-", t.n]), {r: [2], empty: "No MITRE techniques in this period's alerts."})),
    incidents: () => panel("c8", "Incidents", fmt(X.nIncidents) + " incidents · by highest severity", tbl(["Incident", "Alerts", "Open", "Severity", "Model", "Range"], X.incidents.map(x => [x.id, x.n, x.open, {h: xSev(x.sev)}, x.models.join("; "), dtime(x.first) + (x.last !== x.first ? " – " + dtime(x.last) : "")]), {r: [1, 2], empty: "No incidents yet."})),
    cover: () => panel("c6", "Ticket Coverage", "open critical and high alerts, matched by host name in the ticket subject", X.ticketed + X.noTicket ? hbars([["With ticket", X.ticketed, 0, fmt(X.ticketed)], ["Without ticket", X.noTicket, 0, fmt(X.noTicket)]]) : `<div class="empty sm">No open critical or high alerts.</div>`),
    aging: () => panel("c4", "Backlog Age", fmt(X.backlog) + " alerts still open (all periods)", hb(X.aging))
  };
}
function vXdr() {
  const X = V.xdr, grid = h => `<div class="grid">${h}</div>`;
  if (!X) return grid(`<section class="panel c12">${empty()}</section>`);
  if (!X.configured || !(X.listN || X.enabled)) return grid(panel("c12", "XDR", "", `<div class="empty"><b>No XDR data yet</b><span>${X.error ? "Last sync failed: " + esc(X.error) : "Enter the regional Base URL and Vision One API key in Admin → Integrations → Trend Micro XDR, enable it, then click Sync now."}</span></div>`));
  const warns = [];
  if (X.error) warns.push(`<li class="crit"><span><b>Trend Micro sync failed:</b> ${esc(X.error)}</span></li>`);
  else if (X.stale) warns.push(`<li class="warn"><span><b>Data not updated</b> since ${esc(dtime(X.updated))}. Check the Trend Micro XDR connector.</span></li>`);
  if (X.backlogCH) warns.push(`<li class="warn"><span><b>${fmt(X.backlogCH)} critical/high alerts still open</b> (all periods).</span></li>`);
  const sv = Object.fromEntries(X.bySev.map(x => [x.k, x.n]));
  const kp = `<div class="kpis k6">${kpi("Alerts", fmt(X.total), "in the period")}${kpi("Still Open", fmt(X.open), "", {cls: X.open ? "warnv" : ""})}${kpi("Critical + High", fmt((sv.critical || 0) + (sv.high || 0)), fmt(sv.critical || 0) + " critical", {cls: sv.critical ? "warnv" : ""})}${kpi("Average Score", X.avgScore != null ? fx(X.avgScore, 1) : "-", "0 to 100")}${kpi("Hosts Affected", fmt(X.nHosts), fmt(X.nAccounts) + " distinct accounts")}${kpi("Incidents", fmt(X.nIncidents), "")}</div>`;
  const P = xdrPanels(X);
  const rows = X.list.map(x => [x.created ? dtime(x.created) : "-", {h: xSev(x.severity)}, {h: `<b>${esc(x.model || "-")}</b>${x.description ? `<span class="sub">${esc(x.description)}</span>` : ""}${(x.techniques || []).length ? `<span class="sub">${esc(x.techniques.join(", "))}</span>` : ""}`}, (x.entities || []).map(e => e.n).filter(Boolean).join(", ") || "-", {h: xTk(x.tickets)}, x.score == null ? "-" : x.score, {h: `${esc(x.status || "-")}${x.result ? `<span class="sub">${esc(x.result)}</span>` : ""}`}, x.incident || "-", {h: xLink(x.link)}]);
  return insArea("xdr") + (warns.length ? grid(`<section class="panel c12"><ul class="att">${warns.join("")}</ul></section>`) : "") + kp + grid(
    P.daily() + P.sev() + P.hosts() + P.accounts() + P.techniques() + P.models() + P.incidents() + P.aging() + P.impact() + P.cover() +
    panel("c12", "Alert List", X.listN + " alerts" + (X.listN > X.list.length ? ", showing " + X.list.length : ""), `<div class="dtool"><input type="search" id="dq" class="msearch" placeholder="Search model, host, account, technique, ticket, or incident" aria-label="Search alerts"><span class="sub">Severity and period are set in the top filter bar</span></div><div id="dlist">${tbl(["Created", "Severity", "Alert", "Host / Account", "Tickets", "Score", "Status", "Incident", "Workbench"], rows, {tall: true, empty: "No alerts for this filter."})}</div>`));
}