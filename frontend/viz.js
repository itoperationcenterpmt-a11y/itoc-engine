/* Visual widgets: sparkline cards, gauges, donuts, heatmaps, link timeline, location wall, and top-problem cards.
   They sit in the same catalog as the other widgets (Customize -> Add widget -> Visual) and read data the page already loaded.
   Charts are drawn so they scale with the container: SVG with a viewBox, or plain HTML boxes sized in percent. */
"use strict";
const VZC = {good: "var(--good)", warn: "var(--warn)", crit: "var(--crit)", s1: "var(--s1)", s2: "var(--s2)", low: "var(--low)", sev: "var(--serious)"};
const vzNum = a => (a || []).map(v => +v || 0);
const vzSum = a => a.reduce((x, y) => x + y, 0);

/* Last 7 points against the 7 before them, in percent. null when the period is shorter than two weeks. */
function vzDelta(vals) {
  const v = vzNum(vals); if (v.length < 14) return null;
  const a = vzSum(v.slice(-7)), b = vzSum(v.slice(-14, -7));
  return b ? (a - b) / b : (a ? 1 : 0);
}
const vzDeltaHtml = (d, badWhenUp = true) => d == null ? `<span class="vz-d">needs 14 days</span>` : `<span class="vz-d ${Math.abs(d) < 0.03 ? "" : (d > 0) === badWhenUp ? "bad" : "good"}">${d > 0 ? "▲" : d < 0 ? "▼" : "■"} ${Math.abs(Math.round(d * 100))}% <i>7 days vs the 7 before</i></span>`;

function vzSpark(vals, color = VZC.s1) {
  const v = vzNum(vals); if (v.length < 2) return `<div class="vz-spark empty"></div>`;
  const mx = Math.max(...v), mn = Math.min(...v), rng = mx - mn || 1, W = 120, H = 36, P = 3;
  const pts = v.map((y, i) => [P + i * (W - 2 * P) / (v.length - 1), H - P - (y - mn) / rng * (H - 2 * P)]);
  const line = pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
  return `<svg class="vz-spark" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" aria-label="Trend"><path d="${line} L${W - P} ${H} L${P} ${H} Z" fill="${color}" opacity=".14"/><path d="${line}" fill="none" stroke="${color}" stroke-width="2" vector-effect="non-scaling-stroke" stroke-linejoin="round" stroke-linecap="round"/><circle cx="${pts[pts.length - 1][0].toFixed(1)}" cy="${pts[pts.length - 1][1].toFixed(1)}" r="2.6" fill="${color}"/></svg>`;
}
const vzSparkCard = (size, title, value, sub, vals, color, badWhenUp, note) => panel(size, title, "", `<div class="vz-card"><div class="vz-val">${value}</div><div class="vz-sub">${sub}</div>${vzSpark(vals, color)}${note ? `<span class="vz-d">${note}</span>` : vzDeltaHtml(vzDelta(vals), badWhenUp)}</div>`);
const vzPal = [VZC.s1, VZC.s2, VZC.good, VZC.warn, VZC.sev, VZC.low];

