/* IT PMT Dashboard — komponen & tampilan halaman (dari mockup, kini membaca bundel API). */
"use strict";
/* ---------- komponen ---------- */
function nice(v) { if (v <= 0) return 1; const p = Math.pow(10, Math.floor(Math.log10(v))), f = v / p; return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * p; }
function xl(labels, x, y) { const n = labels.length, sparse = labels.some(t => t === ""), k = sparse ? 1 : Math.ceil(n / 12); return labels.map((t, i) => (i % k === 0) ? `<text x="${x(i)}" y="${y}" text-anchor="middle">${esc(t)}</text>` : "").join(""); }
const empty = (t) => `<div class="empty"><b>Belum ada data</b><span>${t || "Tidak ada data untuk filter ini. Coba ubah periode, shift, atau lokasi."}</span></div>`;
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
  B.forEach((b, i) => { ov += `<rect x="${x(i) - gw / 2}" y="${T}" width="${gw}" height="${ph}" fill="transparent" data-tip="${esc(b.full + "\n" + series.map(s => s.name + ": " + (s.v[i] == null ? "tidak ada data" : fx(s.v[i], o.dec ?? 1) + (o.unit || ""))).join("\n"))}"/>`; });
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
const info = t => `<button type="button" class="ib" data-tip="${esc(t)}" aria-label="Rumus: ${esc(t)}">i</button>`;
function delta(cur, prev, o = {}) {
  if (!S.cmp || cur == null || prev == null || isNaN(cur) || isNaN(prev)) return "";
  const d = cur - prev; if (Math.abs(d) < 1e-9) return `<span class="dl flat">= sama</span>`;
  const good = o.up === undefined ? null : (d > 0) === o.up, txt = o.pct ? fx(Math.abs(d) * 100, 1) + " poin" : prev ? fx(Math.abs(d / prev) * 100, 0) + "%" : fmt(Math.abs(d));
  return `<span class="dl ${good == null ? "flat" : good ? "good" : "bad"}">${d > 0 ? "▲" : "▼"} ${txt}</span>`;
}
const kpi = (l, v, d, o = {}) => `<div class="kpi ${o.cls || ""}"><span class="lbl">${l}${o.tip ? info(o.tip) : ""}</span><span class="v">${v}</span><span class="d">${o.dl || ""}${d || ""}</span></div>`;
function tbl(heads, rows, o = {}) {
  if (!rows.length) return `<div class="empty sm">${o.empty || "Tidak ada data untuk filter ini."}</div>`;
  const isN = heads.map((h, i) => rows.some(r => typeof r[i] === "number") || (o.r || []).includes(i));
  const cell = c => c == null ? "–" : typeof c === "number" ? (Number.isInteger(c) ? fmt(c) : fx(c, 2)) : c.h != null ? c.h : esc(c);
  return `<div class="scroll ${o.tall ? "tall" : ""}"><table><thead><tr>${heads.map((h, i) => `<th class="${isN[i] ? "r" : ""}">${esc(h)}</th>`).join("")}</tr></thead><tbody>` + rows.map(r => `<tr>${r.map((c, i) => `<td class="${isN[i] ? "r num" : "t"}">${cell(c)}</td>`).join("")}</tr>`).join("") + `</tbody></table></div>`;
}
const dayB = arr => arr.map(x => ({label: dmon(x.date), full: dlong(x.date)}));
const stPill = s => ({h: s === NST.ok ? pill("good", s) : s === NST.bad ? pill("crit", s) : pill("idle", s)});
const go = (tab, t) => `<button type="button" class="lnk" data-go="${tab}">${t || "Buka rincian"} →</button>`;

/* ---------- header, nav, filter ---------- */
const ICO = {
  dashboard: '<rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/>',
  ticket: '<path d="M3 9V6a1 1 0 0 1 1-1h16a1 1 0 0 1 1 1v3a2.5 2.5 0 0 0 0 5v3a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-3a2.5 2.5 0 0 0 0-5z"/><path d="M14 5v2.5M14 10.75v2.5M14 16.5V19"/>',
  activity: '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
  shield: '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
  users: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c0-3.6 2.9-6 6.5-6s6.5 2.4 6.5 6"/><path d="M16 4.6a3.5 3.5 0 0 1 0 6.8M18.5 14.3c1.9.8 3 2.6 3 5.7"/>',
  handover: '<path d="M17 3l4 4-4 4"/><path d="M3 11V9a2 2 0 0 1 2-2h16"/><path d="M7 21l-4-4 4-4"/><path d="M21 13v2a2 2 0 0 1-2 2H3"/>',
  database: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>',
  sliders: '<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>',
  report: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 17v-3M12 17v-6M15 17v-4"/>',
  calendar: '<rect x="3" y="4" width="18" height="17" rx="2"/><path d="M3 9h18M8 2v4M16 2v4"/>'
};
const icon = k => `<svg viewBox="0 0 24 24" aria-hidden="true">${ICO[(MODS[k] || {}).icon] || '<circle cx="12" cy="12" r="4"/>'}</svg>`;const topOf = k => { const p = (MODS[k] || {}).parent; return p && MODS[p] ? p : k; };
/* Sub-menu: halaman induk dan anak-anaknya (mis. Report + Handover) sebagai tab di dalam halaman */
function subnav(parent) {
  const items = TABS.filter(t => t[0] === parent || (MODS[t[0]] || {}).parent === parent);
  return items.length < 2 ? "" : `<div class="subtabs">${items.map(([k, l]) => `<button type="button" data-tab="${k}" aria-selected="${k === S.tab}">${esc(l)}</button>`).join("")}</div>`;
}
function renderShell() {
  const NAVT = TABS.filter(t => topOf(t[0]) === t[0]), curTop = topOf(S.tab);
  $("tabs").innerHTML = NAVT.map(([k, l, bd]) => `<button role="tab" data-tab="${k}" aria-selected="${k === curTop}">${icon(k)}<span>${esc(l)}</span></button>`).join("");
  $("sheetGrid").innerHTML = NAVT.map(([k, l, bd]) => `<button type="button" data-tab="${k}" aria-selected="${k === curTop}">${icon(k)}<span>${esc(l)}</span></button>`).join("");
  $("moreBtn").classList.toggle("on", NAVT.findIndex(t => t[0] === curTop) > 3);
  const cur = TABS.find(t => t[0] === S.tab); $("ptitle").textContent = cur ? cur[1] : "";
  $("psub").textContent = APPLY[S.tab] && APPLY[S.tab].p ? rangeTxt() : "";
  $("fPreset").innerHTML = PRESETS.map(([k, l]) => `<button type="button" data-p="${k}" aria-pressed="${S.preset === k}">${l}</button>`).join("");
  $("fShift").innerHTML = SN.map((l, i) => `<button type="button" data-s="${i}" aria-pressed="${S.sf === i}" ${i ? `title="${shiftHours(i)}"` : ""}>${l}</button>`).join("");
  $("fSite").innerHTML = `<option value="">${CFG.me.site ? "Lokasi akun Anda" : "All lokasi"}</option>` + CFG.sites.map(s => `<option ${s === S.site ? "selected" : ""}>${esc(s)}</option>`).join("");
  $("fFrom").value = S.from; $("fTo").value = S.to; $("fFrom").max = $("fTo").max = nowShift().today; $("fFrom").min = $("fTo").min = CFG.params.data_start; $("fCmp").checked = S.cmp;
  const ap = APPLY[S.tab];
  $("fwrap").hidden = !ap.p;
  $("fbar").classList.toggle("off", !ap.p);
  [["gPeriode", ap.p], ["gShift", ap.s], ["gSite", ap.l], ["gCmp", ap.p && ap.c]].forEach(([id, on]) => { const el = $(id); el.classList.toggle("na", !on); el.querySelectorAll("button,select,input").forEach(x => x.disabled = !on); });
  if (CFG.me.site) { $("fSite").disabled = true; $("gSite").classList.add("na"); }
  const chips = [], active = [];
  if (ap.p) active.push(rangeTxt()); if (ap.s && S.sf) active.push("shift " + SN[S.sf] + " (" + shiftHours(S.sf) + ")"); if (ap.l && S.site) active.push(S.site); if (S.cmp && $("gCmp").querySelector("input:not(:disabled)")) active.push("dibanding " + dmon(prevRange().from) + " – " + dmon(prevRange().to));
  if (ap.p) { chips.push(`<span class="on">Active filter: <b>${esc(active.join(" · "))}</b></span>`);
    if (!ap.s && S.sf || !ap.l && S.site) chips.push(`<span class="na-txt">${(!ap.s && S.sf ? "Shift" : "") + (!ap.s && S.sf && !ap.l && S.site ? " dan " : "") + (!ap.l && S.site ? "lokasi" : "")} tidak berlaku di halaman ini</span>`); }
  $("fApplies").innerHTML = chips.join("");
  const n = nowShift(), tm = teamOn(n.date, n.shift);
  $("duty").innerHTML = `<i></i><span>On duty: Team ${tm} · ${SN[n.shift]}<small>${n.clock} WIB</small></span>`; $("dutyM").textContent = `Team ${tm} · ${SN[n.shift]}`;
  $("fSum").textContent = ap.p ? active.join(" · ") : "Tidak berlaku di halaman ini";

}

