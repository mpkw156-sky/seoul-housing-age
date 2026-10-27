/* 3D view for the map tab. Loaded on demand; window.startMap3D(geo) builds it inside #v3d. */
window.startMap3D = function (GEO) {
const DATA = JSON.parse(document.getElementById("site-data").textContent);
const S = DATA.seoul;
const $ = id => document.getElementById("d3-" + id);
const METRICS = {
  share30: { label: "서른 살 넘은 집 비율", unit: "%", full: 60, breaks: [20, 25, 30, 40], ticks: ["20%↓", "20–25", "25–30", "30–40", "40%↑"], ref: S.share30, refName: "서울 평균 " + S.share30 + "%" },
  delta: { label: `서른 살 넘은 집, ${DATA.y0}→${DATA.y1} 늘어난 폭`, unit: "%p", plus: true, full: 25, breaks: [5, 10, 15, 20], ticks: ["5%p↓", "5–10", "10–15", "15–20", "20%p↑"], ref: +(S.share30 - S.share30_prev).toFixed(1), refName: "서울 전체 +" + (S.share30 - S.share30_prev).toFixed(1) + "%p" },
  aptShare30: { label: "서른 살 넘은 아파트 비율 (재건축 연한)", unit: "%", full: 65, breaks: [10, 20, 30, 40], ticks: ["10%↓", "10–20", "20–30", "30–40", "40%↑"], ref: S.aptShare30, refName: "서울 평균 " + S.aptShare30 + "%" },
  aptNext: { label: "20대 아파트 비율 (10년 안에 서른 살)", unit: "%", full: 60, breaks: [25, 35, 45, 50], ticks: ["25%↓", "25–35", "35–45", "45–50", "50%↑"], ref: S.aptNext, refName: "서울 평균 " + S.aptNext + "%" },
  low20: { label: "스무 살 넘은 저층 주택 비율 (재개발 기준)", unit: "%", full: 90, breaks: [50, 55, 60, 65], ticks: ["50%↓", "50–55", "55–60", "60–65", "65%↑"], ref: 60, legal: true, refName: "재개발 노후도 기준 60%" }
};
const KIND = { rebuild: "재건축 진행", redev: "재개발 · 신속통합기획 후보지", moa: "모아타운" };
const RAMP = ["--r0", "--r1", "--r2", "--r3", "--r4"];
const HMAX = 20;
const byGu = Object.fromEntries(DATA.rows.map(r => [r.gu, r]));
let metric = (document.querySelector('.controls .seg button[data-m][aria-pressed="true"]') || {}).dataset?.m || "share30";
if (!METRICS[metric]) metric = "share30";
const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
const fmt = n => n.toLocaleString("ko-KR");
const short = g => g.length > 2 ? g.replace(/구$/, "") : g;
const binOf = (v, b) => { const i = b.findIndex(x => v < x); return i === -1 ? 4 : i; };
const tok = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const hOf = v => Math.max(0.15, v / METRICS[metric].full * HMAX);
const CX = GEO.w / 2, CY = GEO.h / 2, SC = 10;
const W = (x, y) => [(x - CX) / SC, (y - CY) / SC];

const stage = $("stage");
const labelsEl = $("labels");
const infoEl = $("info");
const pinsOn = () => document.getElementById("sites-on").checked;
let selected = null, selectedSite = null;

function sortedRows() { return [...DATA.rows].sort((a, b) => b[metric] - a[metric]); }

function readingText() {
  const M = METRICS[metric], rows = sortedRows();
  const over = rows.filter(r => r[metric] >= M.ref);
  const top = rows.slice(0, 3).map(r => `${r.gu} ${M.plus ? "+" : ""}${r[metric]}${M.unit}`).join(", ");
  const chip = '<span class="glass-chip" aria-hidden="true"></span>';
  if (M.legal) return `${chip}판은 재개발 노후도 기준 60%예요. 판 위로 솟은 <b>${over.length}개 구</b>는 단독·다세대 주택 중 스무 살 넘은 집이 구 평균만으로도 기준을 넘어요. 가장 높은 곳은 ${top}예요.`;
  if (metric === "aptShare30") return `${chip}판은 서울 평균 ${M.ref}%예요. 판보다 높은 <b>${over.length}개 구</b>에 재건축 연한(서른 살)을 넘긴 아파트가 많아요 (${top}).`;
  if (metric === "aptNext") return `${chip}판은 서울 평균 ${M.ref}%예요. 판보다 높은 <b>${over.length}개 구</b>는 10년 안에 서른 살이 되는 아파트가 많은 곳이에요 (${top}).`;
  if (metric === "delta") return `${chip}판은 서울 전체 증가폭 +${M.ref}%p예요. 판 위의 <b>${over.length}개 구</b>는 5년 새 서울 평균보다 빨리 나이 들었어요 (${top}).`;
  return `${chip}판은 서울 평균 ${M.ref}%예요. 판보다 높은 <b>${over.length}개 구</b>는 서른 살 넘은 집이 평균보다 많아요 (${top}).`;
}

function renderPanels() {
  const M = METRICS[metric];
  const colors = RAMP.map(tok);
  $("reading").innerHTML = readingText();
  $("legend").innerHTML =
    `<div class="title">${M.label}<br>높이: 바닥 0 → 판 = ${M.refName}</div><div class="bins">${colors.map(c => `<div style="background:${c}"></div>`).join("")}</div><div class="ticks">${M.ticks.map(t => `<span>${t}</span>`).join("")}</div>` +
    `<div class="keys"><span><i style="background:var(--mk-rebuild)"></i>재건축</span><span><i style="background:var(--mk-redev);border-radius:50%"></i>재개발 후보지</span><span><i style="background:var(--mk-moa);clip-path:polygon(50% 0,100% 100%,0 100%)"></i>모아타운</span></div>`;
  $("rank-title").textContent = M.label;
  $("rank-sub").textContent = "파란 선: " + M.refName;
  const rows = sortedRows(), max = Math.max(...rows.map(r => r[metric]), M.ref) * 1.04;
  $("rows").innerHTML = rows.map((r, i) => {
    const b = binOf(r[metric], M.breaks);
    return `<div class="row${selected === r.gu ? " hl" : ""}" tabindex="0" role="button" data-gu="${r.gu}"><span class="rk">${i + 1}</span><span class="nm">${r.gu}</span><span class="bar"><span style="width:${(r[metric] / max * 100).toFixed(1)}%;background:${colors[b]}"></span><span class="ref" style="left:${(M.ref / max * 100).toFixed(1)}%"></span></span><span class="v">${M.plus ? "+" : ""}${r[metric].toFixed(1)}${M.unit}</span></div>`;
  }).join("");
  document.querySelectorAll(".controls .seg button[data-m]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.m === metric)));
  renderInfo();
}

function renderInfo() {
  const M = METRICS[metric];
  if (selectedSite != null) {
    const m = DATA.markers[selectedSite];
    infoEl.innerHTML = `<button type="button" class="close" aria-label="닫기">×</button><div class="kind">${KIND[m.t]}</div><h4>${m.name} · ${m.gu}</h4><ul>${m.items.map(x => `<li>${x}</li>`).join("")}</ul>`;
    return;
  }
  if (selected) {
    const r = byGu[selected], rank = sortedRows().findIndex(x => x.gu === selected) + 1;
    const sites = DATA.markers.filter(m => m.gu === selected).map(m => m.name);
    infoEl.innerHTML = `<button type="button" class="close" aria-label="닫기">×</button><div class="kind">${M.label} · ${rank}위 / 25</div>
      <h4>${selected}<span class="big">${M.plus ? "+" : ""}${r[metric]}${M.unit}</span></h4>
      <dl><dt>서른 살 넘은 집</dt><dd>${r.share30}%</dd>
      <dt>서른 살 넘은 아파트</dt><dd>${r.aptShare30}% · ${fmt(r.apt30)}호</dd>
      <dt>20대 아파트</dt><dd>${r.aptNext}%</dd>
      <dt>스무 살 넘은 저층</dt><dd>${r.low20}%</dd>
      <dt>${DATA.y0} → ${DATA.y1}</dt><dd>${r.share30_prev}% → ${r.share30}%</dd>
      ${sites.length ? `<dt>사업장</dt><dd style="font-family:var(--f-sans)">${sites.join(", ")}</dd>` : ""}</dl>`;
    return;
  }
  const top = sortedRows()[0];
  infoEl.innerHTML = `<p class="hint"><b>구나 깃대를 눌러 보세요.</b><br>지금 가장 높은 기둥은 ${top.gu}(${M.plus ? "+" : ""}${top[metric]}${M.unit})예요.</p>`;
}
infoEl.addEventListener("click", e => { if (e.target.closest(".close")) select(null); });

/* ---------- 3D scene ---------- */
let renderer, scene, camera, controls, raycaster, pointer;
const districts = {}; const pins = []; let glass, glassEdge, glassLabel;
let ok = false;
try {
  if (!window.THREE) throw new Error("no three");
  renderer = new THREE.WebGLRenderer({ antialias: true });
  ok = true;
} catch (e) {
  stage.insertAdjacentHTML("beforeend", `<div class="nogl"><p>이 브라우저에서는 3D 화면을 그릴 수 없어요.<br>'3D로 보기'를 끄면 평면 지도로 같은 내용을 볼 수 있어요.</p></div>`);
}

function buildScene() {
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.domElement.setAttribute("tabindex", "0");
  renderer.domElement.setAttribute("aria-label", "3D 지도. 드래그해서 돌리고, 구를 눌러 선택합니다.");
  stage.prepend(renderer.domElement);
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(34, 1, 0.5, 1000);
  controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true; controls.dampingFactor = 0.08;
  controls.minDistance = 30; controls.maxDistance = 240;
  controls.maxPolarAngle = Math.PI * 0.47; controls.minPolarAngle = 0.02;
  controls.autoRotateSpeed = 0.7;
  controls.target.set(0, 5, 0);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x666666, 0.75));
  const dl = new THREE.DirectionalLight(0xffffff, 0.55); dl.position.set(-30, 60, 45); scene.add(dl);

  const ground = new THREE.Mesh(new THREE.CircleGeometry(46, 64), new THREE.MeshBasicMaterial({ color: 0xffffff }));
  ground.rotation.x = -Math.PI / 2; ground.position.y = -0.02; scene.add(ground); scene.userData.ground = ground;

  for (const [gu, g] of Object.entries(GEO.gu)) {
    const shapes = g.p.map(rings => {
      const toPts = arr => { const pts = []; for (let i = 0; i < arr.length; i += 2) { const [x, z] = W(arr[i], arr[i + 1]); pts.push(new THREE.Vector2(x, -z)); } return pts; };
      const sh = new THREE.Shape(toPts(rings[0]));
      rings.slice(1).forEach(h => sh.holes.push(new THREE.Path(toPts(h))));
      return sh;
    });
    const geom = new THREE.ExtrudeGeometry(shapes, { depth: 1, bevelEnabled: false });
    const cap = new THREE.MeshBasicMaterial({ color: 0xffffff });
    const side = new THREE.MeshLambertMaterial({ color: 0xffffff });
    const mesh = new THREE.Mesh(geom, [cap, side]);
    mesh.rotation.x = -Math.PI / 2; mesh.scale.z = 0.01; mesh.userData.gu = gu;
    const edges = new THREE.LineSegments(new THREE.EdgesGeometry(geom, 25), new THREE.LineBasicMaterial({ color: 0xffffff }));
    mesh.add(edges);
    scene.add(mesh);
    const [cx, cz] = W(g.cx, g.cy);
    const lb = document.createElement("div"); lb.className = "lb"; labelsEl.append(lb);
    districts[gu] = { mesh, cap, side, edges, cx, cz, h: 0.01, target: 0.01, lb };
  }

  const gw = 64, gd = 56;
  glass = new THREE.Mesh(new THREE.PlaneGeometry(gw, gd), new THREE.MeshBasicMaterial({ color: 0x2a5fa8, transparent: true, opacity: 0.16, depthWrite: false, side: THREE.DoubleSide }));
  glass.rotation.x = -Math.PI / 2; glass.renderOrder = 10; scene.add(glass);
  const eg = new THREE.BufferGeometry().setFromPoints([[-gw / 2, -gd / 2], [gw / 2, -gd / 2], [gw / 2, gd / 2], [-gw / 2, gd / 2], [-gw / 2, -gd / 2]].map(([x, z]) => new THREE.Vector3(x, 0, z)));
  glassEdge = new THREE.Line(eg, new THREE.LineBasicMaterial({ color: 0x2a5fa8 })); scene.add(glassEdge);
  glassLabel = document.createElement("div"); glassLabel.className = "lb glasslb"; labelsEl.append(glassLabel);
  glass.userData.corner = new THREE.Vector3(-gw / 2 + 0.8, 0, -gd / 2 + 0.8);

  DATA.markers.forEach((m, i) => {
    const [x, z] = W(m.x, m.y);
    const grp = new THREE.Group(); grp.position.set(x, 0, z);
    const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.07, 1, 6), new THREE.MeshBasicMaterial({ color: 0x777777 }));
    pole.position.y = 0.5; grp.add(pole);
    let headGeom;
    if (m.t === "rebuild") headGeom = new THREE.BoxGeometry(1.2, 1.2, 1.2);
    else if (m.t === "redev") headGeom = new THREE.SphereGeometry(0.72, 20, 14);
    else headGeom = new THREE.ConeGeometry(0.8, 1.5, 4);
    const head = new THREE.Mesh(headGeom, new THREE.MeshLambertMaterial({ color: 0xffffff }));
    head.userData.site = i; grp.add(head);
    const ring = new THREE.Mesh(new THREE.TorusGeometry(1.15, 0.12, 8, 28), new THREE.MeshBasicMaterial({ color: 0x000000 }));
    ring.rotation.x = Math.PI / 2; ring.visible = false; grp.add(ring);
    scene.add(grp);
    pins.push({ m, grp, pole, head, ring, h: 0.01 });
  });

  raycaster = new THREE.Raycaster(); pointer = new THREE.Vector2();
  setView("tilt", true);
  applyTheme(); setTargets();
  const ro = new ResizeObserver(resize); ro.observe(stage); resize();
  bindPointer();
  animate();
}

