/* IT Pelindo Multi Terminal Dashboard — Admin: Integrations, API Keys, Email (SMTP), Webhooks. Secrets are write-only and never shown again. */
"use strict";
const INT = {integrations: null, apikeys: null, smtp: null, webhooks: null, msg: null, newKey: null, hookEdit: null, keyForm: false, busy: {}};
const intReset = () => { if (typeof AUD !== "undefined") AUD.loaded = false; INT.integrations = INT.apikeys = INT.smtp = INT.webhooks = INT.msg = INT.newKey = INT.hookEdit = INT.todo = INT.status = INT.roles = INT.roleEdit = null; INT.keyForm = false; };
const intDt = s => s ? new Date(s).toLocaleString("id-ID", {dateStyle: "medium", timeStyle: "short"}) : "–";
const intMsg = () => INT.msg ? `<div class="msg ${INT.msg.ok ? "ok" : "err"}">${esc(INT.msg.t)}</div>` : "";
async function intLoad(name, path) {
  if (INT.busy[name]) return; INT.busy[name] = true;
  try { INT[name] = await api("/api/admin/" + path); } catch (e) { INT[name] = {rows: [], error: e.message}; }
  INT.busy[name] = false; render(false);
}
const intLoading = () => `<div class="empty sm">Memuat…</div>`;
const intOpt = (arr, cur) => arr.map(([v, l]) => `<option value="${esc(v)}" ${v === cur ? "selected" : ""}>${esc(l)}</option>`).join("");
const intField = (id, label, inp, wide) => `<div class="fld ${wide ? "wide" : ""}"><label for="${id}">${esc(label)}</label>${inp}</div>`;

function vIntegrations() {
  if (!INT.integrations) { intLoad("integrations", "integrations"); return intLoading(); }
  return intMsg() + `<p class="sub">Data source connectors. Credentials are stored encrypted and never shown again; leave a field empty to keep the stored value.</p><div class="icards">${INT.integrations.rows.map(s => {
    const f = "i_" + s.key;
    const creds = s.creds.map(c => `<div class="fld"><label for="${f}_${c.name}">${esc(c.label)} ${c.set ? `<span class="tag">saved</span>` : c.env_set ? `<span class="tag">from .env (${esc(c.env)})</span>` : `<span class="tag warn">not set</span>`}</label>
      <input id="${f}_${c.name}" data-secret="${esc(c.name)}" type="password" autocomplete="new-password" placeholder="${c.set ? "•••••••• (leave empty = unchanged)" : "Fill in to save"}">${c.set ? `<button type="button" class="btn ghost sm" data-w data-int="clear" data-key="${esc(s.key)}" data-name="${esc(c.name)}">Remove saved</button>` : ""}</div>`).join("");
    const body = s.api_capable ? `<form class="form intform" data-int-form="${esc(s.key)}">
        ${intField(f + "_mode", "Mode", `<select id="${f}_mode" data-f="mode">${intOpt([["api", "API (sinkron terjadwal)"], ["import", "Impor RAW manual"]], s.mode)}</select>`)}
        ${intField(f + "_en", "Status", `<select id="${f}_en" data-f="enabled">${intOpt([["true", "Active"], ["false", "Inactive"]], String(s.enabled))}</select>`)}
        ${intField(f + "_iv", "Interval (minutes)", `<input id="${f}_iv" data-f="interval_min" type="number" min="1" max="1440" value="${esc(s.interval_min)}">`)}
        ${intField(f + "_tls", "Verify TLS", `<select id="${f}_tls" data-f="verify_tls">${intOpt([["true", "Yes"], ["false", "No (internal certificate)"]], String(s.verify_tls))}</select>`)}
        ${intField(f + "_url", "Base URL", `<input id="${f}_url" data-f="base_url" type="text" autocomplete="off" placeholder="e.g. 10.181.1.224 or https://host/zabbix" value="${esc(s.base_url)}">`, true)}
        ${(s.extra || []).map(e => intField(f + "_x_" + e.key, e.label, `<textarea id="${f}_x_${e.key}" data-xlist="${esc(e.key)}" rows="3" spellcheck="false">${esc((e.value || []).join("\n"))}</textarea>`, true)).join("")}
        ${creds}
        <div class="acts wide"><button class="btn" type="submit" data-w>Save</button><button class="btn ghost" type="button" data-int="test" data-key="${esc(s.key)}" data-w>Test connection</button><button class="btn ghost" type="button" data-int="sync" data-key="${esc(s.key)}" data-w>Sync now</button></div></form>`
      : `<p class="sub">This source has no API. Data comes in through RAW upload in Report → Data.</p>`;
    return `<article class="icard"><header><b>${esc(s.label)}</b><span class="tag ${s.enabled ? "on" : ""}">${s.enabled ? "Active" : "Inactive"}</span><span class="tag">${s.mode === "api" ? "API" : "Impor"}</span></header>
      <span class="sub">${esc(s.tip || "")}</span>
      ${s.stats ? `<span class="sub">Devices: <b>${s.stats.total}</b> · up ${s.stats.up} · down <b class="${s.stats.down ? "errtx" : ""}">${s.stats.down}</b> · maintenance ${s.stats.maintenance} · disabled ${s.stats.disabled}</span>` : ""}
      <span class="sub">Last successful sync: ${esc(intDt(s.last_ok_at))}${s.last_error ? ` · <b class="errtx">error: ${esc(String(s.last_error).slice(0, 120))}</b>` : ""}</span>${body}</article>`;
  }).join("")}</div>`;
}