/* ---------- Ringkasan ---------- */
function vRingkasan() {
  const hasT = "tk" in V, hasN = "net" in V, hasS = "soc" in V, hasH = "ho_open" in V;
  const T = hasT ? tkR() : null, N = hasN ? netR() : null, R = hasS ? socR() : null, chk = hasS ? socCheck() : [], okDays = chk.filter(x => x.s === "ok" || x.s === "dup").length, now = nowShift();
  const P = S.cmp ? prevRange() : null, Tp = P && tkR(P), Np = P && netR(P), Rp = P && socR(P);
  const openOld = V.open_old || [], oldD = CFG.params["sd.open_alert_days"];
  const badLinks = N ? N.rank.filter(s => s.status === NST.bad) : [];
  const att = [];
  if (openOld.length) att.push(["crit", `<b>${openOld.length} tiket open lebih dari ${oldD} hari</b>, terlama ${esc(openOld[0].subject)} (#${esc(openOld[0].id)}, ${fx(openOld[0].age, 0)} hari).`, "servicedesk"]);
  if (badLinks.length) att.push(["crit", `<b>${badLinks.length} link di bawah target ${pc(PAR.target, 1)}</b>: ${badLinks.slice(0, 3).map(s => esc(s.link) + " (" + pc(s.av, 2) + ")").join(", ")}${badLinks.length > 3 ? ", …" : ""}.`, "noc"]);
  if (N && N.nodata) att.push(["warn", `<b>${N.nodata} link data kurang</b> (cakupan pantau &lt; ${pc(PAR.minCov, 0)}), tidak dinilai SLA.`, "noc"]);
  if (R && R.chAlert) att.push(["warn", `<b>${fmt(R.chAlert)} event critical/high hanya alert</b>, tidak diblokir firewall.`, "soc"]);
  if (R && R.unknown && Object.keys(R.unknown).length) att.push(["warn", `<b>Cyber Security: nilai baru di luar daftar parameter</b> (${Object.entries(R.unknown).map(([k, r]) => ({type: "tipe", action: "tindakan", severity: "severity"}[k]) + ": " + r.map(x => esc(x[0])).join(", ")).join("; ")})`, "soc"]);
  if (N && (N.unmappedIsp || []).length) att.push(["warn", `<b>${N.unmappedIsp.length} link belum cocok dengan ISP mana pun</b>: ${N.unmappedIsp.slice(0, 3).map(esc).join(", ")}`, "noc"]);
  const bad = chk.filter(x => x.s === "bad" || x.s === "miss"); if (bad.length) att.push(["warn", `<b>Data SOC belum lengkap</b>: ${bad.length} dari ${chk.length} hari tidak terbaca atau belum diunggah.`, "kelengkapan"]);
  const hoOpen = V.ho_open || []; if (hoOpen.some(h => prTone(h.prio) === "crit")) att.push(["crit", `<b>${hoOpen.filter(h => prTone(h.prio) === "crit").length} handover prioritas tinggi</b> belum ditutup.`, "serahterima"]);
  const s1 = hasT ? [{name: "Tickets In", c: "--s1", v: T.daily.map(x => x.in)}, {name: "Tickets Closed", c: "--s2", v: T.daily.map(x => x.done)}] : [];
  const cg = GROUPS.find(g => g.kind === "office"), care = cg ? CFG.people.filter(p => p.unit === cg.unit) : [], ct = CFG.params["report.contact"] || {};
  const careP = cg ? panel("c4", esc(cg.label), esc(cg.start + "–" + cg.end), `<div class="carenum">${ct.phone ? `<span class="lbl">Layanan ${esc(cg.label)}</span><b class="num">${esc(ct.phone)}</b>` : ""}${ct.email ? `<span class="sub">${esc(ct.email)}</span>` : ""}</div>${care.length ? `<ul class="plist">${care.map(p => `<li><span>${esc(p.name)}<span class="sub"> · ${esc(p.job || "")}</span></span><span class="num sub">${esc(p.phone || "")}</span></li>`).join("")}</ul>` : ""}`) : "";
  const lead = CFG.people.filter(p => p.unit === "ITOC" && !p.team_code), leadP = lead.length ? panel("c4", "Escalation", "Supervisor & Lead", `<ul class="plist">${lead.map(p => `<li><span>${esc(p.name)}<span class="sub"> · ${esc((p.job || "").replace(/^ITOC /, ""))}</span></span><span class="num sub">${esc(p.phone || "")}</span></li>`).join("")}</ul>`) : "";
  const dom = (title, tab, src, body) => `<section class="panel c4 dom"><header><h2>${title}</h2>${src}</header><div class="mini">${body}</div>${go(tab)}</section>`;
  return `<div class="grid">
  ${!hasT ? "" : dom("Ticketing", "servicedesk", ``, kpi("Tickets In", fmt(T.n), fx(T.perDay, 1) + "/hari", {tip: RUMUS.tkIn, dl: Tp ? delta(T.n, Tp.n) : ""}) + kpi("Close", pc(T.doneRate), fmt(T.open) + " open", {tip: RUMUS.tkDone, dl: Tp ? delta(T.doneRate, Tp.doneRate, {up: true, pct: 1}) : ""}) + kpi("Within SLA Target", pc(T.slaPct), fmt(T.slaOut) + " melewati", {tip: RUMUS.tkSla, dl: Tp ? delta(T.slaPct, Tp.slaPct, {up: true, pct: 1}) : "", cls: T.slaPct != null && T.slaPct < CFG.params["sd.sla_warn"] ? "warnv" : ""}) + kpi("Median Duration", fx(T.medMin, 0) + " mnt", "P90 " + fx(T.p90, 1) + " jam", {tip: RUMUS.tkMed, dl: Tp ? delta(T.medMin, Tp.medMin, {up: false}) : ""}))}
  ${!hasN ? "" : dom("Networking", "noc", ``, N ? kpi("Availability", pc(N.avail, 2), "target " + pc(PAR.target, 1), {tip: RUMUS.av, dl: Np ? delta(N.avail, Np.avail, {up: true, pct: 1}) : "", cls: N.avail < PAR.target ? "warnv" : ""}) + kpi("Links Meeting SLA", N.ok + "/" + (N.ok + N.bad), N.bad + " tidak, " + N.nodata + " data kurang", {tip: RUMUS.link}) + kpi("Total Downtime", fx(N.downH, 1) + " jam", N.events + " kejadian", {tip: RUMUS.down, dl: Np ? delta(N.downH, Np.downH, {up: false}) : ""}) + kpi("High Utilization", fmt(N.utilHigh), "link puncak ≥ " + pc(PAR.utilPeak, 0), {tip: RUMUS.util}) : empty())}
  ${!hasS ? "" : dom("Cyber Security", "soc", ``, kpi("Critical + High Blocked", R.ch ? pc(R.chBlkPct) : "–", fmt(R.chAlert) + " hanya alert", {tip: RUMUS.socCH, dl: Rp && Rp.ch ? delta(R.chBlkPct, Rp.chBlkPct, {up: true, pct: 1}) : ""}) + kpi("Total Events", R.total ? fmt(R.total) : "–", fmt(R.ch) + " critical/high", {tip: RUMUS.socTot}) + kpi("Validated Days", okDays + "/" + chk.length, okDays < chk.length ? "sisanya tidak dihitung" : "lengkap", {cls: okDays < chk.length ? "warnv" : ""}) + kpi("Internal Source", pc(R.internalPct), "dari total event", {tip: RUMUS.socInt}))}
  ${panel("c8", "Attention", ctxTxt(), att.length ? `<ul class="att">${att.map(a => `<li class="${a[0]}"><span>${a[1]}</span>${go(a[2], "Lihat")}</li>`).join("")}</ul>` : `<div class="empty sm">Tidak ada yang perlu ditindaklanjuti.</div>`)}
  ${panel("c4", "On Duty", dlong(now.date) + " · " + shiftHours(now.shift), onDuty(now))}
  ${!hasT ? "" : panel("c8", "Tickets In and Closed per Day", ctxTxt(), legend(s1) + bars(dayB(T.daily), s1, {label: "Tiket per hari"}))}
  ${careP}
  ${leadP}
  ${!hasH ? "" : panel("c4", "Handover open", hoOpen.length + " item", hoList(hoOpen.slice(0, 3), true) + go("serahterima", "All handover"))}
  ${N ? panel("c12", "Link Downtime per Day", "Jumlah menit downtime semua link dalam filter", bars(dayB(N.daily), [{name: "Downtime (menit)", c: "--crit", v: N.daily.map(x => x.down)}], {dec: 1, unit: " mnt", label: "Daily Downtime", w: 1200})) : ""}
  </div>`;
}
function onDuty(n) {
  const g = teamOn(n.date, n.shift), c = crew(g);
  return `<div class="duty-card"><div class="big"><span class="code ${SC[n.shift]}">${SC[n.shift]}</span><div><b>Shift ${SN[n.shift]} · Team ${g}</b><span class="sub">Berikutnya: ${SN[n.shift % NS + 1]} · Team ${teamOn(n.shift === NS ? addDays(n.date, 1) : n.date, n.shift % NS + 1)}</span></div></div>
  <ul class="plist">${c.map(p => `<li><span>${esc(p.name)}<span class="sub"> · ${esc(p.job.replace("ITOC ", ""))}</span></span><span class="num sub">${esc(p.phone)}</span></li>`).join("")}</ul></div>`;
}
function hoList(L, compact) {
  if (!L.length) return `<div class="empty sm">Tidak ada handover untuk filter ini.</div>`;
  return `<ul class="ho">${L.map(h => `<li class="${h.open ? "" : "done"}"><div class="tx"><div><span class="pr ${prTone(h.prio)}">${h.prio}</span> <span class="tag">${h.cat}</span> ${esc(h.title)}</div>
    <div class="meta">${dtime(h.at)} · Shift ${SN[h.shift]} → ${SN[h.shift % NS + 1]} · ${esc(h.site)}${h.ticket ? " · tiket #" + esc(h.ticket) : ""} · ${esc(h.by)}</div>
    ${compact ? "" : `<div class="body">${esc(h.body)}</div>${h.next ? `<div class="next"><b>Tindak lanjut:</b> ${esc(h.next)}</div>` : ""}${h.open ? "" : `<div class="next"><b>Ditutup</b> ${esc(h.closedBy)} · ${dtime(h.closedAt)}: ${esc(h.closeNote)}</div>`}
    ${S.closing === h.id ? `<div class="closebox"><label for="cn">Closing Note (required)</label><textarea id="cn" placeholder="Apa hasil akhirnya?"></textarea><div class="acts"><button class="btn" data-close-ok="${h.id}">Close Handover</button><button class="btn ghost" data-close-cancel>Cancel</button><span class="msg err" id="cnmsg"></span></div></div>` : ""}`}
    </div>${!compact && h.open && S.closing !== h.id ? `<button class="btn ghost" data-close="${h.id}">Tutup…</button>` : ""}</li>`).join("")}</ul>`;
}

