"""Regenerate src/assets/og.png (social preview, 1200x630) in the '우리 동네 집 나이' style.

Needs: pip install playwright && playwright install chromium
Fonts load from Google Fonts. Offline, set OG_FONT_CSS to a local CSS file with @font-face rules for Jua / IBM Plex Sans KR.
"""
import asyncio, importlib.util, os, pathlib, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("b", str(ROOT / "scripts" / "build.py"))
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)

ramp = ["#f4e2d2", "#eabd95", "#d98f5c", "#b85f2f", "#853813"]; br = [20, 25, 30, 40]
def col(v):
    return ramp[next((k for k, x in enumerate(br) if v < x), 4)]

paths = "".join(f'<path d="{p["d"]}" fill="{col(b.BY[n]["share30"])}" stroke="#fffcf7" stroke-width="2"/>' for n, p in b.GEO2D["gu"].items())
S = b.SEOUL
n10 = b.tens(S["share30"])
houses = "".join(f'<svg viewBox="0 0 24 24" width="40" height="40"><path d="M3 12 L12 4 L21 12 V20 a1.5 1.5 0 0 1 -1.5 1.5 H4.5 A1.5 1.5 0 0 1 3 20 Z" fill="{"#b24a1f" if k < n10 else "#e7dccd"}"/></svg>' for k in range(10))
mascot = b.mascot(150).replace("var(--m-body)", "#fbe3cf").replace("var(--m-roof)", "#e8825a").replace("var(--m-line)", "#6b3a22").replace("var(--m-glass)", "#fffaf3").replace("var(--m-cheek)", "#f2a98a")
font_link = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;500&family=Jua&display=swap">'
if os.environ.get("OG_FONT_CSS"):
    font_link = "<style>" + pathlib.Path(os.environ["OG_FONT_CSS"]).read_text(encoding="utf-8") + "</style>"

html = f"""<html><head><meta charset="utf-8">{font_link}<style>
body{{margin:0;width:1200px;height:630px;background:#f7f1e8;font-family:"IBM Plex Sans KR",sans-serif;color:#2b2420;display:grid;grid-template-columns:720px 480px;position:relative}}
.l{{padding:60px 0 0 64px;display:grid;align-content:start;gap:14px}}
.e{{font-size:24px;color:#74675d}} h1{{margin:0;font-family:Jua,sans-serif;font-weight:400;font-size:76px;line-height:1.1}}
.say{{display:flex;align-items:flex-end;gap:16px;margin-top:10px}}
.bubble{{background:#fffcf7;border:2px solid #e7dccd;border-radius:24px;padding:18px 22px;display:grid;gap:12px}}
.bubble p{{margin:0;font-family:Jua,sans-serif;font-size:32px}} .bubble b{{font-weight:400;color:#b24a1f}}
.hs{{display:flex;gap:4px}} .u{{position:absolute;left:64px;bottom:40px;font-size:24px;color:#594d45}}
</style></head><body>
<div class="l"><div class="e">서울 주택 노후도 · {b.Y1}년 기준</div><h1>우리 동네 집은<br>몇 살일까요?</h1>
<div class="say">{mascot}<div class="bubble"><p>서울 집 10채 중 <b>{n10}채</b>는<br>서른 살이 넘었어요</p><div class="hs">{houses}</div></div></div></div>
<div style="display:grid;place-items:center"><svg viewBox="-6 -6 {b.GW + 12} {b.GH + 12}" width="440">{paths}</svg></div>
<div class="u">seoul-housing-age.com</div></body></html>"""

tmp = pathlib.Path(tempfile.mkdtemp()) / "og.html"
tmp.write_text(html, encoding="utf-8")
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        br_ = await p.chromium.launch(); pg = await br_.new_page(viewport={"width": 1200, "height": 630})
        await pg.goto(tmp.as_uri()); await pg.evaluate("document.fonts.ready"); await pg.wait_for_timeout(300)
        await pg.screenshot(path=str(ROOT / "src" / "assets" / "og.png")); await br_.close()

asyncio.run(main())
