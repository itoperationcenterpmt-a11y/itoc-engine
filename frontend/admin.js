/* Admin menu: grouped pages, roles and access, data that needs completing, source status, and page access (Super Admin lock). */
"use strict";
const ADM = [
  ["akses", "Access", [["pengguna", "Users"], ["roles", "Roles"], ["apikeys", "API Keys"]]],
  ["sumber", "Data Sources", [["integrasi", "Integrations"], ["pemetaan", "Mapping"], ["dilengkapi", "Needs Completion"]]],
  ["operasional", "Operations", [["personel", "Personnel"], ["tim", "Teams & Shifts"], ["parameter", "Targets & Parameters"], ["rumus", "Formulas"]]],
  ["notifikasi", "Notifications", [["smtp", "Email"], ["webhooks", "Webhooks"]]],
  ["sistem", "System", [["audit", "Audit Log"], ["status", "Source Status"], ["menu", "Menus & Widgets"], ["akses", "Page Access"], ["backup", "Backup & Restore"]]]
];
const COLN = {id: "ID", name: "Name", kind: "Type", aliases: "Aliases", active: "Active", sort: "Order", lat: "Latitude", lon: "Longitude", sys_name: "System Name", unit: "Unit", job: "Job Title",
  team_code: "Team Code", branch: "Branch", phone: "Phone", is_coordinator: "Coordinator", is_shared: "Shared", exclude_rank: "Exclude from Ranking", code: "Code", label: "Label",
  rotation_offset: "Rotation Offset", no: "No.", start_hour: "Start Hour", keyword: "Keyword", target: "Target", hours: "Limit (hours)", device: "Location (PRTG Device)", capacity_mbps: "Capacity (Mbps)",
  key: "Key", enabled: "Enabled", filters: "Filters", note: "Note", why: "Reason", parent: "Parent Menu", icon: "Icon", badge: "Badge", notice: "Notice", title: "Title", section: "Section",
  top_n: "Top N", hero: "Featured", presets: "Presets", modules: "Menus", can_write: "Can Edit", is_admin: "Full Admin", uploads: "Upload Types", admin_view: "View Admin", scope: "Scope",
  text: "Formula", source: "Source", mode: "Mode", interval_min: "Interval (min)", config: "Configuration", tip: "Description", site: "Location", description: "Description"};
const colLabel = n => COLN[n] || n.replace(/_/g, " ").replace(/^./, c => c.toUpperCase());

/* Crucial pages are hidden from every role except Super Admin; the list is set in System > Page Access. */
const admVisible = k => CFG.me.is_admin || !((CFG.admin_locked || []).includes(k) || k === "akses");
const admPages = () => ADM.map(([gk, gt, ps]) => [gk, gt, ps.filter(p => admVisible(p[0]))]).filter(g => g[2].length);
const admGroup = k => admPages().find(g => g[2].some(s => s[0] === k)) || admPages()[0] || ADM[0];
function admEnsure() { if (!admVisible(S.adm) || !ADM.some(g => g[2].some(p => p[0] === S.adm))) { const g = admPages()[0]; if (g) S.adm = g[2][0][0]; } }

function admNav() {
  const g = admGroup(S.adm), todo = INT.todo ? INT.todo.total : 0;
  return `<div class="admnav"><div class="subtabs admgrp">${admPages().map(([k, t]) => `<button type="button" data-admgrp="${k}" aria-selected="${g[0] === k}">${t}</button>`).join("")}</div>
    <div class="subtabs">${g[2].map(([k, t]) => `<button type="button" data-adm="${k}" aria-selected="${S.adm === k}">${t}${k === "dilengkapi" && todo ? ` <span class="tag warn">${todo}</span>` : ""}</button>`).join("")}</div></div>`;
}
const admTitle = (t, d) => `<div class="admhead"><h3>${esc(t)}</h3>${d ? `<span class="sub">${esc(d)}</span>` : ""}</div>`;
const admGo = (adm, mkey) => set({adm, mkey: mkey || "", mdata: null, medit: null, msg: "", addUser: false, editUser: "", params: adm === "parameter" ? null : S.params});

