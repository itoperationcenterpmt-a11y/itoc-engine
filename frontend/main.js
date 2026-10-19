/* IT PMT Dashboard — render, event, Admin (parameter & master data generik), login. */
"use strict";
const VIEWS = {report: vReport, ringkasan: vRingkasan, servicedesk: vSD, noc: vNoc, soc: vSoc, jadwal: vJadwal, serahterima: vHo, kelengkapan: vData, admin: vAdmin};
function openSheet(on) { $("sheet").hidden = !on; $("moreBtn").setAttribute("aria-expanded", on); document.body.style.overflow = on ? "hidden" : ""; }
document.addEventListener("keydown", e => { if (e.key === "Escape" && !$("sheet").hidden) openSheet(false); });
const RELOAD = ["tab", "preset", "from", "to", "sf", "site", "cmp", "sensor", "rpreset"];
let seq = 0;
async function render(reload) {
  writeHash(); renderShell();
  if (reload) {
    const q = new URLSearchParams({from: S.from, to: S.to, shift: S.sf, site: S.site, cmp: S.cmp, sensor: S.sensor, preset: S.rpreset}), my = ++seq;
    $("view").classList.add("loading");
    try { const v = await api(`/api/view/${S.tab}?${q}`); if (my !== seq) return; V = v; }
    catch (e) { if (my === seq) $("view").innerHTML = `<div class="grid"><section class="panel c12">${empty(esc(e.message))}</section></div>`; return; }
    finally { if (my === seq) $("view").classList.remove("loading"); }
    renderShell();
  }
  try { $("view").innerHTML = VIEWS[S.tab](); if (S.tab === "admin" && !CFG.me.is_admin) lockAdmin(); applyLayout(); } catch (e) { console.error(e); $("view").innerHTML = `<div class="grid"><section class="panel c12">${empty("Gagal menampilkan halaman: " + esc(e.message))}</section></div>`; }
}
/* Admin hanya-baca (role dengan admin_view tanpa is_admin): semua kontrol ubah disembunyikan; server tetap menolak perubahan. */
function lockAdmin() {
  const v = $("view");
  v.querySelectorAll("[data-adduser],[data-edit-user],[data-reset-user],[data-toggle-user],[data-resetuser],[data-w],[data-toggleuser],[data-medit],[data-mdel],[data-sync],form button[type=submit]").forEach(e => e.hidden = true);
  v.querySelectorAll("form input, form select, form textarea").forEach(e => e.disabled = true);
  v.insertAdjacentHTML("afterbegin", `<div class="msg" style="margin-bottom:10px">Hanya baca</div>`);
}
async function downloadReport(kind, btn) {
  const q = new URLSearchParams({from: S.from, to: S.to, shift: S.sf, site: S.site, kind: S.rkind || "full", preset: S.rpreset}), old = btn.innerHTML;
  btn.disabled = true; btn.textContent = "Menyiapkan…";
  try {
    const r = await fetch(`/api/report/${kind}?${q}`, {headers: {Authorization: "Bearer " + API.token}});
    if (!r.ok) { let msg = r.statusText; try { const j = await r.json(); if (typeof j.detail === "string") msg = j.detail; } catch (_) {} throw new Error(msg); }
    const blob = await r.blob(), a = document.createElement("a"), cd = r.headers.get("content-disposition") || "", nm = (cd.match(/filename="([^"]+)"/) || [])[1];
    a.href = URL.createObjectURL(blob); a.download = nm || "laporan." + kind; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 5000);
  } finally { btn.innerHTML = old; btn.disabled = false; }
}
/* Tata letak halaman (widget): urutan, ukuran, judul, tampil/sembunyi per role. Admin mengatur lewat tombol Customize; tersimpan di tabel layout. */
const LAYOUT_PAGES = ["ringkasan", "servicedesk", "noc", "soc"], SIZES = [["c3", "S"], ["c4", "M"], ["c6", "L"], ["c8", "XL"], ["c12", "Full"]], SZ = /\bc(?:3|4|5|6|7|8|12)\b/g;
const slug = s => (s || "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
const nearest = c => { const n = +(String(c).slice(1)) || 12; return SIZES.reduce((a, s) => Math.abs(+s[0].slice(1) - n) < Math.abs(+a[0].slice(1) - n) ? s : a)[0]; };
function layoutRows(page, role) {
  const L = CFG.layouts || [], mine = L.filter(r => r.page === page && r.role === role);
  return mine.length ? mine : L.filter(r => r.page === page && r.role === "");
}
function applyLayout() {
  const v = $("view"), on = LAYOUT_PAGES.includes(S.tab);
  $("layBtn").hidden = !(on && CFG.me.is_admin); $("laybar").innerHTML = "";
  if (!on) return;
  const els = [...v.querySelectorAll(":scope > .grid > .panel, :scope > .grid > .stack > .panel, :scope > .kpis")];
  if (!els.length) return;
  const grid = document.createElement("div"); grid.className = "grid lay" + (S.layEdit ? " lay-edit" : "");
  const role = S.layEdit ? S.layRole : CFG.me.role, byKey = Object.fromEntries(layoutRows(S.tab, role).map(r => [r.key, r])), seen = {};
  const blocks = els.map((el, i) => {
    let key, blk = el, h2 = null, dsize = (el.className.match(SZ) || ["c12"])[0];
    if (el.classList.contains("kpis")) { key = "kpis"; blk = document.createElement("div"); blk.className = "c12"; blk.appendChild(el); dsize = "c12"; }
    else { h2 = el.querySelector(":scope > header h2"); if (h2) { const c = h2.cloneNode(true); c.querySelectorAll("select").forEach(s => s.remove()); key = slug(c.textContent) || "detail"; } else key = "block"; }
    seen[key] = (seen[key] || 0) + 1; if (seen[key] > 1) key += "-" + seen[key];
    blk.classList.add("wblock"); blk.dataset.wkey = key; blk.dataset.dsize = dsize; blk.dataset.dtitle = h2 && !h2.querySelector("*") ? h2.textContent : "";
    return {key, blk, h2, i, s: byKey[key] ? byKey[key].sort : 1e6 + i};
  }).sort((a, b) => a.s - b.s || a.i - b.i);
  blocks.forEach(({key, blk, h2}) => {
    const r = byKey[key];
    if (r) {
      if (r.size) { blk.className = blk.className.replace(SZ, "").trim() + " " + r.size; blk.dataset.size = r.size; }
      if (r.title && h2 && !h2.querySelector("*")) h2.textContent = r.title;
      blk.dataset.title = r.title || "";
      if (!r.enabled) { if (S.layEdit) blk.classList.add("off"); else return; }
    }
    grid.appendChild(blk);
  });
  v.prepend(grid);
  v.querySelectorAll(":scope > .grid:not(.lay)").forEach(g => { g.querySelectorAll(".stack").forEach(s => { if (!s.children.length) s.remove(); }); if (!g.children.length) g.remove(); });
  if (!S.layEdit) return;
  grid.querySelectorAll(".wblock").forEach(blk => {
    const t = document.createElement("div"), cur = nearest(blk.dataset.size || blk.dataset.dsize); t.className = "wtools";
    t.innerHTML = `<span class="wdrag" title="Drag to move">⠿ Move</span><button type="button" data-lay="up" title="Move up">▲</button><button type="button" data-lay="down" title="Move down">▼</button><select data-lay-size aria-label="Size">${SIZES.map(([k, l]) => `<option value="${k}" ${k === cur ? "selected" : ""}>${l}</option>`).join("")}</select><input data-lay-title placeholder="Title" value="${esc(blk.dataset.title || "")}" aria-label="Title"><button type="button" data-lay="eye">${blk.classList.contains("off") ? "Show" : "Hide"}</button>`;
    blk.appendChild(t);
    const rz = document.createElement("span"); rz.className = "wresize"; rz.title = "Drag sideways to resize"; blk.appendChild(rz);
  });
  $("laybar").innerHTML = `<div class="laybar"><b>Customize</b><label>Apply to <select id="layRole"><option value="">All roles</option>${Object.values(CFG.roles).map(r => `<option value="${esc(r.key)}" ${r.key === S.layRole ? "selected" : ""}>${esc(r.label)}</option>`).join("")}</select></label><button class="btn" type="button" id="laySave">Save</button><button class="btn ghost" type="button" id="layReset">Reset</button><button class="btn ghost" type="button" id="layCancel">Cancel</button></div>`;
}
function moveBlock(b, dir) {
  const blk = b.closest(".wblock");
  if (dir === "eye") { const off = blk.classList.toggle("off"); b.textContent = off ? "Show" : "Hide"; }
  else if (dir === "up" && blk.previousElementSibling) blk.parentNode.insertBefore(blk, blk.previousElementSibling);
  else if (dir === "down" && blk.nextElementSibling) blk.parentNode.insertBefore(blk.nextElementSibling, blk);
}
// Customize: seret ⠿ untuk memindah, seret sudut kanan bawah untuk mengubah lebar (pointer events: mouse dan sentuh)
let LDRAG = null;
document.addEventListener("pointerdown", e => {
  const t = e.target.closest && e.target.closest(".wdrag,.wresize"); if (!t || !S.layEdit) return;
  const blk = t.closest(".wblock"); LDRAG = {mode: t.classList.contains("wdrag") ? "move" : "size", blk}; blk.classList.add("lifting"); e.preventDefault();
});
document.addEventListener("pointermove", e => {
  if (!LDRAG) return; const {blk, mode} = LDRAG, grid = blk.parentNode;
  if (mode === "size") {
    const g = grid.getBoundingClientRect(), b = blk.getBoundingClientRect(), size = nearest("c" + Math.round((e.clientX - b.left) / g.width * 12));
    if (blk.dataset.size !== size) { blk.className = blk.className.replace(SZ, "").trim() + " " + size; blk.dataset.size = size; const sel = blk.querySelector("[data-lay-size]"); if (sel) sel.value = size; }
  } else {
    const over = document.elementsFromPoint(e.clientX, e.clientY).map(x => x.closest && x.closest(".grid.lay > .wblock")).find(x => x && x !== blk);
    if (over) { const r = over.getBoundingClientRect(), bb = blk.getBoundingClientRect(), sameRow = Math.abs(r.top - bb.top) < 40, after = sameRow ? e.clientX > r.left + r.width / 2 : e.clientY > r.top + r.height / 2; grid.insertBefore(blk, after ? over.nextSibling : over); }
  }
});
const endDrag = () => { if (LDRAG) { LDRAG.blk.classList.remove("lifting"); LDRAG = null; } };
document.addEventListener("pointerup", endDrag); document.addEventListener("pointercancel", endDrag);
async function saveLayout() {
  const blocks = [...$("view").querySelectorAll(".grid.lay > .wblock")].map(b => { const t = (b.dataset.title || "").trim(); return {key: b.dataset.wkey, title: t === (b.dataset.dtitle || "") ? "" : t, size: b.dataset.size || "", enabled: !b.classList.contains("off")}; });
  await send("/api/admin/layout", {page: S.tab, role: S.layRole, blocks}, "PUT");
  await reloadConfig(); set({layEdit: false});
}
async function resetLayout() {
  if (!confirm("Reset this page layout to default?")) return;
  await api("/api/admin/layout/" + S.tab + "?role=" + encodeURIComponent(S.layRole), {method: "DELETE"});
  await reloadConfig(); set({layEdit: false});
}
document.addEventListener("input", e => { const t = e.target; if (t.id === "mq") { const q = t.value.trim().toLowerCase(); document.querySelectorAll(".mcard,.pcard").forEach(c => { c.hidden = !!q && !c.dataset.q.includes(q); }); return; } if (t.dataset && t.dataset.layTitle !== undefined) t.closest(".wblock").dataset.title = t.value; });
const set = (o, keepMsg) => { const re = Object.keys(o).some(k => RELOAD.includes(k) && o[k] !== S[k]); Object.assign(S, o); if (!keepMsg) S.msg = ""; render(re); };
const refresh = (o, keepMsg) => { Object.assign(S, o || {}); if (!keepMsg) S.msg = ""; render(true); };
async function reloadConfig() { applyConfig(await api("/api/config")); }

/* ---------- Admin: parameter generik ---------- */
async function loadParams() { try { S.params = await api("/api/admin/params"); } catch (e) { S.params = []; S.msg = e.message; } render(false); }
function paramField(p) {
  const id = "pp_" + p.key.replace(/\W/g, "_"), u = p.ui || {}, a = `id="${id}" data-key="${esc(p.key)}" data-ed="${p.editor}"`, wide = ["list", "json", "text"].includes(p.editor);
  let inp;
  if (p.editor === "percent") inp = `<input type="number" ${a} step="${(u.step || .01) * 100}" ${u.min != null ? `min="${u.min * 100}"` : ""} ${u.max != null ? `max="${u.max * 100}"` : ""} value="${+(p.value * 100).toFixed(4)}">`;
  else if (p.editor === "number") inp = `<input type="number" ${a} step="${u.step || "any"}" ${u.min != null ? `min="${u.min}"` : ""} ${u.max != null ? `max="${u.max}"` : ""} value="${p.value}">`;
  else if (p.editor === "date") inp = `<input type="date" ${a} value="${esc(p.value)}">`;
  else if (p.editor === "text") inp = `<input type="text" ${a} value="${esc(p.value)}">`;
  else if (p.editor === "list") inp = `<textarea ${a} rows="3">${esc((p.value || []).join("\n"))}</textarea>`;
  else inp = `<textarea ${a} rows="4" class="jsed">${esc(JSON.stringify(p.value, null, 1))}</textarea>`;
  return `<div class="fld ${wide ? "wide" : ""}"><label for="${id}">${esc(p.label)}${p.editor === "percent" ? " (%)" : ""}${p.editor === "list" ? ` <span class="sub">satu per baris</span>` : ""}</label>${inp}${p.description ? `<span class="sub">${esc(p.description)}</span>` : ""}</div>`;
}
function paramForm() {
  if (!S.params) { loadParams(); return `<div class="empty sm">Memuat parameter…</div>`; }
  const groups = [...new Set(S.params.map(p => p.group))];
  return `<form id="pF" class="form">${groups.map(g => `<div class="fld wide pgh"><span class="lbl">${esc(g)}</span></div>` + S.params.filter(p => p.group === g).map(paramField).join("")).join("")}
    <div class="acts wide"><button class="btn" type="submit">Save Parameters</button><span class="sub">Hanya nilai yang berubah yang dikirim. Semua halaman dihitung ulang dan perubahan tercatat di audit log.</span><span class="msg ok" id="pMsg">${esc(S.msg)}</span></div></form>`;
}
function readParam(el) {
  const ed = el.dataset.ed, v = el.value;
  if (ed === "percent") return parseFloat(v) / 100;
  if (ed === "number") return parseFloat(v);
  if (ed === "list") return v.split("\n").map(x => x.trim()).filter(Boolean);
  if (ed === "json") return JSON.parse(v);
  return v.trim();
}

/* ---------- Admin: master data generik (lokasi, personel, tim, shift, ISP, target SLA, sensor, modul, role, rumus, sumber data) ---------- */
async function loadMaster() { try { S.mdata = await api("/api/admin/master/" + S.mkey); } catch (e) { S.mdata = {key: S.mkey, columns: [], rows: [], pk: []}; S.msg = e.message; } render(false); }
const mShow = (v, c) => v == null ? "–" : c.kind === "bool" ? (v ? "Ya" : "–") : c.kind === "json" ? {h: `<span class="num sub">${esc(JSON.stringify(v).slice(0, 80))}</span>`} : c.kind === "int" || c.kind === "float" ? v : String(v);
function mField(c, row, isNew) {
  const id = "mf_" + c.name, v = row[c.name], ro = c.pk && !isNew ? "disabled" : "", a = `id="${id}" data-col="${c.name}" data-kind="${c.kind}" ${ro}`;
  let inp;
  if (c.kind === "bool") inp = `<select ${a}><option value="true" ${v ? "selected" : ""}>Ya</option><option value="false" ${v ? "" : "selected"}>Tidak</option></select>`;
  else if (c.kind === "json") inp = `<textarea ${a} rows="3" class="jsed">${esc(v == null ? "" : JSON.stringify(v, null, 1))}</textarea>`;
  else if (c.kind === "text") inp = `<textarea ${a} rows="2">${esc(v ?? "")}</textarea>`;
  else inp = `<input type="${c.kind === "int" || c.kind === "float" ? "number" : c.kind === "date" ? "date" : "text"}" ${c.kind === "float" ? `step="any"` : ""} ${a} value="${esc(v ?? "")}">`;
  return `<div class="fld ${c.kind === "json" || c.kind === "text" ? "wide" : ""}"><label for="${id}">${esc(c.name)}${c.nullable ? "" : " *"}</label>${inp}</div>`;
}
const mTitle = cols => ["name", "label", "keyword", "key", "title", "code", "username"].map(n => cols.find(c => c.name === n)).find(Boolean) || cols.find(c => c.name !== "id") || cols[0];
function mCard(r, i, cols) {
  const tc = mTitle(cols), skip = new Set([tc.name, "id", "sort"]);
  const meta = cols.filter(c => !skip.has(c.name)).map(c => [c, r[c.name]]).filter(([c, x]) => x != null && x !== "" && x !== false && !(Array.isArray(x) && !x.length));
  const val = ([c, x]) => c.kind === "bool" ? "" : c.kind === "json" ? JSON.stringify(x).replace(/[\[\]"{}]/g, "").slice(0, 46) : String(x).slice(0, 46);
  const chips = meta.slice(0, 5).map(a => `<span class="mchip" title="${esc(a[0].name + ": " + (a[0].kind === "json" ? JSON.stringify(a[1]) : a[1]))}"><i>${esc(a[0].name.replace(/_/g, " "))}</i>${esc(val(a))}</span>`).join("") + (meta.length > 5 ? `<span class="mchip more">+${meta.length - 5}</span>` : "");
  const q = cols.map(c => r[c.name]).join(" ").toLowerCase();
  return `<article class="mcard" data-q="${esc(q)}"><div class="mh"><b>${esc(String(r[tc.name] ?? "–"))}</b>${r.id != null ? `<span class="mid">#${esc(r.id)}</span>` : ""}</div><div class="mchips">${chips || `<span class="sub">–</span>`}</div><button class="btn ghost" type="button" data-medit="${i}">Edit</button></article>`;
}
function masterView(fixed) {
  if (fixed) S.mkey = fixed; else if (!S.mkey) S.mkey = (CFG.master[0] || {}).key;
  const M = S.mdata && S.mdata.key === S.mkey ? S.mdata : null;
  const pick = fixed ? `<b>${esc(((CFG.master || []).find(x => x.key === fixed) || {}).label || fixed)}</b>` : `<div class="mpick">${CFG.master.map(m => `<button type="button" data-mkey="${m.key}" aria-pressed="${m.key === S.mkey}">${esc(m.label)}</button>`).join("")}</div>`;
  if (!M) { loadMaster(); return pick + `<div class="empty sm">Memuat…</div>`; }
  const cols = M.columns, isNew = S.medit && S.medit.__i == null;
  const form = S.medit ? `<form id="mF" class="form formbox">${cols.filter(c => !(c.auto && isNew)).map(c => mField(c, S.medit, isNew)).join("")}
    <div class="acts wide"><button class="btn" type="submit">Save</button><button class="btn ghost" type="button" data-medit="x">Cancel</button>${isNew ? "" : `<button class="btn ghost" type="button" data-mdel>Delete</button>`}<span class="msg err" id="mMsg"></span></div></form>` : "";
  return `<div class="toolbar mbar">${pick}<span class="mtools"><input type="search" id="mq" class="msearch" placeholder="Search ${M.rows.length} rows" aria-label="Search"><button class="btn" type="button" data-medit="new">+ Add</button></span></div>${S.msg ? `<div class="msg">${esc(S.msg)}</div>` : ""}${form}
    <div class="mcards">${M.rows.map((r, i) => mCard(r, i, cols)).join("") || `<div class="empty sm">Belum ada data.</div>`}</div>`;
}
const pkOf = row => S.mdata.pk.map(k => row[k]).join("");

/* ---------- event ---------- */
document.addEventListener("click", async e => {
  const b = e.target.closest("button"); if (!b || b.disabled) return;
  const d = b.dataset;
  try {
    if (b.id === "layBtn") set({layEdit: !S.layEdit, layRole: ""});
    else if (b.id === "laySave") await saveLayout();
    else if (b.id === "layReset") await resetLayout();
    else if (b.id === "layCancel") set({layEdit: false});
    else if (d.lay) moveBlock(b, d.lay);
    else if (b.id === "moreBtn") { openSheet(true); }
    else if (d.closeSheet !== undefined) { openSheet(false); }
    else if (d.tab) { openSheet(false); set({tab: d.tab, hoForm: false, closing: null}); window.scrollTo({top: 0}); }
    else if (d.go) { set({tab: d.go}); window.scrollTo({top: 0}); }
    else if (d.p) { setPreset(d.p); render(true); }
    else if (d.s != null && b.closest("#fShift")) set({sf: +d.s});
    else if (d.pers) set({pers: d.pers});
    else if (d.rkind) set({rkind: d.rkind});
    else if (d.rpreset) set({rpreset: d.rpreset});
    else if (d.rep) await downloadReport(d.rep, b);
    else if (d.ho) set({hoSt: d.ho});
    else if (d.hoform) set({hoForm: d.hoform === "1"});
    else if (d.close) set({closing: +d.close});
    else if (d.closeCancel !== undefined) set({closing: null});
    else if (d.closeOk) { await send(`/api/handover/${d.closeOk}/close`, {note: $("cn").value.trim()}).catch(err => { $("cnmsg").textContent = err.message; throw null; }); refresh({closing: null, msg: "Handover ditutup."}, true); }
    else if (d.mkey) set({mkey: d.mkey, mdata: null, medit: null, msg: ""});
    else if (d.adm) { if (typeof intReset === "function") intReset(); set({adm: d.adm, msg: "", medit: null, mkey: "", mdata: null, addUser: false, editUser: "", params: d.adm === "parameter" ? null : S.params}); }
    else if (d.adduser !== undefined) set({addUser: !S.addUser && !S.editUser, editUser: ""});
    else if (d.editUser) set({editUser: d.editUser, addUser: false});
    else if (d.toggleUser) { const u = V.users.find(x => x.u === d.toggleUser); await send("/api/admin/users/" + encodeURIComponent(u.u), {active: !u.active}, "PATCH"); refresh(); }
    else if (d.resetUser) { if (!confirm("Reset password " + d.resetUser + "?")) return; const r = await send("/api/admin/users/" + encodeURIComponent(d.resetUser), {reset_password: true}, "PATCH"); refresh({msg: `Password awal ${d.resetUser}: ${r.initial_password} (wajib diganti saat login).`}, true); }
    else if (d.medit) { S.msg = ""; set({medit: d.medit === "x" ? null : d.medit === "new" ? {} : Object.assign({__i: +d.medit}, S.mdata.rows[+d.medit])}, true); }
    else if (d.mdel !== undefined) { if (!confirm("Hapus baris ini?")) return; await api(`/api/admin/master/${S.mkey}/${encodeURIComponent(pkOf(S.medit))}`, {method: "DELETE"}).catch(err => { $("mMsg").textContent = err.message; throw null; }); await reloadConfig(); S.mdata = null; refresh({medit: null}); }
    else if (d.sync) { b.disabled = true; b.textContent = "Menyinkron…"; await send("/api/ingest/sync/" + d.sync, {}).catch(err => { alert(err.message); }); refresh(); }
    else if (b.id === "fReset") { S.sf = 0; S.site = CFG.me.site || ""; S.cmp = false; setPreset(CFG.params["ui.default_preset"]); render(true); }
    else if (b.id === "fToggle") { const w = $("fwrap").classList.toggle("open"); b.setAttribute("aria-expanded", w); }
    else if (b.id === "logout" || b.id === "logoutM" || b.id === "logoutS") logout();
    else if (b.id === "theme" || b.id === "themeM" || b.id === "themeS" || b.id === "themeL") { const r = document.documentElement, dark = (r.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")) === "dark"; r.dataset.theme = dark ? "light" : "dark"; }
  } catch (err) { if (err) alert(err.message); }
});
document.addEventListener("change", async e => {
  const t = e.target;
  if (t.id === "fFrom" || t.id === "fTo") { let f = $("fFrom").value, to = $("fTo").value; if (!f || !to) return; if (f > to) [f, to] = [to, f]; set({preset: "", from: f, to}); }
  else if (t.id === "fSite") set({site: t.value});
  else if (t.id === "fCmp") set({cmp: t.checked});
  else if (t.dataset.rkind) set({rkind: t.dataset.rkind});
  else if (t.id === "layRole") set({layRole: t.value});
  else if (t.dataset.laySize !== undefined) { const blk = t.closest(".wblock"); blk.className = blk.className.replace(SZ, "").trim() + " " + t.value; blk.dataset.size = t.value; }
  else if (t.id === "dim") set({dim: t.value});
  else if (t.id === "sdim") set({sdim: t.value});
  else if (t.id === "stop") set({stop: t.value});
  else if (t.id === "sensor") set({sensor: t.value});
  else if (t.id === "mkey") set({mkey: t.value, mdata: null, medit: null});
  else if (t.id === "upf" && t.files.length) {
    const fd = new FormData(); [...t.files].forEach(f => fd.append("files", f));
    $("upmsg").innerHTML = `<div class="msg">Memeriksa ${t.files.length} file…</div>`;
    try { const b = await send("/api/ingest/soc", fd); refresh({msg: ""}); setTimeout(() => { const m = $("upmsg"); if (m) m.innerHTML = `<div class="msg ${b.status === "failed" ? "err" : "ok"}">${esc(b.file)}: ${b.status === "failed" ? "gagal validasi, tidak dipakai di KPI" : "tersimpan"} · ${fmt(b.rows)} baris terbaca${b.skipped ? ", " + fmt(b.skipped) + " dilewati" : ""}.${(b.issues || []).map(i => `<div class="sub">${esc(i.t)}</div>`).join("")}</div>`; }, 400); }
    catch (err) { $("upmsg").innerHTML = `<div class="msg err">${esc(err.message)}</div>`; }
  }
  else if (t.id === "upn" && t.files.length) {
    const fd = new FormData(); [...t.files].forEach(f => fd.append("files", f));
    $("upmsg3").innerHTML = `<div class="msg">Membaca ${t.files.length} file PDF, mohon tunggu…</div>`;
    try { const r = await send("/api/ingest/prtg", fd); refresh({msg: ""}); setTimeout(() => { const m = $("upmsg3"); if (m) m.innerHTML = `<div class="msg ok">${fmt(r.files)} PDF dibaca: ${fmt(r.rows)} data sensor-hari, ${fmt(r.sensors)} sensor, ${r.days.length} hari (${esc(r.days[0])} – ${esc(r.days[r.days.length - 1])}).${(r.notes || []).map(i => `<div class="sub">${esc(i)}</div>`).join("")}</div>`; }, 400); }
    catch (err) { $("upmsg3").innerHTML = `<div class="msg err">${esc(err.message)}</div>`; }
  }
  else if (t.id === "upt" && t.files[0]) {
    const fd = new FormData(); fd.append("file", t.files[0]);
    $("upmsg2").innerHTML = `<div class="msg">Memeriksa <b>${esc(t.files[0].name)}</b>…</div>`;
    try { const r = await send("/api/ingest/tickets", fd); refresh({msg: ""}); setTimeout(() => { const m = $("upmsg2"); if (m) m.innerHTML = `<div class="msg ok">${esc(r.file)}: ${fmt(r.rows)} tiket disimpan atau diperbarui${r.skipped ? ", " + fmt(r.skipped) + " dilewati (tanggal dibuat tidak terbaca)" : ""}.</div>`; }, 400); }
    catch (err) { $("upmsg2").innerHTML = `<div class="msg err">${esc(err.message)}</div>`; }
  }
});
document.addEventListener("submit", async e => {
  e.preventDefault(); const f = e.target, v = id => ($(id) ? $(id).value.trim() : "");
  if (f.id === "hoF") {
    try { await send("/api/handover", {category: v("hCat"), priority: v("hPr"), site: v("hSite"), ticket_id: v("hTk") || null, title: v("hTitle"), body: v("hBody"), next_action: v("hNext")}); refresh({hoForm: false, hoSt: "open", msg: "Handover tersimpan dan terlihat oleh shift berikutnya."}, true); }
    catch (err) { $("hMsg").textContent = err.message; }
  }
  if (f.id === "pF") {
    const errs = [], changed = [];
    f.querySelectorAll("[data-key]").forEach(el => { const p = S.params.find(x => x.key === el.dataset.key); let nv; try { nv = readParam(el); } catch (_) { errs.push(p.label + ": JSON tidak valid"); return; } if (JSON.stringify(nv) !== JSON.stringify(p.value)) changed.push([p, nv]); });
    for (const [p, nv] of changed) { try { await send("/api/admin/params/" + encodeURIComponent(p.key), {value: nv}, "PUT"); } catch (err) { errs.push(p.label + ": " + err.message); } }
    await reloadConfig(); S.params = null;
    refresh({msg: errs.length ? "Sebagian gagal: " + errs.join("; ") : changed.length ? `Tersimpan (${changed.length} parameter). Semua angka dihitung ulang.` : "Tidak ada perubahan."}, true);
  }
  if (f.id === "uF") {
    if (S.editUser) { try { const b = {full_name: v("uN"), site: v("uS") || ""}; if (!$("uR").disabled) b.role_key = v("uR"); await send("/api/admin/users/" + encodeURIComponent(S.editUser), b, "PATCH"); await reloadConfig(); refresh({editUser: "", msg: `Akun ${S.editUser} diperbarui.`}, true); } catch (err) { $("uMsg").textContent = err.message; } return; }
    try { const r = await send("/api/admin/users", {username: v("uU"), full_name: v("uN"), role_key: v("uR"), site: v("uS") || null}); refresh({addUser: false, msg: `Akun ${v("uU")} dibuat. Password awal: ${r.initial_password} (wajib diganti saat login pertama).`}, true); }
    catch (err) { $("uMsg").textContent = err.message; }
  }
  if (f.id === "mF") {
    const row = {}; let bad = "";
    f.querySelectorAll("[data-col]").forEach(el => { if (el.disabled) return; const k = el.dataset.kind, x = el.value;
      if (k === "json") { try { row[el.dataset.col] = x.trim() ? JSON.parse(x) : null; } catch (_) { bad = el.dataset.col + ": JSON tidak valid"; } }
      else if (k === "bool") row[el.dataset.col] = x === "true"; else row[el.dataset.col] = x === "" ? null : x; });
    if (bad) { $("mMsg").textContent = bad; return; }
    try { const isNew = S.medit.__i == null; await send(isNew ? `/api/admin/master/${S.mkey}` : `/api/admin/master/${S.mkey}/${encodeURIComponent(pkOf(S.medit))}`, row, isNew ? "POST" : "PUT");
      await reloadConfig(); S.mdata = null; refresh({medit: null, msg: "Tersimpan."}, true); }
    catch (err) { $("mMsg").textContent = err.message; }
  }
  if (f.id === "loginF") {
    try { const r = await send("/api/auth/login", {username: v("lU"), password: $("lP").value}); API.token = r.token; localStorage.setItem("itoc.token", r.token); boot(); }
    catch (err) { $("lMsg").textContent = err.message; }
  }
  if (f.id === "pwF") {
    if ($("nP").value !== $("nP2").value) { $("lMsg").textContent = "Konfirmasi password tidak sama."; return; }
    try { await send("/api/auth/password", {old: $("oP").value, new: $("nP").value}); boot(); } catch (err) { $("lMsg").textContent = err.message; }
  }
});

/* ---------- tooltip ---------- */
const tip = $("tip");
document.addEventListener("pointerover", e => { const el = e.target.closest("[data-tip]"); if (!el) { tip.hidden = true; return; } tip.textContent = el.dataset.tip; tip.hidden = false; });
document.addEventListener("pointermove", e => { if (tip.hidden) return; const w = tip.offsetWidth, h = tip.offsetHeight; tip.style.left = Math.min(innerWidth - w - 8, e.clientX + 12) + "px"; tip.style.top = (e.clientY + 14 + h > innerHeight ? e.clientY - h - 10 : e.clientY + 14) + "px"; });
document.addEventListener("focusin", e => { const el = e.target.closest(".ib"); if (!el) return; const r = el.getBoundingClientRect(); tip.textContent = el.dataset.tip; tip.hidden = false; tip.style.left = Math.min(innerWidth - tip.offsetWidth - 8, r.left) + "px"; tip.style.top = r.bottom + 6 + "px"; });
document.addEventListener("focusout", () => { tip.hidden = true; });
setInterval(() => { if (!CFG || $("app").hidden) return; const n = nowShift(); $("duty").innerHTML = `<i></i><span>On duty: Team ${teamOn(n.date, n.shift)} · ${SN[n.shift]}<small>${n.clock} WIB</small></span>`; $("dutyM").textContent = `Team ${teamOn(n.date, n.shift)} · ${SN[n.shift]}`; }, 30000);

/* ---------- login & boot ---------- */
function showLogin(msg, change) {
  $("app").hidden = true; $("login").hidden = false;
  const form = change
    ? `<form id="pwF" class="loginbox"><div class="brand"><span class="mk"><img src="assets/logo.png" alt=""></span><h1>Change password</h1></div><span class="sub">Password awal wajib diganti sebelum memakai dashboard.</span>
      <div class="fld"><label for="oP">Current password</label><input type="password" id="oP" autocomplete="current-password"></div><div class="fld"><label for="nP">New password</label><input type="password" id="nP" autocomplete="new-password"></div><div class="fld"><label for="nP2">Repeat new password</label><input type="password" id="nP2" autocomplete="new-password"></div>
      <button class="btn" type="submit">Save</button><span class="msg err" id="lMsg">${esc(msg || "")}</span></form>`
    : `<form id="loginF" class="loginbox"><div class="lhead"><h1>Sign in</h1></div>
      <div class="fld"><label for="lU">Username</label><input type="text" id="lU" autocomplete="username"></div><div class="fld"><label for="lP">Password</label><input type="password" id="lP" autocomplete="current-password"></div>
      <button class="btn" type="submit">Sign in</button><span class="msg err" id="lMsg">${esc(msg || "")}</span></form>`;
      $("login").innerHTML = `<div class="lg"><div class="lg-bg"></div><div class="lg-wrap">
    <section class="lg-card lg-info"><button type="button" class="lg-theme" id="themeL" aria-label="Ganti tema terang/gelap">◐</button>
      ${LOGIN.eyebrow ? `<span class="lg-eyebrow">${esc(LOGIN.eyebrow)}</span>` : ""}<h2>${brandHtml()}</h2>${LOGIN.tagline ? `<p>${esc(LOGIN.tagline)}</p>` : ""}
      ${LOGIN.points.length ? `<ul class="lg-pts">${LOGIN.points.map(x => `<li>${esc(x)}</li>`).join("")}</ul>` : ""}</section>
    <section class="lg-card lg-form"><img class="lg-logo lg-l" src="assets/logo-g2.png" alt="IT Operation Center"><img class="lg-logo lg-d" src="assets/logo-g2-dark.png" alt="">${form}<div class="loginfoot">${esc(footText())}</div></section></div></div>`;
  const first = $("login").querySelector("input"); if (first) first.focus();
}function logout(msg) { API.token = ""; localStorage.removeItem("itoc.token"); CFG = null; showLogin(typeof msg === "string" ? msg : ""); }
const footText = () => FOOT.replace("{year}", new Date().getFullYear());
/* Baris pertama nama utama (tidak dipotong), kata terakhir ("Dashboard") di baris kedua */
/* Nama yang tampil di sidebar dan halaman login = BSPLIT kata pertama ("Dashboard IT"); nama lengkap dipakai di judul tab, laporan, dan email. */
const brandHtml = () => { const w = BRAND.trim().split(/\s+/), n = Math.max(1, Math.min(typeof BSPLIT === "number" ? BSPLIT : 2, w.length)); return `<span class="b1">${esc(w.slice(0, n).join(" "))}</span>`; };
function applyBrand() { document.title = BRAND; document.querySelectorAll(".brandName").forEach(e => e.innerHTML = brandHtml()); }
let LOGIN = {tagline: "", points: [], place: "", eyebrow: ""};
async function loadPublic() { try { const r = await (await fetch("/api/public")).json(); BRAND = r.brand || BRAND; if (typeof BSPLIT === "number") BSPLIT = +r.brand_split || BSPLIT; FOOT = r.footer || FOOT; LOGIN = {tagline: r.tagline || "", points: r.points || [], place: r.place || "", eyebrow: r.eyebrow || ""}; } catch (_) {} applyBrand(); }
async function boot() {
  await loadPublic();
  if (!API.token) return showLogin();
  try { await reloadConfig(); } catch (e) { return showLogin(e.message); }
  if (CFG.me.must_change_pw) return showLogin("", true);
  if (!TABS.length) return showLogin("Role Anda belum punya akses ke halaman mana pun.");
  $("login").hidden = true; $("app").hidden = false;
  $("me").textContent = CFG.me.name; $("av").textContent = CFG.me.name.split(/\s+/).slice(0, 2).map(w => w[0]).join("").toUpperCase(); $("role").textContent = ROLES[CFG.me.role] || CFG.me.role; applyBrand(); $("foot").textContent = footText();
  readHash(); render(true);
}
boot();
