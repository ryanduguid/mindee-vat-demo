#!/usr/bin/env python3
"""Render the demo's terminal output to a self-contained SVG (no external tools).

    python make_svg.py          # writes demo.svg

For an animated GIF instead, see demo.tape (needs `vhs`).
"""

from __future__ import annotations

import subprocess
import sys
from xml.sax.saxutils import escape

BG = "#0d1117"
DEFAULT = "#c9d1d9"
MUTED = "#8b949e"
WHITE = "#e6edf3"
CYAN = "#39c5cf"
GREEN = "#3fb950"
AMBER = "#d29922"
ACCENT = "#58a6ff"

CHAR_W = 8.0
LINE_H = 22
PAD_X = 24
PAD_Y = 34


def color_for(line: str) -> str:
    s = line.strip()
    if s.startswith("Mindee → OpenAccountants"):
        return ACCENT
    if s.startswith("📄"):
        return WHITE
    if "✅" in s:
        return GREEN
    if "⚠" in s:
        return AMBER
    if s.startswith("OpenAccountants →"):
        return CYAN
    if s.startswith("Mindee →") or s.startswith("net ") or "·" in s and "VAT" in s:
        return MUTED
    if s.startswith("rule:") or s.startswith("→ handoff"):
        return MUTED
    return DEFAULT


def main() -> int:
    out = subprocess.run(
        [sys.executable, "pipeline.py"], capture_output=True, text=True
    ).stdout.rstrip("\n")
    lines = out.split("\n")

    width = int(max((len(ln) for ln in lines), default=60) * CHAR_W + PAD_X * 2)
    height = len(lines) * LINE_H + PAD_Y + 24

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="SFMono-Regular,Consolas,Menlo,monospace" font-size="14">',
        f'<rect width="{width}" height="{height}" rx="10" fill="{BG}"/>',
        # window dots
        '<circle cx="20" cy="18" r="6" fill="#ff5f56"/>',
        '<circle cx="40" cy="18" r="6" fill="#ffbd2e"/>',
        '<circle cx="60" cy="18" r="6" fill="#27c93f"/>',
    ]
    y = PAD_Y + 6
    for ln in lines:
        if ln.strip():
            parts.append(
                f'<text x="{PAD_X}" y="{y}" xml:space="preserve" '
                f'fill="{color_for(ln)}">{escape(ln)}</text>'
            )
        y += LINE_H
    parts.append("</svg>")

    with open("demo.svg", "w") as fh:
        fh.write("\n".join(parts))
    print(f"wrote demo.svg ({width}x{height}, {len(lines)} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
