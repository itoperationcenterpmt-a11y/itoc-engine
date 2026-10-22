/* Menu Insight: temuan analisis otomatis (lonjakan, tren menurun, kejadian berulang) dari data yang sudah tersimpan. */
"use strict";
const INS_SEV = {crit: ["crit", "Kritis"], warn: ["warn", "Peringatan"], info: ["idle", "Info"]};
const INS_M = {nilai: "Nilai", biasanya: "Biasanya", z: "Skor z", jumlah: "Jumlah", jumlah_link: "Jumlah link", downtime_terlama_menit: "Downtime terlama (menit)", periode_hari: "Periode (hari)", hari_menuju_target: "Hari menuju target",
  terlama_hari: "Tertua (hari)", alert_7_hari: "Alert 7 hari", offline: "Offline", total: "Total", sekarang: "Sekarang", kemiringan_per_hari: "Kemiringan per hari", target: "Target"};
const insMetric = m => Object.entries(m || {}).filter(([k]) => k !== "z" || true).map(([k, v]) => `<span class="mchip"><i>${esc(INS_M[k] || k.replace(/_/g, " "))}</i>${esc(typeof v === "number" ? (Number.isInteger(v) ? fmt(v) : fx(v, Math.abs(v) < 1 ? 4 : 1)) : v)}</span>`).join("");
const insTab = t => t && MODS[t] ? `<button type="button" class="btn ghost sm" data-go="${esc(t)}">Buka ${esc(MODS[t].label)}</button>` : "";
function insCard(r, o = {}) {
  const [tone, label] = INS_SEV[r.sev] || INS_SEV.info;
  return `<article class="icard ins ${tone}"><header>${pill(tone, label)}<b>${esc(r.title)}</b>${r.status === "baru" ? `<span class="tag warn">Baru</span>` : r.status === "selesai" ? `<span class="tag">Selesai</span>` : ""}</header>
    <p>${esc(r.detail)}</p>${o.compact ? "" : `<div class="mchips">${insMetric(r.metric)}</div>`}
    <span class="sub">${r.site ? esc(r.site) + " · " : ""}pertama terlihat ${esc(dtime(r.first))} · terakhir ${esc(dtime(r.last))}${r.ackBy ? " · dibaca oleh " + esc(r.ackBy) : ""}</span>
    <div class="acts">${insTab(r.tab)}${r.status === "baru" && !o.compact ? `<button type="button" class="btn ghost sm" data-ins-ack="${r.id}">Tandai dibaca</button>` : ""}</div></article>`;
}
function insightPanel(I, n = 5) {
  const rows = I.open.slice(0, n);
  return panel("c12", "Insight Terbaru", I.open.length + " temuan aktif · dihitung otomatis dari data tersimpan", rows.length ? `<ul class="att">${rows.map(r => `<li class="${r.sev === "crit" ? "crit" : r.sev === "warn" ? "warn" : ""}"><span><b>${esc(r.title)}</b> ${esc(r.detail)}</span>${go(r.tab && MODS[r.tab] ? r.tab : "insight", "Lihat")}</li>`).join("")}</ul>${I.open.length > n ? go("insight", "Semua insight") : ""}` : `<div class="empty sm">Tidak ada temuan aktif.</div>`);
}
function vInsight() {
  const I = V.insight, grid = h => `<div class="grid">${h}</div>`;
  if (!I) return grid(`<section class="panel c12">${empty()}</section>`);
  const c = I.counts, kp = `<div class="kpis k6">${kpi("Kritis", fmt(c.crit), "perlu ditangani segera", {cls: c.crit ? "warnv" : ""})}${kpi("Peringatan", fmt(c.warn), "perlu dicek", {cls: c.warn ? "warnv" : ""})}${kpi("Info", fmt(c.info), "untuk diketahui")}${kpi("Belum dibaca", fmt(I.new), "temuan baru")}${kpi("Pembaruan", I.updated ? dtime(I.updated) : "-", "analisis terakhir")}</div>`;
  const how = panel("c12", "Cara Kerja", "", `<p class="sub">Analisis berjalan otomatis tiap 30 menit pada data yang sudah tersimpan, tanpa layanan luar. Nilai terbaru dibandingkan dengan pola biasanya (median dan simpangan dari 4 sampai 8 minggu sebelumnya, pada hari yang sama bila ada pola mingguan). Temuan muncul bila selisihnya jauh di atas biasanya. Tren dihitung dari kemiringan 21 hari terakhir untuk memperkirakan kapan target terlewati. Temuan yang tidak muncul lagi otomatis berstatus selesai.</p>${CFG.me.is_admin ? `<button type="button" class="btn ghost sm" data-ins-run>Analisis sekarang</button>` : ""}`);
  const done = I.done.length ? panel("c12", "Selesai 14 Hari Terakhir", "", tbl(["Selesai", "Temuan", "Keterangan"], I.done.map(r => [dtime(r.resolved), r.title, r.detail]), {tall: true})) : "";
  return (S.msg ? `<div class="msg ok">${esc(S.msg)}</div>` : "") + kp + grid(`<section class="panel c12"><header><h2>Temuan Aktif</h2><span class="sub">urut tingkat keparahan</span></header>${I.open.length ? `<div class="icards">${I.open.map(r => insCard(r)).join("")}</div>` : `<div class="empty"><b>Tidak ada temuan aktif</b><span>Semua indikator berada dalam batas biasanya.</span></div>`}</section>` + how + done);
}
document.addEventListener("click", async e => {
  const a = e.target.closest("[data-ins-ack]"), r = e.target.closest("[data-ins-run]");
  try {
    if (a) { a.disabled = true; await send("/api/insights/" + a.dataset.insAck + "/ack", {}); refresh(); }
    else if (r) { r.disabled = true; r.textContent = "Menganalisis…"; const x = await send("/api/insights/run", {}); refresh({msg: x.msg || "Analisis selesai."}, true); }
  } catch (er) { if (er) alert(er.message); }
});