/* Half-circle gauge. pct and target are fractions; lo..hi is the scale shown (availability sits near 100%, so a zoomed scale is more useful). */
function vzGauge(pct, o = {}) {
  const lo = o.lo ?? 0, hi = o.hi ?? 1, f = x => Math.max(0, Math.min(1, (x - lo) / (hi - lo)));
  const R = 80, CX = 100, CY = 100, pt = (t, r = R) => [CX - r * Math.cos(Math.PI * t), CY - r * Math.sin(Math.PI * t)];
  const arc = (t0, t1, r = R) => { const a = pt(t0, r), b = pt(t1, r); return `M${a[0].toFixed(2)} ${a[1].toFixed(2)} A${r} ${r} 0 0 1 ${b[0].toFixed(2)} ${b[1].toFixed(2)}`; };
  const t = f(pct), warn = o.target != null ? o.target : hi, tone = pct == null ? VZC.low : pct >= warn ? VZC.good : pct >= warn - (hi - lo) * 0.25 ? VZC.warn : VZC.crit;
  const tk = o.target != null ? (() => { const a = pt(f(o.target), R - 14), b = pt(f(o.target), R + 10); return `<line x1="${a[0]}" y1="${a[1]}" x2="${b[0]}" y2="${b[1]}" stroke="var(--ink)" stroke-width="3" stroke-linecap="round"/>`; })() : "";
  return `<div class="vz-gauge"><svg viewBox="0 0 200 112" role="img" aria-label="${esc(o.label || "Gauge")}"><path d="${arc(0, 1)}" fill="none" stroke="var(--sunken)" stroke-width="16" stroke-linecap="round"/>${pct == null ? "" : `<path d="${arc(0, Math.max(t, 0.012))}" fill="none" stroke="${tone}" stroke-width="16" stroke-linecap="round"/>`}${tk}</svg>
    <div class="vz-gv"><b>${pct == null ? "–" : o.fmt ? o.fmt(pct) : pc(pct, 1)}</b>${o.sub ? `<span>${o.sub}</span>` : ""}</div></div>`;
}
const vzGaugeCard = (size, title, pct, o) => panel(size, title, "", vzGauge(pct, o) + (o.note ? `<div class="vz-note">${o.note}</div>` : ""));

/* Donut with a legend. parts: [{k, v, c}] */
function vzDonut(parts, o = {}) {
  const tot = vzSum(parts.map(p => p.v)); if (!tot) return `<div class="empty sm">No data.</div>`;
  let off = 0; const C = 2 * Math.PI * 15.9155;
  const seg = parts.filter(p => p.v > 0).map(p => { const len = p.v / tot * C, s = `<circle r="15.9155" cx="21" cy="21" fill="none" stroke="${p.c}" stroke-width="6" stroke-dasharray="${len.toFixed(2)} ${(C - len).toFixed(2)}" stroke-dashoffset="${(-off).toFixed(2)}" transform="rotate(-90 21 21)"><title>${esc(p.k)}: ${fmt(p.v)}</title></circle>`; off += len; return s; }).join("");
  return `<div class="vz-donut"><div class="vz-dwrap"><svg viewBox="0 0 42 42" role="img" aria-label="${esc(o.label || "Distribution")}"><circle r="15.9155" cx="21" cy="21" fill="none" stroke="var(--sunken)" stroke-width="6"/>${seg}</svg><div class="vz-gv"><b>${o.center != null ? o.center : fmt(tot)}</b>${o.sub ? `<span>${o.sub}</span>` : ""}</div></div>
    <ul class="vz-leg">${parts.map(p => `<li><i style="background:${p.c}"></i><span>${esc(p.k)}</span><b>${fmt(p.v)}</b></li>`).join("")}</ul></div>`;
}

/* Weekday x hour heatmap drawn with a CSS grid (cells shrink with the container, labels stay readable). grid: 7 rows (Mon..Sun) x 24 columns. */
function vzHeat(grid, o = {}) {
  const mx = Math.max(...grid.flat(), 0); if (!mx) return `<div class="empty sm">No data in this period.</div>`;
  const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], col = o.color || "var(--s1)";
  const head = `<span></span>` + [...Array(24).keys()].map(h => `<span class="vz-hl ${h % 3 ? "x" : ""}">${h % 3 ? "" : pad(h)}</span>`).join("");
  const rows = grid.map((r, d) => `<span class="vz-hd">${days[d]}</span>` + r.map((v, h) => `<i class="vz-c" style="--a:${(v / mx).toFixed(3)};--c:${col}" title="${days[d]} ${pad(h)}.00 · ${o.unit ? fx(v, 0) + " " + o.unit : fmt(v)}"></i>`).join("")).join("");
  return `<div class="vz-heat">${head}${rows}</div><div class="vz-note">Darker = more. Busiest: ${days[grid.findIndex(r => r.includes(mx))]} ${pad(grid[grid.findIndex(r => r.includes(mx))].indexOf(mx))}.00 (${o.unit ? fx(mx, 0) + " " + o.unit : fmt(mx)}).</div>`;
}

