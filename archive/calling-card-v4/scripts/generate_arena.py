"""Draw the sword row: one sword per hackathon entered, the winners in gold.

59 swords stand in one rack (two rows of 30 and 29 on phones); the 36 that won
are gilded, the rest stay dark iron. Gold means won, and nothing else on the
row is gold. It is a still picture (stills only, see CLAUDE.md); in the dark
the gold swords carry a soft glow. The record lives in ink.WON / ink.ENTERED.

Run from the repo root: python scripts/generate_arena.py
Writes assets/arena/record.svg, record-light.svg, record-phone.svg.
"""

from __future__ import annotations

from pathlib import Path

import ink

OUT = Path("assets/arena")
CAPTION = "one sword per hackathon"


def sword_d(x: float, top: float, height: float, width: float = 8.0) -> str:
    """A straight jian, tip up: blade with a ridge line's taper, guard, grip, pommel."""
    k = height / 64
    hw = width / 8
    blade = 2.2 * hw

    def p(px: float, py: float) -> str:
        return f"{ink.fmt(x + px)} {ink.fmt(top + py * k)}"

    return (f"M{p(0, 0)}L{p(blade, 6)}L{p(blade, 44)}L{p(-blade, 44)}L{p(-blade, 6)}Z"
            f"M{p(-5.5 * hw, 44.6)}Q{p(0, 42.6)} {p(5.5 * hw, 44.6)}L{p(5 * hw, 47.6)}Q{p(0, 46.2)} {p(-5 * hw, 47.6)}Z"
            f"M{p(-1.3 * hw, 47.6)}L{p(1.3 * hw, 47.6)}L{p(1.3 * hw, 58)}L{p(-1.3 * hw, 58)}Z"
            f"M{p(-2.4 * hw, 60.2)}A{ink.fmt(2.4 * hw)} {ink.fmt(2.4 * hw * k)} 0 1 0 {p(2.4 * hw, 60.2)}"
            f"A{ink.fmt(2.4 * hw)} {ink.fmt(2.4 * hw * k)} 0 1 0 {p(-2.4 * hw, 60.2)}Z")


def rack(x0: float, y_top: float, width: float, per_row: int, height: float, row_gap: float,
         glow: bool, sword_w: float) -> tuple[str, str]:
    """(svg, css). The gold swords come first in the rack."""
    pitch = width / per_row
    won, dark = [], []
    for i in range(ink.ENTERED):
        r, c = divmod(i, per_row)
        x = x0 + pitch * (c + 0.5)
        top = y_top + r * (height + row_gap)
        (won if i < ink.WON else dark).append((i, sword_d(x, top, height, sword_w)))
    out = [f'<path d="{"".join(d for _, d in dark)}" class="tk"/>',
           f'<path d="{"".join(d for _, d in dark)}" class="ln" stroke-width=".8"/>']
    css = ""
    gold = f'<path d="{"".join(d for _, d in won)}" class="au"/>'
    out.append(f'<g class="glow">{gold}</g>' if glow else gold)
    # the rack: a stone ledge under each row
    rows = -(-ink.ENTERED // per_row)
    for r in range(rows):
        y = y_top + r * (height + row_gap) + height + 3
        out.append(ink.rect(x0 - 4, y, width + 8, 3, "lnf", 1.5))
    return "".join(out), css


def label() -> str:
    pct = round(100 * ink.WON / ink.ENTERED)
    return (f"{ink.WON} hackathons won out of {ink.ENTERED} entered ({pct}%). "
            f"One sword for each hackathon, gold for a win.")


def headline(x: float, y: float, num: float, small: float, gap: float, sep: str = "") -> tuple[list[str], float]:
    """'36 won', a gap (or a separator), '59 entered'. Returns (svg runs, end x)."""
    middle = ("  " + sep + "  ", "mu", "body", small) if sep else (None, "", "", gap)
    parts = [(str(ink.WON), "au", "display", num), (" won", "mu", "body", small), middle,
             (str(ink.ENTERED), "tx", "display", num), (" entered", "mu", "body", small)]
    out = []
    for text_, cls, face, size in parts:
        if text_ is None:
            x += size
            continue
        out.append(ink.text(x, y, text_, size, face, cls))
        x += ink.measure(text_, size, face)
    return out, x


def record_svg(mode: str) -> str:
    w, h = ink.W, 136
    glow = mode == "dark"
    body = [ink.plate(0, 0, w, h, corner=0)]
    runs, _ = headline(24, 44, 30, 14, 20)
    body += runs
    body.append(ink.text(w - 24, 44, CAPTION, 12, "body", "mu", anchor="end"))
    svg, css = rack(24, 60, w - 48, ink.ENTERED, 56, 0, glow, 8)
    body.append(svg)
    return ink.doc(w, h, "".join(body), label(), mode, extra_css=css)


def record_phone_svg() -> str:
    w = ink.WP
    per_row = -(-ink.ENTERED // 2)
    height, gap = 44, 12
    y_rack = 52
    y_caption = y_rack + 2 * height + gap + 6 + 24
    h = y_caption + 16
    body = [ink.plate(0, 0, w, h, corner=0)]
    runs, _ = headline(16, 38, 26, 12, 0, sep="·")
    body += runs
    svg, css = rack(16, y_rack, w - 32, per_row, height, gap, True, 7)
    body.append(svg)
    body.append(ink.text(16, y_caption, CAPTION, 12, "body", "mu"))
    return ink.doc(w, h, "".join(body), label(), "dark", extra_css=css)


def main() -> None:
    files = {"record.svg": record_svg("dark"), "record-light.svg": record_svg("light"),
             "record-phone.svg": record_phone_svg()}
    changed = sum(ink.write_svg(OUT / name, svg) for name, svg in files.items())
    print(f"arena: {changed} of {len(files)} file(s) changed in {OUT.as_posix()}")


if __name__ == "__main__":
    main()