function resize() {
  const w = stage.clientWidth, h = stage.clientHeight;
  renderer.setSize(w, h, false); camera.aspect = w / h;
  camera.updateProjectionMatrix();
}

const VIEWS = { tilt: [0, 58, 66], low: [0, 16, 92], top: [0, 104, 0.01] };
let camAnim = null;
function setView(v, instant) {
  const p = VIEWS[v]; const narrow = Math.min(2.3, Math.max(1, 1.55 / (stage.clientWidth / stage.clientHeight)));
  const to = new THREE.Vector3(p[0] * narrow, p[1] * narrow, p[2] * narrow);
  const tgt = new THREE.Vector3(0, v === "top" ? 0 : 5, 0);
  document.querySelectorAll(".v3d .views .seg button").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.v === v)));
  if (instant || reduced) { camera.position.copy(to); controls.target.copy(tgt); controls.update(); camAnim = null; return; }
  camAnim = { from: camera.position.clone(), to, tFrom: controls.target.clone(), tgt, t: 0 };
}

function color(n) { return new THREE.Color(tok(n) || "#888888"); }
function applyTheme() {
  if (!ok) return;
  const bg = color("--stage"), surf = color("--surface"), ink = color("--ink"), glassC = color("--glass");
  scene.background = bg; scene.userData.ground.material.color = surf.clone().lerp(bg, 0.35);
  glass.material.color = glassC; glassEdge.material.color = glassC;
  const mk = { rebuild: color("--mk-rebuild"), redev: color("--mk-redev"), moa: color("--mk-moa") };
  pins.forEach(p => { p.head.material.color = mk[p.m.t]; p.pole.material.color = color("--ink-3"); p.ring.material.color = ink; });
  paintDistricts();
}
function paintDistricts() {
  if (!ok) return;
  const M = METRICS[metric], ramp = RAMP.map(color), bg = color("--stage"), surf = color("--surface"), ink = color("--ink");
  for (const [gu, d] of Object.entries(districts)) {
    const c = ramp[binOf(byGu[gu][metric], M.breaks)].clone();
    const dim = selected && selected !== gu;
    if (dim) c.lerp(bg, 0.6);
    d.cap.color = c; d.side.color = c.clone().multiplyScalar(0.92);
    d.edges.material.color = selected === gu ? ink : (dim ? surf.clone().lerp(bg, 0.5) : surf);
  }
}
function setTargets() {
  for (const [gu, d] of Object.entries(districts)) d.target = hOf(byGu[gu][metric]);
  glass.userData.target = hOf(METRICS[metric].ref);
  if (reduced) { for (const d of Object.values(districts)) d.h = d.target; glass.userData.h = glass.userData.target; }
  paintDistricts();
}

