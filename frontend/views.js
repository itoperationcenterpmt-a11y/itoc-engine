/* IT PMT Dashboard: components and page views, reading the API bundle. */
"use strict";
/* ---------- komponen ---------- */
function nice(v) { if (v <= 0) return 1; const p = Math.pow(10, Math.floor(Math.log10(v))), f = v / p; return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * p; }
function xl(labels, x, y) { const n = labels.length, sparse = labels.some(t => t === ""), k = sparse ? 1 : Math.ceil(n / 12); return labels.map((t, i) => (i % k === 0) ? `<text x="${x(i)}" y="${y}" text-anchor="middle">${esc(t)}</text>` : "").join(""); }
const empty = (t) => `<div class="empty"><b>No data yet</b><span>${t || "No data for this filter. Try changing the period, shift, or location."}</span></div>`;
function axisFmt(v, unit) { return unit === "mbps" ? fx(v, v < 10 && v ? 1 : 0) : fmt(v); }
function bars(B, series, o = {}) {
  const W = o.w || 720, Hh = o.h || 220, L = 52, R = 8, T = 10, Bm = 26, pw = W - L - R, ph = Hh - T - Bm, n = B.length, k = series.length, dec = o.dec || 0, ff = v => dec ? fx(v, dec) : fmt(v);
  if (!n || !series.some(s => s.v.some(v => v > 0))) return empty(o.empty);
  const top = Math.max(...B.map((b, i) => o.stack ? series.reduce((a, s) => a + s.v[i], 0) : Math.max(...series.map(s => s.v[i])))), mx = nice(top), steps = [4, 5, 2].find(s => mx / s >= 1 ? Number.isInteger(mx / s) : true) || 4, gw = pw / n, y = v => T + ph - v / mx * ph;
  let g = ""; for (let i = 0; i <= steps; i++) { const v = mx / steps * i; g += `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" stroke="var(${i ? "--line" : "--axis"})"/><text x="${L - 6}" y="${y(v) + 3.5}" text-anchor="end">${mx / steps < 1 ? fx(v, 1) : fmt(v)}</text>`; }
  let m = ""; const bw = o.stack || k === 1 ? Math.min(28, gw * .66) : Math.min(16, gw * .72 / k);
  B.forEach((b, i) => { const cx = L + gw * i + gw / 2, tip = esc(b.full + "\n" + series.map(s => s.name + ": " + ff(s.v[i]) + (o.unit || "")).join("\n"));
    if (o.stack) { let acc = 0; series.forEach(s => { const v = s.v[i]; if (!v) return; m += `<rect x="${cx - bw / 2}" y="${y(acc + v)}" width="${bw}" height="${Math.max(v / mx * ph, 1)}" fill="var(${s.c})" stroke="var(--surface)" stroke-width="1"/>`; acc += v; }); }
    else series.forEach((s, j) => { const v = s.v[i], x = cx - (k * bw + (k - 1) * 2) / 2 + j * (bw + 2); if (v) m += `<rect x="${x}" y="${y(v)}" width="${bw}" height="${Math.max(v / mx * ph, 1)}" rx="2" fill="var(${s.c})"/>`; });
    m += `<rect x="${L + gw * i}" y="${T}" width="${gw}" height="${ph}" fill="transparent" data-tip="${tip}"/>`; });
  return `<svg class="chart" viewBox="0 0 ${W} ${Hh}" role="img" aria-label="${esc(o.label || "")}">${g}${m}${xl(B.map(b => b.label), i => L + gw * i + gw / 2, Hh - 8)}</svg>`;
}
function lines(B, series, o = {}) {
  const W = o.w || 720, Hh = o.h || 230, L = 52, R = 10, T = 10, Bm = 26, pw = W - L - R, ph = Hh - T - Bm, n = B.length;
  const vals = series.flatMap(s => s.v.filter(v => v != null)); if (!n || !vals.some(v => v > 0)) return empty(o.empty);
  const mx = nice(Math.max(...vals)), x = i => L + (n < 2 ? pw / 2 : pw * i / (n - 1)), y = v => T + ph - v / mx * ph;
  let g = ""; for (let i = 0; i <= 4; i++) { const v = mx / 4 * i; g += `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" stroke="var(${i ? "--line" : "--axis"})"/><text x="${L - 6}" y="${y(v) + 3.5}" text-anchor="end">${mx / 4 < 1 ? fx(v, 1) : fmt(v)}</text>`; }
  let m = ""; series.forEach(s => { let d = "", pen = false; s.v.forEach((v, i) => { if (v == null) { pen = false; return; } d += (pen ? "L" : "M") + x(i).toFixed(1) + " " + y(v).toFixed(1); pen = true; }); m += `<path d="${d}" fill="none" stroke="var(${s.c})" stroke-width="${o.thin ? 1.4 : 2}" stroke-linejoin="round" stroke-linecap="round"/>`; });
  if (o.marks) o.marks.forEach(i => { m += `<line x1="${x(i)}" x2="${x(i)}" y1="${T}" y2="${T + ph}" stroke="var(--crit)" stroke-opacity=".35" stroke-width="${Math.max(1, pw / n)}"/>`; });
  const gw = pw / Math.max(1, n - 1); let ov = "";
  B.forEach((b, i) => { ov += `<rect x="${x(i) - gw / 2}" y="${T}" width="${gw}" height="${ph}" fill="transparent" data-tip="${esc(b.full + "\n" + series.map(s => s.name + ": " + (s.v[i] == null ? "no data" : fx(s.v[i], o.dec ?? 1) + (o.unit || ""))).join("\n"))}"/>`; });
  return `<svg class="chart" viewBox="0 0 ${W} ${Hh}" role="img" aria-label="${esc(o.label || "")}">${g}${m}${ov}${xl(B.map(b => b.label), x, Hh - 8)}</svg>`;
}
function hbars(rows, o = {}) {
  const e = rows.filter(x => x[1] > 0 || (x[2] || 0) > 0); if (!e.length) return empty();
  const mx = Math.max(...e.map(x => Math.max(x[1], x[2] || 0)));
  return `<div class="hb ${o.two ? "two" : ""}">` + e.map(r => `<div class="t" title="${esc(r[0])}">${esc(r[0])}</div><div class="tracks"><div class="track"><div class="fill" style="width:${Math.max(1, r[1] / mx * 100)}%"></div></div>${o.two ? `<div class="track"><div class="fill b" style="width:${Math.max(1, (r[2] || 0) / mx * 100)}%"></div></div>` : ""}</div><div class="num">${esc(r[3] != null ? r[3] : fmt(r[1]))}</div>`).join("") + `</div>`;
}
const legend = s => `<div class="legend">` + s.map(x => `<span><b style="background:var(${x.c})"></b>${esc(x.name)}</span>`).join("") + `</div>`;
const pill = (k, t) => `<span class="pill ${k}"><i>${{good: "✓", warn: "!", crit: "✕", idle: "–"}[k]}</i>${esc(t)}</span>`;
const panel = (cls, title, sub, body, extra) => `<section class="panel ${cls}"><header><h2>${title}</h2>${sub ? `<span class="sub">${sub}</span>` : ""}${extra || ""}</header>${body}</section>`;
const info = t => `<button type="button" class="ib" data-tip="${esc(t)}" aria-label="Formula: ${esc(t)}">i</button>`;
function delta(cur, prev, o = {}) {
  if (!S.cmp || cur == null || prev == null || isNaN(cur) || isNaN(prev)) return "";
  const d = cur - prev; if (Math.abs(d) < 1e-9) return `<span class="dl flat">= same</span>`;
  const good = o.up === undefined ? null : (d > 0) === o.up, txt = o.pct ? fx(Math.abs(d) * 100, 1) + " pts" : prev ? fx(Math.abs(d / prev) * 100, 0) + "%" : fmt(Math.abs(d));
  return `<span class="dl ${good == null ? "flat" : good ? "good" : "bad"}">${d > 0 ? "▲" : "▼"} ${txt}</span>`;
}
const kpi = (l, v, d, o = {}) => `<div class="kpi ${o.cls || ""}"><span class="lbl">${l}${o.tip ? info(o.tip) : ""}</span><span class="v">${v}</span><span class="d">${o.dl || ""}${d || ""}</span></div>`;
function tbl(heads, rows, o = {}) {
  if (!rows.length) return `<div class="empty sm">${o.empty || "No data for this filter."}</div>`;
  const isN = heads.map((h, i) => rows.some(r => typeof r[i] === "number") || (o.r || []).includes(i));
  const cell = c => c == null ? "–" : typeof c === "number" ? (Number.isInteger(c) ? fmt(c) : fx(c, 2)) : c.h != null ? c.h : esc(c);
  const auto = rows.length > (o.max || 12) && o.tall !== false;      // long tables scroll inside their own box instead of stretching the page
  return `<div class="scroll ${o.tall || auto ? "tall" : ""}"><table><thead><tr>${heads.map((h, i) => `<th class="${isN[i] ? "r" : ""}">${esc(h)}</th>`).join("")}</tr></thead><tbody>` + rows.map(r => `<tr>${r.map((c, i) => typeof c === "string" && !isN[i] && c.length > 48 ? `<td class="t cut" title="${esc(c)}">${esc(c)}</td>` : `<td class="${isN[i] ? "r num" : "t"}">${cell(c)}</td>`).join("")}</tr>`).join("") + `</tbody></table></div>` + (auto ? `<div class="sub tcount">${fmt(rows.length)} rows · scroll inside the table to see more</div>` : "");
}
const dayB = arr => arr.map(x => ({label: dmon(x.date), full: dlong(x.date)}));
const stPill = s => ({h: s === NST.ok ? pill("good", s) : s === NST.bad ? pill("crit", s) : pill("idle", s)});
const go = (tab, t) => `<a class="lnk" href="#${tab}" data-go="${tab}">${t || "View details"} →</a>`;

