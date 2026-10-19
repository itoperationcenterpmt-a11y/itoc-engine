/* ITOC Dashboard — inti frontend. Tidak ada data atau parameter yang tertanam:
   semuanya dari GET /api/config (master & parameter) dan GET /api/view/<halaman> (angka hasil hitung server). */
"use strict";
const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
const nf = new Intl.NumberFormat("id-ID"), fmt = n => nf.format(Math.round(n || 0));
const fx = (n, d = 1) => n == null || isNaN(n) ? "–" : n.toLocaleString("id-ID", {minimumFractionDigits: d, maximumFractionDigits: d});
const pc = (n, d = 1) => n == null || isNaN(n) ? "–" : fx(n * 100, d) + "%";
const pad = n => String(n).padStart(2, "0");
const dayMs = s => Date.parse(s + "T00:00:00Z"), iso = ms => new Date(ms).toISOString().slice(0, 10);
const addDays = (s, n) => iso(dayMs(s) + n * 864e5);

let CFG = null, V = {}, PAR, MB = [], HR = [], TABS = [], APPLY = {}, PRESETS = [], SN = [], SC = [], NS = 3, CODES = [], OFFC = "O", OFF = 3, TEAMS = [], ROLES = {}, RUMUS = {}, DIMS = {}, MODS = {}, NST = {}, UST = {}, GROUPS = [], BRAND = "Dashboard IT Pelindo Multi Terminal", BSPLIT = 2, FOOT = "";
const dmon = s => { const d = new Date(dayMs(s)); return d.getUTCDate() + " " + MB[d.getUTCMonth()]; };
const dfull = s => { const d = new Date(dayMs(s)); return d.getUTCDate() + " " + MB[d.getUTCMonth()] + " " + d.getUTCFullYear(); };
const dlong = s => { const d = new Date(dayMs(s)); return HR[d.getUTCDay()] + ", " + d.getUTCDate() + " " + MB[d.getUTCMonth()] + " " + d.getUTCFullYear(); };
const dtime = ms => { if (ms == null) return "–"; const d = new Date(ms); return d.getUTCDate() + " " + MB[d.getUTCMonth()] + " " + pad(d.getUTCHours()) + "." + pad(d.getUTCMinutes()); };
const hm = ms => { const d = new Date(ms); return pad(d.getUTCHours()) + "." + pad(d.getUTCMinutes()); };

/* ---------- API ---------- */
const API = {token: localStorage.getItem("itoc.token") || ""};
async function api(path, o = {}) {
  const h = Object.assign({}, o.body && !(o.body instanceof FormData) ? {"Content-Type": "application/json"} : {}, API.token ? {Authorization: "Bearer " + API.token} : {});
  const r = await fetch(path, Object.assign({}, o, {headers: h}));
  const j = (r.headers.get("content-type") || "").includes("json") ? await r.json() : null;
  if (r.status === 401 && !path.startsWith("/api/auth/login")) { logout(j && j.detail); throw new Error("Sesi berakhir"); }
  if (!r.ok) throw new Error(j ? (typeof j.detail === "string" ? j.detail : (j.detail || []).map(x => x.msg || x).join("; ")) : r.statusText);
  return j;
}
const send = (path, body, method = "POST") => api(path, {method, body: body instanceof FormData ? body : JSON.stringify(body)});