/* ---------- Service Desk ---------- */
function vSD() {
  const T = tkR(), Tp = S.cmp ? tkR(prevRange()) : null, s1 = [{name: "Tickets In", c: "--s1", v: T.daily.map(x => x.in)}, {name: "Tickets Closed", c: "--s2", v: T.daily.map(x => x.done)}];
  if (!T.n) return `<div class="grid"><section class="panel c12">${empty()}</section></div>`;
  const dimRows = T.dims[S.dim].map(x => [x.k, x.n, pc(x.pct), x.done, x.open, x.avg, x.med, x.zero, x.in, x.out, pc(x.inPct)]);
  const rk = T.ranking.filter(x => x.n > 0 || !S.site).map(x => [x.rank, x.name, {h: x.unit ? `<span class="tag">${esc(x.unit)}</span>` : ""}, x.n, pc(x.share), x.done, x.open, x.avg, x.med, pc(x.zeroPct, 0), pc(x.inPct), x.high, pc(x.okPct, 0), x.loc]);
  const hrs = [...Array(24).keys()].map(h => ({label: pad(h), full: "Pukul " + pad(h) + ".00–" + pad(h) + ".59 · shift " + SN[shiftOf(h)]}));
  return `<div class="kpis k6">${kpi("Tickets In", fmt(T.n), fx(T.perDay, 1) + " per hari", {tip: RUMUS.tkIn, dl: Tp ? delta(T.n, Tp.n) : ""})}${kpi("Completion Rate", pc(T.doneRate), fmt(T.open) + " masih open", {tip: RUMUS.tkDone, dl: Tp ? delta(T.doneRate, Tp.doneRate, {up: true, pct: 1}) : ""})}${kpi("Within SLA Target", pc(T.slaPct), fmt(T.slaIn) + " dalam, " + fmt(T.slaOut) + " melewati", {tip: RUMUS.tkSla, dl: Tp ? delta(T.slaPct, Tp.slaPct, {up: true, pct: 1}) : ""})}${kpi("Median Duration", fx(T.medMin, 0) + " mnt", "rata-rata " + fx(T.avgH, 1) + " jam, P90 " + fx(T.p90, 1) + " jam", {tip: RUMUS.tkMed, dl: Tp ? delta(T.medMin, Tp.medMin, {up: false}) : ""})}${kpi("0-Minute Duration", fmt(T.zero), pc(T.n ? T.zero / T.n : 0) + " dari total")}${kpi("Incomplete Input", fmt(T.incomplete), pc(T.n ? T.incomplete / T.n : 0) + " dari total")}</div>
  <div class="grid">${panel("c8", "Daily Trend", ctxTxt() + (T.doneAfter ? " · " + T.doneAfter + " tiket close setelah periode" : ""), legend(s1) + bars(dayB(T.daily), s1, {label: "Tren harian tiket"}))}
  ${panel("c4", "Resolution Duration Distribution", "", hbars(T.durasi.map(x => [x.k, x.n, 0, fmt(x.n) + " · " + pc(x.pct, 0)])))}
  ${panel("c7", "Tickets per Hour", T.peakHour != null ? "Jam tersibuk " + pad(T.peakHour) + ".00" : "", bars(hrs, [{name: "Tickets In", c: "--s1", v: T.hours}], {label: "Tiket per jam"}))}
  ${panel("c5", "Per Weekday", "Hari kerja " + fx(T.perWorkday, 1) + "/hari, akhir pekan " + fx(T.perWeekend, 1), tbl(["Hari", "Tiket", "Jumlah hari", "Rata-rata/hari"], T.weekday.map(x => [x.k, x.n, x.days, fx(x.avg, 1)]), {r: [3]}))}
  ${panel("c12", `Rincian per <select class="pick" id="dim" aria-label="Dimensi">${Object.entries(DIMS).map(([k, v]) => `<option value="${k}" ${k === S.dim ? "selected" : ""}>${v[0]}</option>`).join("")}</select>`, "", tbl([DIMS[S.dim][0], "Jumlah", "% total", "Close", "Open", "Rata-rata", "Median", "0 menit", "Dalam target", "Melewati", "% dalam target"], dimRows, {tall: true, r: [2, 10]}))}
  ${panel("c12", "Group Ranking", "", tbl(["#", "Group", "Anggota", "Tiket", "% daftar", "Close", "Open", "Rata-rata (jam)", "Median (jam)", "% dalam target", "High"], (T.groupRanking || []).map(x => [x.rank, x.name, x.members, x.n, pc(x.share), x.done, x.open, x.avg, x.med, pc(x.inPct), x.high]), {r: [3, 4, 5, 6, 7, 8, 9, 10]}))}
  ${panel("c12", "Technician Ranking", "", tbl(["#", "Nama", "Unit", "Tiket", "% daftar", "Close", "Open", "Rata-rata (jam)", "Median (jam)", "% 0 menit", "% dalam target", "High", "% input lengkap", "Lokasi utama"], rk, {tall: true, r: [4, 9, 10, 12]}))}
  ${panel("c12", "Open Tickets", "", tbl(["Subjek", "ID", "Lokasi", "Kategori", "Teknisi", "Prioritas", "Status", "Dibuat", "Umur (hari)"], T.openList.map(x => [x.subj, x.id, x.loc, x.cat, x.tech, x.prio, x.status, dtime(x.created), {h: `<span class="${x.age > 3 ? "crit-t" : ""}">${fx(x.age, 1)}</span>`}]), {r: [8], empty: "Tidak ada tiket open."}))}
  ${panel("c7", "Data Quality Notes", "", tbl(["Pemeriksaan", "Tiket", "% total"], T.quality.map(x => [x.k, x.n, pc(x.pct)]), {r: [2]}))}
  ${panel("c5", "Top Requesters", "", tbl(["Requester", "Tiket", "% total"], T.requesters.map(x => [x.k, x.n, pc(x.pct)]), {r: [2]}))}
  ${panel("c12", "25 Longest-Duration Tickets", "", tbl(["Subjek", "ID", "Lokasi", "Kategori", "Teknisi", "Prioritas", "Dibuat", "Durasi (hari)", "Pola"], T.longest.map(x => [x.subj, x.id, x.loc, x.cat, x.tech, x.prio, dtime(x.created), fx(x.days, 1), x.pola]), {tall: true, r: [7]}))}</div>`;
}

