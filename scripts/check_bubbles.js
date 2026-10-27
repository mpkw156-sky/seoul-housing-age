// 사용법: dist/를 localhost:8765에서 띄운 뒤 `node scripts/check_bubbles.js` (Playwright 필요). 모든 페이지·화면 폭에서 연식이 말풍선이 화면 안에 보이는지 확인합니다.
// Tap every 연식이 on every page at several phone/desktop widths; report bubbles that leave the screen or are hidden.
const { chromium } = require('playwright');
const pages = ['/', '/map/', '/gu/', '/gu/nowon/', '/gu/gangnam/', '/projects/', '/news/', '/data/', '/about/', '/404.html'];
const sizes = (process.env.SIZES || '320,360,375,390,414,768,1024,1280').split(',').map(Number);
(async () => {
  const b = await chromium.launch();
  let bad = 0, checked = 0;
  for (const w of sizes) {
    const ctx = await b.newContext({ viewport: { width: w, height: 800 }, hasTouch: w < 900, isMobile: w < 900 });
    const p = await ctx.newPage();
    await p.route(/googletagmanager|google-analytics|fonts\.g/, r => r.abort());
    for (const u of pages) {
      await p.goto('http://localhost:8765' + u, { waitUntil: 'load' });
      const n = await p.locator('.yk-btn').count();
      for (let k = 0; k < n; k++) {
        const btn = p.locator('.yk-btn').nth(k);
        await btn.scrollIntoViewIfNeeded();
        for (let t = 0; t < 4; t++) {           // every line (long and short)
          if (w < 900) await btn.tap(); else await btn.click();
          await p.waitForTimeout(260);
          const r = await btn.evaluate(el => {
            const say = el.parentElement.querySelector('.yk-say'); const rc = say.getBoundingClientRect();
            const cx = rc.left + rc.width / 2, cy = rc.top + rc.height / 2;
            say.style.pointerEvents = 'auto'; const top = document.elementFromPoint(Math.min(Math.max(cx, 1), innerWidth - 1), Math.min(Math.max(cy, 1), innerHeight - 1));
            const res = { l: Math.round(rc.left), r: Math.round(rc.right), t: Math.round(rc.top), vw: innerWidth, docW: document.documentElement.scrollWidth, text: say.textContent, onTop: !!top && (top === say || say.contains(top)), op: getComputedStyle(say).opacity }; say.style.pointerEvents = ''; return res;
          });
          checked++;
          const issues = [];
          if (r.l < 4) issues.push('left ' + r.l);
          if (r.r > r.vw - 4) issues.push('right ' + r.r + '/' + r.vw);
          if (r.t < 0) issues.push('top ' + r.t);
          if (r.docW > r.vw) issues.push('page overflow ' + r.docW);
          if (!r.onTop) issues.push('covered');
          if (+r.op < 0.9) issues.push('not shown');
          if (issues.length) { bad++; console.log('BAD', w, u, k, t, issues.join(', '), '|', r.text.slice(0, 24)); }
        }
      }
    }
    await ctx.close();
  }
  console.log(`checked ${checked} bubbles, problems ${bad}`);
  await b.close();
})();