/* Outages as bars on a shared 7-day time axis; positions are percentages so the chart is fluid. rows: [{name, minutes, events: [[startMs, endMs]]}] */
function vzTimeline(rows, from, to) {
  if (!rows.length) return `<div class="empty sm">No outages in the last 7 days.</div>`;
  const span = to - from, ticks = [...Array(8).keys()].map(i => from + span * i / 7);
  return `<div class="vz-tl"><div class="vz-tlh"><span></span><div>${ticks.map((t, i) => `<em style="left:${i / 7 * 100}%">${dmon(iso(t))}</em>`).join("")}</div></div>` +
    rows.map(r => `<div class="vz-tlr"><span title="${esc(r.name)}">${esc(r.name)}</span><div class="vz-tla">${r.events.map(([s, e]) => `<i style="left:${((s - from) / span * 100).toFixed(2)}%;width:${Math.max(0.5, (e - s) / span * 100).toFixed(2)}%" title="${dtime(s)} – ${dtime(e)} · ${fx((e - s) / 60000, 0)} min"></i>`).join("")}</div><b>${fmt(r.minutes)} min</b></div>`).join("") + `</div>`;
}

/* One tile per location, coloured by health score (0-100). */
function vzWall(items) {
  if (!items.length) return `<div class="empty sm">No location data yet.</div>`;
  return `<div class="vz-wall">${items.map(x => { const tone = x.score >= 80 ? "good" : x.score >= 60 ? "warn" : "crit";
    return `<div class="vz-tile ${tone}" title="Link ${x.link == null ? "–" : pc(x.link, 2)} · devices down ${x.devDown} · tickets past SLA ${x.overdue}"><b>${esc(x.site)}</b><span class="vz-score">${x.score}</span><small>${x.devTotal ? x.devDown + "/" + x.devTotal + " down" : "–"}${x.overdue ? " · " + x.overdue + " late" : ""}</small></div>`; }).join("")}</div>`;
}

/* Cards for the top problems (replaces a long ranking table). items: [{title, sub, value, tone}] */
const vzTop = items => items.length ? `<div class="vz-top">${items.map((x, i) => `<div class="vz-topc ${x.tone || ""}"><span class="vz-rank">${i + 1}</span><div><b>${esc(x.title)}</b><small>${esc(x.sub)}</small></div><em>${x.value}</em></div>`).join("")}</div>` : `<div class="empty sm">Nothing to show.</div>`;

