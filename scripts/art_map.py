"""The map screen: the top of the profile is the map you get by pressing M on art3m1s.me.

Pure drawing (stdlib): scripts/generate_map.py cuts the site's painted map and
its opening poster into strips (Pillow, local only) and calls render_all()
here to draw the tiles. Nothing here touches the network.

One panel, cut into 13 tiles that the README stacks with <br>, each inside its
own link (GitHub has no image maps, so one link per picture):

  head     the poster band: 日月神教 SUN MOON DIVINE SECT, the carved seal and
           "Bill Zhang", his line, and the gold ENTER ART3M1S.ME key
  11 rows  one per stop, top (11, the summit) to bottom (01, the gate). Each
           row is a strip of the painting in its scroll mount, the stop's
           medallion on the dotted route, and its legend entry: number, place
           name, English name, the README section and one plain fact
  foot     how to use it, and the bridge to the site's own map key (M)

Rows are cut halfway between stops, so each stop's medallion and legend sit in
their own tile. Every tile carries its painting strip inside it (an SVG shown
by <img> cannot load other files), with a few pixels of bleed so no seam shows.

Files (assets/map/): <tile>.svg (dark), <tile>-light.svg, <tile>-phone.svg
(phones get the dark drawing in both themes, so it carries its own ground).
The gate row also has -still twins: its red ink ring draws itself once
(ink.doc motion="once"); the README serves the still under
prefers-reduced-motion.
"""

from __future__ import annotations

import base64
import json
import math
from pathlib import Path

import ink

DATA = Path("scripts/data/map")
OUT = Path("assets/map")
REPO = "IdkwhatImD0ing/IdkwhatImD0ing"

# Top to bottom, as the legend reads (the painting has the summit at the top).
# (id, stop, Chinese name, English name, README section, one plain fact, link, rank)
# Rank 1: the three rows a recruiter wants, set bigger. 0: the gate, "you are here".
STOPS = (
    ("summit", 11, "望月台", "Moon-Gazing Terrace", "Contact", "billzhangsc@gmail.com", "#contact", 2),
    ("abode", 10, "洞府", "Cave Abode", "Now", "3 repos I'm working on", "#now", 2),
    ("formation", 9, "护宗大阵", "Grand Sect-Protecting Formation", "Play", "Minesweeper on GitHub issues", "#play", 2),
    ("scroll", 8, "玉简阁", "Jade Slip Pavilion", "Résumé", "PDF", "https://art3m1s.me/resume.pdf", 2),
    ("steles", 7, "碑林", "Stele Forest", "Tools", "TypeScript and Python", "#tools", 2),
    ("library", 6, "藏经阁", "Scripture Pavilion", "School", "USC, UC Santa Cruz", "#school", 2),
    ("mission", 5, "任务殿", "Mission Hall", "Work", "Pinterest, Scale AI, RingCentral", "#work", 1),
    ("arena", 4, "论剑台", "Sword-Discussion Arena", "Hackathons", f"{ink.WON} won of {ink.ENTERED}", "#hackathons", 1),
    ("forge", 3, "炼器峰", "Artifact Forge Peak", "Shipped", "4 builds, 3 of them won", "#shipped", 1),
    ("mirror", 2, "心镜台", "Heart-Mirror Terrace", "About", "", "#about", 2),
    ("gate", 1, "山门", "Mountain Gate", "You are here", "", ink.SITE, 0),
)
ORDER = tuple(s[0] for s in STOPS)
TILES = ("head",) + ORDER + ("foot",)
RING_STOP = "gate"

NAME_LINE = "builds voice-first LLM agents at Pinterest"
KEY_LABEL = "ENTER ART3M1S.ME"

# The painting (the site's public/sect/map/map_full.webp) and the part of it shown.
MAP_W, MAP_H = 2048, 3072
V0, V1 = 0.035, 0.94
BLEED = 3            # painting drawn past each tile's edge, in CSS px: no seam at odd scales

KINDS = {
    #       panel width, header, painting x and width, the u range shown, pixels per CSS px,
    #       medallion radius, ink ring radius, how far the rods stick out, foot, gaps
    "desk": dict(W=ink.W, head=200, px=46, pw=304, u0=0.19, u1=0.81, R=2, r_med=14.0, ring_r=30.0,
                 rod_out=12, foot=54, gap_top=34, gap_bottom=37, lx=390),
    "phone": dict(W=ink.WP, head=330, px=20, pw=150, u0=0.33, u1=0.70, R=3, r_med=11.5, ring_r=24.0,
                  rod_out=8, foot=46, gap_top=30, gap_bottom=33, lx=202),
}
HEAD_PHONE_PICTURE = 156     # the poster band's height on the phone header


# --- geometry ----------------------------------------------------------------------------


def stops_data() -> dict:
    """Stop positions and the route, as (u, v) on the painting, measured on the
    live map at art3m1s.me (scripts/data/map/stops.json)."""
    return json.loads((DATA / "stops.json").read_text(encoding="utf-8"))


