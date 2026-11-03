/* Internet Usage (Network menu): traffic, applications, web categories, and top users per location, from the Palo Alto firewalls (Panorama). Period and location follow the top filter bar. */
"use strict";
function vInternet() {
  const F = V.inet, grid = h => `<div class="grid">${h}</div>`;
  if (!F) return grid(`<section class="panel c12">${empty()}</section>`);
  if (!F.nFw || !F.total.bytes) return grid(`<section class="panel c12">${empty("No Palo Alto traffic data for this period" + (S.site ? " and location" : "") + " yet. It is collected on every Panorama sync.")}</section>` + socProgress(F));
  const T = F.total, B = F.days.map(x => ({label: dmon(x.date), full: dlong(x.date)})), busy = F.days.reduce((m, x) => x.bytes > m.bytes ? x : m, F.days[0]);
  const avg = F.dayN ? T.bytes * 8 / (F.dayN * 86400) / 1e6 : null;
  const hb = (rows, f = fmt) => rows.length ? hbars(rows.map(x => [x.k, x.n, 0, f(x.n)])) : `<div class="empty sm">No data for this period yet. It is filled in on every Panorama sync.</div>`;
  const sites = F.bySite.filter(s => s.bytes).sort((a, b) => b.bytes - a.bytes);
  const P = V.inet_prev, pAvg = P && P.dayN ? P.total.bytes * 8 / (P.dayN * 86400) / 1e6 : null, cmp = (c, p) => P && p && P.dayN >= F.dayN * 0.9 ? delta(c, p) : "";                  // no change is shown while the previous period has fewer days of data
  const kp = `<div class="kpis k6">${kpi("Total Traffic", fwB(T.bytes), fmt(F.nFw) + " firewall" + (F.nFw > 1 ? "s" : ""), {dl: cmp(T.bytes, P && P.total.bytes)})}${kpi("Average Bandwidth", avg == null ? "–" : fx(avg, 1) + " Mb/s", "over the days with data", {dl: cmp(avg, pAvg)})}${kpi("Busiest Day", fwB(busy.bytes), dmon(busy.date))}${kpi("Sessions", fmt(T.sessions), "", {dl: cmp(T.sessions, P && P.total.sessions)})}${kpi("Web Requests", F.webTotal ? fmt(F.webTotal) : "–", F.webTotal ? "all web categories" : "not collected yet", {dl: cmp(F.webTotal, P && P.webTotal)})}${kpi("Top Application", F.app[0] ? esc(F.app[0].k) : "–", F.app[0] ? fwB(F.app[0].n) : "")}</div>`;
  return (F.detailFrom && F.detailFrom > S.from ? `<p class="sub msnote">Application categories and web data are collected since ${dfull(F.detailFrom)}; earlier days of this period are not included in them.</p>` : "") + kp + grid(
    panel("c8", "Traffic per Day", S.site || "all locations", bars(B, [{name: "Traffic", c: "--s1", v: F.days.map(x => x.bytes / 1e9)}], {dec: 1, unit: " GB", label: "Traffic per day"})) +
    (S.site ? panel("c4", "Sessions per Day", "", bars(B, [{name: "Sessions", c: "--s2", v: F.days.map(x => x.sessions)}], {label: "Sessions per day"})) : panel("c4", "Traffic per Location", "", sites.length ? hbars(sites.slice(0, 10).map(s => [s.site, s.bytes, 0, fwB(s.bytes)])) : `<div class="empty sm">No data.</div>`)) +
    panel("c6", "Top Applications", "by volume", hb(F.app, fwB)) +
    panel("c6", "Traffic by Application Category", "", hb(F.acat, fwB)) +
    panel("c6", "Top Source Networks by Traffic", "internal, per /24 network", hb(F.src, fwB)) +
    panel("c6", "Top Source Networks by Web Requests", "internal, per /24 network", hb(F.webu)) +
    panel("c12", "Web Categories", "requests the URL filtering profile logs (alert or block)", hb(F.urlc)) +
    socProgress(F) +
    (S.site ? "" : panel("c12", "Traffic per Location", "firewalls matched to each location", tbl(["Location", "Traffic", "Share", "Firewalls"], sites.map(s => [s.site, {h: `<span class="nw">${fwB(s.bytes)}</span>`}, pc(s.bytes / T.bytes, 1), s.fw]), {r: [1, 2, 3]}))));
}