/* ---------- header, nav, filter ---------- */
const ICO = {
  dashboard: '<rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/>',
  ticket: '<path d="M3 9V6a1 1 0 0 1 1-1h16a1 1 0 0 1 1 1v3a2.5 2.5 0 0 0 0 5v3a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-3a2.5 2.5 0 0 0 0-5z"/><path d="M14 5v2.5M14 10.75v2.5M14 16.5V19"/>',
  activity: '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
  wifi: '<path d="M5 12.55a11 11 0 0 1 14 0M1.42 9a16 16 0 0 1 21.16 0M8.53 16.11a6 6 0 0 1 6.95 0"/><circle cx="12" cy="20" r="1"/>',
  cctv: '<path d="M3 8l11-4 2 5-11 4z"/><path d="M9 14l-1 5M5 19h6M16 8l5 1.5"/>',
  xdr: '<circle cx="12" cy="12" r="8"/><path d="M12 2v4M12 18v4M2 12h4M18 12h4"/><circle cx="12" cy="12" r="2"/>',
  server: '<rect x="3" y="4" width="18" height="6" rx="1.5"/><rect x="3" y="14" width="18" height="6" rx="1.5"/><path d="M7 7h.01M7 17h.01M12 7h5M12 17h5"/>',
  camera: '<path d="M3 8a2 2 0 0 1 2-2h2l1.5-2h7L17 6h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><circle cx="12" cy="12.5" r="3.5"/>',
  shield: '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
  users: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c0-3.6 2.9-6 6.5-6s6.5 2.4 6.5 6"/><path d="M16 4.6a3.5 3.5 0 0 1 0 6.8M18.5 14.3c1.9.8 3 2.6 3 5.7"/>',
  handover: '<path d="M17 3l4 4-4 4"/><path d="M3 11V9a2 2 0 0 1 2-2h16"/><path d="M7 21l-4-4 4-4"/><path d="M21 13v2a2 2 0 0 1-2 2H3"/>',
  database: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>',
  sliders: '<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>',
  report: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 17v-3M12 17v-6M15 17v-4"/>',
  calendar: '<rect x="3" y="4" width="18" height="17" rx="2"/><path d="M3 9h18M8 2v4M16 2v4"/>'
};
const icon = k => `<svg viewBox="0 0 24 24" aria-hidden="true">${ICO[(MODS[k] || {}).icon] || '<circle cx="12" cy="12" r="4"/>'}</svg>`;const topOf = k => { const p = (MODS[k] || {}).parent; return p && MODS[p] ? p : k; };
/* Sub-menu: a parent page and its children (e.g. Report + Handover) as tabs inside the page */
const SUBSUM = {network: "Summary", cyber: "Summary", devices: "Summary"};
function subnav(parent) {
  const items = TABS.filter(t => t[0] === parent || (MODS[t[0]] || {}).parent === parent);
  return items.length < 2 ? "" : `<div class="subtabs">${items.map(([k, l]) => `<a href="#${k}" data-tab="${k}" aria-selected="${k === S.tab}">${esc(k === parent && SUBSUM[parent] ? SUBSUM[parent] : l)}</a>`).join("")}</div>`;
}
/* Running shift clock: called on render and every second so it never freezes. */
function renderDuty() {
  const n = nowShift(), tm = teamOn(n.date, n.shift), d = new Date(nowMs()), hh = pad(d.getUTCHours()), mm = pad(d.getUTCMinutes()), ss = pad(d.getUTCSeconds());
  ["duty", "dutyH"].forEach(id => {
    const e = $(id); if (!e) return;
    if (!e.querySelector(".clk")) e.innerHTML = `<i></i><span><span class="dtxt"></span><small class="clk"><span class="th"></span><b>:</b><span class="tm"></span><b>:</b><span class="ts"></span> WIB</small></span>`;   // structure is built once so the animation does not restart every second
    e.querySelector(".dtxt").textContent = `On duty: Team ${tm} · ${SN[n.shift]}`;
    e.querySelector(".th").textContent = hh; e.querySelector(".tm").textContent = mm; e.querySelector(".ts").textContent = ss;
  });
  $("dutyM").textContent = `Team ${tm} · ${SN[n.shift]} · ${hh}.${mm}`;
}function renderShell() {
  const NAVT = TABS.filter(t => topOf(t[0]) === t[0]), curTop = topOf(S.tab);
  $("tabs").innerHTML = NAVT.map(([k, l, bd]) => `<a role="tab" href="#${k}" data-tab="${k}" title="${esc(l)}" aria-selected="${k === curTop}">${icon(k)}<span>${esc(l)}</span></a>`).join("");
  $("sheetGrid").innerHTML = NAVT.map(([k, l, bd]) => `<a href="#${k}" data-tab="${k}" aria-selected="${k === curTop}">${icon(k)}<span>${esc(l)}</span></a>`).join("");
  $("moreBtn").classList.toggle("on", NAVT.findIndex(t => t[0] === curTop) > 3);
  const cur = TABS.find(t => t[0] === S.tab), par = (MODS[S.tab] || {}).parent, grp = SUBSUM[S.tab] ? S.tab : (SUBSUM[par] ? par : "");
  $("ptitle").textContent = !cur ? "" : grp ? MODS[grp].label + " · " + (S.tab === grp ? SUBSUM[grp] : cur[1]) : cur[1];
  $("subnav").innerHTML = grp ? subnav(grp) : "";
  $("psub").textContent = APPLY[S.tab] && APPLY[S.tab].p ? rangeTxt() : "";
  $("fPreset").innerHTML = PRESETS.map(([k, l]) => `<button type="button" data-p="${k}" aria-pressed="${S.preset === k}">${l}</button>`).join("");
  $("fShift").innerHTML = SN.map((l, i) => `<button type="button" data-s="${i}" aria-pressed="${S.sf === i}" ${i ? `title="${shiftHours(i)}"` : ""}>${l}</button>`).join("");
  $("fSite").innerHTML = `<option value="">${CFG.me.site ? "Your account's location" : "All locations"}</option>` + [...CFG.sites, ...(DEVTAB(S.tab) && V.dev ? V.dev.unmapped.map(u => u.code) : []), ...(S.tab === "wifi" && V.wifi ? V.wifi.opts.locs.filter(x => !CFG.sites.includes(x)) : [])].map(s => `<option ${s === S.site ? "selected" : ""}>${esc(s)}</option>`).join("");
  $("fFrom").value = S.from; $("fTo").value = S.to; $("fFrom").max = $("fTo").max = nowShift().today; $("fFrom").min = $("fTo").min = CFG.params.data_start; $("fCmp").checked = S.cmp;
  const ap = APPLY[S.tab], anyF = !!(ap.p || ap.l || ap.k || ap.t || ap.g || ap.y), KL = CFG.params["dev.kind_labels"] || {}, SL = [["", "All"], ["down", "Down"], ["degraded", "Interface"], ["up", "Online"], ["maintenance", "Maintenance"], ["disabled", "Disabled"]];
  const kinds = new Map(Object.entries(KL)); ((V.dev && V.dev.byKind) || []).forEach(k => kinds.set(k.key, KL[k.key] || k.k));
  const gl = ((V.dev && V.dev.groups) || []).filter(g => !S.kind || g.kind === S.kind);
  const WF = S.tab === "wifi" && V.wifi ? V.wifi.opts : null;
  [["gKind", "Band", "Category"], ["gGrp", "SSID", "Group"], ["gTyp", "Zone", "Type"]].forEach(([id, w, d]) => { $(id).querySelector(".k").textContent = S.tab === "wifi" ? w : S.tab === "xdr" && id === "gKind" ? "Severity" : S.tab === "cctv" ? {gGrp: "Server", gTyp: "Hardware", gKind: "Type"}[id] || d : d; });
  const MS_ = S.tab === "cctv" && V.cctv ? V.cctv.opts : null;
  if (MS_) {
    $("fKind").innerHTML = [["", "All"], ["fix", "FIX"], ["ptz", "PTZ"], ["pa", "Public Announcers"]].map(([k, l]) => `<button type="button" data-k="${esc(k)}" aria-pressed="${S.kind === k}">${esc(l)}</button>`).join("");
    $("fGrp").innerHTML = `<option value="">All servers</option>` + MS_.servers.map(z => `<option ${z === S.grp ? "selected" : ""}>${esc(z)}</option>`).join("");
    $("fTyp").innerHTML = `<option value="">All hardware</option>` + MS_.hardware.filter(h => !S.grp || h.server === S.grp).map(h => `<option ${h.name === S.dtype ? "selected" : ""}>${esc(h.name)}</option>`).join("");
  } else if (WF) {
    $("fTyp").innerHTML = `<option value="">All zones</option>` + WF.zones.map(z => `<option ${z === S.dtype ? "selected" : ""}>${esc(z)}</option>`).join("");
    $("fGrp").innerHTML = `<option value="">All SSIDs</option>` + WF.ssids.map(z => `<option ${z === S.grp ? "selected" : ""}>${esc(z)}</option>`).join("");
    $("fKind").innerHTML = [["", "All"], ["2.4 GHz", "2.4 GHz"], ["5 GHz", "5 GHz"], ["6 GHz", "6 GHz"]].map(([k, l]) => `<button type="button" data-k="${esc(k)}" aria-pressed="${S.kind === k}">${esc(l)}</button>`).join("");
  } else {
  $("fTyp").innerHTML = `<option value="">All types</option>` + ((V.dev && V.dev.byType) || []).map(t => `<option value="${esc(t.code)}" ${t.code === S.dtype ? "selected" : ""}>${esc(t.k)} (${t.total})</option>`).join("");
  $("fGrp").innerHTML = `<option value="">All groups</option>` + gl.map(g => `<option value="${esc(g.name)}" ${g.name === S.grp ? "selected" : ""}>${esc(g.name)} (${g.n})</option>`).join("");
  $("fKind").innerHTML = [["", "All"], ...kinds].map(([k, l]) => `<button type="button" data-k="${esc(k)}" aria-pressed="${S.kind === k}">${esc(l)}</button>`).join("");
  }
  if (S.tab === "xdr") $("fKind").innerHTML = [["", "All"], ["critical", "Critical"], ["high", "High"], ["medium", "Medium"], ["low", "Low"]].map(([k, l]) => `<button type="button" data-k="${esc(k)}" aria-pressed="${S.kind === k}">${esc(l)}</button>`).join("");
  $("fStat").innerHTML = (S.tab === "cctv" ? [["", "All"], ["up", "Online"], ["down", "Offline"], ["nozbx", "No status"], ["rec", "Recording"], ["norec", "Not recording"], ["off", "Disabled"]] : SL).map(([k, l]) => `<button type="button" data-st="${k}" aria-pressed="${S.dstat === k}">${l}</button>`).join("");
  $("gKind").hidden = !ap.k; $("gStat").hidden = !ap.t; $("gGrp").hidden = !ap.g; $("gTyp").hidden = !ap.y;
  $("fwrap").hidden = !anyF;
  $("fbar").classList.toggle("off", !anyF);
  [["gPeriode", ap.p], ["gShift", ap.s], ["gSite", ap.l], ["gCmp", ap.p && ap.c]].forEach(([id, on]) => { const el = $(id); el.hidden = !on; el.classList.toggle("na", !on); el.querySelectorAll("button,select,input").forEach(x => x.disabled = !on); });
  if (CFG.me.site) { $("fSite").disabled = true; $("gSite").classList.add("na"); }
  const chips = [], active = [];
  if (ap.p) active.push(rangeTxt()); if (ap.s && S.sf) active.push("shift " + SN[S.sf] + " (" + shiftHours(S.sf) + ")"); if (ap.l && S.site) active.push(S.site); if (ap.k && S.kind) active.push(S.tab === "wifi" || S.tab === "xdr" ? S.kind : (KL[S.kind] || S.kind)); if (ap.g && S.grp) active.push(S.grp); if (ap.y && S.dtype) active.push(((V.dev && V.dev.byType.find(t => t.code === S.dtype)) || {k: S.dtype}).k); if (ap.t && S.dstat) active.push(SL.find(x => x[0] === S.dstat)[1]); if (S.cmp && $("gCmp").querySelector("input:not(:disabled)")) active.push("vs " + dmon(prevRange().from) + " – " + dmon(prevRange().to));
  if (anyF) { chips.push(`<span class="on">Active filter: <b>${esc(active.join(" · ") || "All")}</b></span>`);
    if (!ap.s && S.sf || !ap.l && S.site) chips.push(`<span class="na-txt">${(!ap.s && S.sf ? "Shift" : "") + (!ap.s && S.sf && !ap.l && S.site ? " and " : "") + (!ap.l && S.site ? "location" : "")} does not apply on this page</span>`); }
  $("fApplies").innerHTML = chips.join("");
  renderDuty();
  $("fSum").textContent = anyF ? (active.join(" · ") || "All") : "Not applicable on this page";

}

