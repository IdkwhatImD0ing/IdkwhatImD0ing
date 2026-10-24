"""The art of 炼器峰, the Artifact Forge Peak: one panel per forged artifact.

Pure drawing: no README, no network. scripts/render_hacklog.py reads the
hackathon log and ships.json, then calls artifact_svg() for every newest
artifact (dark, light, phone) and writes the files to assets/forge/.

Each panel: a title row (index and name, the award in words, a red seal:
胜 won, 成 shipped), the name engraved on a dark nameplate, the payload,
the event and the date, and where the artifact is kept. The newest
artifact's frame still glows from the furnace; the oldest nameplate has one
rune that flickers (dark only). A missing payload gets an in-fiction excuse,
never an invented one.
"""

from __future__ import annotations

import hashlib
import unicodedata

import ink

PANE_W = 414
SIGNATURE = 'aria-label="forged artifact '   # in the first 600 chars of every pane SVG
GUTTER = 4          # half on each side of a desktop pane; the same under it
PAD = 16
DESK = {"size": 13, "lh": 19, "title": 12.5, "plate_h": 50, "name": 32}
PHONE = {"size": 12.5, "lh": 18, "title": 12, "plate_h": 46, "name": 28}

GLOW_CSS = (".live{animation:fglive 4.2s ease-in-out infinite}"
            "@keyframes fglive{0%,100%{stroke-opacity:1}50%{stroke-opacity:.45}}")
FLICKER_CSS = (".flk{animation:fgflk 6.7s steps(1) 2.3s infinite}"
               "@keyframes fgflk{0%,86%{opacity:1}87%{opacity:.12}88%{opacity:1}90%{opacity:.3}91%,100%{opacity:1}}")


def _get(ship: dict, key: str) -> str:
    return str(ship.get(key) or "").strip()


def _count(value: object) -> int | None:
    try:
        n = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return n if n >= 0 else None