def layout(kind: str) -> dict:
    """Every position the cut and the drawing share. Tile edges are whole CSS px."""
    k = dict(KINDS[kind])
    data = stops_data()
    s = k["pw"] / ((k["u1"] - k["u0"]) * MAP_W)
    ph = (V1 - V0) * MAP_H * s
    py = k["head"] + k["gap_top"]
    uv = {st["id"]: (st["u"], st["v"]) for st in data["stops"]}

    def X(u: float) -> float:
        return k["px"] + (u - k["u0"]) * MAP_W * s

    def Y(v: float) -> float:
        return py + (v - V0) * MAP_H * s

    vs = [uv[i][1] for i in ORDER]
    mids = [round(Y((a + b) / 2)) for a, b in zip(vs, vs[1:])]
    rows_bottom = round(py + ph) + k["gap_bottom"]
    cuts = [0, k["head"], *mids, rows_bottom, rows_bottom + k["foot"]]
    k.update(s=s, ph=ph, py=py, H=cuts[-1], cuts=cuts, rows_bottom=rows_bottom,
             at={i: (X(u), Y(v)) for i, (u, v) in uv.items()},
             route=[(X(u), Y(v)) for u, v in data["route_uv"]])
    return k


def tile_band(geo: dict, name: str) -> tuple[int, int]:
    i = TILES.index(name)
    return geo["cuts"][i], geo["cuts"][i + 1]


def strip_band(geo: dict, name: str) -> tuple[float, float] | None:
    """The part of the painting a row tile shows, with bleed (CSS px), or None."""
    y0, y1 = tile_band(geo, name)
    top, bottom = geo["py"], geo["py"] + geo["ph"]
    a, b = max(top, y0 - BLEED), min(bottom, y1 + BLEED)
    return (a, b) if b > a else None


# --- the site's map pieces (map-emblems.tsx, map-view.tsx, sect.css) ------------------------


def _bagua() -> str:
    out = []
    for k in range(8):
        a = (22.5 + 45 * k + 22.5) * math.pi / 180
        cx, cy = 20 + 9.6 * math.cos(a), 20 + 9.6 * math.sin(a)
        tx, ty, h = -math.sin(a), math.cos(a), 2.6

        def p(x: float, y: float) -> str:
            return f"{x:.2f} {y:.2f}"

        if k % 2 == 0:
            out.append(f'<path d="M{p(cx - tx * h, cy - ty * h)}L{p(cx + tx * h, cy + ty * h)}"/>')
        else:
            out.append(f'<path d="M{p(cx - tx * h, cy - ty * h)}L{p(cx - tx * .7, cy - ty * .7)}'
                       f'M{p(cx + tx * .7, cy + ty * .7)}L{p(cx + tx * h, cy + ty * h)}"/>')
    return "".join(out)


