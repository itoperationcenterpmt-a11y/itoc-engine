/* Command Center UI Modules:
   1. Live Alert Bell & Notification Center
   2. Global Quick Search Modal
   3. SLA Breach Countdown (Ticketing)
   4. Major Incident War Room & Timeline
   5. Admin -> Access -> SSO / Identity
   6. Admin -> Notifications -> Scheduled Reports
*/
"use strict";

/* ==================== 1. LIVE ALERT BELL ==================== */
const ALERTS = {items: [], unread: 0, timer: null};
async function loadAlerts() {
  if (!CFG || $("app").hidden) return;
  try {
    const r = await api("/api/alerts");
    ALERTS.items = r.items || [];
    ALERTS.unread = r.unread || 0;
    const b = $("bellBadge");
    if (b) { b.textContent = ALERTS.unread > 99 ? "99+" : String(ALERTS.unread); b.hidden = !ALERTS.unread; }
    const pop = $("bellPop");
    if (pop && !pop.hidden) renderBellPop();
  } catch (_) {}
}
function renderBellPop() {
  const pop = $("bellPop"); if (!pop) return;
  const rows = ALERTS.items;
  pop.innerHTML = `<div class="pop-hd" style="display:flex;align-items:center;justify-content:space-between;gap:8px">
      <div><b>Alerts &amp; Notifications</b><small>${ALERTS.unread ? ALERTS.unread + " unread" : "All caught up"}</small></div>
      ${ALERTS.unread ? `<button type="button" class="btn ghost sm" data-ack-all style="margin:0">Ack All</button>` : ""}
    </div>
    <div class="bell-list">${rows.length ? rows.map(a => `
      <div class="bell-item ${a.sev} ${a.unread ? "unread" : ""}">
        <div class="bell-body">
          <b>${esc(a.title)}</b>
          <span class="sub">${esc(a.detail)}</span>
          <div class="bell-meta"><span>${a.site ? esc(a.site) + " · " : ""}${a.at ? dtime(a.at) : "Live"}</span>
            <span class="acts">${a.ins_id && a.unread ? `<button type="button" class="btn ghost sm" data-ack-ins="${a.ins_id}" style="margin:0">Ack</button>` : ""}<button type="button" class="btn ghost sm" data-bell-go="${esc(a.tab)}" data-bell-site="${esc(a.site || "")}" style="margin:0">View →</button></span>
          </div>
        </div>
      </div>`).join("") : `<div class="empty sm" style="padding:18px">No active alerts. Everything looks healthy.</div>`}</div>`;
}
function opsInit() {
  loadAlerts();
  if (ALERTS.timer) clearInterval(ALERTS.timer);
  ALERTS.timer = setInterval(loadAlerts, 60000);
}

