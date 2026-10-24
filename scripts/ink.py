"""ink: the design system of 日月神教, the Sun Moon Divine Sect.

Every SVG on the profile is drawn through this module, so the page reads as
one sect, in the same dress as art3m1s.me. Stdlib only. Nothing here touches
the network or README.md.

Ground   gold on ink at night (dark), ink on aged paper by day (light). The
         ground is the site's own ink (#0E0C14) and paper (#F4ECDC).
Type     glyph outlines, never <text>: scripts/ink_glyphs/<face>.json holds
         the outlines (cut by generate_glyphs.py), and every run of text is
         drawn as <use> of one <path> per glyph, so every OS shows the same
         letters and Chinese never falls back to empty boxes. A character
         missing from its table raises MissingGlyph: the renderer keeps the
         old files instead of drawing a hole.
           brush    Ma Shan Zheng       Chinese names, seals (16 px and up)
           serif    Noto Serif SC 500   small Chinese labels
           display  Instrument Serif    "Bill Zhang", place names
           body     Geist 400           sentences and labels
           medium   Geist 500           emphasis
           mono     Geist Mono 400      numbers, dates, missions
         Chinese inside a Latin run is set in the serif automatically.
Colour   gold = lit, won, active. jade = you can act here (and qi).
         danger = the formation's backlash, a qi deviation, nothing else.
         seal red = seals only. Everything else is paper, ink and muted.
Light    the same drawing with mode="light". Served only through
         <picture><source media="(prefers-color-scheme: light)">.
Stills   nothing on the profile moves: doc() refuses @keyframes and <animate>
         in every mode (CLAUDE.md, "Stills only"). The reduced-motion rule in
         css() stays as a harmless guard.
Ornament the site's own path data (app/sect/sect.css, ornaments.tsx,
         lib/sect/logo.ts): cloud corners, brush strokes, the ink ring, the
         worn seal and the sun-and-moon logo.
"""

from __future__ import annotations

import json
import math
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from xml.sax.saxutils import escape

# --- who -----------------------------------------------------------------------

NAME = "Bill Zhang"
WON, ENTERED = 36, 59          # lifetime hackathon record (the log holds only the greatest hits)
SITE = "https://art3m1s.me"
ACCOUNT_CREATED = datetime(2021, 9, 21, tzinfo=timezone.utc)
SECT_ZH = "日月神教"
SECT_EN = "Sun Moon Divine Sect"

W = 846    # desktop README column
WP = 360   # phone design width

# --- colour ----------------------------------------------------------------------

TOKENS = {
    "dark": {
        "ground": "#0E0C14", "raised": "#1B1826", "track": "#2A2433", "line": "#4D402C",
        "text": "#F5ECDC", "muted": "#A89F91", "gold": "#E9C77E", "ember": "#C98A4B",
        "jade": "#8FE3C8", "seal": "#B8412D", "danger": "#F0A089", "cut": "#F5ECDC",
    },
    "light": {
        "ground": "#F4ECDC", "raised": "#EBE0C8", "track": "#DDD0B4", "line": "#C4AE86",
        "text": "#1F1A17", "muted": "#6B5F50", "gold": "#7A5518", "ember": "#A0742C",
        "jade": "#2C6E5A", "seal": "#A8321F", "danger": "#A8321F", "cut": "#F4ECDC",
    },
}
MODES = (("dark", ""), ("light", "-light"))

# class -> token. Fills are the bare name; strokes end in -s.
FILLS = {"bg": "ground", "rs": "raised", "tk": "track", "lnf": "line", "tx": "text", "mu": "muted",
         "au": "gold", "em": "ember", "jd": "jade", "sl": "seal", "dg": "danger", "ct": "cut"}
STROKES = {"ln": "line", "bg-s": "ground", "tk-s": "track", "tx-s": "text", "mu-s": "muted",
           "au-s": "gold", "em-s": "ember", "jd-s": "jade", "sl-s": "seal", "dg-s": "danger",
           "ct-s": "cut"}

REDUCED_MOTION = "@media (prefers-reduced-motion: reduce){*{animation:none!important}}"
GLOW = ('<filter id="inkglow" x="-40%" y="-40%" width="180%" height="180%">'
        '<feGaussianBlur stdDeviation="2.4" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')


def palette(mode: str) -> dict[str, str]:
    return TOKENS[mode]