_FC = 'fill="currentColor" stroke="none"'
# Each stop's emblem in a 40 x 40 box, copied from the site's map-emblems.tsx.
EMBLEMS = {
    "gate": (f'<path d="M11 11.8C14.5 12.4 17.4 11 20 8.6C22.6 11 25.5 12.4 29 11.8L27.8 14H12.2Z" {_FC}/>'
             f'<path d="M5 16.6C7.4 17 9.4 16 10.8 14.6C11.6 15.6 12.6 16.2 13.6 16.4L13 18H6Z" {_FC}/>'
             f'<path d="M35 16.6C32.6 17 30.6 16 29.2 14.6C28.4 15.6 27.4 16.2 26.4 16.4L27 18H34Z" {_FC}/>'
             '<path d="M14.2 14V31M25.8 14V31M7.6 18V31M32.4 18V31M12.6 19.4H27.4"/>'
             '<path d="M17.6 14.6H22.4V17.4H17.6Z" stroke-width="1.2"/>'
             '<path d="M12.6 31.4H15.8M24.2 31.4H27.4M6.4 31.4H8.8M31.2 31.4H33.6" stroke-width="1.5"/>'),
    "mirror": ('<circle cx="20" cy="16.4" r="9"/>'
               '<circle cx="20" cy="16.4" r="5.9" stroke-width="1" stroke-dasharray="1.5 1.6"/>'
               f'<circle cx="20" cy="16.4" r="1.7" {_FC}/>'
               '<path d="M14.4 12.2A7 7 0 0 1 17.8 9.6" stroke-width="1.2" opacity=".85"/>'
               '<path d="M20 25.4V27.4"/>'
               f'<path d="M13.4 31.6C14.2 28.8 16.9 27.4 20 27.4C23.1 27.4 25.8 28.8 26.6 31.6Z" {_FC}/>'),
    "forge": (f'<path d="M20 6.4C23.8 10 24.8 13.2 22.8 15.8C22.6 14 21.8 13 20.7 12.3C21.1 14.3 19.9 15.6 '
              f'18.6 16.2C16.3 14.6 16.1 11.4 20 6.4Z" {_FC}/>'
              '<path d="M10.6 19.2H29.4M11.6 19.2C11.6 25 15 28.2 20 28.2C25 28.2 28.4 25 28.4 19.2"/>'
              '<path d="M12.8 19.2V16.2H16V19.2M24 19.2V16.2H27.2V19.2" stroke-width="1.5"/>'
              '<path d="M13.6 22.6H26.4" stroke-width="1.1" opacity=".85"/>'
              '<path d="M15.2 27.2L14 31.6M24.8 27.2L26 31.6M20 28.2V31.6"/>'),
    "arena": ('<path d="M13.4 26.6L29.6 10.4M10.2 29.8L13.4 26.6M11.6 23.4L16.6 28.4"/>'
              '<path d="M26.6 26.6L10.4 10.4M29.8 29.8L26.6 26.6M28.4 23.4L23.4 28.4"/>'
              f'<circle cx="9.4" cy="30.6" r="1.2" {_FC}/><circle cx="30.6" cy="30.6" r="1.2" {_FC}/>'),
    "mission": ('<path d="M17.4 10.6Q20 7.6 22.6 10.6"/>'
                '<path d="M13.6 26C13.6 17.8 15.6 11 20 11C24.4 11 26.4 17.8 26.4 26Z"/>'
                '<path d="M11.4 26.4H28.6M15.2 17.6H24.8"/>'
                '<path d="M15 21.6H25" stroke-width="1" opacity=".8"/>'
                f'<circle cx="20" cy="29.4" r="1.7" {_FC}/>'),
    "library": ('<path d="M20 5.6V9.4"/>'
                f'<path d="M13.2 13C16.4 12.4 18.4 11.2 20 9.4C21.6 11.2 23.6 12.4 26.8 13L25.8 14.2H14.2Z" {_FC}/>'
                f'<path d="M11 19.2C15 18.6 17.8 17.2 20 15.4C22.2 17.2 25 18.6 29 19.2L28 20.4H12Z" {_FC}/>'
                f'<path d="M8.6 25.6C13.6 25 17.4 23.4 20 21.4C22.6 23.4 26.4 25 31.4 25.6L30.4 26.8H9.6Z" {_FC}/>'
                '<path d="M16.4 14.2V15.8M23.6 14.2V15.8M14.4 20.4V22.4M25.6 20.4V22.4M12.4 26.8V31.2'
                'M27.6 26.8V31.2M9.4 31.4H30.6"/>'
                '<path d="M18.2 31.2V28.6H21.8V31.2" stroke-width="1.2"/>'),
    "steles": ('<path d="M6.6 30V21C6.6 18.6 10.6 18.6 10.6 21V30M29.4 30V21C29.4 18.6 33.4 18.6 33.4 21V30" '
               'stroke-width="1.3" opacity=".8"/>'
               f'<path d="M13.6 14.8C13.6 8.4 26.4 8.4 26.4 14.8Z" {_FC}/>'
               '<path d="M15 14.8V30M25 14.8V30"/>'
               '<path d="M18 17.4V19.8M18 21.6V24M18 25.8V27.6M22 17.4V19.8M22 21.6V24M22 25.8V27.6" '
               'stroke-width="1.3"/>'
               '<path d="M5.4 30.6H34.6M13.4 30.6V28.8H26.6V30.6" stroke-width="1.5"/>'),
    "scroll": ('<path d="M8.6 11.4H11.4V28.6H8.6ZM12.8 10.6H15.6V29.4H12.8ZM17 11.4H19.8V28.6H17Z'
               'M21.2 10.6H24V29.4H21.2Z" stroke-width="1.4"/>'
               '<circle cx="29" cy="20" r="5.4" stroke-width="1.6"/>'
               '<path d="M29 20.2m-1.9 0a1.9 1.9 0 1 1 1.9 1.9" stroke-width="1.3"/>'
               '<path d="M7.4 16C14 15.2 19.4 16.6 25.4 15.8M7.4 24.4C14 23.6 19.4 25 25.4 24.2" stroke-width="1.4"/>'
               '<path d="M7.4 24.4L5.4 28.4" stroke-width="1.3"/>'
               f'<path d="M5.4 28.4L4.2 31.4H6.6Z" {_FC}/>'),
    "formation": ('<path d="M32 25 L25 32 L15 32 L8 25 L8 15 L15 8 L25 8 L32 15 Z" stroke-width="1.4"/>'
                  f'<g stroke-width="1.5">{_bagua()}</g>'
                  '<circle cx="20" cy="20" r="4.6" stroke-width="1.3"/>'
                  f'<path d="M20 15.4A2.3 2.3 0 0 1 20 20A2.3 2.3 0 0 0 20 24.6A4.6 4.6 0 0 1 20 15.4Z" {_FC}/>'),
    "abode": ('<path d="M6.6 17.4L13.6 9.6L17.6 13.2L22.8 7.4L33.4 17.4" stroke-width="1.5"/>'
              '<path d="M7.4 20.2L9 18.6H31L32.6 20.2"/>'
              '<path d="M9.4 20.2V31M30.6 20.2V31M7.4 31.2H32.6"/>'
              '<path d="M15.2 31A6.4 6.4 0 1 1 24.8 31"/>'),
    "summit": (f'<path d="M19.14 7.5A8.5 8.5 0 1 0 26.9 19.14A7 7 0 0 1 19.14 7.5Z" {_FC}/>'
               '<path d="M10.6 31.4H29.4M12.8 31.4V27.6H27.2V31.4M11.6 27.6H28.4" stroke-width="1.5"/>'),
}

