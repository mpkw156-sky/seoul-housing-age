#!/usr/bin/env python3
"""Build the static site into dist/ from data/*.json and src/.

Usage: python scripts/build.py   (stdlib only, Python 3.9+)
"""
from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
import math
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
DATA = ROOT / "data"
OUT = ROOT / "dist"
KST = dt.timezone(dt.timedelta(hours=9))

CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
H = json.loads((DATA / "housing_age.json").read_text(encoding="utf-8"))
GEOJSON = json.loads((DATA / "seoul_gu.geojson").read_text(encoding="utf-8"))
PROJ = json.loads((DATA / "projects.json").read_text(encoding="utf-8"))
NEWS_FILE = DATA / "news.json"
NEWS = json.loads(NEWS_FILE.read_text(encoding="utf-8")) if NEWS_FILE.exists() else {"updated": "", "items": []}

BASE = CFG["base_url"].rstrip("/")
SITE = CFG["site_name"]
TODAY = dt.datetime.now(KST).date()
YEARS = sorted(H["years"])
Y1 = YEARS[-1]
Y0 = str(int(Y1) - 5) if str(int(Y1) - 5) in YEARS else YEARS[0]
GU = H["gu"]
KIND = {"rebuild": "재건축 진행", "redev": "재개발 · 신속통합기획 후보지", "moa": "모아타운"}
KIND_ORDER = ["rebuild", "redev", "moa"]
SYM = {
    "rebuild": '<svg viewBox="0 0 14 14" aria-hidden="true"><rect x="2" y="2" width="10" height="10" rx="1.5" fill="var(--mk-rebuild)"></rect></svg>',
    "redev": '<svg viewBox="0 0 14 14" aria-hidden="true"><circle cx="7" cy="7" r="5.5" fill="var(--mk-redev)"></circle></svg>',
    "moa": '<svg viewBox="0 0 14 14" aria-hidden="true"><path d="M7 1.5 L12.8 12 H1.2 Z" fill="var(--mk-moa)"></path></svg>',
}
LOGO = ('<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="2" y="13" width="5" height="9" rx="1" fill="var(--r1)"></rect>'
        '<rect x="9.5" y="7" width="5" height="15" rx="1" fill="var(--r2)"></rect><rect x="17" y="2" width="5" height="20" rx="1" fill="var(--r4)"></rect></svg>')

esc = html.escape

# 마스코트 '연식이': 안경 쓴 작은 집 (이 사이트용 창작 캐릭터, 2026-10 KIPRIS 동일·유사 상표 없음 확인)
MASCOT_NAME = "연식이"


def mascot(size: int = 96, cls: str = "mascot") -> str:
    return (f'<svg class="{cls}" width="{size}" height="{size}" viewBox="0 0 120 120" aria-hidden="true">'
            '<path d="M14 58 L60 18 L106 58" fill="none" stroke="var(--m-line)" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"></path>'
            '<rect x="78" y="22" width="12" height="22" rx="2" fill="var(--m-roof)" stroke="var(--m-line)" stroke-width="4"></rect>'
            '<path d="M24 54 L60 24 L96 54 V102 a8 8 0 0 1 -8 8 H32 a8 8 0 0 1 -8 -8 Z" fill="var(--m-body)" stroke="var(--m-line)" stroke-width="5" stroke-linejoin="round"></path>'
            '<circle cx="47" cy="70" r="9" fill="var(--m-glass)" stroke="var(--m-line)" stroke-width="4"></circle>'
            '<circle cx="73" cy="70" r="9" fill="var(--m-glass)" stroke="var(--m-line)" stroke-width="4"></circle>'
            '<path d="M56 70 H64" stroke="var(--m-line)" stroke-width="4" stroke-linecap="round"></path>'
            '<circle cx="47" cy="71" r="2.6" fill="var(--m-line)"></circle><circle cx="73" cy="71" r="2.6" fill="var(--m-line)"></circle>'
            '<path d="M50 88 Q60 95 70 88" fill="none" stroke="var(--m-line)" stroke-width="4" stroke-linecap="round"></path>'
            '<circle cx="36" cy="86" r="4.5" fill="var(--m-cheek)"></circle><circle cx="84" cy="86" r="4.5" fill="var(--m-cheek)"></circle>'
            '</svg>')


def tens(share: float) -> int:
    """비율을 '10채 중 몇 채'로 (반올림)."""
    return max(0, min(10, int(share / 10 + 0.5)))


def houses(n_on: int, label: str) -> str:
    one = ('<path d="M3 12 L12 4 L21 12 V20 a1.5 1.5 0 0 1 -1.5 1.5 H4.5 A1.5 1.5 0 0 1 3 20 Z"></path>')
    cells = "".join(f'<svg class="hs{" on" if k < n_on else ""}" viewBox="0 0 24 24" aria-hidden="true">{one}</svg>' for k in range(10))
    return f'<div class="houses" role="img" aria-label="{esc(label)}">{cells}</div>'


def fmt(n: int) -> str:
    return f"{n:,}"


def pct(a: float, b: float) -> float:
    return round(a / b * 100, 1) if b else 0.0


def ym_label(s: str) -> str:
    y, m = s.split("-")
    return f"{y}년 {int(m)}월"


# ---------------------------------------------------------------- metrics
def rec(year: str, i: int):
    tot, at, lt, a20, a30, l20, l30 = H["m"][year][i]
    return dict(tot=tot, at=at, lt=lt, a20=a20, a30=a30, l20=l20, l30=l30)


def metrics_from(r: dict) -> dict:
    return dict(
        total=r["tot"], old30=r["a30"] + r["l30"], share30=pct(r["a30"] + r["l30"], r["tot"]),
        apt=r["at"], apt20=r["a20"], apt30=r["a30"], aptShare30=pct(r["a30"], r["at"]), aptNext=pct(r["a20"], r["at"]),
        lowTotal=r["lt"], lowOld20=r["l20"] + r["l30"], lowOld30=r["l30"],
        low20=pct(r["l20"] + r["l30"], r["lt"]), low30=pct(r["l30"], r["lt"]),
    )


def raw_share30(r: dict) -> float:
    return (r["a30"] + r["l30"]) / r["tot"] * 100 if r["tot"] else 0.0


def seoul_rec(year: str) -> dict:
    keys = ["tot", "at", "lt", "a20", "a30", "l20", "l30"]
    return {k: sum(rec(year, i)[k] for i in range(len(GU))) for k in keys}


ROWS = []
for i, g in enumerate(GU):
    r1, r0 = rec(Y1, i), rec(Y0, i)
    m = metrics_from(r1)
    m.update(gu=g, share30_prev=round(raw_share30(r0), 1), delta=round(raw_share30(r1) - raw_share30(r0), 1))
    ROWS.append(m)
S1, S0 = seoul_rec(Y1), seoul_rec(Y0)
SEOUL = metrics_from(S1)
SEOUL.update(share30_prev=round(raw_share30(S0), 1), delta=round(raw_share30(S1) - raw_share30(S0), 1))
BY = {r["gu"]: r for r in ROWS}
RANK = {r["gu"]: k + 1 for k, r in enumerate(sorted(ROWS, key=lambda r: -r["share30"]))}


# ---------------------------------------------------------------- geography
def rings(geom):
    return [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]


LAT0 = 37.55
KX = math.cos(math.radians(LAT0))
_pts = [p for f in GEOJSON["features"] for poly in rings(f["geometry"]) for r in poly for p in r]
_minx, _maxx = min(p[0] * KX for p in _pts), max(p[0] * KX for p in _pts)
_miny, _maxy = min(-p[1] for p in _pts), max(-p[1] for p in _pts)
GW = 600.0
_s = GW / (_maxx - _minx)
GH = round((_maxy - _miny) * _s, 1)


