const DATA = JSON.parse(document.getElementById("site-data").textContent);
const GEO = JSON.parse(document.getElementById("geo-data").textContent);
const CANDS = [];
const S = DATA.seoul;
const METRICS = {
  share30: { label: "서른 살 넘은 집 비율", unit: "%", breaks: [20, 25, 30, 40], ticks: ["20% 미만", "20–25%", "25–30%", "30–40%", "40% 이상"], ref: S.share30, sub: "세로선: 서울 평균 " + S.share30 + "%" },
  delta: { label: `서른 살 넘은 집, ${DATA.y0}→${DATA.y1} 늘어난 폭`, unit: "%p", plus: true, breaks: [5, 10, 15, 20], ticks: ["5%p 미만", "5–10", "10–15", "15–20", "20%p 이상"], ref: +(S.share30 - S.share30_prev).toFixed(1), sub: "세로선: 서울 전체 +" + (S.share30 - S.share30_prev).toFixed(1) + "%p" },
  aptShare30: { label: "서른 살 넘은 아파트 비율 (재건축 연한)", unit: "%", breaks: [10, 20, 30, 40], ticks: ["10% 미만", "10–20%", "20–30%", "30–40%", "40% 이상"], ref: S.aptShare30, sub: "세로선: 서울 평균 " + S.aptShare30 + "%" },
  aptNext: { label: "20대 아파트 비율 (10년 안에 서른 살)", unit: "%", breaks: [25, 35, 45, 50], ticks: ["25% 미만", "25–35%", "35–45%", "45–50%", "50% 이상"], ref: S.aptNext, sub: "세로선: 서울 평균 " + S.aptNext + "%" },
  low20: { label: "스무 살 넘은 저층 주택 비율 (재개발 기준)", unit: "%", breaks: [50, 55, 60, 65], ticks: ["50% 미만", "50–55%", "55–60%", "60–65%", "65% 이상"], ref: 60, thr: true, sub: "굵은 선: 재개발 노후도 기준 60% · 서울 평균 " + S.low20 + "%" }
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

/* 아이소메트릭 지도: 북쪽을 위로 둔 채 비스듬히 내려다본 모습이에요.
   구마다 같은 두께의 판(옆면 = 같은 색을 조금 어둡게 겹쳐 쌓음)으로 그리고, 고른 구는 살짝 떠올라요. */
const svg = document.getElementById("map");
const NS = "http://www.w3.org/2000/svg", XL = "http://www.w3.org/1999/xlink";
const K = GEO.k || 1, DEPTH = GEO.depth || 0, LIFT = 7, PIN = 13;
const reduceMotion = () => window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
svg.setAttribute("viewBox", `-8 ${-8 - PIN} ${GEO.w + 16} ${GEO.h + DEPTH + 24 + PIN}`);
const mk = (tag, attrs) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); return e; };
const use = (id, attrs) => { const u = mk("use", attrs); u.setAttribute("href", "#" + id); u.setAttributeNS(XL, "xlink:href", "#" + id); return u; };
const defs = mk("defs", {});
const gShadow = mk("g", { class: "iso-shadow", "aria-hidden": "true" }), gWall = mk("g", { class: "iso-wall", "aria-hidden": "true" });
const gFill = mk("g", {}), gCand = mk("g", {}), gHi = mk("g", { class: "iso-lift", "aria-hidden": "true" }), gLbl = mk("g", {}), gMk = mk("g", {});
svg.append(defs, gShadow, gWall, gFill, gCand, gHi, gLbl, gMk);
gShadow.append(mk("ellipse", { cx: GEO.w / 2, cy: GEO.h + DEPTH + 8, rx: GEO.w * 0.46, ry: 9 }));
const paths = {}, labels = {}, walls = {}, ids = {};
Object.keys(GEO.gu).forEach((gu, i) => {
  const p = GEO.gu[gu], id = "iso-g" + i; ids[gu] = id;
  defs.append(mk("path", { id, d: p.d }));
  const w = mk("g", {}); for (let k = DEPTH; k >= 1; k--) w.append(use(id, { y: k })); gWall.append(w); walls[gu] = w;
  const el = mk("path", { d: p.d, class: "gu", tabindex: "0", role: "button" }); el.dataset.gu = gu;
  gFill.append(el); paths[gu] = el;
  const c = mk("path", { d: p.d, class: "cand" }); c.dataset.gu = gu; c.style.display = "none"; gCand.append(c);
  const t = mk("text", { x: p.cx, y: p.cy + 4, class: "lbl" }); t.textContent = short(gu); gLbl.append(t); labels[gu] = t;
});