C = ink.MAP_COLORS


def _f(v: float) -> str:
    return ink.fmt(round(v, 2))


def defs_common(mode: str) -> str:
    """Gradients every tile may use: the medallion faces, the rods, the rod caps."""
    def radial(uid: str, stops: tuple[str, str, str], mid: str) -> str:
        return (f'<radialGradient id="{uid}" cx="50%" cy="32%" r="70%"><stop offset="0" stop-color="{stops[0]}"/>'
                f'<stop offset="{mid}" stop-color="{stops[1]}"/><stop offset="1" stop-color="{stops[2]}"/>'
                "</radialGradient>")

    def vertical(uid: str, stops: tuple[str, str, str]) -> str:
        return (f'<linearGradient id="{uid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{stops[0]}"/>'
                f'<stop offset=".55" stop-color="{stops[1]}"/><stop offset="1" stop-color="{stops[2]}"/>'
                "</linearGradient>")

    out = (radial("face", C["face"], ".62") + radial("faceHere", C["face_here"], ".55")
           + vertical("rod", C["rod"]) + vertical("cap", C["cap"]))
    if mode == "light":
        grain_defs, _ = ink.paper_grain(1, 1, "grain")
        out += grain_defs
    return out


def medallion(cx: float, cy: float, r: float, stop: str, here: bool) -> str:
    """The site's stop seal: an ink face, a gold rim, the gold emblem. The stop
    you are at is a gold face with an ink emblem."""
    k = r * 2 * 0.82 / 40
    colour = C["emblem_here"] if here else C["gold"]
    return (f'<circle cx="{_f(cx)}" cy="{_f(cy)}" r="{_f(r + 3.2)}" fill="none" stroke="{C["gold"]}" '
            'stroke-opacity=".6" stroke-width="1.25"/>'
            f'<circle cx="{_f(cx)}" cy="{_f(cy)}" r="{_f(r + 2.2)}" fill="{C["halo"]}" fill-opacity=".9"/>'
            f'<circle cx="{_f(cx)}" cy="{_f(cy)}" r="{_f(r)}" fill="url(#{"faceHere" if here else "face"})" '
            f'stroke="{C["gold"]}" stroke-width="1.5"/>'
            f'<g transform="translate({_f(cx - 20 * k)} {_f(cy - 20 * k)}) scale({ink.fmt_k(k)})" fill="none" '
            f'stroke="{colour}" color="{colour}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
            f"{EMBLEMS[stop]}</g>")


def rod(x0: float, x1: float, y: float, h: float) -> str:
    """A scroll rod with gold caps on its ends."""
    cap_w = 8
    return (f'<rect x="{_f(x0)}" y="{_f(y)}" width="{_f(x1 - x0)}" height="{_f(h)}" rx="{_f(min(5, h / 2))}" '
            'fill="url(#rod)"/>'
            + "".join(f'<rect x="{_f(cx)}" y="{_f(y - 2)}" width="{cap_w}" height="{_f(h + 4)}" rx="3" fill="url(#cap)"/>'
                      for cx in (x0 - 4, x1 - cap_w + 4)))


RING_ARC_START = 258.0   # degrees, screen frame: the ink ring's head is at the top, its tail at the upper left
RING_CSS = (".ringdraw{stroke-dasharray:100 100;"
            "animation:inkring 1.4s cubic-bezier(.45,.05,.25,1) 1.2s 1 both}"
            "@keyframes inkring{from{stroke-dashoffset:100}to{stroke-dashoffset:0}}")


def ring_mask(cx: float, cy: float, r: float) -> str:
    """A mask that uncovers the ink ring along its brush path, head first. The
    ring is drawn as ink.enso; the mask's stroke follows its centre line
    clockwise from the top and runs a little past the start."""
    s = r / 16
    rc, width = 14.25 * s, 8 * s
    a0 = RING_ARC_START

    def p(deg: float) -> str:
        t = math.radians(deg)
        return f"{_f(cx + rc * math.cos(t))} {_f(cy + rc * math.sin(t))}"

    d = (f"M{p(a0)}A{_f(rc)} {_f(rc)} 0 0 1 {p(a0 + 180)}A{_f(rc)} {_f(rc)} 0 0 1 {p(a0 + 360)}"
         f"A{_f(rc)} {_f(rc)} 0 0 1 {p(a0 + 364)}")
    box = r + 6
    return (f'<mask id="inkring" maskUnits="userSpaceOnUse" x="{_f(cx - box)}" y="{_f(cy - box)}" '
            f'width="{_f(2 * box)}" height="{_f(2 * box)}">'
            f'<path d="{d}" pathLength="100" class="ringdraw" fill="none" stroke="{C["mask"]}" '
            f'stroke-width="{_f(width)}" stroke-linecap="butt"/></mask>')


