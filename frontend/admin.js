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
/* ---------- Appearance Studio & Live Multi-Menu Preview ---------- */
const AP_SW = [["#1c5cab", "Pelindo Blue"], ["#0b2f6b", "Pelindo Navy"], ["#0891b2", "Maritime Cyan"], ["#059669", "Emerald"], ["#4f46e5", "Indigo"], ["#334155", "Slate"]];
const AP_MENUS = [["overview", "Overview"], ["ticketing", "Ticketing"], ["network", "Network / ISP"], ["cyber", "Cyber Security"], ["devices", "Devices"], ["personnel", "Personnel"], ["report", "Report"], ["admin", "Admin"], ["login", "Login Page"], ["wall", "TV / Wall Mode"]];
const AP = {d: null, menu: "overview", theme: "light", vp: "desktop", saving: false};
function apInit() {
  const P = (CFG && CFG.params) || {};
  AP.d = {
    accent: P["ui.accent_color"] || "#1c5cab",
    density: P["ui.density"] || "compact",
    radius: +(P["ui.card_radius"] ?? 14),
    defTheme: P["ui.default_theme"] || "auto",
    brand: P["ui.brand_name"] || "TERA Dashboard",
    footer: P["ui.footer"] || "© {year} IT Operation Center",
    publicUrl: P["ui.public_url"] || "",
    supportPhone: P["ui.support_phone"] || "",
    eyebrow: P["ui.login_eyebrow"] || "PT Pelindo Multi Terminal",
    headline: P["ui.login_headline"] || "Satu layar untuk seluruh terminal",
    tagline: P["ui.login_tagline"] || "",
    wallSlide: +(P["ui.wall_slide_sec"] || 15),
    wallRef: +(P["ui.wall_refresh_sec"] || 60),
    wallTabs: Array.isArray(P["ui.wall_rotate_tabs"]) ? [...P["ui.wall_rotate_tabs"]] : ["ringkasan", "noc", "devices", "cyber"],
  };
}
function apPreviewHtml() {
  const d = AP.d, m = AP.menu, pad = d.density === "spacious" ? "13px" : d.density === "comfortable" ? "10px" : "8px";
  const st = `--p-acc:${esc(d.accent)};--p-rad:${Math.max(4, Math.min(22, +d.radius || 14))}px;--p-pad:${pad}`;
  const cls = `ap-frame vp-${AP.vp} ${AP.theme === "dark" ? "th-dark" : ""}`;
  const foot = (d.footer || "").replace("{year}", new Date().getFullYear());
  if (m === "login") {
    return `<div class="${cls}" style="${st};padding:18px;background:linear-gradient(135deg,#0f1b2d,#1c3b68)">
      <div style="display:grid;grid-template-columns:${AP.vp === "mobile" ? "1fr" : "1.2fr 1fr"};gap:12px">
        <div class="ap-card" style="padding:16px"><small style="color:var(--p-acc);font-weight:700">${esc(d.eyebrow)}</small><b style="font-size:16px;color:var(--p-ink);margin:4px 0">${esc(d.headline)}</b><span class="s">${esc(d.tagline || "Unified operational dashboard")}</span><div class="ap-bar" style="margin-top:8px"><i style="width:72%"></i></div></div>
        <div class="ap-card" style="padding:16px;align-items:center;text-align:center"><img src="assets/tera-icon-col.png" alt="" style="width:42px;height:42px;object-fit:contain"><b style="font-size:13px">${esc(d.brand)}</b><div style="width:100%;height:22px;border-radius:6px;background:var(--p-sunk);border:1px solid var(--p-line)"></div><div style="width:100%;height:22px;border-radius:6px;background:var(--p-sunk);border:1px solid var(--p-line)"></div><div style="width:100%;padding:5px;border-radius:6px;background:var(--p-acc);color:#fff;font-size:10px;font-weight:700">Sign in</div></div>
      </div></div>`;
  }
  const bodyByMenu = {
    overview: `<div class="ap-grid"><div class="ap-card"><h5>Ticket SLA</h5><span class="v">87,0%</span><span class="s">within target</span></div><div class="ap-card"><h5>Link Availability</h5><span class="v">99,4%</span><span class="s">average</span></div><div class="ap-card"><h5>Infrastructure</h5><span class="v">82,8%</span><span class="s">devices up</span></div><div class="ap-card"><h5>Surveillance</h5><span class="v">91,7%</span><span class="s">servers syncing</span></div><div class="ap-card span2"><h5>Needs Attention</h5><span class="s">• 2 ISP links degraded · 15 XDR alerts open</span><div class="ap-bar"><i style="width:65%"></i></div></div><div class="ap-card span2"><h5>On Duty · Team 3</h5><span class="s">Shift Pagi · 08.00–15.00 WIB</span><div class="ap-bar"><i style="width:88%"></i></div></div></div>`,
    ticketing: `<div class="ap-grid"><div class="ap-card"><h5>Total Tickets</h5><span class="v">1.482</span><span class="s">30 days</span></div><div class="ap-card"><h5>SLA Met</h5><span class="v">87,0%</span><span class="s">target 85%</span></div><div class="ap-card"><h5>Open Now</h5><span class="v">17</span><span class="s">2 overdue</span></div><div class="ap-card"><h5>Median Time</h5><span class="v">42 min</span><span class="s">resolution</span></div><div class="ap-card span4"><h5>Daily Tickets & Open Queue</h5><div class="ap-bar"><i style="width:78%"></i></div><span class="s">Paginated table · 50 rows/page</span></div></div>`,
    network: `<div class="ap-grid"><div class="ap-card"><h5>ISP Links</h5><span class="v">54 / 54</span><span class="s">100% live</span></div><div class="ap-card"><h5>Dual-Link</h5><span class="v">21</span><span class="s">branches redundant</span></div><div class="ap-card"><h5>WiFi APs</h5><span class="v">169 / 186</span><span class="s">1.248 clients</span></div><div class="ap-card"><h5>Web Monitors</h5><span class="v">24 / 24</span><span class="s">all reachable</span></div><div class="ap-card span4"><h5>Branch ISP Redundancy Matrix</h5><span class="s">Astinet · Lintasarta · JLM · NEUVIZ — Dual OK / Single-Link Risk</span><div class="ap-bar"><i style="width:96%"></i></div></div></div>`,
    cyber: `<div class="ap-grid"><div class="ap-card"><h5>NDR Events</h5><span class="v">2,47M</span><span class="s">firewall / NDR</span></div><div class="ap-card"><h5>Blocked C/H</h5><span class="v">94,2%</span><span class="s">policy active</span></div><div class="ap-card"><h5>XDR Alerts</h5><span class="v">12</span><span class="s">in period</span></div><div class="ap-card"><h5>Open C/H (all)</h5><span class="v">15</span><span class="s">endpoint backlog</span></div><div class="ap-card span4"><h5>Threat Trend & Investigation Queue</h5><div class="ap-bar"><i style="width:54%"></i></div><span class="s">NDR daily trend + XDR severity mix</span></div></div>`,
    devices: `<div class="ap-grid"><div class="ap-card"><h5>Total Devices</h5><span class="v">1.803</span><span class="s">39 locations</span></div><div class="ap-card"><h5>Availability</h5><span class="v">82,8%</span><span class="s">live status</span></div><div class="ap-card"><h5>Cameras</h5><span class="v">1.203</span><span class="s">820 recording</span></div><div class="ap-card"><h5>PA Units</h5><span class="v">55</span><span class="s">2 offline</span></div><div class="ap-card span4"><h5>Interactive Site Map & Device Inventory</h5><div class="ap-bar"><i style="width:83%"></i></div><span class="s">Paginated table · 50 rows/page</span></div></div>`,
    personnel: `<div class="ap-grid"><div class="ap-card span2"><h5>On Duty · Shift Pagi</h5><span class="v">Team 3</span><span class="s">5 analysts active</span></div><div class="ap-card span2"><h5>Open Handovers</h5><span class="v">3</span><span class="s">1 high priority</span></div><div class="ap-card span4"><h5>Monthly Shift Rotation Schedule</h5><span class="s">Auto-scrolled to today's date</span><div class="ap-bar"><i style="width:60%"></i></div></div></div>`,
    report: `<div class="ap-grid"><div class="ap-card span2"><h5>Export Suite</h5><span class="v">XLSX · PDF · PPTX</span><span class="s">3-day Share Link ready</span></div><div class="ap-card span2"><h5>Shift Summary & Insights</h5><span class="v">9 Templates</span><span class="s">incl. ISP · WhatsApp ready</span></div><div class="ap-card span4"><h5>30-Day Data Completeness</h5><div class="ap-bar"><i style="width:92%"></i></div><span class="s">Validated batches & fallback uploader</span></div></div>`,
    admin: `<div class="ap-grid"><div class="ap-card span4"><h5>Admin · Access / Data Sources / Operations / Notifications / System</h5><span class="s">Users table (search + pagination) · Source Status (% synced + Partial) · Bot & Notifier API (17 commands)</span><div class="ap-bar"><i style="width:100%"></i></div></div></div>`,
    wall: `<div style="background:#0f1b2d;color:#fff;padding:7px 10px;border-radius:8px;display:flex;align-items:center;justify-content:space-between;font-size:10px;margin-bottom:6px"><b>${esc(d.brand)} · NOC Wall</b><span>Slide 1/4 · ${d.wallSlide}s · Rotate (${d.wallTabs.length}) · Refresh ${d.wallRef}s</span></div><div class="ap-grid"><div class="ap-card"><h5>ISP Live</h5><span class="v">98,2%</span></div><div class="ap-card"><h5>Devices</h5><span class="v">82,8%</span></div><div class="ap-card"><h5>WiFi APs</h5><span class="v">90,9%</span></div><div class="ap-card"><h5>Surveillance</h5><span class="v">91,7%</span></div><div class="ap-card span4"><h5>Branch Dual-Link Redundancy & Health Wall</h5><div class="ap-bar"><i style="width:94%"></i></div></div></div>`,
  };
  const navs = AP_MENUS.slice(0, 8);
  const title = (AP_MENUS.find(x => x[0] === m) || ["", "Overview"])[1];
  return `<div class="${cls}" style="${st}"><div class="ap-shell">
    ${m === "wall" ? "" : `<aside class="ap-side"><div class="ap-sbrand"><img src="assets/tera-icon-rev.png" alt=""><b>${esc(d.brand)}</b></div>${navs.map(([k, l]) => `<button type="button" class="ap-snav ${k === m ? "on" : ""}" data-ap-menu="${k}">${esc(l)}</button>`).join("")}</aside>`}
    <div class="ap-main" style="${m === "wall" ? "grid-column:1/-1" : ""}">
      ${m === "wall" ? "" : `<div class="ap-hd"><div><small>DASHBOARD › ${esc(title.toUpperCase())}</small><b>${esc(title)}</b></div><span class="ap-pill">● Team 3 · Pagi</span></div>`}
      ${bodyByMenu[m] || bodyByMenu.overview}
      <div class="ap-foot"><span>${esc(foot)}</span><span>${esc(d.density)} · ${d.radius}px</span></div>
    </div></div></div>`;
}
function vAppearance() {
  if (!AP.d) apInit();
  const d = AP.d, rotTabs = [["ringkasan", "Overview"], ["servicedesk", "Ticketing"], ["network", "Network"], ["noc", "ISP"], ["wifi", "WiFi"], ["cyber", "Cyber Security"], ["devices", "Devices"], ["cctv", "Milestone"]];
  return admTitle("Appearance & Theme Studio", "Configure brand identity, accent color, UI density, card radius, login copy, and TV/Wall slideshow settings with live multi-menu preview.", `<button type="button" class="btn ghost sm" data-ap="reset">Reset Defaults</button>`) + intMsg() +
    `<div class="grid" style="margin-top:4px">
      <form class="panel c5 intform" data-ap-form>
        <header><h2>Visual &amp; Theme Settings</h2></header>
        <div class="fld wide"><label>Accent Color</label><div class="ap-swatches">${AP_SW.map(([hex, nm]) => `<button type="button" class="ap-sw ${d.accent.toLowerCase() === hex ? "on" : ""}" style="background:${hex}" data-ap-color="${hex}" title="${esc(nm)}" aria-label="${esc(nm)}"></button>`).join("")}<input type="color" id="apColor" data-ap-f="accent" value="${esc(d.accent)}" style="width:36px;height:28px;padding:1px;border-radius:6px;cursor:pointer"><span class="sub num">${esc(d.accent)}</span></div></div>
        <div class="fld"><label for="apDen">UI Density (All Menus)</label><select id="apDen" data-ap-f="density">${[["compact", "Compact (100% zoom ideal)"], ["comfortable", "Comfortable"], ["spacious", "Spacious"]].map(([k, l]) => `<option value="${k}" ${d.density === k ? "selected" : ""}>${l}</option>`).join("")}</select></div>
        <div class="fld"><label for="apRad">Card Corner Radius: <b class="num">${d.radius}px</b></label><input id="apRad" type="range" min="6" max="22" step="2" data-ap-f="radius" value="${d.radius}"></div>
        <div class="fld"><label for="apTh">Default Theme (New Sessions)</label><select id="apTh" data-ap-f="defTheme">${[["auto", "Auto (follow OS)"], ["light", "Light"], ["dark", "Dark"]].map(([k, l]) => `<option value="${k}" ${d.defTheme === k ? "selected" : ""}>${l}</option>`).join("")}</select></div>
        <h4 class="admsub" style="margin:8px 0 4px">Branding &amp; Login Page</h4>
        <div class="fld"><label for="apBrand">Brand Name</label><input id="apBrand" type="text" data-ap-f="brand" value="${esc(d.brand)}"></div>
        <div class="fld"><label for="apFoot">Footer Text ({year} = current year)</label><input id="apFoot" type="text" data-ap-f="footer" value="${esc(d.footer)}"></div>
        <div class="fld"><label for="apUrl">Public URL (used in Shift Summary links)</label><input id="apUrl" type="url" data-ap-f="publicUrl" value="${esc(d.publicUrl)}"></div>
        <div class="fld"><label for="apEye">Login Eyebrow</label><input id="apEye" type="text" data-ap-f="eyebrow" value="${esc(d.eyebrow)}"></div>
        <div class="fld"><label for="apHl">Login Headline</label><input id="apHl" type="text" data-ap-f="headline" value="${esc(d.headline)}"></div>
        <div class="fld"><label for="apTag">Login Tagline</label><input id="apTag" type="text" data-ap-f="tagline" value="${esc(d.tagline)}"></div>
        <h4 class="admsub" style="margin:8px 0 4px">TV / Wall Slideshow Defaults</h4>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px"><div class="fld"><label for="apWs">Slide Duration (sec)</label><input id="apWs" type="number" min="5" max="120" data-ap-f="wallSlide" value="${d.wallSlide}"></div><div class="fld"><label for="apWr">Auto-Refresh (sec)</label><input id="apWr" type="number" min="15" max="600" data-ap-f="wallRef" value="${d.wallRef}"></div></div>
        <div class="fld"><label>Rotating Menus in Wall Mode</label><div class="chkgrid">${rotTabs.map(([k, l]) => `<label class="chk"><input type="checkbox" data-ap-rot="${k}" ${d.wallTabs.includes(k) ? "checked" : ""}> ${esc(l)}</label>`).join("")}</div></div>
        <div class="acts" style="margin-top:6px"><button class="btn" type="submit"${AP.saving ? " disabled" : ""}>${AP.saving ? "Saving…" : "Save Appearance"}</button></div>
      </form>
      <section class="panel c7">
        <header><h2>Live Preview (All Menus)</h2>
          <div class="acts"><div class="seg">${[["light", "Light"], ["dark", "Dark"]].map(([k, l]) => `<button type="button" data-ap-th="${k}" aria-pressed="${AP.theme === k}">${l}</button>`).join("")}</div><div class="seg">${[["desktop", "Desktop"], ["tablet", "Tablet"], ["mobile", "Mobile"]].map(([k, l]) => `<button type="button" data-ap-vp="${k}" aria-pressed="${AP.vp === k}">${l}</button>`).join("")}</div></div>
        </header>
        <div class="chips sm">${AP_MENUS.map(([k, l]) => `<button type="button" class="chip" data-ap-menu="${k}" aria-pressed="${AP.menu === k}">${esc(l)}</button>`).join("")}</div>
        <div class="ap-stage" id="apStage">${apPreviewHtml()}</div>
      </section>
    </div>`;
}
document.addEventListener("click", async e => {
  const m = e.target.closest("[data-ap-menu]"); if (m) { AP.menu = m.dataset.apMenu; render(false); return; }
  const th = e.target.closest("[data-ap-th]"); if (th) { AP.theme = th.dataset.apTh; render(false); return; }
  const vp = e.target.closest("[data-ap-vp]"); if (vp) { AP.vp = vp.dataset.apVp; render(false); return; }
  const sw = e.target.closest("[data-ap-color]"); if (sw && AP.d) { AP.d.accent = sw.dataset.apColor; render(false); return; }
  const rs = e.target.closest('[data-ap="reset"]');
  if (rs && AP.d) { AP.d.accent = "#1c5cab"; AP.d.density = "compact"; AP.d.radius = 14; AP.d.defTheme = "auto"; AP.d.wallSlide = 15; AP.d.wallRef = 60; render(false); }
});
document.addEventListener("input", e => {
  const f = e.target.dataset && e.target.dataset.apF; if (!f || !AP.d) return;
  AP.d[f] = e.target.type === "range" || e.target.type === "number" ? +e.target.value : e.target.value;
  const st = $("apStage"); if (st) st.innerHTML = apPreviewHtml();
});
document.addEventListener("change", e => {
  if (e.target.dataset && e.target.dataset.apRot && AP.d) {
    const k = e.target.dataset.apRot;
    AP.d.wallTabs = e.target.checked ? [...new Set([...AP.d.wallTabs, k])] : AP.d.wallTabs.filter(x => x !== k);
    const st = $("apStage"); if (st) st.innerHTML = apPreviewHtml();
  } else if (e.target.dataset && e.target.dataset.apF && AP.d) {
    AP.d[e.target.dataset.apF] = e.target.type === "number" ? +e.target.value : e.target.value;
    render(false);
  }
});
document.addEventListener("submit", async e => {
  const f = e.target.closest("[data-ap-form]"); if (!f || !AP.d) return;
  e.preventDefault(); e.stopImmediatePropagation();
  AP.saving = true; render(false);
  const d = AP.d, pairs = [
    ["ui.accent_color", d.accent], ["ui.density", d.density], ["ui.card_radius", +d.radius || 14], ["ui.default_theme", d.defTheme],
    ["ui.brand_name", d.brand.trim() || "TERA Dashboard"], ["ui.footer", d.footer.trim()], ["ui.public_url", d.publicUrl.trim()],
    ["ui.login_eyebrow", d.eyebrow.trim()], ["ui.login_headline", d.headline.trim()], ["ui.login_tagline", d.tagline.trim()],
    ["ui.wall_slide_sec", Math.max(5, +d.wallSlide || 15)], ["ui.wall_refresh_sec", Math.max(15, +d.wallRef || 60)], ["ui.wall_rotate_tabs", d.wallTabs],
  ];
  try {
    for (const [k, v] of pairs) await send("/api/admin/params/" + encodeURIComponent(k), {value: v}, "PUT");
    await reloadConfig(); applyBrand(); $("foot").textContent = footText();
    AP.d = null; INT.msg = {ok: true, t: "Appearance settings saved and applied across all menus."};
  } catch (er) { INT.msg = {ok: false, t: er.message || String(er)}; }
  finally { AP.saving = false; render(false); }
}, true);