/* ==================== 2. GLOBAL QUICK SEARCH ==================== */
let _SRCH_T = null;
function openSearch() {
  const dlg = $("dlgSearch"); if (!dlg) return;
  if (!dlg.open) dlg.showModal();
  const inp = $("srchQ");
  if (inp) { inp.value = ""; inp.focus(); runSearch(""); }
}
async function runSearch(q) {
  const res = $("srchRes"); if (!res) return;
  try {
    const r = await api("/api/search?q=" + encodeURIComponent(q || ""));
    const sec = (title, html) => html ? `<div class="srch-sec"><span class="lbl">${title}</span>${html}</div>` : "";
    const menus = (r.menus || []).map(m => `<button type="button" class="srch-row" data-srch-tab="${esc(m.key)}"><b>${esc(m.label)}</b><span class="sub">Menu</span></button>`).join("");
    const sites = (r.sites || []).map(s => `<button type="button" class="srch-row" data-srch-site="${esc(s.name)}"><b>${esc(s.name)}</b><span class="sub">Filter location · ${esc(s.kind)}</span></button>`).join("");
    const devs = (r.devices || []).map(d => `<button type="button" class="srch-row" data-srch-tab="${esc(d.tab)}" data-srch-site="${esc(d.site)}"><b>${esc(d.name)}</b><span class="sub">${esc(d.ip || "")}${d.site ? " · " + esc(d.site) : ""} · ${esc(d.status)}</span></button>`).join("");
    const tks = (r.tickets || []).map(t => `<button type="button" class="srch-row" data-srch-tab="servicedesk" data-srch-site="${esc(t.site)}"><b>#${esc(t.id)} · ${esc(t.subject)}</b><span class="sub">${esc(t.site)} · ${esc(t.tech)} · ${esc(t.status)}</span></button>`).join("");
    const ppl = (r.people || []).map(p => `<button type="button" class="srch-row" data-srch-tab="jadwal"><b>${esc(p.name)}</b><span class="sub">${esc(p.unit)}${p.branch ? " · " + esc(p.branch) : ""}${p.phone ? " · " + esc(p.phone) : ""}</span></button>`).join("");
    const incs = (r.incidents || []).map(i => `<button type="button" class="srch-row" data-srch-tab="incidents"><b>[${esc(i.severity.toUpperCase())}] ${esc(i.title)}</b><span class="sub">${esc(i.site || "All")} · ${esc(i.status)}</span></button>`).join("");
    const all = sec("Menus", menus) + sec("Locations", sites) + sec("Major Incidents", incs) + sec("Devices & ISP Links", devs) + sec("Tickets", tks) + sec("Personnel", ppl);
    res.innerHTML = all || `<div class="empty sm" style="padding:20px">No matches found for "${esc(q)}".</div>`;
  } catch (e) { res.innerHTML = `<div class="msg err">${esc(e.message)}</div>`; }
}

/* ==================== 3. SLA BREACH COUNTDOWN ==================== */
function fmtCountdown(min) {
  const a = Math.abs(min), h = Math.floor(a / 60), m = a % 60;
  const txt = h ? `${h}h ${m}m` : `${m}m`;
  return min <= 0 ? `Breached ${txt}` : `${txt} left`;
}
async function loadSlaRisk() {
  const el = $("slaRiskBody"); if (!el) return;
  try {
    const r = await api("/api/sla-risk?site=" + encodeURIComponent(S.site || ""));
    const badge = $("slaRiskSub");
    if (badge) badge.textContent = `${r.breached} breached · ${r.imminent} due within 2h · ${r.total} open tracked`;
    if (!r.rows.length) { el.innerHTML = `<div class="empty sm">No open tickets approaching SLA breach.</div>`; return; }
    el.innerHTML = tbl(["Ticket", "Subject", "Location", "Technician", "SLA Target", "Countdown"],
      r.rows.map(x => [
        "#" + x.id, x.subject, x.site, x.tech, x.sla_h + " h",
        {h: `<span class="pill ${x.tone}"><i>${x.tone === "crit" ? "✕" : x.tone === "warn" ? "!" : "✓"}</i>${esc(fmtCountdown(x.rem_min))}</span>`}
      ]), {pageSize: 10, tall: true});
  } catch (e) { el.innerHTML = `<div class="sub">${esc(e.message)}</div>`; }
}

