/* Menu XDR: alert Workbench Trend Micro Vision One yang tersimpan di database dashboard. Severity dipilih lewat filter atas; periode lewat Period. */
"use strict";
const XSEV = {critical: ["Critical", "--crit"], high: ["High", "--serious"], medium: ["Medium", "--warn"], low: ["Low", "--low"]};
const xLink = u => /^https:\/\//i.test(u || "") ? `<a href="${esc(u)}" target="_blank" rel="noopener noreferrer">Buka</a>` : "-";
function xdrPanels(X) {
  const sv = Object.fromEntries(X.bySev.map(x => [x.k, x.n])), days = X.daily.map(x => ({label: dmon(x.date), full: dlong(x.date)}));
  const hb = a => hbars(a.map(x => [x.k, x.n, 0, fmt(x.n)]));
  return {
    kpi: () => `<section class="panel c4 dom"><header><h2>XDR</h2></header><div class="mini">${kpi("Alert", fmt(X.total), "pada periode")}${kpi("Masih Terbuka", fmt(X.open), "belum Closed", {cls: X.open ? "warnv" : ""})}${kpi("Critical", fmt(sv.critical || 0), "", {cls: sv.critical ? "warnv" : ""})}${kpi("Backlog C/H", fmt(X.backlogCH), "terbuka saat ini", {cls: X.backlogCH ? "warnv" : ""})}</div>${go("xdr")}</section>`,
    daily: () => panel("c8", "Alert per Hari", "per severity", legend(["critical", "high", "medium", "low"].map(k => ({name: XSEV[k][0], c: XSEV[k][1]}))) + bars(days, ["critical", "high", "medium", "low"].map(k => ({name: XSEV[k][0], c: XSEV[k][1], v: X.daily.map(x => x[k])})), {stack: true, label: "Alert XDR per hari"})),
    sev: () => panel("c4", "Severity dan Status", "", `<span class="lbl">Severity</span>` + hbars(X.bySev.map(x => [XSEV[x.k][0], x.n, 0, fmt(x.n)])) + `<span class="lbl">Status investigasi</span>` + hb(X.byStatus)),
    models: () => panel("c6", "Model Deteksi Teratas", "10 teratas", hb(X.byModel)),
    impact: () => panel("c6", "Cakupan Dampak", "jumlah entitas pada alert (bisa tumpang tindih)", `<div class="mini">${kpi("Desktop", fmt(X.impact.desktop), "")}${kpi("Server", fmt(X.impact.server), "")}${kpi("Akun", fmt(X.impact.account), "")}${kpi("Email", fmt(X.impact.email), "")}</div>`)
  };
}
function vXdr() {
  const X = V.xdr, grid = h => `<div class="grid">${h}</div>`;
  if (!X) return grid(`<section class="panel c12">${empty()}</section>`);
  if (!X.configured || !(X.listN || X.enabled)) return grid(panel("c12", "XDR", "", `<div class="empty"><b>Belum ada data XDR</b><span>${X.error ? "Sinkron terakhir gagal: " + esc(X.error) : "Isi Base URL regional dan API key Vision One di Admin → Integrations → Trend Micro XDR, aktifkan, lalu klik Sync now."}</span></div>`));
  const warns = [];
  if (X.error) warns.push(`<li class="crit"><span><b>Sinkron Trend Micro gagal:</b> ${esc(X.error)}</span></li>`);
  else if (X.stale) warns.push(`<li class="warn"><span><b>Data belum diperbarui</b> sejak ${esc(dtime(X.updated))}. Cek konektor Trend Micro XDR.</span></li>`);
  if (X.backlogCH) warns.push(`<li class="warn"><span><b>${fmt(X.backlogCH)} alert critical/high masih terbuka</b> (semua periode).</span></li>`);
  const sv = Object.fromEntries(X.bySev.map(x => [x.k, x.n]));
  const kp = `<div class="kpis k6">${kpi("Alert", fmt(X.total), "pada periode")}${kpi("Masih Terbuka", fmt(X.open), "belum Closed", {cls: X.open ? "warnv" : ""})}${kpi("Critical", fmt(sv.critical || 0), "", {cls: sv.critical ? "warnv" : ""})}${kpi("High", fmt(sv.high || 0), "")}${kpi("Skor Rata-rata", X.avgScore != null ? fx(X.avgScore, 1) : "-", "0 sampai 100")}${kpi("Backlog Critical/High", fmt(X.backlogCH), "terbuka saat ini, semua periode", {cls: X.backlogCH ? "warnv" : ""})}</div>`;
  const P = xdrPanels(X);
  const rows = X.list.map(x => [x.created ? dtime(x.created) : "-", {h: x.severity ? pill(x.severity === "critical" ? "crit" : x.severity === "high" ? "warn" : "idle", (XSEV[x.severity] || [x.severity])[0]) : "-"}, x.model || "-", x.score == null ? "-" : x.score, x.status || "-", x.provider || "-", {h: xLink(x.link)}]);
  return (warns.length ? grid(`<section class="panel c12"><ul class="att">${warns.join("")}</ul></section>`) : "") + kp + grid(
    P.daily() + P.sev() + P.models() + P.impact() +
    panel("c12", "Alert List", X.listN + " alert" + (X.listN > X.list.length ? ", menampilkan " + X.list.length : ""), `<div class="dtool"><input type="search" id="dq" class="msearch" placeholder="Cari model, status, atau provider" aria-label="Cari alert"><span class="sub">Severity dan periode diatur di bar filter atas</span></div><div id="dlist">${tbl(["Dibuat", "Severity", "Model", "Skor", "Status", "Provider", "Workbench"], rows, {tall: true, empty: "Tidak ada alert untuk filter ini."})}</div>`));
}