/* ---------- Ringkasan ---------- */
function vRingkasan() {
  const hasT = "tk" in V, hasN = "net" in V, hasS = "soc" in V, hasH = "ho_open" in V, D = V.dev, hasD = !!(D && D.all && D.all.total), Wf = V.wifi, hasW = !!(Wf && (Wf.total || Wf.apTotal)), Xd = V.xdr, hasX = !!(Xd && Xd.configured && (Xd.total || Xd.backlogCH)), Cc = V.cctv, hasC = !!(Cc && Cc.configured && Cc.total), In = V.insight, hasI = !!(In && In.open.length);
  const T = hasT ? tkR() : null, N = hasN ? netR() : null, R = hasS ? socR() : null, chk = hasS ? socCheck() : [], okDays = chk.filter(x => x.s === "ok" || x.s === "dup").length, now = nowShift();
  const P = S.cmp ? prevRange() : null, Tp = P && tkR(P), Np = P && netR(P), Rp = P && socR(P);
  const openOld = V.open_old || [], oldD = CFG.params["sd.open_alert_days"], badLinks = N ? N.rank.filter(s => s.status === NST.bad) : [], hoOpen = V.ho_open || [], hiCrit = hoOpen.filter(h => prTone(h.prio) === "crit").length;
  const att = [];
  if (openOld.length) att.push(["crit", `<b>${pl(openOld.length, "ticket")} open for more than ${oldD} days</b>, oldest: ${esc(openOld[0].subject)} (#${esc(openOld[0].id)}, ${fx(openOld[0].age, 0)} days).`, "servicedesk"]);
  if (badLinks.length) att.push(["crit", `<b>${badLinks.length} links below the ${pc(PAR.target, 1)} target</b>: ${badLinks.slice(0, 3).map(s => esc(s.link) + " (" + pc(s.av, 2) + ")").join(", ")}${badLinks.length > 3 ? ", …" : ""}.`, "noc"]);
  if (hiCrit) att.push(["crit", `<b>${hiCrit} high-priority handovers</b> are still open.`, "serahterima"]);
  if (N && N.nodata) att.push(["warn", `<b>${pl(N.nodata, "link")} with insufficient data</b> (monitoring coverage below ${pc(PAR.minCov, 0)}), not assessed against SLA.`, "noc"]);
  if (R && R.chAlert) att.push(["warn", `<b>${fmt(R.chAlert)} critical/high events were alert-only</b>, not blocked by the firewall.`, "soc"]);
  if (R && R.unknown && Object.keys(R.unknown).length) att.push(["warn", `<b>Cyber Security: new values outside the parameter list</b> (${Object.entries(R.unknown).map(([k, r]) => ({type: "type", action: "action", severity: "severity"}[k]) + ": " + r.map(x => esc(x[0])).join(", ")).join("; ")})`, "soc"]);
  if (N && (N.unmappedIsp || []).length) att.push(["warn", `<b>${N.unmappedIsp.length} links do not match any ISP</b>: ${N.unmappedIsp.slice(0, 3).map(esc).join(", ")}`, "noc"]);
  if (hasD && D.all.down) att.push(["warn", `<b>${fmt(D.all.down)} devices down</b> (CCTV and Gate System), ${fmt(D.chronic)} of them for more than 30 days.`, "devices"]);
  if (hasX && Xd.backlogCH) att.push(["warn", `<b>${Xd.backlogCH} critical/high XDR alerts</b> are still open.`, "xdr"]);
  if (hasW && Wf.apTotal - Wf.apOnline > 0) att.push(["warn", `<b>${Wf.apTotal - Wf.apOnline} of ${Wf.apTotal} WiFi Access Points</b> are offline.`, "wifi"]);
  if (hasD && (D.error || D.stale)) att.push(["warn", `<b>Zabbix data ${D.error ? "failed to sync" : "is not up to date"}</b>. Check the connector in Admin.`, "devices"]);
  const bad = chk.filter(x => x.s === "bad" || x.s === "miss"); if (bad.length) att.push(["warn", `<b>SOC data is incomplete</b>: ${bad.length} of ${chk.length} days unreadable or not uploaded.`, "kelengkapan"]);
  const s1 = hasT ? [{name: "Tickets In", c: "--s1", v: T.daily.map(x => x.in)}, {name: "Tickets Closed", c: "--s2", v: T.daily.map(x => x.done)}] : [];
  const cg = GROUPS.find(g => g.kind === "office"), care = cg ? CFG.people.filter(p => p.unit === cg.unit) : [], ct = CFG.params["report.contact"] || {};
  const careP = cg ? panel("c3", esc(cg.label), esc(cg.start + "–" + cg.end), `<div class="carenum">${ct.phone ? `<span class="lbl">${esc(cg.label)} hotline</span><b class="num">${esc(ct.phone)}</b>` : ""}${ct.email ? `<span class="sub">${esc(ct.email)}</span>` : ""}</div>${care.length ? `<ul class="plist">${care.map(p => `<li><span>${esc(p.name)}<span class="sub"> · ${esc(p.job || "")}</span></span><span class="num sub">${esc(p.phone || "")}</span></li>`).join("")}</ul>` : ""}`) : "";
  const lead = CFG.people.filter(p => p.unit === "ITOC" && !p.team_code), leadP = lead.length ? panel("c3", "Escalation", "Supervisor & Lead", `<ul class="plist">${lead.map(p => `<li><span>${esc(p.name)}<span class="sub"> · ${esc((p.job || "").replace(/^ITOC /, ""))}</span></span><span class="num sub">${esc(p.phone || "")}</span></li>`).join("")}</ul>`) : "";
  const dom = (title, tab, body) => `<section class="panel c3 dom"><header><h2>${title}</h2></header><div class="mini">${body}</div>${go(tab)}</section>`;
  const wg = k => { const w = widgetFind(k); return w && widgetOk(w) ? w.html() : ""; };
  const xCrit = hasX ? (Xd.bySev.find(x => x.k === "critical") || {n: 0}).n : 0, apOff = hasW ? Wf.apTotal - Wf.apOnline : 0;
  const tile = (tab, name, tone, head, sub) => `<button type="button" class="stile ${tone}" data-go="${tab}"><span class="k">${esc(name)}</span><b>${head}</b><span class="sub">${sub}</span></button>`;
  const tiles = [
    hasT ? tile("servicedesk", "Ticketing", openOld.length ? "crit" : "good", openOld.length ? pl(openOld.length, "old open ticket") : "Under control", fmt(T.n) + " tickets · " + fmt(T.open) + " open · SLA " + pc(T.slaPct)) : "",
    hasN || hasW ? tile("network", "Network", badLinks.length ? "crit" : (N && N.nodata) || apOff ? "warn" : "good", badLinks.length ? pl(badLinks.length, "link") + " below target" : apOff ? apOff + " APs offline" : "Stable", (N ? "Availability " + pc(N.avail, 2) : "") + (N && hasW ? " · " : "") + (hasW ? fmt(Wf.total) + " WiFi clients" : "")) : "",
    hasS || hasX ? tile("cyber", "Cyber Security", xCrit ? "crit" : (R && R.chAlert) || (hasX && Xd.backlogCH) ? "warn" : "good", xCrit ? xCrit + " critical XDR alerts" : (R && R.chAlert) || (hasX && Xd.backlogCH) ? "Needs follow-up" : "No issues", (R ? fmt(R.total) + " NDR events" : "") + (R && hasX ? " · " : "") + (hasX ? fmt(Xd.total) + " XDR alerts" : "")) : "",
    hasD ? tile("devices", "Devices", D.all.down ? "warn" : "good", D.all.down ? fmt(D.all.down) + " devices down" : "All online", "Availability " + (D.all.avail != null ? pc(D.all.avail, 1) : "-") + " · " + fmt(D.all.total) + " devices") : "",
    hasC ? tile("cctv", "Milestone", Cc.srv.failed.length ? "warn" : "good", Cc.srv.ok + " of " + Cc.srv.total + " servers syncing", fmt(Cc.zbx.up + Cc.zbx.other) + " cameras online" + (Cc.zbx.down ? " · " + fmt(Cc.zbx.down) + " offline" : "") + " · " + fmt(Cc.total) + " cameras") : "",
    hasH ? tile("serahterima", "Handover", hiCrit ? "crit" : hoOpen.length ? "warn" : "good", hoOpen.length ? hoOpen.length + " open handovers" : "None open", hiCrit ? hiCrit + " high priority" : "all under control") : "",
    hasI ? tile("insight", "Insights", In.counts.crit ? "crit" : In.counts.warn ? "warn" : "good", In.open.length + " active findings", In.counts.crit + " critical · " + In.counts.warn + " warning") : ""
  ].filter(Boolean);
  const tilesP = tiles.length ? panel("c12", "Today's Status", ctxTxt(), `<div class="stiles">${tiles.join("")}</div>`) : "";
  return `<div class="grid">
  ${tilesP}
  ${panel("c8", "Needs Attention", ctxTxt(), att.length ? `<ul class="att">${att.map(a => `<li class="${a[0]}"><span>${a[1]}</span>${go(a[2], "View")}</li>`).join("")}</ul>` : `<div class="empty sm">Nothing needs follow-up.</div>`)}
  ${panel("c4", "On Duty", dlong(now.date) + " · " + shiftHours(now.shift), onDuty(now))}
  ${hasI ? insightPanel(In, 4, "c6") : ""}
  ${leadP}
  ${careP}
  ${!hasT ? "" : dom("Ticketing", "servicedesk", kpi("Tickets In", fmt(T.n), fx(T.perDay, 1) + "/day", {tip: RUMUS.tkIn, dl: Tp ? delta(T.n, Tp.n) : ""}) + kpi("Closed", pc(T.doneRate), fmt(T.open) + " open", {tip: RUMUS.tkDone, dl: Tp ? delta(T.doneRate, Tp.doneRate, {up: true, pct: 1}) : ""}) + kpi("Within SLA Target", pc(T.slaPct), fmt(T.slaOut) + " over", {tip: RUMUS.tkSla, dl: Tp ? delta(T.slaPct, Tp.slaPct, {up: true, pct: 1}) : "", cls: T.slaPct != null && T.slaPct < CFG.params["sd.sla_warn"] ? "warnv" : ""}) + kpi("Median Duration", fx(T.medMin, 0) + " min", "P90 " + fx(T.p90, 1) + " h", {tip: RUMUS.tkMed, dl: Tp ? delta(T.medMin, Tp.medMin, {up: false}) : ""}))}
  ${!hasN ? "" : dom("Networking", "noc", N ? kpi("Availability", pc(N.avail, 2), "target " + pc(PAR.target, 1), {tip: RUMUS.av, dl: Np ? delta(N.avail, Np.avail, {up: true, pct: 1}) : "", cls: N.avail < PAR.target ? "warnv" : ""}) + kpi("Links Meeting SLA", N.ok + "/" + (N.ok + N.bad), N.bad + " not met, " + N.nodata + " no data", {tip: RUMUS.link}) + kpi("Total Downtime", fx(N.downH, 1) + " h", N.events + " incidents", {tip: RUMUS.down, dl: Np ? delta(N.downH, Np.downH, {up: false}) : ""}) + kpi("High Utilization", fmt(N.utilHigh), "links peaking ≥ " + pc(PAR.utilPeak, 0), {tip: RUMUS.util}) : empty())}
  ${!hasS ? "" : dom("Cyber Security", "soc", kpi("Critical + High Blocked", R.ch ? pc(R.chBlkPct) : "–", fmt(R.chAlert) + " alert-only", {tip: RUMUS.socCH, dl: Rp && Rp.ch ? delta(R.chBlkPct, Rp.chBlkPct, {up: true, pct: 1}) : ""}) + kpi("Total Events", R.total ? fmt(R.total) : "–", fmt(R.ch) + " critical/high", {tip: RUMUS.socTot}) + kpi("Validated Days", okDays + "/" + chk.length, okDays < chk.length ? "the rest are not counted" : "complete", {cls: okDays < chk.length ? "warnv" : ""}) + kpi("Internal Source", pc(R.internalPct), "of all events", {tip: RUMUS.socInt}))}
  ${!hasX ? "" : dom("XDR", "xdr", kpi("Alerts", fmt(Xd.total), "in period") + kpi("Still Open", fmt(Xd.open), "not closed", {cls: Xd.open ? "warnv" : ""}) + kpi("Critical", fmt(xCrit), "in period") + kpi("Critical/High Backlog", fmt(Xd.backlogCH), "", {cls: Xd.backlogCH ? "warnv" : ""}))}
  ${!hasD ? "" : dom("Devices", "devices", kpi("Devices", fmt(D.all.total), "") + kpi("Availability Now", D.all.avail != null ? pc(D.all.avail, 1) : "-", "", {cls: D.all.avail != null && D.all.avail < 0.95 ? "warnv" : ""}) + kpi("Down", fmt(D.all.down), fmt(D.chronic) + " for over 30 days", {cls: D.all.down ? "warnv" : ""}) + kpi("Interface Issues", fmt(D.all.deg || 0), ""))}
  ${!hasW ? "" : dom("WiFi", "wifi", kpi("Active Clients", fmt(Wf.total), "connected now") + kpi("Access Points", Wf.apTotal ? fmt(Wf.apOnline) + " / " + fmt(Wf.apTotal) : "-", "online", {cls: Wf.apTotal && Wf.apOnline < Wf.apTotal ? "warnv" : ""}) + kpi("Weak Signal", fmt(Wf.weak), "below " + Wf.weakAt + " dBm", {cls: Wf.weak ? "warnv" : ""}) + kpi("Usage", wBytes(Wf.tx + Wf.rx), ""))}
  ${!hasC ? "" : dom("Milestone", "cctv", kpi("Servers", Cc.srv.ok + " / " + Cc.srv.total, Cc.srv.failed.length ? fmt(Cc.srv.failed.length) + " not syncing" : "all syncing", {cls: Cc.srv.failed.length ? "warnv" : ""}) + kpi("Cameras", fmt(Cc.total), fmt(Cc.nHw) + " hardware") + kpi("Online", fmt(Cc.zbx.up + Cc.zbx.other), "") + kpi("Offline", fmt(Cc.zbx.down), "", {cls: Cc.zbx.down ? "warnv" : ""}))}
  ${!hasH ? "" : panel("c3", "Open Handovers", hoOpen.length + " items", hoList(hoOpen.slice(0, 3), true) + go("serahterima", "All handovers"))}
  ${!hasT ? "" : panel("c8", "Tickets In and Closed per Day", ctxTxt(), legend(s1) + bars(dayB(T.daily), s1, {label: "Tickets per day"}))}
  ${N ? panel("c4", "Top 5 Links by Downtime", "", tbl(["Link", "Availability", "Hours"], N.rank.slice(0, 5).map(s => [s.link, pc(s.av, 2), fx(s.down / 3600, 1)]), {r: [1, 2], empty: "No data yet."})) : ""}
  ${N ? panel("c8", "Link Downtime per Day", "", bars(dayB(N.daily), [{name: "Downtime (min)", c: "--crit", v: N.daily.map(x => x.down)}], {dec: 1, unit: " min", label: "Daily downtime"})) : ""}
  ${hasW ? wifiPanels(Wf).apdown() + wifiPanels(Wf).trend() : ""}
  ${R && R.hasData ? panel("c8", "NDR · Critical and High per Day", "Palo Alto events", legend([{name: "Critical", c: "--crit"}, {name: "High", c: "--serious"}]) + bars(dayB(R.daily), [{name: "Critical", c: "--crit", v: R.daily.map(x => x.critical)}, {name: "High", c: "--serious", v: R.daily.map(x => x.high)}], {stack: true, label: "Critical and high"})) : ""}
  ${R && R.hasData ? panel("c4", "NDR · Severity", "", tbl(["Severity", "Events", "Blocked"], R.sev.map(x => [x.k, x.n, pc(x.blkPct, 0)]), {r: [1, 2]})) : ""}
  ${hasX ? xdrPanels(Xd).daily() + xdrPanels(Xd).sev() : ""}
  ${wg("dev-map:NETWORK-SDWAN")}
</div>`;
}
function onDuty(n) {
  const g = teamOn(n.date, n.shift), c = crew(g);
  return `<div class="duty-card"><div class="big"><span class="code ${SC[n.shift]}">${SC[n.shift]}</span><div><b>Shift ${SN[n.shift]} · Team ${g}</b><span class="sub">Next: ${SN[n.shift % NS + 1]} · Team ${teamOn(n.shift === NS ? addDays(n.date, 1) : n.date, n.shift % NS + 1)}</span></div></div>
  <ul class="plist">${c.map(p => `<li><span>${esc(p.name)}<span class="sub"> · ${esc(p.job.replace("ITOC ", ""))}</span></span><span class="num sub">${esc(p.phone)}</span></li>`).join("")}</ul></div>`;
}
function hoList(L, compact) {
  if (!L.length) return `<div class="empty sm">No handovers for this filter.</div>`;
  return `<ul class="ho">${L.map(h => `<li class="${h.open ? "" : "done"}"><div class="tx"><div><span class="pr ${prTone(h.prio)}">${h.prio}</span> <span class="tag">${h.cat}</span> ${esc(h.title)}</div>
    <div class="meta">${dtime(h.at)} · Shift ${SN[h.shift]} → ${SN[h.shift % NS + 1]} · ${esc(h.site)}${h.ticket ? " · ticket #" + esc(h.ticket) : ""} · ${esc(h.by)}</div>
    ${compact ? "" : `<div class="body">${esc(h.body)}</div>${h.next ? `<div class="next"><b>Follow-up:</b> ${esc(h.next)}</div>` : ""}${h.open ? "" : `<div class="next"><b>Closed</b> ${esc(h.closedBy)} · ${dtime(h.closedAt)}: ${esc(h.closeNote)}</div>`}
    ${S.closing === h.id ? `<div class="closebox"><label for="cn">Closing Note (required)</label><textarea id="cn" placeholder="What was the outcome?"></textarea><div class="acts"><button class="btn" data-close-ok="${h.id}">Close Handover</button><button class="btn ghost" data-close-cancel>Cancel</button><span class="msg err" id="cnmsg"></span></div></div>` : ""}`}
    </div>${!compact && h.open && S.closing !== h.id ? `<button class="btn ghost" data-close="${h.id}">Close…</button>` : ""}</li>`).join("")}</ul>`;
}