def css(mode: str, extra: str = "") -> str:
    p = palette(mode)
    rules = [f".{k}{{fill:{p[v]}}}" for k, v in FILLS.items()]
    rules += [f".{k}{{stroke:{p[v]};fill:none}}" for k, v in STROKES.items()]
    rules.append(".glow{filter:url(#inkglow)}" if mode == "dark" else ".glow{filter:none}")
    return "<style>" + "".join(rules) + extra + REDUCED_MOTION + "</style>"


def fmt(v: float) -> str:
    if isinstance(v, int):
        return str(v)
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def plural(n: int, word: str, many: str = "") -> str:
    return f"{n} {word}" if n == 1 else f"{n} {many or word + 's'}"


def attr(s: str) -> str:
    return escape(s, {'"': "&quot;"})


# --- glyphs -------------------------------------------------------------------------

GLYPH_DIR = Path(__file__).resolve().with_name("ink_glyphs")
FACE_CODES = {"brush": "k", "serif": "s", "display": "d", "body": "b", "medium": "w", "mono": "m"}
CODE_FACES = {code: face for face, code in FACE_CODES.items()}
LATIN_FACES = ("display", "body", "medium", "mono")
UPM = 1000


class MissingGlyph(KeyError):
    """A character the glyph tables do not hold. Renderers catch it and keep
    the old files: a hole in a word is worse than yesterday's picture."""


@lru_cache(maxsize=None)
def face_table(face: str) -> dict:
    table = json.loads((GLYPH_DIR / f"{face}.json").read_text(encoding="utf-8"))
    if table.get("upm") != UPM:
        raise ValueError(f"{face}: glyph table must be cut at {UPM} units per em")
    return table


def is_cjk(ch: str) -> bool:
    return ord(ch) >= 0x2E80 and not 0xFE00 <= ord(ch) <= 0xFE0F


def _face_for(face: str, ch: str) -> str:
    if face == "brush":
        return "brush" if is_cjk(ch) else "body"
    if face == "serif":
        return "serif" if is_cjk(ch) or ch == "·" else "body"
    return "serif" if is_cjk(ch) else face


def glyph_id(face: str, ch: str) -> str:
    return f"g{FACE_CODES[face]}{ord(ch):x}"


def _layout(s: str, face: str, tracking: float = 0.0) -> tuple[list[tuple[str, str, float]], float]:
    """[(face, char, pen position in em)] and the run's advance in em.
    In the mono face a Chinese character takes two cells, centred."""
    items: list[tuple[str, str, float]] = []
    pen = 0.0
    cell = face_table("mono")["glyphs"]["0"][0] / UPM if face == "mono" else 0.0
    for ch in s:
        f = _face_for(face, ch)
        glyph = face_table(f)["glyphs"].get(ch)
        if glyph is None:
            if ch == " ":
                adv = cell or 0.28
                pen += adv + tracking
                continue
            raise MissingGlyph(f"{face}: no glyph for {ch!r} (U+{ord(ch):04X}); re-run generate_glyphs.py")
        adv = glyph[0] / UPM
        offset = 0.0
        if face == "mono" and f != "mono":
            wide = 2 * cell
            offset, adv = (wide - adv) / 2, wide
        if glyph[1]:
            items.append((f, ch, pen + offset))
        pen += adv + tracking
    return items, (pen - tracking if s else 0.0)


def measure(s: str, size: float, face: str = "body", tracking: float = 0.0) -> float:
    """Width in px of `s` set at `size` px (tracking in em)."""
    return _layout(s, face, tracking)[1] * size


def check(s: str, face: str = "body") -> None:
    """Raise MissingGlyph if any character of `s` cannot be drawn."""
    _layout(s, face)


def text(x: float, y: float, s: str, size: float, face: str = "body", cls: str = "tx",
         anchor: str = "start", tracking: float = 0.0, extra: str = "") -> str:
    """One run of outlined text, baseline at y. Returns '' for an empty run.
    The group carries data-run="x0 x1" (its ink box, in the parent's units)
    so tests can check that nothing spills out of a panel."""
    if not s:
        return ""
    items, width_em = _layout(s, face, tracking)
    width = width_em * size
    x0 = x - width if anchor == "end" else x - width / 2 if anchor == "middle" else x
    k = size / UPM
    uses = "".join(f'<use href="#{glyph_id(f, ch)}"' + (f' x="{round(pen * UPM)}"' if pen else "") + "/>"
                   for f, ch, pen in items)
    cls_attr = f' class="{cls}"' if cls else ""
    return (f'<g{cls_attr} data-run="{fmt(x0)} {fmt(x0 + width)}" '
            f'transform="translate({fmt(x0)} {fmt(y)}) scale({fmt_k(k)} {fmt_k(-k)})"{extra}>{uses}</g>')


