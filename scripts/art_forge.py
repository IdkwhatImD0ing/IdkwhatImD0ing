"""The project cards: one quiet card per shipped build.

Pure drawing: no README, no network. scripts/render_hacklog.py reads the
hackathon log and ships.json, then calls artifact_svg() for each of the four
newest builds (dark, light, phone) and writes the files to assets/forge/.

Each card: the name in Instrument Serif, the one-liner, and one small line
with the award, the event and the month. The award words are gold when the
build won (gold means won, nowhere else) and plain text when it shipped. The
card links to its repo in the README, so it does not repeat the address. No
seals, cloud corners, runes, glow or star counts: detail lives in the hero and
the footer. A missing one-liner says so plainly; it is never invented.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date

import ink

PANE_W = 414
SIGNATURE = 'aria-label="project card '      # in the first 600 chars of every card SVG
OLD_SIGNATURE = 'aria-label="forged artifact '  # cards drawn before 2026-10-24, still pruned
GUTTER = 4          # half on each side of a desktop pane; the same under it
PAD = 16
NAME_SIZE = 24
TEXT_SIZE, LINE_H = 14, 20
SMALL_SIZE = 12
NO_PAYLOAD = "No description yet."
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
MONTHS_LONG = ("January", "February", "March", "April", "May", "June", "July", "August", "September",
               "October", "November", "December")


def _get(ship: dict, key: str) -> str:
    return str(ship.get(key) or "").strip()


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


def won(ship: dict) -> bool:
    return _get(ship, "tag").upper() == "WIN"


def short_event(event: str) -> str:
    """'HackUTD 2024' -> 'HackUTD': the date line already carries the year."""
    return re.sub(r"\s+(19|20)\d\d$", "", event).strip() or event


def month(ship: dict, long: bool = False) -> str:
    """'2024-11-16' -> 'Nov 2024' (or 'November 2024'); the raw text if it is not a date."""
    raw = _get(ship, "date")
    try:
        d = date.fromisoformat(raw)
    except ValueError:
        return raw
    return f"{(MONTHS_LONG if long else MONTHS)[d.month - 1]} {d.year}"


def one_liner(ship: dict) -> str:
    """The payload as a tagline: first letter up, no closing full stop."""
    text = _get(ship, "payload").rstrip(".")
    return text[:1].upper() + text[1:] if text else ""


def _type(phone: bool) -> tuple[float, float]:
    """(panel x, panel width)."""
    return (0.0, float(ink.WP)) if phone else (GUTTER / 2, PANE_W - GUTTER)


def _text_width(phone: bool) -> float:
    return _type(phone)[1] - 2 * PAD


def payload_lines_needed(ships: list[dict], phone: bool) -> int:
    width = _text_width(phone)
    return max((min(len(ink.wrap(drawable(one_liner(s)), width, TEXT_SIZE)), 2)
                for s in ships if _get(s, "payload")), default=1)


def label(ship: dict, index: int) -> str:
    name = _get(ship, "name") or "unnamed"
    award = _get(ship, "award") or ("won" if won(ship) else "shipped")
    bits = [f"project card {index + 1}: {name}.", f"{award} at {_get(ship, 'event')}, {month(ship, long=True)}."]
    payload = one_liner(ship)
    bits.append(payload + "." if payload else NO_PAYLOAD)
    return " ".join(bits)


def artifact_svg(ship: dict, index: int, *, mode: str, phone: bool = False, payload_lines: int = 1) -> str:
    x0, pw = _type(phone)
    width = ink.WP if phone else PANE_W
    tx = x0 + PAD
    tw = pw - 2 * PAD
    name = drawable(_get(ship, "name")) or "unnamed"
    payload = drawable(one_liner(ship))
    award = drawable(_get(ship, "award")) or ("won" if won(ship) else "shipped")
    event = drawable(short_event(_get(ship, "event")))

    y_name = 40
    y_pay = 66
    y_award = y_pay + (payload_lines - 1) * LINE_H + 18
    panel_h = y_award + 28
    height = panel_h + GUTTER  # the gutter under a card; phones stack them

    body = [ink.plate(x0, 0, pw, panel_h, corner=0, rx=4)]
    body.append(ink.text(tx, y_name, ink.fit(name, tw, NAME_SIZE, "display"), NAME_SIZE, "display", "tx"))

    if payload:
        for k, line in enumerate(ink.balanced(payload, tw, TEXT_SIZE, "body", payload_lines)):
            body.append(ink.text(tx, y_pay + k * LINE_H, line, TEXT_SIZE, "body", "tx"))
    else:
        body.append(ink.text(tx, y_pay, ink.fit(NO_PAYLOAD, tw, TEXT_SIZE), TEXT_SIZE, "body", "mu"))

    tail = "  ·  ".join(x for x in (event, month(ship)) if x)
    parts = [(award, "au" if won(ship) else "tx")]
    if tail:
        parts.append(("  ·  " + tail, "mu"))
    if ink.measure("".join(p[0] for p in parts), SMALL_SIZE) > tw:
        parts = [(ink.fit(award, tw * 0.45, SMALL_SIZE), parts[0][1]),
                 (ink.fit("  ·  " + tail, tw * 0.55, SMALL_SIZE), "mu")]
    body.append(ink.runs(tx, y_award, parts, SMALL_SIZE)[0])

    return ink.doc(width, height, "".join(body), label(ship, index), mode)