/* ---------- Service Desk ---------- */
function vSD() {
  const T = tkR(), Tp = S.cmp ? tkR(prevRange()) : null, s1 = [{name: "Tickets In", c: "--s1", v: T.daily.map(x => x.in)}, {name: "Tickets Closed", c: "--s2", v: T.daily.map(x => x.done)}];
  if (!T.n) return `<div class="grid"><section class="panel c12">${empty()}</section></div>`;
  const dimRows = T.dims[S.dim].map(x => [x.k, x.n, pc(x.pct), x.done, x.open, x.avg, x.med, x.zero, x.in, x.out, pc(x.inPct)]);
  const rk = T.ranking.filter(x => x.n > 0 || !S.site).map(x => [x.rank, x.name, {h: x.unit ? `<span class="tag">${esc(x.unit)}</span>` : ""}, x.n, pc(x.share), x.done, x.open, x.avg, x.med, pc(x.zeroPct, 0), pc(x.inPct), x.high, pc(x.okPct, 0), x.loc]);
  const hrs = [...Array(24).keys()].map(h => ({label: pad(h), full: "Pukul " + pad(h) + ".00–" + pad(h) + ".59 · shift " + SN[shiftOf(h)]}));
  return insArea("servicedesk") + `<div class="kpis k6">${kpi("Tickets In", fmt(T.n), fx(T.perDay, 1) + " per day", {tip: RUMUS.tkIn, dl: Tp ? delta(T.n, Tp.n) : ""})}${kpi("Completion Rate", pc(T.doneRate), fmt(T.open) + " still open", {tip: RUMUS.tkDone, dl: Tp ? delta(T.doneRate, Tp.doneRate, {up: true, pct: 1}) : ""})}${kpi("Within SLA Target", pc(T.slaPct), fmt(T.slaIn) + " within, " + fmt(T.slaOut) + " over", {tip: RUMUS.tkSla, dl: Tp ? delta(T.slaPct, Tp.slaPct, {up: true, pct: 1}) : ""})}${kpi("Median Duration", fx(T.medMin, 0) + " min", "average " + fx(T.avgH, 1) + " h, P90 " + fx(T.p90, 1) + " h", {tip: RUMUS.tkMed, dl: Tp ? delta(T.medMin, Tp.medMin, {up: false}) : ""})}${kpi("0-Minute Duration", fmt(T.zero), pc(T.n ? T.zero / T.n : 0) + " of total")}${kpi("Incomplete Input", fmt(T.incomplete), pc(T.n ? T.incomplete / T.n : 0) + " of total")}</div>
  <div class="grid">${panel("c8", "Daily Trend", ctxTxt() + (T.doneAfter ? " · " + T.doneAfter + " tickets closed after the period" : ""), legend(s1) + bars(dayB(T.daily), s1, {label: "Daily ticket trend"}))}
  ${panel("c4", "Resolution Duration Distribution", "", hbars(T.durasi.map(x => [x.k, x.n, 0, fmt(x.n) + " · " + pc(x.pct, 0)])))}
  ${panel("c7", "Tickets per Hour", T.peakHour != null ? "Busiest hour " + pad(T.peakHour) + ".00" : "", bars(hrs, [{name: "Tickets In", c: "--s1", v: T.hours}], {label: "Tickets per hour"}))}
  ${panel("c5", "Per Weekday", "Weekdays " + fx(T.perWorkday, 1) + "/day, weekends " + fx(T.perWeekend, 1), tbl(["Day", "Tickets", "Days counted", "Average/day"], T.weekday.map(x => [x.k, x.n, x.days, fx(x.avg, 1)]), {r: [3]}))}
  ${panel("c12", `Breakdown by <select class="pick" id="dim" aria-label="Dimension">${Object.entries(DIMS).map(([k, v]) => `<option value="${k}" ${k === S.dim ? "selected" : ""}>${v[0]}</option>`).join("")}</select>`, "", tbl([DIMS[S.dim][0], "Count", "% of total", "Closed", "Open", "Average", "Median", "0 min", "Within target", "Over target", "% within target"], dimRows, {tall: true, r: [2, 10]}))}
  ${panel("c12", "Group Ranking", "", tbl(["#", "Group", "Members", "Tickets", "% of list", "Closed", "Open", "Average (h)", "Median (h)", "% within target", "High"], (T.groupRanking || []).map(x => [x.rank, x.name, x.members, x.n, pc(x.share), x.done, x.open, x.avg, x.med, pc(x.inPct), x.high]), {r: [3, 4, 5, 6, 7, 8, 9, 10]}))}
  ${panel("c12", "Technician Ranking", "", tbl(["#", "Name", "Unit", "Tickets", "% of list", "Closed", "Open", "Average (h)", "Median (h)", "% 0 min", "% within target", "High", "% complete input", "Main location"], rk, {tall: true, r: [4, 9, 10, 12]}))}
  ${panel("c12", "Open Tickets", "", tbl(["Subject", "ID", "Location", "Category", "Technician", "Priority", "Status", "Created", "Age (days)"], T.openList.map(x => [x.subj, x.id, x.loc, x.cat, x.tech, x.prio, x.status, dtime(x.created), {h: `<span class="${x.age > 3 ? "crit-t" : ""}">${fx(x.age, 1)}</span>`}]), {r: [8], empty: "No open tickets."}))}
  ${panel("c7", "Data Quality Notes", "", tbl(["Check", "Tickets", "% of total"], T.quality.map(x => [x.k, x.n, pc(x.pct)]), {r: [2]}))}
  ${panel("c5", "Top Requesters", "", tbl(["Requester", "Tickets", "% of total"], T.requesters.map(x => [x.k, x.n, pc(x.pct)]), {r: [2]}))}
  ${panel("c12", "25 Longest-Duration Tickets", "", tbl(["Subject", "ID", "Location", "Category", "Technician", "Priority", "Created", "Duration (days)", "Pattern"], T.longest.map(x => [x.subj, x.id, x.loc, x.cat, x.tech, x.prio, dtime(x.created), fx(x.days, 1), x.pola]), {tall: true, r: [7]}))}</div>`;
}

