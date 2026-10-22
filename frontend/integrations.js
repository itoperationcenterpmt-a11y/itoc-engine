/* IT Pelindo Multi Terminal Dashboard — Admin: Integrations, API Keys, Email (SMTP), Webhooks. Rahasia hanya ditulis, tidak pernah ditampilkan ulang. */
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
  return intMsg() + `<p class="sub">Konektor sumber data. Kredensial disimpan terenkripsi dan tidak ditampilkan lagi; kosongkan kolom untuk membiarkan yang tersimpan.</p><div class="icards">${INT.integrations.rows.map(s => {
    const f = "i_" + s.key;
    const creds = s.creds.map(c => `<div class="fld"><label for="${f}_${c.name}">${esc(c.label)} ${c.set ? `<span class="tag">tersimpan</span>` : c.env_set ? `<span class="tag">dari .env (${esc(c.env)})</span>` : `<span class="tag warn">belum diisi</span>`}</label>
      <input id="${f}_${c.name}" data-secret="${esc(c.name)}" type="password" autocomplete="new-password" placeholder="${c.set ? "•••••••• (biarkan kosong = tidak diubah)" : "Isi untuk menyimpan"}">${c.set ? `<button type="button" class="btn ghost sm" data-w data-int="clear" data-key="${esc(s.key)}" data-name="${esc(c.name)}">Hapus tersimpan</button>` : ""}</div>`).join("");
    const body = s.api_capable ? `<form class="form intform" data-int-form="${esc(s.key)}">
        ${intField(f + "_mode", "Mode", `<select id="${f}_mode" data-f="mode">${intOpt([["api", "API (sinkron terjadwal)"], ["import", "Impor RAW manual"]], s.mode)}</select>`)}
        ${intField(f + "_en", "Status", `<select id="${f}_en" data-f="enabled">${intOpt([["true", "Aktif"], ["false", "Nonaktif"]], String(s.enabled))}</select>`)}
        ${intField(f + "_iv", "Interval (menit)", `<input id="${f}_iv" data-f="interval_min" type="number" min="1" max="1440" value="${esc(s.interval_min)}">`)}
        ${intField(f + "_tls", "Verifikasi TLS", `<select id="${f}_tls" data-f="verify_tls">${intOpt([["true", "Ya"], ["false", "Tidak (sertifikat internal)"]], String(s.verify_tls))}</select>`)}
        ${intField(f + "_url", "Base URL", `<input id="${f}_url" data-f="base_url" type="text" autocomplete="off" placeholder="mis. 10.181.1.224 atau https://host/zabbix" value="${esc(s.base_url)}">`, true)}
        ${(s.extra || []).map(e => intField(f + "_x_" + e.key, e.label, `<textarea id="${f}_x_${e.key}" data-xlist="${esc(e.key)}" rows="3" spellcheck="false">${esc((e.value || []).join("\n"))}</textarea>`, true)).join("")}
        ${creds}
        <div class="acts wide"><button class="btn" type="submit" data-w>Simpan</button><button class="btn ghost" type="button" data-int="test" data-key="${esc(s.key)}" data-w>Uji koneksi</button><button class="btn ghost" type="button" data-int="sync" data-key="${esc(s.key)}" data-w>Sinkron sekarang</button></div></form>`
      : `<p class="sub">Sumber ini belum punya API. Data masuk lewat unggah RAW di menu Report → Data.</p>`;
    return `<article class="icard"><header><b>${esc(s.label)}</b><span class="tag ${s.enabled ? "on" : ""}">${s.enabled ? "Aktif" : "Nonaktif"}</span><span class="tag">${s.mode === "api" ? "API" : "Impor"}</span></header>
      <span class="sub">${esc(s.tip || "")}</span>
      ${s.stats ? `<span class="sub">Perangkat: <b>${s.stats.total}</b> · up ${s.stats.up} · down <b class="${s.stats.down ? "errtx" : ""}">${s.stats.down}</b> · maintenance ${s.stats.maintenance} · nonaktif ${s.stats.disabled}</span>` : ""}
      <span class="sub">Sinkron terakhir OK: ${esc(intDt(s.last_ok_at))}${s.last_error ? ` · <b class="errtx">galat: ${esc(String(s.last_error).slice(0, 120))}</b>` : ""}</span>${body}</article>`;
  }).join("")}</div>`;
}