/* ==================== 4. MAJOR INCIDENT WAR ROOM ==================== */
const INC = {data: null, filter: "open", showNew: false, updId: null, resolveId: null, msg: null};
async function loadIncidents() {
  try { INC.data = await api("/api/incidents?status=" + encodeURIComponent(INC.filter) + "&site=" + encodeURIComponent(S.site || "")); }
  catch (e) { INC.data = {rows: [], suggested: [], open_count: 0, err: e.message}; }
  if (S.tab === "incidents") render(false);
}
function fmtElapsed(min) {
  const d = Math.floor(min / 1440), h = Math.floor((min % 1440) / 60), m = min % 60;
  return d ? `${d}d ${h}h ${m}m` : h ? `${h}h ${m}m` : `${m}m`;
}
function vIncidents() {
  if (!INC.data) { loadIncidents(); return `<div class="grid"><section class="panel c12"><div class="empty sm">Loading Major Incident War Room…</div></section></div>`; }
  const D = INC.data, canW = CFG.me.can_write || CFG.me.is_admin;
  const sevPill = s => pill(s === "sev1" ? "crit" : s === "sev2" ? "warn" : "idle", s.toUpperCase());
  const stPillI = s => pill(s === "resolved" ? "good" : s === "monitoring" ? "warn" : "crit", s === "resolved" ? "Resolved" : s === "monitoring" ? "Monitoring" : "Active");
  const sug = (D.suggested || []).length && canW ? `<div class="inc-sug"><b>Auto-Detected Multi-System Outages</b>${D.suggested.map(x => `<div class="inc-sug-row"><span>${esc(x.title)}</span><button type="button" class="btn sm" data-inc-quick="${esc(x.site)}" data-inc-qtitle="${esc(x.title)}">Declare Incident</button></div>`).join("")}</div>` : "";
  const form = INC.showNew ? `<form id="incNewF" class="form formbox" style="margin-bottom:12px">
    <div class="fld wide"><label for="incT">Incident Title *</label><input id="incT" type="text" placeholder="e.g. Branch Bagendang total uplink & CCTV outage" required></div>
    <div class="fld"><label for="incSev">Severity</label><select id="incSev"><option value="sev1">SEV1 · Critical Outage</option><option value="sev2" selected>SEV2 · Major Degradation</option><option value="sev3">SEV3 · Localized Impact</option></select></div>
    <div class="fld"><label for="incSite">Affected Location</label><select id="incSite"><option value="">Multiple / All locations</option>${CFG.sites.map(x => `<option value="${esc(x)}">${esc(x)}</option>`).join("")}</select></div>
    <div class="fld"><label for="incCmd">Incident Commander</label><input id="incCmd" type="text" value="${esc(CFG.me.name || "")}"></div>
    <div class="fld wide"><label for="incSum">Initial Impact Summary</label><textarea id="incSum" rows="2" placeholder="Describe affected services, ISP links, devices, or operational impact…"></textarea></div>
    <div class="acts wide"><button class="btn" type="submit">Declare Major Incident</button><button class="btn ghost" type="button" data-inc-act="cancel">Cancel</button></div></form>` : "";
  const cards = (D.rows || []).map(x => `<article class="panel c12 inc-card ${x.status === "resolved" ? "res" : x.severity}">
    <header>
      <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
        ${sevPill(x.severity)} ${stPillI(x.status)}
        <h2 style="padding-left:0">#${x.id} · ${esc(x.title)}</h2>
      </div>
      <span class="sub num">Duration: <b>${fmtElapsed(x.elapsed_min)}</b> · Started ${dtime(x.started_at)}</span>
    </header>
    <div class="rflags">
      ${x.site ? `<span>Location: <b>${esc(x.site)}</b></span>` : ""}
      <span>Commander: <b>${esc(x.commander || "–")}</b></span>
      ${x.root_cause ? `<span>Root Cause: <b>${esc(x.root_cause)}</b></span>` : ""}
    </div>
    ${x.summary ? `<p style="margin:0;color:var(--ink2)">${esc(x.summary)}</p>` : ""}
    <div class="inc-tl">${(x.updates || []).map(u => `<div class="inc-tli">
      <span class="tag ${u.kind === "escalation" ? "warn" : ""}">${esc(u.kind)}</span>
      <span class="num sub">${dtime(u.at)}</span>
      <b>${esc(u.author)}</b>
      <span>${esc(u.message)}</span>
    </div>`).join("")}</div>
    ${canW && x.status !== "resolved" ? `
      <div class="acts">
        <button type="button" class="btn ghost sm" data-inc-upd="${x.id}">+ Post Timeline Update</button>
        ${x.status === "open" ? `<button type="button" class="btn ghost sm" data-inc-mon="${x.id}">Set Monitoring</button>` : ""}
        <button type="button" class="btn sm" data-inc-res="${x.id}">Resolve Incident</button>
      </div>
      ${INC.updId === x.id ? `<form class="form formbox" data-inc-updf="${x.id}" style="margin-top:6px">
        <div class="fld"><label>Entry Type</label><select name="kind"><option value="update">Status Update</option><option value="escalation">Escalation</option><option value="mitigation">Mitigation Applied</option></select></div>
        <div class="fld wide"><label>Timeline Message *</label><input name="message" type="text" placeholder="e.g. Escalated to ISP Astinet NOC, ticket #..." required></div>
        <div class="acts wide"><button class="btn sm" type="submit">Post Update</button><button type="button" class="btn ghost sm" data-inc-upd="0">Cancel</button></div></form>` : ""}
      ${INC.resolveId === x.id ? `<form class="form formbox" data-inc-resf="${x.id}" style="margin-top:6px">
        <div class="fld wide"><label>Root Cause &amp; Resolution Summary *</label><input name="root_cause" type="text" placeholder="e.g. Fiber cut repaired by ISP at 14:20 WIB; all links restored" required></div>
        <div class="acts wide"><button class="btn sm" type="submit">Confirm Resolved</button><button type="button" class="btn ghost sm" data-inc-res="0">Cancel</button></div></form>` : ""}
    ` : ""}
  </article>`).join("");
  return `<div class="grid"><section class="panel c12">
    <header>
      <div><h2>Major Incident War Room</h2><span class="sub">Coordinate cross-shift major outages, escalations, and root cause timelines</span></div>
      <div class="acts">
        <div class="seg">${[["open", "Active (" + (D.open_count || 0) + ")"], ["resolved", "Resolved"], ["all", "All"]].map(([k, l]) => `<button type="button" data-inc-flt="${k}" aria-pressed="${INC.filter === k}">${l}</button>`).join("")}</div>
        ${canW ? `<button type="button" class="btn" data-inc-act="new">+ Declare Incident</button>` : ""}
      </div>
    </header>
    ${INC.msg ? `<div class="msg ${INC.msg.ok ? "ok" : "err"}">${esc(INC.msg.t)}</div>` : ""}
    ${sug}${form}
    ${cards || `<div class="empty sm">No ${INC.filter === "open" ? "active" : ""} major incidents. All operations normal.</div>`}
  </section></div>`;
}

