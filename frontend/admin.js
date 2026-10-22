/* Menu Admin: pengelompokan halaman, role dan hak akses, data yang perlu dilengkapi, dan status sumber data. */
"use strict";
const ADM = [
  ["akses", "Akses", [["pengguna", "Pengguna"], ["roles", "Role"], ["apikeys", "Kunci API"]]],
  ["sumber", "Sumber Data", [["integrasi", "Integrasi"], ["pemetaan", "Pemetaan"], ["dilengkapi", "Perlu Dilengkapi"]]],
  ["operasional", "Operasional", [["personel", "Personel"], ["tim", "Tim dan Shift"], ["parameter", "Target dan Parameter"], ["rumus", "Rumus"]]],
  ["notifikasi", "Notifikasi", [["smtp", "Email"], ["webhooks", "Webhook"]]],
  ["sistem", "Sistem", [["audit", "Audit Log"], ["status", "Status Sumber"], ["menu", "Menu dan Widget"]]]
];
const admGroup = k => ADM.find(g => g[2].some(s => s[0] === k)) || ADM[0];
const COLN = {id: "ID", name: "Nama", kind: "Jenis", aliases: "Alias", active: "Aktif", sort: "Urutan", lat: "Lintang (lat)", lon: "Bujur (lon)", sys_name: "Nama di Sistem", unit: "Unit", job: "Jabatan",
  team_code: "Kode Tim", branch: "Cabang", phone: "Telepon", is_coordinator: "Koordinator", is_shared: "Dipakai Bersama", exclude_rank: "Tidak Masuk Peringkat", code: "Kode", label: "Label",
  rotation_offset: "Geser Rotasi", no: "No", start_hour: "Jam Mulai", keyword: "Kata Kunci", target: "Target", hours: "Batas (jam)", device: "Lokasi (Device PRTG)", capacity_mbps: "Kapasitas (Mbps)",
  key: "Kunci", enabled: "Aktif", filters: "Filter", note: "Catatan", why: "Alasan", parent: "Menu Induk", icon: "Ikon", badge: "Lencana", notice: "Pemberitahuan", title: "Judul", section: "Bagian",
  top_n: "Jumlah Teratas", hero: "Utama", presets: "Preset", modules: "Menu", can_write: "Boleh Menulis", is_admin: "Admin Penuh", uploads: "Jenis Unggah", admin_view: "Lihat Admin", scope: "Lingkup",
  text: "Rumus", source: "Sumber", mode: "Mode", interval_min: "Interval (menit)", config: "Konfigurasi", tip: "Keterangan", site: "Lokasi", description: "Deskripsi"};
const colLabel = n => COLN[n] || n.replace(/_/g, " ").replace(/^./, c => c.toUpperCase());

function admNav() {
  const g = admGroup(S.adm), todo = INT.todo ? INT.todo.total : 0;
  return `<div class="admnav"><div class="subtabs admgrp">${ADM.map(([k, t]) => `<button type="button" data-admgrp="${k}" aria-selected="${g[0] === k}">${t}</button>`).join("")}</div>
    <div class="subtabs">${g[2].map(([k, t]) => `<button type="button" data-adm="${k}" aria-selected="${S.adm === k}">${t}${k === "dilengkapi" && todo ? ` <span class="tag warn">${todo}</span>` : ""}</button>`).join("")}</div></div>`;
}
const admTitle = (t, d) => `<div class="admhead"><h3>${esc(t)}</h3>${d ? `<span class="sub">${esc(d)}</span>` : ""}</div>`;
const admGo = (adm, mkey) => set({adm, mkey: mkey || "", mdata: null, medit: null, msg: "", addUser: false, editUser: "", params: adm === "parameter" ? null : S.params});