function vApiKeys(roles) {
  if (!INT.apikeys) { intLoad("apikeys", "apikeys"); return intLoading(); }
  const rk = Object.entries(CFG.roles).filter(([k, r]) => !r.is_admin).map(([k, r]) => [k, r.label]);
  const o = location.origin;
  const nk = INT.newKey ? `<div class="keybox"><b>Salin kunci ini sekarang, tidak akan ditampilkan lagi:</b><code id="newKeyVal">${esc(INT.newKey)}</code><button class="btn ghost sm" type="button" data-int="copykey">Copy</button></div>` : "";
  const form = INT.keyForm ? `<form class="form formbox intform" data-int-form="apikey">
      ${intField("k_name", "Nama / tujuan *", `<input id="k_name" data-f="name" type="text" placeholder="mis. Power BI">`)}
      ${intField("k_role", "Hak akses (role) *", `<select id="k_role" data-f="role_key">${intOpt(rk, "")}</select>`)}
      ${intField("k_site", "Batasi lokasi", `<select id="k_site" data-f="site"><option value="">Semua sesuai role</option>${CFG.sites.map(x => `<option>${esc(x)}</option>`).join("")}</select>`)}
      ${intField("k_days", "Berlaku", `<select id="k_days" data-f="days">${intOpt([["", "Tanpa batas"], ["30", "30 hari"], ["90", "90 hari"], ["365", "1 tahun"]], "90")}</select>`)}
      <div class="acts wide"><button class="btn" type="submit" data-w>Generate</button><button class="btn ghost" type="button" data-int="keyform">Batal</button><span class="sub">Kunci hanya bisa membaca (GET) dan tidak punya akses Admin.</span></div></form>` : "";
  return intMsg() + `<div class="toolbar"><span class="sub">API key untuk sistem lain yang membaca data dashboard.</span><button class="btn" type="button" data-w data-int="keyform">+ Generate key</button></div>${nk}${form}
    <div class="mcards">${INT.apikeys.rows.map(k => `<article class="mcard ${k.revoked ? "off" : ""}"><div class="mh"><b>${esc(k.name)}</b><span class="mid">${esc(k.prefix)}…</span></div>
      <div class="mchips"><span class="mchip"><i>role</i>${esc(CFG.roles[k.role_key] ? CFG.roles[k.role_key].label : k.role_key)}</span>${k.site ? `<span class="mchip"><i>lokasi</i>${esc(k.site)}</span>` : ""}<span class="mchip"><i>dipakai</i>${esc(intDt(k.last_used_at))}</span><span class="mchip"><i>berakhir</i>${k.expires_at ? esc(intDt(k.expires_at)) : "tidak"}</span>${k.revoked ? `<span class="mchip">dicabut</span>` : ""}</div>
      ${k.revoked ? "" : `<button class="btn ghost" type="button" data-w data-int="revoke" data-id="${k.id}">Revoke</button>`}</article>`).join("") || `<div class="empty sm">Belum ada API key.</div>`}</div>
    <details class="howto"><summary>Cara memakai</summary><pre>curl -H "X-API-Key: itoc_xxx" "${esc(o)}/api/view/servicedesk?from=2026-10-01&amp;to=2026-10-19"</pre><span class="sub">Endpoint baca yang sama dengan dashboard (/api/view/…, /api/report/…) mengikuti hak role pada kunci.</span></details>`;
}

function vSmtp() {
  if (!INT.smtp) { intLoad("smtp", "smtp"); return intLoading(); }
  const c = INT.smtp;
  return intMsg() + `<p class="sub">Dipakai untuk email uji sekarang, dan untuk laporan terjadwal atau reset password nantinya. Kata sandi disimpan terenkripsi.</p>
    <form class="form formbox intform" data-int-form="smtp">
      ${intField("m_host", "Host", `<input id="m_host" data-f="host" type="text" placeholder="smtp.pelindo.co.id" value="${esc(c.host)}">`)}
      ${intField("m_port", "Port", `<input id="m_port" data-f="port" type="number" value="${esc(c.port)}">`)}
      ${intField("m_sec", "Keamanan", `<select id="m_sec" data-f="security">${intOpt([["starttls", "STARTTLS (587)"], ["ssl", "SSL/TLS (465)"], ["none", "Tanpa enkripsi"]], c.security)}</select>`)}
      ${intField("m_user", "Username", `<input id="m_user" data-f="user" type="text" autocomplete="off" value="${esc(c.user)}">`)}
      ${intField("m_pw", "Password " + (c.password_set ? "(tersimpan)" : ""), `<input id="m_pw" data-f="password" type="password" autocomplete="new-password" placeholder="${c.password_set ? "•••••••• (kosong = tidak diubah)" : ""}">`)}
      ${intField("m_from", "Alamat pengirim", `<input id="m_from" data-f="sender" type="email" placeholder="itoc@pelindo.co.id" value="${esc(c.sender)}">`)}
      ${intField("m_fn", "Nama pengirim", `<input id="m_fn" data-f="from_name" type="text" value="${esc(c.from_name)}">`)}
      <div class="acts wide"><button class="btn" type="submit" data-w>Simpan</button></div></form>
    <form class="form intform smtptest" data-int-form="smtptest"><div class="fld"><label for="m_to">Kirim email uji ke</label><input id="m_to" data-f="to" type="email" placeholder="nama@pelindo.co.id"></div><div class="acts"><button class="btn ghost" type="submit" data-w>Send test</button></div></form>`;
}