def fmt_k(k: float) -> str:
    return f"{k:.5f}".rstrip("0").rstrip(".")


Part = tuple  # (text, cls) or (text, cls, face)


def runs(x: float, y: float, parts: list[Part], size: float, face: str = "body",
         anchor: str = "start") -> tuple[str, float]:
    """Several coloured runs on one baseline. Returns (svg, total width)."""
    widths = [measure(p[0], size, p[2] if len(p) > 2 else face) for p in parts]
    total = sum(widths)
    pen = x - total if anchor == "end" else x - total / 2 if anchor == "middle" else x
    out = []
    for p, w in zip(parts, widths):
        if p[0].strip():
            out.append(text(pen, y, p[0], size, p[2] if len(p) > 2 else face, p[1]))
        pen += w
    return "".join(out), total


def fit(s: str, width: float, size: float, face: str = "body") -> str:
    """Clip to `width` px, ending in '...' when anything was cut. Whole
    words go first; a single long word is cut by characters."""
    if measure(s, size, face) <= width:
        return s
    while " " in s.strip() and measure(s.rstrip(" ,;:-") + "...", size, face) > width:
        s = s.rstrip().rsplit(" ", 1)[0]
    while s and measure(s.rstrip(" ,;:-") + "...", size, face) > width:
        s = s[:-1]
    return s.rstrip(" ,;:-") + "..." if s else ""


def wrap(s: str, width: float, size: float, face: str = "body", max_lines: int = 0) -> list[str]:
    """Greedy word wrap by measured width. A word longer than a line is cut
    by characters. With max_lines, the last line is clipped with '...'."""
    lines: list[str] = []
    line = ""
    for word in s.split():
        trial = f"{line} {word}" if line else word
        if measure(trial, size, face) <= width:
            line = trial
            continue
        if line:
            lines.append(line)
        while measure(word, size, face) > width and len(word) > 1:
            cut = len(word)
            while cut > 1 and measure(word[:cut], size, face) > width:
                cut -= 1
            lines.append(word[:cut])
            word = word[cut:]
        line = word
    if line:
        lines.append(line)
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines - 1] + [fit(" ".join(lines[max_lines - 1:]), width, size, face)]
    return lines


def balanced(s: str, width: float, size: float, face: str = "body", max_lines: int = 2) -> list[str]:
    """Wrap, then narrow the measure while the line count holds, so a two-line
    wrap never ends on one orphaned word."""
    lines = wrap(s, width, size, face, max_lines)
    if len(lines) < 2 or lines[-1].endswith("..."):
        return lines
    trial_w = width
    while trial_w > width * 0.5:
        trial_w -= 4
        trial = wrap(s, trial_w, size, face)
        if len(trial) != len(lines):
            break
        lines = trial
    return lines


def glyph_defs(markup: str) -> str:
    """One <path id> for every glyph the markup uses."""
    out = []
    for code, hexcode in sorted(set(re.findall(r'href="#g([a-z])([0-9a-f]+)"', markup))):
        face = CODE_FACES[code]
        ch = chr(int(hexcode, 16))
        out.append(f'<path id="g{code}{hexcode}" d="{face_table(face)["glyphs"][ch][1]}"/>')
    return "".join(out)


# --- the document ------------------------------------------------------------------


def doc(w: float, h: float, body: str, label: str, mode: str = "dark", defs: str = "",
        extra_css: str = "") -> str:
    """A complete SVG. `label` is the accessible description (aria-label and
    <title>): the same facts a sighted visitor gets. Stills only: a document
    that tries to animate raises ValueError."""
    glow = GLOW if "glow" in body and mode == "dark" else ""
    out = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{fmt(w)}" height="{fmt(h)}" '
           f'viewBox="0 0 {fmt(w)} {fmt(h)}" role="img" aria-label="{attr(label)}">'
           f"<title>{escape(label)}</title>{css(mode, extra_css)}"
           f"<defs>{glyph_defs(body + defs)}{glow}{defs}</defs>{body}</svg>\n")
    if "@keyframes" in out or "<animate" in out:
        raise ValueError("stills only: no SVG on the profile animates")
    return out