/* ---------- Roles and access ---------- */
const ROLE_SCOPE = [["all", "All locations"], ["ho", "Head office only"], ["own", "Account's own location"]];
const ROLE_UPLOAD = [["soc", "SOC data (NDR)"], ["tickets", "Tickets"], ["prtg", "PRTG"]];
const modName = m => { const x = MODS[m]; if (!x) return m; const p = x.parent ? MODS[x.parent] : null; return (p ? p.label + " › " : "") + x.label; };
function vRoles() {
  if (!INT.roles) { intLoad("roles", "master/role"); return intLoading(); }
  const rows = INT.roles.rows.slice().sort((a, b) => (a.sort || 0) - (b.sort || 0)), mods = Object.values(MODS).filter(m => m.key !== "admin");
  const e = INT.roleEdit, can = CFG.me.is_admin;
  const flag = (r, f) => r[f] ? `<span class="ok-t">Yes</span>` : `<span class="sub">–</span>`;
  const form = !e ? "" : `<form class="form formbox" data-role-form>
    <div class="fld"><label for="rK">Key${e.__new ? " *" : ""}</label><input id="rK" type="text" value="${esc(e.key || "")}" ${e.__new ? "" : "readonly"} placeholder="lowercase, no spaces, e.g. auditor"></div>
    <div class="fld"><label for="rL">Role Name *</label><input id="rL" type="text" value="${esc(e.label || "")}"></div>
    <div class="fld wide"><label for="rD">Description (who uses this role)</label><input id="rD" type="text" value="${esc(e.description || "")}"></div>
    <div class="fld wide"><label>Menus this role can open</label><div class="chkgrid"><label class="chk"><input type="checkbox" id="rAll" ${(e.modules || []).includes("*") ? "checked" : ""}> All menus</label>
      ${mods.map(m => `<label class="chk"><input type="checkbox" data-rmod="${esc(m.key)}" ${(e.modules || []).includes("*") || (e.modules || []).includes(m.key) ? "checked" : ""}> ${esc(modName(m.key))}</label>`).join("")}</div></div>
    <div class="fld"><label for="rS">Location scope</label><select id="rS">${intOpt(ROLE_SCOPE, e.scope || "all")}</select></div>
    <div class="fld wide"><label>Permissions</label><div class="chkgrid">
      <label class="chk"><input type="checkbox" id="rW" ${e.can_write ? "checked" : ""}> Can edit (handover and data upload)</label>
      <label class="chk"><input type="checkbox" id="rA" ${e.is_admin ? "checked" : ""}> Super Admin (manage users, settings, integrations)</label>
      <label class="chk"><input type="checkbox" id="rV" ${e.admin_view ? "checked" : ""}> Can open Admin, read-only (unlocked pages only)</label></div></div>
    <div class="fld wide"><label>Data types this role can upload</label><div class="chkgrid">${ROLE_UPLOAD.map(([v, l]) => `<label class="chk"><input type="checkbox" data-rup="${v}" ${(e.uploads || []).includes("*") || (e.uploads || []).includes(v) ? "checked" : ""}> ${l}</label>`).join("")}</div></div>
    <div class="acts wide"><button class="btn" type="submit">Save</button><button class="btn ghost" type="button" data-role="x">Cancel</button>${e.__new || e.key === "superadmin" ? "" : `<button class="btn ghost" type="button" data-role="del">Delete</button>`}<span class="msg err" id="rMsg"></span></div></form>`;
  return intMsg() + admTitle("Roles & Access", "A role controls which menus are visible, whether data can be edited, and the location scope. Each user has one role.") + form + `<div class="toolbar">${can ? `<button class="btn" type="button" data-role="new">+ Add Role</button>` : ""}</div>
    <div class="rolecards">${rows.map(r => `<article class="rcard"><header><b>${esc(r.label)}</b><span class="sub">${esc(r.key)}</span>${can ? `<button class="btn ghost sm" type="button" data-role="edit" data-key="${esc(r.key)}">Edit</button>` : ""}</header>
      <p>${esc(r.description || "No description.")}</p>
      <div class="rflags"><span>Scope: <b>${esc((ROLE_SCOPE.find(x => x[0] === r.scope) || ["", r.scope])[1])}</b></span><span>Edit: ${flag(r, "can_write")}</span><span>Admin: ${r.is_admin ? `<span class="ok-t">Full</span>` : r.admin_view ? `<b>Read-only</b>` : `<span class="sub">–</span>`}</span></div></article>`).join("")}</div>
    <h4 class="admsub">Menus per role</h4><div class="scroll"><table class="matrix"><thead><tr><th>Role</th>${mods.map(m => `<th title="${esc(modName(m.key))}">${esc(m.label)}</th>`).join("")}</tr></thead><tbody>
      ${rows.map(r => `<tr><td><b>${esc(r.label)}</b></td>${mods.map(m => `<td class="${(r.modules || []).includes("*") || (r.modules || []).includes(m.key) ? "yes" : ""}">${(r.modules || []).includes("*") || (r.modules || []).includes(m.key) ? "✓" : ""}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}

/* ---------- Page access (Super Admin lock) ---------- */
function vAccess() {
  const locked = new Set(CFG.admin_locked || []);
  const rows = ADM.flatMap(([, gt, ps]) => ps.filter(p => p[0] !== "akses").map(([k, t]) => [k, gt, t]));
  return intMsg() + admTitle("Page Access", "Checked pages are visible to Super Admin only. Other roles that can open Admin (read-only) will not see them, and the server rejects their requests.") +
    `<form class="form formbox" data-access-form><div class="chkgrid">${rows.map(([k, g, t]) => `<label class="chk"><input type="checkbox" data-lock="${esc(k)}" ${locked.has(k) ? "checked" : ""}> <b>${esc(t)}</b> <span class="sub">${esc(g)}</span></label>`).join("")}</div>
    <div class="acts wide"><button class="btn" type="submit">Save</button><span class="sub">Page Access itself is always Super Admin only.</span></div></form>`;
}

/* ---------- Needs completion ---------- */
function vTodo() {
  if (!INT.todo) { intLoad("todo", "todo"); return intLoading(); }
  const T = INT.todo, head = T.total ? `${fmt(T.total)} items need completing` : "Everything is complete";
  return admTitle("Needs Completion", "New data from the APIs is added automatically, but some of it must be mapped or completed here to be counted correctly.") + `<div class="todohead ${T.total ? "warn" : "good"}">${head}</div>
    <div class="todolist">${T.items.map(i => `<article class="todo"><header><b>${esc(i.title)}</b><span class="tag warn">${fmt(i.count)}</span></header><p class="sub">${esc(i.hint)}</p>
      <div class="mchips">${i.examples.map(x => `<span class="mchip">${esc(x)}</span>`).join("")}${i.count > i.examples.length ? `<span class="sub">and ${fmt(i.count - i.examples.length)} more</span>` : ""}</div>
      <button class="btn ghost sm" type="button" data-adm-go="${esc(i.go[0])}|${esc(i.go[1] || "")}">Open</button></article>`).join("") || `<div class="empty sm">Nothing to complete.</div>`}</div>`;
}

/* ---------- Source status ---------- */
function vSourceStatus() {
  if (!INT.status) { intLoad("status", "status"); return intLoading(); }
  const S_ = INT.status, tone = {ok: ["good", "Normal"], warn: ["warn", "Stale"], crit: ["crit", "Failed"], off: ["idle", "Disabled"]};
  const when = s => s.schedule.length ? "Daily at " + s.schedule.join(" and ") : s.mode === "api" ? "Every " + s.interval + " min" : "Manual import";
  const ago = m => m == null ? "–" : m < 1 ? "just now" : m < 60 ? m + " min ago" : m < 1440 ? Math.floor(m / 60) + " h ago" : Math.floor(m / 1440) + " d ago";
  return admTitle("Source Status", "Sync state of each source and the last 30 sync records.") + tbl(["Source", "Schedule", "Last success", "Last result", "Status"],
    S_.sources.map(s => [s.label, when(s), ago(s.age_min), s.error ? {h: `<span class="errtx">${esc(String(s.error).slice(0, 140))}</span>`} : (s.last_msg || "–"), {h: pill(tone[s.state][0], tone[s.state][1])}]), {empty: "No sources."})
    + `<h4 class="admsub">Sync Records</h4>` + tbl(["Time", "Source", "Result", "Rows", "Duration", "Message"], S_.log.map(l => [l.at.replace("T", " ").slice(0, 19), l.source, {h: l.ok ? pill("good", "Success") : pill("crit", "Failed")}, l.rows, (l.ms / 1000).toFixed(1) + " s", l.msg]), {r: [3, 4], tall: true, empty: "No records."});
}

/* ---------- events ---------- */
document.addEventListener("click", async e => {
  const g = e.target.closest("[data-admgrp]");
  if (g) { const grp = admPages().find(x => x[0] === g.dataset.admgrp); if (typeof intReset === "function") intReset(); admGo(grp[2][0][0]); return; }
  const go = e.target.closest("[data-adm-go]");
  if (go) { const [a, k] = go.dataset.admGo.split("|"); if (typeof intReset === "function") intReset(); admGo(a, k); return; }
  const b = e.target.closest("[data-role]"); if (!b) return;
  const a = b.dataset.role;
  try {
    if (a === "new") { INT.roleEdit = {__new: true, modules: [], uploads: [], scope: "all", can_write: false}; INT.msg = null; render(false); }
    else if (a === "edit") { INT.roleEdit = Object.assign({}, INT.roles.rows.find(r => r.key === b.dataset.key)); INT.msg = null; render(false); }
    else if (a === "x") { INT.roleEdit = null; render(false); }
    else if (a === "del") { if (!confirm("Delete this role? Roles still assigned to users cannot be deleted.")) return; await api("/api/admin/master/role/" + encodeURIComponent(INT.roleEdit.key), {method: "DELETE"}); INT.roleEdit = null; INT.roles = null; await reloadConfig(); INT.msg = {ok: true, t: "Role deleted."}; render(false); }
  } catch (er) { if (er) { $("rMsg").textContent = er.message || String(er); } }
});
document.addEventListener("change", e => {
  if (e.target.id === "rAll") document.querySelectorAll("[data-rmod]").forEach(c => { c.checked = e.target.checked; });
});
document.addEventListener("submit", async e => {
  const f = e.target.closest("[data-role-form]"), af = e.target.closest("[data-access-form]");
  if (af) {
    e.preventDefault(); e.stopImmediatePropagation();
    try { await send("/api/admin/params/admin.locked_pages", {value: [...af.querySelectorAll("[data-lock]:checked")].map(x => x.dataset.lock)}, "PUT"); await reloadConfig(); INT.msg = {ok: true, t: "Page access saved."}; }
    catch (er) { INT.msg = {ok: false, t: er.message}; }
    render(false); return;
  }
  if (!f) return;
  e.preventDefault(); e.stopImmediatePropagation();
  const v = id => $(id).value.trim(), isNew = !!INT.roleEdit.__new;
  const mods = $("rAll").checked ? ["*"] : [...f.querySelectorAll("[data-rmod]:checked")].map(x => x.dataset.rmod);
  const body = {key: v("rK"), label: v("rL"), description: v("rD") || null, modules: mods, scope: v("rS"), can_write: $("rW").checked, is_admin: $("rA").checked, admin_view: $("rV").checked,
    uploads: [...f.querySelectorAll("[data-rup]:checked")].map(x => x.dataset.rup), sort: isNew ? 99 : (INT.roleEdit.sort || 0)};
  if (!/^[a-z][a-z0-9_]{1,38}$/.test(body.key)) { $("rMsg").textContent = "Key must use lowercase letters, digits, or underscores (2 to 39 characters)."; return; }
  if (!body.label) { $("rMsg").textContent = "Role name is required."; return; }
  try { await send(isNew ? "/api/admin/master/role" : "/api/admin/master/role/" + encodeURIComponent(body.key), body, isNew ? "POST" : "PUT"); INT.roleEdit = null; INT.roles = null; await reloadConfig(); INT.msg = {ok: true, t: "Role saved."}; render(false); }
  catch (er) { $("rMsg").textContent = er.message; }
}, true);

/* Admin → System → Backup & Restore: unduh cadangan .sql dan pulihkan dari .sql (hanya Super Admin). */
const BK = {msg: null, busy: false};
function vBackup() {
  if (!CFG.me.is_admin) return `<div class="empty"><b>Hanya Super Admin</b><span>Backup dan restore database hanya untuk Super Admin.</span></div>`;
  const m = BK.msg ? `<div class="msg ${BK.msg.ok ? "ok" : "err"}">${esc(BK.msg.t)}</div>` : "";
  return `${m}<p class="sub">Cadangan berupa file .sql (pg_dump, format teks). Simpan di tempat aman: berisi data personel dan hash kata sandi.</p>
    <form class="form formbox intform"><div class="fld wide"><span class="lbl">Backup</span></div>
      <div class="acts wide"><button class="btn" type="button" data-bk="backup" ${BK.busy ? "disabled" : ""}>Download backup .sql</button></div></form>
    <form class="form formbox intform" data-bk-form="restore"><div class="fld wide"><span class="lbl">Restore</span></div>
      <p class="sub">Mengganti SELURUH isi database dengan isi file. Cadangan pengaman dibuat di server sebelum restore. Setelah restore, restart api dan worker.</p>
      <div class="fld wide"><label for="bkFile">File .sql</label><input id="bkFile" type="file" accept=".sql" required></div>
      <div class="fld wide"><label for="bkConfirm">Ketik RESTORE untuk konfirmasi</label><input id="bkConfirm" type="text" autocomplete="off" required></div>
      <div class="acts wide"><button class="btn" type="submit" ${BK.busy ? "disabled" : ""}>Restore database</button></div></form>`;
}
document.addEventListener("click", async e => {
  const b = e.target.closest("[data-bk]"); if (!b) return;
  BK.busy = true; BK.msg = null; render(false);
  try {
    const r = await fetch("/api/admin/system/backup", {credentials: "same-origin", headers: {"X-Requested-With": "itoc"}});
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || "HTTP " + r.status);
    const name = (r.headers.get("content-disposition") || "").match(/filename="([^"]+)"/)?.[1] || "itoc-backup.sql";
    const url = URL.createObjectURL(await r.blob()), a = document.createElement("a");
    a.href = url; a.download = name; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
    BK.msg = {ok: true, t: "Cadangan " + name + " diunduh."};
  } catch (er) { BK.msg = {ok: false, t: er.message}; }
  BK.busy = false; render(false);
});
document.addEventListener("submit", async e => {
  const f = e.target.closest("[data-bk-form]"); if (!f) return; e.preventDefault();
  const file = document.getElementById("bkFile").files[0], conf = document.getElementById("bkConfirm").value;
  if (!file) { BK.msg = {ok: false, t: "Pilih file .sql dulu."}; render(false); return; }
  if (conf.trim() !== "RESTORE") { BK.msg = {ok: false, t: "Ketik RESTORE untuk konfirmasi."}; render(false); return; }
  if (!window.confirm("Restore akan MENGGANTI seluruh data database dengan isi " + file.name + ". Lanjutkan?")) return;
  const fd = new FormData(); fd.append("file", file); fd.append("confirm", conf);
  BK.busy = true; BK.msg = {ok: true, t: "Memulihkan database… jangan tutup halaman ini."}; render(false);
  try {
    const r = await send("/api/admin/system/restore", fd);
    BK.msg = {ok: true, t: "Restore selesai. Cadangan pengaman: " + r.pre_backup + ". " + (r.warning ? "PERINGATAN: " + r.warning + " " : "") + "Restart api dan worker."};
  } catch (er) { BK.msg = {ok: false, t: er.message}; }
  BK.busy = false; render(false);
});