function vWebhooks() {
  if (!INT.webhooks) { intLoad("webhooks", "webhooks"); return intLoading(); }
  const W = INT.webhooks, e = INT.hookEdit, ev = Object.entries(W.events || {}).filter(([k]) => k !== "test"), kinds = Object.entries(W.kinds || {});
  const form = e ? `<form class="form formbox intform" data-int-form="webhook">
      ${intField("w_name", "Nama *", `<input id="w_name" data-f="name" type="text" value="${esc(e.name || "")}">`)}
      ${intField("w_kind", "Jenis", `<select id="w_kind" data-f="kind">${intOpt(kinds, e.kind || "generic")}</select>`)}
      ${intField("w_url", "URL " + (e.id ? "(tersimpan, kosong = tidak diubah)" : "*"), `<input id="w_url" data-f="url" type="url" autocomplete="off" placeholder="${e.id ? esc(e.url) : "https://…"}">`, true)}
      <div class="fld wide"><span class="lbl">Kirim saat</span><div class="evs">${ev.map(([k, l]) => `<label class="chk"><input type="checkbox" data-ev="${esc(k)}" ${(e.events || []).includes(k) ? "checked" : ""}> ${esc(l)}</label>`).join("")}</div></div>
      ${intField("w_en", "Status", `<select id="w_en" data-f="enabled">${intOpt([["true", "Aktif"], ["false", "Nonaktif"]], String(e.enabled !== false))}</select>`)}
      <div class="acts wide"><button class="btn" type="submit" data-w>Simpan</button><button class="btn ghost" type="button" data-int="hookform" data-id="x">Batal</button><span class="sub">Telegram: pakai URL …/sendMessage?chat_id=ID. Teams/Slack: URL incoming webhook.</span></div></form>` : "";
  return intMsg() + `<div class="toolbar"><span class="sub">Notifikasi otomatis ke chat atau sistem lain.</span><button class="btn" type="button" data-w data-int="hookform" data-id="new">+ Tambah webhook</button></div>${form}
    <div class="mcards">${W.rows.map(w => `<article class="mcard"><div class="mh"><b>${esc(w.name)}</b><span class="mid">${esc((W.kinds || {})[w.kind] || w.kind)}</span></div>
      <div class="mchips"><span class="mchip"><i>url</i>${esc(w.url)}</span>${w.events.map(k => `<span class="mchip">${esc((W.events || {})[k] || k)}</span>`).join("")}${w.enabled ? "" : `<span class="mchip">nonaktif</span>`}<span class="mchip"><i>terakhir</i>${esc(w.last_status || "belum pernah")}${w.last_at ? " · " + esc(intDt(w.last_at)) : ""}</span></div>
      <span class="acts"><button class="btn ghost" type="button" data-w data-int="hookform" data-id="${w.id}">Ubah</button><button class="btn ghost" type="button" data-w data-int="hooktest" data-id="${w.id}">Test</button><button class="btn ghost" type="button" data-w data-int="hookdel" data-id="${w.id}">Hapus</button></span></article>`).join("") || `<div class="empty sm">Belum ada webhook.</div>`}</div>`;
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
    if (a === "test") { b.disabled = true; b.textContent = "Menguji…"; const r = await send("/api/admin/integrations/" + key + "/test", {}).catch(er => ({ok: false, msg: er.message})); INT.msg = {ok: r.ok, t: r.msg || "Gagal"}; render(false); }
    else if (a === "sync") { b.disabled = true; b.textContent = "Menyinkron…"; const r = await send("/api/ingest/sync/" + key, {}).catch(er => ({ok: false, msg: er.message})); INT.integrations = null; INT.msg = {ok: r.ok !== false, t: r.ok === false ? r.msg : "Sinkron selesai: " + (r.rows ?? 0) + " baris"}; render(false); }
    else if (a === "clear") { if (!confirm("Hapus kredensial tersimpan?")) return; await send("/api/admin/integrations/" + key, {clear: [b.dataset.name]}, "PUT"); intDone("integrations", true, "Kredensial dihapus."); }
    else if (a === "keyform") { INT.keyForm = !INT.keyForm; INT.newKey = null; render(false); }
    else if (a === "copykey") { try { await navigator.clipboard.writeText($("newKeyVal").textContent); b.textContent = "Tersalin"; } catch (er) { const r = document.createRange(); r.selectNode($("newKeyVal")); getSelection().removeAllRanges(); getSelection().addRange(r); } }
    else if (a === "revoke") { if (!confirm("Cabut API key ini? Sistem yang memakainya akan ditolak.")) return; await api("/api/admin/apikeys/" + id, {method: "DELETE"}); intDone("apikeys", true, "API key dicabut."); }
    else if (a === "hookform") { INT.hookEdit = id === "x" ? null : id === "new" ? {events: ["handover_high"], enabled: true} : Object.assign({}, INT.webhooks.rows.find(w => String(w.id) === id)); INT.msg = null; render(false); }
    else if (a === "hooktest") { b.disabled = true; b.textContent = "Mengirim…"; const r = await send("/api/admin/webhooks/" + id + "/test", {}).catch(er => ({ok: false, msg: er.message})); INT.webhooks = null; INT.msg = {ok: r.ok, t: r.msg || "Gagal"}; render(false); }
    else if (a === "hookdel") { if (!confirm("Hapus webhook ini?")) return; await api("/api/admin/webhooks/" + id, {method: "DELETE"}); intDone("webhooks", true, "Webhook dihapus."); }
  } catch (er) { if (er) { INT.msg = {ok: false, t: er.message || String(er)}; render(false); } }
});

document.addEventListener("submit", async e => {
  const f = e.target.closest("[data-int-form]"); if (!f) return;
  e.preventDefault();
  const k = f.dataset.intForm, v = intForm(f);
  try {
    if (k === "smtp") { await send("/api/admin/smtp", {host: v.host, port: +v.port || 587, security: v.security, user: v.user, password: v.password || null, sender: v.sender, from_name: v.from_name}, "PUT"); intDone("smtp", true, "Pengaturan SMTP tersimpan."); }
    else if (k === "smtptest") { const r = await send("/api/admin/smtp/test", {to: v.to}); INT.msg = {ok: true, t: r.msg}; render(false); }
    else if (k === "apikey") { const r = await send("/api/admin/apikeys", {name: v.name, role_key: v.role_key, site: v.site || null, days: v.days ? +v.days : null}); INT.apikeys = null; INT.keyForm = false; INT.newKey = r.key; INT.msg = {ok: true, t: "API key dibuat."}; render(false); }
    else if (k === "webhook") {
      const body = {name: v.name, kind: v.kind, url: v.url || null, enabled: v.enabled === "true", events: [...f.querySelectorAll("[data-ev]:checked")].map(x => x.dataset.ev)};
      await send(INT.hookEdit && INT.hookEdit.id ? "/api/admin/webhooks/" + INT.hookEdit.id : "/api/admin/webhooks", body, INT.hookEdit && INT.hookEdit.id ? "PUT" : "POST");
      INT.hookEdit = null; intDone("webhooks", true, "Webhook tersimpan.");
    } else {
      await intSaveIntegration(f);
      intDone("integrations", true, "Tersimpan.");
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
  return `<p class="sub">Catatan aktivitas pengguna dan perubahan pengaturan. Ekspor memakai filter yang sedang dipilih.</p>${AUD.err ? `<div class="msg err">${esc(AUD.err)}</div>` : ""}
    <form class="toolbar mbar" data-int-form="audit">
      <label class="sub">Dari <input type="date" data-f="frm" value="${esc(f.frm)}"></label><label class="sub">Sampai <input type="date" data-f="to" value="${esc(f.to)}"></label>
      <label class="sub">Pengguna <select data-f="who"><option value="">Semua</option>${AUD.users.map(u => `<option ${u === f.who ? "selected" : ""}>${esc(u)}</option>`).join("")}</select></label>
      <input type="search" class="msearch" data-f="q" value="${esc(f.q)}" placeholder="Cari aktivitas atau pengguna" aria-label="Cari">
      <button class="btn" type="submit">Terapkan</button><button class="btn ghost" type="button" data-int="audreset">Atur Ulang</button>
      <span class="mtools"><button class="btn" type="button" data-int="audexport">Ekspor CSV</button></span></form>
    <p class="sub">${fmt(AUD.total)} catatan${AUD.rows.length < AUD.total ? `, menampilkan ${fmt(AUD.rows.length)}` : ""}</p>
    ${tbl(["Waktu (WIB)", "Pengguna", "Aktivitas", "IP"], rows, {tall: true, empty: "Tidak ada catatan untuk filter ini."})}
    ${AUD.rows.length < AUD.total ? `<div class="toolbar"><button class="btn ghost" type="button" data-int="audmore">Tampilkan lebih banyak</button></div>` : ""}`;
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