def write_svg(path: str | Path, content: str) -> bool:
    """Validate, then write only if changed. True when the file changed.
    Raises ValueError on malformed XML, so a bad render never lands on disk."""
    try:
        ET.fromstring(content)
    except ET.ParseError as error:
        raise ValueError(f"refusing to write malformed SVG {path}: {error}") from error
    target = Path(path)
    data = content.encode("utf-8")
    if target.exists() and target.read_bytes() == data:
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return True


# --- shapes ---------------------------------------------------------------------------


def rect(x: float, y: float, w: float, h: float, cls: str, rx: float = 0, extra: str = "") -> str:
    r = f' rx="{fmt(rx)}"' if rx else ""
    return f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}"{r} class="{cls}"{extra}/>'


def hline(x0: float, x1: float, y: float, cls: str = "ln", width: float = 1, extra: str = "") -> str:
    return (f'<path d="M{fmt(x0)} {fmt(y)}H{fmt(x1)}" class="{cls}" stroke-width="{fmt(width)}"{extra}/>')


def vline(x: float, y0: float, y1: float, cls: str = "ln", width: float = 1, extra: str = "") -> str:
    return (f'<path d="M{fmt(x)} {fmt(y0)}V{fmt(y1)}" class="{cls}" stroke-width="{fmt(width)}"{extra}/>')


# The site's ornaments (app/sect/sect.css), verbatim path data.
CLOUD = ("M35 1.6H17.2C15.6 1.6 14.6 2.6 14.6 3.9C14.6 5.4 15.9 6.3 17.2 6.1C18.3 5.9 18.8 5 18.5 4.2"
         "M1.6 35V17.2C1.6 15.6 2.6 14.6 3.9 14.6C5.4 14.6 6.3 15.9 6.1 17.2C5.9 18.3 5 18.8 4.2 18.5"
         "M14.6 3.9C10.8 2.4 6.6 3.4 4.6 6.4C2.8 9.2 3.2 12.4 5.4 14.2C3.4 12 3.8 8.6 6.4 7C8.4 5.8 11 6.4 "
         "12 8.2C12.9 9.8 12 11.6 10.4 11.8C9.2 12 8.4 11 8.8 10")
CLOUD_SM = ("M19 1.4H8.6C7 1.4 6 2.4 6 3.6C6 4.8 7 5.5 7.9 5.3C8.6 5.1 8.9 4.4 8.6 3.8"
            "M1.4 19V8.6C1.4 7 2.4 6 3.6 6C4.8 6 5.5 7 5.3 7.9C5.1 8.6 4.4 8.9 3.8 8.6"
            "M6 3.6C3.8 3.4 2.2 5 2.6 6.8")
BRUSH = ("M3 6.4C2.2 4.2 4.4 2.6 7.4 2.5C10 2.4 13 3 17 3.1C33 3.4 52 3.2 72 3.6C90 3.9 104 4.6 118.5 5.9"
         "C113 6.4 104 6.7 92 7.3C74 8.1 52 8.6 33 8.9C22 9.1 13 9.6 8.6 9.6C5.4 9.6 3.6 8.4 3 6.4Z"
         "M46 5.2C62 4.9 80 5.1 101 5.7L101 6.05C80 5.7 62 5.6 46 5.75Z"
         "M58 7.3C72 7 84 6.8 96 6.6L96 6.85C84 7.1 72 7.4 58 7.65Z"
         "M30 4.6C40 4.4 49 4.4 56 4.5L56 4.75C49 4.7 40 4.8 30 4.95Z")
BRUSH_RULE = ("M0 4.4C30 3.2 80 2.5 140 2.4C200 2.3 270 2.6 330 3.1C360 3.4 385 3.9 400 4.6"
              "C384 5.2 360 5.5 330 5.7C270 6 200 6.1 140 5.9C80 5.7 30 5.3 0 4.4Z"
              "M60 3.9C100 3.5 150 3.4 190 3.5L190 3.85C150 3.8 100 3.9 60 4.25Z"
              "M230 4.7C270 4.6 310 4.7 350 4.9L350 5.15C310 5 270 5 230 5.05Z"
              "M120 4.9C150 4.8 175 4.85 205 4.95L205 5.2C175 5.15 150 5.15 120 5.2Z")