function vApiKeys(roles) {
  if (!INT.apikeys) { intLoad("apikeys", "apikeys"); return intLoading(); }
  const rk = Object.entries(CFG.roles).filter(([k, r]) => !r.is_admin).map(([k, r]) => [k, r.label]);
  const o = location.origin;
  const nk = INT.newKey ? `<div class="keybox"><b>Copy this key now, it will not be shown again:</b><code id="newKeyVal">${esc(INT.newKey)}</code><button class="btn ghost sm" type="button" data-int="copykey">Copy</button></div>` : "";
  const form = INT.keyForm ? `<form class="form formbox intform" data-int-form="apikey">
      ${intField("k_name", "Name / purpose *", `<input id="k_name" data-f="name" type="text" placeholder="mis. Power BI">`)}
      ${intField("k_role", "Hak akses (role) *", `<select id="k_role" data-f="role_key">${intOpt(rk, "")}</select>`)}
      ${intField("k_site", "Limit to location", `<select id="k_site" data-f="site"><option value="">All allowed by role</option>${CFG.sites.map(x => `<option>${esc(x)}</option>`).join("")}</select>`)}
      ${intField("k_days", "Valid for", `<select id="k_days" data-f="days">${intOpt([["", "No expiry"], ["30", "30 days"], ["90", "90 days"], ["365", "1 year"]], "90")}</select>`)}
      <div class="acts wide"><button class="btn" type="submit" data-w>Generate</button><button class="btn ghost" type="button" data-int="keyform">Cancel</button><span class="sub">Keys are read-only (GET) and have no Admin access.</span></div></form>` : "";
  return intMsg() + `<div class="toolbar"><span class="sub">API keys for other systems that read dashboard data.</span><button class="btn" type="button" data-w data-int="keyform">+ Generate key</button></div>${nk}${form}
    <div class="mcards">${INT.apikeys.rows.map(k => `<article class="mcard ${k.revoked ? "off" : ""}"><div class="mh"><b>${esc(k.name)}</b><span class="mid">${esc(k.prefix)}…</span></div>
      <div class="mchips"><span class="mchip"><i>role</i>${esc(CFG.roles[k.role_key] ? CFG.roles[k.role_key].label : k.role_key)}</span>${k.site ? `<span class="mchip"><i>location</i>${esc(k.site)}</span>` : ""}<span class="mchip"><i>last used</i>${esc(intDt(k.last_used_at))}</span><span class="mchip"><i>expires</i>${k.expires_at ? esc(intDt(k.expires_at)) : "never"}</span>${k.revoked ? `<span class="mchip">revoked</span>` : ""}</div>
      ${k.revoked ? "" : `<button class="btn ghost" type="button" data-w data-int="revoke" data-id="${k.id}">Revoke</button>`}</article>`).join("") || `<div class="empty sm">No API keys yet.</div>`}</div>
    <details class="howto"><summary>How to use</summary><pre>curl -H "X-API-Key: itoc_xxx" "${esc(o)}/api/view/servicedesk?from=2026-10-01&amp;to=2026-10-19"</pre><span class="sub">The same read endpoints as the dashboard (/api/view/…, /api/report/…) follow the role rights on the key.</span></details>`;
}