# --- the panel, piece by piece -------------------------------------------------------------
# Every piece is (top, bottom, markup[, owner]) in panel coordinates. A tile keeps the
# pieces that overlap its band and shows them through its own window; a piece with an
# owner (a picture strip) goes only into that tile, so no tile carries its neighbour's
# picture.

Piece = tuple


def pieces(kind: str, mode: str, geo: dict, strips: dict, moving: bool) -> list[Piece]:
    W, H = geo["W"], geo["H"]
    out: list[Piece] = []
    out += header(kind, mode, geo, strips)
    out += scroll(kind, geo, strips)
    for stop in STOPS:
        out += row(kind, mode, geo, stop, moving)
    out += foot(kind, geo)
    # on top of everything: a gold hairline round the whole panel, and cloud corners top left
    # and bottom right (the site's dialogue panels)
    out.append((0, H, f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="3" class="au-s" '
                      'stroke-opacity=".38" stroke-width="1"/>'))
    corner = 30 if kind == "desk" else 24
    out.append((0, corner + 6, ink.corner(4, 4, corner, large=True, width=1.4)))
    out.append((H - corner - 6, H, ink.corner(W - 4, H - 4, corner, flip_x=True, flip_y=True, large=True,
                                              width=1.4)))
    return out


def _jpeg(name: str, strips: dict) -> str:
    return "data:image/jpeg;base64," + strips[name]


def header(kind: str, mode: str, geo: dict, strips: dict) -> list[tuple[float, float, str]]:
    W, head = geo["W"], geo["head"]
    pal = ink.palette(mode)
    ground = pal["ground"]
    desk = kind == "desk"
    pic_h = head if desk else HEAD_PHONE_PICTURE
    src = f"head-{kind}" + ("-light" if mode == "light" else "")
    out = [f'<image href="{_jpeg(src, strips)}" x="0" y="0" width="{W}" height="{pic_h}" '
           'preserveAspectRatio="none"/>']
    # the ink (or paper) fade: from the left behind the words, and at the foot into the panel
    if desk:
        out.append(f'<defs><linearGradient id="fadeL" x1="0" y1="0" x2="1" y2="0">'
                   f'<stop offset="0" stop-color="{ground}" stop-opacity=".95"/>'
                   f'<stop offset=".3" stop-color="{ground}" stop-opacity=".86"/>'
                   f'<stop offset=".56" stop-color="{ground}" stop-opacity=".4"/>'
                   f'<stop offset=".76" stop-color="{ground}" stop-opacity=".08"/>'
                   f'<stop offset="1" stop-color="{ground}" stop-opacity=".22"/></linearGradient></defs>'
                   f'<rect width="{W}" height="{pic_h}" fill="url(#fadeL)"/>')
    out.append(f'<defs><linearGradient id="fadeB" x1="0" y1="0" x2="0" y2="1">'
               f'<stop offset="0" stop-color="{ground}" stop-opacity="0"/>'
               f'<stop offset="{".6" if desk else ".45"}" stop-color="{ground}" stop-opacity="0"/>'
               f'<stop offset="1" stop-color="{ground}" stop-opacity="1"/></linearGradient></defs>'
               f'<rect width="{W}" height="{pic_h + 1}" fill="url(#fadeB)"/>')

    if desk:
        x, eyebrow_y, base, line_y = 36, 50, 120, 160
        name_size, line_size, brush_size, caps_size = 64, 24, 16, 12
    else:
        x, eyebrow_y, base, line_y = 20, 180, 232, 260
        name_size, line_size, brush_size, caps_size = 46, 16, 15, 11
    cap_h = 0.72 * name_size   # Instrument Serif's capital height
    zh_w = ink.measure(ink.SECT_ZH, brush_size, "brush")
    out.append(ink.text(x, eyebrow_y + 1, ink.SECT_ZH, brush_size, "brush", "au"))
    out.append(ink.text(x + zh_w + 12, eyebrow_y, ink.SECT_EN.upper(), caps_size, "medium", "au",
                        tracking=0.3 if desk else 0.22))
    # the carved seal beside the name, as on the site's top bar: as tall as a capital
    seal = round(cap_h)
    out.append(ink.logo(x, base - seal, seal, variant=mode))
    out.append(ink.text(x + seal + (16 if desk else 12), base, ink.NAME, name_size, "display", "tx"))
    out.append(ink.text(x, line_y, NAME_LINE, line_size, "body", "tx", extra=' fill-opacity=".86"'))

    # the one filled key, gold like the site's
    key_size, tracking = 14, 0.16
    label_w = ink.measure(KEY_LABEL, key_size, "medium", tracking)
    if desk:
        kw, kh = round(label_w + 48), 46
        kx, ky = W - 36 - kw, line_y - 34
    else:
        kw, kh = W - 2 * x, 46
        kx, ky = x, 276
    out.append(ink.rect(kx, ky, kw, kh, "au", 2))
    out.append(ink.text(kx + (kw - label_w) / 2, ky + kh / 2 + 5, KEY_LABEL, key_size, "medium", "bg",
                        tracking=tracking))
    return [(0, head, "".join(out), "head")]