ENSO = ("M20 4.2C29.4 4 36.1 11.4 35.8 20.4C35.5 29.6 27.8 36.2 19 35.7C10.6 35.2 4.4 28.6 4.3 20.6"
        "C4.2 14.6 7.4 9.6 12 6.9C8.6 9.8 6.6 14.6 7.1 19.8C7.8 27.4 13.6 32.8 20.4 32.8"
        "C27.4 32.8 33.2 27.2 33.2 20.2C33.2 13 27.4 7.6 20.8 7.3C17.4 7.2 15 7.9 13.4 8.8"
        "C15.2 6.2 17.4 4.3 20 4.2Z")
SEAL_40 = ((3.6, 3.2), (12, 2.7), (20.4, 3.1), (29, 2.6), (36.8, 3.5), (37.2, 12), (36.9, 20.6),
           (37.4, 29), (36.5, 36.8), (28, 37.3), (19.6, 36.9), (11.2, 37.4), (3.1, 36.6), (2.7, 28.2),
           (3.2, 19.6), (2.6, 11.4))


def corners(x: float, y: float, w: float, h: float, size: float = 16, cls: str = "au-s",
            large: bool = False, width: float = 1.4, extra: str = "") -> str:
    """祥云 auspicious-cloud corners on a box, as on the site's dialogue panels."""
    vb = 36 if large else 20
    d = CLOUD if large else CLOUD_SM
    s = size / vb
    sw = fmt(width / s)
    out = []
    for tx, ty, sx, sy in ((x, y, s, s), (x + w, y, -s, s), (x, y + h, s, -s), (x + w, y + h, -s, -s)):
        out.append(f'<path d="{d}" transform="translate({fmt(tx)} {fmt(ty)}) scale({fmt_k(sx)} {fmt_k(sy)})" '
                   f'class="{cls}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"{extra}/>')
    return "".join(out)


def corner(x: float, y: float, size: float = 16, flip_x: bool = False, flip_y: bool = False,
           cls: str = "au-s", large: bool = False, width: float = 1.4, extra: str = "") -> str:
    """One cloud corner; (x, y) is the box corner it hugs."""
    vb = 36 if large else 20
    s = size / vb
    return (f'<path d="{CLOUD if large else CLOUD_SM}" transform="translate({fmt(x)} {fmt(y)}) '
            f'scale({fmt_k(-s if flip_x else s)} {fmt_k(-s if flip_y else s)})" class="{cls}" '
            f'stroke-width="{fmt(width / s)}" stroke-linecap="round" stroke-linejoin="round"{extra}/>')


def brush(x: float, y: float, w: float, h: float, cls: str = "au", extra: str = "") -> str:
    """The short brush stroke under a title: pressed on the left, flicked off right."""
    return (f'<path d="{BRUSH}" fill-rule="evenodd" class="{cls}" '
            f'transform="translate({fmt(x)} {fmt(y)}) scale({fmt_k(w / 120)} {fmt_k(h / 12)})"{extra}/>')


def brush_rule(x: float, y: float, w: float, h: float = 6, cls: str = "au", extra: str = "") -> str:
    """A long dry stroke, thin at both ends, with streaks of flying white."""
    return (f'<path d="{BRUSH_RULE}" fill-rule="evenodd" class="{cls}" '
            f'transform="translate({fmt(x)} {fmt(y)}) scale({fmt_k(w / 400)} {fmt_k(h / 8)})"{extra}/>')


def enso(cx: float, cy: float, r: float, cls: str = "au", extra: str = "") -> str:
    """The ink ring: thick where the brush landed, tapering to its tail."""
    s = r / 16
    return (f'<path d="{ENSO}" class="{cls}" '
            f'transform="translate({fmt(cx - 20 * s)} {fmt(cy - 20 * s)}) scale({fmt_k(s)})"{extra}/>')


def seal_path(size: float) -> str:
    k = size / 40
    return "M" + "L".join(f"{fmt(px * k)} {fmt(py * k)}" for px, py in SEAL_40) + "Z"