/* ==================== 5. ADMIN -> ACCESS -> SSO / IDENTITY ==================== */
const SSO_ST = {d: null, msg: null, busy: false};
async function loadSso() {
  try { SSO_ST.d = await api("/api/admin/sso"); } catch (e) { SSO_ST.msg = {ok: false, t: e.message}; SSO_ST.d = {}; }
  render(false);
}
function vSso() {
  if (!SSO_ST.d) { loadSso(); return `<div class="empty sm">Loading SSO configuration…</div>`; }
  const d = SSO_ST.d;
  return admTitle("Single Sign-On (SSO / OIDC)", "Connect TERA Dashboard to Microsoft Entra ID (Azure AD), Keycloak, Google Workspace, or any standard OpenID Connect identity provider.", `<button type="button" class="btn ghost sm" data-sso="test">Test OIDC Discovery</button>`) +
    (SSO_ST.msg ? `<div class="msg ${SSO_ST.msg.ok ? "ok" : "err"}">${esc(SSO_ST.msg.t)}</div>` : "") +
    `<form class="form formbox" data-sso-form style="margin-top:6px">
      <div class="fld wide"><label class="chk"><input type="checkbox" id="ssoEn" ${d.enabled ? "checked" : ""}> <b>Enable SSO Sign-In on Login Page</b></label></div>
      <div class="fld"><label for="ssoProv">Button Label / Provider Name</label><input id="ssoProv" type="text" value="${esc(d.provider_name || "Corporate SSO")}" placeholder="e.g. Pelindo Microsoft SSO"></div>
      <div class="fld"><label for="ssoCb">Redirect / Callback URL (register in your IdP)</label><input id="ssoCb" type="text" value="${esc(d.callback_url || "")}" readonly></div>
      <div class="fld wide"><label for="ssoIss">OIDC Issuer / Discovery Base URL</label><input id="ssoIss" type="url" value="${esc(d.issuer_url || "")}" placeholder="e.g. https://login.microsoftonline.com/<tenant-id>/v2.0"></div>
      <div class="fld"><label for="ssoCid">Client ID *</label><input id="ssoCid" type="text" value="${esc(d.client_id || "")}"></div>
      <div class="fld"><label for="ssoSec">Client Secret ${d.secret_set ? "(saved — leave blank to keep)" : ""}</label><input id="ssoSec" type="password" placeholder="${d.secret_set ? "••••••••" : "Enter client secret"}"></div>
      <div class="fld"><label for="ssoScp">Scopes</label><input id="ssoScp" type="text" value="${esc(d.scopes || "openid email profile")}"></div>
      <div class="fld"><label for="ssoDom">Allowed Email Domains (comma-separated, optional)</label><input id="ssoDom" type="text" value="${esc(d.allowed_domains || "")}" placeholder="e.g. pelindomultiterminal.co.id"></div>
      <div class="fld"><label for="ssoUcl">Username Claim</label><input id="ssoUcl" type="text" value="${esc(d.username_claim || "preferred_username")}"></div>
      <div class="fld"><label for="ssoNcl">Display Name Claim</label><input id="ssoNcl" type="text" value="${esc(d.name_claim || "name")}"></div>
      <div class="fld"><label for="ssoRole">Auto-Provision Default Role</label><select id="ssoRole">${Object.entries(ROLES).map(([k, v]) => `<option value="${esc(k)}" ${d.default_role === k ? "selected" : ""}>${esc(v)}</option>`).join("")}</select></div>
      <div class="fld"><label class="chk" style="margin-top:22px"><input type="checkbox" id="ssoAuto" ${d.auto_provision ? "checked" : ""}> Auto-create local user on first SSO login</label></div>
      <div class="fld wide"><details class="how" style="padding:6px 0"><summary>Advanced: Explicit OAuth2 Endpoints (optional if Issuer Discovery is set)</summary>
        <div class="form" style="margin-top:8px">
          <div class="fld"><label for="ssoAuth">Authorization URL</label><input id="ssoAuth" type="url" value="${esc(d.auth_url || "")}"></div>
          <div class="fld"><label for="ssoTok">Token URL</label><input id="ssoTok" type="url" value="${esc(d.token_url || "")}"></div>
          <div class="fld"><label for="ssoInfo">UserInfo URL</label><input id="ssoInfo" type="url" value="${esc(d.userinfo_url || "")}"></div>
          <div class="fld"><label class="chk" style="margin-top:22px"><input type="checkbox" id="ssoTls" ${d.verify_tls !== false ? "checked" : ""}> Verify TLS Certificate</label></div>
        </div></details></div>
      <div class="acts wide"><button class="btn" type="submit"${SSO_ST.busy ? " disabled" : ""}>Save SSO Configuration</button></div>
    </form>`;
}