function select(gu, site) {
  selected = gu || null; selectedSite = site != null ? site : null;
  if (site != null) selected = null;
  pins.forEach((p, i) => p.ring.visible = i === selectedSite);
  paintDistricts();
  $("rows").querySelectorAll(".row").forEach(r => r.classList.toggle("hl", r.dataset.gu === selected));
  renderInfo();
}

function pick(ev) {
  const r = renderer.domElement.getBoundingClientRect();
  pointer.x = ((ev.clientX - r.left) / r.width) * 2 - 1; pointer.y = -((ev.clientY - r.top) / r.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
  const objs = [];
  if (pinsOn()) pins.forEach(p => objs.push(p.head));
  Object.values(districts).forEach(d => objs.push(d.mesh));
  const hit = raycaster.intersectObjects(objs, false)[0];
  if (!hit) return null;
  if (hit.object.userData.site != null) return { site: hit.object.userData.site };
  return { gu: hit.object.userData.gu };
}
function bindPointer() {
  const el = renderer.domElement; let down = null;
  el.addEventListener("pointerdown", e => { down = { x: e.clientX, y: e.clientY }; stopSpin(); });
  el.addEventListener("pointerup", e => {
    if (!down) return; const moved = Math.hypot(e.clientX - down.x, e.clientY - down.y); down = null;
    if (moved > 6) return;
    const t = pick(e);
    if (!t) select(null); else if (t.site != null) select(null, t.site); else select(t.gu === selected ? null : t.gu);
  });
  el.addEventListener("pointermove", e => {
    if (e.pointerType !== "mouse" || e.buttons) return;
    const t = pick(e); el.style.cursor = t ? "pointer" : "grab";
  });
  el.addEventListener("wheel", stopSpin, { passive: true });
}
function stopSpin() { const s = $("spin"); if (s.checked) { s.checked = false; controls.autoRotate = false; } }

function project(x, y, z) {
  const v = new THREE.Vector3(x, y, z).project(camera);
  return { x: (v.x + 1) / 2 * stage.clientWidth, y: (1 - v.y) / 2 * stage.clientHeight, vis: v.z < 1 };
}

function animate() {
  requestAnimationFrame(animate);
  const k = reduced ? 1 : 0.12;
  for (const d of Object.values(districts)) { d.h += (d.target - d.h) * k; d.mesh.scale.z = d.h; }
  const gd = glass.userData; gd.h = gd.h == null ? gd.target : gd.h + (gd.target - gd.h) * k;
  glass.position.y = gd.h; glassEdge.position.y = gd.h;
  const showPins = pinsOn();
  pins.forEach(p => {
    const base = districts[p.m.gu].h, top = base + 3.2;
    p.grp.visible = showPins;
    p.pole.scale.y = top; p.pole.position.y = top / 2;
    p.head.position.y = top + 0.6; p.ring.position.y = top + 0.6;
    if (p.m.t === "rebuild") p.head.rotation.y += reduced ? 0 : 0.01;
  });
  if (camAnim) {
    camAnim.t = Math.min(1, camAnim.t + 0.04); const e = 1 - Math.pow(1 - camAnim.t, 3);
    camera.position.lerpVectors(camAnim.from, camAnim.to, e); controls.target.lerpVectors(camAnim.tFrom, camAnim.tgt, e);
    if (camAnim.t >= 1) camAnim = null;
  }
  controls.update();
  renderer.render(scene, camera);
  const M = METRICS[metric], narrow = stage.clientWidth < 640;
  for (const [gu, d] of Object.entries(districts)) {
    const p = project(d.cx, d.h + 0.5, d.cz), v = byGu[gu][metric];
    const show = p.vis && (!narrow || gu === selected || v >= M.ref);
    d.lb.style.display = show ? "" : "none";
    if (show) {
      d.lb.style.transform = `translate(${p.x.toFixed(1)}px, ${p.y.toFixed(1)}px) translate(-50%, -100%)`;
      const txt = `${short(gu)}<small>${M.plus ? "+" : ""}${v}</small>`;
      if (d.lb._t !== txt) { d.lb.innerHTML = txt; d.lb._t = txt; }
      d.lb.classList.toggle("sel", gu === selected);
      d.lb.style.opacity = selected && gu !== selected ? 0.45 : 1;
    }
  }
  const c = glass.userData.corner, gp = project(c.x, gd.h, c.z);
  glassLabel.style.display = gp.vis ? "" : "none";
  glassLabel.style.transform = `translate(${gp.x.toFixed(1)}px, ${(gp.y - 2).toFixed(1)}px) translate(0, -100%)`;
  const gt = "판 = " + M.refName; if (glassLabel._t !== gt) { glassLabel.textContent = gt; glassLabel._t = gt; }
}

/* ---------- wiring ---------- */
document.querySelectorAll(".controls .seg").forEach(sg => sg.addEventListener("click", e => {
  const b = e.target.closest("button[data-m]"); if (!b) return;
  metric = b.dataset.m;
  if (ok) setTargets(); renderPanels();
}));
document.querySelector(".v3d .views .seg").addEventListener("click", e => { const b = e.target.closest("button"); if (b && ok) { stopSpin(); setView(b.dataset.v); } });
$("spin").addEventListener("change", e => { if (ok) controls.autoRotate = e.target.checked; });
document.getElementById("sites-on").addEventListener("change", () => { if (selectedSite != null) select(null); });
const rowsEl = $("rows");
rowsEl.addEventListener("click", e => { const r = e.target.closest(".row"); if (r) select(r.dataset.gu === selected ? null : r.dataset.gu); });
rowsEl.addEventListener("keydown", e => { if ((e.key === "Enter" || e.key === " ") && e.target.closest(".row")) { e.preventDefault(); const g = e.target.closest(".row").dataset.gu; select(g === selected ? null : g); } });
const mq = matchMedia("(prefers-color-scheme: dark)");
const retheme = () => { applyTheme(); renderPanels(); };
mq.addEventListener && mq.addEventListener("change", retheme);

renderPanels();
if (ok) buildScene();
};