def seal(x: float, y: float, size: float, char: str = "神", tilt: float = -3.0, crack: bool = False,
         extra: str = "") -> str:
    """The sect's seal, pressed by hand: one character cut in paper white out
    of a worn cinnabar square, set a touch askew (ornaments.tsx SealStamp).
    crack=True: the seal split by a qi deviation. (x, y) is the top left."""
    k = size / 40
    c = size / 2
    out = [f'<g transform="translate({fmt(x)} {fmt(y)}) rotate({fmt(tilt)} {fmt(c)} {fmt(c)})"{extra}>',
           f'<path d="{seal_path(size)}" class="sl"/>',
           f'<path d="{seal_path(size)}" class="sl-s" stroke-width="{fmt(0.9 * k)}" stroke-linejoin="round"/>',
           f'<path d="M{fmt(6.7 * k)} {fmt(6.6 * k)}H{fmt(33.3 * k)}V{fmt(33.4 * k)}H{fmt(6.7 * k)}Z" '
           f'class="ct-s" stroke-opacity=".5" stroke-width="{fmt(max(0.6, k))}"/>']
    out.append(glyph_centred(char, c, c, 25 * k, "brush", "ct"))
    if crack:
        out.append(f'<path d="M{fmt(23 * k)} {fmt(1 * k)}L{fmt(19 * k)} {fmt(11 * k)}L{fmt(24 * k)} {fmt(17 * k)}'
                   f'L{fmt(17 * k)} {fmt(27 * k)}L{fmt(21 * k)} {fmt(31 * k)}L{fmt(16 * k)} {fmt(40 * k)}" '
                   f'class="bg-s" stroke-width="{fmt(1.6 * k)}" stroke-linejoin="round"/>')
    out.append("</g>")
    return "".join(out)


def glyph_centred(ch: str, cx: float, cy: float, size: float, face: str = "brush", cls: str = "tx") -> str:
    """One glyph centred on its ink box (seals, keys, single brush marks)."""
    f = _face_for(face, ch)
    glyph = face_table(f)["glyphs"].get(ch)
    if glyph is None:
        raise MissingGlyph(f"{face}: no glyph for {ch!r}")
    x0, y0, x1, y1 = glyph[2]
    k = size / UPM
    tx = cx - (x0 + x1) / 2 * k
    ty = cy + (y0 + y1) / 2 * k
    return (f'<g class="{cls}" data-run="{fmt(cx - (x1 - x0) / 2 * k)} {fmt(cx + (x1 - x0) / 2 * k)}" '
            f'transform="translate({fmt(tx)} {fmt(ty)}) scale({fmt_k(k)} {fmt_k(-k)})">'
            f'<use href="#{glyph_id(f, ch)}"/></g>')


# --- the sect's logo (PortfolioV5 client/src/lib/sect/logo.ts) ---------------------------
# A sun cradled in a crescent moon on the cinnabar seal: 日月, sun and moon. The
# colours are the site's own and the same by day and night (it is a stamp).

LOGO_COLORS = {"ink": "#0e0c14", "cinnabar": "#b8412d", "paper": "#f5ecdc", "gold": "#e9c77e"}
LOGO_GEOMETRY = {
    "bold": {"moon": (28.6, 35.4, 21.2), "bite": (37.4, 26.6, 17.4), "sun": (41.2, 22.9, 7.6)},
    "full": {"moon": (29.6, 34.4, 16.6), "bite": (36.6, 27.4, 13.6), "sun": (39.4, 24.6, 5)},
}


def _f(n: float) -> str:
    return str(round(n * 100) / 100).removesuffix(".0")


def logo_seal_path(reach: float) -> str:
    k = 64 * reach / 34.8
    return "M" + "L".join(f"{_f(32 + (x - 20) * k)} {_f(32 + (y - 20) * k)}" for x, y in SEAL_40) + "Z"


def crescent_path(moon: tuple[float, float, float], bite: tuple[float, float, float]) -> str:
    x1, y1, r1 = moon
    x2, y2, r2 = bite
    dx, dy = x2 - x1, y2 - y1
    d = math.hypot(dx, dy)
    a = (r1 * r1 - r2 * r2 + d * d) / (2 * d)
    h = math.sqrt(max(0.0, r1 * r1 - a * a))
    px, py = x1 + a * dx / d, y1 + a * dy / d
    ax, ay = px + h * -dy / d, py + h * dx / d
    bx, by = px - h * -dy / d, py - h * dx / d
    return (f"M{_f(ax)} {_f(ay)}A{_f(r1)} {_f(r1)} 0 1 1 {_f(bx)} {_f(by)}"
            f"A{_f(r2)} {_f(r2)} 0 0 0 {_f(ax)} {_f(ay)}Z")


