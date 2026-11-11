function vHo() { return vHoBody(); }
function vHoBody(embed) {
  const inF = h => embed || (h.date >= S.from && h.date <= S.to && (!S.sf || h.shift === S.sf) && (!S.site || h.site === S.site));       // embedded under Personnel: the page has no filters, so it shows the last 14 days and everything still open
  const L = (V.handover || []).filter(h => inF(h) && (S.hoSt === "all" || (S.hoSt === "open") === h.open)).sort((a, b) => b.at - a.at);
  const now = nowShift(), nx = now.shift % NS + 1, openT = V.open_tickets || [];
  const form = `<form id="hoF" class="form" novalidate>
    <div class="fld"><label>From</label><div class="ro">Shift ${SN[now.shift]} · Team ${teamOn(now.date, now.shift)}</div></div>
    <div class="fld"><label>To</label><div class="ro">Shift ${SN[nx]} · Team ${teamOn(now.shift === NS ? addDays(now.date, 1) : now.date, nx)}</div></div>
    <div class="fld"><label for="hCat">Category *</label><select id="hCat" required><option value="">Select…</option>${CFG.params["ho.categories"].map(x => `<option>${esc(x)}</option>`).join("")}</select></div>
    <div class="fld"><label for="hPr">Priority *</label><select id="hPr" required><option value="">Select…</option>${CFG.params["ho.priorities"].map(x => `<option>${esc(x.value)}</option>`).join("")}</select></div>
    <div class="fld"><label for="hSite">Location *</label><select id="hSite" required><option value="">Select…</option>${CFG.sites.map(s => `<option ${s === S.site ? "selected" : ""}>${esc(s)}</option>`).join("")}</select></div>
    <div class="fld"><label for="hTk">Related Ticket</label><select id="hTk"><option value="">None</option>${openT.map(t => `<option value="${esc(t.id)}">#${esc(t.id)} · ${esc(String(t.subject).slice(0, 48))}</option>`).join("")}</select></div>
    <div class="fld wide"><label for="hTitle">Title * <span class="sub">min. ${CFG.params["ho.rules"].min_title} characters</span></label><input type="text" id="hTitle" maxlength="120" placeholder="Example: Astinet link Meulaboh down, waiting for the ISP"></div>
    <div class="fld wide"><label for="hBody">Situation and actions taken * <span class="sub">min. ${CFG.params["ho.rules"].min_body} characters</span></label><textarea id="hBody" placeholder="What happened, since when, who it was escalated to"></textarea></div>
    <div class="fld wide"><label for="hNext">Follow-up for Next Shift</label><input type="text" id="hNext" placeholder="What should be checked or done"></div>
    <div class="acts wide"><button class="btn" type="submit">Save Handover</button><button class="btn ghost" type="button" data-hoform="0">Cancel</button><span class="msg err" id="hMsg"></span></div></form>`;
  return `<div class="grid">${panel("c12", "Hand Over Shift", embed ? "last 14 days and everything still open" : ctxTxt(), `<div class="toolbar"><div class="seg" id="hoSt">${[["open", "Open"], ["closed", "Closed"], ["all", "All"]].map(([k, l]) => `<button type="button" data-ho="${k}" aria-pressed="${S.hoSt === k}">${l}</button>`).join("")}</div>${S.hoForm ? "" : `<button class="btn" data-hoform="1">+ New Handover</button>`}</div>${S.msg ? `<div class="msg ok">${esc(S.msg)}</div>` : ""}${S.hoForm ? `<div class="formbox">${form}</div>` : ""}${hoList(L)}${embed ? go("serahterima", "Full history with filters") : ""}`)}</div>`;
}