/* ---------- konfigurasi dari server ---------- */
function applyConfig(c) {
  CFG = c; const P = c.params;
  PAR = c.par; MB = P["ui.months"]; HR = P["ui.weekdays_short"];
  MODS = Object.fromEntries(c.modules.map(m => [m.key, m]));
  TABS = c.modules.map(m => [m.key, m.label, m.badge]);
  APPLY = Object.fromEntries(c.modules.map(m => [m.key, Object.assign({p: 0, s: 0, l: 0, c: 0}, m.filters, {note: m.note, why: m.why})]));
  PRESETS = P["ui.presets"];
  SN = ["All", ...c.shifts.map(s => s.name)]; SC = ["", ...c.shifts.map(s => s.code)]; NS = c.shifts.length;
  OFFC = (c.rotation || {}).off_code || "O"; CODES = [...c.shifts.map(s => s.code), OFFC]; OFF = NS;
  TEAMS = c.teams.map(t => t.code);
  ROLES = Object.fromEntries(Object.values(c.roles).map(r => [r.key, r.label]));
  RUMUS = Object.fromEntries(c.formulas.map(f => [f.key, f.text]));
  GROUPS = (P.personel || {}).groups || []; BRAND = P["ui.brand_name"] || BRAND; BSPLIT = +P["ui.brand_split"] || BSPLIT; FOOT = P["ui.footer"] || FOOT;
  DIMS = P["sd.dims"]; NST = P["net.status_labels"]; UST = P["net.util_labels"];
}
const SHIFTS = () => [...CFG.shifts].sort((a, b) => a.start - b.start);
const shiftOf = h => { const L = SHIFTS(); let cur = L[L.length - 1]; for (const s of L) if (h >= s.start) cur = s; return cur.no; };
const shiftHours = i => { const L = SHIFTS(), k = L.findIndex(s => s.no === i); return k < 0 ? "" : pad(L[k].start) + ".00–" + pad(L[(k + 1) % L.length].start) + ".00"; };
const nowMs = () => Date.now() + (CFG ? CFG.params.tz_offset_hours : 7) * 36e5;
function nowShift() { const j = nowMs(), h = new Date(j).getUTCHours(); return {date: iso(j - SHIFTS()[0].start * 36e5), today: iso(j), shift: shiftOf(h), clock: hm(j)}; }
/* indeks kode shift (0..NS-1) atau OFF, menurut pola rotasi di Admin → Parameter → rotation */
function codeOf(g, date) {
  const R = CFG.rotation || {}, t = CFG.teams.find(x => x.code === String(g)); if (!R.pattern || !t) return OFF;
  const diff = Math.round((dayMs(date) - dayMs(R.anchor)) / 864e5) + (t.offset || 0) * (R.team_step || 0), L = R.pattern.length;
  const k = CODES.indexOf(R.pattern[((diff % L) + L) % L]); return k < 0 ? OFF : k;
}
const teamOn = (date, shift) => TEAMS.find(g => codeOf(g, date) === shift - 1) || "–";
const crew = g => CFG.people.filter(p => p.team_code === String(g)).sort((a, b) => b.is_coordinator - a.is_coordinator);
const prTone = v => ((CFG.params["ho.priorities"] || []).find(x => x.value === v) || {}).tone || "low";
const roleAccess = k => { const r = CFG.roles[k]; if (!r) return "–"; return r.modules.includes("*") ? "All" : r.modules.map(m => (MODS[m] || {label: m}).label).join(", "); };

/* ---------- state + filter seragam ---------- */
const S = {tab: "", pers: "", rkind: "", rpreset: "standar", layEdit: false, layRole: "", preset: "", from: "", to: "", sf: 0, site: "", cmp: false, dim: "kategori", sdim: "type", stop: "", sensor: "", hoSt: "open", adm: "pengguna", hoForm: false, closing: null, msg: "", addUser: false, params: null, mkey: "", mdata: null, medit: null};
function setPreset(p) {
  const t = nowShift().today, d = new Date(dayMs(t)); S.preset = p;
  if (p === "hari") S.from = S.to = t;
  else if (p === "kemarin") S.from = S.to = addDays(t, -1);
  else if (p === "bulan") { S.from = t.slice(0, 8) + "01"; S.to = t; }
  else if (p === "lalu") { S.from = iso(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() - 1, 1)); S.to = iso(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), 0)); }
  else if (/^\d+$/.test(p)) { S.from = addDays(t, 1 - +p); S.to = t; }
}
function readHash() {
  const [tab, q] = location.hash.slice(1).split("?"); S.tab = TABS.some(t => t[0] === tab) ? tab : TABS[0][0];
  const p = new URLSearchParams(q || ""); setPreset(p.get("p") || CFG.params["ui.default_preset"]);
  if (p.get("dari") && p.get("sampai") && !p.get("p")) { S.preset = ""; S.from = p.get("dari"); S.to = p.get("sampai"); }
  S.sf = +p.get("shift") || 0; S.site = CFG.me.site || p.get("lokasi") || ""; S.cmp = p.get("banding") === "1";
}
function writeHash() {
  const p = new URLSearchParams(); if (S.preset) p.set("p", S.preset); else { p.set("dari", S.from); p.set("sampai", S.to); }
  if (S.sf) p.set("shift", S.sf); if (S.site) p.set("lokasi", S.site); if (S.cmp) p.set("banding", "1");
  history.replaceState(null, "", "#" + S.tab + "?" + p.toString());
}
const nDays = () => Math.round((dayMs(S.to) - dayMs(S.from)) / 864e5) + 1;
const prevRange = () => ({from: addDays(S.from, -nDays()), to: addDays(S.from, -1)});
const rangeTxt = () => (S.from === S.to ? dfull(S.from) : dmon(S.from) + " – " + dfull(S.to));
const ctxTxt = (ap) => { ap = ap || APPLY[S.tab]; return rangeTxt() + (ap.s && S.sf ? " · shift " + SN[S.sf] : "") + (ap.l && S.site ? " · " + S.site : ""); };

/* ---------- hasil hitung server (bundel /api/view) ---------- */
const tkR = r => r && r !== S ? V.tk_prev : V.tk;
const netR = r => r && r !== S ? V.net_prev : V.net;
const netB = () => V.net_base;
const socR = r => r && r !== S ? V.soc_prev : V.soc;
const socCheck = () => V.soc_check || [];
const batchFor = () => V.soc_batch;
