"""Draw 论剑台, the Sword-Discussion Arena record: one sword per hackathon entered.

58 swords stand in the rack (two rows of 29 on phones); the 35 that won are
gilded, the rest stay dark iron. In the dark the gilded ones take their gold
one after another as the picture loads; the picture without animation is the
finished rack. The record lives in ink.WON / ink.ENTERED.

Run from the repo root: python scripts/generate_arena.py
Writes assets/arena/record.svg, record-light.svg, record-phone.svg.
"""

from __future__ import annotations

from pathlib import Path

import ink

OUT = Path("assets/arena")


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
         animate: bool, sword_w: float) -> tuple[str, str]:
    """(svg, css). Gilded swords first: a tally, not a timeline."""
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
    if animate:
        out.append('<g class="glow">' + "".join(
            f'<path d="{d}" class="au gd" style="animation-delay:{0.3 + i * 0.035:.2f}s"/>' for i, d in won) + "</g>")
        css = f".gd{{animation:argild .5s ease-out backwards}}@keyframes argild{{from{{fill:{ink.palette('dark')['track']}}}}}"
    else:
        out.append(f'<path d="{"".join(d for _, d in won)}" class="au"/>')
    # the rack: a stone ledge under each row
    rows = -(-ink.ENTERED // per_row)
    for r in range(rows):
        y = y_top + r * (height + row_gap) + height + 3
        out.append(ink.rect(x0 - 4, y, width + 8, 3, "lnf", 1.5))
    return "".join(out), css


def label() -> str:
    pct = round(100 * ink.WON / ink.ENTERED)
    return (f"Sword-Discussion Arena record: {ink.WON} hackathons won out of {ink.ENTERED} entered ({pct}%). "
            f"One sword per hackathon; {ink.WON} are gilded.")


def headline(x: float, y: float, size: float, compact: bool) -> list[str]:
    pct = round(100 * ink.WON / ink.ENTERED)
    out = [ink.text(x, y, "论剑", size * 1.15, "brush", "au")]
    x += ink.measure("论剑", size * 1.15, "brush") + 14
    parts = [(str(ink.WON), "au", "display"), (" won", "mu", "body"), ("   ·   ", "mu", "body"),
             (str(ink.ENTERED), "tx", "display"), (" entered", "mu", "body")]
    for text_, cls, face in parts:
        s = size * (1.3 if face == "display" else 0.55)
        out.append(ink.text(x, y - (0 if face == "display" else 1), text_, s, face, cls))
        x += ink.measure(text_, s, face)
    if not compact:
        out.append(ink.text(x + 20, y - 1, f"{pct}% of the swords drawn came back gilded", size * 0.5, "body", "mu"))
    return out


def record_svg(mode: str) -> str:
    w, h = ink.W, 168
    animate = mode == "dark"
    body = [ink.plate(0, 0, w, h, corner=14)]
    body += headline(26, 46, 24, compact=False)
    svg, css = rack(26, 70, w - 52, ink.ENTERED, 74, 0, animate, 8)
    body.append(svg)
    return ink.doc(w, h, "".join(body), label(), mode, extra_css=css)


def record_phone_svg() -> str:
    w = ink.WP
    per_row = -(-ink.ENTERED // 2)
    height, gap = 50, 16
    h = 62 + 2 * height + gap + 22
    body = [ink.plate(0, 0, w, h, corner=12)]
    body += headline(16, 40, 20, compact=True)
    svg, css = rack(16, 58, w - 32, per_row, height, gap, True, 7)
    body.append(svg)
    pct = round(100 * ink.WON / ink.ENTERED)
    body.append(ink.text(w - 16, 40, f"{pct}%", 12, "mono", "mu", anchor="end"))
    return ink.doc(w, h, "".join(body), label(), "dark", extra_css=css)


def main() -> None:
    files = {"record.svg": record_svg("dark"), "record-light.svg": record_svg("light"),
             "record-phone.svg": record_phone_svg()}
    changed = sum(ink.write_svg(OUT / name, svg) for name, svg in files.items())
    print(f"arena: {changed} of {len(files)} file(s) changed in {OUT.as_posix()}")


if __name__ == "__main__":
    main()