/* ---------- Role dan hak akses ---------- */
const ROLE_SCOPE = [["all", "Semua lokasi"], ["ho", "Kantor pusat saja"], ["own", "Lokasi pada akun sendiri"]];
const ROLE_UPLOAD = [["soc", "Data SOC (NDR)"], ["tickets", "Tiket"], ["prtg", "PRTG"]];
const modName = m => { const x = MODS[m]; if (!x) return m; const p = x.parent ? MODS[x.parent] : null; return (p ? p.label + " › " : "") + x.label; };
function vRoles() {
  if (!INT.roles) { intLoad("roles", "master/role"); return intLoading(); }
  const rows = INT.roles.rows.slice().sort((a, b) => (a.sort || 0) - (b.sort || 0)), mods = Object.values(MODS).filter(m => m.key !== "admin");
  const e = INT.roleEdit, can = CFG.me.is_admin;
  const flag = (r, f) => r[f] ? `<span class="ok-t">Ya</span>` : `<span class="sub">–</span>`;
  const form = !e ? "" : `<form class="form formbox" data-role-form>
    <div class="fld"><label for="rK">Kunci${e.__new ? " *" : ""}</label><input id="rK" type="text" value="${esc(e.key || "")}" ${e.__new ? "" : "readonly"} placeholder="huruf kecil tanpa spasi, mis. auditor"></div>
    <div class="fld"><label for="rL">Nama Role *</label><input id="rL" type="text" value="${esc(e.label || "")}"></div>
    <div class="fld wide"><label for="rD">Keterangan (siapa yang memakai role ini)</label><input id="rD" type="text" value="${esc(e.description || "")}"></div>
    <div class="fld wide"><label>Menu yang boleh dibuka</label><div class="chkgrid"><label class="chk"><input type="checkbox" id="rAll" ${(e.modules || []).includes("*") ? "checked" : ""}> Semua menu</label>
      ${mods.map(m => `<label class="chk"><input type="checkbox" data-rmod="${esc(m.key)}" ${(e.modules || []).includes("*") || (e.modules || []).includes(m.key) ? "checked" : ""}> ${esc(modName(m.key))}</label>`).join("")}</div></div>
    <div class="fld"><label for="rS">Lingkup lokasi</label><select id="rS">${intOpt(ROLE_SCOPE, e.scope || "all")}</select></div>
    <div class="fld wide"><label>Izin</label><div class="chkgrid">
      <label class="chk"><input type="checkbox" id="rW" ${e.can_write ? "checked" : ""}> Boleh menulis (serah terima dan unggah data)</label>
      <label class="chk"><input type="checkbox" id="rA" ${e.is_admin ? "checked" : ""}> Admin penuh (kelola pengguna, pengaturan, integrasi)</label>
      <label class="chk"><input type="checkbox" id="rV" ${e.admin_view ? "checked" : ""}> Boleh membuka menu Admin, hanya baca</label></div></div>
    <div class="fld wide"><label>Jenis data yang boleh diunggah</label><div class="chkgrid">${ROLE_UPLOAD.map(([v, l]) => `<label class="chk"><input type="checkbox" data-rup="${v}" ${(e.uploads || []).includes("*") || (e.uploads || []).includes(v) ? "checked" : ""}> ${l}</label>`).join("")}</div></div>
    <div class="acts wide"><button class="btn" type="submit">Simpan</button><button class="btn ghost" type="button" data-role="x">Batal</button>${e.__new || e.key === "superadmin" ? "" : `<button class="btn ghost" type="button" data-role="del">Hapus</button>`}<span class="msg err" id="rMsg"></span></div></form>`;
  return intMsg() + admTitle("Role dan Hak Akses", "Role menentukan menu yang terlihat, hak mengubah data, dan lingkup lokasi. Tiap pengguna memiliki satu role.") + form + `<div class="toolbar">${can ? `<button class="btn" type="button" data-role="new">+ Tambah Role</button>` : ""}</div>
    <div class="rolecards">${rows.map(r => `<article class="rcard"><header><b>${esc(r.label)}</b><span class="sub">${esc(r.key)}</span>${can ? `<button class="btn ghost sm" type="button" data-role="edit" data-key="${esc(r.key)}">Ubah</button>` : ""}</header>
      <p>${esc(r.description || "Belum ada keterangan.")}</p>
      <div class="rflags"><span>Lingkup: <b>${esc((ROLE_SCOPE.find(x => x[0] === r.scope) || ["", r.scope])[1])}</b></span><span>Tulis: ${flag(r, "can_write")}</span><span>Admin: ${r.is_admin ? `<span class="ok-t">Penuh</span>` : r.admin_view ? `<b>Baca saja</b>` : `<span class="sub">–</span>`}</span></div></article>`).join("")}</div>
    <h4 class="admsub">Menu per role</h4><div class="scroll"><table class="matrix"><thead><tr><th>Role</th>${mods.map(m => `<th title="${esc(modName(m.key))}">${esc(m.label)}</th>`).join("")}</tr></thead><tbody>
      ${rows.map(r => `<tr><td><b>${esc(r.label)}</b></td>${mods.map(m => `<td class="${(r.modules || []).includes("*") || (r.modules || []).includes(m.key) ? "yes" : ""}">${(r.modules || []).includes("*") || (r.modules || []).includes(m.key) ? "✓" : ""}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}

/* ---------- Perlu dilengkapi ---------- */
function vTodo() {
  if (!INT.todo) { intLoad("todo", "todo"); return intLoading(); }
  const T = INT.todo, head = T.total ? `${fmt(T.total)} hal perlu dilengkapi` : "Semua data sudah lengkap";
  return admTitle("Perlu Dilengkapi", "Data baru dari API masuk otomatis, tetapi sebagian perlu dipetakan atau dilengkapi admin supaya ikut terhitung dengan benar.") + `<div class="todohead ${T.total ? "warn" : "good"}">${head}</div>
    <div class="todolist">${T.items.map(i => `<article class="todo"><header><b>${esc(i.title)}</b><span class="tag warn">${fmt(i.count)}</span></header><p class="sub">${esc(i.hint)}</p>
      <div class="mchips">${i.examples.map(x => `<span class="mchip">${esc(x)}</span>`).join("")}${i.count > i.examples.length ? `<span class="sub">dan ${fmt(i.count - i.examples.length)} lainnya</span>` : ""}</div>
      <button class="btn ghost sm" type="button" data-adm-go="${esc(i.go[0])}|${esc(i.go[1] || "")}">Buka</button></article>`).join("") || `<div class="empty sm">Tidak ada yang perlu dilengkapi.</div>`}</div>`;
}

/* ---------- Status sumber data ---------- */
function vSourceStatus() {
  if (!INT.status) { intLoad("status", "status"); return intLoading(); }
  const S_ = INT.status, tone = {ok: ["good", "Normal"], warn: ["warn", "Belum segar"], crit: ["crit", "Gagal"], off: ["idle", "Nonaktif"]};
  const when = s => s.schedule.length ? "Setiap hari " + s.schedule.join(" dan ") : s.mode === "api" ? "Setiap " + s.interval + " menit" : "Impor manual";
  const ago = m => m == null ? "–" : m < 1 ? "baru saja" : m < 60 ? m + " menit lalu" : m < 1440 ? Math.floor(m / 60) + " jam lalu" : Math.floor(m / 1440) + " hari lalu";
  return admTitle("Status Sumber Data", "Kondisi sinkron tiap sumber dan 30 catatan sinkron terakhir.") + tbl(["Sumber", "Jadwal", "Terakhir berhasil", "Hasil terakhir", "Status"],
    S_.sources.map(s => [s.label, when(s), ago(s.age_min), s.error ? {h: `<span class="errtx">${esc(String(s.error).slice(0, 140))}</span>`} : (s.last_msg || "–"), {h: pill(tone[s.state][0], tone[s.state][1])}]), {empty: "Belum ada sumber."})
    + `<h4 class="admsub">Catatan sinkron</h4>` + tbl(["Waktu", "Sumber", "Hasil", "Baris", "Durasi", "Keterangan"], S_.log.map(l => [l.at.replace("T", " ").slice(0, 19), l.source, {h: l.ok ? pill("good", "Berhasil") : pill("crit", "Gagal")}, l.rows, (l.ms / 1000).toFixed(1) + " dtk", l.msg]), {r: [3, 4], tall: true, empty: "Belum ada catatan."});
}

/* ---------- peristiwa ---------- */
document.addEventListener("click", async e => {
  const g = e.target.closest("[data-admgrp]");
  if (g) { const grp = ADM.find(x => x[0] === g.dataset.admgrp); if (typeof intReset === "function") intReset(); admGo(grp[2][0][0]); return; }
  const go = e.target.closest("[data-adm-go]");
  if (go) { const [a, k] = go.dataset.admGo.split("|"); if (typeof intReset === "function") intReset(); admGo(a, k); return; }
  const b = e.target.closest("[data-role]"); if (!b) return;
  const a = b.dataset.role;
  try {
    if (a === "new") { INT.roleEdit = {__new: true, modules: [], uploads: [], scope: "all", can_write: false}; INT.msg = null; render(false); }
    else if (a === "edit") { INT.roleEdit = Object.assign({}, INT.roles.rows.find(r => r.key === b.dataset.key)); INT.msg = null; render(false); }
    else if (a === "x") { INT.roleEdit = null; render(false); }
    else if (a === "del") { if (!confirm("Hapus role ini? Role yang masih dipakai pengguna tidak bisa dihapus.")) return; await api("/api/admin/master/role/" + encodeURIComponent(INT.roleEdit.key), {method: "DELETE"}); INT.roleEdit = null; INT.roles = null; await reloadConfig(); INT.msg = {ok: true, t: "Role dihapus."}; render(false); }
  } catch (er) { if (er) { $("rMsg").textContent = er.message || String(er); } }
});
document.addEventListener("change", e => {
  if (e.target.id === "rAll") document.querySelectorAll("[data-rmod]").forEach(c => { c.checked = e.target.checked; });
});
document.addEventListener("submit", async e => {
  const f = e.target.closest("[data-role-form]"); if (!f) return;
  e.preventDefault(); e.stopImmediatePropagation();
  const v = id => $(id).value.trim(), isNew = !!INT.roleEdit.__new;
  const mods = $("rAll").checked ? ["*"] : [...f.querySelectorAll("[data-rmod]:checked")].map(x => x.dataset.rmod);
  const body = {key: v("rK"), label: v("rL"), description: v("rD") || null, modules: mods, scope: v("rS"), can_write: $("rW").checked, is_admin: $("rA").checked, admin_view: $("rV").checked,
    uploads: [...f.querySelectorAll("[data-rup]:checked")].map(x => x.dataset.rup), sort: isNew ? 99 : (INT.roleEdit.sort || 0)};
  if (!/^[a-z][a-z0-9_]{1,38}$/.test(body.key)) { $("rMsg").textContent = "Kunci harus huruf kecil, angka, atau garis bawah (2 sampai 39 karakter)."; return; }
  if (!body.label) { $("rMsg").textContent = "Nama role wajib diisi."; return; }
  try { await send(isNew ? "/api/admin/master/role" : "/api/admin/master/role/" + encodeURIComponent(body.key), body, isNew ? "POST" : "PUT"); INT.roleEdit = null; INT.roles = null; await reloadConfig(); INT.msg = {ok: true, t: "Role tersimpan."}; render(false); }
  catch (er) { $("rMsg").textContent = er.message; }
}, true);
