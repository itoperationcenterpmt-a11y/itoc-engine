/* TERA Dashboard: components and page views, reading the API bundle. */
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
  return `<div class="scroll ${o.tall || auto ? "tall" : ""}"><table class="rt"><thead><tr>${heads.map((h, i) => `<th class="${isN[i] ? "r" : ""}">${esc(h)}</th>`).join("")}</tr></thead><tbody>` + rows.map(r => `<tr>${r.map((c, i) => typeof c === "string" && !isN[i] && c.length > 48 ? `<td class="t cut" data-l="${esc(heads[i])}" title="${esc(c)}">${esc(c)}</td>` : `<td class="${isN[i] ? "r num" : "t" + (typeof c === "string" && c.length <= 28 ? " nw" : "")}" data-l="${esc(heads[i])}">${cell(c)}</td>`).join("")}</tr>`).join("") + `</tbody></table></div>` + (auto ? `<div class="sub tcount">${fmt(rows.length)} rows · scroll inside the table to see more</div>` : "");
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
  network: '<circle cx="12" cy="5" r="2.5"/><circle cx="5" cy="19" r="2.5"/><circle cx="19" cy="19" r="2.5"/><path d="M12 7.5v4M12 11.5L6.5 17M12 11.5L17.5 17"/>',
  link: '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
  globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18"/>',
  bulb: '<path d="M9 18h6M10 21h4"/><path d="M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0 0 12 3z"/>',
  router: '<rect x="3" y="13" width="18" height="7" rx="1.5"/><path d="M7 16.5h.01M11 16.5h.01M8 13V9M16 13V9M6 9a8 8 0 0 1 4-3M18 9a8 8 0 0 0-4-3"/>',
  wrench: '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.1L3 17.7 6.3 21l6.3-6.3a4 4 0 0 0 5.1-5.4l-2.4 2.4-2.4-.6-.6-2.4z"/>',
  pulse: '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M7 10h2l1.5-3 2 6 1.5-3h3M9 20h6M12 16v4"/>',
  calendar: '<rect x="3" y="4" width="18" height="17" rx="2"/><path d="M3 9h18M8 2v4M16 2v4"/>'
};
const icon = k => `<svg viewBox="0 0 24 24" aria-hidden="true">${ICO[(MODS[k] || {}).icon] || '<circle cx="12" cy="12" r="4"/>'}</svg>`;const topOf = k => { const p = (MODS[k] || {}).parent; return p && MODS[p] ? p : k; };
/* Sub-menu: a parent page and its children (e.g. Report + Handover) as tabs inside the page */
const SUBSUM = {network: "Summary", cyber: "Summary", devices: "Summary"};
const SUBHIDE = ["serahterima"];                                       /* children that are shown inside their parent page instead of as a tab (Handover, below Personnel > ITOC) */
function subnav(parent) {
  const items = TABS.filter(t => !SUBHIDE.includes(t[0]) && (t[0] === parent || (MODS[t[0]] || {}).parent === parent));
  return items.length < 2 ? "" : `<div class="subtabs">${items.map(([k, l]) => `<a href="#${k}" data-tab="${k}" aria-selected="${k === S.tab}">${esc(k === parent && SUBSUM[parent] ? SUBSUM[parent] : l)}</a>`).join("")}</div>`;
}
/* Running shift clock: called on render and every second so it never freezes. */
/* A KPI strip must not leave one box alone on a second row: the columns follow the number of boxes (--kn), and on narrower screens a divisor of it (--kc, --kb) */
function kpiCols() { $("view").querySelectorAll(".kpis").forEach(k => { const n = k.children.length, c = n <= 6 ? n : Math.ceil(n / 2); k.style.setProperty("--kn", c); k.style.setProperty("--kc", c < 6 ? Math.min(c, 4) : c % 3 === 0 ? 3 : 2); k.style.setProperty("--kb", c % 3 === 0 ? 3 : 2); }); }
function renderDuty() {
  const n = nowShift(), tm = teamOn(n.date, n.shift), d = new Date(nowMs()), hh = pad(d.getUTCHours()), mm = pad(d.getUTCMinutes()), ss = pad(d.getUTCSeconds());
  ["duty", "dutyH"].forEach(id => {
    const e = $(id); if (!e) return;
    if (!e.querySelector(".clk")) e.innerHTML = `<i></i><span><span class="dtxt"></span><small class="clk"><span class="th"></span><b>:</b><span class="tm"></span><b>:</b><span class="ts"></span> WIB</small></span>`;   // structure is built once so the animation does not restart every second
    e.querySelector(".dtxt").textContent = `On duty: Team ${tm} · ${SN[n.shift]}`;
    e.querySelector(".th").textContent = hh; e.querySelector(".tm").textContent = mm; e.querySelector(".ts").textContent = ss;
  });
  $("dutyM").textContent = `Team ${tm} · ${SN[n.shift]} · ${hh}:${mm}`;
}
/* Skeleton placeholder shown in #view while a page's data loads (only when the page changed or the view is empty; a refresh of the same page keeps the old content dimmed). */
function skeletonHtml() {
  const card = (c, rows) => `<section class="panel ${c} skel" aria-hidden="true"><div class="sk sk-title"></div>${Array.from({length: rows}, (_, i) => `<div class="sk sk-line" style="width:${92 - i * 14}%"></div>`).join("")}</section>`;
  return `<div class="grid skel-wrap" role="status" aria-label="Loading"><div class="kpis">${Array.from({length: 4}, () => `<div class="sk sk-kpi"></div>`).join("")}</div>${card("c8", 5)}${card("c4", 4)}${card("c6", 4)}${card("c6", 4)}</div>`;
}
function renderShell(loading) {
  if (loading && (!$("view").innerHTML.trim() || $("view").dataset.tab !== S.tab)) $("view").innerHTML = skeletonHtml();
  const NAVT = TABS.filter(t => topOf(t[0]) === t[0]), curTop = topOf(S.tab);
  /* The pages under a menu item (ISP, WiFi, ...) are listed under it in the sidebar while it is open; on a phone they stay as tabs inside the page */
  const subL = k => { const it = TABS.filter(t => !SUBHIDE.includes(t[0]) && (t[0] === k || (MODS[t[0]] || {}).parent === k)); return it.length < 2 ? "" : it.map(([sk, sl]) => `<a role="tab" class="subl" href="#${sk}" data-tab="${sk}" aria-selected="${sk === S.tab}">${esc(sk === k && SUBSUM[k] ? SUBSUM[k] : sl)}</a>`).join(""); }, SHORT = {cyber: "Cyber"};
  $("tabs").innerHTML = NAVT.map(([k, l, bd]) => `<a role="tab" href="#${k}" data-tab="${k}" title="${esc(l)}" aria-selected="${k === curTop}">${icon(k)}<span>${SHORT[k] ? `<span class="lf">${esc(l)}</span><span class="ls">${SHORT[k]}</span>` : esc(l)}</span></a>${k === curTop ? subL(k) : ""}`).join("");
  $("sheetGrid").innerHTML = NAVT.map(([k, l, bd]) => `<a href="#${k}" data-tab="${k}" aria-selected="${k === curTop}">${icon(k)}<span>${esc(l)}</span></a>`).join("");
  $("moreBtn").classList.toggle("on", NAVT.findIndex(t => t[0] === curTop) > 3);
  const cur = TABS.find(t => t[0] === S.tab), par = (MODS[S.tab] || {}).parent, grp = SUBSUM[S.tab] ? S.tab : (SUBSUM[par] ? par : "");
  $("ptitle").textContent = !cur ? "" : grp ? MODS[grp].label + " · " + (S.tab === grp ? SUBSUM[grp] : cur[1]) : cur[1];
  $("subnav").innerHTML = subnav(curTop);
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
  /* Period and Location stay in view; the other filters fold behind "More filters" until one of them is in use */
  const exIds = ["gKind", "gStat", "gGrp", "gTyp"], exN = exIds.filter(id => !$(id).hidden).length, exUse = !!(ap.k && S.kind || ap.t && S.dstat || ap.g && S.grp || ap.y && S.dtype), exOpen = S.fMore || exUse;
  exIds.forEach(id => $(id).classList.toggle("fx", !exOpen));
  $("fMore").hidden = !exN; $("fMore").disabled = exUse; $("fMore").textContent = exOpen ? "Fewer filters" : "More filters · " + exN; $("fMore").setAttribute("aria-expanded", exOpen);
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
const spark = (v, c) => {
  if (!v || v.length < 2 || !v.some(x => x > 0)) return "";
  const mx = Math.max(...v), pts = v.map((x, i) => (100 * i / (v.length - 1)).toFixed(1) + "," + (20 - x / mx * 18).toFixed(1)).join(" ");
  return `<svg class="spark" viewBox="0 0 100 22" preserveAspectRatio="none" aria-hidden="true"><polyline points="${pts}" fill="none" stroke="var(${c})" stroke-width="1.6" stroke-linejoin="round" vector-effect="non-scaling-stroke"/></svg>`;
};
const stile = (tab, name, tone, head, sub, o = {}) => `<button type="button" class="stile ${tone}" data-go="${tab}"${o.tip ? ` title="${esc(o.tip)}"` : ""}><span class="k">${esc(name)}</span><b>${head}</b><span class="sub">${sub}</span>${o.dl ? `<span class="sub">${o.dl}</span>` : ""}${o.spark || ""}</button>`;
const fold = (title, body) => `<details class="fold"><summary>${title}</summary>${body}</details>`;
const attRow = a => `<li class="${a[0]}"><span>${a[1]}</span>${go(a[2], "View")}</li>`;

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
const fwB = n => n >= 1e12 ? fx(n / 1e12, 2) + " TB" : fx(n / 1e9, 1) + " GB";
const canUp = k => { const u = CFG.me.uploads || []; return u.includes("*") || u.includes(k); };
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
function upCards() {
  const C = [
    ["soc", "Cyber Security · Panorama", "Panorama CSV, multiple files or .zip", "upf", ".csv,.zip", true, "Choose CSV / ZIP", "upmsg"],
    ["tickets", "Ticketing · ManageEngine", "Ekspor ManageEngine .xls / .xlsx", "upt", ".xls,.xlsx", false, "Choose XLS / XLSX", "upmsg2"],
    ["prtg", "Networking · PRTG", "PRTG daily report PDF, multiple files or .zip", "upn", ".pdf,.zip", true, "Choose PDF / ZIP", "upmsg3"]
  ].filter(c => canUp(c[0]));
  if (!C.length) return `<div class="empty sm">No upload permission.</div>`;
  return `<div class="uploads">${C.map(([, ttl, hint, id, acc, multi, btn, msg]) => `<div class="drop"><b>${ttl}</b><span class="sub">${hint}</span><label class="btn upbtn" for="${id}">${btn}</label><input type="file" id="${id}" accept="${acc}" ${multi ? "multiple" : ""} class="vh"><div id="${msg}"></div></div>`).join("")}</div>`;
}
const fk = (v, k) => v == null || v === "" ? "–" : k === "n" ? fmt(v) : /^f\d$/.test(k) ? fx(v, +k[1]) : /^p\d$/.test(k) ? pc(v, +k[1]) : esc(v);
