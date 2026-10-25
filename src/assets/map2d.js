const DATA = JSON.parse(document.getElementById("site-data").textContent);
const GEO = JSON.parse(document.getElementById("geo-data").textContent);
const CANDS = [];
const S = DATA.seoul;
const METRICS = {
  share30: { label: "전체 주택 중 30년 이상 비율", unit: "%", breaks: [20, 25, 30, 40], ticks: ["20% 미만", "20–25%", "25–30%", "30–40%", "40% 이상"], ref: S.share30, sub: "세로선: 서울 평균 " + S.share30 + "%" },
  delta: { label: `30년 이상 비율, ${DATA.y0}→${DATA.y1} 증가폭`, unit: "%p", plus: true, breaks: [5, 10, 15, 20], ticks: ["5%p 미만", "5–10", "10–15", "15–20", "20%p 이상"], ref: +(S.share30 - S.share30_prev).toFixed(1), sub: "세로선: 서울 전체 +" + (S.share30 - S.share30_prev).toFixed(1) + "%p" },
  aptShare30: { label: "아파트 중 30년 이상 비율 (재건축 대상)", unit: "%", breaks: [10, 20, 30, 40], ticks: ["10% 미만", "10–20%", "20–30%", "30–40%", "40% 이상"], ref: S.aptShare30, sub: "세로선: 서울 평균 " + S.aptShare30 + "%" },
  aptNext: { label: "아파트 중 20~30년 비율 (10년 내 재건축 대상)", unit: "%", breaks: [25, 35, 45, 50], ticks: ["25% 미만", "25–35%", "35–45%", "45–50%", "50% 이상"], ref: S.aptNext, sub: "세로선: 서울 평균 " + S.aptNext + "%" },
  low20: { label: "단독·다세대 등 저층 주택 중 20년 이상 비율 (재개발)", unit: "%", breaks: [50, 55, 60, 65], ticks: ["50% 미만", "50–55%", "55–60%", "60–65%", "65% 이상"], ref: 60, thr: true, sub: "굵은 선: 재개발 노후도 기준 60% · 서울 평균 " + S.low20 + "%" }
};
const KIND = { rebuild: "재건축 진행", redev: "재개발 · 신속통합기획 후보지", moa: "모아타운" };
const RAMP = ["--r0", "--r1", "--r2", "--r3", "--r4"];
const byGu = Object.fromEntries(DATA.rows.map(r => [r.gu, r]));
let metric = "share30";
try { const s = localStorage.getItem("aging-metric"); if (s && METRICS[s]) metric = s; } catch (e) {}

const lum = hex => { const h = hex.replace("#", ""); const c = [0, 2, 4].map(i => parseInt(h.substr(i, 2), 16) / 255).map(v => v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4)); return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]; };
const fmt = n => n.toLocaleString("ko-KR");
const short = g => g.length > 2 ? g.replace(/구$/, "") : g;
const binOf = (v, b) => { const i = b.findIndex(x => v < x); return i === -1 ? 4 : i; };

const svg = document.getElementById("map");
const NS = "http://www.w3.org/2000/svg";
svg.setAttribute("viewBox", `-6 -6 ${GEO.w + 12} ${GEO.h + 12}`);
const mk = (tag, attrs) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); return e; };
const gFill = mk("g", {}), gCand = mk("g", {}), gHi = mk("g", {}), gLbl = mk("g", {}), gMk = mk("g", {});
svg.append(gFill, gCand, gHi, gLbl, gMk);
const paths = {}, labels = {};
for (const [gu, p] of Object.entries(GEO.gu)) {
  const el = mk("path", { d: p.d, class: "gu", tabindex: "0", role: "button" }); el.dataset.gu = gu;
  gFill.append(el); paths[gu] = el;
  const c = mk("path", { d: p.d, class: "cand" }); c.dataset.gu = gu; c.style.display = "none"; gCand.append(c);
  const t = mk("text", { x: p.cx, y: p.cy + 4, class: "lbl" }); t.textContent = short(gu); gLbl.append(t); labels[gu] = t;
}
const hi = mk("path", { class: "outline" }); hi.style.display = "none"; gHi.append(hi);

const markerEls = DATA.markers.map((m, i) => {
  const g = mk("g", { class: "mk " + m.t, tabindex: "0", role: "button", "aria-label": `${m.name} (${m.gu}) ${KIND[m.t]}` });
  g.dataset.i = i;
  g.append(mk("circle", { class: "hit", cx: m.x, cy: m.y, r: 13 }));
  let s;
  if (m.t === "rebuild") s = mk("rect", { class: "shape", x: m.x - 6, y: m.y - 6, width: 12, height: 12, rx: 2 });
  else if (m.t === "redev") s = mk("circle", { class: "shape", cx: m.x, cy: m.y, r: 6.5 });
  else s = mk("path", { class: "shape", d: `M${m.x} ${m.y - 7.5}L${m.x + 7.5} ${m.y + 5.5}H${m.x - 7.5}Z` });
  g.append(s); gMk.append(g); return g;
});