/* ---------- NOC ---------- */
function vNoc() {
  const B = netB(), N = netR(); if (!N) return `<div class="grid"><section class="panel c12">${empty()}</section></div>`;
  const Np = S.cmp ? netR(prevRange()) : null, P = N.P, hr0 = B.hourly, tot = !!hr0.ttot && !hr0.tin.some(v => v > 0), hr = tot ? {k: hr0.k, tin: hr0.ttot, tout: hr0.tout} : hr0, long = hr.k.length > 24 * 8;
  let lb, vin, vout;
  if (long) { const by = {}; hr.k.forEach((t, j) => { const d = iso(t), o = by[d] || (by[d] = {i: 0, o: 0, n: 0}); o.i += hr.tin[j]; o.o += hr.tout[j]; o.n++; }); const ks = Object.keys(by).sort(); lb = ks.map(d => ({label: dmon(d), full: dlong(d) + " (daily average)"})); vin = ks.map(d => by[d].i / by[d].n); vout = ks.map(d => by[d].o / by[d].n); }
  else { lb = hr.k.map(t => ({label: new Date(t).getUTCHours() === 0 || hr.k.length <= 24 ? (hr.k.length <= 24 ? pad(new Date(t).getUTCHours()) + ".00" : dmon(iso(t))) : "", full: dtime(t) + " WIB"})); vin = [...hr.tin]; vout = [...hr.tout]; }
  const pk = Math.max(...hr.tin), pkO = Math.max(...hr.tout), avI = hr.tin.reduce((a, b) => a + b, 0) / (hr.k.length || 1), avO = hr.tout.reduce((a, b) => a + b, 0) / (hr.k.length || 1);
  const top = [...B.N.sensors].sort((a, b) => tot ? b.avg - a.avg : b.avgIn - a.avgIn).slice(0, 10);
  const sid = V.sensor_id, ss = V.sensor_series, sMeta = B.N.sensors.find(s => s.id === sid) || {};
  const sb = ss ? ss.t.map(t => ({label: "", full: dtime(t) + " WIB"})) : [];
  if (ss) { const step = Math.ceil(ss.t.length / 10); ss.t.forEach((t, i) => { if (i % step === 0) sb[i].label = ss.t.length <= 24 ? pad(new Date(t).getUTCHours()) + ".00" : dmon(iso(t)); }); }
  const marks = ss ? ss.d.map((d, i) => d > 0 ? i : -1).filter(i => i >= 0) : [];
  const tr = tot ? [{name: "Total Traffic", c: "--s1", v: vin}] : [{name: "Traffic In", c: "--s1", v: vin}, {name: "Traffic Out", c: "--s2", v: vout}];
  const um = (N.unmappedIsp || []).length ? `<div class="grid">${panel("c12", "Links Not Matching Any ISP", "", `<ul class="att"><li class="warn"><span>${N.unmappedIsp.map(esc).join(", ")} · add a keyword in Admin → Data Sources → Mapping → ISP</span></li></ul>`)}</div>` : "";
  return um + insArea("noc") + `<div class="kpis k6">${kpi("Availability", pc(N.avail, 2), "target " + pc(P.target, 1), {tip: RUMUS.av, dl: Np ? delta(N.avail, Np.avail, {up: true, pct: 1}) : "", cls: N.avail < P.target ? "warnv" : ""})}${kpi("Links Meeting SLA", N.ok + " of " + (N.ok + N.bad), N.bad + " not met, " + N.nodata + " no data", {tip: RUMUS.link})}${kpi("Total Downtime", fx(N.downH, 1) + " h", N.events + " incidents · " + N.noDown + " links with no downtime", {tip: RUMUS.down, dl: Np ? delta(N.downH, Np.downH, {up: false}) : ""})}${kpi("Data Coverage", pc(N.cov), "")}${(tot ? kpi("Peak Traffic", fx(pk, 1) + " Mbit/s", "average " + fx(avI, 1) + " · total In + Out, from daily reports") : kpi("Peak Traffic In", fx(pk, 1) + " Mbit/s", "average " + fx(avI, 1) + " · Out peak " + fx(pkO, 1)))}${kpi("High Peak Utilization", fmt(N.utilHigh), "links ≥ " + pc(P.utilPeak, 0) + " of capacity", {tip: RUMUS.util})}</div>
  <div class="grid">${panel("c8", "Total Traffic In and Out (Mbit/s)", ctxTxt() + (long ? " · daily average" : " · hourly average"), legend(tr) + lines(lb, tr, {unit: " Mbit/s", label: "Total traffic"}))}
  ${panel("c4", "Top 10 Links by Traffic", tot ? "Average Mbit/s (total)" : "Average Mbit/s, In and Out", (tot ? "" : legend([{name: "In", c: "--s1"}, {name: "Out", c: "--s2"}])) + (tot ? hbars(top.map(s => [s.dev.replace("Branch ", "") + " – " + (s.name.split(" - ")[1] || s.name).replace(" Traffic", ""), s.avg, 0, fx(s.avg, 1) + " Mbit/s"])) : hbars(top.map(s => [s.dev.replace("Branch ", "") + " – " + (s.name.split(" - ")[1] || s.name).replace(" Traffic", ""), s.avgIn, s.avgOut, fx(s.avgIn, 1) + " / " + fx(s.avgOut, 1)]), {two: true})))}
  ${panel("c12", `Traffic per sensor: <select class="pick" id="sensor" aria-label="Sensor">${B.N.sensors.map(s => `<option value="${s.id}" ${s.id === sid ? "selected" : ""}>${esc(s.dev + " – " + s.name)}</option>`).join("")}</select>`, sMeta.cap ? "Capacity " + sMeta.cap + " Mbit/s · red area = hours with downtime" : "", ss ? legend((tot ? [{name: "Total", c: "--s1"}] : [{name: "In", c: "--s1"}, {name: "Out", c: "--s2"}]).concat([{name: "Has downtime", c: "--crit"}])) + lines(sb, tot ? [{name: "Total", c: "--s1", v: ss.a}] : [{name: "In", c: "--s1", v: ss.i}, {name: "Out", c: "--s2", v: ss.o}], {unit: " Mbit/s", thin: true, marks, label: "Sensor traffic", w: 1200, h: 260}) : empty())}
  ${panel("c8", "Daily Downtime", "", bars(dayB(N.daily), [{name: "Downtime", c: "--crit", v: N.daily.map(x => x.down)}], {dec: 1, unit: " min", label: "Daily Downtime"}))}
  ${panel("c4", "Link Availability Distribution", "", tbl(["Kelompok", "Link", "% link"], N.buckets.map(x => [x.k, x.n, pc(x.pct, 0)]), {r: [2]}))}
  ${panel("c12", "Summary per ISP", "", tbl(["ISP", "Links", "Availability", "Downtime (h)", "Target", "Met", "Not met", "No data", "% met", "Traffic (Mbit/s)", "Volume (GB)"], N.isp.map(x => [x.k, x.n, pc(x.av, 3), x.downH, pc(x.target, 1), x.ok, x.bad, x.nodata, pc(x.okPct, 0), x.mbps, x.volGB]), {r: [2, 4, 8]}))}
  ${panel("c12", "Link Ranking by Downtime", "No data when coverage < " + pc(P.minCov, 0), tbl(["#", "Link", "Availability", "Downtime (h)", "Target", "SLA Status", "Margin (+) / over (−) min", "Coverage", "Average (Mbit/s)", "Peak (Mbit/s)", "Sensor"], N.rank.map(s => [s.rank, s.link, pc(s.av, 3), s.down / 3600, pc(s.target, 1), stPill(s.status), s.sisa, pc(s.cov, 0), s.avg, s.max, s.id]), {tall: true, r: [2, 4, 7]}))}
  ${panel("c12", "Summary per Location", N.sameYes + " of " + N.sameCmp + " locations with dual links went down together (within " + CFG.params["net.same_tolerance_min"] + " min): a sign of a site-side fault", tbl(["Location", "Links", "Downtime (min)", "Longest link", "Shortest link", "Lowest availability", "Met", "Not met", "No data", "Down together?"], N.lokasi.map(x => [x.k, x.n, x.downMin, x.maxMin, x.minMin, pc(x.minAv, 3), x.ok, x.bad, x.nodata, x.same]), {tall: true, r: [5]}))}
  ${panel("c5", "20 Longest Downtime Events", N.events + " incidents in the filter", tbl(["Link", "Start", "End", "Minutes"], N.kej.map(k => [k.link, dtime(k.start), dtime(k.end), k.min]), {tall: true}))}
  ${panel("c7", "Capacity Utilization", "Peak ≥ " + pc(P.utilPeak, 0) + " or average ≥ " + pc(P.utilAvg, 0) + " is flagged", tbl(["Link", "Capacity", "Average", "Peak", "Avg. util.", "Peak util.", "Status"], N.util.map(s => [s.link, s.cap, s.avg, s.max, pc(s.uA, 0), pc(s.uP, 0), {h: s.ust === UST.ok ? pill("good", UST.ok) : pill("warn", s.ust)}]), {tall: true, r: [4, 5]}))}</div>`;
}