def _sunburst(sun: tuple[float, float, float], r0: float = 6.4, r1: float = 10.2, half: float = 0.13) -> str:
    sx, sy, _ = sun

    def p(a: float, r: float) -> str:
        return f"{_f(sx + math.cos(a) * r)} {_f(sy + math.sin(a) * r)}"

    d = ""
    for i in range(12):
        a = i / 12 * math.pi * 2
        length = r1 * 0.86 if i % 2 else r1
        d += f"M{p(a - half, r0)}L{p(a, length)}L{p(a + half, r0)}Z"
    return d


def logo_markup(bold: bool = False, reach: float | None = None) -> str:
    """The logo's inner markup in its 64-unit box (logo.ts logoMarkup)."""
    c = LOGO_COLORS
    reach = reach if reach is not None else (1.0 if bold else 0.96)
    g = LOGO_GEOMETRY["bold" if bold else "full"]
    parts = []
    if bold:
        parts.append(f'<path d="{logo_seal_path(reach)}" fill="{c["cinnabar"]}"/>')
    else:
        parts.append(f'<path d="{logo_seal_path(reach)}" fill="{c["cinnabar"]}" stroke="{c["cinnabar"]}" '
                     'stroke-width=".9" stroke-linejoin="round"/>')
        inset = 32 - 32 * reach + 64 * reach * 0.105
        side = 64 - 2 * inset
        parts.append(f'<rect x="{_f(inset)}" y="{_f(inset)}" width="{_f(side)}" height="{_f(side)}" fill="none" '
                     f'stroke="{c["paper"]}" stroke-opacity=".5" stroke-width="1.1"/>')
    s = reach / (1.0 if bold else 0.96)
    emblem = (f'<path d="{crescent_path(g["moon"], g["bite"])}" fill="{c["paper"]}"/>'
              f'<circle cx="{_f(g["sun"][0])}" cy="{_f(g["sun"][1])}" r="{_f(g["sun"][2])}" fill="{c["gold"]}"/>'
              + ("" if bold else f'<path d="{_sunburst(g["sun"])}" fill="{c["gold"]}"/>'))
    if abs(s - 1) < 1e-9:
        parts.append(emblem)
    else:
        parts.append(f'<g transform="translate(32 32) scale({round(s * 1000) / 1000}) translate(-32 -32)">'
                     f"{emblem}</g>")
    return "".join(parts)


def logo(x: float, y: float, size: float, bold: bool = True, extra: str = "") -> str:
    return (f'<g transform="translate({fmt(x)} {fmt(y)}) scale({fmt_k(size / 64)})"{extra}>'
            f"{logo_markup(bold=bold)}</g>")


# --- the moon ----------------------------------------------------------------------------

NEW_MOON_EPOCH = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)
SYNODIC_DAYS = 29.530588853


def moon_phase(now: datetime) -> tuple[float, bool, str]:
    """(illuminated fraction 0..1, waxing?, phase name). The name follows the
    illumination, so the two never contradict each other."""
    age = ((now - NEW_MOON_EPOCH).total_seconds() / 86400.0) % SYNODIC_DAYS
    frac = age / SYNODIC_DAYS
    illum = (1 - math.cos(2 * math.pi * frac)) / 2
    waxing = frac < 0.5
    pct = illum * 100
    if pct < 2:
        name = "new moon"
    elif pct > 98:
        name = "full moon"
    elif 46 <= pct <= 54:
        name = "first quarter" if waxing else "last quarter"
    elif pct < 46:
        name = "waxing crescent" if waxing else "waning crescent"
    else:
        name = "waxing gibbous" if waxing else "waning gibbous"
    return illum, waxing, name


def moon_lit_path(cx: float, cy: float, r: float, illum: float, waxing: bool) -> str:
    """The lit part of the disc: one limb arc and the terminator's half
    ellipse (northern sky: a waxing moon is lit on the right)."""
    k = 1 - 2 * illum
    rx = abs(k) * r
    top, bottom = f"{fmt(cx)} {fmt(cy - r)}", f"{fmt(cx)} {fmt(cy + r)}"
    crescent = illum < 0.5
    if waxing:
        limb, term = 1, (0 if crescent else 1)
    else:
        limb, term = 0, (1 if crescent else 0)
    if illum >= 0.995:
        return (f"M{top}A{fmt(r)} {fmt(r)} 0 0 1 {bottom}A{fmt(r)} {fmt(r)} 0 0 1 {top}Z")
    if illum <= 0.005:
        return ""
    return f"M{top}A{fmt(r)} {fmt(r)} 0 0 {limb} {bottom}A{fmt(max(rx, 0.01))} {fmt(r)} 0 0 {term} {top}Z"


