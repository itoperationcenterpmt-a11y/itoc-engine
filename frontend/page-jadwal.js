function vJadwal() {
  /* Personnel menu (no filters). Sub-menu = parameter "personel" (Admin → Operations → Targets & Parameters): each group has kind shift | office | branch. */
  const now = nowShift(), gs = GROUPS, G = gs.find(g => g.key === S.pers) || gs[0];
  if (!G) return `<div class="grid"><section class="panel c12">${empty("No personnel groups yet. Set the personnel parameter in Admin.")}</section></div>`;
  const bar = `<div class="subtabs">${gs.map(g => `<button type="button" data-pers="${esc(g.key)}" aria-selected="${g.key === G.key}">${esc(g.label)}</button>`).join("")}</div>`;
  const group = CFG.people.filter(p => p.unit === G.unit), person = p => `<li><span>${esc(p.name)}<span class="sub"> · ${esc((p.job || "").replace(/^ITOC /, ""))}</span></span><span class="num sub">${esc(p.phone || "")}</span></li>`;
  let body = "";
  if (G.kind === "shift") {
    const ym = S.schedM || now.today.slice(0, 7), first = ym + "-01", mEnd = iso(Date.UTC(+ym.slice(0, 4), +ym.slice(5, 7), 0)), days = [];
    for (let d = first; d <= mEnd; d = addDays(d, 1)) days.push(d);
    const head = `<div class="h"></div>` + days.map(d => `<div class="h ${d === now.date ? "today" : ""}">${new Date(dayMs(d)).getUTCDate()}<br>${HR[new Date(dayMs(d)).getUTCDay()]}</div>`).join("");
    const rows = TEAMS.map(g => `<div class="tn">Team ${g}</div>` + days.map(d => { const c = codeOf(g, d), k = CODES[c]; return `<div class="c ${k} ${d === now.date && c === now.shift - 1 ? "today" : ""}" data-tip="${esc("Team " + g + " · " + dlong(d) + "\n" + (k === OFFC ? "Off" : "Shift " + SN[c + 1] + " " + shiftHours(c + 1)))}">${k}</div>`; }).join("")).join("");
    body = `<div class="grid">${panel("c12", "Lead & Supervisor", "", `<div class="pcards">${group.filter(p => !p.team_code).map(pcard).join("") || `<div class="sub">No data yet.</div>`}</div>`)}
    ${panel("c4", "On Duty", dlong(now.date) + " · " + now.clock + " WIB", onDuty(now))}
    ${panel("c8", "Shift Schedule " + esc(G.label), "", `<div class="scroll"><div class="sched" style="grid-template-columns:72px repeat(${days.length},minmax(30px,1fr))">${head}${rows}</div></div>
      <div class="legend">${[...CFG.shifts.map(x => [x.code, x.name + " " + shiftHours(x.no)]), [OFFC, "Off"]].map(([k, l]) => `<span><b class="sw ${k}"></b>${l}</span>`).join("")}</div>`, `<span class="acts monthnav"><button type="button" class="btn ghost sm" data-sm="-1" aria-label="Previous month">‹</button><b class="num">${rangeMonth(first)}</b><button type="button" class="btn ghost sm" data-sm="1" aria-label="Next month">›</button>${ym !== now.today.slice(0, 7) ? `<button type="button" class="btn ghost sm" data-sm="0">Today</button>` : ""}</span>`)}
    ${TEAMS.map(g => { const c = codeOf(g, now.date); return panel("c3 shcard " + (c === OFF ? "sh-off" : "sh" + c), "Team " + g, c === OFF ? `<span class="shb"><i></i>${backOn(g, now)}</span>` : `<span class="shb"><i></i>${esc(SN[c + 1])}</span>`, `<ul class="plist">${crew(g).map(person).join("")}</ul>`); }).join("")}
    </div>`;
  } else if (G.kind === "office") {
    const dow = new Date(dayMs(now.today)).getUTCDay(), open = (G.days || []).includes(dow) && now.clock >= G.start && now.clock < G.end;
    body = `<div class="grid">${panel("c12", esc(G.label), "",
      `<div class="hchips">${(CFG.params["report.contact"] || {}).phone ? `<a class="hchip link" href="${esc(telHref(CFG.params["report.contact"].phone))}"><i></i>${esc(CFG.params["report.contact"].phone)}</a>` : ""}${(CFG.params["report.contact"] || {}).email ? `<a class="hchip link" href="mailto:${esc(CFG.params["report.contact"].email)}"><i></i>${esc(CFG.params["report.contact"].email)}</a>` : ""}</div>` +
      (group.length ? `<div class="pcards">${group.map(pcard).join("")}</div>` : `<div class="empty sm">No members yet.</div>`))}</div>`;
  } else {
    const by = new Map(); group.forEach(p => { const k = p.branch || "Shared"; if (!by.has(k)) by.set(k, []); by.get(k).push(p); });
    const ord = k => { const i = CFG.sites.indexOf(k); return i < 0 ? 999 : i; }, ob = V.open_by_site || {}, totOpen = [...by.keys()].reduce((a, k) => a + (ob[k] || 0), 0);
    const cards = [...by.entries()].sort((a, b) => ord(a[0]) - ord(b[0])).map(([k, ps]) => { const o = ob[k] || 0, tone = o === 0 ? "good" : o < 5 ? "warn" : "crit";
      return `<article class="bcard pcard" data-q="${esc((k + " " + ps.map(p => p.name).join(" ")).toLowerCase())}"><header><b>${esc(k.replace(/^Branch /, ""))}</b><span class="obadge ${tone}" title="Open tickets at this branch">${o} open</span></header>${ps.map(p => `<div class="brow">${pav(p.name, 1)}<span class="pb"><b>${esc(p.name)}</b></span>${p.phone ? `<a class="pph" href="${esc(telHref(p.phone))}">${esc(p.phone)}</a>` : ""}</div>`).join("")}</article>`; }).join("");
    body = `<div class="grid">${panel("c12", esc(G.label), `<span class="hchips"><span class="hchip"><i></i>${by.size} locations</span><span class="hchip"><i></i>${group.length} people</span><span class="hchip ${totOpen ? "warn" : ""}"><i></i>${totOpen} open tickets</span></span>`, `<input type="search" id="mq" class="msearch" placeholder="Search name or location" aria-label="Search"><div class="bcards">${cards || `<div class="empty sm">No members yet.</div>`}</div>`)}</div>`;
  }
  if (G.kind === "shift" && TABS.some(t => t[0] === "serahterima")) body += vHoBody(true);
  return bar + body;
}const rangeMonth = d => MB[+d.slice(5, 7) - 1] + " " + d.slice(0, 4);
/* ---------- Handover ---------- */
