#!/usr/bin/env python3
"""Sanity-check data/housing_age.json (and compare with a baseline when given).

Usage:
  python scripts/validate.py --new data/housing_age.json
  python scripts/validate.py --new data/housing_age.new.json --baseline data/housing_age.json --report report.md
Exit code 1 on any hard failure. Warnings go into the report but do not fail.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load(p: str) -> dict:
    return json.loads(Path(p).read_text(encoding="utf-8"))


def share30(r) -> float:
    return (r[4] + r[6]) / r[0] * 100 if r[0] else 0.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--new", required=True)
    ap.add_argument("--baseline", default="")
    ap.add_argument("--report", default="")
    a = ap.parse_args()
    d = load(a.new)
    errors: list[str] = []
    warns: list[str] = []
    notes: list[str] = []

    geo = json.loads((ROOT / "data" / "seoul_gu.geojson").read_text(encoding="utf-8"))
    geo_names = {f["properties"]["name"] for f in geo["features"]}
    if len(d["gu"]) != 25 or set(d["gu"]) != geo_names:
        errors.append(f"자치구 목록이 경계 데이터와 다릅니다: {sorted(set(d['gu']) ^ geo_names)}")
    years = d["years"]
    if years != sorted(years) or any(int(b) - int(a_) != 1 for a_, b in zip(years, years[1:])):
        errors.append(f"연도가 연속되지 않습니다: {years}")
    for y in years:
        rows = d["m"].get(y)
        if not rows or len(rows) != len(d["gu"]):
            errors.append(f"{y}년 행 수가 맞지 않습니다")
            continue
        for g, r in zip(d["gu"], rows):
            if len(r) != 7 or any((not isinstance(v, int)) or v < 0 for v in r):
                errors.append(f"{y} {g}: 값 형식 오류 {r}")
            elif r[0] != r[1] + r[2] or r[3] + r[4] > r[1] or r[5] + r[6] > r[2] or r[0] == 0:
                errors.append(f"{y} {g}: 합계 불일치 {r}")
    by = d["bandsYear"]
    if by in d["m"]:
        for k, g in enumerate(d["gu"]):
            A, L = d["bands"][k]
            row = d["m"][by][k]
            if sum(A) != row[1] or sum(L) != row[2]:
                errors.append(f"{g}: 건축연도 구간 합계({sum(A)}/{sum(L)})가 {by}년 주택 수({row[1]}/{row[2]})와 다릅니다")
    else:
        errors.append(f"bandsYear {by}가 연도 목록에 없습니다")

    latest = years[-1]
    if len(years) >= 2:
        prev = years[-2]
        st = sum(r[0] for r in d["m"][latest]); sp = sum(r[0] for r in d["m"][prev])
        if abs(st / sp - 1) > 0.05:
            warns.append(f"서울 전체 주택 수가 {prev}→{latest}년 {st / sp - 1:+.1%} 바뀌었습니다")
        for g, r1, r0 in zip(d["gu"], d["m"][latest], d["m"][prev]):
            if abs(r1[0] / r0[0] - 1) > 0.15:
                warns.append(f"{g} 주택 수 {prev}→{latest}년 {r1[0] / r0[0] - 1:+.1%}")
            if abs(share30(r1) - share30(r0)) > 15:
                warns.append(f"{g} 30년 이상 비율 {share30(r0):.1f}% → {share30(r1):.1f}%")

    if a.baseline and Path(a.baseline).exists():
        b = load(a.baseline)
        new_years = [y for y in years if y not in b["years"]]
        gone = [y for y in b["years"] if y not in years]
        notes.append(f"기존 {b['years'][0]}–{b['years'][-1]}년 → 새 {years[0]}–{years[-1]}년")
        notes.append("새로 추가된 연도: " + (", ".join(new_years) if new_years else "없음"))
        if gone:
            warns.append(f"기존에 있던 연도가 빠졌습니다: {gone}")
        changed = 0
        for y in set(years) & set(b["years"]):
            for g in d["gu"]:
                if g not in b["gu"]:
                    continue
                r_new, r_old = d["m"][y][d["gu"].index(g)], b["m"][y][b["gu"].index(g)]
                if r_new != r_old:
                    changed += 1
                    if r_old[0] and abs(r_new[0] / r_old[0] - 1) > 0.05:
                        errors.append(f"{y} {g}: 기존 값과 5% 넘게 다릅니다 ({r_old[0]} → {r_new[0]})")
        notes.append(f"기존 연도에서 값이 바뀐 행: {changed}개" + (" (원자료 수정 반영)" if changed else ""))
        s_new = sum(r[4] + r[6] for r in d["m"][latest]) / sum(r[0] for r in d["m"][latest]) * 100
        notes.append(f"{latest}년 서울 30년 이상 주택 비율: {s_new:.1f}%")

    lines = ["## 주택 노후도 데이터 검증", ""]
    lines += [f"- {n}" for n in notes]
    lines += ["", f"**오류 {len(errors)}건 · 경고 {len(warns)}건**", ""]
    lines += [f"- ❌ {e}" for e in errors] + [f"- ⚠️ {w}" for w in warns]
    if not errors and not warns:
        lines.append("- ✅ 모든 검사를 통과했습니다.")
    report = "\n".join(lines) + "\n"
    print(report)
    if a.report:
        Path(a.report).write_text(report, encoding="utf-8")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
