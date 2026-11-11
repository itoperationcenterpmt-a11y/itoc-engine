const RGROUPS = [
  ["overview", "Overview", "dashboard", ["summary", "full", "custom"]],
  ["ticketing", "Ticketing", "ticket", ["servicedesk", "performance"]],
  ["network", "Network", "network", ["network", "noc", "wifi", "internet", "kuma"]],
  ["cyber", "Cyber Security", "shield", ["cyber", "soc", "xdr"]],
  ["devices", "Devices", "server", ["devices", "cctv"]]
];
const RSHORT = {summary: "Summary", full: "Full Report", custom: "Custom…", servicedesk: "Ticketing", performance: "Performance", network: "All Network", noc: "Links (PRTG)", wifi: "WiFi (Ruckus)", internet: "Internet Usage", kuma: "Web Availability", cyber: "All Cyber", soc: "NDR (Palo Alto)", xdr: "XDR (Trend Micro)", devices: "Devices (Zabbix)", cctv: "CCTV (Milestone)"};
function vReport() {
  const rp = V.report || {sections: [], kinds: []}, kinds = rp.kinds || [];
  if (!kinds.length) return `<div class="grid"><section class="panel c12">${empty("No reports are available to this role.")}</section></div>`;
  if (S.rkind !== "custom" && !kinds.some(k => k.key === S.rkind)) S.rkind = kinds[0].key;
  const kind = S.rkind, avail = rp.avail || [], picked = (S.rsecs || []).filter(x => avail.some(a => a.key === x)), kd = kind === "custom" ? {label: "Custom Report", desc: "", sections: picked} : kinds.find(k => k.key === kind) || {}, secs = kd.sections || [kind], shown = rp.sections.filter(s => kind === "custom" ? picked.includes(s.key) : kind === "full" ? s.key !== "performance" : (kind === "summary" ? s.key === "ringkasan" : secs.includes(s.key) || (s.key === "ringkasan" && secs.length > 1)));
  const byKey = Object.fromEntries(kinds.map(k => [k.key, k]));
  if (avail.length > 1) byKey.custom = {key: "custom", label: "Custom…", desc: "Pick any combination of sections"};
  const known = new Set(RGROUPS.flatMap(g => g[3])), extra = kinds.map(k => k.key).filter(k => !known.has(k));
  const groups = RGROUPS.map(([gk, gl, ico, ks]) => [gk, gl, ico, (gk === "overview" ? [...ks.slice(0, 2), ...extra, "custom"] : ks).map(k => byKey[k]).filter(Boolean)]).filter(g => g[3].length);
  const curGrp = groups.find(g => g[3].some(k => k.key === kind)) || groups[0];
  const catTabs = `<div class="rcats" role="tablist" aria-label="Report category">${groups.map(([gk, gl, ico, list]) => `<button type="button" class="rcat" data-rkind="${esc(list[0].key)}" aria-selected="${curGrp[0] === gk}"><svg viewBox="0 0 24 24" aria-hidden="true">${ICO[ico]}</svg><span>${esc(gl)}</span></button>`).join("")}</div>`;
  const subTabs = curGrp[3].length > 1 ? `<div class="seg rsubs" role="tablist" aria-label="${esc(curGrp[1])} report">${curGrp[3].map(k => `<button type="button" data-rkind="${esc(k.key)}" aria-pressed="${k.key === kind}" title="${esc(k.desc || k.label)}">${esc(RSHORT[k.key] || k.label)}</button>`).join("")}</div>` : "";
  const chips = `<div class="rnav">${catTabs}${subTabs}</div>${kind === "custom" ? `<div class="rpick">${avail.map(a => `<label class="pchip"><input type="checkbox" data-rsec="${esc(a.key)}" ${picked.includes(a.key) ? "checked" : ""}>${esc(a.label)}</label>`).join("")}</div>` : ""}`;
  const pre = `<div class="rctl-g"><span class="lbl">Size</span><div class="seg">${[["ringkas", "Compact"], ["standar", "Standard"], ["lengkap", "Full"]].map(([k, l]) => `<button type="button" data-rpreset="${k}" aria-pressed="${k === S.rpreset}">${l}</button>`).join("")}</div></div>`;
  const tkOn = ["servicedesk", "performance", "full", "summary"].includes(kind) || (kind === "custom" && ["servicedesk", "performance"].some(x => picked.includes(x)));
  const tkSel = tkOn ? `<label class="rinl"><span class="lbl">Group</span><select id="rgrp" aria-label="Group"><option value="">Any group</option>${(rp.groups || []).map(g => `<option value="${esc(g)}" ${S.rgrp === g ? "selected" : ""}>${esc(g)}</option>`).join("")}</select></label><label class="rinl"><span class="lbl">Technician</span><select id="rtech" aria-label="Technician"><option value="">All technicians</option>${(rp.techs || []).map(t => `<option value="${esc(t.key)}" ${S.rtech === t.key ? "selected" : ""}>${esc(t.label)}</option>`).join("")}</select></label>` : "";
  const lkOn = ["full", "network", "noc"].includes(kind) || (kind === "custom" && picked.includes("noc"));
  const lkSel = lkOn ? `<label class="rinl"><span class="lbl">ISP</span><select id="risp" aria-label="ISP"><option value="">All ISPs</option>${(rp.isps || []).map(n => `<option value="${esc(n)}" ${S.risp === n ? "selected" : ""}>${esc(n)}</option>`).join("")}</select></label>` : "";
  const dis = kind === "custom" && !picked.length ? "disabled" : "";
  const dl = `<div class="rctl-g"><span class="lbl">Download</span><div class="rdl">${[["xlsx", "Excel"], ["pdf", "PDF"], ["pptx", "PowerPoint"]].map(([k, l]) => `<button type="button" class="btn" data-rep="${k}" ${dis}>${l}</button>`).join("")}</div></div>`;
  const share = `<div class="rshare"><span class="sub">Share 3-day link (no sign-in):</span><div class="rshare-btns">${[["xlsx", "Excel"], ["pdf", "PDF"], ["pptx", "PowerPoint"]].map(([k, l]) => `<button type="button" class="btn ghost sm" data-rshare="${k}" ${dis}>${l}</button>`).join("")}</div></div>${S.shareUrl ? `<div class="msg ok rlink"><input type="text" readonly id="shareUrl" value="${esc(S.shareUrl)}" aria-label="Report link"><button type="button" class="btn ghost sm" data-rcopy>Copy</button><span class="sub">expires ${esc(S.shareExp)}</span></div>` : ""}`;
  const kp = shown.flatMap(s => s.kpis).slice(0, 12), nc = shown.reduce((a, s) => a + s.charts.length, 0), nt = shown.reduce((a, s) => a + s.tables.length, 0);
  const list = (a, n) => a.length ? `<ul class="rlist">${a.slice(0, n).map(x => `<li>${esc(x.title)}</li>`).join("")}${a.length > n ? `<li class="sub">+${a.length - n} more</li>` : ""}</ul>` : `<span class="sub">None in this preset</span>`;
  const none = s => !s.kpis.length && !s.charts.length && !s.tables.length, why = shown.filter(none).flatMap(s => s.notes.slice(0, 1));
  const secs2 = shown.map(s => `<div class="rsec ${none(s) ? "na" : ""}"><div class="rsec-h"><h4>${esc(s.title)}</h4><span class="rbadge ${none(s) ? "warn" : "ok"}">${none(s) ? "No data" : pl(s.charts.length, "chart") + " · " + pl(s.tables.length, "table")}</span></div>${none(s) ? `<span class="sub">${esc((s.notes[0] || "Nothing to report for the selected filters.").slice(0, 220))}</span>` : `<div class="rsec-body"><div class="rsec-col"><span class="lbl">Charts</span>${list(s.charts, 5)}</div><div class="rsec-col"><span class="lbl">Tables</span>${list(s.tables, 5)}</div></div>`}</div>`).join("");
  const descTxt = kd.desc || (kind === "custom" ? (picked.length ? picked.map(k => (avail.find(a => a.key === k) || {}).label).filter(Boolean).join(" · ") : "Choose at least one section above to build a custom report.") : "");
  const badgeTxt = shown.length ? (shown.length > 1 ? pl(shown.length, "section") + " · " : "") + pl(nc, "chart") + " · " + pl(nt, "table") : "0 sections";
  const topCard = `<section class="panel c12 rpanel">${chips}<div class="rhead"><div class="rinfo"><div class="rtitle"><h3>${esc(kd.label || "Report")}</h3><span class="rbadge ${shown.length && !shown.every(none) ? "ok" : "warn"}">${badgeTxt}</span></div>${descTxt ? `<p class="sub">${esc(descTxt)}</p>` : ""}${tkSel || lkSel ? `<div class="rsel">${tkSel}${lkSel}</div>` : ""}</div><div class="racts"><div class="rctl-row">${pre}${dl}</div>${share}</div></div></section>`;
  const kpStrip = kp.length ? `<div class="kpis rkpis">${kp.map(k => { const p = String(k.label).split(" · "), src = p.length > 1 ? p[0] : "", lbl = p.slice(p.length > 1 ? 1 : 0).join(" · "), v = fk(k.value, k.kind); return `<div class="kpi">${src ? `<span class="src">${esc(src)}</span>` : ""}<span class="lbl">${esc(lbl)}</span><span class="v${k.kind === "t" && String(v).length > 12 ? " smv" : ""}">${v}</span><span class="d">${esc(k.sub || "")}</span></div>`; }).join("")}</div>` : "";
  const s0 = shown[0];
  const contentCard = !shown.length
    ? panel("c12", "Included in Report", "", `<div class="empty sm">${kind === "custom" && !picked.length ? "Pick at least one section above." : esc(why[0] || "No data for the selected filters.")}</div>`)
    : shown.length === 1
      ? (none(s0)
          ? panel("c12", esc(s0.title), "No data", `<div class="empty sm">${esc((s0.notes[0] || "Nothing to report for the selected filters.").slice(0, 220))}</div>`)
          : panel("c12", "Included in Report", pl(s0.charts.length, "chart") + " · " + pl(s0.tables.length, "table"), `<div class="rsec-split"><div class="rsec-col"><span class="lbl">Charts (${s0.charts.length})</span>${list(s0.charts, 12)}</div><div class="rsec-col"><span class="lbl">Tables (${s0.tables.length})</span>${list(s0.tables, 12)}</div></div>`))
      : panel("c12", "Included in Report", pl(shown.length, "section") + " · " + pl(nc, "chart") + " · " + pl(nt, "table"), `<div class="rsecs">${secs2}</div>`);
  return `<div class="grid">${topCard}</div>${kpStrip}<div class="grid">${contentCard}</div>`;
}
/* ---------- Admin ---------- */
