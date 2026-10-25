#!/usr/bin/env python3
"""Download the two Seoul Data Hub statistics and rebuild data/housing_age.json.

Sources (공공누리 제1유형, 국가데이터처 주택총조사):
  474  서울시 노후기간별 주택현황 통계   (yr, signgu, spanuat_pd, house_knd, house_cnt)
  460  서울시 건축연도별 주택현황 통계   (yr, signgu, bld_yr,     house_knd, house_cnt)

The rows come from the same public JSON endpoint the Seoul Data Hub page uses
for its data preview (no login or key needed). Suppressed cells (<5, shown as x)
arrive as null and are counted as 0.

Usage: python scripts/fetch_data.py --out data/housing_age.new.json [--raw-dir raw]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

URL = "https://data.seoul.go.kr/bsp/wgs/dataset/dataTypeList.do"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "seoul-housing-age-updater (+https://github.com/mpkw156-sky/seoul-housing-age)",
    "Referer": "https://data.seoul.go.kr/bsp/wgs/dataView/data300View/474.do",
}
PAGE = 1000
BAND_LABELS = ["~1979", "1980s", "1990s", "2000-04", "2005-09", "2010-14", "2015-19", "2020-"]


def post(dataset_id: int, page: int, retries: int = 4) -> list[dict]:
    body = json.dumps({"id": str(dataset_id), "rowFilterList": [], "currentPage": page, "pagePer": PAGE}).encode()
    for attempt in range(retries):
        try:
            req = urllib.request.Request(URL, data=body, headers=HEADERS, method="POST")
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read().decode("utf-8"))
            if data.get("header", {}).get("resultCode") != "ok":
                raise RuntimeError(f"unexpected header: {data.get('header')}")
            return data.get("dataTypeList") or []
        except Exception as e:  # noqa: BLE001
            if attempt == retries - 1:
                raise
            wait = 5 * (attempt + 1)
            print(f"  retry {dataset_id} p{page} after error: {e} (wait {wait}s)", file=sys.stderr)
            time.sleep(wait)
    return []


def fetch_all(dataset_id: int) -> list[dict]:
    rows: list[dict] = []
    for page in range(1, 200):
        chunk = post(dataset_id, page)
        if not chunk:
            break
        rows.extend(chunk)
        time.sleep(0.3)
    print(f"dataset {dataset_id}: {len(rows)} rows", file=sys.stderr)
    if not rows:
        raise SystemExit(f"dataset {dataset_id} returned no rows")
    return rows


def kind(k: str) -> str:
    if k == "아파트":
        return "A"
    if k == "단독주택":
        return "D"
    if k == "다세대주택":
        return "M"
    if k == "연립주택":
        return "R"
    if "건물내" in k:
        return "N"
    raise SystemExit(f"unknown house kind: {k!r}")


def period(p: str) -> str:
    if p.startswith("30"):
        return "30"
    if p.startswith("20"):
        return "20"
    raise SystemExit(f"unknown age period: {p!r}")


def num(v) -> int:
    if isinstance(v, (int, float)):
        return int(v)
    if isinstance(v, str) and re.fullmatch(r"\d+", v.replace(",", "")):
        return int(v.replace(",", ""))
    return 0


def band(bld_yr: str) -> str:
    if "이전" in bld_yr:
        return "~1979"
    y = int(re.match(r"(\d{4})", bld_yr).group(1))
    for lab, (a, b) in {"1980s": (1980, 1989), "1990s": (1990, 1999), "2000-04": (2000, 2004), "2005-09": (2005, 2009),
                        "2010-14": (2010, 2014), "2015-19": (2015, 2019)}.items():
        if a <= y <= b:
            return lab
    if y >= 2020:
        return "2020-"
    return "~1979"


def aggregate(age_rows: list[dict], year_rows: list[dict]) -> dict:
    gu = sorted({r["signgu"] for r in year_rows})
    years = sorted({r["yr"] for r in age_rows} & {r["yr"] for r in year_rows})
    tot: dict[tuple, int] = {}
    for r in year_rows:
        k = (r["yr"], r["signgu"], kind(r["house_knd"]))
        tot[k] = tot.get(k, 0) + num(r["house_cnt"])
    age: dict[tuple, int] = {}
    for r in age_rows:
        k = (r["yr"], r["signgu"], period(r["spanuat_pd"]), kind(r["house_knd"]) == "A")
        age[k] = age.get(k, 0) + num(r["house_cnt"])
    m = {}
    for y in years:
        rows = []
        for g in gu:
            t = sum(v for (yy, gg, _), v in tot.items() if yy == y and gg == g)
            at = tot.get((y, g, "A"), 0)
            rows.append([t, at, t - at, age.get((y, g, "20", True), 0), age.get((y, g, "30", True), 0),
                         age.get((y, g, "20", False), 0), age.get((y, g, "30", False), 0)])
        m[y] = rows
    latest = max(r["yr"] for r in year_rows)
    bands = []
    for g in gu:
        a, low = [0] * len(BAND_LABELS), [0] * len(BAND_LABELS)
        for r in year_rows:
            if r["yr"] == latest and r["signgu"] == g:
                i = BAND_LABELS.index(band(r["bld_yr"]))
                (a if kind(r["house_knd"]) == "A" else low)[i] += num(r["house_cnt"])
        bands.append([a, low])
    return {"years": years, "gu": gu, "cols": ["tot", "aptTot", "lowTot", "apt20", "apt30", "low20", "low30"], "m": m,
            "bandLabels": BAND_LABELS, "bandsYear": latest, "bands": bands}


def write_raw(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = sorted({k for r in rows for k in r})
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--raw-dir", default="")
    args = ap.parse_args()
    age_rows, year_rows = fetch_all(474), fetch_all(460)
    if args.raw_dir:
        write_raw(age_rows, Path(args.raw_dir) / "seoul_474_age_period.csv")
        write_raw(year_rows, Path(args.raw_dir) / "seoul_460_build_year.csv")
    out = aggregate(age_rows, year_rows)
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"wrote {args.out}: years {out['years'][0]}–{out['years'][-1]}, {len(out['gu'])} districts", file=sys.stderr)


if __name__ == "__main__":
    main()