def moon(cx: float, cy: float, r: float, illum: float, waxing: bool, mode: str, uid: str = "m",
         lit_cls: str = "", dark_cls: str = "") -> str:
    """Tonight's moon: the dark disc, the lit part with soft maria, an
    earthshine rim. uid keeps clip ids unique within one document."""
    lit = moon_lit_path(cx, cy, r, illum, waxing)
    # night: a paper-white moon on dark iron; day: a pale disc in an ink-wash sky
    lit_cls = lit_cls or ("tx" if mode == "dark" else "bg")
    dark_cls = dark_cls or ("tk" if mode == "dark" else "lnf")
    out = [f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="{fmt(r)}" class="{dark_cls}"/>']
    if lit:
        out.append(f'<clipPath id="{uid}lit"><path d="{lit}"/></clipPath>')
        out.append(f'<path d="{lit}" class="{lit_cls}"/>')
        # maria: the old seas of the moon, faint, inside the lit part only
        seas = ((-0.22, -0.28, 0.30, 0.22), (0.18, -0.05, 0.26, 0.2), (-0.05, 0.3, 0.22, 0.16),
                (0.32, 0.36, 0.14, 0.11), (-0.38, 0.12, 0.16, 0.13))
        maria = "".join(f'<ellipse cx="{fmt(cx + dx * r)}" cy="{fmt(cy + dy * r)}" rx="{fmt(ex * r)}" '
                        f'ry="{fmt(ey * r)}"/>' for dx, dy, ex, ey in seas)
        tone = "mu" if mode == "dark" else "em"
        out.append(f'<g clip-path="url(#{uid}lit)" class="{tone}" opacity="{".22" if mode == "dark" else ".14"}">'
                   f"{maria}</g>")
    out.append(f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="{fmt(r - 0.5)}" class="mu-s" stroke-opacity=".35" '
               'stroke-width="1"/>')
    return "".join(out)


# --- panels ----------------------------------------------------------------------------------


def plate(x: float, y: float, w: float, h: float, corner: float = 16, large: bool = False,
          fill: str = "bg", frame: str = "ln", corner_cls: str = "au-s", rx: float = 3) -> str:
    """A sect dialogue plate: ink ground, a hairline frame, cloud corners."""
    out = [rect(x, y, w, h, fill, rx),
           f'<rect x="{fmt(x + 0.5)}" y="{fmt(y + 0.5)}" width="{fmt(w - 1)}" height="{fmt(h - 1)}" '
           f'rx="{fmt(rx)}" class="{frame}" stroke-width="1"/>']
    if corner:
        inset = 4
        out.append(corners(x + inset, y + inset, w - 2 * inset, h - 2 * inset, corner, corner_cls, large))
    return "".join(out)


def paper_grain(w: float, h: float, uid: str = "grain", opacity: float = 0.07) -> tuple[str, str]:
    """Light mode only: a faint fibre grain over the paper. (defs, overlay)."""
    defs = (f'<filter id="{uid}" x="0" y="0" width="100%" height="100%">'
            '<feTurbulence type="fractalNoise" baseFrequency="0.9 0.35" numOctaves="2" seed="7"/>'
            '<feColorMatrix values="0 0 0 0 0.35 0 0 0 0 0.25 0 0 0 0 0.12 0 0 0 1.1 -0.45"/></filter>')
    overlay = (f'<rect width="{fmt(w)}" height="{fmt(h)}" filter="url(#{uid})" opacity="{fmt(opacity)}" '
               'pointer-events="none"/>')
    return defs, overlay


def local_now() -> datetime:
    """Bill's clock (America/Los_Angeles) when tzdata exists, else UTC."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Los_Angeles"))
    except Exception:
        return datetime.now(timezone.utc)


def week_seed() -> tuple[int, str]:
    """(seed, label) from Bill's ISO week: every redraw in a week agrees."""
    year, week, _ = local_now().isocalendar()
    return year * 100 + week, f"{year}-W{week:02d}"