function vSmtp() {
  if (!INT.smtp) { intLoad("smtp", "smtp"); return intLoading(); }
  const c = INT.smtp;
  return intMsg() + `<p class="sub">Used for test emails now, and later for scheduled reports and password resets. The password is stored encrypted.</p>
    <form class="form formbox intform" data-int-form="smtp">
      ${intField("m_host", "Host", `<input id="m_host" data-f="host" type="text" placeholder="smtp.pelindo.co.id" value="${esc(c.host)}">`)}
      ${intField("m_port", "Port", `<input id="m_port" data-f="port" type="number" value="${esc(c.port)}">`)}
      ${intField("m_sec", "Keamanan", `<select id="m_sec" data-f="security">${intOpt([["starttls", "STARTTLS (587)"], ["ssl", "SSL/TLS (465)"], ["none", "No encryption"]], c.security)}</select>`)}
      ${intField("m_user", "Username", `<input id="m_user" data-f="user" type="text" autocomplete="off" value="${esc(c.user)}">`)}
      ${intField("m_pw", "Password " + (c.password_set ? "(saved)" : ""), `<input id="m_pw" data-f="password" type="password" autocomplete="new-password" placeholder="${c.password_set ? "•••••••• (empty = unchanged)" : ""}">`)}
      ${intField("m_from", "Alamat pengirim", `<input id="m_from" data-f="sender" type="email" placeholder="itoc@pelindo.co.id" value="${esc(c.sender)}">`)}
      ${intField("m_fn", "Sender name", `<input id="m_fn" data-f="from_name" type="text" value="${esc(c.from_name)}">`)}
      <div class="acts wide"><button class="btn" type="submit" data-w>Save</button></div></form>
    <form class="form intform smtptest" data-int-form="smtptest"><div class="fld"><label for="m_to">Send test email to</label><input id="m_to" data-f="to" type="email" placeholder="name@pelindo.co.id"></div><div class="acts"><button class="btn ghost" type="submit" data-w>Send test</button></div></form>`;
}

