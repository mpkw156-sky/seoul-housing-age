#!/usr/bin/env python3
"""Collect today's Seoul housing / real-estate press releases into data/news.json.

Sources (official press releases only, not newspaper articles):
  - 서울특별시 보도자료 RSS   https://seoulboard.seoul.go.kr/rss/RSSGenerator?bbsNo=158
  - 국토교통부 보도자료 목록  https://www.molit.go.kr/USR/NEWS/m_71/lst.jsp (주택토지·국토도시)

Only the title, issuing body, department, date and a link to the original are stored.
No body text, summary, image or attachment is copied.

Usage: python scripts/fetch_news.py [--per-day 3] [--keep-days 180] [--dry-run]
Stdlib only. Exits 0 even if one source fails, as long as the other works.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "news.json"
KST = dt.timezone(dt.timedelta(hours=9))
UA = "Mozilla/5.0 (compatible; seoul-housing-age-news/1.0; +https://seoul-housing-age.com/news/)"

SEOUL_RSS = "https://seoulboard.seoul.go.kr/rss/RSSGenerator?bbsNo=158"
MOLIT_LIST = "https://www.molit.go.kr/USR/NEWS/m_71/lst.jsp?search_section={sec}&lcmspage={page}"
MOLIT_DTL = "https://www.molit.go.kr/USR/NEWS/m_71/dtl.jsp?lcmspage=1&id={id}"
MOLIT_SECTIONS = {"p_sec_2": "주택토지", "p_sec_9": "국토도시"}

STRONG = ["재건축", "재개발", "정비사업", "정비구역", "재정비", "모아타운", "모아주택", "신속통합", "실거래", "주택공급",
          "공공주택", "임대주택", "공공임대", "전세", "임대차", "토지거래허가", "아파트", "부동산", "청약", "분양",
          "도시계획위원회", "주거", "집값", "주택시장", "역세권"]
WEAK = ["주택", "정비", "재생", "택지", "용적률", "공시가격", "공시지가"]
SEOUL_HOUSING_BODIES = {"주택실": 2, "도시공간본부": 1, "균형발전본부": 1}
PREFIX = re.compile(r"^\s*(?:[\(\[][^\)\]]{0,24}?(?:석간|조간|엠바고|자료제공|보도|배포|즉시|설명|참고)[^\)\]]{0,24}[\)\]]\s*)+")


def get(url: str, tries: int = 3) -> str:
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})
            with urllib.request.urlopen(req, timeout=30) as r:
                raw = r.read()
                cs = r.headers.get_content_charset() or "utf-8"
            return raw.decode(cs, errors="replace")
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (k + 1))
    raise RuntimeError(f"{url}: {last}")


def clean(s: str) -> str:
    s = html.unescape(html.unescape(s or ""))
    s = re.sub(r"\s+", " ", s).strip()
    return PREFIX.sub("", s).strip()


def score(title: str) -> int:
    sc = sum(3 for w in STRONG if w in title)
    sc += sum(1 for w in WEAK if w in title)
    return sc


# ---------------------------------------------------------------- Seoul
def seoul_items(pages: int = 2) -> list[dict]:
    out = []
    for p in range(1, pages + 1):
        xml = get(SEOUL_RSS + (f"&page={p}" if p > 1 else ""))
        root = ET.fromstring(xml.encode("utf-8"))
        for it in root.iter("item"):
            t = lambda tag: (it.findtext(tag) or "").strip()  # noqa: E731
            link = t("link")
            m = re.search(r"(\d{5,})\s*$", link)
            if not m:
                continue
            title = clean(t("title"))
            body, dept = t("crdns"), t("dept")
            body = "" if body == "null" else body
            s = score(title)
            if s == 0:
                continue
            s += SEOUL_HOUSING_BODIES.get(body, 0)
            when = dt.datetime.strptime(t("pubDate")[:19], "%Y-%m-%d %H:%M:%S")
            out.append(dict(id=f"seoul-{m.group(1)}", src="seoul", org="서울특별시",
                            dept=" ".join(x for x in (body, dept) if x), title=title,
                            url=f"https://www.seoul.go.kr/news/news_report.do#view/{m.group(1)}",
                            date=when.date().isoformat(), time=when.strftime("%H:%M"), score=s))
    return out


# ---------------------------------------------------------------- MOLIT
class _Rows(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self._row, self._cell, self._href, self._in_tbody = [], None, None, None, False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "tbody":
            self._in_tbody = True
        elif tag == "tr" and self._in_tbody:
            self._row, self._href = [], None
        elif tag == "td" and self._row is not None:
            self._cell = []
        elif tag == "a" and self._row is not None and self._href is None and "dtl.jsp" in (a.get("href") or ""):
            self._href = a["href"]

    def handle_endtag(self, tag):
        if tag == "td" and self._row is not None and self._cell is not None:
            self._row.append(re.sub(r"\s+", " ", "".join(self._cell)).strip())
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._href:
                self.rows.append((self._row, self._href))
            self._row = None
        elif tag == "tbody":
            self._in_tbody = False

    def handle_data(self, d):
        if self._cell is not None:
            self._cell.append(d)


def molit_items() -> list[dict]:
    out = []
    for sec, name in MOLIT_SECTIONS.items():
        p = _Rows()
        p.feed(get(MOLIT_LIST.format(sec=sec, page=1)))
        for cells, href in p.rows:
            m = re.search(r"[?&]id=(\d+)", href)
            dates = [c for c in cells if re.fullmatch(r"\d{4}-\d{2}-\d{2}", c)]
            if not m or not dates or len(cells) < 2:
                continue
            title = clean(cells[1])
            s = score(title)
            if sec == "p_sec_9" and s < 3:
                continue
            s += 1 if sec == "p_sec_2" else 0
            if re.search(r"서울|수도권", title):
                s += 2
            out.append(dict(id=f"molit-{m.group(1)}", src="molit", org="국토교통부", dept=name, title=title,
                            url=MOLIT_DTL.format(id=m.group(1)), date=dates[0], time="", score=s))
    return out


# ---------------------------------------------------------------- merge
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-day", type=int, default=3)
    ap.add_argument("--min-score", type=int, default=3)
    ap.add_argument("--keep-days", type=int, default=180)
    ap.add_argument("--lookback-days", type=int, default=7, help="이 기간 안의 날짜만 새로 채웁니다")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"items": []}
    have = {it["id"] for it in old["items"]}
    cand, errors = [], []
    for name, fn in (("서울시", seoul_items), ("국토교통부", molit_items)):
        try:
            got = fn()
            print(f"{name}: 후보 {len(got)}건")
            cand += got
        except Exception as e:  # noqa: BLE001
            errors.append(f"{name}: {e}")
            print(f"::warning::{name} 수집 실패 - {e}")
    if len(errors) == 2:
        print("::error::두 출처 모두 수집하지 못했습니다")
        sys.exit(1)

    today = dt.datetime.now(KST).date()
    since = (today - dt.timedelta(days=a.lookback_days)).isoformat()
    per_day: dict[str, int] = {}
    for it in old["items"]:
        per_day[it["date"]] = per_day.get(it["date"], 0) + 1
    seen_titles = {it["title"] for it in old["items"]}
    new = []
    for it in sorted(cand, key=lambda x: (-x["score"], x["date"], x["time"]), reverse=False):
        if it["id"] in have or it["title"] in seen_titles or it["score"] < a.min_score:
            continue
        if it["date"] < since or it["date"] > today.isoformat():
            continue
        if per_day.get(it["date"], 0) >= a.per_day:
            continue
        per_day[it["date"]] = per_day.get(it["date"], 0) + 1
        have.add(it["id"]); seen_titles.add(it["title"])
        new.append({k: it[k] for k in ("id", "date", "time", "org", "dept", "title", "url", "src")})

    keep_from = (today - dt.timedelta(days=a.keep_days)).isoformat()
    items = [it for it in old["items"] + new if it["date"] >= keep_from]
    items.sort(key=lambda x: (x["date"], x["time"], x["id"]), reverse=True)
    for it in new:
        print(f"+ {it['date']} [{it['org']}] {it['title']}")
    print(f"새 항목 {len(new)}건, 전체 {len(items)}건")
    if a.dry_run:
        return
    if not new and OUT.exists():
        return
    OUT.write_text(json.dumps({"updated": dt.datetime.now(KST).isoformat(timespec="minutes"), "items": items},
                              ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