/* ==================== 6. ADMIN -> NOTIFICATIONS -> SCHEDULED REPORTS ==================== */
const SCH = {rows: null, edit: null, msg: null};
async function loadSchedules() {
  try { SCH.rows = (await api("/api/admin/schedules")).rows || []; } catch (e) { SCH.rows = []; SCH.msg = {ok: false, t: e.message}; }
  render(false);
}
function vSchedules() {
  if (!SCH.rows) { loadSchedules(); return `<div class="empty sm">Loading scheduled reports…</div>`; }
  const e = SCH.edit;
  const form = !e ? "" : `<form class="form formbox" data-sch-form style="margin-bottom:12px">
    <div class="fld"><label for="schName">Schedule Name *</label><input id="schName" type="text" value="${esc(e.name || "")}" placeholder="e.g. Shift Handover Digest" required></div>
    <div class="fld"><label for="schFreq">Frequency</label><select id="schFreq">${[["shift", "Every Shift Change (08:00, 15:00, 22:00)"], ["daily", "Daily"], ["weekly", "Weekly"], ["monthly", "Monthly"]].map(([k, l]) => `<option value="${k}" ${e.frequency === k ? "selected" : ""}>${l}</option>`).join("")}</select></div>
    <div class="fld"><label for="schTime">Run Time (WIB, HH:MM)</label><input id="schTime" type="text" value="${esc(e.run_time || "08:00")}" placeholder="08:00"></div>
    <div class="fld"><label for="schKind">Report Content</label><select id="schKind">${[["shift_summary", "Shift Summary Digest"], ["summary", "Management Summary"], ["full", "Full Report"], ["noc", "ISP & Network"], ["servicedesk", "Ticketing"], ["cyber", "Cyber Security"], ["devices", "Devices"]].map(([k, l]) => `<option value="${k}" ${e.report_kind === k ? "selected" : ""}>${l}</option>`).join("")}</select></div>
    <div class="fld"><label for="schFmt">Format</label><select id="schFmt">${[["text", "Text Digest"], ["pdf", "PDF Attachment"], ["xlsx", "Excel Attachment"]].map(([k, l]) => `<option value="${k}" ${e.fmt === k ? "selected" : ""}>${l}</option>`).join("")}</select></div>
    <div class="fld"><label for="schCh">Delivery Channel</label><select id="schCh">${[["webhook", "Webhooks (WhatsApp / Telegram / Teams)"], ["email", "Email (SMTP)"], ["both", "Both Email & Webhooks"]].map(([k, l]) => `<option value="${k}" ${e.channel === k ? "selected" : ""}>${l}</option>`).join("")}</select></div>
    <div class="fld"><label for="schSite">Location Filter (optional)</label><select id="schSite"><option value="">All locations</option>${CFG.sites.map(x => `<option value="${esc(x)}" ${e.site === x ? "selected" : ""}>${esc(x)}</option>`).join("")}</select></div>
    <div class="fld"><label for="schRec">Email Recipients (comma-separated)</label><input id="schRec" type="text" value="${esc(e.recipients || "")}" placeholder="ops@pelindo.co.id, noc@pelindo.co.id"></div>
    <div class="fld wide"><label class="chk"><input type="checkbox" id="schEn" ${e.enabled !== false ? "checked" : ""}> Enabled</label></div>
    <div class="acts wide"><button class="btn" type="submit">Save Schedule</button><button class="btn ghost" type="button" data-sch="cancel">Cancel</button>${e.id ? `<button class="btn danger" type="button" data-sch="del" data-id="${e.id}" style="margin-left:auto">Delete</button>` : ""}</div>
  </form>`;
  return admTitle("Scheduled Reports & Auto-Digest", "Automatically deliver shift summaries or PDF/Excel reports via Email or Webhooks on a recurring schedule.", `<button type="button" class="btn" data-sch="new">+ Add Schedule</button>`) +
    (SCH.msg ? `<div class="msg ${SCH.msg.ok ? "ok" : "err"}">${esc(SCH.msg.t)}</div>` : "") + form +
    tbl(["Name", "Schedule", "Content", "Channel", "Last Run", "Status", "Actions"], SCH.rows.map(s => [
      {h: `<b>${esc(s.name)}</b>${s.enabled ? "" : ` <span class="tag warn">Paused</span>`}`},
      s.frequency === "shift" ? "Every shift" : `${s.frequency} @ ${s.run_time}`,
      `${s.report_kind} (${s.fmt})`, s.channel,
      dtime(s.last_run_at), s.last_status || "–",
      {h: `<span class="acts"><button type="button" class="btn ghost sm" data-sch="run" data-id="${s.id}">Run Now</button><button type="button" class="btn ghost sm" data-sch="edit" data-id="${s.id}">Edit</button></span>`}
    ]), {empty: "No scheduled reports configured yet. Click + Add Schedule to create one."});
}