function vWebhooks() {
  if (!INT.webhooks) { intLoad("webhooks", "webhooks"); return intLoading(); }
  const W = INT.webhooks, e = INT.hookEdit, ev = Object.entries(W.events || {}).filter(([k]) => k !== "test"), kinds = Object.entries(W.kinds || {});
  const form = e ? `<form class="form formbox intform" data-int-form="webhook">
      ${intField("w_name", "Name *", `<input id="w_name" data-f="name" type="text" value="${esc(e.name || "")}">`)}
      ${intField("w_kind", "Type", `<select id="w_kind" data-f="kind">${intOpt(kinds, e.kind || "generic")}</select>`)}
      ${intField("w_url", "URL " + (e.id ? "(saved, empty = unchanged)" : "*"), `<input id="w_url" data-f="url" type="url" autocomplete="off" placeholder="${e.id ? esc(e.url) : "https://…"}">`, true)}
      <div class="fld wide"><span class="lbl">Send on</span><div class="evs">${ev.map(([k, l]) => `<label class="chk"><input type="checkbox" data-ev="${esc(k)}" ${(e.events || []).includes(k) ? "checked" : ""}> ${esc(l)}</label>`).join("")}</div></div>
      ${intField("w_en", "Status", `<select id="w_en" data-f="enabled">${intOpt([["true", "Active"], ["false", "Inactive"]], String(e.enabled !== false))}</select>`)}
      <div class="acts wide"><button class="btn" type="submit" data-w>Save</button><button class="btn ghost" type="button" data-int="hookform" data-id="x">Cancel</button><span class="sub">Telegram: pakai URL …/sendMessage?chat_id=ID. Teams/Slack: URL incoming webhook.</span></div></form>` : "";
  return intMsg() + `<div class="toolbar"><span class="sub">Automatic notifications to chat or other systems.</span><button class="btn" type="button" data-w data-int="hookform" data-id="new">+ Add webhook</button></div>${form}
    <div class="mcards">${W.rows.map(w => `<article class="mcard"><div class="mh"><b>${esc(w.name)}</b><span class="mid">${esc((W.kinds || {})[w.kind] || w.kind)}</span></div>
      <div class="mchips"><span class="mchip"><i>url</i>${esc(w.url)}</span>${w.events.map(k => `<span class="mchip">${esc((W.events || {})[k] || k)}</span>`).join("")}${w.enabled ? "" : `<span class="mchip">disabled</span>`}<span class="mchip"><i>last</i>${esc(w.last_status || "never")}${w.last_at ? " · " + esc(intDt(w.last_at)) : ""}</span></div>
      <span class="acts"><button class="btn ghost" type="button" data-w data-int="hookform" data-id="${w.id}">Edit</button><button class="btn ghost" type="button" data-w data-int="hooktest" data-id="${w.id}">Test</button><button class="btn ghost" type="button" data-w data-int="hookdel" data-id="${w.id}">Delete</button></span></article>`).join("") || `<div class="empty sm">No webhooks yet.</div>`}</div>`;
}

const intVal = el => el.type === "checkbox" ? el.checked : el.value;
async function intSaveIntegration(f) {
  const k = f.dataset.intForm, v = intForm(f), secrets = {}, lists = {};
  f.querySelectorAll("[data-secret]").forEach(el => { if (el.value.trim()) secrets[el.dataset.secret] = el.value; });
  f.querySelectorAll("[data-xlist]").forEach(el => { lists[el.dataset.xlist] = el.value.split("\n"); });
  await send("/api/admin/integrations/" + k, {mode: v.mode, enabled: v.enabled === "true", interval_min: +v.interval_min || 60, base_url: v.base_url, verify_tls: v.verify_tls === "true", secrets, config_lists: lists}, "PUT");
}
const intForm = f => Object.fromEntries([...f.querySelectorAll("[data-f]")].map(el => [el.dataset.f, intVal(el)]));
const intDone = (name, ok, t) => { INT[name] = null; INT.msg = {ok, t}; render(false); };

document.addEventListener("click", async e => {
  const b = e.target.closest("[data-int]"); if (!b) return;
  const a = b.dataset.int, id = b.dataset.id, key = b.dataset.key;
  try {
    if (a === "test" || a === "sync") { const fm = b.closest("form"); if (fm) { b.disabled = true; b.textContent = "Menyimpan…"; await intSaveIntegration(fm); } }
    if (a === "test") { b.disabled = true; b.textContent = "Testing…"; const r = await send("/api/admin/integrations/" + key + "/test", {}).catch(er => ({ok: false, msg: er.message})); INT.msg = {ok: r.ok, t: r.msg || "Failed"}; render(false); }
    else if (a === "sync") { b.disabled = true; b.textContent = "Syncing…"; const r = await send("/api/ingest/sync/" + key, {}).catch(er => ({ok: false, msg: er.message})); INT.integrations = null; INT.msg = {ok: r.ok !== false, t: r.ok === false ? r.msg : "Sync finished: " + (r.rows ?? 0) + " rows"}; render(false); }
    else if (a === "clear") { if (!confirm("Remove the saved credentials?")) return; await send("/api/admin/integrations/" + key, {clear: [b.dataset.name]}, "PUT"); intDone("integrations", true, "Credentials removed."); }
    else if (a === "keyform") { INT.keyForm = !INT.keyForm; INT.newKey = null; render(false); }
    else if (a === "copykey") { try { await navigator.clipboard.writeText($("newKeyVal").textContent); b.textContent = "Tersalin"; } catch (er) { const r = document.createRange(); r.selectNode($("newKeyVal")); getSelection().removeAllRanges(); getSelection().addRange(r); } }
    else if (a === "revoke") { if (!confirm("Revoke this API key? Systems using it will be rejected.")) return; await api("/api/admin/apikeys/" + id, {method: "DELETE"}); intDone("apikeys", true, "API key revoked."); }
    else if (a === "hookform") { INT.hookEdit = id === "x" ? null : id === "new" ? {events: ["handover_high"], enabled: true} : Object.assign({}, INT.webhooks.rows.find(w => String(w.id) === id)); INT.msg = null; render(false); }
    else if (a === "hooktest") { b.disabled = true; b.textContent = "Mengirim…"; const r = await send("/api/admin/webhooks/" + id + "/test", {}).catch(er => ({ok: false, msg: er.message})); INT.webhooks = null; INT.msg = {ok: r.ok, t: r.msg || "Failed"}; render(false); }
    else if (a === "hookdel") { if (!confirm("Delete this webhook?")) return; await api("/api/admin/webhooks/" + id, {method: "DELETE"}); intDone("webhooks", true, "Webhook deleted."); }
  } catch (er) { if (er) { INT.msg = {ok: false, t: er.message || String(er)}; render(false); } }
});

document.addEventListener("submit", async e => {
  const f = e.target.closest("[data-int-form]"); if (!f) return;
  e.preventDefault();
  const k = f.dataset.intForm, v = intForm(f);
  try {
    if (k === "smtp") { await send("/api/admin/smtp", {host: v.host, port: +v.port || 587, security: v.security, user: v.user, password: v.password || null, sender: v.sender, from_name: v.from_name}, "PUT"); intDone("smtp", true, "SMTP settings saved."); }
    else if (k === "smtptest") { const r = await send("/api/admin/smtp/test", {to: v.to}); INT.msg = {ok: true, t: r.msg}; render(false); }
    else if (k === "apikey") { const r = await send("/api/admin/apikeys", {name: v.name, role_key: v.role_key, site: v.site || null, days: v.days ? +v.days : null}); INT.apikeys = null; INT.keyForm = false; INT.newKey = r.key; INT.msg = {ok: true, t: "API key created."}; render(false); }
    else if (k === "webhook") {
      const body = {name: v.name, kind: v.kind, url: v.url || null, enabled: v.enabled === "true", events: [...f.querySelectorAll("[data-ev]:checked")].map(x => x.dataset.ev)};
      await send(INT.hookEdit && INT.hookEdit.id ? "/api/admin/webhooks/" + INT.hookEdit.id : "/api/admin/webhooks", body, INT.hookEdit && INT.hookEdit.id ? "PUT" : "POST");
      INT.hookEdit = null; intDone("webhooks", true, "Webhook saved.");
    } else {
      await intSaveIntegration(f);
      intDone("integrations", true, "Saved.");
    }
  } catch (er) { INT.msg = {ok: false, t: (er && er.message) || String(er)}; render(false); }
});
/* ---------- Audit log: filter, daftar bertahap, ekspor CSV ---------- */
const AUD = {rows: [], total: 0, users: [], f: {frm: "", to: "", who: "", q: ""}, loaded: false, busy: false};
const audQs = (o = {}) => new URLSearchParams(Object.entries({...AUD.f, ...o}).filter(([, v]) => v !== "" && v != null)).toString();
async function audLoad(more) {
  if (AUD.busy) return; AUD.busy = true;
  try {
    const r = await api("/api/admin/audit?" + audQs({limit: 100, offset: more ? AUD.rows.length : 0}));
    AUD.rows = more ? AUD.rows.concat(r.rows) : r.rows; AUD.total = r.total; AUD.users = r.users; AUD.err = "";
  } catch (e) { AUD.err = e.message; }
  AUD.loaded = true; AUD.busy = false; render(false);
}
function vAudit() {
  if (!AUD.loaded) { audLoad(false); return intLoading(); }
  const f = AUD.f, rows = AUD.rows.map(a => [a.at.replace("T", " ").slice(0, 19), a.by, a.t, a.ip || "–"]);
  return `<p class="sub">Log of user activity and settings changes. Export uses the current filters.</p>${AUD.err ? `<div class="msg err">${esc(AUD.err)}</div>` : ""}
    <form class="toolbar mbar" data-int-form="audit">
      <label class="sub">Dari <input type="date" data-f="frm" value="${esc(f.frm)}"></label><label class="sub">Sampai <input type="date" data-f="to" value="${esc(f.to)}"></label>
      <label class="sub">User <select data-f="who"><option value="">All</option>${AUD.users.map(u => `<option ${u === f.who ? "selected" : ""}>${esc(u)}</option>`).join("")}</select></label>
      <input type="search" class="msearch" data-f="q" value="${esc(f.q)}" placeholder="Search activity or user" aria-label="Search">
      <button class="btn" type="submit">Terapkan</button><button class="btn ghost" type="button" data-int="audreset">Reset</button>
      <span class="mtools"><button class="btn" type="button" data-int="audexport">Ekspor CSV</button></span></form>
    <p class="sub">${fmt(AUD.total)} catatan${AUD.rows.length < AUD.total ? `, menampilkan ${fmt(AUD.rows.length)}` : ""}</p>
    ${tbl(["Time (WIB)", "User", "Activity", "IP"], rows, {tall: true, empty: "No records for this filter."})}
    ${AUD.rows.length < AUD.total ? `<div class="toolbar"><button class="btn ghost" type="button" data-int="audmore">Show more</button></div>` : ""}`;
}
document.addEventListener("click", e => {
  const b = e.target.closest("[data-int]"); if (!b) return;
  const a = b.dataset.int;
  if (a === "audreset") { AUD.f = {frm: "", to: "", who: "", q: ""}; AUD.loaded = false; render(false); }
  else if (a === "audmore") audLoad(true);
  else if (a === "audexport") { const l = document.createElement("a"); l.href = "/api/admin/audit/export?" + audQs(); l.download = ""; document.body.appendChild(l); l.click(); l.remove(); }
});
document.addEventListener("submit", e => {
  const f = e.target.closest('[data-int-form="audit"]'); if (!f) return;
  e.preventDefault(); e.stopImmediatePropagation();
  AUD.f = intForm(f); AUD.loaded = false; render(false);
}, true);
