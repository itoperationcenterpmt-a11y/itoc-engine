/* Admin menu: grouped pages, roles and access, data that needs completing, source status, and page access (Super Admin lock). */
"use strict";
const ADM = [
  ["akses", "Access", [["pengguna", "Users"], ["roles", "Roles"], ["apikeys", "API Keys"]]],
  ["sumber", "Data Sources", [["integrasi", "Integrations"], ["pemetaan", "Mapping"], ["dilengkapi", "Needs Completion"]]],
  ["operasional", "Operations", [["personel", "Personnel"], ["tim", "Teams & Shifts"], ["parameter", "Targets & Parameters"], ["rumus", "Formulas"]]],
  ["notifikasi", "Notifications", [["smtp", "Email"], ["webhooks", "Webhooks"], ["chatcmd", "Bot & Notifier API"]]],
  ["sistem", "System", [["appearance", "Appearance"], ["audit", "Audit Log"], ["sharelinks", "Share Links"], ["status", "Source Status"], ["menu", "Menus & Widgets"], ["akses", "Page Access"], ["backup", "Backup & Restore"]]]
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
  return `<div class="admnav"><div class="admgrp" role="tablist" aria-label="Admin groups">${admPages().map(([k, t]) => `<button type="button" role="tab" data-admgrp="${k}" aria-selected="${g[0] === k}">${t}</button>`).join("")}</div>
    <div class="admsubtabs" role="tablist" aria-label="Admin sections">${g[2].map(([k, t]) => `<button type="button" role="tab" data-adm="${k}" aria-selected="${S.adm === k}">${t}${k === "dilengkapi" && todo ? ` <span class="tag warn">${todo}</span>` : ""}</button>`).join("")}</div></div>`;
}
const admTitle = (t, d, act = "") => `<div class="admhead"><div class="admhead-t"><h3>${esc(t)}</h3>${d ? `<span class="sub">${esc(d)}</span>` : ""}</div>${act ? `<div class="acts">${act}</div>` : ""}</div>`;
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
  const uCnt = {}; (V.users || []).forEach(u => { uCnt[u.role] = (uCnt[u.role] || 0) + 1; });
  return intMsg() + admTitle("Roles & Access", "A role controls which menus are visible, whether data can be edited, and the location scope. Each user has one role.", can ? `<button class="btn" type="button" data-role="new">+ Add Role</button>` : "") + form + `
    <div class="rolecards">${rows.map(r => `<article class="rcard"><header><b>${esc(r.label)}</b><span class="tag">${fmt(uCnt[r.key] || 0)} users</span><span class="sub">${esc(r.key)}</span>${can ? `<button class="btn ghost sm" type="button" data-role="edit" data-key="${esc(r.key)}">Edit</button>` : ""}</header>
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
  const S_ = INT.status, tone = {ok: ["good", "Normal"], partial: ["warn", "Partial"], warn: ["warn", "Stale"], crit: ["crit", "Failed"], off: ["idle", "Disabled"]};
  const when = s => s.schedule.length ? (s.schedule.length === 4 ? "Every 6h (" + s.schedule.join(", ") + ")" : "Daily at " + s.schedule.join(" and ")) : s.mode === "api" ? "Every " + s.interval + " min" : "Manual import";
  const ago = m => m == null ? "–" : m < 1 ? "just now" : m < 60 ? m + " min ago" : m < 1440 ? Math.floor(m / 60) + " h ago" : Math.floor(m / 1440) + " d ago";
  const prog = s => {
    if (s.sync_pct == null) return "–";
    const cls = s.state === "crit" ? "crit" : s.state === "partial" || s.sync_pct < 90 ? "warn" : "";
    return {h: `<span class="sprog" title="${esc(s.sync_detail || "")}"><span class="sprog-bar"><i class="${cls}" style="width:${Math.max(4, s.sync_pct)}%"></i></span><b class="num">${s.sync_pct}%</b><span class="sub">${esc(s.sync_detail || "")}</span></span>`};
  };
  return admTitle("Source Status", "Sync state, completeness progress (%), and the last 30 sync records for each technical integrator.") + tbl(["Source", "Schedule", "Sync Progress", "Last success", "Last result", "Status"],
    S_.sources.map(s => [s.label, when(s), prog(s), ago(s.age_min), s.error ? {h: `<span class="errtx">${esc(String(s.error).slice(0, 140))}</span>`} : (s.last_msg || "–"), {h: pill((tone[s.state] || tone.off)[0], (tone[s.state] || tone.off)[1])}]), {empty: "No sources."})
    + `<h4 class="admsub">Sync Records</h4>` + tbl(["Time", "Source", "Result", "Rows", "Duration", "Message"], S_.log.map(l => [l.at.replace("T", " ").slice(0, 19), l.source, {h: !l.ok ? pill("crit", "Failed") : l.partial ? pill("warn", "Partial") : pill("good", "Success")}, l.rows, (l.ms / 1000).toFixed(1) + " s", l.msg]), {r: [3, 4], tall: true, empty: "No records."});
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
  else if (e.target.id === "uRoleF") { S.uRoleF = e.target.value; render(false); }
  else if (e.target.id === "uStatF") { S.uStatF = e.target.value; render(false); }
});
document.addEventListener("input", e => {
  if (e.target.id === "uQ") { S.uQ = e.target.value; const pos = e.target.selectionStart; render(false); const el = $("uQ"); if (el) { el.focus(); el.setSelectionRange(pos, pos); } }
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

/* Admin → System → Backup & Restore: download a .sql backup and restore from one (Super Admin only). */
const BK = {msg: null, busy: false};
function vBackup() {
  if (!CFG.me.is_admin) return admTitle("Backup & Restore", "Database backup and restore (Super Admin only).") + `<div class="empty"><b>Super Admin only</b><span>Database backup and restore are only for the Super Admin.</span></div>`;
  const m = BK.msg ? `<div class="msg ${BK.msg.ok ? "ok" : "err"}">${esc(BK.msg.t)}</div>` : "";
  return admTitle("Backup & Restore", "Download a plain-text PostgreSQL .sql backup or restore the database from a previous backup.") + m +
    `<div class="grid" style="margin-top:4px">
      <form class="panel c6 intform"><header><h2>Download Backup (.sql)</h2></header>
        <p class="sub" style="margin:0">Generates a full pg_dump .sql file containing configuration, operational data, personnel, and password hashes. Keep it in a secure location.</p>
        <div class="acts" style="margin-top:auto"><button class="btn" type="button" data-bk="backup" ${BK.busy ? "disabled" : ""}>Download backup .sql</button></div></form>
      <form class="panel c6 intform" data-bk-form="restore"><header><h2>Restore Database</h2></header>
        <p class="sub" style="margin:0">Replaces the <b>entire</b> database with the uploaded .sql file. A safety backup is created automatically on the server first. Restart api and worker after restore.</p>
        <div class="fld"><label for="bkFile">Backup file (.sql)</label><input id="bkFile" type="file" accept=".sql" required></div>
        <div class="fld"><label for="bkConfirm">Type RESTORE to confirm</label><input id="bkConfirm" type="text" autocomplete="off" placeholder="RESTORE" required></div>
        <div class="acts"><button class="btn" type="submit" ${BK.busy ? "disabled" : ""}>Restore database</button></div></form>
    </div>`;
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
    BK.msg = {ok: true, t: "Backup " + name + " downloaded."};
  } catch (er) { BK.msg = {ok: false, t: er.message}; }
  BK.busy = false; render(false);
});
document.addEventListener("submit", async e => {
  const f = e.target.closest("[data-bk-form]"); if (!f) return; e.preventDefault();
  const file = document.getElementById("bkFile").files[0], conf = document.getElementById("bkConfirm").value;
  if (!file) { BK.msg = {ok: false, t: "Choose a .sql file first."}; render(false); return; }
  if (conf.trim() !== "RESTORE") { BK.msg = {ok: false, t: "Type RESTORE to confirm."}; render(false); return; }
  if (!window.confirm("The restore will REPLACE the entire database with the content of " + file.name + ". Continue?")) return;
  const fd = new FormData(); fd.append("file", file); fd.append("confirm", conf);
  BK.busy = true; BK.msg = {ok: true, t: "Restoring the database… do not close this page."}; render(false);
  try {
    const r = await send("/api/admin/system/restore", fd);
    BK.msg = {ok: true, t: "Restore finished. Safety backup: " + r.pre_backup + ". " + (r.warning ? "WARNING: " + r.warning + " " : "") + "Restart the api and worker."};
  } catch (er) { BK.msg = {ok: false, t: er.message}; }
  BK.busy = false; render(false);
});
/* ---------- Appearance: Icons & Sizing ---------- */
const AP = {d: null, saving: false};
function apInit() {
  const P = (CFG && CFG.params) || {};
  AP.d = {
    scale: +(P["ui.scale"] ?? 0.90),
    sideIco: +(P["ui.side_icon_px"] ?? 44),
    loginIco: +(P["ui.login_icon_px"] ?? 56),
    defTheme: P["ui.default_theme"] || "auto",
  };
}
function apPreviewHtml() {
  const d = AP.d, pct = Math.round((+d.scale || 0.9) * 100);
  const si = Math.max(28, Math.min(60, +d.sideIco || 44));
  const li = Math.max(36, Math.min(88, +d.loginIco || 56));
  const fs = (13.5 * (+d.scale || 0.9)).toFixed(1);
  return `<div class="grid" style="gap:12px">
    <div class="panel c6" style="background:var(--side-bg);color:#fff;border-color:rgba(255,255,255,.1)">
      <span class="lbl" style="color:rgba(255,255,255,.6)">Sidebar Icon Preview (${si}px)</span>
      <div style="display:flex;align-items:center;gap:10px;padding:6px 4px">
        <img src="assets/tera-icon-rev.png" alt="TERA" style="width:${si}px;height:${si}px;object-fit:contain;flex:none">
        <div><b style="font-size:${Math.round(si * 0.42)}px;letter-spacing:.04em;display:block;line-height:1.1">TERA</b><span style="font-size:11px;opacity:.75">Dashboard · IT Operation Center</span></div>
      </div>
    </div>
    <div class="panel c6" style="align-items:center;text-align:center;justify-content:center">
      <span class="lbl">Login Logo Preview (${li}px)</span>
      <div style="display:flex;align-items:center;justify-content:center;gap:12px;padding:6px 0">
        <img src="assets/tera-icon-col.png" alt="TERA" style="width:${li}px;height:${li}px;object-fit:contain">
        <div style="text-align:left"><b style="font-size:${Math.round(li * 0.36)}px;letter-spacing:.03em;display:block;line-height:1.1">TERA</b><span class="sub">Dashboard</span></div>
      </div>
    </div>
    <div class="panel c12">
      <span class="lbl">UI Scale Preview (${pct}% · Base text ${fs}px)</span>
      <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;font-size:${fs}px">
        <div style="padding:10px;border:1px solid var(--line);border-radius:10px;background:var(--sunken)"><small class="sub" style="display:block">TICKET SLA</small><b class="num" style="font-size:1.5em">87,0%</b></div>
        <div style="padding:10px;border:1px solid var(--line);border-radius:10px;background:var(--sunken)"><small class="sub" style="display:block">LINK AVAILABILITY</small><b class="num" style="font-size:1.5em">99,93%</b></div>
        <div style="padding:10px;border:1px solid var(--line);border-radius:10px;background:var(--sunken)"><small class="sub" style="display:block">DEVICES ONLINE</small><b class="num" style="font-size:1.5em">81,3%</b></div>
      </div>
    </div>
  </div>`;
}
function vAppearance() {
  if (!AP.d) apInit();
  const d = AP.d;
  return admTitle("Appearance (Icons & Sizing)", "Adjust brand icon sizes and global UI zoom scale across all menus.", `<button type="button" class="btn ghost sm" data-ap="reset">Reset Defaults</button>`) + intMsg() +
    `<div class="grid" style="margin-top:4px">
      <form class="panel c5 intform" data-ap-form>
        <header><h2>Icons &amp; UI Size</h2></header>
        <div class="fld"><label for="apScale">Global UI Scale (Zoom Level)</label><select id="apScale" data-ap-f="scale">${[[0.80, "80% · Extra Compact"], [0.85, "85% · Compact"], [0.90, "90% · Balanced (Recommended)"], [0.95, "95% · Comfortable"], [1.00, "100% · Standard"]].map(([k, l]) => `<option value="${k}" ${Math.abs((+d.scale || 0.9) - k) < 0.02 ? "selected" : ""}>${l}</option>`).join("")}</select><span class="sub">Controls overall typography and card density at 100% browser zoom.</span></div>
        <div class="fld"><label for="apSideIco">Sidebar Icon Size: <b class="num">${d.sideIco}px</b></label><input id="apSideIco" type="range" min="28" max="60" step="2" data-ap-f="sideIco" value="${d.sideIco}"></div>
        <div class="fld"><label for="apLoginIco">Login Logo Size: <b class="num">${d.loginIco}px</b></label><input id="apLoginIco" type="range" min="36" max="88" step="4" data-ap-f="loginIco" value="${d.loginIco}"></div>
        <div class="fld"><label for="apTh">Default Theme (New Sessions)</label><select id="apTh" data-ap-f="defTheme">${[["auto", "Auto (follow OS)"], ["light", "Light"], ["dark", "Dark"]].map(([k, l]) => `<option value="${k}" ${d.defTheme === k ? "selected" : ""}>${l}</option>`).join("")}</select></div>
        <div class="acts" style="margin-top:6px"><button class="btn" type="submit"${AP.saving ? " disabled" : ""}>${AP.saving ? "Saving…" : "Save Appearance"}</button></div>
      </form>
      <section class="panel c7">
        <header><h2>Live Preview</h2></header>
        <div id="apStage">${apPreviewHtml()}</div>
      </section>
    </div>`;
}
document.addEventListener("click", async e => {
  const rs = e.target.closest('[data-ap="reset"]');
  if (rs && AP.d) { AP.d.scale = 0.90; AP.d.sideIco = 44; AP.d.loginIco = 56; AP.d.defTheme = "auto"; render(false); }
});
document.addEventListener("input", e => {
  const f = e.target.dataset && e.target.dataset.apF; if (!f || !AP.d) return;
  AP.d[f] = e.target.type === "range" || e.target.type === "number" ? +e.target.value : e.target.value;
  const st = $("apStage"); if (st) st.innerHTML = apPreviewHtml();
  const lbl = e.target.previousElementSibling && e.target.previousElementSibling.querySelector("b");
  if (lbl && e.target.type === "range") lbl.textContent = AP.d[f] + "px";
});
document.addEventListener("change", e => {
  if (e.target.dataset && e.target.dataset.apF && AP.d) {
    AP.d[e.target.dataset.apF] = ["scale", "sideIco", "loginIco"].includes(e.target.dataset.apF) ? +e.target.value : e.target.value;
    const st = $("apStage"); if (st) st.innerHTML = apPreviewHtml();
  }
});
document.addEventListener("submit", async e => {
  const f = e.target.closest("[data-ap-form]"); if (!f || !AP.d) return;
  e.preventDefault(); e.stopImmediatePropagation();
  AP.saving = true; render(false);
  const d = AP.d, pairs = [
    ["ui.scale", +d.scale || 0.90], ["ui.side_icon_px", +d.sideIco || 44], ["ui.login_icon_px", +d.loginIco || 56], ["ui.default_theme", d.defTheme || "auto"],
  ];
  try {
    for (const [k, v] of pairs) await send("/api/admin/params/" + encodeURIComponent(k), {value: v}, "PUT");
    await reloadConfig(); applyAppearance(CFG.params);
    AP.d = null; INT.msg = {ok: true, t: "Appearance settings saved and applied."};
  } catch (er) { INT.msg = {ok: false, t: er.message || String(er)}; }
  finally { AP.saving = false; render(false); }
}, true);