function facts() {
  const rows = DATA.rows;
  const topApt = [...rows].sort((a, b) => b.aptShare30 - a.aptShare30)[0];
  const over60 = rows.filter(r => r.low20 >= 60).length;
  document.getElementById("facts").innerHTML = [
    [S.share30 + "%", "서울 전체 주택 중 30년 이상 (" + fmt(S.old30) + "호)"],
    [S.aptShare30 + "%", "아파트 중 30년 이상 · 최고 " + topApt.gu + " " + topApt.aptShare30 + "%"],
    [S.low20 + "%", "저층 주택 중 20년 이상 (재개발 기준 60%)"],
    [over60 + "개 구", "저층 주택 노후도가 구 평균으로 60% 이상"]
  ].map(([b, t]) => `<div class="fact"><b>${b}</b><span>${t}</span></div>`).join("");
}

function render() {
  const M = METRICS[metric], cs = getComputedStyle(document.documentElement);
  const colors = RAMP.map(v => cs.getPropertyValue(v).trim());
  for (const [gu, el] of Object.entries(paths)) {
    const b = binOf(byGu[gu][metric], M.breaks);
    el.style.fill = colors[b];
    el.setAttribute("aria-label", `${gu} ${byGu[gu][metric]}${M.unit}`);
    labels[gu].setAttribute("class", "lbl " + (lum(colors[b]) < 0.35 ? "on-dark" : "on-light"));
  }
  document.getElementById("legend").innerHTML =
    `<div class="title">${M.label}</div><div class="bins">${colors.map(c => `<div style="background:${c}"></div>`).join("")}</div><div class="ticks">${M.ticks.map(t => `<span>${t}</span>`).join("")}</div>`;
  document.getElementById("rank-title").textContent = M.label;
  document.getElementById("rank-sub").textContent = M.sub;
  const sorted = [...DATA.rows].sort((a, b) => b[metric] - a[metric]);
  const max = Math.max(...sorted.map(r => r[metric]), M.ref) * 1.04;
  const showCand = false;
  document.getElementById("rows").innerHTML = sorted.map((r, i) => {
    const b = binOf(r[metric], M.breaks);
    return `<div class="row" tabindex="0" data-gu="${r.gu}"><span class="rk">${i + 1}</span><span class="nm">${r.gu}${showCand && CANDS.includes(r.gu) ? "<i>●</i>" : ""}</span><span class="bar"><span style="width:${(r[metric] / max * 100).toFixed(1)}%;background:${colors[b]}"></span><span class="avg${M.thr ? " thr" : ""}" style="left:${(M.ref / max * 100).toFixed(1)}%"></span></span><span class="v">${M.plus ? "+" : ""}${r[metric].toFixed(1)}${M.unit}</span></div>`;
  }).join("");
  document.querySelectorAll(".seg button").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.m === metric)));
  document.querySelectorAll("path.cand").forEach(p => p.style.display = showCand && CANDS.includes(p.dataset.gu) ? "" : "none");
  const sitesOn = document.getElementById("sites-on").checked;
  gMk.style.display = sitesOn ? "" : "none";
  document.getElementById("mklegend").hidden = !sitesOn;
}

function siteList() {
  const cols = ["rebuild", "redev", "moa"].map(t => {
    const items = DATA.markers.map((m, i) => ({ m, i })).filter(x => x.m.t === t);
    return `<div class="sitecol"><h3><svg aria-hidden="true"><use href="#sym-${t}"></use></svg>${KIND[t]} · ${items.length}곳</h3>` +
      items.map(({ m, i }) => `<button type="button" class="site" data-i="${i}"><b>${m.name}<small>${m.gu}</small></b>${m.items.map(x => `<span>${x}</span>`).join("")}</button>`).join("") + `</div>`;
  });
  document.getElementById("sites").innerHTML = cols.join("");
}

function table() {
  const rows = [...DATA.rows].sort((a, b) => b.share30 - a.share30);
  document.getElementById("tbl").innerHTML =
    `<thead><tr><th>자치구</th><th>전체 주택(호)</th><th>30년 이상</th><th>${DATA.y0} → ${DATA.y1}</th><th>아파트(호)</th><th>아파트 30년+</th><th>아파트 20~30년</th><th>저층 주택(호)</th><th>저층 20년+</th><th>저층 30년+</th></tr></thead><tbody>` +
    rows.map(r => `<tr><td>${r.gu}</td><td>${fmt(r.total)}</td><td>${r.share30}%</td><td>${r.share30_prev}% → ${r.share30}%</td><td>${fmt(r.apt)}</td><td>${r.aptShare30}%</td><td>${r.aptNext}%</td><td>${fmt(r.lowTotal)}</td><td>${r.low20}%</td><td>${r.low30}%</td></tr>`).join("") +
    `<tr><td><b>서울 전체</b></td><td>${fmt(S.total)}</td><td>${S.share30}%</td><td>${S.share30_prev}% → ${S.share30}%</td><td></td><td>${S.aptShare30}%</td><td>${S.aptNext}%</td><td></td><td>${S.low20}%</td><td></td></tr></tbody>`;
}

