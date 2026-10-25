"""Regenerate src/assets/og.png (social preview). Needs: pip install playwright && playwright install chromium"""
import importlib.util, asyncio, tempfile, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('b',str(ROOT / 'scripts' / 'build.py')); b=importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
ramp=["#f4e2d2","#eabd95","#d98f5c","#b85f2f","#853813"]; br=[20,25,30,40]
def col(v): 
    i=next((k for k,x in enumerate(br) if v<x),4); return ramp[i]
paths="".join(f'<path d="{p["d"]}" fill="{col(b.BY[n]["share30"])}" stroke="#fbfbfa" stroke-width="2"/>' for n,p in b.GEO2D["gu"].items())
S=b.SEOUL
html=f'''<html><head><meta charset="utf-8"><style>body{{margin:0;width:1200px;height:630px;background:#f1f2f1;font-family:"Noto Sans CJK KR","Noto Sans KR",sans-serif;color:#1d1f1f;display:grid;grid-template-columns:600px 600px}}
.l{{padding:64px 0 0 64px;display:grid;align-content:start;gap:18px}} .e{{font-size:22px;color:#6f7472;letter-spacing:.04em}} h1{{margin:0;font-size:66px;line-height:1.1}} .s{{font-size:26px;color:#4f5452;line-height:1.4}}
.n{{display:flex;gap:40px;margin-top:22px}} .n b{{display:block;font-size:56px;font-family:monospace}} .n span{{font-size:20px;color:#6f7472}} .u{{position:absolute;left:64px;bottom:48px;font-size:22px;color:#4f5452}}</style></head>
<body><div class="l"><div class="e">{b.Y1}년 기준 · 매년 갱신</div><h1>서울 주택<br>노후도</h1><div class="s">25개 자치구 주택·아파트가<br>얼마나 오래됐는지 지도로</div>
<div class="n"><div><b>{S["share30"]}%</b><span>30년 이상 주택</span></div><div><b>{S["aptShare30"]}%</b><span>30년 이상 아파트</span></div></div></div>
<div style="display:grid;place-items:center"><svg viewBox="-6 -6 {b.GW+12} {b.GH+12}" width="560">{paths}</svg></div><div class="u">seoul-housing-age.com</div></body></html>'''
tmp = pathlib.Path(tempfile.mkdtemp()) / 'og.html'
tmp.write_text(html, encoding='utf-8')
from playwright.async_api import async_playwright
async def m():
    async with async_playwright() as p:
        br_=await p.chromium.launch(); pg=await br_.new_page(viewport={'width':1200,'height':630})
        await pg.goto(tmp.as_uri()); await pg.screenshot(path=str(ROOT / 'src' / 'assets' / 'og.png')); await br_.close()
asyncio.run(m())
