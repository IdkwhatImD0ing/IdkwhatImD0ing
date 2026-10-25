"""The Shipped journal: one spread for the star build and a page for each of the others.

Pure drawing (stdlib): scripts/render_hacklog.py reads the hackathon log,
ships.json and the checked commit quotes, then calls spread_svg() and
leaf_svg() here and writes the files to assets/journal/. Nothing here touches
the network or README.md.

It is built like the Journal (影神图) in Black Myth: Wukong. The star build gets
a spread: on the left a print of its object from my site's forge (the prints
are made by generate_prints.py from captures of art3m1s.me, mounted like the
map's scroll), on the right the prize line, the name, what it is, a few facts,
one sentence from our own write-up and one of my real commit messages from the
build, with its time and hash. The other builds get a smaller page each: the
print, the prize, the name, the one-liner and the commit. Gold means won.

Words come from data only: the log, ships.json and the commit itself (checked
against the GitHub API by render_hacklog.py before anything is drawn). Nothing
here writes a sentence about a build.

Files: <slug>-spread.svg (dark), -spread-light.svg, -spread-phone.svg (phones
get the dark file in both themes, so it carries its own ground); <slug>.svg
and <slug>-light.svg for a page (276 px wide, so a phone shows it at full size;
phones get the dark file in both themes, like every other drawing).
"""

from __future__ import annotations

import base64
import json
import re
import unicodedata
from datetime import date, datetime
from pathlib import Path

import ink

DATA = Path("scripts/data/journal")
SIGNATURE = 'aria-label="journal, '        # in the first 600 chars of every journal SVG
PC = ink.PRINT_COLORS
MC = ink.MAP_COLORS

# Three pages sit side by side in 828 px. The column is 846 px from a 1280 px
# window up, but Chrome on Windows keeps 15-17 px for its scrollbar, so a
# 1280 px screen (a 1920 px laptop at 150%) gets a 829 px column; three 282 px
# pages wrapped to two plus one there. A phone shows one page at full size.
LEAF_W = 276
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
MONTHS_LONG = ("January", "February", "March", "April", "May", "June", "July", "August", "September",
               "October", "November", "December")
NO_PRINT = "No print yet"


# --- data -------------------------------------------------------------------------------------


def spec() -> dict:
    return json.loads((DATA / "prints.json").read_text(encoding="utf-8"))


def jpeg(name: str) -> str | None:
    path = DATA / f"{name}.jpg"
    if not path.exists():
        return None
    return "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def get(d: dict, key: str) -> str:
    return str(d.get(key) or "").strip()