def scroll(kind: str, geo: dict, strips: dict) -> list[tuple[float, float, str]]:
    """The painting in its mount, the rods, and the dotted route. The painting
    goes in as one strip per row tile (see strip_band)."""
    px, pw, py, ph = geo["px"], geo["pw"], geo["py"], geo["ph"]
    pb = py + ph
    out: list[tuple[float, float, str]] = []
    # mount: an ink edge, a 6 px brown band, a gold line (sect.css .sect-map-sheet)
    out.append((py - 7, pb + 7,
                f'<rect x="{_f(px - 7)}" y="{_f(py - 7)}" width="{_f(pw + 14)}" height="{_f(ph + 14)}" '
                f'fill="{C["mount_edge"]}" fill-opacity=".6"/>'
                f'<rect x="{_f(px - 6)}" y="{_f(py - 6)}" width="{_f(pw + 12)}" height="{_f(ph + 12)}" '
                f'fill="{C["mount"]}"/>'
                f'<rect x="{_f(px - .5)}" y="{_f(py - .5)}" width="{_f(pw + 1)}" height="{_f(ph + 1)}" fill="none" '
                f'stroke="{C["gold"]}" stroke-opacity=".55" stroke-width="1"/>'))
    for name in ORDER:
        band = strip_band(geo, name)
        meta = strips["rows"][kind][name]
        y = py + meta["px0"] / geo["R"]
        h = (meta["px1"] - meta["px0"]) / geo["R"]
        if not band or abs(band[0] - y) > 1 or abs(band[1] - (y + h)) > 1:
            raise ValueError(f"the {kind} {name} strip does not fit this layout: run generate_map.py cut")
        out.append((y, y + h, f'<image href="{_jpeg(f"{kind}-{name}", strips)}" x="{_f(px)}" y="{_f(y)}" '
                              f'width="{_f(pw)}" height="{_f(h)}" preserveAspectRatio="none"/>', name))
    # rods: the top one thin, the bottom one heavier (it holds the scroll down)
    x0, x1 = px - geo["rod_out"] - 7, px + pw + geo["rod_out"] + 7
    out.append((py - 18, py - 7, rod(x0, x1, py - 16, 7)))
    out.append((pb + 6, pb + 21, rod(x0, x1, pb + 8, 11)))
    # the route: gold beads ringed in ink along the painted walkways (sizes from the site's
    # 824 px tall sheet)
    k = ph / 824
    pts = " ".join(f"{_f(x)},{_f(y)}" for x, y in geo["route"])
    dash = f"0.1 {_f(7.5 * k)}"
    out.append((py, pb, f'<polyline points="{pts}" fill="none" stroke="{C["route_ink"]}" stroke-opacity=".62" '
                        f'stroke-width="{_f(5.4 * k)}" stroke-dasharray="{dash}" stroke-linecap="round" '
                        'stroke-linejoin="round"/>'
                        f'<polyline points="{pts}" fill="none" stroke="{C["gold"]}" stroke-width="{_f(2.7 * k)}" '
                        f'stroke-dasharray="{dash}" stroke-linecap="round" stroke-linejoin="round"/>'))
    return out


