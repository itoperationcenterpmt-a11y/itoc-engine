/* ISP Live Monitoring (Zabbix hosts starting with 'ISP-'): live status by provider, branch dual-link redundancy matrix, and outage history. */
"use strict";
const zispDur = h => h == null ? "-" : h < 1 ? Math.max(1, Math.round(h * 60)) + " min" : h < 48 ? fx(h, 1) + " h" : fx(h / 24, 1) + " d";
const zispTone = a => a == null ? "" : a >= 0.99 ? "good-t" : a >= 0.95 ? "warn-t" : "crit-t";
const zispPill = s => s === "down" ? pill("crit", "Down") : s === "up" ? pill("good", "Online") : s === "degraded" ? pill("good", "Ping OK") : s === "maintenance" ? pill("idle", "Maintenance") : pill("idle", s || "-");
const zispBar = r => {
  const t = r.total || 1, w = n => (n / t * 100).toFixed(2) + "%";
  return `<div class="stbar" title="${esc(`${r.online} reachable (${r.up} full up, ${r.deg} ping-only) · ${r.down} down · ${r.maint} maintenance`)}"><i class="u" style="width:${w(r.online)}"></i><i class="m" style="width:${w(r.maint)}"></i><i class="d" style="width:${w(r.down)}"></i></div>`;
};

function zbxIspPanels(Z) {
  const A = Z.all, H = Z.hist;
  const provRows = Z.byProvider.map(r => `<div class="strow"><b>${esc(r.k)}</b>${zispBar(r)}<span class="num">${fmt(r.online)} / ${fmt(r.total)} · <span class="${zispTone(r.avail)}">${r.avail != null ? pc(r.avail, 1) : "-"}</span></span></div>`).join("");
  const provChip = l => `<span class="zisp-chip ${l.reachable ? "ok" : "bad"}" title="${esc(l.name + " · " + (l.reachable ? "Reachable" : "DOWN" + (l.ageH != null ? " (" + zispDur(l.ageH) + ")" : "")))}"><i></i>${esc(l.provider)}</span>`;
  const matRows = Z.byLoc.map(r => [
    {h: `<span class="zisp-loc" data-filter-site="${esc(r.k)}" title="Click to filter ${esc(r.k)}">${esc(r.k)}</span>`},
    {h: `<div class="zisp-chips">${r.links.map(provChip).join("")}</div>`},
    r.online + " / " + r.total,
    {h: r.down ? `<b class="crit-t">${r.down}</b>` : "0"},
    {h: pill(r.rtone, r.redundancy)}
  ]);
  return {
    providers: () => panel("c5", "ISP Status by Provider", "Zabbix ISP-* · Updated " + dtime(Z.updated), `<div class="legend"><span><b style="background:var(--good)"></b>Reachable (ICMP OK)</span><span><b style="background:var(--crit)"></b>Down</span><span><b style="background:var(--warn)"></b>Maintenance</span></div>` + (provRows || `<div class="empty sm">No ISP-* hosts synced from Zabbix yet.</div>`)),
    matrix: () => panel("c12", "Branch ISP Redundancy Matrix", fmt(A.locations) + " locations · " + fmt(A.dualSites) + " dual-link" + (A.singleRisk ? " · " + fmt(A.singleRisk) + " single-link risk" : ""), tbl(["Location", "ISP Links", "Reachable", "Down", "Redundancy"], matRows, {tall: true, r: [2, 3], empty: "No ISP-* hosts found."})),
    down: () => panel("c6", "ISP Links Down Now", fmt(Z.downN) + " down", Z.down.length ? vzTop(Z.down.slice(0, 8).map(x => ({title: x.loc + " · " + x.provider, sub: x.name + (x.problem ? " · " + x.problem : ""), value: zispDur(x.ageH), tone: "crit"}))) : `<div class="empty sm">All ${fmt(A.total)} ISP links are currently reachable.</div>`),
    timeline: () => panel("c12", "ISP Outage Timeline (Zabbix)", H && H.events ? fmt(H.events) + " outages · last 7 days" : "last 7 days", H ? vzTimeline(H.timeline || [], H.tlFrom, H.tlTo) : `<div class="empty sm">No outage history.</div>`),
    byProvHist: () => panel("c6", "ISP Outages by Provider", H ? dmon(H.from) + " – " + dmon(H.to) : "", tbl(["Provider", "Incidents", "Downtime (h)", "Period Availability"], (H && H.byProvider || []).map(r => [r.k, r.events, fx(r.hours, 1), r.avail != null ? {h: `<span class="${zispTone(r.avail)}">${pc(r.avail, 2)}</span>`} : "-"]), {r: [1, 2, 3], empty: "No ISP outages in this period."})),
  };
}

function applyZispFilter() {
  const q = (($("zq") || {}).value || "").trim().toLowerCase();
  document.querySelectorAll("#zlist tbody tr").forEach(r => { r.hidden = q && !r.textContent.toLowerCase().includes(q); });
}