/* ---------- NOC ---------- */
function vNoc() {
  const B = netB(), N = netR(); if (!N) return `<div class="grid"><section class="panel c12">${empty()}</section></div>`;
  const Np = S.cmp ? netR(prevRange()) : null, P = N.P, hr0 = B.hourly, tot = !!hr0.ttot && !hr0.tin.some(v => v > 0), hr = tot ? {k: hr0.k, tin: hr0.ttot, tout: hr0.tout} : hr0, long = hr.k.length > 24 * 8;
  let lb, vin, vout;
  if (long) { const by = {}; hr.k.forEach((t, j) => { const d = iso(t), o = by[d] || (by[d] = {i: 0, o: 0, n: 0}); o.i += hr.tin[j]; o.o += hr.tout[j]; o.n++; }); const ks = Object.keys(by).sort(); lb = ks.map(d => ({label: dmon(d), full: dlong(d) + " (rata-rata harian)"})); vin = ks.map(d => by[d].i / by[d].n); vout = ks.map(d => by[d].o / by[d].n); }
  else { lb = hr.k.map(t => ({label: new Date(t).getUTCHours() === 0 || hr.k.length <= 24 ? (hr.k.length <= 24 ? pad(new Date(t).getUTCHours()) + ".00" : dmon(iso(t))) : "", full: dtime(t) + " WIB"})); vin = [...hr.tin]; vout = [...hr.tout]; }
  const pk = Math.max(...hr.tin), pkO = Math.max(...hr.tout), avI = hr.tin.reduce((a, b) => a + b, 0) / (hr.k.length || 1), avO = hr.tout.reduce((a, b) => a + b, 0) / (hr.k.length || 1);
  const top = [...B.N.sensors].sort((a, b) => tot ? b.avg - a.avg : b.avgIn - a.avgIn).slice(0, 10);
  const sid = V.sensor_id, ss = V.sensor_series, sMeta = B.N.sensors.find(s => s.id === sid) || {};
  const sb = ss ? ss.t.map(t => ({label: "", full: dtime(t) + " WIB"})) : [];
  if (ss) { const step = Math.ceil(ss.t.length / 10); ss.t.forEach((t, i) => { if (i % step === 0) sb[i].label = ss.t.length <= 24 ? pad(new Date(t).getUTCHours()) + ".00" : dmon(iso(t)); }); }
  const marks = ss ? ss.d.map((d, i) => d > 0 ? i : -1).filter(i => i >= 0) : [];
  const tr = tot ? [{name: "Total Traffic", c: "--s1", v: vin}] : [{name: "Trafik In", c: "--s1", v: vin}, {name: "Trafik Out", c: "--s2", v: vout}];
  const um = (N.unmappedIsp || []).length ? `<div class="grid">${panel("c12", "Links Not Matching Any ISP", "", `<ul class="att"><li class="warn"><span>${N.unmappedIsp.map(esc).join(", ")} · tambahkan kata kunci di Admin → Master data → ISP</span></li></ul>`)}</div>` : "";
  return um + `<div class="kpis k6">${kpi("Availability", pc(N.avail, 2), "target " + pc(P.target, 1), {tip: RUMUS.av, dl: Np ? delta(N.avail, Np.avail, {up: true, pct: 1}) : "", cls: N.avail < P.target ? "warnv" : ""})}${kpi("Links Meeting SLA", N.ok + " dari " + (N.ok + N.bad), N.bad + " tidak, " + N.nodata + " data kurang", {tip: RUMUS.link})}${kpi("Total Downtime", fx(N.downH, 1) + " jam", N.events + " kejadian · " + N.noDown + " link tanpa down", {tip: RUMUS.down, dl: Np ? delta(N.downH, Np.downH, {up: false}) : ""})}${kpi("Data Coverage", pc(N.cov), "jam terpantau ÷ jam periode")}${(tot ? kpi("Peak Traffic", fx(pk, 1) + " Mbit/s", "rata-rata " + fx(avI, 1) + " · total In + Out, dari laporan harian") : kpi("Peak Traffic In", fx(pk, 1) + " Mbit/s", "rata-rata " + fx(avI, 1) + " · Out puncak " + fx(pkO, 1)))}${kpi("High Peak Utilization", fmt(N.utilHigh), "link ≥ " + pc(P.utilPeak, 0) + " kapasitas", {tip: RUMUS.util})}</div>
  <div class="grid">${panel("c8", "Total Traffic In and Out (Mbit/s)", ctxTxt() + (long ? " · rata-rata per hari" : " · rata-rata per jam"), legend(tr) + lines(lb, tr, {unit: " Mbit/s", label: "Total trafik"}))}
  ${panel("c4", "Top 10 Links by Traffic", tot ? "Rata-rata Mbit/s (total)" : "Rata-rata Mbit/s, In dan Out", (tot ? "" : legend([{name: "In", c: "--s1"}, {name: "Out", c: "--s2"}])) + (tot ? hbars(top.map(s => [s.dev.replace("Branch ", "") + " – " + (s.name.split(" - ")[1] || s.name).replace(" Traffic", ""), s.avg, 0, fx(s.avg, 1) + " Mbit/s"])) : hbars(top.map(s => [s.dev.replace("Branch ", "") + " – " + (s.name.split(" - ")[1] || s.name).replace(" Traffic", ""), s.avgIn, s.avgOut, fx(s.avgIn, 1) + " / " + fx(s.avgOut, 1)]), {two: true})))}
  ${panel("c12", `Trafik per sensor: <select class="pick" id="sensor" aria-label="Sensor">${B.N.sensors.map(s => `<option value="${s.id}" ${s.id === sid ? "selected" : ""}>${esc(s.dev + " – " + s.name)}</option>`).join("")}</select>`, sMeta.cap ? "Kapasitas " + sMeta.cap + " Mbit/s · area merah = jam dengan downtime" : "", ss ? legend((tot ? [{name: "Total", c: "--s1"}] : [{name: "In", c: "--s1"}, {name: "Out", c: "--s2"}]).concat([{name: "Ada downtime", c: "--crit"}])) + lines(sb, tot ? [{name: "Total", c: "--s1", v: ss.a}] : [{name: "In", c: "--s1", v: ss.i}, {name: "Out", c: "--s2", v: ss.o}], {unit: " Mbit/s", thin: true, marks, label: "Trafik sensor", w: 1200, h: 260}) : empty())}
  ${panel("c8", "Daily Downtime", "Menit downtime semua link", bars(dayB(N.daily), [{name: "Downtime", c: "--crit", v: N.daily.map(x => x.down)}], {dec: 1, unit: " mnt", label: "Daily Downtime"}))}
  ${panel("c4", "Link Availability Distribution", "", tbl(["Kelompok", "Link", "% link"], N.buckets.map(x => [x.k, x.n, pc(x.pct, 0)]), {r: [2]}))}
  ${panel("c12", "Summary per ISP", "Availability = Σ Up ÷ Σ (Up + Down) semua link ISP itu", tbl(["ISP", "Link", "Availability", "Downtime (jam)", "Target", "Capai", "Tidak", "Data kurang", "% capai", "Trafik (Mbit/s)", "Volume (GB)"], N.isp.map(x => [x.k, x.n, pc(x.av, 3), x.downH, pc(x.target, 1), x.ok, x.bad, x.nodata, pc(x.okPct, 0), x.mbps, x.volGB]), {r: [2, 4, 8]}))}
  ${panel("c12", "Link Ranking by Downtime", "Data kurang bila cakupan < " + pc(P.minCov, 0), tbl(["#", "Link", "Availability", "Downtime (jam)", "Target", "Status SLA", "Sisa (+) / lebih (−) menit", "Cakupan", "Rata-rata (Mbit/s)", "Puncak (Mbit/s)", "Sensor"], N.rank.map(s => [s.rank, s.link, pc(s.av, 3), s.down / 3600, pc(s.target, 1), stPill(s.status), s.sisa, pc(s.cov, 0), s.avg, s.max, s.id]), {tall: true, r: [2, 4, 7]}))}
  ${panel("c12", "Summary per Location", N.sameYes + " dari " + N.sameCmp + " lokasi ber-link ganda turun bersamaan (selisih ≤ " + CFG.params["net.same_tolerance_min"] + " menit): tanda gangguan di sisi lokasi", tbl(["Lokasi", "Link", "Downtime (menit)", "Link terlama", "Link tersingkat", "Availability terendah", "Capai", "Tidak", "Data kurang", "Turun bersamaan?"], N.lokasi.map(x => [x.k, x.n, x.downMin, x.maxMin, x.minMin, pc(x.minAv, 3), x.ok, x.bad, x.nodata, x.same]), {tall: true, r: [5]}))}
  ${panel("c5", "20 Longest Downtime Events", N.events + " kejadian dalam filter", tbl(["Link", "Mulai", "Selesai", "Menit"], N.kej.map(k => [k.link, dtime(k.start), dtime(k.end), k.min]), {tall: true}))}
  ${panel("c7", "Capacity Utilization", "Puncak ≥ " + pc(P.utilPeak, 0) + " atau rata-rata ≥ " + pc(P.utilAvg, 0) + " ditandai", tbl(["Link", "Kapasitas", "Rata-rata", "Puncak", "Util. rata-rata", "Util. puncak", "Status"], N.util.map(s => [s.link, s.cap, s.avg, s.max, pc(s.uA, 0), pc(s.uP, 0), {h: s.ust === UST.ok ? pill("good", UST.ok) : pill("warn", s.ust)}]), {tall: true, r: [4, 5]}))}</div>`;
}