function vAdmin() {
  admEnsure();
  let body = "";
  const eu = S.editUser ? (V.users || []).find(x => x.u === S.editUser) : null;
  if (S.adm === "pengguna") {
    const allU = V.users || [], actN = allU.filter(u => u.active).length;
    const uq = (S.uQ || "").trim().toLowerCase(), ur = S.uRoleF || "", us = S.uStatF || "";
    const filtU = allU.filter(u => (!uq || (u.name + " " + u.u + " " + (u.site || "")).toLowerCase().includes(uq)) && (!ur || u.role === ur) && (!us || (us === "active" ? u.active : !u.active)));
    const uRows = filtU.map(u => [
      {h: `<span style="display:inline-flex;align-items:center;gap:8px">${pav(u.name || u.u, 1)}<span><b>${esc(u.name)}</b><span class="sub" style="display:block">@${esc(u.u)}</span></span></span>`},
      {h: `<span class="tag" title="${esc(roleAccess(u.role))}">${esc(ROLES[u.role] || u.role)}</span>`},
      u.site || "All allowed",
      {h: pill(u.active ? "good" : "idle", u.active ? "Active" : "Inactive")},
      dtime(u.last),
      {h: `<span class="acts"><button class="btn ghost sm" data-edit-user="${esc(u.u)}">Edit</button>${u.u === CFG.me.username ? "" : `<button class="btn ghost sm" data-toggle-user="${esc(u.u)}">${u.active ? "Disable" : "Enable"}</button><button class="btn ghost sm" data-reset-user="${esc(u.u)}">Reset PW</button>`}</span>`}
    ]);
    body = admTitle("Users", `${fmt(allU.length)} accounts (${fmt(actN)} active, ${fmt(allU.length - actN)} inactive). Manage user accounts, roles, location scopes, and password resets.`, `<button class="btn" data-adduser>+ Add User</button>`) + `${S.msg ? `<div class="msg ok">${esc(S.msg)}</div>` : ""}
    ${S.addUser || eu ? `<form id="uF" class="form formbox" style="margin-bottom:12px"><div class="fld"><label for="uU">Username *</label><input id="uU" type="text" value="${eu ? esc(eu.u) : ""}" ${eu ? "readonly" : ""}></div><div class="fld"><label for="uN">Name *</label><input id="uN" type="text" value="${eu ? esc(eu.name) : ""}"></div><div class="fld"><label for="uR">Role *</label><select id="uR" ${eu && eu.u === CFG.me.username ? "disabled" : ""}>${Object.entries(ROLES).map(([k, v]) => `<option value="${k}" ${eu && eu.role === k ? "selected" : ""}>${v}</option>`).join("")}</select></div><div class="fld"><label for="uS">Branch (EOS only)</label><select id="uS"><option value="">–</option>${CFG.sites.map(x => `<option ${eu && eu.site === x ? "selected" : ""}>${esc(x)}</option>`).join("")}</select></div><div class="acts wide"><button class="btn" type="submit">Save</button><button class="btn ghost" type="button" data-adduser>Cancel</button>${eu ? "" : `<span class="sub">The initial password is random and must be changed at first login.</span>`}<span class="msg err" id="uMsg"></span></div></form>` : ""}
    <div class="toolbar mbar"><input type="search" id="uQ" class="msearch" value="${esc(S.uQ || "")}" placeholder="Search name, @username, or branch" aria-label="Search users"><select id="uRoleF" aria-label="Filter by role"><option value="">All roles</option>${Object.entries(ROLES).map(([k, v]) => `<option value="${esc(k)}" ${ur === k ? "selected" : ""}>${esc(v)}</option>`).join("")}</select><select id="uStatF" aria-label="Filter by status"><option value="">All statuses</option><option value="active"${us === "active" ? " selected" : ""}>Active</option><option value="inactive"${us === "inactive" ? " selected" : ""}>Inactive</option></select><span class="sub">${fmt(filtU.length)} of ${fmt(allU.length)} shown</span></div>
    ${tbl(["User", "Role", "Location Scope", "Status", "Last Login", "Actions"], uRows, {pageSize: 15, tall: true, empty: "No users match this filter."})}`;
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