def ascii_fold(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")


def drawable(s: str, face: str = "body") -> str:
    """Fold accents and drop anything the glyph tables cannot draw, so one
    odd character in a hand-typed log can never sink the render."""
    out = []
    for ch in s:
        try:
            ink.check(ch, face)
            out.append(ch)
        except ink.MissingGlyph:
            folded = ascii_fold(ch)
            out.append(folded if folded and all(_ok(c, face) for c in folded) else "")
    return "".join(out)


def _ok(ch: str, face: str) -> bool:
    try:
        ink.check(ch, face)
        return True
    except ink.MissingGlyph:
        return False


def verdict(ship: dict) -> tuple[str, str]:
    """(seal character, verdict word)."""
    tag = _get(ship, "tag").upper()
    if tag == "WIN":
        return "胜", "won"
    if tag == "SHIP":
        return "成", "shipped"
    return "成", tag.lower() or "logged"


def stats_text(ship: dict) -> str:
    stars, forks = _count(ship.get("stars")), _count(ship.get("forks"))
    if stars is None or forks is None:
        return ""
    return f"{ink.plural(stars, 'star')}  {ink.plural(forks, 'fork')}"


def _type(phone: bool) -> dict:
    return PHONE if phone else DESK


def _text_width(phone: bool) -> float:
    return (ink.WP if phone else PANE_W - GUTTER) - 2 * PAD


def payload_lines_needed(ships: list[dict], phone: bool) -> int:
    t = _type(phone)
    width = _text_width(phone)
    return max((min(len(ink.wrap(drawable(_get(s, "payload")), width, t["size"])), 2)
                for s in ships if _get(s, "payload")), default=1)


def _rune(x: float, y: float, cls: str, extra: str = "") -> str:
    return f'<path d="M{ink.fmt(x)} {ink.fmt(y - 3.2)}l3.2 3.2l-3.2 3.2l-3.2-3.2z" class="{cls}"{extra}/>'


def label(ship: dict, index: int, active: bool) -> str:
    _, word = verdict(ship)
    name = _get(ship, "name") or "unnamed"
    bits = [f"forged artifact {index}{' (newest)' if active else ''}: {name}."]
    bits.append(f"{word}: {_get(ship, 'award') or 'logged'} at {_get(ship, 'event')}, {_get(ship, 'date')}.")
    payload = _get(ship, "payload")
    bits.append(payload.rstrip(".") + "." if payload else "no inscription on file. it was forged anyway.")
    facts = [x for x in (_get(ship, "lang"), stats_text(ship).replace("  ", ", ")) if x]
    if facts:
        bits.append(", ".join(facts) + ".")
    repo = _get(ship, "repo")
    bits.append(f"kept at github.com/{repo}." if repo else "kept nowhere public.")
    return " ".join(bits)


def artifact_svg(ship: dict, index: int, *, active: bool, mode: str, phone: bool = False,
                 payload_lines: int = 1, flaky: bool = False) -> str:
    t = _type(phone)
    size, lh = t["size"], t["lh"]
    if phone:
        width, x0, pw = ink.WP, 0.0, float(ink.WP)
    else:
        width, x0, pw = PANE_W, GUTTER / 2, PANE_W - GUTTER
    tx, rx = x0 + PAD, x0 + pw - PAD
    tw = rx - tx
    dark = mode == "dark"
    flaky = flaky and dark
    seal_ch, word = verdict(ship)
    name = drawable(_get(ship, "name")) or "unnamed"
    award = drawable(_get(ship, "award").lower()) or "logged"
    payload = drawable(_get(ship, "payload"))
    event = drawable(_get(ship, "event"))
    repo = drawable(_get(ship, "repo"))
    lang = drawable(_get(ship, "lang"))
    stats = stats_text(ship)

    rows = [("event", event), ("forged", f"{_get(ship, 'date')}" + (f"  ·  {lang}" if lang else ""))]
    if phone and stats:
        rows.append(("kept", stats))

    y_title = 26
    y_plate = 38
    plate_h = t["plate_h"]
    y_pay = y_plate + plate_h + 24
    y_rows = y_pay + (payload_lines - 1) * lh + lh + 6
    y_foot = y_rows + (len(rows) - 1) * lh + lh + 8
    panel_h = y_foot + 16
    height = panel_h + GUTTER

    css = ""
    body = [ink.plate(x0, 0, pw, panel_h, corner=0, rx=4)]
    frame_cls = "au-s" if active else "ln"
    live = ' class="live"' if active and dark else ""
    body.append(f'<g{live}><rect x="{ink.fmt(x0 + 0.5)}" y="0.5" width="{ink.fmt(pw - 1)}" '
                f'height="{ink.fmt(panel_h - 1)}" rx="4" class="{frame_cls}" stroke-width="1"/></g>')
    body.append(ink.corners(x0 + 4, 4, pw - 8, panel_h - 8, 14, "au-s" if active else "ln", False))
    if active and dark:
        css += GLOW_CSS

    # title row: index and name left; the award in words and the seal right
    seal_size = 20
    seal_x = rx - seal_size
    right = f"{word}: {award}"
    left_w = ink.measure(f"{index}  ", t["title"], "mono")
    name_small = ink.fit(name, tw * 0.42, t["title"], "medium")
    room = seal_x - 8 - (tx + left_w + ink.measure(name_small, t["title"], "medium") + 14)
    right = ink.fit(right, room, t["title"], "body")
    body.append(ink.text(tx, y_title, str(index), t["title"], "mono", "mu"))
    body.append(ink.text(tx + left_w, y_title, name_small, t["title"], "medium", "au" if active else "tx"))
    body.append(ink.text(seal_x - 8, y_title, right, t["title"], "body", "mu", anchor="end"))
    body.append(ink.seal(seal_x, y_title - 15, seal_size, seal_ch))

    # the nameplate: the name engraved in gold on a dark plate
    body.append(ink.rect(tx, y_plate, tw, plate_h, "tk", 3))
    body.append(f'<rect x="{ink.fmt(tx + 0.5)}" y="{ink.fmt(y_plate + 0.5)}" width="{ink.fmt(tw - 1)}" '
                f'height="{plate_h - 1}" rx="3" class="ln" stroke-width="1"/>')
    rune_room = 34
    name_size = t["name"]
    while name_size > 20 and ink.measure(name, name_size, "display") > tw - 28 - rune_room:
        name_size -= 1
    shown = ink.fit(name, tw - 28 - rune_room, name_size, "display")
    base = y_plate + plate_h / 2 + name_size * 0.33
    if dark:
        body.append(ink.text(tx + 14, base + 1.2, shown, name_size, "display", "bg"))
    body.append(ink.text(tx + 14, base, shown, name_size, "display", "au"))
    pick = int(hashlib.sha256(name.encode("utf-8")).hexdigest(), 16) % 3
    for k in range(3):
        rx_k = rx - 12 - k * 10
        flick = flaky and k == pick
        rune = _rune(rx_k, y_plate + plate_h / 2, "au" if k == 0 else "em", ' opacity=".8"')
        body.append(f'<g class="flk">{rune}</g>' if flick else rune)
    if flaky:
        css += FLICKER_CSS

    # payload, or the excuse
    if payload:
        for k, line in enumerate(ink.balanced(payload, tw, size, "body", payload_lines)):
            body.append(ink.text(tx, y_pay + k * lh, line, size, "body", "tx"))
    else:
        body.append(ink.text(tx, y_pay, ink.fit("no inscription on file. it was forged anyway.", tw, size),
                             size, "body", "mu"))

    label_w = 58
    for k, (key, value) in enumerate(rows):
        y = y_rows + k * lh
        body.append(ink.text(tx, y, key, 11.5, "mono", "mu"))
        body.append(ink.text(tx + label_w, y, ink.fit(value, tw - label_w, size), size, "body",
                             "mu" if key == "kept" else "tx"))

    # where it is kept, and its stars
    body.append(ink.hline(tx, rx, y_foot - 15, "ln"))
    right_stats = "" if phone else stats
    if repo:
        kept_parts = [("kept at ", "mu"), ("github.com/", "mu"), (repo, "tx")]
    else:
        kept_parts = [("kept nowhere public. the forge remembers.", "mu")]
    room = tw - (ink.measure(right_stats, 12, "mono") + 14 if right_stats else 0)
    if right_stats and ink.measure("".join(p[0] for p in kept_parts), 12) > room:
        right_stats = ink.plural(_count(ship.get("stars")) or 0, "star")
        room = tw - ink.measure(right_stats, 12, "mono") - 14
    if ink.measure("".join(p[0] for p in kept_parts), 12) > room:
        kept_parts = [("kept at ", "mu"), (ink.fit(repo, room - ink.measure("kept at ", 12), 12), "tx")]
    body.append(ink.runs(tx, y_foot, kept_parts, 12)[0])
    if right_stats:
        body.append(ink.text(rx, y_foot, right_stats, 12, "mono", "mu", anchor="end"))

    return ink.doc(width, height, "".join(body), label(ship, index, active), mode, extra_css=css)