/* ---------- SOC (perlu validasi) ---------- */
const CST = {ok: ["ok", "Tervalidasi"], dup: ["dup", "Ada di 2 batch (dipakai terbaru)"], bad: ["bad", "Gagal dibaca"], miss: ["miss", "Belum diunggah"], wait: ["wait", "Hari ini, belum waktunya"]};
function covStrip(chk) { return `<div class="cov">${chk.map(x => `<span class="c ${CST[x.s][0]}" data-tip="${esc(dlong(x.d) + "\n" + CST[x.s][1] + (x.b ? "\nBatch " + x.b : ""))}">${new Date(dayMs(x.d)).getUTCDate()}</span>`).join("")}</div>
  <div class="legend">${[["ok", "Tervalidasi"], ["dup", "Duplikat, dipakai terbaru"], ["bad", "Gagal dibaca"], ["miss", "Belum diunggah"]].map(([k, l]) => `<span><b class="c ${k}"></b>${l}</span>`).join("")}</div>`; }
function vSoc() {
  const R = socR(), chk = socCheck(), okD = chk.filter(x => x.s === "ok" || x.s === "dup"), bt = batchFor(), Rp = S.cmp ? socR(prevRange()) : null;
  const crit = (V.batches || []).filter(b => b.issues.some(i => i.k === "crit") && b.to >= S.from && b.from <= S.to);
  const checks = [
    [okD.length === chk.length ? "good" : okD.length ? "warn" : "crit", `Hari dengan data harian: ${okD.length} dari ${chk.length}`, ""],
    ...crit.map(b => ["crit", `Batch ${esc(b.file)} gagal validasi`, b.issues.filter(i => i.k === "crit").map(i => esc(i.t)).join(" ")]),
    [Object.keys((V.soc_dup || {})).some(d => d >= S.from && d <= S.to) ? "warn" : "good", "Duplikasi tanggal antar-batch", Object.keys((V.soc_dup || {})).filter(d => d >= S.from && d <= S.to).map(dmon).join(", ") || "Tidak ada"],
    [R.ch <= R.total && R.sevTotal.blk <= R.total && R.urlBlk <= R.url ? "good" : "crit", "Konsistensi angka", ""],
    [bt ? (bt.from === S.from && bt.to === S.to ? "good" : "warn") : "idle", "Tabel periode (laporan Top)", bt ? `${esc(bt.file)} · ${dmon(bt.from)} – ${dmon(bt.to)}` : "Belum ada"]
  ];
  const head = "";
  const UK = {type: ["Tipe ancaman", "soc.threat_types"], action: ["Tindakan", "soc.actions"], severity: ["Severity", "soc.severities"]};
  const unkL = Object.entries(R.unknown || {}).map(([k, rows]) => `<li class="warn"><span><b>${UK[k][0]} baru:</b> ${rows.map(([n, c]) => `${esc(n)} (${fmt(c)})`).join(", ")} · tambahkan ke <span class="num">${UK[k][1]}</span> di Admin → Parameter</span></li>`).join("");
  const unkP = unkL ? panel("c12", "New Values Outside Parameter List", "", `<ul class="att">${unkL}</ul>`) : "";
  const val = panel("c12", "SOC Data Validation", ctxTxt(APPLY.soc), `<div class="valgrid"><div>${covStrip(chk)}</div><ul class="checks">${checks.map(c => `<li>${pill(c[0], "")}<div><b>${c[1]}</b>${c[2] ? `<span>${c[2]}</span>` : ""}</div></li>`).join("")}</ul></div>`);
  if (!okD.length) return head + `<div class="grid">${val}<section class="panel c12">${empty("Belum ada hari SOC yang lolos validasi.")}</section></div>`;
  const B = dayB(R.daily), ch = [{name: "Critical", c: "--crit", v: R.daily.map(x => x.critical)}, {name: "High", c: "--serious", v: R.daily.map(x => x.high)}], ml = [{name: "Medium", c: "--warn", v: R.daily.map(x => x.medium)}, {name: "Low", c: "--low", v: R.daily.map(x => x.low)}, {name: "Informational", c: "--ss", v: R.daily.map(x => x.informational)}];
  const sd = {type: ["Tipe ancaman", R.type], action: ["Tindakan firewall", R.action], cat: ["Kategori ancaman", R.cat], dir: ["Arah ancaman", R.dir]}, cur = sd[S.sdim];
  const tabs = bt ? bt.tables : [], tb = tabs.find(t => t.id === S.stop) || tabs[0], part = okD.length < chk.length ? ` · dari ${okD.length}/${chk.length} hari` : "";
  return head + `<div class="grid">${val}${unkP}</div>
  <div class="kpis k6">${kpi("Total Events", fmt(R.total), "rata-rata " + fmt(R.total / okD.length) + " per hari tervalidasi" + part, {tip: RUMUS.socTot})}${kpi("Critical + High", fmt(R.ch), fmt(R.crit) + " critical")}${kpi("Critical + High Blocked", pc(R.chBlkPct), "tindakan selain alert", {tip: RUMUS.socCH, dl: Rp && Rp.ch ? delta(R.chBlkPct, Rp.chBlkPct, {up: true, pct: 1}) : ""})}${kpi("Alert Only", fmt(R.chAlert), "critical/high tidak dihentikan", {cls: R.chAlert ? "warnv" : ""})}${kpi("Internal Source", pc(R.internalPct), bt && bt.K ? fmt(bt.K.hosts) + " host internal (tabel " + dmon(bt.from) + "–" + dmon(bt.to) + ")" : "tabel host tidak tersedia", {tip: RUMUS.socInt})}${kpi("URL Blocked", fmt(R.urlBlk), "dari " + fmt(R.url) + " event URL")}</div>
  <div class="grid">${panel("c6", "Critical and High per Day", "", legend(ch) + bars(B, ch, {stack: true, label: "Critical dan high"}))}
  ${panel("c6", "Medium, Low, Informational per Day", "", legend(ml) + bars(B, ml, {stack: true, label: "Medium low informational"}))}
  ${panel("c6", "Severity and Action", "", tbl(["Severity", "Event", "% total", "Diblokir", "Hanya alert", "% diblokir"], R.sev.concat(R.sevTotal).map(x => [x.k, x.n, pc(x.pct), x.blk, x.alert, pc(x.blkPct)]), {r: [2, 5]}))}
  ${panel("c6", `Per <select class="pick" id="sdim" aria-label="Rincian">${Object.entries(sd).map(([k, v]) => `<option value="${k}" ${k === S.sdim ? "selected" : ""}>${v[0].toLowerCase()}</option>`).join("")}</select>`, "", tbl([cur[0], "Event", "% total", "Critical + High", "Diblokir", "Hanya alert"], cur[1].map(x => [x.k, x.n, pc(x.pct), x.ch, x.blk, x.alert]), {tall: true, r: [2]}))}
  ${panel("c6", "Traffic per Day (TB)", fx(R.tb, 2) + " TB, " + fmt(R.sess) + " sesi", bars(B, [{name: "Trafik", c: "--s1", v: R.daily.map(x => x.tb)}], {dec: 2, unit: " TB", label: "Trafik"}))}
  ${panel("c6", "URL Filtering per Category", "", tbl(["Kategori", "Total", "% total", "Diblokir", "Lainnya"], R.urlCat.map(x => [x.k, x.n, pc(x.pct), x.blk, x.alert]), {tall: true, r: [2]}))}
  ${tb ? panel("c12", `<select class="pick" id="stop" aria-label="Tabel periode">${tabs.map(t => `<option value="${esc(t.id)}" ${t.id === tb.id ? "selected" : ""}>${esc(t.t)}</option>`).join("")}</select>`, `<span class="warn-t">Periode tabel ${dmon(bt.from)} – ${dmon(bt.to)}</span>, tidak mengikuti filter`, tbl(tb.h, tb.r, {tall: true}) + (tb.note ? `<div class="sub">${esc(tb.note)}</div>` : "")) : panel("c12", "Top Report Tables", "", empty("Tidak ada batch valid berisi laporan Top untuk periode ini."))}</div>`;
}