def row(kind: str, mode: str, geo: dict, stop: tuple, moving: bool) -> list[tuple[float, float, str]]:
    sid, n, zh, en, section, fact, _href, rank = stop
    cx, cy = geo["at"][sid]
    r = geo["r_med"]
    px, pw, lx = geo["px"], geo["pw"], geo["lx"]
    desk = kind == "desk"
    out: list[tuple[float, float, str]] = []

    # the leader: ink dots across the painting, gold dots from the mount to the legend
    start = cx + (geo["ring_r"] + 3 if sid == RING_STOP else r + 6)   # clear of the medallion (and the ring)
    leader = (f'<path d="M{_f(start)} {_f(cy)}H{_f(px + pw - 2)}" stroke="{C["leader_ink"]}" '
              'stroke-opacity=".75" stroke-width="1.5" stroke-dasharray="0.1 3.4" stroke-linecap="round"/>'
              f'<path d="M{_f(px + pw + 10)} {_f(cy)}H{_f(lx - 10)}" class="au-s" stroke-opacity=".85" '
              'stroke-width="1.2" stroke-dasharray="0.1 3.4" stroke-linecap="round"/>'
              f'<circle cx="{_f(lx - 7)}" cy="{_f(cy)}" r="1.6" class="au"/>')
    out.append((cy - 2, cy + 2, leader))
    out.append((cy - r - 4, cy + r + 4, medallion(cx, cy, r, sid, here=rank == 0)))

    if sid == RING_STOP:
        ring = ink.enso(cx, cy, geo["ring_r"], "sl")
        if moving:
            ring = f'<g mask="url(#inkring)">{ring}</g>'
        out.append((cy - geo["ring_r"] - 1, cy + geo["ring_r"] + 1, ring))

    quiet = ' opacity=".8"' if rank == 2 else ""
    num = f"{n:02d}"
    if desk:
        zx, tx = lx + 24, lx + 128
        title_size = 30 if rank == 1 else 24
        base = cy + (18 if rank == 1 else 16)
        legend = [ink.text(lx, cy + 4.5, num, 12, "body", "au", extra=' opacity=".75"'),
                  ink.text(zx, cy + 8.5, zh, 24, "brush", "tx", extra=quiet),
                  ink.text(tx, cy - 8, en.upper(), 12, "medium", "au", tracking=0.16, extra=' opacity=".9"'),
                  ink.text(tx, base, section, title_size, "display", "au" if rank == 0 else "tx", extra=quiet)]
        fx = tx + ink.measure(section, title_size, "display") + 12
        if sid == "arena":
            legend.append(ink.runs(fx, base, [(str(ink.WON), "au", "medium"), (f" won of {ink.ENTERED}", "mu")], 14)[0])
        elif fact:
            legend.append(ink.text(fx, base, fact, 14, "body", "mu"))
    else:
        title_size = 22 if rank == 1 else 20
        legend = [ink.text(lx, cy - 5, num, 11, "body", "au", extra=' opacity=".75"'),
                  ink.text(lx + 20, cy - 3, zh, 18, "brush", "tx", extra=quiet),
                  ink.text(lx, cy + 18, section, title_size, "display", "au" if rank == 0 else "tx", extra=quiet)]
        if sid == "arena":
            fx = lx + ink.measure(section, title_size, "display") + 7
            legend.append(ink.runs(fx, cy + 18, [(str(ink.WON), "au", "medium"), (f" of {ink.ENTERED}", "mu")], 13)[0])
    out.append((cy - 26, cy + 26, "".join(legend)))
    return out


def keycap(x: float, y: float, label: str, h: float = 22) -> tuple[str, float]:
    """A drawn key, like the site's <kbd>: (markup, width)."""
    w = ink.measure(label, 12, "medium", 0.06) + 14
    return (f'<rect x="{_f(x)}" y="{_f(y)}" width="{_f(w)}" height="{_f(h)}" rx="3" class="au" fill-opacity=".08"/>'
            f'<rect x="{_f(x + .5)}" y="{_f(y + .5)}" width="{_f(w - 1)}" height="{_f(h - 1)}" rx="3" class="au-s" '
            'stroke-opacity=".5" stroke-width="1"/>'
            + ink.text(x + 7, y + h / 2 + 4.2, label, 12, "medium", "au", tracking=0.06), w)


def foot(kind: str, geo: dict) -> list[tuple[float, float, str]]:
    W, y0 = geo["W"], geo["rows_bottom"]
    desk = kind == "desk"
    x = 36 if desk else 20
    out = [ink.brush_rule(28 if desk else 16, y0 - 2, W - (56 if desk else 32), 4, "au", extra=' opacity=".3"')]
    ky = y0 + (16 if desk else 12)
    cap, w = keycap(x, ky, "Click" if desk else "Tap")
    out.append(cap)
    out.append(ink.text(x + w + 8, ky + 15.5, "a place to jump to it", 14, "body", "mu"))
    if desk:
        tail = "for this map"
        tail_w = ink.measure(tail, 14, "body")
        cap_m, mw = keycap(0, 0, "M")
        mx = W - 36 - tail_w - 8 - mw
        out.append(ink.text(W - 36, ky + 15.5, tail, 14, "body", "mu", anchor="end"))
        out.append(keycap(mx, ky, "M")[0])
        out.append(ink.text(mx - 8, ky + 15.5, "On art3m1s.me, press", 14, "body", "mu", anchor="end"))
    return [(y0 - 4, geo["H"], "".join(out))]


# --- tiles -------------------------------------------------------------------------------------


def alt(name: str) -> str:
    """The words a screen reader gets for each tile: the same facts as the picture."""
    if name == "head":
        return (f"{ink.NAME} {NAME_LINE}. The gold key says Enter art3m1s.me, my site. Behind the name are the "
                f"gate of {ink.SECT_ZH} (the {ink.SECT_EN}) and the moon, from the site.")
    if name == "foot":
        return "Click a place on the map to jump to it. On art3m1s.me, press M for this map."
    sid, n, zh, en, section, fact, _href, _rank = next(s for s in STOPS if s[0] == name)
    start = f"The map of {ink.SECT_ZH} from my site, top to bottom. " if n == 11 else ""
    if name == RING_STOP:
        return f"{start}Stop {n:02d}, {zh} ({en}): you are here. A red ink ring circles the gate."
    return f"{start}Stop {n:02d}, {zh} ({en}): {section}." + (f" {fact}." if fact else "")