// 정비사업 표시: 바닥에 그림자, 짧은 깃대 위에 기호 (■ 재건축 · ● 재개발 · ▲ 모아타운)
const MK = DATA.markers.map(m => ({ ...m, y: m.y * K }));
const markerEls = MK.map((m, i) => {
  const g = mk("g", { class: "mk " + m.t, tabindex: "0", role: "button", "aria-label": `${m.name} (${m.gu}) ${KIND[m.t]}` });
  g.dataset.i = i;
  const top = m.y - PIN;
  g.append(mk("ellipse", { class: "foot", cx: m.x, cy: m.y, rx: 4.5, ry: 2 }));
  g.append(mk("line", { class: "stick", x1: m.x, y1: m.y, x2: m.x, y2: top + 4 }));
  g.append(mk("circle", { class: "hit", cx: m.x, cy: top, r: 13 }));
  let s;
  if (m.t === "rebuild") s = mk("rect", { class: "shape", x: m.x - 6, y: top - 6, width: 12, height: 12, rx: 2 });
  else if (m.t === "redev") s = mk("circle", { class: "shape", cx: m.x, cy: top, r: 6.5 });
  else s = mk("path", { class: "shape", d: `M${m.x} ${top - 7.5}L${m.x + 7.5} ${top + 5.5}H${m.x - 7.5}Z` });
  g.append(s); gMk.append(g); return g;
});
// 깃대가 구 이름을 가리면, 이름을 아래·위·왼쪽·오른쪽 중 비어 있는 자리로 옮겨요
const pinBox = m => [m.x - 8, m.y - PIN - 8, m.x + 8, m.y + 3];
const lblBox = (x, y, half) => [x - half, y - 12, x + half, y + 3];
const clash = (a, b) => a[0] < b[2] && a[2] > b[0] && a[1] < b[3] && a[3] > b[1];
for (const [gu, t] of Object.entries(labels)) {
  const cx = +t.getAttribute("x"), cy = +t.getAttribute("y"), half = short(gu).length * 6.5 + 3;
  const pins = MK.map(pinBox), free = (x, y) => !pins.some(p => clash(lblBox(x, y, half), p));
  if (free(cx, cy)) continue;
  const near = MK.filter(m => clash(lblBox(cx, cy, half + 30), pinBox(m)));
  const lo = Math.max(...near.map(m => m.y)), hi = Math.min(...near.map(m => m.y - PIN));
  const tries = [[cx, lo + 15], [cx, hi - 10], [cx - half - 14, cy], [cx + half + 14, cy], [cx, lo + 30]];
  const ok = tries.find(([x, y]) => free(x, y)) || tries[0];
  t.setAttribute("x", ok[0]); t.setAttribute("y", ok[1]);
}
// 앞(남쪽)에 있는 깃대가 뒤 깃대를 가리도록 위쪽(북쪽)부터 차례로 그려요
markerEls.map((g, i) => [g, MK[i].y]).sort((a, b) => a[1] - b[1]).forEach(([g]) => gMk.append(g));

// 옆면 색: 윗면 색을 어둡게 섞어요(아래로 갈수록 조금 더 어둡게)
const shade = (hex, f) => { const h = hex.replace("#", ""); return "#" + [0, 2, 4].map(i => Math.round(parseInt(h.substr(i, 2), 16) * f).toString(16).padStart(2, "0")).join(""); };
function paintWalls(gu, color) {
  const w = walls[gu], n = w.children.length;
  [...w.children].forEach((u, j) => u.setAttribute("fill", shade(color, 0.58 + 0.16 * (j / Math.max(1, n - 1)))));
}

function facts() {
  const rows = DATA.rows;
  const topApt = [...rows].sort((a, b) => b.aptShare30 - a.aptShare30)[0];
  const over60 = rows.filter(r => r.low20 >= 60).length;
  document.getElementById("facts").innerHTML = [
    [S.share30 + "%", "서른 살 넘은 서울 집 (" + fmt(S.old30) + "호)"],
    [S.aptShare30 + "%", "서른 살 넘은 아파트 · 가장 많은 곳 " + topApt.gu + " " + topApt.aptShare30 + "%"],
    [S.low20 + "%", "스무 살 넘은 저층 주택 (재개발 기준 60%)"],
    [over60 + "개 구", "저층 주택 노후도가 60%를 넘는 구"]
  ].map(([b, t]) => `<div class="fact"><b>${b}</b><span>${t}</span></div>`).join("");
}

