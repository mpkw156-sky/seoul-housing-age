/* 연식이 반응: 눈이 커서를 따라보고, 누르면 폴짝 뛰며 한마디 합니다. 동작 줄이기 설정이면 눈 따라보기와 점프를 끕니다. */
(function () {
  var reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  var fine = window.matchMedia && matchMedia("(hover: hover) and (pointer: fine)").matches;
  var all = Array.prototype.slice.call(document.querySelectorAll(".yk"));
  if (!all.length) return;

  if (!reduce && fine) {
    var px = 0, py = 0, queued = false;
    var look = function () {
      queued = false;
      all.forEach(function (el) {
        var p = el.querySelector(".pupils"); if (!p) return;
        var r = el.getBoundingClientRect();
        if (r.bottom < 0 || r.top > innerHeight) return;
        var cx = r.left + r.width / 2, cy = r.top + r.height * 0.53;
        var dx = px - cx, dy = py - cy, d = Math.hypot(dx, dy) || 1, k = Math.min(1, d / 260);
        p.setAttribute("transform", "translate(" + (dx / d * 2.6 * k).toFixed(2) + " " + (dy / d * 2.2 * k).toFixed(2) + ")");
      });
    };
    addEventListener("pointermove", function (e) { px = e.clientX; py = e.clientY; if (!queued) { queued = true; requestAnimationFrame(look); } }, { passive: true });
  }

  all.forEach(function (el) {
    var btn = el.querySelector(".yk-btn"), say = el.querySelector(".yk-say");
    if (!btn || !say) return;
    var lines = []; try { lines = JSON.parse(btn.getAttribute("data-lines")) || []; } catch (e) {}
    var i = -1, timer = 0;
    btn.addEventListener("click", function () {
      if (!lines.length) return;
      i = (i + 1) % lines.length;
      say.textContent = lines[i];
      el.classList.add("talking");
      if (!reduce) { el.classList.remove("hop"); void el.offsetWidth; el.classList.add("hop"); }
      clearTimeout(timer);
      timer = setTimeout(function () { el.classList.remove("talking"); }, 4200);
    });
  });
})();