/* ==================== GLOBAL EVENT HANDLERS ==================== */
document.addEventListener("click", async e => {
  if (!e.target.closest("#bellWrap")) { const p = $("bellPop"); if (p) p.hidden = true; }
  const b = e.target.closest("button"); if (!b) return;
  if (b.id === "searchBtn") { openSearch(); return; }
  if (b.hasAttribute("data-srch-close")) { const d = $("dlgSearch"); if (d) d.close(); return; }
  if (b.id === "bellBtn") {
    const p = $("bellPop"); if (!p) return;
    const open = p.hidden; closePops(); p.hidden = !open;
    if (open) { renderBellPop(); loadAlerts(); }
    return;
  }
  if (b.dataset.ackIns) { await send("/api/alerts/ack/" + b.dataset.ackIns, {}); loadAlerts(); return; }
  if (b.hasAttribute("data-ack-all")) { await send("/api/alerts/ack-all", {}); loadAlerts(); return; }
  if (b.dataset.bellGo) {
    const p = $("bellPop"); if (p) p.hidden = true;
    const o = {tab: b.dataset.bellGo}; if (b.dataset.bellSite && !CFG.me.site) o.site = b.dataset.bellSite;
    set(o); return;
  }
  if (b.dataset.srchTab || b.dataset.srchSite) {
    const d = $("dlgSearch"); if (d) d.close();
    const o = {};
    if (b.dataset.srchTab) o.tab = b.dataset.srchTab;
    if (b.dataset.srchSite && !CFG.me.site) o.site = b.dataset.srchSite;
    set(o); return;
  }
  // Major Incidents
  if (b.dataset.incFlt) { INC.filter = b.dataset.incFlt; INC.data = null; render(false); return; }
  if (b.dataset.incAct === "new") { INC.showNew = true; INC.msg = null; render(false); return; }
  if (b.dataset.incAct === "cancel") { INC.showNew = false; render(false); return; }
  if (b.dataset.incQuick) {
    try { await send("/api/incidents", {title: b.dataset.incQtitle, severity: "sev1", site: b.dataset.incQuick, summary: "Declared from auto-detected multi-system site outage."}); INC.data = null; INC.msg = {ok: true, t: "Major incident declared."}; loadAlerts(); render(false); }
    catch (er) { INC.msg = {ok: false, t: er.message}; render(false); }
    return;
  }
  if (b.dataset.incUpd !== undefined) { INC.updId = +b.dataset.incUpd || null; INC.resolveId = null; render(false); return; }
  if (b.dataset.incRes !== undefined) { INC.resolveId = +b.dataset.incRes || null; INC.updId = null; render(false); return; }
  if (b.dataset.incMon) { await send("/api/incidents/" + b.dataset.incMon, {status: "monitoring"}, "PATCH"); INC.data = null; render(false); return; }
  // SSO Test
  if (b.dataset.sso === "test") {
    try { const r = await send("/api/admin/sso/test", {}); SSO_ST.msg = {ok: true, t: "Discovery OK: " + (r.authorization_endpoint || "endpoints resolved")}; }
    catch (er) { SSO_ST.msg = {ok: false, t: er.message}; }
    render(false); return;
  }
  // Schedules
  if (b.dataset.sch) {
    const a = b.dataset.sch, id = +b.dataset.id;
    if (a === "new") { SCH.edit = {enabled: true, frequency: "daily", run_time: "08:00", report_kind: "shift_summary", fmt: "text", channel: "webhook"}; SCH.msg = null; render(false); }
    else if (a === "edit") { SCH.edit = Object.assign({}, (SCH.rows || []).find(x => x.id === id)); SCH.msg = null; render(false); }
    else if (a === "cancel") { SCH.edit = null; render(false); }
    else if (a === "del") { if (!confirm("Delete this schedule?")) return; await api("/api/admin/schedules/" + id, {method: "DELETE"}); SCH.edit = null; SCH.rows = null; SCH.msg = {ok: true, t: "Schedule deleted."}; render(false); }
    else if (a === "run") {
      b.disabled = true; b.textContent = "Sending…";
      try { const r = await send("/api/admin/schedules/" + id + "/run", {}); SCH.msg = {ok: true, t: "Sent: " + r.status}; SCH.rows = null; }
      catch (er) { SCH.msg = {ok: false, t: er.message}; }
      render(false);
    }
  }
});
document.addEventListener("input", e => {
  if (e.target.id === "srchQ") {
    clearTimeout(_SRCH_T);
    const v = e.target.value;
    _SRCH_T = setTimeout(() => runSearch(v), 150);
  }
});
document.addEventListener("submit", async e => {
  const f = e.target;
  if (f.id === "incNewF") {
    e.preventDefault(); e.stopImmediatePropagation();
    try { await send("/api/incidents", {title: $("incT").value, severity: $("incSev").value, site: $("incSite").value || null, commander: $("incCmd").value, summary: $("incSum").value}); INC.showNew = false; INC.data = null; INC.msg = {ok: true, t: "Major incident declared and alert dispatched."}; loadAlerts(); }
    catch (er) { INC.msg = {ok: false, t: er.message}; }
    render(false); return;
  }
  if (f.dataset && f.dataset.incUpdf) {
    e.preventDefault(); e.stopImmediatePropagation();
    try { await send("/api/incidents/" + f.dataset.incUpdf + "/updates", {kind: f.kind.value, message: f.message.value}); INC.updId = null; INC.data = null; }
    catch (er) { INC.msg = {ok: false, t: er.message}; }
    render(false); return;
  }
  if (f.dataset && f.dataset.incResf) {
    e.preventDefault(); e.stopImmediatePropagation();
    try { await send("/api/incidents/" + f.dataset.incResf, {status: "resolved", root_cause: f.root_cause.value}, "PATCH"); INC.resolveId = null; INC.data = null; loadAlerts(); }
    catch (er) { INC.msg = {ok: false, t: er.message}; }
    render(false); return;
  }
  if (f.matches("[data-sso-form]")) {
    e.preventDefault(); e.stopImmediatePropagation();
    SSO_ST.busy = true; render(false);
    try {
      await send("/api/admin/sso", {
        enabled: $("ssoEn").checked, provider_name: $("ssoProv").value.trim(), issuer_url: $("ssoIss").value.trim(),
        auth_url: $("ssoAuth").value.trim(), token_url: $("ssoTok").value.trim(), userinfo_url: $("ssoInfo").value.trim(),
        client_id: $("ssoCid").value.trim(), client_secret: $("ssoSec").value, scopes: $("ssoScp").value.trim(),
        auto_provision: $("ssoAuto").checked, default_role: $("ssoRole").value, allowed_domains: $("ssoDom").value.trim(),
        username_claim: $("ssoUcl").value.trim(), name_claim: $("ssoNcl").value.trim(), verify_tls: $("ssoTls").checked,
      }, "PUT");
      SSO_ST.d = null; SSO_ST.msg = {ok: true, t: "SSO configuration saved."};
    } catch (er) { SSO_ST.msg = {ok: false, t: er.message}; }
    finally { SSO_ST.busy = false; render(false); }
    return;
  }
  if (f.matches("[data-sch-form]")) {
    e.preventDefault(); e.stopImmediatePropagation();
    const body = {
      name: $("schName").value.trim(), enabled: $("schEn").checked, frequency: $("schFreq").value,
      run_time: $("schTime").value.trim() || "08:00", report_kind: $("schKind").value, fmt: $("schFmt").value,
      site: $("schSite").value || null, channel: $("schCh").value, recipients: $("schRec").value.trim() || null,
    };
    try {
      if (SCH.edit && SCH.edit.id) await send("/api/admin/schedules/" + SCH.edit.id, body, "PUT");
      else await send("/api/admin/schedules", body, "POST");
      SCH.edit = null; SCH.rows = null; SCH.msg = {ok: true, t: "Schedule saved."};
    } catch (er) { SCH.msg = {ok: false, t: er.message}; }
    render(false);
  }
}, true);
