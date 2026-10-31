/* Uptime Kuma (Network menu): status now, and availability and response time of the watched services over the period. Period and location follow the top filter bar. */
"use strict";
const KUMA_TONE = {0: "crit", 1: "good", 2: "warn", 3: "idle"};
function vKuma() {
  const K = V.kuma, grid = h => `<div class="grid">${h}</div>`;
  if (!K) return grid(`<section class="panel c12">${empty()}</section>`);
  if (!K.enabled) return grid(`<section class="panel c12">${empty("Uptime Kuma is not connected yet. Enter the Base URL and the API key in Admin → Data Sources → Integrations, then switch the source on.")}</section>`);
  if (!K.total) return grid(`<section class="panel c12">${empty("No monitors" + (S.site ? " for " + S.site : "") + " yet. They appear after the first sync." + (K.error ? " The last sync failed: " + K.error : ""))}</section>`);
  const B = K.daily.map(x => ({label: dmon(x.date), full: dlong(x.date)})), slow = K.mons.filter(m => m.avgMs).sort((a, b) => b.avgMs - a.avgMs).slice(0, 10);
  const warnA = K.avail != null && K.avail < PAR.target ? "warnv" : "";
  const kp = `<div class="kpis k6">${kpi("Monitors", fmt(K.total), fmt(K.up) + " up")}${kpi("Down Now", fmt(K.down), fmt(K.pending) + " pending · " + fmt(K.maint) + " in maintenance", {cls: K.down ? "warnv" : ""})}${kpi("Availability", K.avail != null ? pc(K.avail, 2) : "–", "target " + pc(PAR.target, 1), {cls: warnA})}${kpi("Average Response", K.avgMs != null ? fx(K.avgMs, 0) + " ms" : "–", "monitors with a response time")}${kpi("Certificates Expiring", fmt(K.certSoon), "within " + K.certWarn + " days", {cls: K.certSoon ? "warnv" : ""})}</div>`;
  const note = (K.stale ? `<p class="sub msnote">The last sync was more than 20 minutes ago. Check the connector status in Admin.</p>` : "") + (K.since && K.since.slice(0, 10) > S.from ? `<p class="sub msnote">Availability is recorded since ${dfull(K.since.slice(0, 10))}; earlier days of this period have no samples.</p>` : "");
  const rows = K.mons.map(m => [m.name, m.type, m.target, m.loc, {h: pill(KUMA_TONE[m.status] || "idle", m.label)}, m.avail != null ? pc(m.avail, 2) : "–", fx(m.downH, 1), m.avgMs != null ? fx(m.avgMs, 0) : "–", m.maxMs != null ? fx(m.maxMs, 0) : "–", m.cert != null ? m.cert : "–"]);
  const loc = K.byLoc.map(r => [r.k, r.n, r.down, r.avail != null ? pc(r.avail, 2) : "–", r.avgMs != null ? fx(r.avgMs, 0) : "–"]);
  return note + kp + grid(
    panel("c8", "Availability per Day", S.site || "all locations", lines(B, [{name: "Availability (%)", c: "--s1", v: K.daily.map(x => x.avail == null ? null : x.avail * 100)}], {dec: 2, unit: "%", label: "Availability per day"})) +
    panel("c4", "Status", "now", hbars([["Up", K.up, 0, fmt(K.up)], ["Down", K.down, 0, fmt(K.down)], ["Pending", K.pending, 0, fmt(K.pending)], ["Maintenance", K.maint, 0, fmt(K.maint)]])) +
    panel("c12", "Monitors", fmt(K.mons.length) + " monitors", tbl(["Monitor", "Type", "Target", "Location", "Status", "Availability", "Downtime (h)", "Average (ms)", "Max (ms)", "Cert (days)"], rows, {r: [5, 6, 7, 8, 9], tall: true})) +
    (S.site ? "" : panel("c6", "Per Location", "", tbl(["Location", "Monitors", "Down now", "Availability", "Average (ms)"], loc, {r: [1, 2, 3, 4], empty: "No monitors yet."}))) +
    panel(S.site ? "c12" : "c6", "Slowest Monitors", "average response (ms)", hbars(slow.map(m => [m.name, m.avgMs, 0, fx(m.avgMs, 0)]))) +
    (K.unmapped.length ? panel("c12", "Monitors Without a Location", fmt(K.unmapped.length), `<p class="sub">Add the location name or its code as a site alias (Admin → Data Sources → Mapping) so these appear under their location:</p><p>${K.unmapped.slice(0, 40).map(esc).join(", ")}</p>`) : ""));
}