/* ---------- SOC (needs validation) ---------- */
const CST = {ok: ["ok", "Validated"], dup: ["dup", "In 2 batches (latest used)"], bad: ["bad", "Unreadable"], miss: ["miss", "Not uploaded"], wait: ["wait", "Today, not due yet"]};
function covStrip(chk) { return `<div class="cov">${chk.map(x => `<span class="c ${CST[x.s][0]}" data-tip="${esc(dlong(x.d) + "\n" + CST[x.s][1] + (x.b ? "\nBatch " + x.b : ""))}">${new Date(dayMs(x.d)).getUTCDate()}</span>`).join("")}</div>
  <div class="legend">${[["ok", "Validated"], ["dup", "Duplicate, latest used"], ["bad", "Unreadable"], ["miss", "Not uploaded"]].map(([k, l]) => `<span><b class="c ${k}"></b>${l}</span>`).join("")}</div>`; }
const fwB = n => n >= 1e12 ? fx(n / 1e12, 2) + " TB" : fx(n / 1e9, 1) + " GB";
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
function socFwVal(F, R) {
  const cut = n => n.replace(/^SPMT-/, "").replace(/-(PA|FW)[-\d].*$/, ""), late = F.fw.filter(x => x.tfrom && x.tfrom > S.from), none = F.fw.filter(x => !x.tfrom);
  const diff = R && !S.site && F.dayN === F.span && R.total ? Math.abs(F.total.events - R.total) / R.total : null;
  const rows = [
    [F.dayN === F.span ? "good" : "warn", `Days with firewall data: ${F.dayN} of ${F.span}`, F.dayN < F.span && F.from ? `Collected since ${dfull(F.from)}; older days are filled in on every Panorama sync.` : ""],
    [late.length || none.length ? "warn" : "good", "Traffic data per firewall", late.length || none.length ? [...late.map(x => `${esc(cut(x.fw))} from ${dmon(x.tfrom)}`), ...none.map(x => `${esc(cut(x.fw))} none`)].join(", ") + ". Panorama has no traffic summary for these firewalls before that date." : "Every firewall has traffic for the whole period"],
    ...(diff == null ? [] : [[diff < 0.05 ? "good" : "warn", "Firewall events against the all-location summary", `${fmt(F.total.events)} against ${fmt(R.total)} (${pc(diff, 1)} difference)`]])];
  return panel("c12", "Firewall Data Validation", S.site || "all locations", `<ul class="checks">${rows.map(c => `<li>${pill(c[0], "")}<div><b>${c[1]}</b>${c[2] ? `<span>${c[2]}</span>` : ""}</div></li>`).join("")}</ul>`);
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
const avHue = s => { let h = 0; for (const c of String(s)) h = (h * 31 + c.charCodeAt(0)) % 360; return h; };
const initials = n => String(n).replace(/[^A-Za-z ]/g, "").split(" ").filter(Boolean).map(w => w[0]).slice(0, 2).join("").toUpperCase() || "?";
const telHref = p => "tel:" + String(p).replace(/[^+\d]/g, "");
const pav = (n, sm) => `<span class="pav ${sm ? "sm" : ""}" style="--h:${avHue(n)}">${esc(initials(n))}</span>`;
const pcard = p => `<article class="pcard" data-q="${esc(((p.name || "") + " " + (p.job || "") + " " + (p.branch || "")).toLowerCase())}">${pav(p.name)}<div class="pb"><b>${esc(p.name)}</b><span class="sub">${esc((p.job || "").replace(/^ITOC /, ""))}${p.branch ? " · " + esc(p.branch) : ""}</span></div>${p.phone ? `<a class="pph" href="${esc(telHref(p.phone))}">${esc(p.phone)}</a>` : ""}</article>`;
/* When an off team starts again: "Off · back Mon 26 Oct · Pagi" */
function backOn(g, now) {
  for (let d = addDays(now.date, 1), i = 0; i < 14; d = addDays(d, 1), i++) { const c = codeOf(g, d); if (c !== OFF) return `Off · back ${HR[new Date(dayMs(d)).getUTCDay()].slice(0, 3)} ${dmon(d)} · ${esc(SN[c + 1])}`; }
  return "Off";
}
function vJadwal() {
  /* Personnel menu (no filters). Sub-menu = parameter "personel" (Admin → Operations → Targets & Parameters): each group has kind shift | office | branch. */
  const now = nowShift(), gs = GROUPS, G = gs.find(g => g.key === S.pers) || gs[0];
  if (!G) return `<div class="grid"><section class="panel c12">${empty("No personnel groups yet. Set the personnel parameter in Admin.")}</section></div>`;
  const bar = `<div class="subtabs">${gs.map(g => `<button type="button" data-pers="${esc(g.key)}" aria-selected="${g.key === G.key}">${esc(g.label)}</button>`).join("")}</div>`;
  const group = CFG.people.filter(p => p.unit === G.unit), person = p => `<li><span>${esc(p.name)}<span class="sub"> · ${esc((p.job || "").replace(/^ITOC /, ""))}</span></span><span class="num sub">${esc(p.phone || "")}</span></li>`;
  let body = "";
  if (G.kind === "shift") {
    const ym = S.schedM || now.today.slice(0, 7), first = ym + "-01", mEnd = iso(Date.UTC(+ym.slice(0, 4), +ym.slice(5, 7), 0)), days = [];
    for (let d = first; d <= mEnd; d = addDays(d, 1)) days.push(d);
    const head = `<div class="h"></div>` + days.map(d => `<div class="h ${d === now.date ? "today" : ""}">${new Date(dayMs(d)).getUTCDate()}<br>${HR[new Date(dayMs(d)).getUTCDay()]}</div>`).join("");
    const rows = TEAMS.map(g => `<div class="tn">Team ${g}</div>` + days.map(d => { const c = codeOf(g, d), k = CODES[c]; return `<div class="c ${k} ${d === now.date && c === now.shift - 1 ? "today" : ""}" data-tip="${esc("Team " + g + " · " + dlong(d) + "\n" + (k === OFFC ? "Off" : "Shift " + SN[c + 1] + " " + shiftHours(c + 1)))}">${k}</div>`; }).join("")).join("");
    body = `<div class="grid">${panel("c12", "Lead & Supervisor", "", `<div class="pcards">${group.filter(p => !p.team_code).map(pcard).join("") || `<div class="sub">No data yet.</div>`}</div>`)}
    ${panel("c4", "On Duty", dlong(now.date) + " · " + now.clock + " WIB", onDuty(now))}
    ${panel("c8", "Shift Schedule " + esc(G.label), "", `<div class="scroll"><div class="sched" style="grid-template-columns:72px repeat(${days.length},minmax(30px,1fr))">${head}${rows}</div></div>
      <div class="legend">${[...CFG.shifts.map(x => [x.code, x.name + " " + shiftHours(x.no)]), [OFFC, "Off"]].map(([k, l]) => `<span><b class="sw ${k}"></b>${l}</span>`).join("")}</div>`, `<span class="acts monthnav"><button type="button" class="btn ghost sm" data-sm="-1" aria-label="Previous month">‹</button><b class="num">${rangeMonth(first)}</b><button type="button" class="btn ghost sm" data-sm="1" aria-label="Next month">›</button>${ym !== now.today.slice(0, 7) ? `<button type="button" class="btn ghost sm" data-sm="0">Today</button>` : ""}</span>`)}
    ${TEAMS.map(g => { const c = codeOf(g, now.date); return panel("c3 shcard " + (c === OFF ? "sh-off" : "sh" + c), "Team " + g, c === OFF ? `<span class="shb"><i></i>${backOn(g, now)}</span>` : `<span class="shb"><i></i>${esc(SN[c + 1])}</span>`, `<ul class="plist">${crew(g).map(person).join("")}</ul>`); }).join("")}
    </div>`;
  } else if (G.kind === "office") {
    const dow = new Date(dayMs(now.today)).getUTCDay(), open = (G.days || []).includes(dow) && now.clock >= G.start && now.clock < G.end;
    body = `<div class="grid">${panel("c12", esc(G.label), "",
      `<div class="hchips">${(CFG.params["report.contact"] || {}).phone ? `<a class="hchip link" href="${esc(telHref(CFG.params["report.contact"].phone))}"><i></i>${esc(CFG.params["report.contact"].phone)}</a>` : ""}${(CFG.params["report.contact"] || {}).email ? `<a class="hchip link" href="mailto:${esc(CFG.params["report.contact"].email)}"><i></i>${esc(CFG.params["report.contact"].email)}</a>` : ""}</div>` +
      (group.length ? `<div class="pcards">${group.map(pcard).join("")}</div>` : `<div class="empty sm">No members yet.</div>`))}</div>`;
  } else {
    const by = new Map(); group.forEach(p => { const k = p.branch || "Shared"; if (!by.has(k)) by.set(k, []); by.get(k).push(p); });
    const ord = k => { const i = CFG.sites.indexOf(k); return i < 0 ? 999 : i; }, ob = V.open_by_site || {}, totOpen = [...by.keys()].reduce((a, k) => a + (ob[k] || 0), 0);
    const cards = [...by.entries()].sort((a, b) => ord(a[0]) - ord(b[0])).map(([k, ps]) => { const o = ob[k] || 0, tone = o === 0 ? "good" : o < 5 ? "warn" : "crit";
      return `<article class="bcard pcard" data-q="${esc((k + " " + ps.map(p => p.name).join(" ")).toLowerCase())}"><header><b>${esc(k.replace(/^Branch /, ""))}</b><span class="obadge ${tone}" title="Open tickets at this branch">${o} open</span></header>${ps.map(p => `<div class="brow">${pav(p.name, 1)}<span class="pb"><b>${esc(p.name)}</b></span>${p.phone ? `<a class="pph" href="${esc(telHref(p.phone))}">${esc(p.phone)}</a>` : ""}</div>`).join("")}</article>`; }).join("");
    body = `<div class="grid">${panel("c12", esc(G.label), `<span class="hchips"><span class="hchip"><i></i>${by.size} locations</span><span class="hchip"><i></i>${group.length} people</span><span class="hchip ${totOpen ? "warn" : ""}"><i></i>${totOpen} open tickets</span></span>`, `<input type="search" id="mq" class="msearch" placeholder="Search name or location" aria-label="Search"><div class="bcards">${cards || `<div class="empty sm">No members yet.</div>`}</div>`)}</div>`;
  }
  return bar + body;
}const rangeMonth = d => MB[+d.slice(5, 7) - 1] + " " + d.slice(0, 4);
/* ---------- Handover ---------- */
function vHo() { return subnav("report") + vHoBody(); }
function vHoBody() {
  const inF = h => h.date >= S.from && h.date <= S.to && (!S.sf || h.shift === S.sf) && (!S.site || h.site === S.site);
  const L = (V.handover || []).filter(h => inF(h) && (S.hoSt === "all" || (S.hoSt === "open") === h.open)).sort((a, b) => b.at - a.at);
  const now = nowShift(), nx = now.shift % NS + 1, openT = V.open_tickets || [];
  const form = `<form id="hoF" class="form" novalidate>
    <div class="fld"><label>From</label><div class="ro">Shift ${SN[now.shift]} · Team ${teamOn(now.date, now.shift)}</div></div>
    <div class="fld"><label>To</label><div class="ro">Shift ${SN[nx]} · Team ${teamOn(now.shift === NS ? addDays(now.date, 1) : now.date, nx)}</div></div>
    <div class="fld"><label for="hCat">Category *</label><select id="hCat" required><option value="">Select…</option>${CFG.params["ho.categories"].map(x => `<option>${esc(x)}</option>`).join("")}</select></div>
    <div class="fld"><label for="hPr">Priority *</label><select id="hPr" required><option value="">Select…</option>${CFG.params["ho.priorities"].map(x => `<option>${esc(x.value)}</option>`).join("")}</select></div>
    <div class="fld"><label for="hSite">Location *</label><select id="hSite" required><option value="">Select…</option>${CFG.sites.map(s => `<option ${s === S.site ? "selected" : ""}>${esc(s)}</option>`).join("")}</select></div>
    <div class="fld"><label for="hTk">Related Ticket</label><select id="hTk"><option value="">None</option>${openT.map(t => `<option value="${esc(t.id)}">#${esc(t.id)} · ${esc(String(t.subject).slice(0, 48))}</option>`).join("")}</select></div>
    <div class="fld wide"><label for="hTitle">Judul * <span class="sub">min. ${CFG.params["ho.rules"].min_title} karakter</span></label><input type="text" id="hTitle" maxlength="120" placeholder="Contoh: Link Astinet Meulaboh down, menunggu ISP"></div>
    <div class="fld wide"><label for="hBody">Situation and actions taken * <span class="sub">min. ${CFG.params["ho.rules"].min_body} characters</span></label><textarea id="hBody" placeholder="What happened, since when, who it was escalated to"></textarea></div>
    <div class="fld wide"><label for="hNext">Follow-up for Next Shift</label><input type="text" id="hNext" placeholder="What should be checked or done"></div>
    <div class="acts wide"><button class="btn" type="submit">Save Handover</button><button class="btn ghost" type="button" data-hoform="0">Cancel</button><span class="msg err" id="hMsg"></span></div></form>`;
  return `<div class="grid">${panel("c12", "Hand Over Shift", ctxTxt(), `<div class="toolbar"><div class="seg" id="hoSt">${[["open", "Open"], ["closed", "Closed"], ["all", "All"]].map(([k, l]) => `<button type="button" data-ho="${k}" aria-pressed="${S.hoSt === k}">${l}</button>`).join("")}</div>${S.hoForm ? "" : `<button class="btn" data-hoform="1">+ New Handover</button>`}</div>${S.msg ? `<div class="msg ok">${esc(S.msg)}</div>` : ""}${S.hoForm ? `<div class="formbox">${form}</div>` : ""}${hoList(L)}`)}</div>`;
}

/* ---------- Data (completeness + RAW upload) ---------- */
const canUp = k => { const u = CFG.me.uploads || []; return u.includes("*") || u.includes(k); };
function upCards() {
  const C = [
    ["soc", "Cyber Security · Panorama", "Panorama CSV, multiple files or .zip", "upf", ".csv,.zip", true, "Choose CSV / ZIP", "upmsg"],
    ["tickets", "Ticketing · ManageEngine", "Ekspor ManageEngine .xls / .xlsx", "upt", ".xls,.xlsx", false, "Choose XLS / XLSX", "upmsg2"],
    ["prtg", "Networking · PRTG", "PRTG daily report PDF, multiple files or .zip", "upn", ".pdf,.zip", true, "Choose PDF / ZIP", "upmsg3"]
  ].filter(c => canUp(c[0]));
  if (!C.length) return `<div class="empty sm">No upload permission.</div>`;
  return `<div class="uploads">${C.map(([, ttl, hint, id, acc, multi, btn, msg]) => `<div class="drop"><b>${ttl}</b><span class="sub">${hint}</span><label class="btn upbtn" for="${id}">${btn}</label><input type="file" id="${id}" accept="${acc}" ${multi ? "multiple" : ""} class="vh"><div id="${msg}"></div></div>`).join("")}</div>`;
}
function vData() { return subnav("report") + vDataBody(); }
function vDataBody() {
  const days = []; for (let d = S.from; d <= S.to && days.length < 62; d = addDays(d, 1)) days.push(d);
  const rows = (V.coverage || []).map(r => [esc(r.label), d => r.cells[d] || ["wait", "–"]]);
  const grid = `<div class="scroll"><div class="mx" style="grid-template-columns:minmax(150px,220px) repeat(${days.length},minmax(22px,1fr))"><div></div>${days.map(d => `<div class="h">${new Date(dayMs(d)).getUTCDate()}</div>`).join("")}
    ${rows.map(([l, f]) => `<div class="rl">${l}</div>` + days.map(d => { const [k, t] = f(d); return `<span class="c ${k}" data-tip="${esc(dlong(d) + "\n" + t)}"></span>`; }).join("")).join("")}</div></div>
    <div class="legend">${[["ok", "Complete"], ["dup", "Complete with notes"], ["bad", "Failed / incomplete"], ["miss", "None"], ["wait", "Not due yet"]].map(([k, l]) => `<span><b class="c ${k}"></b>${l}</span>`).join("")}</div>`;
  const bl = (V.batches || []).slice().reverse().map(b => [b.file, dmon(b.from) + " – " + dmon(b.to), b.by, dtime(b.at), b.rows, b.skipped, {h: b.issues.some(i => i.k === "crit") ? pill("crit", "Failed, not used") : b.issues.length ? pill("warn", "Used, with notes") : pill("good", "Valid")}, {h: b.issues.map(i => `<div class="sub">${esc(i.t)}</div>`).join("") || "–"}]);
  return `<div class="grid">${panel("c12", "Data Completeness per Day", ctxTxt(APPLY.kelengkapan), grid)}
  ${panel("c12", "Raw Data Upload", "", upCards())}  ${panel("c12", "Sync and Upload Log", (canUp("tickets") || canUp("prtg") || canUp("soc")) ? `<span class="acts">${canUp("tickets") ? `<button class="btn ghost" data-sync="manageengine">Sync ManageEngine</button>` : ""}${canUp("prtg") ? `<button class="btn ghost" data-sync="prtg">Sync PRTG</button>` : ""}${canUp("soc") ? `<button class="btn ghost" data-sync="panorama">Pull Panorama now</button>` : ""}</span>` : "Newest first", tbl(["Time", "Source", "Status", "Rows", "Message"], (V.sync_log || []).slice(0, 12).map(x => [dtime(x.at), x.src, {h: x.ok ? pill("good", "OK") : pill("crit", "Failed")}, x.rows, x.msg]), {tall: true}))}
  ${panel("c12", "SOC Upload History", "", tbl(["File", "Period", "Uploaded by", "Time", "Rows read", "Skipped", "Status", "Notes"], bl))}</div>`;
}

/* ---------- Report (Excel / PDF / PowerPoint download) ---------- */
const fk = (v, k) => v == null || v === "" ? "–" : k === "n" ? fmt(v) : /^f\d$/.test(k) ? fx(v, +k[1]) : /^p\d$/.test(k) ? pc(v, +k[1]) : esc(v);
function vReport() {
  const rp = V.report || {sections: [], kinds: []}, kinds = rp.kinds || [], nav = subnav("report");
  if (!kinds.length) return nav + `<div class="grid"><section class="panel c12">${empty("No reports are available to this role.")}</section></div>`;
  if (S.rkind !== "custom" && !kinds.some(k => k.key === S.rkind)) S.rkind = kinds[0].key;
  const kind = S.rkind, avail = rp.avail || [], picked = (S.rsecs || []).filter(x => avail.some(a => a.key === x)), kd = kind === "custom" ? {label: "Custom", desc: "", sections: picked} : kinds.find(k => k.key === kind) || {}, secs = kd.sections || [kind], shown = rp.sections.filter(s => kind === "custom" ? picked.includes(s.key) : kind === "full" || (kind === "summary" ? s.key === "ringkasan" : secs.includes(s.key) || (s.key === "ringkasan" && secs.length > 1)));
  const chips = `<div class="chips rtypes">${kinds.map(k => `<button type="button" class="chip" data-rkind="${esc(k.key)}" aria-pressed="${k.key === kind}" title="${esc(k.desc)}">${esc(k.label)}</button>`).join("")}<button type="button" class="chip" data-rkind="custom" aria-pressed="${kind === "custom"}">Custom…</button></div>${kind === "custom" ? `<div class="rpick">${avail.map(a => `<label class="chk"><input type="checkbox" data-rsec="${esc(a.key)}" ${picked.includes(a.key) ? "checked" : ""}> ${esc(a.label)}</label>`).join("")}</div>` : ""}`;
  const pre = `<div class="chips sm">${[["ringkas", "Compact"], ["standar", "Standard"], ["lengkap", "Full"]].map(([k, l]) => `<button type="button" class="chip" data-rpreset="${k}" aria-pressed="${k === S.rpreset}">${l}</button>`).join("")}</div>`;
  const dl = `<div class="rdl">${[["xlsx", "Excel"], ["pdf", "PDF"], ["pptx", "PowerPoint"]].map(([k, l]) => `<button type="button" class="btn" data-rep="${k}" ${kind === "custom" && !picked.length ? "disabled" : ""}>${l}</button>`).join("")}</div>`;
  const kp = shown.flatMap(s => s.kpis).slice(0, 12), nc = shown.reduce((a, s) => a + s.charts.length, 0), nt = shown.reduce((a, s) => a + s.tables.length, 0);
  const list = (a, n) => a.length ? `<ul>${a.slice(0, n).map(x => `<li>${esc(x.title)}</li>`).join("")}${a.length > n ? `<li class="sub">and ${a.length - n} more</li>` : ""}</ul>` : `<span class="sub">none</span>`;
  const secs2 = shown.map(s => `<div class="rsec"><h4>${esc(s.title)}</h4><span class="lbl">Charts (${s.charts.length})</span>${list(s.charts, 5)}<span class="lbl">Tables (${s.tables.length})</span>${list(s.tables, 5)}</div>`).join("");
  return nav + `<div class="grid">${panel("c12", "Report", ctxTxt(), `${chips}<div class="rmeta"><div class="rdesc"><b>${esc(kd.label || "")}</b><span>${esc(kd.desc || "")}</span></div><div class="rctl"><div class="rgroup"><span class="lbl">Size</span>${pre}</div><div class="rgroup"><span class="lbl">Download</span>${dl}</div></div></div>
    <div class="rkpi2">${kp.map(k => { const p = String(k.label).split(" · "); return `<div class="kpi"><span class="src">${esc(p.length > 1 ? p[0] : "")}</span><span class="lbl">${esc(p.slice(p.length > 1 ? 1 : 0).join(" · "))}</span><span class="v">${fk(k.value, k.kind)}</span><span class="d">${esc(k.sub || "")}</span></div>`; }).join("") || `<div class="empty sm">${kind === "custom" ? "Pick at least one section." : "No data."}</div>`}</div>
    <div class="rsum sub">${pl(shown.length, "section")} · ${pl(nc, "chart")} · ${pl(nt, "table")}</div><div class="rsecs">${secs2}</div>`)}</div>`;
}
/* ---------- Admin ---------- */
function vAdmin() {
  admEnsure();
  let body = "";
  const eu = S.editUser ? (V.users || []).find(x => x.u === S.editUser) : null;
  if (S.adm === "pengguna") body = `${S.msg ? `<div class="msg ok">${esc(S.msg)}</div>` : ""}<div class="toolbar"><button class="btn" data-adduser>+ Add User</button></div>
    ${S.addUser || eu ? `<form id="uF" class="form formbox"><div class="fld"><label for="uU">Username *</label><input id="uU" type="text" value="${eu ? esc(eu.u) : ""}" ${eu ? "readonly" : ""}></div><div class="fld"><label for="uN">Name *</label><input id="uN" type="text" value="${eu ? esc(eu.name) : ""}"></div><div class="fld"><label for="uR">Role *</label><select id="uR" ${eu && eu.u === CFG.me.username ? "disabled" : ""}>${Object.entries(ROLES).map(([k, v]) => `<option value="${k}" ${eu && eu.role === k ? "selected" : ""}>${v}</option>`).join("")}</select></div><div class="fld"><label for="uS">Branch (EOS only)</label><select id="uS"><option value="">–</option>${CFG.sites.map(x => `<option ${eu && eu.site === x ? "selected" : ""}>${esc(x)}</option>`).join("")}</select></div><div class="acts wide"><button class="btn" type="submit">Save</button><button class="btn ghost" type="button" data-adduser>Cancel</button>${eu ? "" : `<span class="sub">The initial password is random and must be changed at first login.</span>`}<span class="msg err" id="uMsg"></span></div></form>` : ""}
    <div class="ucards">${V.users.map(u => `<article class="ucard ${u.active ? "" : "off"}"><span class="av">${esc((u.name || u.u).split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase())}</span><div class="ub"><b>${esc(u.name)}</b><span class="sub">@${esc(u.u)} · ${esc(ROLES[u.role] || u.role)}${u.site ? " · " + esc(u.site) : ""}</span><span class="sub" title="${esc(roleAccess(u.role))}">${u.active ? "Active" : "Inactive"} · last login ${esc(dtime(u.last))}</span></div><span class="acts"><button class="btn ghost" data-edit-user="${esc(u.u)}">Edit</button>${u.u === CFG.me.username ? "" : `<button class="btn ghost" data-toggle-user="${esc(u.u)}">${u.active ? "Disable" : "Enable"}</button><button class="btn ghost" data-reset-user="${esc(u.u)}">Reset</button>`}</span></article>`).join("")}</div>`;
  if (S.adm === "integrasi") body = vIntegrations();
  if (S.adm === "apikeys") body = vApiKeys();
  if (S.adm === "smtp") body = vSmtp();
  if (S.adm === "webhooks") body = vWebhooks();
  if (S.adm === "roles") body = vRoles();
  if (S.adm === "parameter") body = admTitle("Targets & Parameters", "Values used in calculations and display. Changes apply to every page immediately.") + paramForm() + `<h4 class="admsub">SLA Targets</h4>` + masterView("sla_target");
  if (S.adm === "rumus") body = admTitle("Formulas", "Formula descriptions shown in the info tooltips.") + masterView("formula");
  if (S.adm === "pemetaan") body = admTitle("Mapping", "Locations, Zabbix codes, PRTG sensors, and ISPs. New codes from the APIs are registered automatically and need a location or label here.") + masterView(null, ["site", "zbx_loc", "dev_code", "prtg_sensor", "isp"]);
  if (S.adm === "personel") body = admTitle("Personnel", "People and contacts shown on the Personnel page and Overview.") + masterView("person");
  if (S.adm === "tim") body = admTitle("Teams & Shifts", "The rotation pattern is set under Targets & Parameters.") + masterView(null, ["team", "shift"]);
  if (S.adm === "menu") body = admTitle("Menus & Widgets", "Default menu and widget setup. Change with care: every user sees the result.") + masterView(null, ["module", "widget"]);
  if (S.adm === "dilengkapi") body = vTodo();
  if (S.adm === "status") body = vSourceStatus();
  if (S.adm === "akses") body = vAccess();
  if (S.adm === "audit") body = vAudit();
  return `<div class="grid"><section class="panel c12">${admNav()}${body}</section></div>`;
}
