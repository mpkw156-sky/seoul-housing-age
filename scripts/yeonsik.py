"""연식이 — 이 사이트가 직접 만든 마스코트 (안경 쓴 작은 집).

pose: hello(인사) · news(소식) · build(공사중) · search(돋보기) · think(갸우뚱) · cheer(만세)
모든 색은 CSS 변수(--m-*)를 써서 라이트·다크 모드를 따라갑니다. 움직임은 site.css의 .yk 규칙,
반응(눈 따라보기·탭하면 말하기)은 assets/yeonsik.js가 맡습니다.
"""
from __future__ import annotations

import html
import json

POSES = ("hello", "news", "build", "search", "think", "cheer")

L = "var(--m-line)"

ARM_DOWN_L = '<path class="arm arm-l" d="M40 122 Q27 134 29 150" />' '<circle class="hand" cx="29" cy="151" r="6.5" />'
ARM_DOWN_R = '<path class="arm arm-r" d="M120 122 Q133 134 131 150" />' '<circle class="hand" cx="131" cy="151" r="6.5" />'
ARM_UP_R = '<g class="arm-r-g"><path class="arm" d="M121 121 Q146 114 155 92" /><circle class="hand" cx="155" cy="90" r="6.5" /></g>'
ARM_UP_L = '<g class="arm-l-g"><path class="arm" d="M39 121 Q14 114 5 92" /><circle class="hand" cx="5" cy="90" r="6.5" /></g>'

MOUTH = {
    "smile": '<path class="mouth" d="M70 120 Q80 129 90 120" />',
    "open": '<path class="mouth-fill" d="M69 118 Q80 134 91 118 Z" /><path class="tongue" d="M75 125 Q80 130 85 125 Q80 123 75 125 Z" />',
    "o": '<ellipse class="mouth-fill" cx="80" cy="123" rx="5" ry="6" />',
    "flat": '<path class="mouth" d="M72 123 Q80 120 88 123" />',
    "wobble": '<path class="mouth" d="M70 123 Q75 119 80 123 Q85 127 90 123" />',
}


def _props(pose: str) -> tuple[str, str, str]:
    """(behind-body, in-front, mouth) for a pose."""
    if pose == "hello":
        return "", ARM_DOWN_L + ARM_UP_R, "smile"
    if pose == "cheer":
        spark = ('<g class="spark"><path d="M20 52 l3 7 7 3 -7 3 -3 7 -3 -7 -7 -3 7 -3z" />'
                 '<path d="M140 46 l2.5 6 6 2.5 -6 2.5 -2.5 6 -2.5 -6 -6 -2.5 6 -2.5z" /></g>')
        return "", ARM_UP_L + ARM_UP_R + spark, "open"
    if pose == "news":
        paper = ('<g class="paper"><rect x="48" y="136" width="64" height="34" rx="4" />'
                 '<path class="ln" d="M56 145 H92 M56 152 H104 M56 159 H96" />'
                 '<circle class="badge" cx="110" cy="136" r="8" /><path class="badge-t" d="M110 131.5 V137 M110 140 V140.4" /></g>')
        arms = ('<path class="arm" d="M40 126 Q42 146 54 152" /><circle class="hand" cx="54" cy="153" r="6.5" />'
                '<path class="arm" d="M120 126 Q118 146 106 152" /><circle class="hand" cx="106" cy="153" r="6.5" />')
        return "", paper + arms, "open"
    if pose == "build":
        hat = ('<g class="hat"><path d="M52 48 Q80 4 108 48 Z" /><rect x="44" y="45" width="72" height="9" rx="4.5" />'
               '<path class="cross" d="M80 22 V34 M74 28 H86" /></g>')
        hammer = ('<g class="hammer"><path class="handle" d="M131 150 L146 112" />'
                  '<rect class="head" x="136" y="101" width="22" height="12" rx="2.5" transform="rotate(22 147 107)" /></g>')
        sweat = '<path class="sweat" d="M118 70 q4 6 0 9 q-4 -3 0 -9z" />'
        return "", hat + ARM_DOWN_L + '<path class="arm" d="M120 122 Q133 134 131 150" /><circle class="hand" cx="131" cy="151" r="6.5" />' + hammer + sweat, "flat"
    if pose == "search":
        lens = ('<g class="lens"><path class="handle" d="M128 116 L140 132" />'
                '<circle class="glass" cx="120" cy="104" r="14" /></g>')
        arm = '<path class="arm" d="M120 124 Q134 134 140 134" /><circle class="hand" cx="141" cy="134" r="6.5" />'
        return "", ARM_DOWN_L + arm + lens, "o"
    if pose == "think":
        q = '<text class="q" x="132" y="44">?</text>'
        arm = '<path class="arm" d="M120 120 Q142 100 120 76" /><circle class="hand" cx="119" cy="74" r="6.5" />'
        return "", ARM_DOWN_L + arm + q, "wobble"
    raise ValueError(pose)


def svg(pose: str = "hello") -> str:
    behind, front, mouth = _props(pose)
    return (
        f'<svg class="yk-svg" viewBox="-6 0 172 192" aria-hidden="true" focusable="false">'
        '<ellipse class="shadow" cx="80" cy="184" rx="40" ry="5" />'
        '<g class="bob">'
        '<g class="legs"><path d="M58 158 V174 q0 5 -6 5 h-4" /><path d="M102 158 V174 q0 5 6 5 h4" /></g>'
        f"{behind}"
        + ("" if pose == "build" else '<rect class="chimney" x="100" y="36" width="14" height="26" rx="2" />') +
        '<path class="walls" d="M36 82 L80 44 L124 82 V150 a14 14 0 0 1 -14 14 H50 a14 14 0 0 1 -14 -14 Z" />'
        '<path class="roof" d="M22 86 L80 32 L138 86 L128 93 L80 50 L32 93 Z" />'
        '<path class="door" d="M71 164 V150 a9 9 0 0 1 18 0 V164 Z" /><circle class="knob" cx="85" cy="157" r="1.8" />'
        '<circle class="cheek" cx="49" cy="116" r="5.5" /><circle class="cheek" cx="111" cy="116" r="5.5" />'
        '<g class="glasses"><circle cx="64" cy="101" r="11.5" /><circle cx="96" cy="101" r="11.5" /><path d="M75.5 101 H84.5" /></g>'
        '<g class="eyes"><g class="pupils"><circle cx="64" cy="102" r="3.6" /><circle cx="96" cy="102" r="3.6" /></g></g>'
        f"{MOUTH[mouth]}"
        f"{front}"
        "</g></svg>"
    )


def buddy(pose: str = "hello", *, size: str = "", lines: list[str] | None = None, label: str = "연식이",
          cls: str = "") -> str:
    """Character element. With `lines`, it becomes a button that says one of them when tapped."""
    style = f' style="--yk:{size}"' if size else ""
    c = f"yk yk-{pose}" + (f" {cls}" if cls else "")
    if lines:
        data = html.escape(json.dumps(lines, ensure_ascii=False), quote=True)
        return (f'<div class="{c}"{style}><button type="button" class="yk-btn" data-lines="{data}" '
                f'aria-label="{html.escape(label)}에게 말 걸기">{svg(pose)}</button>'
                f'<span class="yk-say" role="status" aria-live="polite"></span></div>')
    return f'<div class="{c}"{style} role="img" aria-label="{html.escape(label)}">{svg(pose)}</div>'