def proj(lon: float, lat: float):
    return (round((lon * KX - _minx) * _s, 1), round((-lat - _miny) * _s, 1))


GEO2D = {"w": GW, "h": GH, "gu": {}}
GEO3D = {"w": GW, "h": GH, "gu": {}}
SLUG = {}
for f in GEOJSON["features"]:
    name = f["properties"]["name"]
    SLUG[name] = f["properties"]["name_eng"].lower().replace("-gu", "")
    d_parts, polys3d, best = [], [], (0.0, 0.0, 0.0)
    for poly in rings(f["geometry"]):
        rr3 = []
        for k, ring in enumerate(poly):
            q = [proj(*p) for p in ring]
            d_parts.append("M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in q) + "Z")
            if q[0] == q[-1]:
                q = q[:-1]
            rr3.append([c for xy in q for c in xy])
            if k == 0:
                a = sx = sy = 0.0
                for (x1, y1), (x2, y2) in zip(q, q[1:] + q[:1]):
                    c = x1 * y2 - x2 * y1
                    a += c; sx += (x1 + x2) * c; sy += (y1 + y2) * c
                a /= 2
                if a and abs(a) > best[0]:
                    best = (abs(a), sx / (6 * a), sy / (6 * a))
        polys3d.append(rr3)
    cx, cy = round(best[1], 1), round(best[2], 1)
    GEO2D["gu"][name] = {"d": "".join(d_parts), "cx": cx, "cy": cy}
    GEO3D["gu"][name] = {"p": polys3d, "cx": cx, "cy": cy}
assert set(SLUG) == set(GU), "geo names do not match data names"

MARKERS = []
for p in PROJ["items"]:
    x, y = proj(p["lon"], p["lat"])
    MARKERS.append({"t": p["type"], "gu": p["gu"], "name": p["name"], "x": x, "y": y,
                    "items": p["items"] + [f"{p['asOf'].replace('-', '.')} 기준"]})


# ---------------------------------------------------------------- assets
def asset_hash() -> str:
    h = hashlib.sha1()
    for p in sorted((SRC / "assets").rglob("*")):
        if p.is_file():
            h.update(p.read_bytes())
    return h.hexdigest()[:8]


VER = asset_hash()


def jdump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def ad(slot: str) -> str:
    client, sid = CFG.get("adsense_client", ""), CFG.get("adsense_slots", {}).get(slot, "")
    if client and sid:
        return (f'<aside class="slot" aria-label="광고"><span class="slot-label">광고</span>'
                f'<ins class="adsbygoogle" style="display:block;width:100%" data-ad-client="{esc(client)}" data-ad-slot="{esc(sid)}" '
                f'data-ad-format="auto" data-full-width-responsive="true"></ins>'
                f'<script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script></aside>')
    unit = CFG.get("kakao_adfit_units", {}).get(slot, "")
    if unit:
        return (f'<aside class="slot" aria-label="광고"><span class="slot-label">광고</span>'
                f'<ins class="kakao_ad_area" style="display:none;" data-ad-unit="{esc(unit)}" data-ad-width="320" data-ad-height="100"></ins>'
                f'<script async src="https://t1.daumcdn.net/kas/static/ba.min.js"></script></aside>')
    return ""


NAV = [("/", "지도"), ("/3d/", "3D"), ("/gu/", "자치구"), ("/projects/", "정비사업"), ("/news/", "뉴스"), ("/methodology/", "방법론"), ("/data/", "데이터")]


def layout(path: str, title: str, desc: str, body: str, *, active: str = "", css=(), js=(), data=None, geo=None,
           jsonld=None, noindex: bool = False) -> None:
    url = f"{BASE}/{path}"
    head_css = "".join(f'<link rel="stylesheet" href="/assets/{c}?v={VER}">' for c in ("site.css", *css))
    ads_head = ""
    if CFG.get("adsense_client"):
        ads_head = (f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={esc(CFG["adsense_client"])}" '
                    f'crossorigin="anonymous"></script>')
    verify = ""
    if CFG.get("google_site_verification"):
        verify += f'<meta name="google-site-verification" content="{esc(CFG["google_site_verification"])}">'
    if CFG.get("naver_site_verification"):
        verify += f'<meta name="naver-site-verification" content="{esc(CFG["naver_site_verification"])}">'
    ga = ""
    gid = CFG.get("ga4_measurement_id", "")
    if gid and re.fullmatch(r"G-[A-Z0-9]+", gid):
        ga = (f'<script async src="https://www.googletagmanager.com/gtag/js?id={gid}"></script>'
              "<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}"
              f"gtag('js',new Date());gtag('config','{gid}',{{allow_google_signals:false,allow_ad_personalization_signals:false}});</script>")
    ld = f'<script type="application/ld+json">{jdump(jsonld)}</script>' if jsonld else ""
    cur = ' aria-current="page"'
    nav = "".join(f'<a href="{h}"{cur if h == active else ""}>{t}</a>' for h, t in NAV)
    datas = ""
    if data is not None:
        datas += f'<script id="site-data" type="application/json">{jdump(data)}</script>'
    if geo is not None:
        datas += f'<script id="geo-data" type="application/json">{jdump(geo)}</script>'
    scripts = "".join(f'<script src="/assets/{s}?v={VER}"></script>' for s in js)
    contact = (f' · 문의 <a href="mailto:{esc(CFG["contact_email"])}">{esc(CFG["contact_email"])}</a>'
               if CFG.get("contact_email") else "")
    doc = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
{verify}
{'<meta name="robots" content="noindex">' if noindex else f'<link rel="canonical" href="{url}">'}
<meta property="og:type" content="website">
<meta property="og:site_name" content="{esc(SITE)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{BASE}/assets/og.png">
<meta property="og:locale" content="ko_KR">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#fffcf7" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#231d19" media="(prefers-color-scheme: dark)">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@500&family=IBM+Plex+Sans+KR:wght@400;500;700&family=Jua&display=swap">
{head_css}
{ga}
{ads_head}
{ld}
</head>
<body>
<a class="skip" href="#main">본문 바로가기</a>
<header class="site-head gutter"><div class="inner">
<a class="brand" href="/">{mascot(30, "brand-mark")}{esc(SITE)}</a>
<nav class="site-nav" aria-label="주요 메뉴">{nav}</nav>
</div></header>
<main id="main" class="wrap gutter">
{body}
</main>
<footer class="site-foot gutter"><div class="inner">
<p>자료: 국가데이터처 주택총조사 (서울 데이터 허브 「서울시 노후기간별 주택현황 통계」, 「서울시 건축연도별 주택현황 통계」, 공공누리 제1유형), {Y1}년 기준. 정비사업 현황은 언론 보도·서울시 발표 기준({ym_label(PROJ['asOf'])})입니다.</p>
<p>이 사이트는 공공 통계로 집 나이를 보여주는 정보 서비스예요. 투자 권유나 자문이 아니에요. 노후도는 주택 호수로 계산한 근사치라 법정 노후도와 다를 수 있어요.</p>
<div class="links"><a href="/news/">보도자료 모음</a><a href="/about/">소개·출처</a><a href="/methodology/">방법론</a><a href="/data/">데이터 출처</a><a href="/privacy/">개인정보처리방침</a></div>
<p>© {TODAY.year} {esc(CFG.get('operator', SITE))}{contact} · 마지막 빌드 {TODAY.isoformat()}</p>
</div></footer>
{datas}
{scripts}
</body>
</html>
"""
    target = OUT / path / "index.html" if not path.endswith(".html") else OUT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(doc, encoding="utf-8")
    if not noindex:
        SITEMAP.append(url)


SITEMAP: list[str] = []


def tpl(name: str, **kw) -> str:
    s = (SRC / "templates" / name).read_text(encoding="utf-8")
    for k, v in kw.items():
        s = s.replace("{{" + k + "}}", str(v))
    assert "{{" not in s, f"unfilled placeholder in {name}"
    return s


# ---------------------------------------------------------------- charts (static SVG)
def nice_max(v: float, step: float) -> float:
    return max(step, math.ceil(v / step) * step)


def trend_svg(gu: str) -> str:
    i = GU.index(gu)
    ys = YEARS
    g = [raw_share30(rec(y, i)) for y in ys]
    s = [raw_share30(seoul_rec(y)) for y in ys]
    W, Hh, ml, mr, mt, mb = 600, 250, 44, 104, 14, 30
    top = nice_max(max(g + s) * 1.08, 10)
    step = 10 if top <= 60 else 20
    X = lambda k: ml + k * (W - ml - mr) / (len(ys) - 1)
    Y = lambda v: mt + (1 - v / top) * (Hh - mt - mb)
    grid = "".join(f'<line x1="{ml}" x2="{W - mr}" y1="{Y(v):.1f}" y2="{Y(v):.1f}"></line>' for v in range(0, int(top) + 1, step))
    yt = "".join(f'<text x="{ml - 8}" y="{Y(v) + 4:.1f}" text-anchor="end">{v}%</text>' for v in range(0, int(top) + 1, step))
    xt = "".join(f'<text x="{X(k):.1f}" y="{Hh - 8}" text-anchor="middle">{y}</text>'
                 for k, y in enumerate(ys) if k % 2 == 0 or k == len(ys) - 1)
    pl = lambda vals: " ".join(f"{X(k):.1f},{Y(v):.1f}" for k, v in enumerate(vals))
    dots = "".join(f'<circle class="dot-gu" cx="{X(k):.1f}" cy="{Y(v):.1f}" r="3.5"><title>{ys[k]}년 {v:.1f}%</title></circle>'
                   for k, v in enumerate(g))
    yg, ys_ = Y(g[-1]), Y(s[-1])
    if abs(yg - ys_) < 16:
        mid = (yg + ys_) / 2
        yg, ys_ = (mid - 8, mid + 8) if g[-1] >= s[-1] else (mid + 8, mid - 8)
    xe = X(len(ys) - 1) + 8
    return f"""<svg viewBox="0 0 {W} {Hh}" role="img" aria-label="{esc(gu)}와 서울 평균의 연도별 30년 이상 주택 비율">
<g class="grid">{grid}</g><g class="axis">{yt}{xt}</g>
<polyline class="line-seoul" points="{pl(s)}"></polyline>
<polyline class="line-gu" points="{pl(g)}"></polyline>{dots}
<text class="val" x="{xe:.1f}" y="{yg + 4:.1f}">{esc(gu)} {g[-1]:.1f}%</text>
<text class="lbl" x="{xe:.1f}" y="{ys_ + 4:.1f}">서울 {s[-1]:.1f}%</text>
</svg>"""


BAND_NAMES = {"~1979": "~1979", "1980s": "1980년대", "1990s": "1990년대", "2000-04": "2000–04", "2005-09": "2005–09",
              "2010-14": "2010–14", "2015-19": "2015–19", "2020-": "2020–"}
BAND_RANGE = {"~1979": (1960, 1979), "1980s": (1980, 1989), "1990s": (1990, 1999), "2000-04": (2000, 2004),
              "2005-09": (2005, 2009), "2010-14": (2010, 2014), "2015-19": (2015, 2019), "2020-": (2020, int(H["bandsYear"]))}


def bands_svg(gu: str) -> str:
    i = GU.index(gu)
    A, L = H["bands"][i]
    labels = H["bandLabels"]
    W, Hh, ml, mr, mt, mb = 600, 260, 60, 8, 26, 30
    top = max(A + L) * 1.1 or 1
    mag = 10 ** max(0, int(math.log10(top)) - 0)
    stepv = mag if top / mag <= 5 else mag * 2
    if top / stepv < 3:
        stepv /= 2
    top = nice_max(top, stepv)
    n = len(labels)
    gw = (W - ml - mr) / n
    bw = gw * 0.34
    Y = lambda v: mt + (1 - v / top) * (Hh - mt - mb)
    grid, yt = "", ""
    v = 0.0
    while v <= top + 1e-9:
        grid += f'<line x1="{ml}" x2="{W - mr}" y1="{Y(v):.1f}" y2="{Y(v):.1f}"></line>'
        yt += f'<text x="{ml - 8}" y="{Y(v) + 4:.1f}" text-anchor="end">{fmt(int(v))}</text>'
        v += stepv
    bars, xt = "", ""
    for k, lab in enumerate(labels):
        x0 = ml + k * gw + gw * 0.14
        for j, (vals, cls, nm) in enumerate(((A, "bar-apt", "아파트"), (L, "bar-low", "저층 주택"))):
            val = vals[k]
            x = x0 + j * (bw + 2)
            h = max(0.0, Y(0) - Y(val))
            r = min(4.0, h / 2, bw / 2)
            yb, yt_ = Y(0), Y(val)
            path = (f"M{x:.1f},{yb:.1f}V{yt_ + r:.1f}Q{x:.1f},{yt_:.1f} {x + r:.1f},{yt_:.1f}H{x + bw - r:.1f}"
                    f"Q{x + bw:.1f},{yt_:.1f} {x + bw:.1f},{yt_ + r:.1f}V{yb:.1f}Z") if h > 0 else ""
            if path:
                bars += f'<path class="{cls}" d="{path}"><title>{BAND_NAMES.get(lab, lab)} {nm} {fmt(val)}호</title></path>'
        xt += f'<text x="{ml + k * gw + gw / 2:.1f}" y="{Hh - 10}" text-anchor="middle">{BAND_NAMES.get(lab, lab)}</text>'
    cut = int(Y1) - 30
    kpos = None
    for k, lab in enumerate(labels):
        a, b = BAND_RANGE.get(lab, (0, 0))
        if a <= cut <= b:
            kpos = k + (cut - a + 1) / (b - a + 1) if k else k + 1
            break
    marker = ""
    if kpos is not None:
        xm = ml + kpos * gw
        marker = (f'<line x1="{xm:.1f}" x2="{xm:.1f}" y1="{mt - 6}" y2="{Y(0):.1f}" stroke="var(--ink-2)" stroke-width="1.5" stroke-dasharray="4 3"></line>'
                  f'<text class="lbl" x="{xm + 6:.1f}" y="{mt + 2}" text-anchor="start">점선 왼쪽: 30년 이상 ({cut}년 이전 준공)</text>')
    return f"""<svg viewBox="0 0 {W} {Hh}" role="img" aria-label="{esc(gu)} 지은 연도별 주택 수">
<g class="grid">{grid}</g><g class="axis">{yt}{xt}</g>{bars}{marker}
</svg>"""


def locator_svg(gu: str) -> str:
    paths = "".join(f'<path class="g{" on" if n == gu else ""}" d="{p["d"]}"><title>{esc(n)}</title></path>' for n, p in GEO2D["gu"].items())
    c = GEO2D["gu"][gu]
    return (f'<svg viewBox="-6 -6 {GW + 12} {GH + 12}" role="img" aria-label="서울 안에서 {esc(gu)}의 위치">{paths}'
            f'<text x="{c["cx"]}" y="{c["cy"] - 14}" text-anchor="middle" style="font-weight:700;fill:var(--ink)">{esc(gu)}</text></svg>')


# ---------------------------------------------------------------- pages
def gu_link(g: str) -> str:
    return f"/gu/{SLUG[g]}/"


def map_payload() -> dict:
    keep = ["gu", "total", "old30", "share30", "share30_prev", "delta", "apt", "apt30", "aptShare30", "aptNext",
            "lowTotal", "lowOld30", "low20", "low30"]
    return {"y0": Y0, "y1": Y1, "rows": [{k: r[k] for k in keep} for r in ROWS],
            "seoul": {k: SEOUL[k] for k in ["share30", "share30_prev", "aptShare30", "aptNext", "low20", "total", "old30"]},
            "markers": MARKERS}


def home_notes() -> str:
    by_apt = sorted(ROWS, key=lambda r: -r["aptShare30"])
    by_low = sorted(ROWS, key=lambda r: -r["low20"])
    by_d = sorted(ROWS, key=lambda r: -r["delta"])
    by_next = sorted(ROWS, key=lambda r: -r["aptNext"])
    over = [r for r in ROWS if r["low20"] >= 60]
    a1, a2 = by_apt[0], by_apt[1]
    notes = [
        (f"아파트가 가장 나이 든 동네는 {a1['gu']}",
         f"{a1['gu']} 아파트 {fmt(a1['apt'])}호 중 {fmt(a1['apt30'])}호({a1['aptShare30']}%)가 서른 살을 넘겼어요. "
         f"그다음은 {a2['gu']}({a2['aptShare30']}%)예요. 서울 전체로 보면 아파트 {SEOUL['aptShare30']}%가 서른 살이 넘었어요."),
        (f"저층 주택은 {len(over)}개 구가 60%를 넘어요",
         f"단독·다세대·연립 같은 저층 주택 가운데 스무 살 넘은 집은 서울 전체 {SEOUL['low20']}%예요. "
         + ", ".join(r["gu"] + " " + str(r["low20"]) + "%" for r in by_low[:3]) + " 순으로 많아요."),
        (f"5년 새 가장 빨리 나이 든 곳은 {by_d[0]['gu']}",
         f"{by_d[0]['gu']}는 서른 살 넘은 집 비율이 {Y0}년 {by_d[0]['share30_prev']}%에서 {Y1}년 {by_d[0]['share30']}%로 "
         f"{by_d[0]['delta']:+.1f}%p 늘었어요. 곧 서른 살이 되는 20대 아파트는 "
         + ", ".join(r["gu"] + " " + str(r["aptNext"]) + "%" for r in by_next[:3]) + " 순으로 많아요."),
    ]
    return "\n".join(f'<div class="note"><h3>{esc(t)}</h3><p>{esc(p)}</p></div>' for t, p in notes)


def build_home():
    links = "\n".join(f'<a href="{gu_link(r["gu"])}">{esc(r["gu"])}<span>{r["share30"]}%</span></a>'
                      for r in sorted(ROWS, key=lambda r: -r["share30"]))
    body = tpl("home.html", Y1=Y1, NOTES=home_notes(), GU_LINKS=links, AD_SLOT=ad("home"),
               PROJECTS_ASOF=ym_label(PROJ["asOf"]), NEWS=home_news(), MASCOT=mascot(112), MASCOT_NAME=MASCOT_NAME,
               TENS=tens(SEOUL["share30"]), HOUSES=houses(tens(SEOUL["share30"]), f"서울 집 10채 중 {tens(SEOUL['share30'])}채가 서른 살 이상"),
               APT_TENS=tens(SEOUL["aptShare30"]))
    jsonld = {"@context": "https://schema.org", "@type": "WebSite", "name": SITE, "url": BASE + "/",
              "inLanguage": "ko", "description": CFG["site_tagline"]}
    layout("", f"{SITE} 지도 – 서울 25개 자치구 주택·아파트 노후도 ({Y1})",
           f"서울 25개 자치구의 30년 이상 노후 주택 비율을 지도로 봅니다. {Y1}년 서울 전체 {SEOUL['share30']}%, "
           f"아파트 {SEOUL['aptShare30']}%. 아파트와 단독·다세대 주택을 나눠 매년 갱신합니다.",
           body, active="/", css=("map2d.css",), js=("map2d.js",), data=map_payload(), geo=GEO2D, jsonld=jsonld)


def build_3d():
    body = tpl("3d.html", Y1=Y1)
    layout("3d/", f"서울 노후도 3D – 자치구별 주택 노후도를 입체로 ({Y1})",
           "서울 25개 자치구를 노후 주택 비율만큼 솟은 3D 기둥으로 보여줍니다. 재개발 노후도 기준 60%와 서울 평균을 반투명 판으로 표시합니다.",
           body, active="/3d/", css=("map3d.css",), js=("vendor/three.min.js", "vendor/OrbitControls.js", "map3d.js"),
           data=map_payload(), geo=GEO3D)


def stat(k: str, v: str, s: str) -> str:
    return f'<div class="stat"><span class="k">{k}</span><span class="v">{v}</span><span class="s">{s}</span></div>'


def project_card(p: dict, show_gu: bool = True) -> str:
    gu = f' · <a href="{gu_link(p["gu"])}">{esc(p["gu"])}</a>' if show_gu else ""
    items = "".join(f"<li>{esc(x)}</li>" for x in p["items"])
    src = " · ".join(f'<a href="{esc(s["url"])}" rel="noopener" target="_blank">{esc(s["title"])}</a>' for s in p["sources"])
    return (f'<article class="project"><span class="kind">{SYM[p["type"]]}{KIND[p["type"]]}</span>'
            f'<b>{esc(p["name"])}{gu}</b><ul>{items}</ul>'
            f'<span class="meta">{ym_label(p["asOf"])} 기준 · 출처: {src}</span></article>')


def build_gu_pages():
    order = sorted(ROWS, key=lambda r: -r["share30"])
    for k, r in enumerate(order):
        g, i = r["gu"], GU.index(r["gu"])
        rk = RANK[g]
        cmp_ = "많아요" if r["share30"] > SEOUL["share30"] else "적어요"
        low_cmp = "넘어요" if r["low20"] >= 60 else "밑돌아요"
        dverb = "늘었어요" if r["delta"] >= 0 else "줄었어요"
        n10 = tens(r["share30"])
        paras = [
            f"{g} 집 {fmt(r['total'])}호 가운데 서른 살(준공 30년)이 넘은 집은 {fmt(r['old30'])}호({r['share30']}%)예요. "
            + ("서울 25개 자치구 중 가장 많아요. " if rk == 1 else f"서울 25개 자치구 중 {rk}번째로 많아요. ") + f"서울 평균({SEOUL['share30']}%)보다 {cmp_}.",
            f"아파트는 {fmt(r['apt'])}호 중 {fmt(r['apt30'])}호({r['aptShare30']}%)가 재건축 연한인 서른 살을 넘겼어요. "
            f"20대 아파트도 {fmt(r['apt20'])}호({r['aptNext']}%) 있어서, 10년 안에 차례로 서른 살이 돼요.",
            f"단독·다세대·연립 같은 저층 주택은 {fmt(r['lowTotal'])}호이고, 이 중 {r['low20']}%가 스무 살을 넘었어요. "
            f"구 평균으로는 재개발 노후도 기준선(60%)을 {low_cmp}. 실제 정비구역 지정은 블록 단위 노후도와 접도율 등으로 따져요.",
            f"5년 전인 {Y0}년에는 서른 살 넘은 집이 {r['share30_prev']}%였고, {Y1}년까지 {abs(r['delta']):.1f}%p {dverb}.",
        ]
        stats = "".join([
            stat("서른 살 넘은 집", f"{r['share30']}%", f"서울 {rk}위 / 25 · 평균 {SEOUL['share30']}%"),
            stat("서른 살 넘은 아파트", f"{r['aptShare30']}%", f"{fmt(r['apt30'])}호 / {fmt(r['apt'])}호"),
            stat("스무 살 넘은 저층 주택", f"{r['low20']}%", "재개발 노후도 기준 60%"),
            stat(f"5년 새 변화", f"{r['delta']:+.1f}%p", f"{Y0}년 {r['share30_prev']}% → {r['share30']}%"),
        ])
        projs = [p for p in PROJ["items"] if p["gu"] == g]
        proj_html = ""
        if projs:
            proj_html = (f'<section class="projects" aria-label="정비사업 진행 현황"><h2>정비사업이 진행 중인 동네</h2>'
                         + "".join(project_card(p, show_gu=False) for p in projs)
                         + f'<p class="crumbs">전체 목록은 <a href="/projects/">정비사업 현황</a>에 있어요.</p></section>')
        rows_html = ""
        for y in reversed(YEARS):
            mm = metrics_from(rec(y, i))
            rows_html += (f"<tr><td>{y}</td><td>{fmt(mm['total'])}</td><td>{fmt(mm['old30'])}</td><td>{mm['share30']}%</td>"
                          f"<td>{mm['aptShare30']}%</td><td>{mm['aptNext']}%</td><td>{mm['low20']}%</td></tr>")
        prev_g = order[k - 1]["gu"] if k > 0 else None
        next_g = order[k + 1]["gu"] if k + 1 < len(order) else None
        pager = '<nav class="pager" aria-label="다른 자치구">'
        pager += f'<a href="{gu_link(prev_g)}">← {esc(prev_g)} ({RANK[prev_g]}위)</a>' if prev_g else "<span></span>"
        pager += '<a href="/gu/">전체 자치구</a>'
        pager += f'<a href="{gu_link(next_g)}">{esc(next_g)} ({RANK[next_g]}위) →</a>' if next_g else "<span></span>"
        pager += "</nav>"
        body = f"""
<nav class="crumbs" aria-label="현재 위치"><a href="/">지도</a> › <a href="/gu/">자치구</a> › {esc(g)}</nav>
<header class="page-head">
  <div class="eyebrow">{esc(g)} 주택 노후도 · {Y1}년 기준 · 25개 구 중 {rk}위</div>
  <h1>{esc(g)} 집은 몇 살일까요?</h1>
</header>
<section class="hello" aria-label="한눈에 보기">
  {mascot(96)}
  <div class="bubble">
    <span class="who">{MASCOT_NAME}가 알려 드려요</span>
    <p class="say">{esc(g)} 집 10채 중 <b>{n10}채</b>는 서른 살이 넘었어요.</p>
    {houses(n10, f"{g} 집 10채 중 {n10}채가 서른 살 이상")}
    <p class="small">{esc(paras[0])}</p>
  </div>
</section>
<div class="statrow">{stats}</div>
<div class="gu-grid">
  <section class="card summary" aria-label="요약">{''.join(f'<p>{esc(p)}</p>' for p in paras[1:])}</section>
  <section class="card locator" aria-label="위치">{locator_svg(g)}</section>
</div>
<section class="card chart" aria-label="연도별 추이">
  <h2>서른 살 넘은 집, 해마다 얼마나 늘었을까요?</h2>
  <div class="chart-legend"><span><i style="background:var(--accent)"></i>{esc(g)}</span><span><i style="background:var(--seoul)"></i>서울 전체 (점선)</span></div>
  <div class="tablewrap">{trend_svg(g)}</div>
</section>
<section class="card chart" aria-label="지은 연도별 주택 수">
  <h2>언제 지은 집이 많을까요? ({H['bandsYear']}년)</h2>
  <div class="chart-legend"><span><i class="box" style="background:var(--r3)"></i>아파트</span><span><i class="box" style="background:var(--r1)"></i>단독·다세대·연립 등 저층 주택</span></div>
  <div class="tablewrap">{bands_svg(g)}</div>
</section>
{ad("gu")}
{proj_html}
<section class="card" aria-label="연도별 수치">
  <h2>연도별 수치</h2>
  <div class="tablewrap"><table class="data">
    <thead><tr><th>연도</th><th>전체 주택(호)</th><th>30년 이상(호)</th><th>30년 이상 비율</th><th>아파트 30년+</th><th>아파트 20~30년</th><th>저층 20년+</th></tr></thead>
    <tbody>{rows_html}</tbody>
  </table></div>
</section>
{pager}
"""
        layout(f"gu/{SLUG[g]}/", f"{g} 주택 노후도 {Y1} – 30년 이상 {r['share30']}% · 아파트 {r['aptShare30']}%",
               f"{g} 주택 {fmt(r['total'])}호 중 30년 이상 {r['share30']}%(서울 {rk}위). 아파트 30년 이상 {r['aptShare30']}%, "
               f"저층 주택 20년 이상 {r['low20']}%. {Y0}년부터의 추이와 지은 연도별 주택 수.",
               body, active="/gu/")


def build_gu_index():
    rows = "".join(
        f'<tr><td><a href="{gu_link(r["gu"])}">{esc(r["gu"])}</a></td><td>{fmt(r["total"])}</td><td>{r["share30"]}%</td>'
        f'<td>{r["aptShare30"]}%</td><td>{r["aptNext"]}%</td><td>{r["low20"]}%</td><td>{r["delta"]:+.1f}%p</td></tr>'
        for r in sorted(ROWS, key=lambda r: -r["share30"]))
    s = SEOUL
    rows += (f'<tr class="seoul"><td>서울 전체</td><td>{fmt(s["total"])}</td><td>{s["share30"]}%</td><td>{s["aptShare30"]}%</td>'
             f'<td>{s["aptNext"]}%</td><td>{s["low20"]}%</td><td>{s["delta"]:+.1f}%p</td></tr>')
    body = f"""
<header class="page-head">
  <div class="eyebrow">자치구별 주택 노후도 · {Y1}년 기준 · 서른 살 넘은 집이 많은 순</div>
  <h1>25개 구 집 나이 한눈에 보기</h1>
  <p class="lede">25개 자치구의 집 나이를 한 표에 모았어요. 구 이름을 누르면 해마다 어떻게 바뀌었는지, 언제 지은 집이 많은지 볼 수 있어요.</p>
</header>
<section class="card"><div class="tablewrap"><table class="data">
<thead><tr><th>자치구</th><th>전체 주택(호)</th><th>30살+ 집</th><th>30살+ 아파트</th><th>20대 아파트</th><th>20살+ 저층</th><th>5년 새 변화</th></tr></thead>
<tbody>{rows}</tbody></table></div></section>
"""
    layout("gu/", f"자치구별 주택 노후도 순위 {Y1} – 서울 25개 구", f"서울 25개 자치구의 30년 이상 주택 비율, 아파트·저층 주택 노후도, 5년간 변화를 한 표로 비교합니다 ({Y1}년 기준).",
           body, active="/gu/")


def build_projects():
    groups = ""
    for t in KIND_ORDER:
        items = [p for p in PROJ["items"] if p["type"] == t]
        if items:
            groups += f'<section class="projects"><h2>{KIND[t]} · {len(items)}곳</h2>' + "".join(project_card(p) for p in items) + "</section>"
    body = f"""
<header class="page-head">
  <div class="eyebrow">정비사업 진행 현황 · {ym_label(PROJ['asOf'])} 기준 · {len(PROJ['items'])}곳</div>
  <h1>새집으로 바뀌는 중인 동네</h1>
  <p class="lede">재건축·재개발·모아타운이 진행 중인 동네를 모았어요. 언론 보도와 서울시 발표를 바탕으로 정리했고, 위치는 동 단위 대략값이에요. 기준월 이후에 단계가 바뀌었을 수 있으니 항목마다 붙은 출처를 확인해 주세요. 지도에도 같은 동네를 기호로 표시했어요.</p>
</header>
{groups}
"""
    layout("projects/", f"서울 정비사업 진행 현황 – 재건축·재개발·모아타운 ({ym_label(PROJ['asOf'])})",
           "서울 주요 재건축 단지, 신속통합기획 재개발 후보지, 모아타운의 진행 단계를 기준월과 출처와 함께 정리했습니다.",
           body, active="/projects/")


# ---------------------------------------------------------------- news (official press releases: title + link only)
WEEKDAY = "월화수목금토일"
NEWS_SOURCES = [
    ("서울특별시 보도자료", "https://www.seoul.go.kr/news/news_report.do"),
    ("국토교통부 보도자료", "https://www.molit.go.kr/USR/NEWS/m_71/lst.jsp"),
]


def day_label(iso: str) -> str:
    d = dt.date.fromisoformat(iso)
    return f"{d.year}년 {d.month}월 {d.day}일 ({WEEKDAY[d.weekday()]})"


def news_item(it: dict) -> str:
    meta = " · ".join(x for x in (it["org"], it.get("dept", ""), it["date"].replace("-", ".") + (" " + it["time"] if it.get("time") else "")) if x)
    return (f'<li class="news-item"><a href="{esc(it["url"])}" target="_blank" rel="noopener nofollow">{esc(it["title"])}'
            f'<span class="ext" aria-label="새 창에서 원문 열기">↗</span></a><span class="meta">{esc(meta)}</span></li>')


def home_news() -> str:
    items = NEWS["items"][:3]
    if not items:
        return ""
    return (f'<section class="news-home" aria-label="최근 보도자료"><div class="news-home-head"><h2 class="sec">오늘의 서울 집 소식</h2>'
            f'<a href="/news/">전체 보기 →</a></div><ul class="news-list">{"".join(news_item(i) for i in items)}</ul>'
            f'<p class="news-note">서울시·국토교통부가 발표한 보도자료의 제목과 원문 링크예요.</p></section>')


def build_news():
    days: dict[str, list] = {}
    for it in NEWS["items"]:
        days.setdefault(it["date"], []).append(it)
    keys = sorted(days, reverse=True)[:45]
    if keys:
        groups = "".join(f'<section class="news-day"><h2 class="sec">{day_label(k)}</h2><ul class="news-list">'
                         + "".join(news_item(i) for i in days[k]) + "</ul></section>" for k in keys)
    else:
        groups = f'<section class="hello">{mascot(80)}<div class="bubble"><p class="say">아직 모은 소식이 없어요.</p><p class="small">매일 낮 12시, 저녁 7시쯤 새 보도자료를 찾아 채워요.</p></div></section>'
    upd = NEWS.get("updated", "")
    upd_txt = f"{upd[:10].replace('-', '.')} {upd[11:16]} 갱신" if upd else "매일 갱신"
    srcs = "".join(f'<li><a href="{esc(u)}" target="_blank" rel="noopener">{esc(t)}</a></li>' for t, u in NEWS_SOURCES)
    body = f"""
<header class="page-head">
  <div class="eyebrow">서울 주택·부동산 보도자료 · {upd_txt} · 하루 최대 3건</div>
  <h1>오늘의 서울 집 소식</h1>
  <p class="lede">서울특별시와 국토교통부가 낸 보도자료 가운데 서울의 주택·정비사업·부동산 소식을 매일 골라 제목과 원문 링크로 모았어요. 내용은 제목을 눌러 각 기관 누리집에서 확인해 주세요.</p>
</header>
<div class="news-days">{groups}</div>
<div class="prose news-about">
  <h2>모으는 기준</h2>
  <ul>
    <li>출처: {srcs.replace('<li>', '').replace('</li>', ', ').rstrip(', ')}. 언론사 기사는 싣지 않아요.</li>
    <li>제목에 재건축·재개발·정비사업·모아타운·신속통합기획·주택공급·전세·실거래 같은 말이 들어간 보도자료를 자동으로 고르고, 하루 최대 3건까지 실어요. 발표가 적은 날이나 주말에는 1건 이하일 수 있어요.</li>
    <li>제목, 발표 기관·부서, 날짜, 원문 링크만 보여 줘요. 본문·요약·사진·첨부파일은 옮기지 않고, 제목 앞의 "(석간)", "(엠바고…)" 같은 배포 표시는 빼요.</li>
    <li>고르는 방식이 자동이라 관련이 적은 자료가 섞이거나 중요한 자료가 빠질 수 있어요. 최근 180일치만 보관해요.</li>
    <li>이 목록은 정보 제공용이며 투자 권유나 자문이 아니에요. 정책 내용은 꼭 원문으로 확인해 주세요.</li>
  </ul>
</div>
"""
    layout("news/", f"서울 주택·부동산 보도자료 모음 – {SITE}",
           "서울시·국토교통부의 서울 주택·재건축·재개발·부동산 관련 보도자료를 매일 골라 제목과 원문 링크로 모았습니다.",
           body, active="/news/")


def build_methodology():
    body = f"""
<header class="page-head">
  <div class="eyebrow">방법론 · 데이터와 계산 방법</div>
  <h1>집 나이는 이렇게 셌어요</h1>
  <p class="lede">이 사이트의 모든 숫자가 어디서 왔고 어떻게 계산했는지 설명해요. 사이트에서 말하는 '서른 살'은 준공 30년, '스무 살'은 준공 20년을 뜻해요.</p>
</header>
<div class="prose">
  <h2>원자료</h2>
  <p>국가데이터처 주택총조사를 서울특별시가 서울 데이터 허브에 공개한 두 통계를 써요. 둘 다 공공누리 제1유형(출처를 밝히면 상업적 이용·변경 가능)이에요.</p>
  <ul>
    <li>「서울시 노후기간별 주택현황 통계」: 자치구·주택종류별로 지은 지 20~30년 미만, 30년 이상 된 주택 수</li>
    <li>「서울시 건축연도별 주택현황 통계」: 자치구·주택종류·건축연도별 주택 수. 전체 주택 수와 지은 연도 분포에 씁니다.</li>
  </ul>
  <p>지금 반영된 기간은 {YEARS[0]}~{Y1}년이에요. 개인정보 보호를 위해 5호 미만이라 비공개(x)로 처리된 칸은 0으로 계산했어요.</p>
  <h2>지표 정의</h2>
  <ul>
    <li><b>서른 살 넘은 집 (30년 이상 주택 비율)</b> = 30년 이상 된 주택 ÷ 전체 주택</li>
    <li><b>서른 살 넘은 아파트</b> = 30년 이상 된 아파트 ÷ 전체 아파트. 재건축 연한(준공 30년)을 넘긴 아파트의 비율이에요.</li>
    <li><b>20대 아파트</b> = 20~30년 된 아파트 ÷ 전체 아파트. 10년 안에 서른 살이 되는 아파트예요.</li>
    <li><b>스무 살 넘은 저층 주택</b> = 20년 이상 된 단독·다세대·연립·비주거용 건물 내 주택 ÷ 전체 저층 주택</li>
    <li><b>5년 새 늘어난 폭</b> = {Y1}년 서른 살 넘은 집 비율 − {Y0}년 비율 (%p)</li>
    <li><b>'10채 중 몇 채'</b> = 위 비율을 10으로 나눠 반올림한 값이에요. 쉽게 읽으라고 붙인 표현이라 정확한 값은 % 숫자를 봐 주세요.</li>
  </ul>
  <h2>법정 노후도와 다른 점</h2>
  <p>재개발 정비구역 지정에 쓰는 법정 노후도는 건축물 <b>동수</b> 기준이고, 구조에 따라 노후 판정 연수(20~30년)가 달라요. 이 사이트의 비율은 주택 <b>호수</b> 기준이라, 다세대 한 동에 여러 호가 있는 경우 등에서 차이가 나요. 또 실제 구역 지정은 블록 단위의 노후도, 접도율, 과소필지, 주민 동의율로 판단하니까, 구 평균은 흐름을 보는 참고값으로 봐 주세요.</p>
  <h2>재건축·재개발 기준</h2>
  <ul>
    <li>재건축: 준공 30년이 넘은 아파트는 안전진단 없이 재건축을 시작할 수 있고, 재건축진단은 사업시행인가 전까지 통과하면 돼요 (2025년 6월 시행 도시정비법 개정).</li>
    <li>재개발: 노후·불량 건축물 60% 이상, 구역 면적 1만㎡ 이상에 과소필지·접도율·호수밀도·노후 연면적 요건 중 하나를 갖춰야 해요.</li>
    <li>모아타운: 2만~10만㎡ 규모에서 노후도 50% 이상이면 추진할 수 있어요.</li>
  </ul>
  <h2>정비사업 현황</h2>
  <p>언론 보도와 서울시 발표를 바탕으로 정리했고, 항목마다 기준월과 출처를 밝혔어요. 지도 위치는 동 단위 대략값이에요. 공식 단계는 서울시 정비사업 정보몽땅에서 확인할 수 있어요.</p>
  <h2>갱신 주기</h2>
  <p>원자료는 매년 4월 무렵 새 연도가 공개돼요. 이 사이트는 매년 5월 1일 자동으로 새 자료를 받아 다시 계산하고, 검증을 통과하면 운영자 확인을 거쳐 반영해요. 계산 코드와 데이터는 모두 <a href="https://github.com/mpkw156-sky/seoul-housing-age" rel="noopener">GitHub 저장소</a>에 공개돼 있어요.</p>
  <h2>경계 데이터</h2>
  <p>자치구 경계는 통계청 센서스용 행정구역경계(2013)를 간략화한 공개 데이터(southkorea/seoul-maps)를 써요. 표시용으로 단순화해서 실제 경계와 조금 다를 수 있어요.</p>
</div>
"""
    layout("methodology/", f"방법론 – {SITE}", "주택 노후도 지표의 원자료, 정의, 계산식, 법정 노후도와의 차이, 갱신 주기를 설명합니다.",
           body, active="/methodology/")


def build_data_page():
    sources = [
        ("주택 노후기간 통계", "서울시 노후기간별 주택현황 통계",
         "자치구·주택종류별로 지은 지 20~30년 미만, 30년 이상 된 주택 수",
         "https://data.seoul.go.kr/bsp/wgs/dataView/data300View/474.do"),
        ("주택 건축연도 통계", "서울시 건축연도별 주택현황 통계",
         "자치구·주택종류·건축연도별 주택 수 (전체 주택 수와 지은 연도 분포)",
         "https://data.seoul.go.kr/bsp/wgs/dataView/data300View/460.do"),
    ]
    cards = "".join(
        f'<div class="card src"><span class="eyebrow">{esc(k)}</span><b>{esc(t)}</b><p>{esc(d)}</p>'
        f'<dl><dt>작성</dt><dd>국가데이터처 주택총조사</dd><dt>제공</dt><dd>서울특별시 (서울 데이터 허브)</dd>'
        f'<dt>이용 조건</dt><dd>공공누리 제1유형 (출처 표시)</dd><dt>사이트 반영</dt><dd>{YEARS[0]}~{Y1}년</dd></dl>'
        f'<a href="{esc(u)}" rel="noopener" target="_blank">서울 데이터 허브에서 보기 →</a></div>'
        for k, t, d, u in sources)
    body = f"""
<header class="page-head">
  <div class="eyebrow">데이터 출처 · {YEARS[0]}~{Y1}년 · 해마다 갱신</div>
  <h1>숫자는 여기서 왔어요</h1>
  <p class="lede">이 사이트의 모든 숫자는 아래 공공 통계를 가공한 거예요. 원자료는 각 기관 사이트에서 직접 확인할 수 있어요.</p>
</header>
<section class="sources" aria-label="주택 통계 출처">{cards}</section>
<div class="prose">
  <h2>그 밖의 출처</h2>
  <ul>
    <li>정비사업 현황: 항목마다 표시한 언론 보도와 서울시 발표 (<a href="/projects/">정비사업 현황</a>에서 기준월과 함께 확인)</li>
    <li>자치구 경계: 통계청 센서스용 행정구역경계(2013), <a href="https://github.com/southkorea/seoul-maps" rel="noopener" target="_blank">southkorea/seoul-maps</a> 가공본</li>
    <li>보도자료 모음: <a href="https://www.seoul.go.kr/news/news_report.do" rel="noopener" target="_blank">서울특별시 보도자료</a>, <a href="https://www.molit.go.kr/USR/NEWS/m_71/lst.jsp" rel="noopener" target="_blank">국토교통부 보도자료</a>의 제목과 원문 링크 (<a href="/news/">보도자료 모음</a>, 매일 갱신)</li>
  </ul>
  <h2>갱신 주기</h2>
  <p>원자료는 매년 4월 무렵 새 연도가 공개되고, 이 사이트는 매년 5월에 반영해요. 지표 정의와 계산 방법은 <a href="/methodology/">방법론</a>에 있어요.</p>
</div>
"""
    layout("data/", f"데이터 출처 – {SITE}",
           "서울 주택 노후도 사이트가 쓰는 공공 통계(국가데이터처 주택총조사, 서울 데이터 허브)의 출처와 이용 조건.", body, active="/data/")


def build_about():
    contact = (f'<a href="mailto:{esc(CFG["contact_email"])}">{esc(CFG["contact_email"])}</a>' if CFG.get("contact_email")
               else "문의 이메일은 준비 중입니다. 그동안은 GitHub 저장소의 Issues로 남겨 주세요.")
    body = f"""
<header class="page-head">
  <div class="eyebrow">사이트 소개</div>
  <h1>{esc(SITE)} 소개</h1>
  <p class="lede">{esc(SITE)}는 공공 통계로 서울의 집이 몇 살인지 보여주는 시각화 사이트예요. 자치구별로 아파트와 단독·다세대 주택의 나이를 나눠 보고, 해마다 새 통계로 고쳐요.</p>
</header>
<section class="hello" aria-label="마스코트 소개">
  {mascot(104)}
  <div class="bubble">
    <span class="who">마스코트 소개</span>
    <p class="say">안녕하세요, {MASCOT_NAME}예요.</p>
    <p class="small">차나 건물이 몇 년 됐는지를 '연식'이라고 하죠. 저는 서울 집들의 연식을 세어 알려 드리는 안경 쓴 작은 집이에요. 숫자는 모두 공공 통계에서 가져오고, 어느 동네가 좋다 나쁘다는 말은 하지 않아요.</p>
  </div>
</section>
<div class="prose">
  <h2>운영 원칙</h2>
  <ul>
    <li>공개된 공식 통계만 쓰고, 모든 숫자에 출처와 기준연도를 밝혀요.</li>
    <li>특정 지역이나 단지의 매수·매도를 권하지 않아요. 이 사이트는 투자 권유나 자문이 아니에요.</li>
    <li>계산 방법과 코드를 공개해서 누구나 같은 결과를 다시 만들 수 있게 해요.</li>
  </ul>
  <h2>출처와 라이선스</h2>
  <ul>
    <li>주택 통계: 국가데이터처 주택총조사 – 서울 데이터 허브 「서울시 노후기간별 주택현황 통계」, 「서울시 건축연도별 주택현황 통계」 (공공누리 제1유형) · <a href="https://data.seoul.go.kr/" rel="noopener">data.seoul.go.kr</a></li>
    <li>자치구 경계: 통계청 센서스용 행정구역경계(2013), <a href="https://github.com/southkorea/seoul-maps" rel="noopener">southkorea/seoul-maps</a> 가공본</li>
    <li>정비사업 현황: 각 항목에 표시한 언론 보도와 서울시 발표 (<a href="/projects/">정비사업 현황</a>)</li>
    <li>보도자료 모음: 서울특별시·국토교통부 보도자료의 제목과 원문 링크만 보여 줘요. 저작권은 각 기관에 있어요 (<a href="/news/">보도자료 모음</a>)</li>
    <li>마스코트 '{MASCOT_NAME}': 이 사이트가 직접 만든 캐릭터</li>
    <li>3D 그래픽: three.js (MIT License)</li>
    <li>글꼴: 배민 주아체(BM JUA), IBM Plex Sans KR, IBM Plex Mono (SIL Open Font License, Google Fonts)</li>
  </ul>
  <h2>문의</h2>
  <p>{contact}</p>
  <p>소스 코드: <a href="https://github.com/mpkw156-sky/seoul-housing-age" rel="noopener">github.com/mpkw156-sky/seoul-housing-age</a></p>
</div>
"""
    layout("about/", f"소개·출처 – {SITE}", f"{SITE}의 운영 원칙, 데이터 출처와 라이선스, 문의처.", body)


def build_privacy():
    contact = esc(CFG["contact_email"]) if CFG.get("contact_email") else "GitHub 저장소 Issues"
    ads = bool(CFG.get("adsense_client") or any(CFG.get("kakao_adfit_units", {}).values()))
    ad_section = ("<h2>광고</h2><p>이 사이트는 Google AdSense 또는 카카오 애드핏 광고를 게재합니다. 광고 사업자는 쿠키 등을 이용해 방문 기록을 바탕으로 광고를 보여줄 수 있습니다. "
                  "Google의 개인 맞춤 광고는 <a href=\"https://adssettings.google.com\" rel=\"noopener\">광고 설정</a>에서 끌 수 있습니다.</p>"
                  if ads else "<h2>광고</h2><p>현재 광고를 게재하지 않습니다. 광고를 도입하면 이 방침을 먼저 고쳐 알립니다.</p>")
    ga_section = ""
    if CFG.get("ga4_measurement_id"):
        ga_section = """<h2>방문 통계 (Google 애널리틱스)</h2>
  <p>어떤 페이지가 얼마나 읽히는지 파악해 사이트를 고치기 위해 Google 애널리틱스 4를 씁니다. 이름·이메일·전화번호 같은 정보는 수집하지 않으며, Google 신호와 광고 개인화 기능은 껐습니다.</p>
  <ul>
    <li>수집 항목: 쿠키 식별자(_ga, _ga_*), 방문한 페이지와 시간, 유입 경로, 기기·브라우저 종류, 대략적인 지역(IP 주소로 추정하며 IP 주소 자체는 저장되지 않음)</li>
    <li>보유 기간: 수집일로부터 14개월이 지나면 Google이 자동으로 삭제합니다.</li>
    <li>국외 이전: 위 정보는 방문 시 정보통신망을 통해 Google LLC(미국)로 전송·보관됩니다. 이전 목적은 방문 통계 분석이며, 원하지 않으면 아래 방법으로 거부할 수 있습니다.</li>
    <li>거부 방법: 브라우저 설정에서 쿠키 저장을 차단하거나, Google의 <a href="https://tools.google.com/dlpage/gaoptout" rel="noopener">애널리틱스 차단 브라우저 부가기능</a>을 설치하면 됩니다. 쿠키를 막아도 사이트 이용에는 지장이 없습니다.</li>
  </ul>
  <p>자세한 내용: <a href="https://policies.google.com/technologies/partner-sites?hl=ko" rel="noopener">Google이 파트너 사이트의 정보를 사용하는 방식</a></p>"""
    lede_tail = ("는 회원가입, 로그인, 문의 양식이 없으며 이용자의 이름·연락처 같은 개인정보를 직접 수집하지 않습니다. 다만 방문 통계를 위해 쿠키를 씁니다."
                 if CFG.get("ga4_measurement_id") else "는 회원가입, 로그인, 문의 양식이 없으며 이용자의 개인정보를 직접 수집하지 않습니다.")
    body = f"""
<header class="page-head">
  <div class="eyebrow">시행일 {TODAY.isoformat()}</div>
  <h1>개인정보처리방침</h1>
  <p class="lede">{esc(SITE)}({esc(CFG['domain'])}){lede_tail}</p>
</header>
<div class="prose">
  <h2>브라우저에 저장하는 정보</h2>
  <p>지도에서 마지막으로 고른 보기(예: 아파트 30년+)를 다음 방문 때 그대로 보여주기 위해 이용자 브라우저의 저장소(localStorage)에 기록합니다. 이 정보는 서버로 보내지 않으며, 브라우저에서 사이트 데이터를 지우면 삭제됩니다.</p>
  <h2>외부 서비스</h2>
  <ul>
    <li>호스팅: GitHub Pages. 접속 시 IP 주소 등 기술 정보가 GitHub의 서버 로그에 남을 수 있습니다 (<a href="https://docs.github.com/ko/site-policy/privacy-policies/github-general-privacy-statement" rel="noopener">GitHub 개인정보처리방침</a>).</li>
    <li>글꼴: Google Fonts. 글꼴을 내려받을 때 IP 주소가 Google에 전달될 수 있습니다.</li>
  </ul>
  {ga_section}
  {ad_section}
  <h2>문의</h2>
  <p>개인정보 관련 문의: {contact}</p>
</div>
"""
    layout("privacy/", f"개인정보처리방침 – {SITE}", f"{SITE}의 개인정보처리방침.", body)


def build_404():
    body = f"""
<header class="page-head">
  <div class="eyebrow">404</div>
  <h1>앗, 길을 잃었어요</h1>
</header>
<section class="hello" aria-label="안내">
  {mascot(96)}
  <div class="bubble">
    <p class="say">이 주소에는 집이 없어요.</p>
    <p class="small">주소가 바뀌었거나 없는 페이지예요. <a href="/">지도</a>나 <a href="/gu/">자치구 목록</a>에서 다시 찾아 주세요.</p>
  </div>
</section>
"""
    layout("404.html", f"페이지를 찾을 수 없습니다 – {SITE}", "요청한 페이지가 없습니다.", body, noindex=True)


def write_static():
    shutil.copytree(SRC / "assets", OUT / "assets", dirs_exist_ok=True)
    (OUT / "CNAME").write_text(CFG["domain"] + "\n", encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n", encoding="utf-8")
    sm = "".join(f"<url><loc>{u}</loc><lastmod>{TODAY.isoformat()}</lastmod></url>" for u in SITEMAP)
    (OUT / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>\n',
        encoding="utf-8")
    if CFG.get("adsense_client"):
        pub = CFG["adsense_client"].replace("ca-", "")
        (OUT / "ads.txt").write_text(f"google.com, {pub}, DIRECT, f08c47fec0942fa0\n", encoding="utf-8")


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    build_home()
    build_3d()
    build_gu_index()
    build_gu_pages()
    build_projects()
    build_news()
    build_methodology()
    build_data_page()
    build_about()
    build_privacy()
    build_404()
    write_static()
    print(f"built {len(SITEMAP)} pages into {OUT.relative_to(ROOT)} (data {YEARS[0]}–{Y1}, compare {Y0})")


if __name__ == "__main__":
    main()
