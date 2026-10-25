"""Draw the record plate: 36 / 59 over the sword row, and one line of mine.

The plate is stop 04 of the map, 论剑台 (the Sword-Discussion Arena), where the
map's Hackathons row lands. It reads like a game's record screen: the place's
name in the brush hand with its English name and stop number (as on the title
cards), the record set big (the 36 in gold, the one number on this screen),
one thing I said in an interview, and under it the rack: one sword per
hackathon entered, the 36 that won gilded, the rest dark iron.

Gold means won (and, in the tag, the place's name, as on the map). It is a
still picture (stills only, see CLAUDE.md); in the dark the gold swords carry
a soft glow, which is a filter, not motion. The record lives in ink.WON /
ink.ENTERED; the place's names come from art_map.STOPS. The quote is mine,
word for word, from the interview in IdkwhatImD0ing/hackathonstarterkit
(.deslop/voice-profile.md, Stance 3, approved 2026-09-14).

Run from the repo root: python scripts/generate_arena.py
Writes assets/arena/record.svg, record-light.svg, record-phone.svg. The
README's alt text for the plate is label() below; keep the two the same.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

import art_journal
import art_map
import ink

OUT = Path("assets/arena")
QUOTE = "Just cause you lost at a hackathon doesn’t mean it’s a bad project."   # curly apostrophes: drawn type
QUOTE_FROM = "ME, IN AN INTERVIEW, SEP 2026"
QUOTE_FROM_SPOKEN = "Me, in an interview, September 2026"
COUNT_LABEL = "HACKATHONS WON"


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
         glow: bool, sword_w: float) -> str:
    """The swords, gold first, on a stone ledge under each row."""
    pitch = width / per_row
    won, dark = [], []
    for i in range(ink.ENTERED):
        r, c = divmod(i, per_row)
        x = x0 + pitch * (c + 0.5)
        top = y_top + r * (height + row_gap)
        (won if i < ink.WON else dark).append(sword_d(x, top, height, sword_w))
    out = [f'<path d="{"".join(dark)}" class="tk"/>',
           f'<path d="{"".join(dark)}" class="ln" stroke-width=".8"/>']
    gold = f'<path d="{"".join(won)}" class="au"/>'
    out.append(f'<g class="glow">{gold}</g>' if glow else gold)
    rows = -(-ink.ENTERED // per_row)
    for r in range(rows):
        y = y_top + r * (height + row_gap) + height + 3
        out.append(ink.rect(x0 - 4, y, width + 8, 3, "lnf", 1.5))
    return "".join(out)


def stop() -> tuple[int, str, str]:
    """(number, Chinese name, English name) of the arena on the map."""
    _sid, n, zh, en, *_ = next(s for s in art_map.STOPS if s[0] == "arena")
    return n, zh, en


def label() -> str:
    """The plate's alt text: every word it draws, in plain words."""
    n, zh, en = stop()
    pct = round(100 * ink.WON / ink.ENTERED)
    return (f"Stop {n:02d} of {len(art_map.STOPS)} on the map, {zh} ({en}): Hackathons. "
            f"{ink.WON} hackathons won out of {ink.ENTERED} entered ({pct}%). "
            f"One sword for each hackathon, gold for a win. "
            f"“{QUOTE}” {QUOTE_FROM_SPOKEN}.")


def tag(n: int, en: str, short: bool = False) -> str:
    return f"{en.upper()}  ·  STOP {n:02d}" + ("" if short else f" OF {len(art_map.STOPS)}")


def eyebrow(x: float, y: float, size_zh: float, size_tag: float, width: float) -> str:
    """The place, as on the title cards: its name in the brush hand, then its
    English name and stop number in gold caps (shorter when the line is narrow)."""
    n, zh, en = stop()
    out = [ink.text(x, y + 1, zh, size_zh, "brush", "tx")]
    tx = x + ink.measure(zh, size_zh, "brush") + 12
    for s in (tag(n, en), tag(n, en, short=True), en.upper()):
        if tx + ink.measure(s, size_tag, "medium", 0.16) <= x + width:
            break
    out.append(ink.text(tx, y, s, size_tag, "medium", "au", tracking=0.16, extra=' opacity=".9"'))
    return "".join(out)