function render() {
  const M = METRICS[metric], cs = getComputedStyle(document.documentElement);
  const colors = RAMP.map(v => cs.getPropertyValue(v).trim());
  for (const [gu, el] of Object.entries(paths)) {
    const b = binOf(byGu[gu][metric], M.breaks);
    el.style.fill = colors[b]; el.dataset.c = colors[b];
    if (/^#[0-9a-f]{6}$/i.test(colors[b])) paintWalls(gu, colors[b]);
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
  document.querySelectorAll(".controls .seg button[data-m]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.m === metric)));
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
  const vb = svg.viewBox.baseVal, scale = sv.width / vb.width;
  let x = (cx - vb.x) * scale + (sv.left - bb.left), y = (cy - vb.y) * scale + (sv.top - bb.top);
  const tw = tip.offsetWidth, th = tip.offsetHeight;
  x = Math.min(Math.max(4, x + 14), bw - tw - 4);
  y = y - th - 14 < 0 ? y + 18 : y - th - 14;
  tip.style.left = x + "px"; tip.style.top = y + "px";
}
let lifted = null;
function drop() {
  gHi.replaceChildren(); if (lifted) labels[lifted].removeAttribute("transform"); lifted = null;
}
function lift(gu) {
  drop(); lifted = gu;
  const id = ids[gu], color = paths[gu].dataset.c || "#999999", L = reduceMotion() ? 0 : LIFT;
  const g = mk("g", { class: "lifted" + (L ? " anim" : "") });
  for (let k = DEPTH; k >= -L + 1; k--) g.append(use(id, { y: k, fill: shade(color, k > 0 ? 0.58 + 0.16 * (1 - k / DEPTH) : 0.74) }));
  const t = use(id, { y: -L, class: "lift-top" }); t.style.fill = color; g.append(t);
  gHi.append(g);
  if (L) labels[gu].setAttribute("transform", `translate(0 ${-L})`);
  gLbl.append(labels[gu]);
}
function clearFocus() {
  tip.hidden = true; drop();
  document.querySelectorAll("#rows .row.hl").forEach(r => r.classList.remove("hl"));
  markerEls.forEach(e => e.classList.remove("on"));
  document.querySelectorAll(".site.on").forEach(e => e.classList.remove("on"));
}
function focusGu(gu) {
  clearFocus(); if (!gu) return;
  const r = byGu[gu];
  lift(gu);
  document.querySelectorAll("#rows .row").forEach(x => x.classList.toggle("hl", x.dataset.gu === gu));
  tip.innerHTML = `<h4>${gu}</h4><dl>
    <dt>서른 살 넘은 집</dt><dd>${r.share30}%</dd>
    <dt>서른 살 넘은 아파트</dt><dd>${r.aptShare30}% · ${fmt(r.apt30)}호</dd>
    <dt>20대 아파트</dt><dd>${r.aptNext}%</dd>
    <dt>스무 살 넘은 저층</dt><dd>${r.low20}%</dd>
    <dt>서른 살 넘은 저층</dt><dd>${r.low30}% · ${fmt(r.lowOld30)}호</dd>
    <dt>${DATA.y0} → ${DATA.y1}</dt><dd>${r.share30_prev}% → ${r.share30}%</dd></dl>`;
  tip.hidden = false; placeTip(GEO.gu[gu].cx, GEO.gu[gu].cy - (reduceMotion() ? 0 : LIFT));
}
function focusSite(i) {
  clearFocus(); const m = MK[i]; if (!m) return;
  markerEls[i].classList.add("on");
  document.querySelectorAll(`.site[data-i="${i}"]`).forEach(e => e.classList.add("on"));
  tip.innerHTML = `<div class="kind">${KIND[m.t]}</div><h4>${m.name} · ${m.gu}</h4><ul>${m.items.map(x => `<li>${x}</li>`).join("")}</ul>`;
  tip.hidden = false; placeTip(m.x, m.y - PIN);
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

document.querySelectorAll(".controls .seg").forEach(s => s.addEventListener("click", e => {
  const b = e.target.closest("button[data-m]"); if (!b) return;
  metric = b.dataset.m; try { localStorage.setItem("aging-metric", metric); } catch (err) {}
  clearFocus(); render();
}));
document.getElementById("sites-on").addEventListener("change", () => { clearFocus(); render(); });
const mq = window.matchMedia("(prefers-color-scheme: dark)");
mq.addEventListener && mq.addEventListener("change", render);
new MutationObserver(render).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

facts(); if (document.getElementById("sites")) siteList(); render(); table();

/* 3D로 보기: three.js와 3D 스크립트, 경계 데이터는 처음 켤 때만 내려받습니다. */
(function () {
  const box = document.getElementById("view-3d"), board = document.querySelector(".board"), v3d = document.getElementById("v3d");
  if (!box || !v3d) return;
  const ver = (document.querySelector('script[src*="map2d.js"]').src.split("?v=")[1] || "");
  let started = false;
  const load = src => new Promise((ok, no) => { const s = document.createElement("script"); s.src = "/assets/" + src + "?v=" + ver; s.onload = ok; s.onerror = no; document.body.append(s); });
  async function start() {
    if (started) return; started = true;
    v3d.setAttribute("aria-busy", "true");
    try {
      await load("vendor/three.min.js"); await load("vendor/OrbitControls.js"); await load("map3d.js");
      const geo = await (await fetch("/assets/geo3d.json?v=" + ver)).json();
      window.startMap3D(geo);
    } catch (e) {
      document.getElementById("d3-stage").insertAdjacentHTML("beforeend", '<div class="nogl"><p>3D 화면을 불러오지 못했어요. 새로고침하거나 평면 지도로 봐 주세요.</p></div>');
    }
    v3d.removeAttribute("aria-busy");
  }
  function apply() {
    const on = box.checked;
    board.hidden = on; v3d.hidden = !on;
    if (on) { clearFocus(); start(); }
    try { history.replaceState(null, "", on ? "#3d" : location.pathname + location.search); } catch (e) {}
  }
  box.addEventListener("change", apply);
  if (location.hash === "#3d" || /[?&]view=3d/.test(location.search)) { box.checked = true; apply(); }
})();