def ascii_fold(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")


def drawable(s: str, face: str = "body") -> str:
    """Drop or fold anything the glyph tables cannot draw, so one odd character
    in a hand-typed log can never sink the render."""
    out = []
    for ch in s:
        try:
            ink.check(ch, face)
            out.append(ch)
        except ink.MissingGlyph:
            folded = ascii_fold(ch)
            try:
                ink.check(folded, face)
                out.append(folded)
            except ink.MissingGlyph:
                pass
    return "".join(out)


def won(ship: dict) -> bool:
    return get(ship, "tag").upper() == "WIN"


def award(ship: dict) -> str:
    return get(ship, "award") or ("won" if won(ship) else "shipped")


def year(ship: dict) -> str:
    return get(ship, "date")[:4]


def event_year(ship: dict) -> str:
    """'HackUTD 2024' stays; 'GDSC Solution Challenge' gets its year."""
    event = get(ship, "event")
    return event if re.search(r"(19|20)\d\d$", event) else f"{event} {year(ship)}".strip()


def short_event(ship: dict) -> str:
    return re.sub(r"\s+(19|20)\d\d$", "", get(ship, "event")).strip()


def month(ship: dict, long: bool = False) -> str:
    try:
        d = date.fromisoformat(get(ship, "date"))
    except ValueError:
        return get(ship, "date")
    return f"{(MONTHS_LONG if long else MONTHS)[d.month - 1]} {d.year}"


def one_liner(ship: dict) -> str:
    text = get(ship, "payload").rstrip(".")
    return text[:1].upper() + text[1:] if text else ""


def when(quote: dict) -> datetime | None:
    try:
        return datetime.fromisoformat(get(quote, "when"))
    except ValueError:
        return None


def clock(t: datetime) -> str:
    h = t.hour % 12 or 12
    return f"{h}:{t.minute:02d} {'AM' if t.hour < 12 else 'PM'}"


def attribution(quote: dict, long: bool) -> str:
    """'MY COMMIT AT 5:23 AM, JUN 23 2024  ·  75485B7' (spread) or 'MY COMMIT  ·  NOV 17, 2024'."""
    t = when(quote)
    sha = get(quote, "sha")[:7].upper()
    if not t:
        return f"MY COMMIT  ·  {sha}" if sha else "MY COMMIT"
    day = f"{MONTHS[t.month - 1].upper()} {t.day} {t.year}"
    if long:
        return f"MY COMMIT AT {clock(t)}, {day}" + (f"  ·  {sha}" if sha else "")
    return f"MY COMMIT  ·  {MONTHS[t.month - 1].upper()} {t.day}, {t.year}"


def spoken_when(quote: dict, long: bool) -> str:
    t = when(quote)
    if not t:
        return "My commit"
    day = f"{MONTHS_LONG[t.month - 1]} {t.day}, {t.year}"
    sha = get(quote, "sha")[:7]
    if long:   # the spread prints the short hash too
        return f"My commit {sha} at {clock(t)} on {day}" if sha else f"My commit at {clock(t)} on {day}"
    return f"My commit on {day}"


# --- alt text (the same words the picture shows) ----------------------------------------------


def artifact_names(slug: str) -> tuple[str, str] | None:
    item = spec()["prints"].get(slug)
    return tuple(item["artifact"]) if item and item.get("artifact") else None


def spread_alt(ship: dict) -> str:
    sp = ship.get("spread") or {}
    bits = [f"{get(ship, 'name')}: {award(ship)} at the {short_event(ship)}, {month(ship, long=True)}."]
    if one_liner(ship):
        bits.append(one_liner(ship) + ".")
    for label, value in sp.get("rows", []):
        bits.append(f"{label}: {value}.")
    if get(sp, "words"):
        bits.append(get(sp, "words"))
    quote = ship.get("quote") or {}
    if get(quote, "text"):
        bits.append(f"{spoken_when(quote, True)}: \"{get(quote, 'text')}\".")
    names = artifact_names(get(ship, "slug"))
    if names:
        bits.append(f"The picture is a print of the {names[0]} ({names[1]}) from my site's forge"
                    + (", with a photo of the dispatcher screen." if get(sp, "photo") else "."))
    return " ".join(bits)


def leaf_alt(ship: dict) -> str:
    bits = [f"{get(ship, 'name')}: {award(ship)} at {event_year(ship)}."]
    if one_liner(ship):
        bits.append(one_liner(ship) + ".")
    quote = ship.get("quote") or {}
    if get(quote, "text"):
        bits.append(f"{spoken_when(quote, False)}: \"{get(quote, 'text')}\".")
    names = artifact_names(get(ship, "slug"))
    if names:
        bits.append(f"The picture is a print of the {names[0]} ({names[1]}) from my site's forge.")
    return " ".join(bits)


# --- pieces -----------------------------------------------------------------------------------


def caps(x: float, y: float, s: str, cls: str = "mu", size: float = 12, tracking: float = 0.14,
         anchor: str = "start", extra: str = "") -> str:
    return ink.text(x, y, s, size, "medium", cls, anchor=anchor, tracking=tracking, extra=extra)


def caps_runs(x: float, y: float, parts: list[tuple[str, str]], size: float = 12, tracking: float = 0.14,
              anchor: str = "start") -> tuple[str, float]:
    """Several tracked caps runs on one baseline: (svg, width)."""
    widths = [ink.measure(p, size, "medium", tracking) + (size * tracking if i < len(parts) - 1 else 0)
              for i, (p, _c) in enumerate(parts)]
    total = sum(widths)
    pen = x - total if anchor == "end" else x
    out = []
    for (s, cls), w in zip(parts, widths):
        out.append(caps(pen, y, s, cls, size, tracking))
        pen += w
    return "".join(out), total


def mount(px: float, py: float, pw: float, ph: float) -> str:
    """The map scroll's mount (sect.css .sect-map-sheet): an ink edge, a brocade
    band and a gold line round the paper."""
    f = ink.fmt
    return (f'<rect x="{f(px - 8)}" y="{f(py - 8)}" width="{f(pw + 16)}" height="{f(ph + 16)}" rx="2" '
            f'fill="{MC["mount_edge"]}" fill-opacity=".7"/>'
            f'<rect x="{f(px - 7)}" y="{f(py - 7)}" width="{f(pw + 14)}" height="{f(ph + 14)}" rx="1.5" '
            f'fill="{MC["mount"]}"/>'
            f'<rect x="{f(px - .5)}" y="{f(py - .5)}" width="{f(pw + 1)}" height="{f(ph + 1)}" fill="none" '
            f'stroke="{MC["gold"]}" stroke-opacity=".55" stroke-width="1"/>')


def print_plate(slug: str, kind: str, px: float, py: float, pw: float, ph: float, brush_size: float,
                photo: dict | None = None) -> str:
    """The print on its paper: the JPEG, a double printed border, the object's
    name upright in the brush hand with its English gloss, and (on the star) a
    photo tipped in at the lower right."""
    f = ink.fmt
    out = [mount(px, py, pw, ph)]
    src = jpeg(f"print-{slug}-{kind}")
    if src:
        out.append(f'<image href="{src}" x="{f(px)}" y="{f(py)}" width="{f(pw)}" height="{f(ph)}" '
                   'preserveAspectRatio="xMidYMid slice"/>')
    else:
        out.append(f'<rect x="{f(px)}" y="{f(py)}" width="{f(pw)}" height="{f(ph)}" fill="{PC["card"]}"/>')
        out.append(ink.text(px + pw / 2, py + ph / 2 + 5, NO_PRINT, 14, "body", "", anchor="middle",
                            extra=f' fill="{PC["grey"]}"'))
    # the printed border: a strong line and a hairline inside it, as on a woodblock plate
    inset = 9 if kind == "spread" else 7
    out.append(f'<rect x="{f(px + inset)}" y="{f(py + inset)}" width="{f(pw - 2 * inset)}" '
               f'height="{f(ph - 2 * inset)}" fill="none" stroke="{PC["ink"]}" stroke-opacity=".78" '
               'stroke-width="1.3"/>'
               f'<rect x="{f(px + inset + 3.5)}" y="{f(py + inset + 3.5)}" width="{f(pw - 2 * inset - 7)}" '
               f'height="{f(ph - 2 * inset - 7)}" fill="none" stroke="{PC["ink"]}" stroke-opacity=".55" '
               'stroke-width=".6"/>')
    names = artifact_names(slug)
    if names:
        zh, en = names
        # the name reads top to bottom in the right margin, like a title slip on a plate
        cx = px + pw - inset - 8 - brush_size * 0.55
        top = py + inset + 10
        for i, ch in enumerate(zh):
            out.append(ink.glyph_centred(ch, cx, top + brush_size * (0.55 + 1.02 * i), brush_size, "brush", ""))
        out[-len(zh):] = [g.replace('<g ', f'<g fill="{PC["ink"]}" ', 1) for g in out[-len(zh):]]
        gloss = en.upper()
        if kind == "spread":
            # upright beside the name, reading down
            gx = cx - brush_size * 0.55 - 12
            out.append(f'<g transform="rotate(90 {f(gx)} {f(top + 2)})">'
                       + caps(gx, top + 2, gloss, "", 12, 0.24, extra=f' fill="{PC["grey"]}"') + "</g>")
        else:
            out.append(caps(px + pw - inset - 9, py + ph - inset - 10, gloss, "", 12, 0.16, anchor="end",
                            extra=f' fill="{PC["grey"]}"'))
    if photo:
        out.append(tipped_photo(photo, px + pw, py + ph))
    return "".join(out)


def tipped_photo(photo: dict, right: float, bottom: float) -> str:
    """A small photo on a white card, tipped in over the print's lower right corner."""
    f = ink.fmt
    src = jpeg(f"photo-{photo['slug']}")
    if not src:
        return ""
    w, h = photo["size"]
    pad, foot = 5, 20
    cw, ch = w + 2 * pad, h + pad + foot
    x, y = right - cw + 14, bottom - ch + 10
    caption = photo.get("caption", "")
    cap = ink.text(x + cw / 2, y + h + pad + 14, caption, 12, "body", "", anchor="middle",
                   extra=f' fill="{PC["grey"]}"') if caption else ""
    return (f'<g transform="rotate(-3 {f(x + cw / 2)} {f(y + ch / 2)})">'
            f'<rect x="{f(x + 2)}" y="{f(y + 4)}" width="{f(cw)}" height="{f(ch)}" fill="{PC["shadow"]}" '
            'fill-opacity=".28" filter="url(#soft)"/>'
            f'<rect x="{f(x)}" y="{f(y)}" width="{f(cw)}" height="{f(ch)}" fill="{PC["card"]}"/>'
            f'<image href="{src}" x="{f(x + pad)}" y="{f(y + pad)}" width="{f(w)}" height="{f(h)}" '
            'preserveAspectRatio="xMidYMid slice"/>'
            f'<rect x="{f(x + pad)}" y="{f(y + pad)}" width="{f(w)}" height="{f(h)}" fill="none" '
            f'stroke="{PC["ink"]}" stroke-opacity=".25" stroke-width=".6"/>{cap}</g>')


SOFT = '<filter id="soft" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="3"/></filter>'


def sheet(w: float, h: float, mode: str, corners: bool) -> tuple[str, str]:
    """The journal's page: the ground, a gold hairline (as on the map panel),
    and on the star only, the site's cloud corners. Light mode adds the paper
    grain. Returns (defs, markup)."""
    defs = ""
    out = [f'<rect x="0" y="0" width="{ink.fmt(w)}" height="{ink.fmt(h)}" rx="3" class="bg"/>']
    if mode == "light":
        grain_defs, overlay = ink.paper_grain(w, h, "grain", 0.07)
        defs += grain_defs
        out.append(overlay)
    out.append(f'<rect x=".5" y=".5" width="{ink.fmt(w - 1)}" height="{ink.fmt(h - 1)}" rx="3" class="au-s" '
               f'stroke-opacity="{".38" if corners else ".24"}" stroke-width="1"/>')
    if corners:
        size = 30 if w > 400 else 24
        out.append(ink.corner(4, 4, size, large=True, width=1.4))
        out.append(ink.corner(w - 4, h - 4, size, flip_x=True, flip_y=True, large=True, width=1.4))
    return defs, "".join(out)


def quote_text(s: str) -> str:
    return f"“{s}”"


def whole_quote(ship: dict, lines: list[str]) -> None:
    """A quote is drawn exactly or not at all: a character the glyph tables
    cannot draw, or a quote too long for its place (fit() and wrap() would cut
    it with '...'), raises, so render_hacklog.py keeps the old files."""
    text = quote_text(get(ship.get("quote") or {}, "text"))
    if drawable(text, "display") != text:
        raise ValueError(f"{get(ship, 'name')}: the quote has a character the glyph tables lack "
                         "(re-run generate_glyphs.py)")
    if "".join(lines).replace(" ", "") != text.replace(" ", ""):
        raise ValueError(f"{get(ship, 'name')}: the quote is too long to draw whole here")


# --- the spread -------------------------------------------------------------------------------

NAME_SIZE = 64          # the star's name: the same size as "Bill Zhang", one per screen
SPREAD = {
    "desk": dict(W=ink.W, pad=24, gap=40, name=NAME_SIZE, line=16, quote=24, words=14, words_lh=20,
                 brush=30, row_h=28),
    "phone": dict(W=ink.WP, pad=23, gap=0, name=46, line=16, quote=20, words=14, words_lh=21,
                  brush=24, row_h=28),
}


def spread_svg(ship: dict, mode: str, phone: bool = False) -> str:
    k = SPREAD["phone" if phone else "desk"]
    W, pad = k["W"], k["pad"]
    frame = spec()["frames"]["spread"]
    pw, ph = frame
    slug = get(ship, "slug")
    sp = ship.get("spread") or {}
    photo = None
    photo_key = get(sp, "photo")
    if photo_key and photo_key in spec().get("photos", {}):
        photo = dict(spec()["photos"][photo_key], slug=photo_key)

    if phone:
        px, py = (W - pw) / 2, pad + 8
        x0, x1 = 20, W - 20
        y = py + ph + 8 + 44
    else:
        px, py = pad + 8, pad + 8
        x0, x1 = px + pw + 8 + k["gap"], W - 36
        y = 58
    tw = x1 - x0
    body: list[str] = []

    # the prize line: gold when it won
    tier = [(drawable(award(ship).upper(), "medium"), "au" if won(ship) else "tx"),
            (f"  ·  {drawable(short_event(ship).upper(), 'medium')}", "mu"),
            (f"  ·  {month(ship).upper()}", "mu")]
    track = 0.12 if not phone else 0.1
    size12 = 12 if not phone else 11
    if ink.measure("".join(p for p, _ in tier), size12, "medium", track) > tw:
        line1, _ = caps_runs(x0, y, tier[:1], size12, track)
        line2, _ = caps_runs(x0, y + 18, [(tier[1][0].lstrip(" ·"), "mu"), tier[2]], size12, track)
        body += [line1, line2]
        y += 18
    else:
        body.append(caps_runs(x0, y, tier, size12, track)[0])

    name = drawable(get(ship, "name"), "display") or "unnamed"
    y += round(k["name"] * 0.72) + 18
    body.append(ink.text(x0, y, ink.fit(name, tw, k["name"], "display"), k["name"], "display", "tx"))
    liner = drawable(one_liner(ship))
    if liner:
        for i, line in enumerate(ink.balanced(liner, tw, k["line"], "body", 2)):
            y += 32 if i == 0 else 22
            body.append(ink.text(x0, y, line, k["line"], "body", "tx", extra=' fill-opacity=".86"'))
    y += 16
    body.append(ink.brush(x0 - 2, y - 3, 64, 6, "au"))
    y += 14

    rows = [(drawable(str(a).upper(), "medium"), drawable(str(b))) for a, b in sp.get("rows", [])]
    if rows:
        for label, value in rows:
            body.append(ink.hline(x0, x1, y + .5, "ln", 1))
            body.append(caps(x0, y + 18.5, label, "mu", size12, 0.14))
            room = tw - ink.measure(label, size12, "medium", 0.14) - 16
            body.append(ink.text(x1, y + 19, ink.fit(value, room, 14), 14, "body", "tx", anchor="end"))
            y += k["row_h"]
        body.append(ink.hline(x0, x1, y + .5, "ln", 1))
    words = drawable(get(sp, "words"))
    if words:
        y += 10
        for line in ink.wrap(words, tw, k["words"], "body", 4):
            y += k["words_lh"]
            body.append(ink.text(x0, y, line, k["words"], "body", "tx", extra=' fill-opacity=".74"'))
    quote = ship.get("quote") or {}
    if get(quote, "text"):
        qtext = drawable(quote_text(get(quote, "text")), "display")
        y += 34
        qlines = ink.wrap(qtext, tw, k["quote"], "display", 2)
        whole_quote(ship, qlines)
        for i, line in enumerate(qlines):
            body.append(ink.text(x1, y, line, k["quote"], "display", "tx", anchor="end"))
            if i < len(qlines) - 1:
                y += k["quote"] + 4
        y += 20
        attr = attribution(quote, long=True)
        if ink.measure(attr, size12, "medium", 0.14) > tw and "  ·  " in attr:
            # too wide for the phone: the time on one line, the hash under it
            first, sha = attr.rsplit("  ·  ", 1)
            body.append(caps(x1, y, first, "mu", size12, 0.14, anchor="end"))
            y += 18
            attr = sha
        body.append(caps(x1, y, attr, "mu", size12, 0.14, anchor="end"))
    bottom = y + 24
    H = max(bottom, py + ph + 8 + pad) if not phone else bottom
    H = int(-(-H // 2) * 2)      # even, so a 2x raster has whole pixels
    if not phone:
        py = round((H - ph) / 2)  # the print sits centred on the page's height

    plate = print_plate(slug, "spread", px, py, pw, ph, k["brush"], photo)
    defs, page = sheet(W, H, mode, corners=True)
    content = page + plate + "".join(body)
    return ink.doc(W, H, content, "journal, " + spread_alt(ship), mode, defs=defs + SOFT)


# --- a page ---------------------------------------------------------------------------------------

LEAF = dict(gutter=3, pad=16, brush=24, name=24, line=14, line_h=20, quote=16)


def leaf_layout(ships: list[dict]) -> int:
    """How many one-liner lines the shared height needs (pages sit side by side)."""
    tw = LEAF_W - 2 * LEAF["gutter"] - 2 * LEAF["pad"]
    return max((min(len(ink.wrap(drawable(one_liner(s)), tw, LEAF["line"])), 2) for s in ships if one_liner(s)),
               default=1)


def snug(s: str, width: float, size: float = 12, tracking: float = 0.12) -> float:
    """The caps tracking that fits s in width: 0.12, tightened to 0.06 at most
    ('GDSC SOLUTION CHALLENGE 2023' is a hair too wide for a page at 0.12)."""
    while tracking > 0.06 and ink.measure(s, size, "medium", tracking) > width:
        tracking = round(tracking - 0.01, 2)
    return tracking


def leaf_svg(ship: dict, mode: str, liner_lines: int = 2) -> str:
    g, pad = LEAF["gutter"], LEAF["pad"]
    pw, ph = spec()["frames"]["leaf"]
    x0 = g + pad
    tw = LEAF_W - 2 * g - 2 * pad
    px = (LEAF_W - pw) / 2
    py = g + 16
    body: list[str] = []
    slug = get(ship, "slug")
    body.append(print_plate(slug, "leaf", px, py, pw, ph, LEAF["brush"]))

    y = py + ph + 8 + 26
    prize = drawable(award(ship).upper(), "medium")
    body.append(caps(x0, y, prize, "au" if won(ship) else "tx", 12, snug(prize, tw)))
    y += 18
    event = drawable(event_year(ship).upper(), "medium")
    body.append(caps(x0, y, event, "mu", 12, snug(event, tw)))
    y += 30
    name = drawable(get(ship, "name"), "display") or "unnamed"
    body.append(ink.text(x0, y, ink.fit(name, tw, LEAF["name"], "display"), LEAF["name"], "display", "tx"))
    liner = drawable(one_liner(ship))
    lines = ink.balanced(liner, tw, LEAF["line"], "body", 2) if liner else []
    for i, line in enumerate(lines):
        body.append(ink.text(x0, y + 24 + i * LEAF["line_h"], line, LEAF["line"], "body", "tx",
                             extra=' fill-opacity=".86"'))
    y += 24 + (liner_lines - 1) * LEAF["line_h"]
    quote = ship.get("quote") or {}
    if get(quote, "text"):
        qtext = ink.fit(drawable(quote_text(get(quote, "text")), "display"), tw, LEAF["quote"], "display")
        whole_quote(ship, [qtext])
        y += 30
        body.append(ink.text(x0, y, qtext, LEAF["quote"], "display", "tx"))
        y += 20
        body.append(caps(x0, y, attribution(quote, long=False), "mu", 12, 0.12))
    else:
        y += 50
    panel_h = y + 16
    H = panel_h + 2 * g + 4      # the gap under a page, so stacked pages on a phone do not touch
    defs, page = sheet(LEAF_W - 2 * g, panel_h, mode, corners=False)
    content = f'<g transform="translate({g} {g})">{page}</g>' + "".join(body)
    return ink.doc(LEAF_W, H, content, "journal, " + leaf_alt(ship), mode, defs=defs)

