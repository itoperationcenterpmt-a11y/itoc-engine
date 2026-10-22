/* Menu XDR (Trend Micro Vision One): alert Workbench yang tersimpan di database dashboard. Severity dipilih lewat filter atas; periode lewat Period. */
"use strict";
const XSEV = {critical: ["Critical", "--crit"], high: ["High", "--serious"], medium: ["Medium", "--warn"], low: ["Low", "--low"]};
const XTONE = s => s === "critical" ? "crit" : s === "high" ? "warn" : "idle";
const xLink = u => /^https:\/\//i.test(u || "") ? `<a href="${esc(u)}" target="_blank" rel="noopener noreferrer">Buka</a>` : "-";
const xSev = s => s ? pill(XTONE(s), (XSEV[s] || [s])[0]) : "-";
function xdrPanels(X) {
  const sv = Object.fromEntries(X.bySev.map(x => [x.k, x.n])), days = X.daily.map(x => ({label: dmon(x.date), full: dlong(x.date)})), SV = ["critical", "high", "medium", "low"];
  const hb = a => hbars(a.map(x => [x.k, x.n, 0, fmt(x.n)]));
  const ent = (rows, nm) => tbl([nm, "IP", "Alert", "Terbuka", "Tertinggi", "Terakhir"], rows.map(x => [x.k, (x.ips || []).join(", ") || "-", x.n, x.open, {h: xSev(x.sev)}, x.last ? dtime(x.last) : "-"]), {r: [2, 3], empty: "Belum ada entitas terdampak pada periode ini."});
  return {
    kpi: () => `<section class="panel c4 dom"><header><h2>XDR</h2></header><div class="mini">${kpi("Alert", fmt(X.total), "pada periode")}${kpi("Masih Terbuka", fmt(X.open), "belum ditutup", {cls: X.open ? "warnv" : ""})}${kpi("Host Terdampak", fmt(X.nHosts), fmt(X.nIncidents) + " insiden")}${kpi("Backlog C/H", fmt(X.backlogCH), "terbuka saat ini", {cls: X.backlogCH ? "warnv" : ""})}</div>${go("xdr")}</section>`,
    daily: () => panel("c8", "Alert per Hari", "per severity", legend(SV.map(k => ({name: XSEV[k][0], c: XSEV[k][1]}))) + bars(days, SV.map(k => ({name: XSEV[k][0], c: XSEV[k][1], v: X.daily.map(x => x[k])})), {stack: true, label: "Alert XDR per hari"})),
    sev: () => panel("c4", "Severity dan Status", "", `<span class="lbl">Severity</span>` + hbars(X.bySev.map(x => [XSEV[x.k][0], x.n, 0, fmt(x.n)])) + `<span class="lbl">Status investigasi</span>` + hb(X.byStatus)),
    models: () => panel("c6", "Model Deteksi Teratas", "10 teratas", hb(X.byModel)),
    impact: () => panel("c6", "Cakupan Dampak", "jumlah entitas pada alert (bisa tumpang tindih)", `<div class="mini">${kpi("Desktop", fmt(X.impact.desktop), "")}${kpi("Server", fmt(X.impact.server), "")}${kpi("Akun", fmt(X.impact.account), "")}${kpi("Email", fmt(X.impact.email), "")}</div><span class="lbl">Hasil investigasi</span>` + hb(X.byResult)),
    hosts: () => panel("c6", "Host Terdampak", fmt(X.nHosts) + " host berbeda · urut severity tertinggi", ent(X.hosts, "Host")),
    accounts: () => panel("c6", "Akun Terdampak", fmt(X.nAccounts) + " akun berbeda", ent(X.accounts, "Akun")),
    techniques: () => panel("c6", "Teknik MITRE ATT&CK", "dari aturan deteksi yang cocok", tbl(["ID", "Teknik", "Alert"], X.techniques.map(t => [t.id, t.name || "-", t.n]), {r: [2], empty: "Belum ada teknik MITRE pada alert periode ini."})),
    incidents: () => panel("c8", "Insiden", fmt(X.nIncidents) + " insiden · urut severity tertinggi", tbl(["Insiden", "Alert", "Terbuka", "Severity", "Model", "Rentang"], X.incidents.map(x => [x.id, x.n, x.open, {h: xSev(x.sev)}, x.models.join("; "), dtime(x.first) + (x.last !== x.first ? " – " + dtime(x.last) : "")]), {r: [1, 2], empty: "Belum ada insiden."})),
    aging: () => panel("c4", "Umur Backlog", fmt(X.backlog) + " alert masih terbuka (semua periode)", hb(X.aging))
  };
}
function vXdr() {
  const X = V.xdr, grid = h => `<div class="grid">${h}</div>`;
  if (!X) return grid(`<section class="panel c12">${empty()}</section>`);
  if (!X.configured || !(X.listN || X.enabled)) return grid(panel("c12", "XDR", "", `<div class="empty"><b>Belum ada data XDR</b><span>${X.error ? "Sinkron terakhir gagal: " + esc(X.error) : "Isi Base URL regional dan API key Vision One di Admin → Sumber Data → Integrasi → Trend Micro XDR, aktifkan, lalu klik Sinkron sekarang."}</span></div>`));
  const warns = [];
  if (X.error) warns.push(`<li class="crit"><span><b>Sinkron Trend Micro gagal:</b> ${esc(X.error)}</span></li>`);
  else if (X.stale) warns.push(`<li class="warn"><span><b>Data belum diperbarui</b> sejak ${esc(dtime(X.updated))}. Cek konektor Trend Micro XDR.</span></li>`);
  if (X.backlogCH) warns.push(`<li class="warn"><span><b>${fmt(X.backlogCH)} alert critical/high masih terbuka</b> (semua periode).</span></li>`);
  const sv = Object.fromEntries(X.bySev.map(x => [x.k, x.n]));
  const kp = `<div class="kpis k6">${kpi("Alert", fmt(X.total), "pada periode")}${kpi("Masih Terbuka", fmt(X.open), "belum ditutup", {cls: X.open ? "warnv" : ""})}${kpi("Critical + High", fmt((sv.critical || 0) + (sv.high || 0)), fmt(sv.critical || 0) + " critical", {cls: sv.critical ? "warnv" : ""})}${kpi("Skor Rata-rata", X.avgScore != null ? fx(X.avgScore, 1) : "-", "0 sampai 100")}${kpi("Host Terdampak", fmt(X.nHosts), fmt(X.nAccounts) + " akun berbeda")}${kpi("Insiden", fmt(X.nIncidents), "alert terkait insiden yang sama digabung")}</div>`;
  const P = xdrPanels(X);
  const rows = X.list.map(x => [x.created ? dtime(x.created) : "-", {h: xSev(x.severity)}, {h: `<b>${esc(x.model || "-")}</b>${x.description ? `<span class="sub">${esc(x.description)}</span>` : ""}`}, (x.entities || []).map(e => e.n).filter(Boolean).join(", ") || "-", (x.techniques || []).join(", ") || "-", x.score == null ? "-" : x.score, x.result || "-", x.status || "-", x.incident || "-", {h: xLink(x.link)}]);
  return (warns.length ? grid(`<section class="panel c12"><ul class="att">${warns.join("")}</ul></section>`) : "") + kp + grid(
    P.daily() + P.sev() + P.hosts() + P.accounts() + P.techniques() + P.models() + P.incidents() + P.aging() + P.impact() +
    panel("c12", "Daftar Alert", X.listN + " alert" + (X.listN > X.list.length ? ", menampilkan " + X.list.length : ""), `<div class="dtool"><input type="search" id="dq" class="msearch" placeholder="Cari model, host, akun, teknik, atau insiden" aria-label="Cari alert"><span class="sub">Severity dan periode diatur di bar filter atas</span></div><div id="dlist">${tbl(["Dibuat", "Severity", "Alert", "Entitas", "MITRE", "Skor", "Hasil", "Status", "Insiden", "Workbench"], rows, {tall: true, empty: "Tidak ada alert untuk filter ini."})}</div>`));
}