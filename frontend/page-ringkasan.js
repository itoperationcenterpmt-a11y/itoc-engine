function vRingkasan() {
  const hasT = "tk" in V, hasN = "net" in V, hasS = "soc" in V, hasH = "ho_open" in V, D = V.dev, hasD = !!(D && D.all && D.all.total), Wf = V.wifi, hasW = !!(Wf && (Wf.total || Wf.apTotal)), Xd = V.xdr, hasX = !!(Xd && Xd.configured && (Xd.total || Xd.backlogCH)), Cc = V.cctv, hasC = !!(Cc && Cc.configured && Cc.total), In = V.insight, hasI = !!(In && In.open.length), Iu = V.inet, hasU = !!(Iu && Iu.nFw && Iu.total.bytes), Ku = V.kuma, hasK = !!(Ku && Ku.configured && Ku.total);
  const T = hasT ? tkR() : null, N = hasN ? netR() : null, R = hasS ? socR() : null, chk = hasS ? socCheck() : [], okDays = chk.filter(x => x.s === "ok" || x.s === "dup").length, now = nowShift();
  const P = S.cmp ? prevRange() : null, Tp = P && tkR(P), Np = P && netR(P), Rp = P && socR(P);
  const openOld = V.open_old || [], oldD = CFG.params["sd.open_alert_days"], badLinks = N ? N.rank.filter(s => s.status === NST.bad) : [], hoOpen = V.ho_open || [], hiCrit = hoOpen.filter(h => prTone(h.prio) === "crit").length;
  const wg = k => { const w = widgetFind(k); return w && widgetOk(w) ? w.html() : ""; };
  const xCrit = hasX ? (Xd.bySev.find(x => x.k === "critical") || {n: 0}).n : 0, apOff = hasW ? Wf.apTotal - Wf.apOnline : 0;

  /* Needs Attention: things to act on, critical first. Data problems are listed apart so they do not bury real incidents. */
  const att = [], dq = [];
  if (openOld.length) att.push(["crit", `<b>${pl(openOld.length, "ticket")} open for more than ${oldD} days</b>, oldest: ${esc(openOld[0].subject)} (#${esc(openOld[0].id)}, ${fx(openOld[0].age, 0)} days).`, "servicedesk"]);
  if (badLinks.length) att.push(["crit", `<b>${badLinks.length} links below the ${pc(PAR.target, 1)} target</b>: ${badLinks.slice(0, 3).map(s => esc(s.link) + " (" + pc(s.av, 2) + ")").join(", ")}${badLinks.length > 3 ? ", …" : ""}.`, "noc"]);
  if (hiCrit) att.push(["crit", `<b>${hiCrit} high-priority handovers</b> are still open.`, "serahterima"]);
  if (R && R.chAlert) att.push(["warn", `<b>${fmt(R.chAlert)} critical/high events were alert-only</b>, not blocked by the firewall.`, "soc"]);
  if (hasD && D.all.down) att.push(["warn", `<b>${fmt(D.all.down)} devices down</b> (CCTV and Gate System), ${fmt(D.chronic)} of them for more than 30 days.`, "devices"]);
  if (hasX && Xd.backlogCH) att.push(["warn", `<b>${Xd.backlogCH} critical/high XDR alerts</b> are still open.`, "xdr"]);
  if (hasK && Ku.down) att.push(["warn", `<b>${pl(Ku.down, "monitor")} down in Link / Web Availability</b>: ${Ku.mons.filter(m => m.status === 0).slice(0, 3).map(m => esc(m.name)).join(", ")}${Ku.down > 3 ? ", …" : ""}.`, "kuma"]);
  if (apOff > 0) att.push(["warn", `<b>${apOff} of ${Wf.apTotal} WiFi Access Points</b> are offline.`, "wifi"]);
  if (N && N.nodata) dq.push(["dq", `<b>${pl(N.nodata, "link")} with insufficient data</b> (monitoring coverage below ${pc(PAR.minCov, 0)}), not assessed against SLA.`, "noc"]);
  if (R && R.unknown && Object.keys(R.unknown).length) dq.push(["dq", `<b>Cyber Security: new values outside the parameter list</b> (${Object.entries(R.unknown).map(([k, r]) => ({type: "type", action: "action", severity: "severity"}[k]) + ": " + r.map(x => esc(x[0])).join(", ")).join("; ")})`, "soc"]);
  if (N && (N.unmappedIsp || []).length) dq.push(["dq", `<b>${N.unmappedIsp.length} links do not match any ISP</b>: ${N.unmappedIsp.slice(0, 3).map(esc).join(", ")}`, "noc"]);
  if (hasD && (D.error || D.stale)) dq.push(["dq", `<b>Zabbix data ${D.error ? "failed to sync" : "is not up to date"}</b>. Check the connector in Admin.`, "devices"]);
  const bad = chk.filter(x => x.s === "bad" || x.s === "miss"); if (bad.length) dq.push(["dq", `<b>SOC data is incomplete</b>: ${bad.length} of ${chk.length} days unreadable or not uploaded.`, "kelengkapan"]);
  const attBody = (att.length ? `<ul class="att">${att.map(attRow).join("")}</ul>` : `<div class="empty sm">Nothing needs follow-up.</div>`) + (dq.length ? (isExec() ? `<p class="sub dqnote">Some figures are still being validated by IT Operation.</p>` : `<div class="dhead">Data health</div><ul class="att dq">${dq.map(attRow).join("")}</ul>`) : "");
  const attP = panel("c8", "Needs Attention", ctxTxt(), attBody);

  /* Right now (live state) and This period (follows the date filter) */
  const nowTiles = [
    hasD ? stile("devices", "Devices", D.all.down ? "warn" : "good", D.all.down ? fmt(D.all.down) + " devices down" : "All online", "Availability " + (D.all.avail != null ? pc(D.all.avail, 1) : "-") + " · " + fmt(D.all.total) + " devices", {tip: D.chronic ? fmt(D.chronic) + " down for more than 30 days" : ""}) : "",
    hasW ? stile("wifi", "WiFi", apOff ? "warn" : "good", Wf.apTotal ? (apOff ? apOff + " APs offline" : "All APs online") : "No AP data", fmt(Wf.total) + " clients connected" + (Wf.weak ? " · " + fmt(Wf.weak) + " weak signal" : ""), {tip: Wf.apTotal ? fmt(Wf.apOnline) + " of " + fmt(Wf.apTotal) + " access points online" : ""}) : "",
    hasK ? stile("kuma", "Link / Web Availability", Ku.down ? "warn" : "good", Ku.down ? pl(Ku.down, "monitor") + " down" : "All monitors up", fmt(Ku.up) + " of " + fmt(Ku.total) + " up · availability " + (Ku.avail != null ? pc(Ku.avail, 2) : "–")) : "",
    hasC ? stile("cctv", "Milestone", Cc.srv.failed.length ? "warn" : "good", Cc.srv.ok + " of " + Cc.srv.total + " servers syncing", fmt(Cc.zbx.up + Cc.zbx.other) + " cameras online" + (Cc.zbx.down ? " · " + fmt(Cc.zbx.down) + " offline" : "") + " · " + fmt(Cc.total) + " cameras") : "",
    hasH ? stile("serahterima", "Handover", hiCrit ? "crit" : hoOpen.length ? "warn" : "good", hoOpen.length ? hoOpen.length + " open handovers" : "None open", hiCrit ? hiCrit + " high priority" : "all under control") : ""
  ].filter(Boolean);
  const periodTiles = [
    hasT ? stile("servicedesk", "Ticketing", openOld.length ? "crit" : "good", openOld.length ? pl(openOld.length, "old open ticket") : "Under control", fmt(T.n) + " tickets · " + fmt(T.open) + " open · SLA " + pc(T.slaPct), {dl: Tp ? delta(T.slaPct, Tp.slaPct, {up: true, pct: 1}) : "", spark: spark(T.daily.map(x => x.in), "--s1"), tip: "Closed " + pc(T.doneRate) + " · median " + fx(T.medMin, 0) + " min · P90 " + fx(T.p90, 1) + " h"}) : "",
    hasN ? stile("network", "Network", badLinks.length ? "crit" : N && N.nodata ? "warn" : "good", badLinks.length ? pl(badLinks.length, "link") + " below target" : "Stable", N ? "Availability " + pc(N.avail, 2) + " · " + fx(N.downH, 1) + " h downtime" : "", {dl: N && Np ? delta(N.avail, Np.avail, {up: true, pct: 1}) : "", spark: N ? spark(N.daily.map(x => x.down), "--crit") : "", tip: N ? N.ok + " of " + (N.ok + N.bad) + " links meet SLA · " + N.events + " incidents · " + fmt(N.utilHigh) + " links with high utilization" : ""}) : "",
    hasU ? stile("internet", "Internet Usage", "good", fwB(Iu.total.bytes) + " in the period", (Iu.dayN ? fx(Iu.total.bytes * 8 / (Iu.dayN * 86400) / 1e6, 0) + " Mb/s average" : "") + (Iu.app[0] ? " · top: " + Iu.app[0].k : "")) : "",
    hasS || hasX ? stile("cyber", "Cyber Security", xCrit ? "crit" : (R && R.chAlert) || (hasX && Xd.backlogCH) ? "warn" : "good", xCrit ? xCrit + " critical XDR alerts" : (R && R.chAlert) || (hasX && Xd.backlogCH) ? "Needs follow-up" : "No issues", (R ? fmt(R.total) + " NDR events" : "") + (R && hasX ? " · " : "") + (hasX ? fmt(Xd.total) + " XDR alerts" : ""), {dl: R && R.ch && Rp && Rp.ch ? "Blocked " + pc(R.chBlkPct) + " " + delta(R.chBlkPct, Rp.chBlkPct, {up: true, pct: 1}) : "", spark: R ? spark(R.daily.map(x => x.critical + x.high), "--serious") : "", tip: R ? "Critical/high blocked " + (R.ch ? pc(R.chBlkPct) : "–") + " · " + fmt(R.chAlert) + " alert-only · " + okDays + "/" + chk.length + " days validated" : ""}) : ""
  ].filter(Boolean);
  const nowP = nowTiles.length ? panel("c12", "Right Now", "Live status", `<div class="stiles">${nowTiles.join("")}</div>`) : "";
  const perP = periodTiles.length ? panel("c12", "This Period", ctxTxt(), `<div class="stiles">${periodTiles.join("")}</div>`) : "";
  const dutyP = panel("c4", "On Duty", dlong(now.date) + " · " + shiftHours(now.shift), onDuty(now));

  /* Contacts change rarely, so they sit folded at the bottom */
  const cg = GROUPS.find(g => g.kind === "office"), care = cg ? CFG.people.filter(p => p.unit === cg.unit) : [], ct = CFG.params["report.contact"] || {};
  const careB = cg ? `<div class="carenum">${ct.phone ? `<span class="lbl">${esc(cg.label)} hotline</span><b class="num">${esc(ct.phone)}</b>` : ""}${ct.email ? `<span class="sub">${esc(ct.email)}</span>` : ""}</div>${care.length ? `<ul class="plist">${care.map(p => `<li><span>${esc(p.name)}<span class="sub"> · ${esc(p.job || "")}</span></span><span class="num sub">${esc(p.phone || "")}</span></li>`).join("")}</ul>` : ""}` : "";
  const lead = CFG.people.filter(p => p.unit === "ITOC" && !p.team_code), leadB = lead.length ? `<ul class="plist">${lead.map(p => `<li><span>${esc(p.name)}<span class="sub"> · ${esc((p.job || "").replace(/^ITOC /, ""))}</span></span><span class="num sub">${esc(p.phone || "")}</span></li>`).join("")}</ul>` : "";
  const contactP = leadB || careB ? panel("c6", "Contacts", "Escalation and hotline", (leadB ? fold("Escalation · Supervisor &amp; Lead", leadB) : "") + (careB ? fold(esc(cg.label) + " · " + esc(cg.start + "–" + cg.end), careB) : "")) : "";

  /* Insights that say the same as a line in Needs Attention are left out of the Overview (the finding is still on the Insights page) */
  const dupKeys = [hasX && Xd.backlogCH ? "xdr_backlog" : "", hasD && D.all.down && D.chronic ? "dev_chronic" : ""].filter(Boolean), dupInsight = r => dupKeys.some(k => (r.key || "").startsWith(k));
  const s1 = hasT ? [{name: "Tickets In", c: "--s1", v: T.daily.map(x => x.in)}, {name: "Tickets Closed", c: "--s2", v: T.daily.map(x => x.done)}] : [];
  return `<div class="grid">
  ${attP}
  ${dutyP}
  ${nowP}
  ${hasI ? insightPanel(In, 3, "c12", null, "", dupInsight) : ""}
  ${perP}
  ${!hasT ? "" : panel("c8", "Tickets In and Closed per Day", ctxTxt(), legend(s1) + bars(dayB(T.daily), s1, {label: "Tickets per day"}))}
  ${N ? panel("c4", "Top 5 Links by Downtime", "", tbl(["Link", "Availability", "Hours"], N.rank.slice(0, 5).map(s => [s.link, pc(s.av, 2), fx(s.down / 3600, 1)]), {r: [1, 2], empty: "No data yet."})) : ""}
  ${N ? panel("c8", "Link Downtime per Day", "Minutes per day", bars(dayB(N.daily), [{name: "Downtime (min)", c: "--crit", v: N.daily.map(x => x.down)}], {dec: 1, unit: " min", label: "Daily downtime"})) : ""}
  ${hasW ? wifiPanels(Wf).apdown() + wifiPanels(Wf).trend() : ""}
  ${R && R.hasData ? panel("c8", "NDR · Critical and High per Day", "Palo Alto events", legend([{name: "Critical", c: "--crit"}, {name: "High", c: "--serious"}]) + bars(dayB(R.daily), [{name: "Critical", c: "--crit", v: R.daily.map(x => x.critical)}, {name: "High", c: "--serious", v: R.daily.map(x => x.high)}], {stack: true, label: "Critical and high"})) : ""}
  ${R && R.hasData ? panel("c4", "NDR · Severity", "", tbl(["Severity", "Events", "Blocked"], R.sev.map(x => [x.k, x.n, pc(x.blkPct, 0)]), {r: [1, 2]})) : ""}
  ${hasX ? xdrPanels(Xd).daily() + xdrPanels(Xd).sev() : ""}
  ${!hasH ? "" : panel("c6", "Open Handovers", hoOpen.length + " items", hoList(hoOpen.slice(0, 3), true) + go("serahterima", "All handovers"))}
  ${contactP}
  ${wg("dev-map:NETWORK-SDWAN")}
</div>`;
}