function vZbxIsp() {
  const Z = V.zbx_isp, grid = h => `<div class="grid">${h}</div>`;
  if (!Z) return grid(`<section class="panel c12">${empty()}</section>`);
  const A = Z.all, H = Z.hist;
  if (!Z.configured || !A.total) {
    return grid(panel("c12", "ISP Monitor (Zabbix)", "", `<div class="empty"><b>No Zabbix ISP-* hosts yet</b><span>${Z.error ? "Last sync failed: " + esc(Z.error) : "Ensure Zabbix hosts named ISP-<Provider>-<Branch> are inside a synced host group (e.g. NETWORK-*) and run Sync now."}</span></div>`));
  }
  const warns = [];
  if (Z.error) warns.push(`<li class="crit"><span><b>Zabbix sync failed:</b> ${esc(Z.error)}</span></li>`);
  else if (Z.stale) warns.push(`<li class="warn"><span><b>Data not updated</b> since ${esc(dtime(Z.updated))}. Check the Zabbix connector.</span></li>`);
  if (A.siteDown) warns.push(`<li class="crit"><span><b>${pl(A.siteDown, "location")} completely offline</b> — all monitored ISP links are down.</span></li>`);
  if (A.singleRisk) warns.push(`<li class="warn"><span><b>${pl(A.singleRisk, "dual-link branch")} running on single link</b> (no active redundancy).</span></li>`);

  const P = zbxIspPanels(Z);
  const oldest = Z.down.find(x => x.ageH != null);
  const kp = `<div class="kpis k6">${kpi("ISP Links", fmt(A.total), fmt(A.providers) + " providers · " + fmt(A.locations) + " locations")}${kpi("Reachable Now", fmt(A.online), A.avail != null ? pc(A.avail, 2) + " live availability" : "")}${kpi("Down Now", fmt(A.down), oldest ? "oldest " + zispDur(oldest.ageH) : "all reachable", {cls: A.down ? "warnv" : ""})}${kpi("Dual-Link Branches", fmt(A.dualSites), A.singleRisk ? fmt(A.singleRisk) + " single-link risk" : "full redundancy", {cls: A.singleRisk ? "warnv" : ""})}${kpi("Period Outages", fmt(H ? H.events : 0), H ? fmt(H.hosts) + " links affected" : "")}${kpi("Period Availability", H && H.avail != null ? pc(H.avail, 2) : "-", H ? fx(H.hours, 1) + " h down" + (H.mttr != null ? " · MTTR " + fx(H.mttr, 1) + " h" : "") : "")}</div>`;

  const days = (H && H.daily || []).map(x => ({label: dmon(x.date), full: dlong(x.date)}));
  const listRows = (Z.list || []).map(x => [
    x.name,
    {h: `<span class="tag">${esc(x.provider)}</span>`},
    x.loc,
    x.ip,
    {h: zispPill(x.status)},
    x.since ? dtime(x.since) : "-",
    {h: `<span class="${x.ageH != null && x.ageH > 1 ? "crit-t" : ""}">${zispDur(x.ageH)}</span>`},
    x.problem || "-"
  ]);

  return insArea("zbxisp") + (warns.length ? grid(`<section class="panel c12"><ul class="att">${warns.join("")}</ul></section>`) : "") + kp + grid(
    vzGaugeCard("c3", "ISP Live Availability", A.avail, {lo: 0, hi: 1, target: 0.99, label: "ISP Live Availability", fmt: v => pc(v, 2), sub: fmt(A.online) + " / " + fmt(A.total) + " up", note: "Target 99% · Zabbix ICMP"}) +
    panel("c4", "Links by Provider", "", vzDonut(Z.byProvider.map((x, i) => ({k: x.k, v: x.total, c: vzPal[i % vzPal.length]})), {sub: "ISP links", label: "ISP links by provider"})) +
    P.providers() +
    P.down() +
    P.byProvHist() +
    P.matrix() +
    P.timeline() +
    panel("c6", "ISP Outage Incidents per Day", H ? dmon(H.from) + " – " + dmon(H.to) : "", bars(days, [{name: "Outages", c: "--crit", v: (H && H.daily || []).map(x => x.events)}], {label: "ISP outages per day"})) +
    panel("c6", "ISP Downtime per Day", "Hours per day", bars(days, [{name: "Downtime (h)", c: "--warn", v: (H && H.daily || []).map(x => x.hours)}], {dec: 1, unit: " h", label: "ISP downtime per day"})) +
    panel("c6", "Downtime by Location", "top 12", tbl(["Location", "Incidents", "Downtime (h)", "Availability"], (H && H.byLoc || []).map(r => [r.k, r.events, fx(r.hours, 1), r.avail != null ? {h: `<span class="${zispTone(r.avail)}">${pc(r.avail, 2)}</span>`} : "-"]), {r: [1, 2, 3], empty: "No ISP outages in this period."})) +
    panel("c6", "Most Frequently Down ISP Links", "flapping / chronic watchlist", tbl(["ISP Host", "Incidents", "Downtime (h)"], (H && H.byHost || []).map(r => [r.k, r.events, fx(r.hours, 1)]), {r: [1, 2], empty: "No ISP outages in this period."})) +
    panel("c12", "All ISP Hosts (Zabbix)", fmt(Z.listN) + " hosts", `<div class="dtool"><input type="search" id="zq" class="msearch" placeholder="Search host name, provider, location, or IP" aria-label="Search ISP hosts"><span class="sub">Provider and status filters are in the top filter bar</span></div><div id="zlist">${tbl(["Host Name", "Provider", "Location", "IP", "Status", "Down since", "Duration", "Trigger / Note"], listRows, {tall: true, empty: "No ISP hosts for this filter."})}</div>`)
  );
}