const tip = document.getElementById("tip"), box = document.getElementById("mapbox");
function placeTip(cx, cy) {
  const bw = box.clientWidth, sv = svg.getBoundingClientRect(), bb = box.getBoundingClientRect();
  const scale = sv.width / (GEO.w + 12);
  let x = (cx + 6) * scale + (sv.left - bb.left), y = (cy + 6) * scale + (sv.top - bb.top);
  const tw = tip.offsetWidth, th = tip.offsetHeight;
  x = Math.min(Math.max(4, x + 14), bw - tw - 4);
  y = y - th - 14 < 0 ? y + 18 : y - th - 14;
  tip.style.left = x + "px"; tip.style.top = y + "px";
}
function clearFocus() {
  tip.hidden = true; hi.style.display = "none";
  document.querySelectorAll(".row.hl").forEach(r => r.classList.remove("hl"));
  markerEls.forEach(e => e.classList.remove("on"));
  document.querySelectorAll(".site.on").forEach(e => e.classList.remove("on"));
}
function focusGu(gu) {
  clearFocus(); if (!gu) return;
  const r = byGu[gu];
  hi.setAttribute("d", GEO.gu[gu].d); hi.style.display = "";
  document.querySelectorAll(".row").forEach(x => x.classList.toggle("hl", x.dataset.gu === gu));
  tip.innerHTML = `<h4>${gu}</h4><dl>
    <dt>전체 30년 이상</dt><dd>${r.share30}%</dd>
    <dt>아파트 30년 이상</dt><dd>${r.aptShare30}% · ${fmt(r.apt30)}호</dd>
    <dt>아파트 20~30년</dt><dd>${r.aptNext}%</dd>
    <dt>저층 20년 이상</dt><dd>${r.low20}%</dd>
    <dt>저층 30년 이상</dt><dd>${r.low30}% · ${fmt(r.lowOld30)}호</dd>
    <dt>${DATA.y0} → ${DATA.y1}</dt><dd>${r.share30_prev}% → ${r.share30}%</dd></dl>`;
  tip.hidden = false; placeTip(GEO.gu[gu].cx, GEO.gu[gu].cy);
}
function focusSite(i) {
  clearFocus(); const m = DATA.markers[i]; if (!m) return;
  markerEls[i].classList.add("on");
  document.querySelectorAll(`.site[data-i="${i}"]`).forEach(e => e.classList.add("on"));
  tip.innerHTML = `<div class="kind">${KIND[m.t]}</div><h4>${m.name} · ${m.gu}</h4><ul>${m.items.map(x => `<li>${x}</li>`).join("")}</ul>`;
  tip.hidden = false; placeTip(m.x, m.y);
}
function targetOf(e) {
  const g = e.target.closest && e.target.closest("g.mk");
  if (g) return { site: +g.dataset.i };
  const gu = e.target.dataset && e.target.classList.contains("gu") ? e.target.dataset.gu : null;
  return gu ? { gu } : null;
}
function act(t) { if (!t) return clearFocus(); if ("site" in t) focusSite(t.site); else focusGu(t.gu); }
svg.addEventListener("pointerover", e => { const t = targetOf(e); if (t) act(t); });
svg.addEventListener("pointerleave", clearFocus);
svg.addEventListener("click", e => act(targetOf(e)));
svg.addEventListener("focusin", e => act(targetOf(e)));
svg.addEventListener("focusout", clearFocus);
const rowsEl = document.getElementById("rows");
rowsEl.addEventListener("pointerover", e => { const r = e.target.closest(".row"); if (r) focusGu(r.dataset.gu); });
rowsEl.addEventListener("pointerleave", clearFocus);
rowsEl.addEventListener("focusin", e => { const r = e.target.closest(".row"); if (r) focusGu(r.dataset.gu); });
rowsEl.addEventListener("focusout", clearFocus);
rowsEl.addEventListener("click", e => { const r = e.target.closest(".row"); if (r) focusGu(r.dataset.gu); });
document.getElementById("sites")?.addEventListener("click", e => {
  const b = e.target.closest(".site"); if (!b) return;
  document.getElementById("sites-on").checked = true; render();
  focusSite(+b.dataset.i);
  box.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "center" });
});

document.querySelectorAll(".seg").forEach(s => s.addEventListener("click", e => {
  const b = e.target.closest("button"); if (!b) return;
  metric = b.dataset.m; try { localStorage.setItem("aging-metric", metric); } catch (err) {}
  clearFocus(); render();
}));
document.getElementById("sites-on").addEventListener("change", () => { clearFocus(); render(); });
const mq = window.matchMedia("(prefers-color-scheme: dark)");
mq.addEventListener && mq.addEventListener("change", render);
new MutationObserver(render).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

facts(); if (document.getElementById("sites")) siteList(); render(); table();
