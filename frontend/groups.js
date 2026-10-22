/* Halaman ringkasan menu induk: Network (PRTG + WiFi) dan Cyber Security (NDR Palo Alto + XDR Trend Micro). Data tiap sumber tetap punya halaman sendiri (sub-menu). */
"use strict";
const attList = att => att.length ? `<ul class="att">${att.map(a => `<li class="${a[0]}"><span>${a[1]}</span>${go(a[2], "Lihat")}</li>`).join("")}</ul>` : `<div class="empty sm">Tidak ada yang perlu ditindaklanjuti.</div>`;
const rowLbl = t => `<div class="rowlbl">${t}</div>`;
function vNetwork() {
  const N = V.net ? netR() : null, Wf = V.wifi, hasW = !!(Wf && (Wf.total || Wf.apTotal)), grid = h => `<div class="grid">${h}</div>`;
  if (!N && !hasW) return grid(`<section class="panel c12">${empty("Belum ada data jaringan untuk filter ini.")}</section>`);
  const att = [], P = N ? N.P : null, WP = hasW ? wifiPanels(Wf) : null, bad = N ? N.rank.filter(s => s.status === NST.bad) : [];
  if (bad.length) att.push(["crit", `<b>${bad.length} link di bawah target ${pc(P.target, 1)}</b>: ${bad.slice(0, 3).map(s => esc(s.link) + " (" + pc(s.av, 2) + ")").join(", ")}${bad.length > 3 ? ", …" : ""}.`, "noc"]);
  if (N && N.nodata) att.push(["warn", `<b>${N.nodata} link data kurang</b> (cakupan pantau &lt; ${pc(P.minCov, 0)}), tidak dinilai SLA.`, "noc"]);
  if (hasW && Wf.apTotal - Wf.apOnline > 0) att.push(["warn", `<b>${Wf.apTotal - Wf.apOnline} Access Point WiFi tidak online</b> dari ${Wf.apTotal}.`, "wifi"]);
  if (hasW && Wf.weak) att.push(["warn", `<b>${Wf.weak} client WiFi dengan sinyal lemah</b> (di bawah ${Wf.weakAt} dBm).`, "wifi"]);
  if (hasW && (Wf.error || Wf.stale)) att.push(["warn", `<b>Data Ruckus ${Wf.error ? "gagal disinkron" : "belum diperbarui"}</b>, cek konektor di Admin.`, "wifi"]);
  const nk = N ? `${rowLbl("Link · PRTG")}<div class="kpis k6">${kpi("Availability", pc(N.avail, 2), "target " + pc(P.target, 1), {tip: RUMUS.av, cls: N.avail < P.target ? "warnv" : ""})}${kpi("Link Memenuhi SLA", N.ok + " dari " + (N.ok + N.bad), N.bad + " tidak, " + N.nodata + " data kurang", {tip: RUMUS.link})}${kpi("Total Downtime", fx(N.downH, 1) + " jam", N.events + " kejadian · " + N.noDown + " link tanpa down", {tip: RUMUS.down})}${kpi("Data Coverage", pc(N.cov), "jam terpantau ÷ jam periode")}${kpi("Volume", fx(N.volTB, 1) + " TB", fx(N.mbps, 0) + " Mbit/s rata-rata")}${kpi("High Peak Utilization", fmt(N.utilHigh), "link ≥ " + pc(P.utilPeak, 0) + " kapasitas", {tip: RUMUS.util})}</div>` : "";
  const nw = hasW ? `${rowLbl("WiFi · Ruckus")}<div class="kpis k6">${kpi("Client Aktif", fmt(Wf.total), "terhubung saat ini")}${kpi("Access Point", Wf.apTotal ? fmt(Wf.apOnline) + " / " + fmt(Wf.apTotal) : "-", "online", {cls: Wf.apTotal && Wf.apOnline < Wf.apTotal ? "warnv" : ""})}${kpi("Sinyal Lemah", fmt(Wf.weak), "di bawah " + Wf.weakAt + " dBm", {cls: Wf.weak ? "warnv" : ""})}${kpi("Login Portal", fmt(Wf.portalLogin), "dari " + fmt(Wf.portal.length) + " client SSID portal")}${kpi("Unduh", wBytes(Wf.tx), "sesi berjalan")}${kpi("Unggah", wBytes(Wf.rx), "sesi berjalan")}</div>` : "";
  const key = s => String(s || "").toLowerCase().replace(/^branch\s+/, "").trim(), rows = {};
  (N ? N.lokasi : []).forEach(x => { rows[key(x.k)] = {k: x.k, n: x.n, av: x.minAv, down: x.downMin, bad: x.bad}; });
  (hasW ? Wf.byLocAp : []).forEach(x => { const r = rows[key(x.k)] || (rows[key(x.k)] = {k: x.k}); Object.assign(r, {ap: x.apTotal, apOn: x.apOnline, cl: x.clients}); });
  const loc = Object.values(rows).sort((a, b) => ((b.bad || 0) - (a.bad || 0)) || (((b.ap || 0) - (b.apOn || 0)) - ((a.ap || 0) - (a.apOn || 0))) || String(a.k).localeCompare(String(b.k)));
  const st = r => (r.bad ? pill("crit", "Link bermasalah") : (r.ap || 0) - (r.apOn || 0) > 0 ? pill("warn", "AP offline") : pill("good", "Normal"));
  const locP = panel("c12", "Ringkasan per Lokasi", "link PRTG dan WiFi Ruckus digabung menurut nama lokasi", tbl(["Lokasi", "Link", "Availability terendah", "Downtime (menit)", "AP online / total", "Client WiFi", "Status"],
    loc.map(r => [r.k, r.n == null ? "-" : r.n, r.av == null ? "-" : pc(r.av, 3), r.down == null ? "-" : r.down, r.ap == null ? "-" : r.apOn + " / " + r.ap, r.cl == null ? "-" : r.cl, {h: st(r)}]), {tall: true, r: [1, 2, 3, 5], empty: "Belum ada data lokasi."}));
  return grid(panel("c12", "Perlu Perhatian", ctxTxt(APPLY.network), attList(att))) + nk + nw + grid(
    (N ? panel("c8", "Downtime Link per Hari", "Menit downtime semua link dalam filter", bars(dayB(N.daily), [{name: "Downtime (menit)", c: "--crit", v: N.daily.map(x => x.down)}], {dec: 1, unit: " mnt", label: "Downtime harian"})) : "") +
    (N ? panel("c4", "5 Link dengan Downtime Terbanyak", "Availability = Σ Up ÷ Σ (Up + Down)", tbl(["Link", "Availability", "Downtime (jam)"], N.rank.slice(0, 5).map(s => [s.link, pc(s.av, 3), fx(s.down / 3600, 1)]), {r: [1, 2], empty: "Belum ada data."})) : "") +
    (hasW ? WP.trend() + WP.apdown() : "") + locP + (hasW ? WP.ssid() + WP.usage() + WP.loc() : ""));
}
function vCyber() {
  const R = V.soc && V.soc.hasData ? socR() : null, chk = socCheck(), okD = chk.filter(x => x.s === "ok" || x.s === "dup").length, X = V.xdr, hasX = !!(X && X.configured && (X.listN || X.enabled)), grid = h => `<div class="grid">${h}</div>`;
  if (!R && !hasX) return grid(`<section class="panel c12">${empty("Belum ada data keamanan untuk filter ini. Impor RAW Panorama atau aktifkan sinkron API, dan isi konektor Trend Micro XDR.")}</section>`);
  const att = [], sv = hasX ? Object.fromEntries(X.bySev.map(x => [x.k, x.n])) : {};
  if (R && R.chAlert) att.push(["warn", `<b>NDR: ${fmt(R.chAlert)} event critical/high hanya alert</b>, tidak diblokir firewall.`, "soc"]);
  if (R && okD < chk.length) att.push(["warn", `<b>NDR: data harian belum lengkap</b> (${okD} dari ${chk.length} hari tervalidasi).`, "kelengkapan"]);
  if (hasX && X.backlogCH) att.push(["warn", `<b>XDR: ${fmt(X.backlogCH)} alert critical/high masih terbuka</b> (semua periode).`, "xdr"]);
  if (hasX && (X.error || X.stale)) att.push(["warn", `<b>Data Trend Micro ${X.error ? "gagal disinkron" : "belum diperbarui"}</b>, cek konektor di Admin.`, "xdr"]);
  const B = R ? dayB(R.daily) : [], ch = R ? [{name: "Critical", c: "--crit", v: R.daily.map(x => x.critical)}, {name: "High", c: "--serious", v: R.daily.map(x => x.high)}] : [];
  const nk = R ? `${rowLbl("NDR · Palo Alto Panorama")}<div class="kpis k6">${kpi("Total Event", fmt(R.total), "rata-rata " + fmt(R.total / (okD || 1)) + " per hari tervalidasi", {tip: RUMUS.socTot})}${kpi("Critical + High", fmt(R.ch), fmt(R.crit) + " critical")}${kpi("Critical + High Diblokir", pc(R.chBlkPct), "tindakan selain alert", {tip: RUMUS.socCH})}${kpi("Alert Only", fmt(R.chAlert), "critical/high tidak dihentikan", {cls: R.chAlert ? "warnv" : ""})}${kpi("Sumber Internal", pc(R.internalPct), "dari total event", {tip: RUMUS.socInt})}${kpi("URL Diblokir", fmt(R.urlBlk), "dari " + fmt(R.url) + " event URL")}</div>` : "";
  const nx = hasX ? `${rowLbl("XDR · Trend Micro Vision One")}<div class="kpis k6">${kpi("Alert", fmt(X.total), "pada periode")}${kpi("Masih Terbuka", fmt(X.open), "belum ditutup", {cls: X.open ? "warnv" : ""})}${kpi("Critical + High", fmt((sv.critical || 0) + (sv.high || 0)), fmt(sv.critical || 0) + " critical", {cls: sv.critical ? "warnv" : ""})}${kpi("Host Terdampak", fmt(X.nHosts), fmt(X.nAccounts) + " akun berbeda")}${kpi("Insiden", fmt(X.nIncidents), "")}${kpi("Backlog Critical/High", fmt(X.backlogCH), "terbuka saat ini, semua periode", {cls: X.backlogCH ? "warnv" : ""})}</div>` : "";
  const XP = hasX ? xdrPanels(X) : null;
  return grid(panel("c12", "Perlu Perhatian", ctxTxt(APPLY.cyber), attList(att))) + nk + nx + grid(
    (R ? panel("c6", "NDR · Critical dan High per Hari", "Event Palo Alto", legend(ch) + bars(B, ch, {stack: true, label: "Critical dan high"})) : "") +
    (hasX ? panel("c6", "XDR · Alert per Hari", "per severity", legend(["critical", "high", "medium", "low"].map(k => ({name: XSEV[k][0], c: XSEV[k][1]}))) + bars(X.daily.map(x => ({label: dmon(x.date), full: dlong(x.date)})), ["critical", "high", "medium", "low"].map(k => ({name: XSEV[k][0], c: XSEV[k][1], v: X.daily.map(x => x[k])})), {stack: true, label: "Alert XDR per hari"})) : "") +
    (R ? panel("c6", "NDR · Severity and Action", "", tbl(["Severity", "Event", "% total", "Diblokir", "Hanya alert"], R.sev.concat(R.sevTotal).map(x => [x.k, x.n, pc(x.pct), x.blk, x.alert]), {r: [2]})) : "") +
    (hasX ? XP.sev().replace("panel c4", "panel c6") : "") +
    (R ? panel("c6", "NDR · Kategori Ancaman Teratas", "", hbars(R.cat.slice(0, 8).map(x => [x.k, x.n, 0, fmt(x.n) + " · " + pc(x.pct, 0)]))) : "") +
    (hasX ? XP.models() : "") + (hasX ? XP.hosts() + XP.techniques() : ""));
}