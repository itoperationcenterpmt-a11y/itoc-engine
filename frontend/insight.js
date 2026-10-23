/* Insights (under Report): automatic findings, rankings, location health, shift summary, and history. Calculated from stored data, no AI. */
"use strict";
const INS_SEV = {crit: ["crit", "Critical"], warn: ["warn", "Warning"], info: ["idle", "Info"]};
const INS_KIND = {tickets: "Tickets", links: "Links", capacity: "Capacity", security: "Security", devices: "Devices", wifi: "WiFi", correlation: "Cross-source", data: "Data quality"};
const INS_M = {value: "Value", normal: "Normal", z: "z-score", count: "Count", links: "Links", longest_downtime_min: "Longest downtime (min)", window_days: "Window (days)", days_to_target: "Days to target", days_to_90pct: "Days to 90%",
  oldest_days: "Oldest (days)", alerts_7_days: "Alerts (7 days)", events_7_days: "Events (7 days)", offline: "Offline", total: "Total", now: "Now", slope_per_day: "Slope per day", target: "Target", devices: "Devices", signals: "Signals",
  peak_pct: "Peak (%)", capacity_mbps: "Capacity (Mbps)", already_past_sla: "Already past SLA", last_7_days: "Last 7 days", previous_7_days: "Previous 7 days", missing_days: "Missing days", readings: "Readings", expected: "Expected",
  sources: "Sources", codes: "Codes", empty: "Empty", weekly_median_hours: "Weekly median (h)", weekly_sla: "Weekly SLA"};
const insVal = v => Array.isArray(v) ? v.join(" → ") : typeof v === "number" ? (Number.isInteger(v) ? fmt(v) : fx(v, Math.abs(v) < 1 ? 4 : 1)) : v;
const insMetric = m => Object.entries(m || {}).map(([k, v]) => `<span class="mchip"><i>${esc(INS_M[k] || k.replace(/_/g, " "))}</i>${esc(insVal(v))}</span>`).join("");
const insTab = t => t && MODS[t] ? `<button type="button" class="btn ghost sm" data-go="${esc(t)}">Open ${esc(MODS[t].label)}</button>` : "";
function insCard(r, o = {}) {
  const [tone, label] = INS_SEV[r.sev] || INS_SEV.info, dis = S.insDis === r.id;
  const acts = o.hist ? (r.status === "dismissed" ? `<button type="button" class="btn ghost sm" data-ins-reopen="${r.id}">Reopen</button>` : "") :
    `${insTab(r.tab)}${r.status === "new" ? `<button type="button" class="btn ghost sm" data-ins-ack="${r.id}">Mark read</button>` : ""}${CFG.me.can_write && !r.handover ? `<button type="button" class="btn ghost sm" data-ins-ho="${r.id}">Add to Handover</button>` : ""}<button type="button" class="btn ghost sm" data-ins-dis="${r.id}">Dismiss</button>`;
  return `<article class="icard ins ${tone}"><header>${pill(tone, label)}<b>${esc(r.title)}</b>${r.status === "new" ? `<span class="tag warn">New</span>` : r.status === "dismissed" ? `<span class="tag">Dismissed</span>` : ""}${r.handover ? `<span class="tag">In Handover</span>` : ""}</header>
    <p>${esc(r.detail)}</p>${o.compact ? "" : `<div class="mchips">${insMetric(r.metric)}</div>`}
    <span class="sub">${r.site ? esc(r.site) + " · " : ""}${esc(INS_KIND[r.kind] || r.kind)} · first seen ${esc(dtime(r.first))} · last ${esc(dtime(r.last))}${r.ackBy ? " · by " + esc(r.ackBy) : ""}${r.reason ? " · reason: " + esc(r.reason) : ""}${r.until && r.status === "dismissed" ? " · hidden until " + esc(dtime(r.until)) : ""}</span>
    ${dis ? `<div class="insdis"><select id="insDays" aria-label="Hide for"><option value="7">Hide for 7 days</option><option value="14">14 days</option><option value="30">30 days</option><option value="90">90 days</option></select><input id="insWhy" type="text" placeholder="Reason (optional)" maxlength="200"><button type="button" class="btn sm" data-ins-dis-ok="${r.id}">Confirm</button><button type="button" class="btn ghost sm" data-ins-dis-x>Cancel</button></div>` : `<div class="acts">${acts}</div>`}</article>`;
}
function insightPanel(I, n = 5, size = "c12", kinds = null) {
  const all = kinds ? I.open.filter(r => kinds.includes(r.kind)) : I.open, rows = all.slice(0, n);
  return panel(size, "Insights", all.length + " active findings · calculated automatically from stored data", rows.length ? `<ul class="att">${rows.map(r => `<li class="${r.sev === "crit" ? "crit" : r.sev === "warn" ? "warn" : ""}"><span><b>${esc(r.title)}</b> ${esc(r.detail)}</span>${go("insight", "View")}</li>`).join("")}</ul>${all.length > n ? go("insight", "All insights") : ""}` : `<div class="empty sm">No active findings.</div>`);
}
/* Insights for one area, shown on its own page (Ticketing, Network, Cyber Security, Devices, ...). Hidden when the area has no active findings. */
const INS_AREA = {servicedesk: ["tickets"], network: ["links", "capacity", "wifi", "correlation"], noc: ["links", "capacity", "correlation"], wifi: ["wifi"], cyber: ["security"], soc: ["security"], xdr: ["security"],
  devices: ["devices"], devnet: ["devices"], devcctv: ["devices"], devops: ["devices"]};
