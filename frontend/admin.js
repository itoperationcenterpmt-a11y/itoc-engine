/* Admin menu: grouped pages, roles and access, data that needs completing, source status, and page access (Super Admin lock). */
"use strict";
const ADM = [
  ["akses", "Access", [["pengguna", "Users"], ["roles", "Roles"], ["apikeys", "API Keys"]]],
  ["sumber", "Data Sources", [["integrasi", "Integrations"], ["status", "Source Status"], ["pemetaan", "Mapping"], ["dilengkapi", "Needs Completion"]]],
  ["operasional", "Operations", [["personel", "Personnel"], ["tim", "Teams & Shifts"], ["parameter", "Targets & Parameters"], ["rumus", "Formulas"]]],
  ["notifikasi", "Notifications", [["smtp", "Email"], ["webhooks", "Webhooks"], ["chatcmd", "Bot & Notifier API"]]],
  ["sistem", "System", [["appearance", "Branding & Icons"], ["menu", "Menus & Widgets"], ["audit", "Audit Log"], ["sharelinks", "Share Links"], ["akses", "Page Access"], ["backup", "Backup & Restore"]]]
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
/* ---------- Branding & Icons Manager (Light & Dark Assets, Colors, Sizing, Menu Icons) ---------- */
const AP = {d: null, tab: "logos", pv: "dark", saving: false, pickMod: ""};
const AP_SW_L = [["#1c5cab", "Pelindo Blue"], ["#0b3d7a", "Deep Navy"], ["#0891b2", "Cyan"], ["#059669", "Emerald"], ["#4f46e5", "Indigo"], ["#334155", "Slate"]];
const AP_SW_D = [["#6da7ec", "Sky Blue"], ["#38bdf8", "Bright Cyan"], ["#34d399", "Mint"], ["#818cf8", "Soft Indigo"], ["#f59e0b", "Amber"], ["#94a3b8", "Cool Slate"]];
const AP_SW_SB = [["#0f1b2d", "Pelindo Navy"], ["#0b1220", "Midnight"], ["#111827", "Charcoal"], ["#0a2540", "Ocean Dark"], ["#171c22", "Graphite"]];
function apInit() {
  const P = (CFG && CFG.params) || {};
  AP.d = {
    brand: P["ui.brand_name"] || "TERA Dashboard",
    brandSub: P["ui.brand_sub"] ?? "Dashboard",
    brandBy: P["ui.brand_by"] ?? "by IT Operation Center",
    footer: P["ui.footer"] || "© {year} IT Operation Center",
    scale: +(P["ui.scale"] ?? 0.90),
    radius: +(P["ui.card_radius"] ?? 14),
    defTheme: P["ui.default_theme"] || "auto",
    sideIco: +(P["ui.side_icon_px"] ?? 48),
    sideWm: +(P["ui.side_wm_px"] ?? 19),
    loginIco: +(P["ui.login_icon_px"] ?? 68),
    sideImg: String(P["ui.side_icon_img"] || ""),
    loginImg: String(P["ui.login_icon_img"] || ""),
    wmLight: String(P["ui.wordmark_light_img"] || ""),
    wmDark: String(P["ui.wordmark_dark_img"] || ""),
    favImg: String(P["ui.favicon_img"] || ""),
    loginBg: String(P["ui.login_bg_img"] || ""),
    accLight: P["ui.accent_light"] || "#1c5cab",
    accDark: P["ui.accent_dark"] || "#6da7ec",
    sideBg: P["ui.side_bg"] || "#0f1b2d",
  };
}
/* Auto-compress raster uploads cleanly via canvas (preserves PNG transparency for logos; SVG kept raw). */
function apReadImage(file, maxW, asJpeg) {
  return new Promise((resolve, reject) => {
    if (!file) return reject(new Error("No file selected."));
    if (file.size > 8 * 1024 * 1024) return reject(new Error("File too large (max 8 MB)."));
    const rd = new FileReader();
    rd.onerror = () => reject(new Error("Could not read file."));
    rd.onload = () => {
      const raw = String(rd.result || "");
      if (file.type === "image/svg+xml" || raw.length < 40000) return resolve(raw);
      const im = new Image();
      im.onerror = () => resolve(raw);
      im.onload = () => {
        let w = im.naturalWidth || maxW, h = im.naturalHeight || maxW;
        if (w > maxW || h > maxW) { const r = Math.min(maxW / w, maxW / h); w = Math.max(1, Math.round(w * r)); h = Math.max(1, Math.round(h * r)); }
        const cv = document.createElement("canvas"); cv.width = w; cv.height = h;
        const ctx = cv.getContext("2d"); ctx.drawImage(im, 0, 0, w, h);
        resolve(asJpeg ? cv.toDataURL("image/jpeg", 0.82) : cv.toDataURL("image/png"));
      };
      im.src = raw;
    };
    rd.readAsDataURL(file);
  });
}
function apApplyDraftLive() {
  if (!AP.d) return;
  const d = AP.d;
  applyAppearance({
    "ui.scale": d.scale, "ui.card_radius": d.radius, "ui.side_icon_px": d.sideIco, "ui.side_wm_px": d.sideWm, "ui.login_icon_px": d.loginIco,
    "ui.side_icon_img": d.sideImg, "ui.login_icon_img": d.loginImg, "ui.wordmark_light_img": d.wmLight, "ui.wordmark_dark_img": d.wmDark,
    "ui.favicon_img": d.favImg, "ui.login_bg_img": d.loginBg, "ui.accent_light": d.accLight, "ui.accent_dark": d.accDark,
    "ui.side_bg": d.sideBg, "ui.brand_sub": d.brandSub, "ui.brand_by": d.brandBy,
  });
}
function apPreviewHtml() {
  const d = AP.d, dark = AP.pv === "dark";
  const acc = dark ? d.accDark : d.accLight;
  const pct = Math.round((+d.scale || 0.9) * 100);
  const si = Math.max(24, Math.min(72, +d.sideIco || 48));
  const swm = Math.max(12, Math.min(34, +d.sideWm || 19));
  const li = Math.max(36, Math.min(110, +d.loginIco || 68));
  const rad = Math.max(4, Math.min(24, +d.radius || 14));
  const sSrc = d.sideImg || "assets/tera-icon-rev.png";
  const lSrc = dark ? (d.sideImg || d.loginImg || "assets/tera-icon-rev.png") : (d.loginImg || "assets/tera-icon-col.png");
  const wmSide = d.wmDark || d.wmLight || "assets/tera-wordmark-rev.svg";
  const wmLogin = dark ? (d.wmDark || d.wmLight || "assets/tera-wordmark-rev.svg") : (d.wmLight || "assets/tera-wordmark-col.svg");
  const fSrc = d.favImg || "assets/tera-favicon.png";
  const bgUrl = d.loginBg || "assets/belawan.jpg";
  const fs = (13.5 * (+d.scale || 0.9)).toFixed(1);
  return `<div class="ap-pvbox ${dark ? "pv-dark" : "pv-light"}">
    <div class="ap-pvgrid">
      <div style="background:${esc(d.sideBg)};color:#d2dce8;padding:12px 10px;display:flex;flex-direction:column;gap:10px">
        <div style="display:flex;align-items:center;gap:8px;padding-bottom:8px;border-bottom:1px solid rgba(255,255,255,.1)">
          <img src="${esc(sSrc)}" alt="" style="width:${Math.round(si * 0.72)}px;height:${Math.round(si * 0.72)}px;object-fit:contain;border-radius:6px;flex:none">
          <div style="min-width:0"><img src="${esc(wmSide)}" alt="${esc(d.brand)}" style="height:${Math.round(swm * 0.85)}px;max-width:100%;object-fit:contain;display:block"><span style="font-size:10px;color:#5bb5e2;display:block;margin-top:2px">${esc(d.brandSub)}</span><span style="font-size:9px;opacity:.65;display:block">${esc(d.brandBy)}</span></div>
        </div>
        <div style="display:flex;flex-direction:column;gap:4px;font-size:11px">
          <span style="padding:5px 8px;border-radius:6px;background:rgba(255,255,255,.12);color:#fff;border-left:3px solid ${esc(acc)}">Overview</span>
          <span style="padding:4px 8px;opacity:.75">Ticketing</span>
          <span style="padding:4px 8px;opacity:.75">Network</span>
          <span style="padding:4px 8px;opacity:.75">Cyber Security</span>
        </div>
      </div>
      <div style="padding:12px;display:flex;flex-direction:column;gap:10px;font-size:${fs}px">
        <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap">
          <div><small style="color:${esc(acc)};font-weight:700;font-size:10px">DASHBOARD › OVERVIEW</small><b style="display:block;font-size:1.15em">Overview</b></div>
          <span style="display:inline-flex;align-items:center;gap:5px;font-size:10.5px;padding:3px 8px;border-radius:999px;background:var(--pv-surf);border:1px solid var(--pv-line)"><img src="${esc(fSrc)}" alt="" style="width:13px;height:13px;object-fit:contain"> ${esc(d.brand)} · ${pct}%</span>
        </div>
        <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px">
          <div style="padding:9px;border:1px solid var(--pv-line);border-radius:${rad}px;background:var(--pv-surf)"><small style="color:var(--pv-muted);font-size:10px;display:block">TICKET SLA</small><b class="num" style="font-size:1.35em;color:${esc(acc)}">87,0%</b></div>
          <div style="padding:9px;border:1px solid var(--pv-line);border-radius:${rad}px;background:var(--pv-surf)"><small style="color:var(--pv-muted);font-size:10px;display:block">LINK AVAIL</small><b class="num" style="font-size:1.35em">99,93%</b></div>
          <div style="padding:9px;border:1px solid var(--pv-line);border-radius:${rad}px;background:var(--pv-surf)"><small style="color:var(--pv-muted);font-size:10px;display:block">DEVICES</small><b class="num" style="font-size:1.35em">81,3%</b></div>
        </div>
        <div style="position:relative;border-radius:${rad}px;overflow:hidden;border:1px solid var(--pv-line);padding:12px;background:url('${esc(bgUrl)}') center/cover no-repeat">
          <div style="position:absolute;inset:0;background:${dark ? "rgba(8,16,30,.78)" : "rgba(236,241,248,.82)"}"></div>
          <div style="position:relative;display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap">
            <div style="display:flex;align-items:center;gap:10px">
              <img src="${esc(lSrc)}" alt="" style="width:${Math.round(li * 0.65)}px;height:${Math.round(li * 0.65)}px;object-fit:contain;border-radius:8px">
              <div><img src="${esc(wmLogin)}" alt="${esc(d.brand)}" style="height:18px;max-width:120px;object-fit:contain;display:block"><span style="font-size:10px;color:var(--pv-muted)">Login Page (${dark ? "Dark" : "Light"} Mode)</span></div>
            </div>
            <span style="padding:5px 12px;border-radius:8px;background:${esc(acc)};color:${dark ? "#0b1420" : "#fff"};font-size:11px;font-weight:700">Sign in</span>
          </div>
        </div>
      </div>
    </div>
  </div>`;
}
function apMenuIconsHtml() {
  const mods = (CFG && CFG.modules) || [];
  const icoKeys = typeof ICO !== "undefined" ? Object.keys(ICO) : [];
  const curMod = AP.pickMod ? mods.find(m => m.key === AP.pickMod) : null;
  return `<section class="panel c12" style="margin-top:4px">
    <header><h2>Sidebar Menu Icons</h2><span class="sub">Click any menu item to change its icon immediately</span></header>
    <div class="mico-list">${mods.map(m => {
      const svg = (typeof ICO !== "undefined" && ICO[m.icon]) || "";
      const p = m.parent ? mods.find(x => x.key === m.parent) : null;
      return `<button type="button" class="mico-item ${AP.pickMod === m.key ? "on" : ""}" data-ap-mod="${esc(m.key)}"><svg viewBox="0 0 24 24" aria-hidden="true">${svg}</svg><span><b>${esc(m.label)}</b>${p ? `<small class="sub">${esc(p.label)}</small>` : `<small class="sub">Main menu</small>`}</span></button>`;
    }).join("")}</div>
    ${curMod ? `<div class="formbox" style="margin-top:8px"><div class="admhead" style="margin-bottom:8px"><b>Pick icon for "${esc(curMod.label)}"</b><button type="button" class="btn ghost sm" data-ap-mod="">Close</button></div>
      <div class="ico-grid">${icoKeys.map(k => `<button type="button" class="ico-btn ${curMod.icon === k ? "on" : ""}" data-ap-setico="${esc(k)}" title="${esc(k)}"><svg viewBox="0 0 24 24" aria-hidden="true">${ICO[k]}</svg><span>${esc(k)}</span></button>`).join("")}</div></div>` : ""}
  </section>`;
}
function vAppearance() {
  if (!AP.d) apInit();
  const d = AP.d;
  const imgRow = (id, key, label, defSrc, opts = {}) => `<div class="fld">
    <label>${label}</label>
    <div class="ap-up">
      <img class="ap-thumb ${opts.dark ? "dark" : ""} ${opts.wide ? "wide" : ""}" src="${esc(d[key] || defSrc)}" alt="">
      <input id="${id}" type="file" accept="image/png,image/jpeg,image/svg+xml,image/webp,image/x-icon" data-ap-upload="${key}" data-ap-max="${opts.max || 512}" data-ap-jpg="${opts.jpg ? "1" : ""}" style="display:none">
      <button type="button" class="btn ghost sm" data-ap-pick="${id}" style="margin:0">Upload / Change</button>
      ${d[key] ? `<button type="button" class="btn ghost sm" data-ap-clear="${key}" style="margin:0">Reset Default</button>` : `<span class="sub">Default asset</span>`}
    </div>
  </div>`;
  const swRow = (key, label, list) => `<div class="fld">
    <label>${label}</label>
    <div class="ap-swatches">
      ${list.map(([hex, nm]) => `<button type="button" class="ap-sw ${String(d[key]).toLowerCase() === hex ? "on" : ""}" style="background:${hex}" data-ap-sw="${key}" data-ap-val="${hex}" title="${esc(nm)}" aria-label="${esc(nm)}"></button>`).join("")}
      <input type="color" data-ap-f="${key}" value="${esc(d[key])}" style="width:32px;height:26px;padding:1px;border-radius:6px;cursor:pointer">
      <span class="sub num">${esc(d[key])}</span>
    </div>
  </div>`;
  const tabBody = AP.tab === "logos" ? `
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px">
      ${imgRow("apLoginUp", "loginImg", "Brand Icon · Light Mode", "assets/tera-icon-col.png", {max: 512})}
      ${imgRow("apSideUp", "sideImg", "Brand Icon · Dark & Sidebar", "assets/tera-icon-rev.png", {dark: true, max: 512})}
    </div>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px">
      ${imgRow("apWmLightUp", "wmLight", "Wordmark · Light Mode", "assets/tera-wordmark-col.svg", {wide: true, max: 600})}
      ${imgRow("apWmDarkUp", "wmDark", "Wordmark · Dark & Sidebar", "assets/tera-wordmark-rev.svg", {dark: true, wide: true, max: 600})}
    </div>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px">
      ${imgRow("apFavUp", "favImg", "Browser Tab Favicon", "assets/tera-favicon.png", {max: 128})}
      ${imgRow("apBgUp", "loginBg", "Login Page Background", "assets/belawan.jpg", {wide: true, max: 1600, jpg: true})}
    </div>
  ` : AP.tab === "colors" ? `
    <div class="fld"><label for="apTh">Default Theme (New Sessions)</label><select id="apTh" data-ap-f="defTheme">${[["auto", "Auto (follow OS)"], ["light", "Light"], ["dark", "Dark"]].map(([k, l]) => `<option value="${k}" ${d.defTheme === k ? "selected" : ""}>${l}</option>`).join("")}</select></div>
    ${swRow("accLight", "Accent Color · Light Mode", AP_SW_L)}
    ${swRow("accDark", "Accent Color · Dark Mode", AP_SW_D)}
    ${swRow("sideBg", "Sidebar Background Color", AP_SW_SB)}
  ` : `
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px">
      <div class="fld"><label for="apScale">Global UI Scale</label><select id="apScale" data-ap-f="scale">${[[0.80, "80% · Extra Compact"], [0.85, "85% · Compact"], [0.90, "90% · Balanced"], [0.95, "95% · Comfortable"], [1.00, "100% · Standard"]].map(([k, l]) => `<option value="${k}" ${Math.abs((+d.scale || 0.9) - k) < 0.02 ? "selected" : ""}>${l}</option>`).join("")}</select></div>
      <div class="fld"><label for="apRad">Card Radius: <b class="num">${d.radius}px</b></label><input id="apRad" type="range" min="6" max="22" step="2" data-ap-f="radius" value="${d.radius}"></div>
    </div>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px">
      <div class="fld"><label for="apSideIco">Sidebar Icon Size: <b class="num">${d.sideIco}px</b></label><input id="apSideIco" type="range" min="28" max="72" step="2" data-ap-f="sideIco" value="${d.sideIco}"></div>
      <div class="fld"><label for="apSideWm">Wordmark Height: <b class="num">${d.sideWm}px</b></label><input id="apSideWm" type="range" min="12" max="34" step="1" data-ap-f="sideWm" value="${d.sideWm}"></div>
      <div class="fld"><label for="apLoginIco">Login Logo Size: <b class="num">${d.loginIco}px</b></label><input id="apLoginIco" type="range" min="40" max="110" step="2" data-ap-f="loginIco" value="${d.loginIco}"></div>
    </div>
    <div class="fld"><label for="apBrand">Brand Name (Title &amp; Reports)</label><input id="apBrand" type="text" data-ap-f="brand" value="${esc(d.brand)}"></div>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px">
      <div class="fld"><label for="apSub">Sidebar Subtitle</label><input id="apSub" type="text" data-ap-f="brandSub" value="${esc(d.brandSub)}"></div>
      <div class="fld"><label for="apBy">Sidebar Byline</label><input id="apBy" type="text" data-ap-f="brandBy" value="${esc(d.brandBy)}"></div>
    </div>
    <div class="fld"><label for="apFoot">Footer Text ({year} = current year)</label><input id="apFoot" type="text" data-ap-f="footer" value="${esc(d.footer)}"></div>
  `;
  return admTitle("Branding & Icons", "Manage Light & Dark logos, theme colors, shared icon sizes, and sidebar menu icons. All changes preview live.", `<button type="button" class="btn ghost sm" data-ap="reset">Reset All Defaults</button>`) + intMsg() +
    `<div class="grid" style="margin-top:4px">
      <form class="panel c6 intform" data-ap-form>
        <header><h2>Configuration</h2>
          <div class="seg">${[["logos", "Logos & Icons"], ["colors", "Theme & Colors"], ["sizing", "Sizing & Text"]].map(([k, l]) => `<button type="button" data-ap-tab="${k}" aria-pressed="${AP.tab === k}">${l}</button>`).join("")}</div>
        </header>
        ${tabBody}
        <div class="acts" style="margin-top:6px"><button class="btn" type="submit"${AP.saving ? " disabled" : ""}>${AP.saving ? "Saving…" : "Save All Branding"}</button><span class="sub">Applies live to all users across Light &amp; Dark modes.</span></div>
      </form>
      <section class="panel c6">
        <header><h2>Live Preview</h2>
          <div class="seg">${[["dark", "Dark Mode"], ["light", "Light Mode"]].map(([k, l]) => `<button type="button" data-ap-pv="${k}" aria-pressed="${AP.pv === k}">${l}</button>`).join("")}</div>
        </header>
        <div id="apStage">${apPreviewHtml()}</div>
      </section>
      ${apMenuIconsHtml()}
    </div>`;
}
document.addEventListener("click", async e => {
  const pk = e.target.closest("[data-ap-pick]");
  if (pk) { const inp = $(pk.dataset.apPick); if (inp) { inp.value = ""; inp.click(); } return; }
  const tb = e.target.closest("[data-ap-tab]");
  if (tb) { AP.tab = tb.dataset.apTab; if (AP.tab === "dark" || AP.tab === "light") AP.pv = AP.tab; render(false); return; }
  const pv = e.target.closest("[data-ap-pv]");
  if (pv) { AP.pv = pv.dataset.apPv; render(false); return; }
  const sw = e.target.closest("[data-ap-sw]");
  if (sw && AP.d) { AP.d[sw.dataset.apSw] = sw.dataset.apVal; apApplyDraftLive(); render(false); return; }
  const rs = e.target.closest('[data-ap="reset"]');
  if (rs && AP.d) {
    Object.assign(AP.d, {brand: "TERA Dashboard", brandSub: "Dashboard", brandBy: "by IT Operation Center", footer: "© {year} IT Operation Center", scale: 0.90, radius: 14, defTheme: "auto", sideIco: 48, sideWm: 19, loginIco: 68, sideImg: "", loginImg: "", wmLight: "", wmDark: "", favImg: "", loginBg: "", accLight: "#1c5cab", accDark: "#6da7ec", sideBg: "#0f1b2d"});
    apApplyDraftLive(); render(false); return;
  }
  const clr = e.target.closest("[data-ap-clear]");
  if (clr && AP.d) { AP.d[clr.dataset.apClear] = ""; apApplyDraftLive(); render(false); return; }
  const mod = e.target.closest("[data-ap-mod]");
  if (mod) { AP.pickMod = AP.pickMod === mod.dataset.apMod ? "" : mod.dataset.apMod; render(false); return; }
  const seti = e.target.closest("[data-ap-setico]");
  if (seti && AP.pickMod) {
    const m = (CFG.modules || []).find(x => x.key === AP.pickMod); if (!m) return;
    try {
      await send("/api/admin/master/module/" + encodeURIComponent(m.key), {label: m.label, icon: seti.dataset.apSetico, parent: m.parent || null, enabled: true}, "PUT");
      await reloadConfig(); renderShell();
      INT.msg = {ok: true, t: `Icon for "${m.label}" updated to "${seti.dataset.apSetico}".`};
    } catch (er) { INT.msg = {ok: false, t: er.message || String(er)}; }
    render(false);
  }
});
document.addEventListener("input", e => {
  const f = e.target.dataset && e.target.dataset.apF; if (!f || !AP.d) return;
  AP.d[f] = e.target.type === "range" || e.target.type === "number" ? +e.target.value : e.target.value;
  apApplyDraftLive();
  const st = $("apStage"); if (st) st.innerHTML = apPreviewHtml();
  const lbl = e.target.previousElementSibling && e.target.previousElementSibling.querySelector("b");
  if (lbl && e.target.type === "range") lbl.textContent = AP.d[f] + "px";
});
document.addEventListener("change", async e => {
  if (e.target.dataset && e.target.dataset.apUpload && AP.d) {
    const file = e.target.files && e.target.files[0], key = e.target.dataset.apUpload;
    if (!file) return;
    try {
      const dataUrl = await apReadImage(file, +e.target.dataset.apMax || 512, e.target.dataset.apJpg === "1");
      AP.d[key] = dataUrl; INT.msg = {ok: true, t: `Loaded "${file.name}". Click "Save All Branding" to persist.`};
      apApplyDraftLive();
    } catch (er) { INT.msg = {ok: false, t: er.message || String(er)}; }
    render(false);
    return;
  }
  if (e.target.dataset && e.target.dataset.apF && AP.d) {
    AP.d[e.target.dataset.apF] = ["scale", "sideIco", "sideWm", "loginIco", "radius"].includes(e.target.dataset.apF) ? +e.target.value : e.target.value;
    apApplyDraftLive();
    const st = $("apStage"); if (st) st.innerHTML = apPreviewHtml();
  }
});
document.addEventListener("submit", async e => {
  const f = e.target.closest("[data-ap-form]"); if (!f || !AP.d) return;
  e.preventDefault(); e.stopImmediatePropagation();
  AP.saving = true; render(false);
  const d = AP.d, pairs = [
    ["ui.brand_name", d.brand.trim() || "TERA Dashboard"],
    ["ui.brand_sub", d.brandSub.trim()],
    ["ui.brand_by", d.brandBy.trim()],
    ["ui.footer", d.footer.trim()],
    ["ui.scale", +d.scale || 0.90],
    ["ui.card_radius", +d.radius || 14],
    ["ui.default_theme", d.defTheme || "auto"],
    ["ui.side_icon_px", +d.sideIco || 48],
    ["ui.side_wm_px", +d.sideWm || 19],
    ["ui.login_icon_px", +d.loginIco || 68],
    ["ui.side_icon_img", d.sideImg || ""],
    ["ui.login_icon_img", d.loginImg || ""],
    ["ui.wordmark_light_img", d.wmLight || ""],
    ["ui.wordmark_dark_img", d.wmDark || ""],
    ["ui.favicon_img", d.favImg || ""],
    ["ui.login_bg_img", d.loginBg || ""],
    ["ui.accent_light", d.accLight || "#1c5cab"],
    ["ui.accent_dark", d.accDark || "#6da7ec"],
    ["ui.side_bg", d.sideBg || "#0f1b2d"],
  ];
  try {
    for (const [k, v] of pairs) await send("/api/admin/params/" + encodeURIComponent(k), {value: v}, "PUT");
    await reloadConfig(); applyBrand(); applyAppearance(CFG.params); $("foot").textContent = footText();
    AP.d = null; INT.msg = {ok: true, t: "All Light & Dark branding settings saved and applied."};
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

