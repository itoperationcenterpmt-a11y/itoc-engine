/* ---------- Data (completeness + RAW upload) ---------- */
function vData() { return subnav("report") + vDataBody(); }
function vDataBody() {
  const days = []; for (let d = S.from; d <= S.to && days.length < 62; d = addDays(d, 1)) days.push(d);
  const rows = (V.coverage || []).map(r => [esc(r.label), d => r.cells[d] || ["wait", "–"]]);
  const grid = `<div class="scroll"><div class="mx" style="grid-template-columns:minmax(150px,220px) repeat(${days.length},minmax(22px,1fr))"><div></div>${days.map(d => `<div class="h">${new Date(dayMs(d)).getUTCDate()}</div>`).join("")}
    ${rows.map(([l, f]) => `<div class="rl">${l}</div>` + days.map(d => { const [k, t] = f(d); return `<span class="c ${k}" data-tip="${esc(dlong(d) + "\n" + t)}"></span>`; }).join("")).join("")}</div></div>
    <div class="legend">${[["ok", "Complete"], ["dup", "Complete with notes"], ["bad", "Failed / incomplete"], ["miss", "None"], ["wait", "Not due yet"]].map(([k, l]) => `<span><b class="c ${k}"></b>${l}</span>`).join("")}</div>`;
  const bl = (V.batches || []).slice().reverse().map(b => [b.file, dmon(b.from) + " – " + dmon(b.to), b.by, dtime(b.at), b.rows, b.skipped, {h: b.issues.some(i => i.k === "crit") ? pill("crit", "Failed, not used") : b.issues.length ? pill("warn", "Used, with notes") : pill("good", "Valid")}, {h: b.issues.map(i => `<div class="sub">${esc(i.t)}</div>`).join("") || "–"}]);
  return `<div class="grid">${panel("c12", "Data Completeness per Day", ctxTxt(APPLY.kelengkapan), grid)}
  ${panel("c12", "Raw Data Upload", "", upCards())}  ${panel("c12", "Sync and Upload Log", (canUp("tickets") || canUp("prtg") || canUp("soc")) ? `<span class="acts">${canUp("tickets") ? `<button class="btn ghost" data-sync="manageengine">Sync ManageEngine</button>` : ""}${canUp("prtg") ? `<button class="btn ghost" data-sync="prtg">Sync PRTG</button>` : ""}${canUp("soc") ? `<button class="btn ghost" data-sync="panorama">Pull Panorama now</button>` : ""}</span>` : "Newest first", tbl(["Time", "Source", "Status", "Rows", "Message"], (V.sync_log || []).slice(0, 12).map(x => [dtime(x.at), x.src, {h: x.ok ? pill("good", "OK") : pill("crit", "Failed")}, x.rows, x.msg]), {tall: true}))}
  ${panel("c12", "SOC Upload History", "", tbl(["File", "Period", "Uploaded by", "Time", "Rows read", "Skipped", "Status", "Notes"], bl))}</div>`;
}

/* ---------- Report (Excel / PDF / PowerPoint download) ---------- */