function insArea(tab = S.tab) {
  const I = V.insight, kinds = INS_AREA[tab];
  return I && kinds && I.open.some(r => kinds.includes(r.kind)) ? `<div class="grid">${insightPanel(I, 4, "c12", kinds)}</div>` : "";
}
async function insSum() {
  const sc = S.sumScope || "24h", q = "scope=" + sc + (S.sumDay && sc !== "24h" ? "&day=" + S.sumDay : "");
  try { const x = await api("/api/insights/summary?" + q); set({sumText: x.text}); } catch (er) { alert(er.message); }
}
const insBar = v => `<span class="hbar"><i style="width:${Math.max(2, v)}%;background:var(${v >= 80 ? "--good" : v >= 60 ? "--warn" : "--crit"})"></i></span>`;
function vInsight() {
  const I = V.insight, grid = h => `<div class="grid">${h}</div>`;
  if (!I) return subnav("report") + grid(`<section class="panel c12">${empty()}</section>`);
  const c = I.counts, tab = S.insTab || "findings", tabs = [["findings", "Findings (" + I.open.length + ")"], ["rankings", "Rankings"], ["health", "Location Health"], ["summary", "Shift Summary"], ["history", "History"]];
  const kp = `<div class="kpis k6">${kpi("Critical", fmt(c.crit), "", {cls: c.crit ? "warnv" : ""})}${kpi("Warning", fmt(c.warn), "", {cls: c.warn ? "warnv" : ""})}${kpi("Info", fmt(c.info), "")}${kpi("New", fmt(I.new), "")}${kpi("Dismissed", fmt((I.dismissed || []).length), "")}${kpi("Last analysis", I.updated ? hm(I.updated) : "-", (I.updated ? dtime(I.updated).replace(/, \d\d:\d\d$/, "") + " · " : "") + "runs every 30 min")}</div>`;
  const nav = `<div class="seg insnav">${tabs.map(([k, l]) => `<button type="button" data-ins-tab="${k}" aria-pressed="${k === tab}">${esc(l)}</button>`).join("")}</div>`;
  let body = "";
  if (tab === "findings") {
    const sev = S.insSev || "", kind = S.insKind || "", rows = I.open.filter(r => (!sev || r.sev === sev) && (!kind || r.kind === kind)), kinds = [...new Set(I.open.map(r => r.kind))];
    const chips = `<div class="chips sm">${[["", "All"], ["crit", "Critical"], ["warn", "Warning"], ["info", "Info"]].map(([k, l]) => `<button type="button" class="chip" data-ins-sev="${k}" aria-pressed="${k === sev}">${l}</button>`).join("")}</div>` +
      (kinds.length > 1 ? `<div class="chips sm"><button type="button" class="chip" data-ins-kind="" aria-pressed="${!kind}">All types</button>${kinds.map(k => `<button type="button" class="chip" data-ins-kind="${esc(k)}" aria-pressed="${k === kind}">${esc(INS_KIND[k] || k)}</button>`).join("")}</div>` : "");
    body = `<div class="insbar">${chips}</div>` + (rows.length ? `<div class="icards">${rows.map(r => insCard(r)).join("")}</div>` : `<div class="empty"><b>No findings</b><span>${I.open.length ? "Nothing matches this filter." : "Every indicator is within its normal range."}</span></div>`);
  } else if (tab === "rankings") {
    const R = I.rank;
    body = `<div class="grid" style="padding:0">${panel("c7", "Problem Links", "", tbl(["Link", "Downtime (min)", "Outages", "Availability", "Score"], R.links.map(x => [x.name, x.downMin, x.events, pc(x.avail, 2), x.score]), {r: [1, 2, 3, 4], empty: "No link problems in the last 30 days."}))}
      ${panel("c5", "Repeat Offender Devices", "", tbl(["Device", "Location", "Down events", "Hours down"], R.hosts.map(x => [x.name, x.site, x.events, x.downH]), {r: [2, 3], empty: "No repeat offenders."}))}</div>`;
  } else if (tab === "health") {
    const H = I.rank.health;
    body = `` +
      tbl(["Location", "Health", "Score", "Link availability", "Devices down", "Tickets past SLA"], H.map(x => [x.site, {h: insBar(x.score)}, x.score, x.link == null ? "–" : pc(x.link, 2), x.devTotal ? x.devDown + " / " + x.devTotal : "–", x.overdue]), {r: [2, 3, 4, 5], tall: true, empty: "No location data yet."});
  } else if (tab === "summary") {
    const sc = S.sumScope || "24h", wins = I.windows || [];
    body = `
      <div class="insbar"><label class="sub">Period <select id="sumScope" aria-label="Summary period">${wins.map(w => `<option value="${esc(w.key)}" ${w.key === sc ? "selected" : ""}>${esc(w.label)}</option>`).join("")}</select></label>
      ${sc === "24h" ? "" : `<label class="sub">Date <input type="date" id="sumDay" value="${esc(S.sumDay || nowShift().today)}" max="${esc(nowShift().today)}" min="${esc(CFG.params.data_start)}"></label>`}</div>
      <pre class="sumtxt" id="sumTxt">${esc(S.sumText || I.summary)}</pre><div class="acts"><button type="button" class="btn" data-ins-copy>Copy text</button><button type="button" class="btn ghost" data-ins-refresh>Regenerate</button></div>`;
  } else {
    const st = Object.entries(I.stats || {}).sort((a, b) => b[1].total - a[1].total);
    body = `<div class="grid" style="padding:0">${panel("c12", "Resolved in the last 14 days", "", I.done.length ? tbl(["Resolved", "Finding", "Detail"], I.done.map(r => [dtime(r.resolved), r.title, r.detail]), {tall: true}) : `<div class="empty sm">Nothing resolved yet.</div>`)}
      ${panel("c7", "Dismissed", "", I.dismissed.length ? `<div class="icards">${I.dismissed.map(r => insCard(r, {hist: true, compact: true})).join("")}</div>` : `<div class="empty sm">No dismissed findings.</div>`)}
      ${panel("c5", "Tuning", "", tbl(["Type", "Findings", "Dismissed", "Rate"], st.map(([k, v]) => [INS_KIND[k] || k, v.total, v.dismissed, pc(v.dismissed / v.total, 0)]), {r: [1, 2, 3], empty: "No data yet."}))}</div>`;
  }
  const how = `<details class="panel c12 how"><summary>How it works</summary><p class="sub">The analysis runs every 30 minutes on stored data, with no external service. The latest value is compared with what is normal (median and deviation of the previous 4 to 8 weeks, same weekday when there is a weekly pattern). A finding appears only when the difference is large and the absolute change is meaningful. Trends use the slope of the last 21 days to forecast when a target is crossed. Devices in maintenance are excluded. A finding that stops appearing is closed automatically.${CFG.me.is_admin ? `</p><button type="button" class="btn ghost sm" data-ins-run>Run analysis now</button>` : "</p>"}</details>`;
  return subnav("report") + (S.msg ? `<div class="msg ok">${esc(S.msg)}</div>` : "") + kp + grid(`<section class="panel c12"><div class="insbar">${nav}</div>${body}</section>` + how);
}
document.addEventListener("click", async e => {
  const q = a => e.target.closest(a), $a = q("[data-ins-ack]"), $d = q("[data-ins-dis]"), $ok = q("[data-ins-dis-ok]"), $x = q("[data-ins-dis-x]"), $h = q("[data-ins-ho]"), $re = q("[data-ins-reopen]"), $run = q("[data-ins-run]"), $t = q("[data-ins-tab]"), $s = q("[data-ins-sev]"), $k = q("[data-ins-kind]"), $c = q("[data-ins-copy]"), $rf = q("[data-ins-refresh]");
  try {
    if ($t) set({insTab: $t.dataset.insTab, insDis: null});
    else if ($s) set({insSev: $s.dataset.insSev});
    else if ($k) set({insKind: $k.dataset.insKind});
    else if ($d) set({insDis: +$d.dataset.insDis});
    else if ($x) set({insDis: null});
    else if ($a) { $a.disabled = true; await send("/api/insights/" + $a.dataset.insAck + "/ack", {}); refresh(); }
    else if ($ok) { $ok.disabled = true; await send("/api/insights/" + $ok.dataset.insDisOk + "/dismiss", {reason: $("insWhy").value, days: +$("insDays").value}); S.insDis = null; refresh({msg: "Finding dismissed."}, true); }
    else if ($re) { $re.disabled = true; await send("/api/insights/" + $re.dataset.insReopen + "/reopen", {}); refresh({msg: "Finding reopened."}, true); }
    else if ($h) { $h.disabled = true; await send("/api/insights/" + $h.dataset.insHo + "/handover", {}); refresh({msg: "Handover created. The next shift will see it."}, true); }
    else if ($run) { $run.disabled = true; $run.textContent = "Analyzing…"; const x = await send("/api/insights/run", {}); refresh({msg: x.msg || "Analysis finished."}, true); }
    else if ($rf) insSum();
    else if ($c) { const t = $("sumTxt").textContent; try { await navigator.clipboard.writeText(t); $c.textContent = "Copied"; } catch (er) { const r = document.createRange(); r.selectNode($("sumTxt")); getSelection().removeAllRanges(); getSelection().addRange(r); $c.textContent = "Selected, press Ctrl+C"; } }
  } catch (er) { if (er) alert(er.message); }
});
document.addEventListener("change", e => {
  if (e.target.id === "sumScope" || e.target.id === "sumDay") { S.sumScope = $("sumScope").value; S.sumDay = $("sumDay") ? $("sumDay").value : ""; insSum(); }
});