/* ---------- Jadwal & Tim ---------- */
const avHue = s => { let h = 0; for (const c of String(s)) h = (h * 31 + c.charCodeAt(0)) % 360; return h; };
const initials = n => String(n).replace(/[^A-Za-z ]/g, "").split(" ").filter(Boolean).map(w => w[0]).slice(0, 2).join("").toUpperCase() || "?";
const telHref = p => "tel:" + String(p).replace(/[^+\d]/g, "");
const pav = (n, sm) => `<span class="pav ${sm ? "sm" : ""}" style="--h:${avHue(n)}">${esc(initials(n))}</span>`;
const pcard = p => `<article class="pcard" data-q="${esc(((p.name || "") + " " + (p.job || "") + " " + (p.branch || "")).toLowerCase())}">${pav(p.name)}<div class="pb"><b>${esc(p.name)}</b><span class="sub">${esc((p.job || "").replace(/^ITOC /, ""))}${p.branch ? " · " + esc(p.branch) : ""}</span></div>${p.phone ? `<a class="pph" href="${esc(telHref(p.phone))}">${esc(p.phone)}</a>` : ""}</article>`;
function vJadwal() {
  /* Menu Personel (tanpa filter). Sub-menu = parameter "personel" (Admin → Parameter): tiap grup punya jenis shift | office | branch. */
  const now = nowShift(), gs = GROUPS, G = gs.find(g => g.key === S.pers) || gs[0];
  if (!G) return `<div class="grid"><section class="panel c12">${empty("Belum ada kelompok personel. Atur parameter personel di Admin.")}</section></div>`;
  const bar = `<div class="subtabs">${gs.map(g => `<button type="button" data-pers="${esc(g.key)}" aria-selected="${g.key === G.key}">${esc(g.label)}</button>`).join("")}</div>`;
  const group = CFG.people.filter(p => p.unit === G.unit), person = p => `<li><span>${esc(p.name)}<span class="sub"> · ${esc((p.job || "").replace(/^ITOC /, ""))}</span></span><span class="num sub">${esc(p.phone || "")}</span></li>`;
  let body = "";
  if (G.kind === "shift") {
    const first = now.today.slice(0, 8) + "01", mEnd = iso(Date.UTC(+now.today.slice(0, 4), +now.today.slice(5, 7), 0)), days = [];
    for (let d = first; d <= mEnd; d = addDays(d, 1)) days.push(d);
    const head = `<div class="h"></div>` + days.map(d => `<div class="h ${d === now.date ? "today" : ""}">${new Date(dayMs(d)).getUTCDate()}<br>${HR[new Date(dayMs(d)).getUTCDay()]}</div>`).join("");
    const rows = TEAMS.map(g => `<div class="tn">Team ${g}</div>` + days.map(d => { const c = codeOf(g, d), k = CODES[c]; return `<div class="c ${k} ${d === now.date && c === now.shift - 1 ? "today" : ""}" data-tip="${esc("Team " + g + " · " + dlong(d) + "\n" + (k === OFFC ? "Off" : "Shift " + SN[c + 1] + " " + shiftHours(c + 1)))}">${k}</div>`; }).join("")).join("");
    body = `<div class="grid">${panel("c12", "Lead & Supervisor", "", `<div class="pcards">${group.filter(p => !p.team_code).map(pcard).join("") || `<div class="sub">Belum ada data.</div>`}</div>`)}
    ${panel("c4", "On Duty", dlong(now.date) + " · " + now.clock + " WIB", onDuty(now))}
    ${panel("c8", "Shift Schedule " + esc(G.label), rangeMonth(now.today) + " · pola " + esc((CFG.rotation || {}).pattern || ""), `<div class="scroll"><div class="sched" style="grid-template-columns:72px repeat(${days.length},minmax(30px,1fr))">${head}${rows}</div></div>
      <div class="legend">${[...CFG.shifts.map(x => [x.code, x.name + " " + shiftHours(x.no)]), [OFFC, "Off"]].map(([k, l]) => `<span><b class="sw ${k}"></b>${l}</span>`).join("")}</div>`)}
    ${TEAMS.map(g => { const c = codeOf(g, now.date); return panel("c3 shcard " + (c === OFF ? "sh-off" : "sh" + c), "Team " + g, c === OFF ? `<span class="shb"><i></i>Off</span>` : `<span class="shb"><i></i>${esc(SN[c + 1])}</span>`, `<ul class="plist">${crew(g).map(person).join("")}</ul>`); }).join("")}
    </div>`;
  } else if (G.kind === "office") {
    const dow = new Date(dayMs(now.today)).getUTCDay(), open = (G.days || []).includes(dow) && now.clock >= G.start && now.clock < G.end;
    body = `<div class="grid">${panel("c12", esc(G.label), "",
      `<div class="hchips">${(CFG.params["report.contact"] || {}).phone ? `<a class="hchip link" href="${esc(telHref(CFG.params["report.contact"].phone))}"><i></i>${esc(CFG.params["report.contact"].phone)}</a>` : ""}${(CFG.params["report.contact"] || {}).email ? `<a class="hchip link" href="mailto:${esc(CFG.params["report.contact"].email)}"><i></i>${esc(CFG.params["report.contact"].email)}</a>` : ""}</div>` +
      (group.length ? `<div class="pcards">${group.map(pcard).join("")}</div>` : `<div class="empty sm">Belum ada anggota.</div>`))}</div>`;
  } else {
    const by = new Map(); group.forEach(p => { const k = p.branch || "Shared"; if (!by.has(k)) by.set(k, []); by.get(k).push(p); });
    const ord = k => { const i = CFG.sites.indexOf(k); return i < 0 ? 999 : i; }, ob = V.open_by_site || {}, totOpen = [...by.keys()].reduce((a, k) => a + (ob[k] || 0), 0);
    const cards = [...by.entries()].sort((a, b) => ord(a[0]) - ord(b[0])).map(([k, ps]) => { const o = ob[k] || 0, tone = o === 0 ? "good" : o < 5 ? "warn" : "crit";
      return `<article class="bcard pcard" data-q="${esc((k + " " + ps.map(p => p.name).join(" ")).toLowerCase())}"><header><b>${esc(k.replace(/^Branch /, ""))}</b><span class="obadge ${tone}" title="Tiket open di branch">${o} open</span></header>${ps.map(p => `<div class="brow">${pav(p.name, 1)}<span class="pb"><b>${esc(p.name)}</b></span>${p.phone ? `<a class="pph" href="${esc(telHref(p.phone))}">${esc(p.phone)}</a>` : ""}</div>`).join("")}</article>`; }).join("");
    body = `<div class="grid">${panel("c12", esc(G.label), `<span class="hchips"><span class="hchip"><i></i>${by.size} lokasi</span><span class="hchip"><i></i>${group.length} orang</span><span class="hchip ${totOpen ? "warn" : ""}"><i></i>${totOpen} tiket open</span></span>`, `<input type="search" id="mq" class="msearch" placeholder="Cari nama atau lokasi" aria-label="Search"><div class="bcards">${cards || `<div class="empty sm">Belum ada anggota.</div>`}</div>`)}</div>`;
  }
  return bar + body;
}const rangeMonth = d => MB[+d.slice(5, 7) - 1] + " " + d.slice(0, 4);
/* ---------- Serah terima ---------- */
function vHo() { return subnav("report") + vHoBody(); }
function vHoBody() {
  const inF = h => h.date >= S.from && h.date <= S.to && (!S.sf || h.shift === S.sf) && (!S.site || h.site === S.site);
  const L = (V.handover || []).filter(h => inF(h) && (S.hoSt === "all" || (S.hoSt === "open") === h.open)).sort((a, b) => b.at - a.at);
  const now = nowShift(), nx = now.shift % NS + 1, openT = V.open_tickets || [];
  const form = `<form id="hoF" class="form" novalidate>
    <div class="fld"><label>From</label><div class="ro">Shift ${SN[now.shift]} · Team ${teamOn(now.date, now.shift)}</div></div>
    <div class="fld"><label>To</label><div class="ro">Shift ${SN[nx]} · Team ${teamOn(now.shift === NS ? addDays(now.date, 1) : now.date, nx)}</div></div>
    <div class="fld"><label for="hCat">Category *</label><select id="hCat" required><option value="">Pilih…</option>${CFG.params["ho.categories"].map(x => `<option>${esc(x)}</option>`).join("")}</select></div>
    <div class="fld"><label for="hPr">Priority *</label><select id="hPr" required><option value="">Pilih…</option>${CFG.params["ho.priorities"].map(x => `<option>${esc(x.value)}</option>`).join("")}</select></div>
    <div class="fld"><label for="hSite">Location *</label><select id="hSite" required><option value="">Pilih…</option>${CFG.sites.map(s => `<option ${s === S.site ? "selected" : ""}>${esc(s)}</option>`).join("")}</select></div>
    <div class="fld"><label for="hTk">Related Ticket</label><select id="hTk"><option value="">Tidak ada</option>${openT.map(t => `<option value="${esc(t.id)}">#${esc(t.id)} · ${esc(String(t.subject).slice(0, 48))}</option>`).join("")}</select></div>
    <div class="fld wide"><label for="hTitle">Judul * <span class="sub">min. ${CFG.params["ho.rules"].min_title} karakter</span></label><input type="text" id="hTitle" maxlength="120" placeholder="Contoh: Link Astinet Meulaboh down, menunggu ISP"></div>
    <div class="fld wide"><label for="hBody">Kondisi dan yang sudah dilakukan * <span class="sub">min. ${CFG.params["ho.rules"].min_body} karakter</span></label><textarea id="hBody" placeholder="Apa yang terjadi, sejak kapan, sudah eskalasi ke siapa"></textarea></div>
    <div class="fld wide"><label for="hNext">Follow-up for Next Shift</label><input type="text" id="hNext" placeholder="Apa yang harus dicek atau dikerjakan"></div>
    <div class="acts wide"><button class="btn" type="submit">Save Handover</button><button class="btn ghost" type="button" data-hoform="0">Cancel</button><span class="msg err" id="hMsg"></span></div></form>`;
  return `<div class="grid">${panel("c12", "Hand Over Shift", ctxTxt(), `<div class="toolbar"><div class="seg" id="hoSt">${[["open", "Open"], ["closed", "Close"], ["all", "All"]].map(([k, l]) => `<button type="button" data-ho="${k}" aria-pressed="${S.hoSt === k}">${l}</button>`).join("")}</div>${S.hoForm ? "" : `<button class="btn" data-hoform="1">+ Handover baru</button>`}</div>${S.msg ? `<div class="msg ok">${esc(S.msg)}</div>` : ""}${S.hoForm ? `<div class="formbox">${form}</div>` : ""}${hoList(L)}`)}</div>`;
}

/* ---------- Data (kelengkapan + unggah RAW) ---------- */
const canUp = k => { const u = CFG.me.uploads || []; return u.includes("*") || u.includes(k); };
function upCards() {
  const C = [
    ["soc", "Cyber Security · Panorama", "CSV Panorama, banyak file atau .zip", "upf", ".csv,.zip", true, "Choose CSV / ZIP", "upmsg"],
    ["tickets", "Ticketing · ManageEngine", "Ekspor ManageEngine .xls / .xlsx", "upt", ".xls,.xlsx", false, "Choose XLS / XLSX", "upmsg2"],
    ["prtg", "Networking · PRTG", "PDF laporan harian PRTG, banyak file atau .zip", "upn", ".pdf,.zip", true, "Choose PDF / ZIP", "upmsg3"]
  ].filter(c => canUp(c[0]));
  if (!C.length) return `<div class="empty sm">Tidak ada izin unggah.</div>`;
  return `<div class="uploads">${C.map(([, ttl, hint, id, acc, multi, btn, msg]) => `<div class="drop"><b>${ttl}</b><span class="sub">${hint}</span><label class="btn upbtn" for="${id}">${btn}</label><input type="file" id="${id}" accept="${acc}" ${multi ? "multiple" : ""} class="vh"><div id="${msg}"></div></div>`).join("")}</div>`;
}
function vData() { return subnav("report") + vDataBody(); }
function vDataBody() {
  const days = []; for (let d = S.from; d <= S.to && days.length < 62; d = addDays(d, 1)) days.push(d);
  const rows = (V.coverage || []).map(r => [esc(r.label), d => r.cells[d] || ["wait", "–"]]);
  const grid = `<div class="scroll"><div class="mx" style="grid-template-columns:minmax(150px,220px) repeat(${days.length},minmax(22px,1fr))"><div></div>${days.map(d => `<div class="h">${new Date(dayMs(d)).getUTCDate()}</div>`).join("")}
    ${rows.map(([l, f]) => `<div class="rl">${l}</div>` + days.map(d => { const [k, t] = f(d); return `<span class="c ${k}" data-tip="${esc(dlong(d) + "\n" + t)}"></span>`; }).join("")).join("")}</div></div>
    <div class="legend">${[["ok", "Lengkap"], ["dup", "Lengkap dengan catatan"], ["bad", "Gagal / kurang"], ["miss", "Tidak ada"], ["wait", "Belum waktunya"]].map(([k, l]) => `<span><b class="c ${k}"></b>${l}</span>`).join("")}</div>`;
  const bl = (V.batches || []).slice().reverse().map(b => [b.file, dmon(b.from) + " – " + dmon(b.to), b.by, dtime(b.at), b.rows, b.skipped, {h: b.issues.some(i => i.k === "crit") ? pill("crit", "Gagal, tidak dipakai") : b.issues.length ? pill("warn", "Dipakai, ada catatan") : pill("good", "Valid")}, {h: b.issues.map(i => `<div class="sub">${esc(i.t)}</div>`).join("") || "–"}]);
  return `<div class="grid">${panel("c12", "Data Completeness per Day", ctxTxt(APPLY.kelengkapan), grid)}
  ${panel("c12", "Raw Data Upload", "", upCards())}  ${panel("c12", "Sync and Upload Log", CFG.me.is_admin ? `<span class="acts"><button class="btn ghost" data-sync="manageengine">Sync ManageEngine</button><button class="btn ghost" data-sync="prtg">Sync PRTG</button></span>` : "Terbaru di atas", tbl(["Waktu", "Sumber", "Status", "Baris", "Keterangan"], (V.sync_log || []).slice(0, 12).map(x => [dtime(x.at), x.src, {h: x.ok ? pill("good", "OK") : pill("crit", "Gagal")}, x.rows, x.msg]), {tall: true}))}
  ${panel("c12", "SOC Upload History", "", tbl(["File", "Periode", "Diunggah oleh", "Waktu", "Baris terbaca", "Dilewati", "Status", "Catatan"], bl))}</div>`;
}

/* ---------- Report (unduh Excel / PDF / PowerPoint) ---------- */
const fk = (v, k) => v == null || v === "" ? "–" : k === "n" ? fmt(v) : /^f\d$/.test(k) ? fx(v, +k[1]) : /^p\d$/.test(k) ? pc(v, +k[1]) : esc(v);
function vReport() {
  const rp = V.report || {sections: [], kinds: []}, kinds = rp.kinds || [], nav = subnav("report");
  if (!kinds.length) return nav + `<div class="grid"><section class="panel c12">${empty("Tidak ada laporan yang boleh diakses role ini.")}</section></div>`;
  if (!kinds.some(k => k.key === S.rkind)) S.rkind = kinds[0].key;
  const kind = S.rkind, shown = rp.sections.filter(s => kind === "full" || (kind === "summary" ? s.key === "ringkasan" : s.key === kind));
  const chips = `<div class="chips">${kinds.map(k => `<button type="button" class="chip" data-rkind="${esc(k.key)}" aria-pressed="${k.key === kind}" title="${esc(k.desc)}">${esc(k.label)}</button>`).join("")}</div>`;
  const pre = `<div class="chips sm">${[["ringkas", "Compact"], ["standar", "Standard"], ["lengkap", "Full"]].map(([k, l]) => `<button type="button" class="chip" data-rpreset="${k}" aria-pressed="${k === S.rpreset}">${l}</button>`).join("")}</div>`;
  const dl = `<div class="rdl">${[["xlsx", "Excel"], ["pdf", "PDF"], ["pptx", "PowerPoint"]].map(([k, l]) => `<button type="button" class="btn" data-rep="${k}">${l}</button>`).join("")}</div>`;
  const kp = shown.flatMap(s => s.kpis).slice(0, 12), nc = shown.reduce((a, s) => a + s.charts.length, 0), nt = shown.reduce((a, s) => a + s.tables.length, 0);
  const prev = `<div class="rkpi">${kp.map(k => `<div class="kpi"><span class="lbl">${esc(k.label)}</span><span class="v">${fk(k.value, k.kind)}</span><span class="d">${esc(k.sub || "")}</span></div>`).join("")}</div><div class="sub">${nc} grafik · ${nt} tabel</div>`;
  return nav + `<div class="grid">${panel("c12", "Report", ctxTxt(), `<div class="rtop">${chips}${pre}</div><div class="rtop">${dl}</div>${prev}`)}</div>`;
}
/* ---------- Admin ---------- */
function vAdmin() {
  const sub = [["pengguna", "Users"], ["roles", "Roles"], ["integrasi", "Integrations"], ["apikeys", "API Keys"], ["smtp", "Email"], ["webhooks", "Webhooks"], ["parameter", "Parameters & Targets"], ["rumus", "Formula Definitions"], ["audit", "Audit Log"], ["master", "Master Data"]];
  let body = "";
  const eu = S.editUser ? (V.users || []).find(x => x.u === S.editUser) : null;
  if (S.adm === "pengguna") body = `${S.msg ? `<div class="msg ok">${esc(S.msg)}</div>` : ""}<div class="toolbar"><button class="btn" data-adduser>+ Add User</button></div>
    ${S.addUser || eu ? `<form id="uF" class="form formbox"><div class="fld"><label for="uU">Username *</label><input id="uU" type="text" value="${eu ? esc(eu.u) : ""}" ${eu ? "readonly" : ""}></div><div class="fld"><label for="uN">Name *</label><input id="uN" type="text" value="${eu ? esc(eu.name) : ""}"></div><div class="fld"><label for="uR">Role *</label><select id="uR" ${eu && eu.u === CFG.me.username ? "disabled" : ""}>${Object.entries(ROLES).map(([k, v]) => `<option value="${k}" ${eu && eu.role === k ? "selected" : ""}>${v}</option>`).join("")}</select></div><div class="fld"><label for="uS">Branch (EOS only)</label><select id="uS"><option value="">–</option>${CFG.sites.map(x => `<option ${eu && eu.site === x ? "selected" : ""}>${esc(x)}</option>`).join("")}</select></div><div class="acts wide"><button class="btn" type="submit">Save</button><button class="btn ghost" type="button" data-adduser>Cancel</button>${eu ? "" : `<span class="sub">Password awal dibuat acak dan wajib diganti saat login pertama.</span>`}<span class="msg err" id="uMsg"></span></div></form>` : ""}
    <div class="ucards">${V.users.map(u => `<article class="ucard ${u.active ? "" : "off"}"><span class="av">${esc((u.name || u.u).split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase())}</span><div class="ub"><b>${esc(u.name)}</b><span class="sub">@${esc(u.u)} · ${esc(ROLES[u.role] || u.role)}${u.site ? " · " + esc(u.site) : ""}</span><span class="sub" title="${esc(roleAccess(u.role))}">${u.active ? "Active" : "Inactive"} · last login ${esc(dtime(u.last))}</span></div><span class="acts"><button class="btn ghost" data-edit-user="${esc(u.u)}">Edit</button>${u.u === CFG.me.username ? "" : `<button class="btn ghost" data-toggle-user="${esc(u.u)}">${u.active ? "Disable" : "Enable"}</button><button class="btn ghost" data-reset-user="${esc(u.u)}">Reset</button>`}</span></article>`).join("")}</div>`;
  if (S.adm === "integrasi") body = vIntegrations();
  if (S.adm === "apikeys") body = vApiKeys();
  if (S.adm === "smtp") body = vSmtp();
  if (S.adm === "webhooks") body = vWebhooks();
  if (S.adm === "roles") body = `<p class="sub">Menu, hak tulis, lingkup lokasi, dan izin unggah per role. Tambah role baru untuk akses khusus.</p>${masterView("role")}`;
  if (S.adm === "parameter") body = paramForm();
  if (S.adm === "rumus") body = masterView("formula");
  if (S.adm === "master") body = masterView();
  if (S.adm === "audit") body = tbl(["Waktu", "Pengguna", "Aktivitas"], (V.audit || []).map(a => [dtime(a.at), a.by, a.t]));
  return `<div class="grid"><section class="panel c12"><div class="subtabs">${sub.map(([k, l]) => `<button type="button" data-adm="${k}" aria-selected="${S.adm === k}">${l}</button>`).join("")}</div>${body}</section></div>`;
}