def numbers(x: float, base: float, big: float, small: float, label_size: float) -> tuple[str, float]:
    """36 big in gold; / 59 raised so its top meets the 36's; HACKATHONS WON on
    the 36's baseline under the 59. Returns (svg, right edge)."""
    cap = 0.73          # Instrument Serif's figures stand 730 units of 1000
    out = [ink.text(x, base, str(ink.WON), big, "display", "au")]
    x2 = x + ink.measure(str(ink.WON), big, "display") + big * 0.16
    raised = base - (big - small) * cap
    out.append(ink.text(x2, raised, f"/ {ink.ENTERED}", small, "display", "tx"))
    lx = x2 + small * 0.05
    out.append(art_journal.caps(lx, base, COUNT_LABEL, "mu", label_size, 0.14))
    right = max(x2 + ink.measure(f"/ {ink.ENTERED}", small, "display"),
                lx + ink.measure(COUNT_LABEL, label_size, "medium", 0.14))
    return "".join(out), right


def quote(x1: float, y: float, width: float, size: float, lh: float, attr_size: float,
          attr_gap: float) -> tuple[str, float]:
    """My line, right-aligned, drawn whole or not at all. Returns (svg, last baseline)."""
    text = f"“{QUOTE}”"
    lines = ink.balanced(text, width, size, "display", 3)
    if "".join(lines).replace(" ", "") != text.replace(" ", ""):
        raise ValueError("the record's quote does not fit whole")
    out = []
    for i, line in enumerate(lines):
        out.append(ink.text(x1, y + i * lh, line, size, "display", "tx", anchor="end"))
    y += (len(lines) - 1) * lh + attr_gap
    out.append(art_journal.caps(x1, y, QUOTE_FROM, "mu", attr_size, 0.14, anchor="end"))
    return "".join(out), y


DESK = dict(W=ink.W, H=172, x0=40, eyebrow=35, base=101, big=64, small=30, quote=24, quote_lh=28,
            quote_top=57, rack_top=117, sword_h=40, sword_w=8)
PHONE = dict(W=ink.WP, x0=26, eyebrow=40, base=98, big=46, small=26, quote=20, quote_lh=25,
             sword_h=40, row_gap=12, sword_w=7)


def record_svg(mode: str) -> str:
    k = DESK
    w, h, x0 = k["W"], k["H"], k["x0"]
    x1 = w - x0
    body = [eyebrow(x0, k["eyebrow"], 24, 12, w / 2 + 40 - x0)]
    nums, right = numbers(x0, k["base"], k["big"], k["small"], 12)
    body.append(nums)
    q, last = quote(x1, k["quote_top"], x1 - right - 120, k["quote"], k["quote_lh"], 12, 20)
    body.append(q)
    if last > k["rack_top"] - 8:
        raise ValueError("the record's quote runs into the swords")
    body.append(rack(x0, k["rack_top"], x1 - x0, ink.ENTERED, k["sword_h"], 0, mode == "dark", k["sword_w"]))
    defs, page = art_journal.sheet(w, h, mode, corners=True)
    return ink.doc(w, h, page + "".join(body), label(), mode, defs=defs)


def record_phone_svg() -> str:
    """Phones get this dark file in both themes, so it carries its own ground."""
    k = PHONE
    w, x0 = k["W"], k["x0"]
    x1 = w - x0
    body = [eyebrow(x0, k["eyebrow"], 22, 11, x1 - x0)]
    nums, _ = numbers(x0, k["base"], k["big"], k["small"], 11)
    body.append(nums)
    q, last = quote(x1, k["base"] + 44, x1 - x0, k["quote"], k["quote_lh"], 11, 22)
    body.append(q)
    per_row = -(-ink.ENTERED // 2)
    y_rack = last + 24
    body.append(rack(x0, y_rack, x1 - x0, per_row, k["sword_h"], k["row_gap"], True, k["sword_w"]))
    h = int(y_rack + 2 * k["sword_h"] + k["row_gap"] + 6 + 22)
    h += h % 2
    defs, page = art_journal.sheet(w, h, "dark", corners=True)
    return ink.doc(w, h, page + "".join(body), label(), "dark", defs=defs)


def check_readme_alt(readme: Path = Path("README.md")) -> None:
    """The README's alt for the plate is hand-written; say so when it no longer
    matches the words the plate draws."""
    if not readme.exists():
        return
    m = re.search(r'<img src="assets/arena/record\.svg"[^>]*alt="([^"]*)"', readme.read_text(encoding="utf-8"))
    if not m:
        print("arena: WARNING: no <img> for assets/arena/record.svg in the README")
    elif html.unescape(m.group(1)) != label():
        print("arena: WARNING: the README's alt for the record plate differs from label(); paste this:\n"
              + html.escape(label(), quote=True))


def main() -> None:
    files = {"record.svg": record_svg("dark"), "record-light.svg": record_svg("light"),
             "record-phone.svg": record_phone_svg()}
    changed = sum(ink.write_svg(OUT / name, svg) for name, svg in files.items())
    print(f"arena: {changed} of {len(files)} file(s) changed in {OUT.as_posix()}")
    check_readme_alt()


if __name__ == "__main__":
    main()