const vzReady = key => w => !!V[w.need] && (key ? !!V[w.need][key] : true);
const VIZ_WIDGETS = [
  {key: "viz-spark-tickets", grp: "Visual", mod: "servicedesk", need: "tk", title: "Tickets · trend", desc: "Tickets received with a sparkline and 7-day change", size: "c3",
    html: () => vzSparkCard("c3", "Tickets · trend", fmt(V.tk.n), fx(V.tk.perDay, 1) + " per day · " + fmt(V.tk.open) + " open", V.tk.daily.map(x => x.in), VZC.s1, false)},
  {key: "viz-spark-downtime", grp: "Visual", mod: "noc", need: "net", title: "Link downtime · trend", desc: "Total link downtime with a sparkline and 7-day change", size: "c3",
    html: () => vzSparkCard("c3", "Link downtime · trend", fx(V.net.downH, 1) + " h", fmt(V.net.events) + " incidents", (V.net.daily || []).map(x => x.down), VZC.crit, true)},
  {key: "viz-spark-ndr", grp: "Visual", mod: "soc", need: "soc", title: "NDR critical + high · trend", desc: "Critical and high threat events per day", size: "c3",
    html: () => vzSparkCard("c3", "NDR critical + high · trend", fmt(V.soc.ch), fmt(V.soc.crit) + " critical", (V.soc.daily || []).map(x => (x.critical || 0) + (x.high || 0)), VZC.sev, true)},
  {key: "viz-spark-xdr", grp: "Visual", mod: "xdr", need: "xdr", title: "XDR alerts · trend", desc: "XDR alerts per day", size: "c3",
    html: () => vzSparkCard("c3", "XDR alerts · trend", fmt(V.xdr.total), fmt(V.xdr.open) + " still open", (V.xdr.daily || []).map(x => ["critical", "high", "medium", "low"].reduce((a, k) => a + (x[k] || 0), 0)), VZC.s2, true)},
  {key: "viz-gauge-sla", grp: "Visual", mod: "servicedesk", need: "tk", title: "Ticket SLA gauge", desc: "Tickets within SLA target against the warning level", size: "c3",
    html: () => { const w = +CFG.params["sd.sla_warn"] || 0.9; return vzGaugeCard("c3", "Ticket SLA", V.tk.slaPct, {lo: 0.5, hi: 1, target: w, label: "Ticket SLA", sub: "within target", note: "Marker = warning level " + pc(w, 0)}); }},
  {key: "viz-gauge-link", grp: "Visual", mod: "noc", need: "net", title: "Link availability gauge", desc: "Average link availability against the SLA target", size: "c3",
    html: () => vzGaugeCard("c3", "Link availability", V.net.avail, {lo: 0.97, hi: 1, target: V.net.P.target, label: "Link availability", fmt: v => pc(v, 2), sub: "average", note: "Marker = target " + pc(V.net.P.target, 1)})},
  {key: "viz-gauge-devices", grp: "Visual", mod: "devices", need: "dev", title: "Device availability gauge", desc: "Online devices out of online + down", size: "c3",
    html: () => vzGaugeCard("c3", "Device availability", V.dev.all.avail, {lo: 0.7, hi: 1, target: 0.95, label: "Device availability", sub: fmt(V.dev.all.down) + " down", note: "Marker = 95%"})},
  {key: "viz-gauge-ms-servers", grp: "Visual", mod: "cctv", need: "cctv", title: "Milestone servers gauge", desc: "Milestone servers that synced without error", size: "c3",
    html: () => vzGaugeCard("c3", "Milestone servers", V.cctv.srv.total ? V.cctv.srv.ok / V.cctv.srv.total : null, {lo: 0, hi: 1, target: 1, label: "Servers syncing", sub: fmt(V.cctv.srv.ok) + " of " + fmt(V.cctv.srv.total) + (V.cctv.srv.failed.length ? " · " + V.cctv.srv.failed.join(", ") : ""), note: "Marker = all servers"})},
  {key: "viz-gauge-cameras", grp: "Visual", mod: "cctv", need: "cctv", title: "Cameras online gauge", desc: "Cameras online out of online + offline (Zabbix status)", size: "c3",
    html: () => { const z = V.cctv.zbx, on = z.up + z.other; return vzGaugeCard("c3", "Cameras online", on + z.down ? on / (on + z.down) : null, {lo: 0.5, hi: 1, target: 0.95, label: "Cameras online", sub: fmt(on) + " online · " + fmt(z.down) + " offline", note: "Marker = 95%"}); }},
  {key: "viz-gauge-recording", grp: "Visual", mod: "cctv", need: "cctv", title: "Milestone recording gauge", desc: "Cameras recording centrally out of enabled cameras", size: "c3",
    html: () => vzGaugeCard("c3", "Milestone recording", V.cctv.camEnabled ? V.cctv.recording / V.cctv.camEnabled : null, {lo: 0, hi: 1, label: "Recording centrally", sub: fmt(V.cctv.recording) + " of " + fmt(V.cctv.camEnabled), note: "Interconnect cameras record on their own site"})},
  {key: "viz-donut-devices", grp: "Visual", mod: "devices", need: "dev", title: "Device status mix", desc: "Online, down, interface issue, maintenance, disabled", size: "c4",
    html: () => { const A = V.dev.all; return panel("c4", "Device status mix", "", vzDonut([{k: "Online", v: A.up, c: VZC.good}, {k: "Down", v: A.down, c: VZC.crit}, {k: "Interface issue", v: A.deg || 0, c: VZC.warn}, {k: "Maintenance", v: A.maint || 0, c: VZC.s1}, {k: "Disabled", v: A.off || 0, c: VZC.low}], {center: A.avail != null ? pc(A.avail, 0) : "–", sub: "online", label: "Device status"})); }},
  {key: "viz-donut-cameras", grp: "Visual", mod: "cctv", need: "cctv", title: "Camera status (Zabbix)", desc: "Cameras online, offline, or not in Zabbix", size: "c4",
    html: () => { const z = V.cctv.zbx; return panel("c4", "Camera status (Zabbix)", "", vzDonut([{k: "Online", v: z.up + z.other, c: VZC.good}, {k: "Offline", v: z.down, c: VZC.crit}, {k: "No status", v: z.none, c: VZC.low}], {sub: "cameras", label: "Camera status"})); }},
  {key: "viz-donut-xdr", grp: "Visual", mod: "xdr", need: "xdr", title: "XDR alerts by severity", desc: "Share of XDR alerts per severity", size: "c4",
    html: () => panel("c4", "XDR alerts by severity", "", vzDonut((V.xdr.bySev || []).map(x => ({k: (XSEV[x.k] || [x.k])[0], v: x.n, c: {critical: VZC.crit, high: VZC.sev, medium: VZC.warn, low: VZC.low}[x.k] || VZC.low})), {sub: "alerts", label: "XDR severity"}))},
  {key: "viz-donut-tickets", grp: "Visual", mod: "servicedesk", need: "tk", title: "Ticket status", desc: "Closed against still open", size: "c4",
    html: () => panel("c4", "Ticket status", "", vzDonut([{k: "Closed", v: V.tk.n - V.tk.open, c: VZC.good}, {k: "Still open", v: V.tk.open, c: VZC.warn}], {center: pc(V.tk.doneRate, 0), sub: "closed", label: "Ticket status"}))},
  {key: "viz-gauge-ap", grp: "Visual", mod: "wifi", need: "wifi", title: "Access Points online gauge", desc: "Access Points online out of all", size: "c3",
    html: () => vzGaugeCard("c3", "Access Points online", V.wifi.apTotal ? V.wifi.apOnline / V.wifi.apTotal : null, {lo: 0.8, hi: 1, target: 0.95, label: "Access Points online", sub: fmt(V.wifi.apTotal - V.wifi.apOnline) + " offline", note: "Marker = 95%"})},
  {key: "viz-donut-band", grp: "Visual", mod: "wifi", need: "wifi", title: "WiFi clients by band", desc: "Share of active clients per radio band", size: "c4",
    html: () => panel("c4", "WiFi clients by band", "", vzDonut((V.wifi.byBand || []).map((x, i) => ({k: x.k, v: x.n, c: vzPal[i % vzPal.length]})), {sub: "clients", label: "Clients by band"}))},
  {key: "viz-spark-wifi", grp: "Visual", mod: "wifi", need: "wifi", title: "WiFi clients · 24 hours", desc: "Active clients over the last 24 hours", size: "c3",
    html: () => vzSparkCard("c3", "WiFi clients · 24 hours", fmt(V.wifi.total), fmt(V.wifi.apOnline) + " Access Points online", (V.wifi.trend || []).map(x => x.c), VZC.good, false, "hourly, last 24 hours")},
  {key: "viz-donut-ndr-action", grp: "Visual", mod: "soc", need: "soc", title: "NDR events by firewall action", desc: "Share of threat events per firewall action", size: "c4",
    html: () => panel("c4", "NDR events by firewall action", ctxTxt(APPLY.soc), vzDonut((V.soc.action || []).slice(0, 6).map((x, i) => ({k: x.k, v: x.n, c: vzPal[i % vzPal.length]})), {sub: "events", label: "Firewall action"}))},
  {key: "viz-donut-kinds", grp: "Visual", mod: "devices", need: "dev", title: "Devices by category", desc: "Share of monitored devices per Zabbix category", size: "c4",
    html: () => panel("c4", "Devices by category", "", vzDonut((V.dev.byKind || []).map((x, i) => ({k: x.k, v: x.total, c: vzPal[i % vzPal.length]})), {sub: "devices", label: "Devices by category"}))},
  {key: "viz-licence", grp: "Visual", mod: "cctv", need: "cctv", title: "Milestone licences", desc: "Licences in use per Milestone server (set the total in Integrations)", size: "c4",
    html: () => { const rows = (V.cctv.servers || []).filter(s => s.licTotal != null); return panel("c4", "Milestone licences", "", rows.length ? `<div class="vz-meters">${rows.map(s => { const p = s.licTotal ? s.licUsed / s.licTotal : 0, tone = p > 1 ? "crit" : p >= 0.9 ? "warn" : "good"; return `<div class="vz-m"><span>${esc(s.name)}</span><div class="vz-mb"><i class="${tone}" style="width:${Math.min(100, p * 100).toFixed(1)}%"></i></div><b>${fmt(s.licUsed)}/${fmt(s.licTotal)}</b></div>`; }).join("")}</div>` : `<div class="empty sm">No licence totals set. Add them per server in Admin → Integrations → Milestone.</div>`); }},
  {key: "viz-heat-tickets", grp: "Visual", mod: "servicedesk", need: "viz", title: "Ticket load · weekday × hour", desc: "When tickets arrive (heatmap)", size: "c8",
    html: () => panel("c8", "Ticket load · weekday × hour", ctxTxt(), vzHeat(V.viz.tkHeat, {color: "var(--s1)"}))},
  {key: "viz-heat-down", grp: "Visual", mod: "noc", need: "viz", title: "Link downtime · weekday × hour", desc: "When links are down (heatmap, minutes)", size: "c8",
    html: () => panel("c8", "Link downtime · weekday × hour", ctxTxt(), vzHeat(V.viz.downHeat, {color: "var(--crit)", unit: "min"}))},
  {key: "viz-timeline", grp: "Visual", mod: "noc", need: "viz", title: "Link outages · last 7 days", desc: "Outage timeline for the ten links with the most downtime", size: "c12",
    html: () => panel("c12", "Link outages · last 7 days", "top 10 by downtime", vzTimeline(V.viz.linkEvents, V.viz.from, V.viz.to))},
  {key: "viz-wall", grp: "Visual", mod: "servicedesk", need: "viz", title: "Location health wall", desc: "One tile per location, coloured by health score", size: "c12",
    html: () => panel("c12", "Location health wall", "score 0 to 100 · lowest first", vzWall(V.viz.wall))},
  {key: "viz-top-links", grp: "Visual", mod: "noc", need: "net", title: "Top problem links (cards)", desc: "The five links with the most downtime", size: "c6",
    html: () => panel("c6", "Top problem links", ctxTxt(), vzTop((V.net.rank || []).slice(0, 5).map(x => ({title: x.link, sub: pc(x.av, 2) + " availability · " + x.status, value: fx(x.downMin, 0) + " min", tone: x.av < V.net.P.target ? "crit" : "warn"}))))},
  {key: "viz-top-devices", grp: "Visual", mod: "devices", need: "dev", title: "Longest-down devices (cards)", desc: "The five devices down the longest", size: "c6",
    html: () => panel("c6", "Longest-down devices", "", vzTop((V.dev.down || []).slice(0, 5).map(x => ({title: x.name, sub: x.loc + (x.problem ? " · " + x.problem : ""), value: durTxt(x.ageH), tone: x.ageH != null && x.ageH > 24 ? "crit" : "warn"}))))},
];
WIDGETS.push(...VIZ_WIDGETS);
