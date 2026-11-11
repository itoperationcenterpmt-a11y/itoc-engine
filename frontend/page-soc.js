const CST = {ok: ["ok", "Validated"], dup: ["dup", "In 2 batches (latest used)"], bad: ["bad", "Unreadable"], miss: ["miss", "Not uploaded"], wait: ["wait", "Today, not due yet"]};
function covStrip(chk) { return `<div class="cov">${chk.map(x => `<span class="c ${CST[x.s][0]}" data-tip="${esc(dlong(x.d) + "\n" + CST[x.s][1] + (x.b ? "\nBatch " + x.b : ""))}">${new Date(dayMs(x.d)).getUTCDate()}</span>`).join("")}</div>
  <div class="legend">${[["ok", "Validated"], ["dup", "Duplicate, latest used"], ["bad", "Unreadable"], ["miss", "Not uploaded"]].map(([k, l]) => `<span><b class="c ${k}"></b>${l}</span>`).join("")}</div>`; }
/* NDR per firewall (Panorama device name) and location. Administrators can correct the location of a firewall in the table. */
function socFw(F) {
  const adm = CFG.me.is_admin, opts = s => `<option value="">Automatic</option><option value="-" ${s === "-" ? "selected" : ""}>No location</option>` + CFG.sites.map(x => `<option ${x === s ? "selected" : ""}>${esc(x)}</option>`).join("");
  const rows = F.fw.map(x => [x.fw, adm ? {h: `<select class="pick" data-fwmap="${esc(x.fw)}" aria-label="Location of ${esc(x.fw)}"><option value="${esc(x.site || "")}">${esc(x.site || "Not matched")}</option>${opts("")}</select>`} : x.site || "Not matched", x.events, x.crit + x.high, x.blocked, {h: `<span class="nw">${fwB(x.bytes)}</span>`}, x.sessions]);
  const top = F.bySite.filter(s => s.ch).slice(0, 10);
  return {
    sites: () => panel("c6", "Critical and High per Location", "firewall events in the period", top.length ? hbars(top.map(s => [s.site, s.ch, 0, fmt(s.ch)])) : `<div class="empty sm">No critical or high events in this period.</div>`),
    traffic: () => panel("c6", "Traffic per Location", "bytes through the firewalls", hbars(F.bySite.filter(s => s.bytes).sort((a, b) => b.bytes - a.bytes).slice(0, 10).map(s => [s.site, s.bytes, 0, fwB(s.bytes)]))),
    table: () => panel("c12", "Firewalls", fmt(F.nFw) + " firewalls" + (F.from ? " · data from " + dmon(F.from) : "") + (F.unmapped.length ? " · " + F.unmapped.length + " not matched to a location" : ""), tbl(["Firewall", "Location", "Events", "Critical + High", "Blocked", "Traffic", "Sessions"], rows, {r: [2, 3, 4, 6], tall: true, empty: "No firewall data in this period yet. It is collected on every Panorama sync."})),
  };
}
/* Progress of the Palo Alto history that is collected in the background, a few days per sync. */
function socProgress(F) {
  const P = (F && F.progress) || [];
  if (!P.length) return "";
  return panel("c12", "Data Collection", P.every(p => !p.pending) ? "complete" : "in progress", `<ul class="checks">${P.map(p => `<li>${pill(p.pending ? "warn" : "good", "")}<div><b>${esc(p.label)}</b><span>${fmt(p.done)} of ${fmt(p.total)} days${p.pending ? ` · ${fmt(p.pending)} still to collect, ${p.per} days per sync` : " · complete"}</span><span class="hbar"><i style="width:${Math.min(100, p.total ? p.done / p.total * 100 : 100)}%;background:var(--${p.pending ? "warn" : "good"})"></i></span></div></li>`).join("")}</ul>`);
}
function socFwVal(F, R) {
  const cut = n => n.replace(/^SPMT-/, "").replace(/-(PA|FW)[-\d].*$/, ""), late = F.fw.filter(x => x.tfrom && x.tfrom > S.from), none = F.fw.filter(x => !x.tfrom);
  const diff = R && !S.site && F.dayN === F.span && R.total ? Math.abs(F.total.events - R.total) / R.total : null;
  const rows = [
    [F.dayN === F.span ? "good" : "warn", `Days with firewall data: ${F.dayN} of ${F.span}`, F.dayN < F.span && F.from ? `Collected since ${dfull(F.from)}; older days are filled in on every Panorama sync.` : ""],
    [late.length || none.length ? "warn" : "good", "Traffic data per firewall", late.length || none.length ? [...late.map(x => `${esc(cut(x.fw))} from ${dmon(x.tfrom)}`), ...none.map(x => `${esc(cut(x.fw))} none`)].join(", ") + ". Panorama has no traffic summary for these firewalls before that date." : "Every firewall has traffic for the whole period"],
    ...(diff == null ? [] : [[diff < 0.05 ? "good" : "warn", "Firewall events against the all-location summary", `${fmt(F.total.events)} against ${fmt(R.total)} (${pc(diff, 1)} difference)`]])];
  return panel("c12", "Firewall Data Validation", S.site || "all locations", `<ul class="checks">${rows.map(c => `<li>${pill(c[0], "")}<div><b>${c[1]}</b>${c[2] ? `<span>${c[2]}</span>` : ""}</div></li>`).join("")}</ul>`) + socProgress(F);
}
function vSocSite() {
  const F = V.socfw, P = socFw(F), T = F.total, B = F.days.map(x => ({label: dmon(x.date), full: dlong(x.date)})), ch = [{name: "Critical", c: "--crit", v: F.days.map(x => x.critical)}, {name: "High", c: "--serious", v: F.days.map(x => x.high)}, {name: "Other", c: "--ss", v: F.days.map(x => x.other)}];
  if (!F.nFw) return `<div class="grid"><section class="panel c12">${empty("No firewall data for " + esc(S.site) + " in this period. A location needs a firewall matched to it (Firewalls table on the all-locations view).")}</section></div>`;
  const hb = (rows, f = fmt) => rows.length ? hbars(rows.map(x => [x.k, x.n, 0, f(x.n)])) : `<div class="empty sm">No detail for this period yet. It is filled in on every Panorama sync.</div>`;
  const SC = {critical: VZC.crit, high: VZC.sev, medium: VZC.warn, low: VZC.low, informational: VZC.good}, sevName = k => k.charAt(0).toUpperCase() + k.slice(1);
  const dayG = F.days.map(x => x.bytes / 1e9), tcat = F.cat[0];
  return (F.from > S.from ? `<p class="sub msnote">Per-firewall data starts on ${dfull(F.from)}; earlier days of this period are not included.</p>` : "") + `<div class="kpis k6">${kpi("Events", fmt(T.events), fmt(F.nFw) + " firewall" + (F.nFw > 1 ? "s" : ""))}${kpi("Critical + High", fmt(T.ch), fmt(T.crit) + " critical", {cls: T.crit ? "warnv" : ""})}${kpi("Blocked", T.events ? pc(T.blocked / T.events) : "-", fmt(T.blocked) + " events")}${kpi("Traffic", fwB(T.bytes), fwB(T.bytes / Math.max(1, F.dayN)) + " per day")}${kpi("Sessions", fmt(T.sessions), "")}${kpi("Top Category", tcat ? esc(tcat.k) : "-", tcat ? fmt(tcat.n) + " events" : "")}</div>
  <div class="grid">${panel("c8", "Events per Day", S.site, legend(ch) + bars(B, ch, {stack: true, label: "Events per day"}))}
  ${panel("c4", "Severity", "", vzDonut(F.sev.map(x => ({k: sevName(x.k), v: x.n, c: SC[x.k] || VZC.low})), {center: fmt(T.events), sub: "events", label: "Severity"}))}
  ${panel("c8", "Traffic per Day (GB)", fwB(T.bytes), bars(B, [{name: "Traffic", c: "--s1", v: dayG}], {dec: 1, unit: " GB", label: "Traffic per day"}))}
  ${panel("c4", "Firewall Action", "", hb(F.act))}
  ${panel("c6", "Threat Categories", "", hb(F.cat))}
  ${panel("c6", "Threat Types", "", hb(F.typ))}
  ${panel("c6", "Top Applications by Volume", "", hb(F.app, fwB))}
  ${panel("c6", "Top Sources by Traffic", "source IP, bytes sent through the firewall", hb(F.src, fwB))}
  ${panel("c6", "Blocked per Day", "events not just alerted", bars(B, [{name: "Blocked", c: "--good", v: F.days.map(x => x.blocked)}], {label: "Blocked per day"}))}
  ${P.table()}${socFwVal(F, null)}</div>`;
}
function vSoc() {
  if (S.site && V.socfw) return insArea("soc") + vSocSite();
  const R = socR(), chk = socCheck(), okD = chk.filter(x => x.s === "ok" || x.s === "dup"), bt = batchFor(), Rp = S.cmp ? socR(prevRange()) : null;
  const crit = (V.batches || []).filter(b => b.issues.some(i => i.k === "crit") && b.to >= S.from && b.from <= S.to);
  const checks = [
    [okD.length === chk.length ? "good" : okD.length ? "warn" : "crit", `Days with daily data: ${okD.length} of ${chk.length}`, ""],
    ...crit.map(b => ["crit", `Batch ${esc(b.file)} failed validation`, b.issues.filter(i => i.k === "crit").map(i => esc(i.t)).join(" ")]),
    [Object.keys((V.soc_dup || {})).some(d => d >= S.from && d <= S.to) ? "warn" : "good", "Dates duplicated across batches", Object.keys((V.soc_dup || {})).filter(d => d >= S.from && d <= S.to).map(dmon).join(", ") || "None"],
    [R.ch <= R.total && R.sevTotal.blk <= R.total && R.urlBlk <= R.url ? "good" : "crit", "Number consistency", ""],
    [bt ? (bt.from === S.from && bt.to === S.to ? "good" : "warn") : "idle", "Period table (Top report)", bt ? `${esc(bt.file)} · ${dmon(bt.from)} – ${dmon(bt.to)}` : "None yet"]
  ];
  const head = "";
  const UK = {type: ["Threat type", "soc.threat_types"], action: ["Action", "soc.actions"], severity: ["Severity", "soc.severities"]};
  const unkL = Object.entries(R.unknown || {}).map(([k, rows]) => `<li class="warn"><span><b>New ${UK[k][0].toLowerCase()}:</b> ${rows.map(([n, c]) => `${esc(n)} (${fmt(c)})`).join(", ")} · add to <span class="num">${UK[k][1]}</span> in Admin → Operations → Targets & Parameters</span></li>`).join("");
  const unkP = unkL ? panel("c12", "New Values Outside Parameter List", "", `<ul class="att">${unkL}</ul>`) : "";
  const val = panel("c12", "SOC Data Validation", ctxTxt(APPLY.soc), `<div class="valgrid"><div>${covStrip(chk)}</div><ul class="checks">${checks.map(c => `<li>${pill(c[0], "")}<div><b>${c[1]}</b>${c[2] ? `<span>${c[2]}</span>` : ""}</div></li>`).join("")}</ul></div>`, canUp("soc") ? `<span class="acts"><span class="sub">Automatic at 00:00 and 12:00 WIB</span><button class="btn ghost" data-sync="panorama">Pull from Panorama now</button></span>` : `<span class="sub">Automatic at 00:00 and 12:00 WIB</span>`);
  if (!okD.length) return head + `<div class="grid">${val}<section class="panel c12">${empty("No SOC day has passed validation yet.")}</section></div>`;
  const B = dayB(R.daily), ch = [{name: "Critical", c: "--crit", v: R.daily.map(x => x.critical)}, {name: "High", c: "--serious", v: R.daily.map(x => x.high)}], ml = [{name: "Medium", c: "--warn", v: R.daily.map(x => x.medium)}, {name: "Low", c: "--low", v: R.daily.map(x => x.low)}, {name: "Informational", c: "--ss", v: R.daily.map(x => x.informational)}];
  const sd = {type: ["Threat type", R.type], action: ["Firewall action", R.action], cat: ["Threat category", R.cat], dir: ["Threat direction", R.dir]}, cur = sd[S.sdim];
  const tabs = bt ? bt.tables : [], tb = tabs.find(t => t.id === S.stop) || tabs[0], part = okD.length < chk.length ? ` · from ${okD.length}/${chk.length} days` : "";
  const FW = V.socfw && V.socfw.nFw ? socFw(V.socfw) : null;
  return head + insArea("soc") + `<div class="grid">${val}${unkP}</div>${FW ? `<div class="grid">${socFwVal(V.socfw, R)}${FW.sites()}${FW.traffic()}${panel("c6", "Top Sources by Traffic", "source IP, all locations", V.socfw.src.length ? hbars(V.socfw.src.map(x => [x.k, x.n, 0, fwB(x.n)])) : `<div class="empty sm">No detail for this period yet. It is filled in on every Panorama sync.</div>`)}${FW.table()}</div>` : ""}
  <div class="kpis k6">${kpi("Total Events", fmt(R.total), "average " + fmt(R.total / okD.length) + " per validated day" + part, {tip: RUMUS.socTot})}${kpi("Critical + High", fmt(R.ch), fmt(R.crit) + " critical")}${kpi("Critical + High Blocked", pc(R.chBlkPct), "", {tip: RUMUS.socCH, dl: Rp && Rp.ch ? delta(R.chBlkPct, Rp.chBlkPct, {up: true, pct: 1}) : ""})}${kpi("Alert Only", fmt(R.chAlert), "", {cls: R.chAlert ? "warnv" : ""})}${kpi("Internal Source", pc(R.internalPct), bt && bt.K ? fmt(bt.K.hosts) + " internal hosts (table " + dmon(bt.from) + "–" + dmon(bt.to) + ")" : "host table not available", {tip: RUMUS.socInt})}${kpi("URL Blocked", fmt(R.urlBlk), "of " + fmt(R.url) + " URL events")}</div>
  <div class="grid">${panel("c6", "Critical and High per Day", "", legend(ch) + bars(B, ch, {stack: true, label: "Critical and high"}))}
  ${panel("c6", "Medium, Low, Informational per Day", "", legend(ml) + bars(B, ml, {stack: true, label: "Medium low informational"}))}
  ${panel("c6", "Severity and Action", "", tbl(["Severity", "Events", "% of total", "Blocked", "Alert only", "% blocked"], R.sev.concat(R.sevTotal).map(x => [x.k, x.n, pc(x.pct), x.blk, x.alert, pc(x.blkPct)]), {r: [2, 5]}))}
  ${panel("c6", `Per <select class="pick" id="sdim" aria-label="Breakdown">${Object.entries(sd).map(([k, v]) => `<option value="${k}" ${k === S.sdim ? "selected" : ""}>${v[0].toLowerCase()}</option>`).join("")}</select>`, "", tbl([cur[0], "Events", "% of total", "Critical + High", "Blocked", "Alert only"], cur[1].map(x => [x.k, x.n, pc(x.pct), x.ch, x.blk, x.alert]), {tall: true, r: [2]}))}
  ${panel("c6", "Traffic per Day (TB)", fx(R.tb, 2) + " TB, " + fmt(R.sess) + " sessions", bars(B, [{name: "Traffic", c: "--s1", v: R.daily.map(x => x.tb)}], {dec: 2, unit: " TB", label: "Traffic"}))}
  ${panel("c6", "URL Filtering per Category", "", tbl(["Category", "Total", "% of total", "Blocked", "Other"], R.urlCat.map(x => [x.k, x.n, pc(x.pct), x.blk, x.alert]), {tall: true, r: [2]}))}
  ${tb ? panel("c12", `<select class="pick" id="stop" aria-label="Period table">${tabs.map(t => `<option value="${esc(t.id)}" ${t.id === tb.id ? "selected" : ""}>${esc(t.t)}</option>`).join("")}</select>`, `<span class="warn-t">Table period ${dmon(bt.from)} – ${dmon(bt.to)}</span> · ${bt.by === "Panorama API" ? "from Panorama API" : "from manual import"}, the batch that best matches the period filter`, tbl(tb.h, tb.r, {tall: true}) + (tb.note ? `<div class="sub">${esc(tb.note)}</div>` : "")) : panel("c12", "Top Report Tables", "", empty("No valid batch with a Top report for this period."))}</div>`;
}

/* ---------- Schedule & Teams ---------- */