def tile_svg(kind: str, mode: str, name: str, geo: dict, strips: dict, moving: bool = False) -> str:
    y0, y1 = tile_band(geo, name)
    W = geo["W"]
    body = [f'<rect x="0" y="{y0 - 1}" width="{W}" height="{y1 - y0 + 2}" class="bg"/>']
    if mode == "light":
        body.append(f'<rect x="0" y="{y0 - 1}" width="{W}" height="{y1 - y0 + 2}" filter="url(#grain)" '
                    'opacity=".07"/>')
    for piece in pieces(kind, mode, geo, strips, moving):
        top, bottom, markup = piece[:3]
        owner = piece[3] if len(piece) > 3 else None
        if owner == name or (owner is None and bottom > y0 and top < y1):
            body.append(markup)
    defs = defs_common(mode)
    extra_css = ""
    motion = ""
    if moving and name == RING_STOP:
        cx, cy = geo["at"][RING_STOP]
        defs += ring_mask(cx, cy, geo["ring_r"])
        extra_css, motion = RING_CSS, "once"
    content = f'<g transform="translate(0 {-y0})">{"".join(body)}</g>'
    return ink.doc(W, y1 - y0, content, alt(name), mode, defs=defs, extra_css=extra_css, motion=motion)


def load_strips() -> dict:
    meta = json.loads((DATA / "strips.json").read_text(encoding="utf-8"))
    out = {"rows": meta["rows"]}
    for path in sorted(DATA.glob("*.jpg")):
        out[path.stem] = base64.b64encode(path.read_bytes()).decode("ascii")
    return out


def files_for(name: str) -> list[tuple[str, str, str, bool]]:
    """(file, kind, mode, moving) for one tile."""
    out = [(f"{name}.svg", "desk", "dark", name == RING_STOP),
           (f"{name}-light.svg", "desk", "light", name == RING_STOP),
           (f"{name}-phone.svg", "phone", "dark", name == RING_STOP)]
    if name == RING_STOP:
        out += [(f"{name}-still.svg", "desk", "dark", False),
                (f"{name}-light-still.svg", "desk", "light", False),
                (f"{name}-phone-still.svg", "phone", "dark", False)]
    return out


def render_all() -> dict[str, str]:
    """Every map file, in memory (a missing glyph raises before anything is written)."""
    strips = load_strips()
    geos = {kind: layout(kind) for kind in KINDS}
    files: dict[str, str] = {}
    for name in TILES:
        for file, kind, mode, moving in files_for(name):
            files[str(OUT / file)] = tile_svg(kind, mode, name, geos[kind], strips, moving)
    return files


# --- the README block ---------------------------------------------------------------------------


def _src(media: str, file: str) -> str:
    return f'<source media="{media}" srcset="{OUT.as_posix()}/{file}">'


def picture(name: str) -> str:
    phone, light, dark = f"{name}-phone.svg", f"{name}-light.svg", f"{name}.svg"
    sources = []
    if name == RING_STOP:
        # the ring draws itself once; anyone who asked for less motion gets the still twin.
        # Width and colour scheme never share one media query (GitHub rewrites the colour part).
        sources += [_src("(max-width: 600px) and (prefers-reduced-motion: reduce)", f"{name}-phone-still.svg"),
                    _src("(max-width: 600px)", phone),
                    _src("(prefers-reduced-motion: reduce) and (prefers-color-scheme: light)",
                         f"{name}-light-still.svg"),
                    _src("(prefers-color-scheme: light)", light),
                    _src("(prefers-reduced-motion: reduce)", f"{name}-still.svg")]
    else:
        sources += [_src("(max-width: 600px)", phone), _src("(prefers-color-scheme: light)", light)]
    img = (f'<img src="{OUT.as_posix()}/{dark}" width="100%" align="top" '
           f'alt="{ink.attr(alt(name))}">')
    return f"<picture>{''.join(sources)}{img}</picture>"


def href(name: str) -> str | None:
    if name == "head":
        return ink.SITE
    if name == "foot":
        return None
    return next(s[6] for s in STOPS if s[0] == name)


def readme_block() -> str:
    """The MAP block: 13 pictures stacked in one paragraph, each in its own link
    (the foot is not a link: a bare picture, so GitHub does not link it to itself)."""
    lines = []
    for name in TILES:
        link = href(name)
        pic = picture(name)
        lines.append(f'<a href="{ink.attr(link)}">{pic}</a>' if link else pic)
    return "<p>" + "<br>\n".join(lines) + "</p>"
