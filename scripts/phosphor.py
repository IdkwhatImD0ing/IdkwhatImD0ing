"""The phosphor design system: one surface, one font, three meaningful colors.

Every SVG on the profile is drawn through this module, so the whole page reads
as one machine. Stdlib only. Nothing here touches the network or README.md.

Surface  #151B23 panels with rx 6. That is GitHub's own code-block background,
         so drawn panes and real ``` blocks look like the same material.
Type     GitHub's code font stack. Every run of text is locked to a 0.6em
         character grid with textLength, so columns line up on Consolas,
         SF Mono and DejaVu alike. Display type is a 5x7 dot matrix drawn as
         rects (identical on every OS).
Color    phosphor (#00FF41) = lit, won, active. amber (#FFB000) = warning, or
         "you can act here". red (#FF5555) = kernel panic, nothing else.
         Everything else is GitHub's own ink and muted grays.
Light    "safe mode": the same drawings on GitHub's light code-block panel,
         with the phosphor accent swapped for amber. Served only through
         <picture> sources, never through prefers-color-scheme inside an SVG
         (that follows the OS, not the visitor's GitHub theme).
Motion   t=0 is the finished frame. Animation may only add motion on top of a
         complete picture, and prefers-reduced-motion switches all of it off.
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

FONT = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"
CW = 0.6  # monospace advance width, in em

W = 846   # desktop README content column
WP = 360  # phone design width (served via <source media="(max-width: 600px)">)

SIZE = 13        # body text
SIZE_CHROME = 12  # pane titles, status bars, labels
LINE = 20        # body line height

# The machine. tianni (天逆) is the Heaven Defying Bead from Renegade Immortal: the
# one artifact bound to its owner, with an old soul living inside (here, the LLM
# daemon that rewrites this page). Rename it here and nowhere else.
HOST = "tianni"
MACHINE = "Tianni Rev 5080"
PROMPT = f"bill@{HOST}:~$ "

WINDOWS = ("boot", "ships", "fsck", "etc")

DARK = {
    "canvas": "#0D1117",  # GitHub dark page
    "panel": "#151B23",   # GitHub dark code block: every drawn surface
    "line": "#3D444D",    # inactive pane borders, key edges
    "fg": "#F0F6FC",      # body text (== code-block text)
    "mu": "#9198A1",      # secondary text, labels, inactive windows
    "acc": "#00FF41",     # phosphor: lit, won, active
    "acct": "#B6F5C4",    # long phosphor text (vibrates less than pure green)
    "accd": "#149238",    # dim phosphor: accent labels, unlit outlines
    "track": "#123D22",   # unlit meter cells
    "ghost": "#162A1E",   # unlit dot-matrix dots
    "chip": "#00FF41",    # filled accent chips (active window, F-keys, WIN tags)
    "ink": "#0D1117",     # text on chips
    "warn": "#FFB000",    # amber: warnings, "you can act here"
    "red": "#FF5555",     # kernel panic only
    "key": "#21262D",     # raised key face
    "keyhi": "#3D444D",   # raised key top bevel
    "keylo": "#010409",   # raised key bottom bevel
    "flat": "#0D1117",    # pressed / revealed cell
    "flatline": "#262C36",
}

LIGHT = {  # safe mode
    "canvas": "#FFFFFF",
    "panel": "#F6F8FA",
    "line": "#D1D9E0",
    "fg": "#1F2328",
    "mu": "#59636E",
    "acc": "#9A6700",
    "acct": "#7D4E00",
    "accd": "#B08800",
    "track": "#EFE3C4",
    "ghost": "#EEE8DA",
    "chip": "#FFB000",
    "ink": "#1F2328",
    "warn": "#BC4C00",
    "red": "#CF222E",
    "key": "#E6EAEF",
    "keyhi": "#FFFFFF",
    "keylo": "#C4CCD5",
    "flat": "#FFFFFF",
    "flatline": "#D1D9E0",
}

MODES = {"dark": DARK, "light": LIGHT}

REDUCED_MOTION = "@media (prefers-reduced-motion: reduce){*{animation:none!important}}"
BLINK = ".blink{animation:phblink 1.06s steps(1) infinite}@keyframes phblink{0%,49%{opacity:1}50%,100%{opacity:0}}"


# --- document ----------------------------------------------------------------


def palette(mode: str) -> dict[str, str]:
    return MODES[mode]


def css(mode: str, extra: str = "") -> str:
    """Class rules for one mode. Fill classes: .cv .pn .ln-f .fg .mu .acc .acct
    .accd .tr .gh .chip .ink .warn .red .key .khi .klo .flat. Stroke classes
    end in -s (.ln .acc-s .accd-s .warn-s .red-s .fl-s). .glow is a phosphor
    bloom in dark mode and a no-op in safe mode."""
    p = palette(mode)
    fills = {
        "cv": "canvas", "pn": "panel", "ln-f": "line", "fg": "fg", "mu": "mu", "acc": "acc",
        "acct": "acct", "accd": "accd", "tr": "track", "gh": "ghost", "chip": "chip",
        "ink": "ink", "warn": "warn", "red": "red", "key": "key", "khi": "keyhi",
        "klo": "keylo", "flat": "flat",
    }
    strokes = {"ln": "line", "acc-s": "acc", "accd-s": "accd", "warn-s": "warn", "red-s": "red",
               "fl-s": "flatline", "mu-s": "mu"}
    rules = [f"text{{font-family:{FONT}}}"]
    rules += [f".{k}{{fill:{p[v]}}}" for k, v in fills.items()]
    rules += [f".{k}{{stroke:{p[v]};fill:none}}" for k, v in strokes.items()]
    rules.append(".glow{filter:url(#phglow)}" if mode == "dark" else ".glow{filter:none}")
    return "<style>" + "".join(rules) + BLINK + extra + REDUCED_MOTION + "</style>"


GLOW_DEFS = (
    '<filter id="phglow" x="-20%" y="-40%" width="140%" height="180%">'
    '<feGaussianBlur stdDeviation="2.2" result="b"/>'
    '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
)


def svg(w: float, h: float, body: str, label: str, mode: str = "dark",
        extra_css: str = "", defs: str = "", fluid: bool = False) -> str:
    """A complete SVG document. `label` is the accessible description: write it
    so a screen-reader user gets the same facts a sighted visitor does.
    fluid=True drops the viewBox and spans 100% of the width at 1:1 scale, so a
    strip (the status bars) never shrinks its text in a narrow column; draw it
    with percentage x positions for anything anchored to the right edge."""
    size = f'width="100%" height="{fmt(h)}"' if fluid else f'width="{fmt(w)}" height="{fmt(h)}" viewBox="0 0 {fmt(w)} {fmt(h)}"'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" {size} '
        f'role="img" aria-label="{escape(label, {chr(34): "&quot;"})}">'
        f"<title>{escape(label)}</title>"
        f"{css(mode, extra_css)}<defs>{GLOW_DEFS}{defs}</defs>{body}</svg>\n"
    )


def write_svg(path: str | Path, content: str) -> bool:
    """Validate, then write only if changed. Returns True when the file changed.
    Raises ValueError on malformed XML so a bad render never lands on disk."""
    try:
        ET.fromstring(content)
    except ET.ParseError as error:
        raise ValueError(f"refusing to write malformed SVG {path}: {error}") from error
    target = Path(path)
    if target.exists() and target.read_text(encoding="utf-8") == content:
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8", newline="\n")
    return True


# --- primitives ----------------------------------------------------------------


def fmt(v: float) -> str:
    return f"{v:.1f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v)


def text_width(s: str, size: float = SIZE) -> float:
    return len(s) * CW * size


def text(x: float, y: float, s: str, cls: str = "fg", size: float = SIZE, anchor: str = "start",
         bold: bool = False, extra: str = "") -> str:
    """Monospace text locked to the 0.6em grid, so layout is platform-proof."""
    if not s:
        return ""
    attrs = f'x="{fmt(x)}" y="{fmt(y)}" class="{cls}" font-size="{fmt(size)}"'
    if bold:
        attrs += ' font-weight="700"'
    if anchor != "start":
        attrs += f' text-anchor="{anchor}"'
    if len(s) > 1:
        attrs += f' textLength="{fmt(text_width(s, size))}" lengthAdjust="spacing"'
    return f'<text {attrs} xml:space="preserve"{extra}>{escape(s)}</text>'


def runs(x: float, y: float, parts: list[tuple[str, str]], size: float = SIZE, extra: str = "") -> str:
    """One terminal line built from colored runs, each placed on the grid.
    A class ending in '!' is bold: [("$ ", "acc"), ("whoami", "fg!")]."""
    out, col = [], 0
    cw = CW * size
    for chunk, cls in parts:
        if chunk.strip():
            bold = cls.endswith("!")
            out.append(text(x + col * cw, y, chunk, cls.rstrip("!"), size, bold=bold, extra=extra))
        col += len(chunk)
    return "".join(out)


def panel(x: float, y: float, w: float, h: float, cls: str = "pn") -> str:
    return f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" rx="6" class="{cls}"/>'


def hline(x0: float, x1: float, y: float, cls: str = "ln") -> str:
    return f'<line x1="{fmt(x0)}" y1="{fmt(y)}" x2="{fmt(x1)}" y2="{fmt(y)}" class="{cls}" stroke-width="1"/>'


def vline(x: float, y0: float, y1: float, cls: str = "ln") -> str:
    return f'<line x1="{fmt(x)}" y1="{fmt(y0)}" x2="{fmt(x)}" y2="{fmt(y1)}" class="{cls}" stroke-width="1"/>'


def pane_title(x0: float, x1: float, y: float, left: str, right: str = "", active: bool = False,
               size: float = SIZE_CHROME, inset: float = 0, right_cls: str = "") -> str:
    """tmux pane-border-status: a 1px border line with the title knocked into it.
    Active panes get a phosphor border and bold title; the rest stay gray."""
    cw = CW * size
    line_cls = "acc-s" if active else "ln"
    title_cls = "acc" if active else "mu"
    x0, x1 = x0 + inset, x1 - inset
    lx = x0 + 12
    out = [hline(x0, lx - 6, y, line_cls), text(lx, y + size * 0.33, left, title_cls, size, bold=active)]
    end = x1
    if right:
        rw = text_width(right, size)
        rx = x1 - 12 - rw
        out.append(text(rx, y + size * 0.33, right, right_cls or title_cls, size))
        out.append(hline(rx + rw + 6, x1, y, line_cls))
        end = rx - 6
    out.append(hline(lx + len(left) * cw + 6, end, y, line_cls))
    return "".join(out)


def status_bar(active: int, width: float, right: str = "", compact: bool = False,
               size: float = SIZE_CHROME, y0: float = 0, height: float = 28,
               windows: tuple[str, ...] = WINDOWS, session: str = HOST,
               fluid: bool = False) -> str:
    """The tmux status line: [session] 0:boot 1:ships* ... "pane title".
    The active window is a filled accent chip; the previous one carries the
    tmux '-' (last window) flag. Compact mode (phones) drops the pane title
    and shows only the window list. fluid=True spans 100% of a fluid svg()
    and pins the pane title (class "rt") to the right edge."""
    cw = CW * size
    base = y0 + height / 2 + size * 0.35
    bar_w = "100%" if fluid else fmt(width)
    out = [f'<rect x="0" y="{fmt(y0)}" width="{bar_w}" height="{fmt(height)}" rx="6" class="pn"/>']
    label = f"[{session}]"
    out.append(text(10, base, label, "acc", size, bold=True))
    col = len(label) + 1
    for i, name in enumerate(windows):
        flag = "*" if i == active else ("-" if i == active - 1 else "")
        win = f"{i}:{name}{flag}"
        lx = 10 + col * cw
        if i == active:
            out.append(f'<rect x="{fmt(lx - 4)}" y="{fmt(y0 + 5)}" width="{fmt(len(win) * cw + 8)}" '
                       f'height="{fmt(height - 10)}" rx="2" class="chip"/>')
            out.append(text(lx, base, win, "ink", size, bold=True))
        else:
            out.append(text(lx, base, win, "mu", size))
        # The chip overhangs its label by 4px each side, so compact mode (1-col
        # gaps) needs an extra column on both sides of the active window.
        col += len(win) + (2 if not compact or i in (active - 1, active) else 1)
    if right and not compact:
        title = f'"{right}"'
        if fluid:
            out.append(f'<text x="100%" dx="-10" y="{fmt(base)}" class="mu rt" font-size="{fmt(size)}" '
                       f'text-anchor="end" textLength="{fmt(text_width(title, size))}" lengthAdjust="spacing" '
                       f'xml:space="preserve">{escape(title)}</text>')
        else:
            out.append(text(width - 10, base, title, "mu", size, anchor="end"))
    return "".join(out)


def meter(x: float, y: float, total: int, lit: int, cell: float = 6, gap: float = 2,
          height: float = 12, on: str = "acc", off: str = "tr", per_row: int = 0,
          row_gap: float = 3) -> str:
    """Segmented bar: `lit` of `total` cells filled. per_row>0 wraps into rows."""
    out = []
    per_row = per_row or total
    for i in range(total):
        r, c = divmod(i, per_row)
        cls = on if i < lit else off
        out.append(f'<rect x="{fmt(x + c * (cell + gap))}" y="{fmt(y + r * (height + row_gap))}" '
                   f'width="{fmt(cell)}" height="{fmt(height)}" class="{cls}"/>')
    return "".join(out)


# --- 5x7 dot-matrix display face -------------------------------------------------

GLYPHS: dict[str, tuple[str, ...]] = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."),
    "D": ("###..", "#..#.", "#...#", "#...#", "#...#", "#..#.", "###.."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "#.#.#", ".#.#."),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", "#...#", ".#.#.", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "0": (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("#####", "...#.", "..#..", "...#.", "....#", "#...#", ".###."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": ("..##.", ".#...", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "...#.", ".##.."),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    "/": (".....", "....#", "...#.", "..#..", ".#...", "#....", "....."),
    ":": (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    "%": ("##...", "##..#", "...#.", "..#..", ".#...", "#..##", "...##"),
    " ": (".....",) * 7,
}


def dot_width(s: str, px: float) -> float:
    """Width of a dot-matrix string: 5 dots per glyph plus a 1-dot gap."""
    return max(len(s) * 6 - 1, 0) * px


def dot_text(s: str, x: float, y: float, px: float, on: str = "acc", off: str | None = "gh",
             tear_rows: tuple[int, ...] = (), tear: float = 0.0, dot: float | None = None) -> str:
    """5x7 dot matrix drawn as rects. `off` draws the unlit dots too (the LED
    look); pass None for a clean face. tear_rows shifts those rows sideways by
    `tear` px (the panic-week glitch). Unknown characters render as blanks."""
    size = dot if dot is not None else max(px - 1, 1)
    lit, unlit = [], []
    cx = x
    for ch in s.upper():
        rows = GLYPHS.get(ch, GLYPHS[" "])
        for ry, row in enumerate(rows):
            dx = tear if ry in tear_rows else 0
            for rx, bit in enumerate(row):
                if bit == "#":
                    lit.append(f'<rect x="{fmt(cx + rx * px + dx)}" y="{fmt(y + ry * px)}" '
                               f'width="{fmt(size)}" height="{fmt(size)}"/>')
                elif off and ch != " ":
                    unlit.append(f'<rect x="{fmt(cx + rx * px)}" y="{fmt(y + ry * px)}" '
                                 f'width="{fmt(size)}" height="{fmt(size)}"/>')
        cx += 6 * px
    out = ""
    if unlit:
        out += f'<g class="{off}">' + "".join(unlit) + "</g>"
    out += f'<g class="{on}">' + "".join(lit) + "</g>"
    return out


# --- moon (same synodic math as the old MOTD) ------------------------------------

NEW_MOON_EPOCH = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)
SYNODIC_DAYS = 29.530588853


def moon_phase(now: datetime) -> tuple[float, bool, str]:
    """(illuminated fraction 0..1, waxing?, phase name). The name follows the
    illumination so the two never contradict each other."""
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