function vAdmin() {
  admEnsure();
  let body = "";
  const eu = S.editUser ? (V.users || []).find(x => x.u === S.editUser) : null;
  if (S.adm === "pengguna") {
    const allU = V.users || [];
    const uq = (S.uQ || "").trim().toLowerCase(), ur = S.uRoleF || "";
    const filtU = allU.filter(u => (!uq || (u.name + " " + u.u + " " + (u.site || "")).toLowerCase().includes(uq)) && (!ur || u.role === ur));
    const uRows = filtU.map(u => [
      {h: `<span style="display:inline-flex;align-items:center;gap:8px">${pav(u.name || u.u, 1)}<span><b>${esc(u.name)}</b>${u.active ? "" : ` <span class="tag warn">Inactive</span>`}<span class="sub" style="display:block">@${esc(u.u)}</span></span></span>`},
      {h: `<span class="tag" title="${esc(roleAccess(u.role))}">${esc(ROLES[u.role] || u.role)}</span>`},
      u.site || "All allowed",
      dtime(u.last),
      {h: `<button class="btn ghost sm" data-edit-user="${esc(u.u)}">Edit</button>`}
    ]);
    const isSelf = eu && eu.u === CFG.me.username;
    body = admTitle("Users", `${fmt(allU.length)} accounts. Click Edit on any user to update role, status, reset password, or delete account.`, `<button class="btn" data-adduser>+ Add User</button>`) + `${S.msg ? `<div class="msg ok">${esc(S.msg)}</div>` : ""}
    ${S.addUser || eu ? `<form id="uF" class="form formbox" style="margin-bottom:12px">
      <div class="fld"><label for="uU">Username *</label><input id="uU" type="text" value="${eu ? esc(eu.u) : ""}" ${eu ? "readonly" : ""}></div>
      <div class="fld"><label for="uN">Name *</label><input id="uN" type="text" value="${eu ? esc(eu.name) : ""}"></div>
      <div class="fld"><label for="uR">Role *</label><select id="uR" ${isSelf ? "disabled" : ""}>${Object.entries(ROLES).map(([k, v]) => `<option value="${k}" ${eu && eu.role === k ? "selected" : ""}>${v}</option>`).join("")}</select></div>
      <div class="fld"><label for="uS">Branch (EOS only)</label><select id="uS"><option value="">–</option>${CFG.sites.map(x => `<option ${eu && eu.site === x ? "selected" : ""}>${esc(x)}</option>`).join("")}</select></div>
      ${eu ? `<div class="fld"><label for="uAct">Account Status</label><select id="uAct" ${isSelf ? "disabled" : ""}><option value="1" ${eu.active ? "selected" : ""}>Active</option><option value="0" ${!eu.active ? "selected" : ""}>Inactive (Disabled)</option></select></div>` : ""}
      <div class="acts wide">
        <button class="btn" type="submit">Save</button>
        <button class="btn ghost" type="button" data-adduser>Cancel</button>
        ${eu && !isSelf ? `<button class="btn ghost" type="button" data-reset-user="${esc(eu.u)}">Reset Password</button><button class="btn danger" type="button" data-del-user="${esc(eu.u)}" style="margin-left:auto">Delete User</button>` : ""}
        ${eu ? "" : `<span class="sub">The initial password is random and must be changed at first login.</span>`}
        <span class="msg err" id="uMsg"></span>
      </div></form>` : ""}
    <div class="toolbar mbar"><input type="search" id="uQ" class="msearch" value="${esc(S.uQ || "")}" placeholder="Search name, @username, or branch" aria-label="Search users"><select id="uRoleF" aria-label="Filter by role"><option value="">All roles</option>${Object.entries(ROLES).map(([k, v]) => `<option value="${esc(k)}" ${ur === k ? "selected" : ""}>${esc(v)}</option>`).join("")}</select><span class="sub">${fmt(filtU.length)} of ${fmt(allU.length)} shown</span></div>
    ${tbl(["User", "Role", "Location Scope", "Last Login", "Actions"], uRows, {pageSize: 15, tall: true, empty: "No users match this filter."})}`;
  }
  if (S.adm === "integrasi") body = vIntegrations();
  if (S.adm === "apikeys") body = vApiKeys();
  if (S.adm === "sharelinks") body = vShareLinks();
  if (S.adm === "smtp") body = vSmtp();
  if (S.adm === "webhooks") body = vWebhooks();
  if (S.adm === "chatcmd") body = vChatCmd();
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
  if (S.adm === "appearance") body = vAppearance();
  if (S.adm === "audit") body = vAudit();
  if (S.adm === "backup") body = vBackup();
  return `<div class="grid"><section class="panel c12">${admNav()}${body}</section></div>`;
}

