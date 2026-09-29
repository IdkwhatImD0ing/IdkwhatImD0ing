"""Render tmux window 1:ships: the four newest hackathon ships as tmux panes.

Source of truth is var/log/hackathons.log (Bill appends one line per event):

    YYYY-MM-DD  EVENT  [TAG]  NAME — AWARD

The newest four entries (by date) each become one pane SVG in assets/ships/
(<slug>.svg dark, <slug>-light.svg safe mode, <slug>-phone.svg for phones),
and the HACKLOG marker block in README.md becomes a centered 2x2 grid of
those panes, each linked to its repo.

var/lib/ships.json (hand-maintained) maps NAME -> {"repo": "owner/name",
"payload": one line, "lang": str, "stars": int, "forks": int}. Stars, forks
and language are refreshed live from the GitHub REST API (GITHUB_TOKEN
optional); on any failure the ships.json values are used. This script never
writes ships.json. A log entry with no ships.json record still renders, just
without a link or stats. A missing or unparseable ships.json is a failed
render, not an empty one: one bad hand edit must not strip every link.

Never blank: everything renders in memory first; on any failure the script
warns, keeps the old files and exits 0. Missing markers warn and exit 0.
Run from the repo root: python scripts/render_hacklog.py [--dry-run]
"""

from __future__ import annotations

import argparse
import hashlib
import html
import http.client
import json
import os
import re
import sys
import textwrap
import unicodedata
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import phosphor as ph
from readme_blocks import replace_block

START = "<!-- HACKLOG:START -->"
END = "<!-- HACKLOG:END -->"
DEFAULT_LOG = "var/log/hackathons.log"
DEFAULT_SHIPS = "var/lib/ships.json"
DEFAULT_OUT = "assets/ships"
SHOW = 4
API = "https://api.github.com/repos/"
API_TIMEOUT = 10

# Pane geometry. Two desktop panes abut in 828px, so they share a row even in a
# maximized 1280px window, where the scrollbar leaves an 831px column. The
# gutter is baked into the SVGs: half of it on each side of every pane (so
# panes also stack flush when a narrower column wraps them one per row), and
# the same amount under each pane (so rows sit one gutter apart).
PANE_W = 414         # desktop pane image width (README width="414")
GUTTER = 4           # gap between neighbouring panes, both directions
MARGIN_B = GUTTER    # baked-in bottom margin == vertical gutter between rows
PAD = 14             # text inset from the panel edge
# (body size, chrome size, line height). Phones use the same scale as the
# hero-phone and fsck phone panes, so the whole phone page reads as one size.
DESK_TYPE = (ph.SIZE, ph.SIZE_CHROME, ph.LINE)
PHONE_TYPE = (12, 11, 18)
TITLE_Y = 14         # pane-border title line
TITLE_INSET = 8      # the border line stops short of the rounded corners
DOT_TOP = 32         # top of the dot-matrix name
DOT_PX = 4           # dot pitch; the name shrinks to 3 only if it must
LED_BEZEL = 5        # recessed display window around the dot field

# The oldest display on the page has one tired LED. Dark mode only; lit at t=0
# and between flickers; prefers-reduced-motion (ph.css) holds it steady.
FLICKER_CSS = (".flk{animation:phflk 6.7s steps(1) infinite 2.3s}"
               "@keyframes phflk{0%,86%{opacity:1}87%{opacity:.12}88%{opacity:1}"
               "90%{opacity:.3}91%,100%{opacity:1}}")

# The log is typed by hand: any run of spaces separates fields (the [TAG] marks
# where the event ends), and the canonical em dash beats looser separators, so
# "Tic - Tac - Toe \u2014 Grand Prize" keeps its name intact.
LOG_LINE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})\s+(?P<event>.+?)\s+\[(?P<tag>[A-Za-z0-9+-]{1,12})\]\s+(?P<rest>.+)$"
)
AWARD_SEPS = ("\u2014", "\u2013", "--", "-")
REPO_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})/(?!\.\.?$)[A-Za-z0-9._-]{1,100}$")
PANE_SIGNATURE = 'aria-label="tmux pane '  # only files carrying it are ever pruned
CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f\u200b-\u200f\u2028-\u202e\u2066-\u2069\ufeff]")


# --- data ----------------------------------------------------------------------


@dataclass
class Ship:
    date: str
    event: str
    tag: str
    name: str
    award: str
    order: int
    slug: str = ""
    repo: str = ""
    payload: str = ""
    lang: str = ""
    stars: int | None = None
    forks: int | None = None
    live: bool = False


def clean(value: object, limit: int = 80) -> str:
    """One printable line: no control or bidi characters, collapsed spaces."""
    text = CONTROL.sub(" ", str(value or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit].rstrip()


def ascii_fold(text: str) -> str:
    """Accents off, anything else non-ASCII dropped: 'CAFÉ' -> 'CAFE'."""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def split_award(rest: str) -> tuple[str, str]:
    for sep in AWARD_SEPS:
        parts = re.split(rf"\s+{re.escape(sep)}(?:\s+|$)", rest, maxsplit=1)
        if len(parts) == 2:
            return parts[0], parts[1]
    return rest, ""


def to_count(value: object) -> int | None:
    try:
        number = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if 0 <= number < 10_000_000 else None


def parse_log(lines: list[str]) -> list[Ship]:
    ships = []
    for order, raw in enumerate(lines):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = LOG_LINE.match(line)
        if not match:
            print(f"WARNING: hackathons.log line {order + 1} not understood, skipped: {clean(line, 60)!r}")
            continue
        try:
            date.fromisoformat(match["date"])
        except ValueError:
            print(f"WARNING: hackathons.log line {order + 1} has a bad date, skipped")
            continue
        name, award = split_award(match["rest"])
        ships.append(Ship(date=match["date"], event=clean(match["event"], 80), tag=clean(match["tag"], 12).upper(),
                          name=clean(name, 60), award=clean(award, 80), order=order))
    return [s for s in ships if s.name]


def newest(ships: list[Ship], count: int = SHOW) -> list[Ship]:
    """Newest first. Same-day entries: the line appended later wins."""
    return sorted(ships, key=lambda s: (s.date, s.order), reverse=True)[:count]


def slugify(name: str, taken: set[str]) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", ascii_fold(name.casefold())).strip("-")[:32] or "ship"
    slug, n = base, 2
    while slug in taken:
        slug, n = f"{base}-{n}", n + 1
    taken.add(slug)
    return slug


def load_records(path: Path) -> dict[str, dict]:
    """Raises (so main keeps the old panes) when the file is missing or broken."""
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))  # -sig: PowerShell 5.1 writes a BOM
    except (OSError, ValueError) as error:
        raise ValueError(f"{path} unreadable ({error})") from error
    if not isinstance(data, dict):
        raise ValueError(f"{path} is not a JSON object")
    return {str(k): v for k, v in data.items() if isinstance(v, dict)}


def attach_records(ships: list[Ship], records: dict[str, dict]) -> None:
    folded = {k.casefold(): v for k, v in records.items()}
    taken: set[str] = set()
    for ship in ships:
        ship.slug = slugify(ship.name, taken)
        record = records.get(ship.name) or folded.get(ship.name.casefold())
        if not record:
            continue
        repo = clean(record.get("repo"), 140)
        ship.repo = repo if REPO_RE.match(repo) else ""
        ship.payload = clean(record.get("payload"), 120)
        ship.lang = clean(record.get("lang"), 24)
        ship.stars = to_count(record.get("stars"))
        ship.forks = to_count(record.get("forks"))


def fetch_live(ships: list[Ship], token: str) -> None:
    """Refresh stars/forks/language per repo. Each failure falls back quietly
    to the ships.json values for that repo only."""
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "tianni-hacklog",
               "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    for ship in ships:
        if not ship.repo:
            continue
        request = urllib.request.Request(API + ship.repo, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=API_TIMEOUT) as response:
                data = json.load(response)
        except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError) as error:
            print(f"WARNING: {ship.repo}: live stats unavailable ({error}); using ships.json")
            continue
        if not isinstance(data, dict):
            print(f"WARNING: {ship.repo}: unexpected API answer; using ships.json")
            continue
        stars, forks = to_count(data.get("stargazers_count")), to_count(data.get("forks_count"))
        if stars is None or forks is None:
            print(f"WARNING: {ship.repo}: API answer had no counts; using ships.json")
            continue
        ship.stars, ship.forks, ship.live = stars, forks, True
        lang = clean(data.get("language"), 24)
        if lang:
            ship.lang = lang


# --- drawing helpers -----------------------------------------------------------


def fit(text: str, chars: int) -> str:
    """Clip to `chars` columns, ending in '...' when there is room for it."""
    if len(text) <= chars:
        return text
    if chars < 4:
        return text[:max(chars, 0)]
    return text[:chars - 3].rstrip() + "..."


def stats_line(ship: Ship) -> str:
    if not ship.repo:
        return "no remote"
    if ship.stars is None or ship.forks is None:
        return ""
    return f"{ph.plural(ship.stars, 'star')}  {ph.plural(ship.forks, 'fork')}"


def award_label(ship: Ship) -> str:
    return ship.award.lower() if ship.award else "logged"


def verdict(ship: Ship) -> str:
    return {"WIN": "won", "SHIP": "shipped"}.get(ship.tag, ship.tag.lower())


def led_label(name: str) -> str:
    """The name as the 5x7 face can show it: upper case, accents folded
    ('Café' -> 'CAFE'), anything else a blank cell."""
    return "".join(ascii_fold(ch) or " " for ch in name.upper())


def dot_cells(s: str, x: float, y: float, px: float) -> list[str]:
    """The lit dots of the ph.dot_text face, one path segment per dot (so one
    dot can be pulled out to flicker)."""
    return [ph.cell_d(cx, cy, px - 1) for i, ch in enumerate(s.upper())
            for cx, cy in ph.glyph_cells(ch, x + i * 6 * px, y, px)]


def led_module(name: str, x: float, y: float, avail: float, px: float = DOT_PX,
               flaky: bool = False) -> tuple[str, str]:
    """The project name on a dot-matrix display module: a recessed window (the
    fsck board's flat material) holding a full-width field of unlit dots (one
    <pattern>, so it costs bytes once), with the name's dots lit and glowing.
    Every pane gets the same module whatever the name length, and the dots
    start on the text column. `flaky` gives one lit dot (picked by a hash of
    the name, so it never moves between renders) an aging-hardware flicker.
    Returns (defs, body)."""
    label = led_label(name)
    while px > 3 and ph.dot_width(label, px) > avail:
        px -= 1
    while len(label) > 1 and ph.dot_width(label, px) > avail:
        label = label[:-1]
    size = ph.fmt(px - 1)
    field_w = int((avail + 1) // px) * px - 1
    field_h = 7 * px - 1
    bez = LED_BEZEL
    cells, flicker = dot_cells(label, x, y, px), ""
    if flaky and len(cells) > 1:
        pick = cells.pop(int(hashlib.sha256(name.encode("utf-8")).hexdigest(), 16) % len(cells))
        flicker = f'<path class="acc flk" d="{pick}"/>'
    defs = (f'<pattern id="led" x="{ph.fmt(x)}" y="{ph.fmt(y)}" width="{ph.fmt(px)}" height="{ph.fmt(px)}" '
            f'patternUnits="userSpaceOnUse"><rect width="{size}" height="{size}" class="gh"/></pattern>')
    body = (f'<rect x="{ph.fmt(x - bez + 0.5)}" y="{ph.fmt(y - bez + 0.5)}" width="{ph.fmt(field_w + 2 * bez - 1)}" '
            f'height="{ph.fmt(field_h + 2 * bez - 1)}" rx="3" class="flat"/>'
            f'<rect x="{ph.fmt(x - bez + 0.5)}" y="{ph.fmt(y - bez + 0.5)}" width="{ph.fmt(field_w + 2 * bez - 1)}" '
            f'height="{ph.fmt(field_h + 2 * bez - 1)}" rx="3" class="fl-s" stroke-width="1"/>'
            f'<rect x="{ph.fmt(x)}" y="{ph.fmt(y)}" width="{ph.fmt(field_w)}" height="{ph.fmt(field_h)}" '
            f'fill="url(#led)"/>'
            f'<g class="glow"><path class="acc" d="{"".join(cells)}"/>{flicker}</g>')
    return defs, body


def border_title(x0: float, x1: float, y: float, left: str, right: list[tuple[str, str]],
                 active: bool, size: float = ph.SIZE_CHROME) -> str:
    """ph.pane_title, but the right-hand title is a list of colored runs, so a
    [WIN] tag can stay phosphor while the award takes the pane's title color.
    A run class of "" means "the title color"; a trailing '!' means bold."""
    cw = ph.CW * size
    line_cls = "acc-s" if active else "ln"
    title_cls = "acc" if active else "mu"
    base = y + size * 0.33
    lx = x0 + 12
    out = [ph.hline(x0, lx - 6, y, line_cls), ph.text(lx, base, left, title_cls, size, bold=active)]
    end = x1
    if right:
        parts = [(t, c or (title_cls + ("!" if active else ""))) for t, c in right]
        rlen = sum(len(t) for t, _ in parts)
        rx = x1 - 12 - rlen * cw
        out.append(ph.runs(rx, base, parts, size))
        out.append(ph.hline(rx + rlen * cw + 6, x1, y, line_cls))
        end = rx - 6
    start = lx + len(left) * cw + 6
    if end > start:
        out.append(ph.hline(start, end, y, line_cls))
    return "".join(out)


def balanced_wrap(text: str, width: int, max_lines: int) -> list[str]:
    """Wrap to the fewest lines, then even them out, so a two-line payload never
    ends on one orphaned word. Overflow past max_lines is clipped with '...'."""
    lines = textwrap.wrap(text, width, break_on_hyphens=False) or [""]
    if len(lines) > max_lines:
        return lines[:max_lines - 1] + [fit(" ".join(lines[max_lines - 1:]), width)]
    for narrower in range(width - 1, width // 2, -1):
        trial = textwrap.wrap(text, narrower, break_on_hyphens=False)
        if len(trial) != len(lines):
            break
        lines = trial
    return lines


def payload_lines_needed(ships: list[Ship], width: float, size: float) -> int:
    cols = int((width - 2 * PAD) // (ph.CW * size))
    return max((min(len(textwrap.wrap(s.payload, cols, break_on_hyphens=False)), 2) for s in ships if s.payload),
               default=1)


# --- the pane ------------------------------------------------------------------


def pane_label(ship: Ship, index: int, active: bool) -> str:
    bits = [f"tmux pane {index}{' (active)' if active else ''}: {ship.name}."]
    bits.append(f"{verdict(ship)}: {ship.award or 'logged'} at {ship.event}, {ship.date}.")
    if ship.payload:
        bits.append(ship.payload.rstrip(".") + ".")
    facts = [x for x in (ship.lang, stats_line(ship).replace("  ", ", ")) if x]
    if facts:
        bits.append(", ".join(facts) + ".")
    bits.append(f"$ cd ~/ships/{ship.slug}")
    return " ".join(bits)


def pane_svg(ship: Ship, index: int, active: bool, mode: str, phone: bool = False,
             payload_lines: int = 1, flaky: bool = False) -> str:
    """One tmux pane. Desktop panes are PANE_W wide with half a gutter baked
    into each side; phone panes are ph.WP wide, use the phone type scale and
    move the repo stats onto their own row. Height grows only with payload_lines, which the caller keeps
    equal across a set so rows stay aligned."""
    size, chrome, lh = PHONE_TYPE if phone else DESK_TYPE
    cw = ph.CW * size
    if phone:
        width, px0, pw = ph.WP, 0.0, float(ph.WP)
    else:
        width, px0, pw = PANE_W, GUTTER / 2, PANE_W - GUTTER
    tx, rx = px0 + PAD, px0 + pw - PAD
    cols = int((rx - tx) // cw)
    stats = stats_line(ship)

    # key/value rows under the payload; labels are padded to one column
    rows: list[tuple[str, list[tuple[str, str]]]] = [("event", [(ship.event, "fg")])]
    rows.append(("date", [(ship.date, "fg")] + ([("  ", ""), (ship.lang, "mu")] if ship.lang else [])))
    if phone and stats:
        rows.append(("repo", [(stats, "mu" if ship.repo else "warn")]))

    # vertical rhythm: title line, LED module, payload, rows, prompt
    y_pay = DOT_TOP + 7 * DOT_PX + 23
    y_rows = y_pay + (payload_lines - 1) * lh + lh + 4
    y_prompt = y_rows + (len(rows) - 1) * lh + lh + 5
    panel_h = y_prompt + 14
    height = panel_h + MARGIN_B

    body = [ph.panel(px0, 0, pw, panel_h)]
    if active:  # tmux draws the active pane's whole border in the active color
        body.append(f'<rect x="{ph.fmt(px0 + 0.5)}" y="0.5" width="{ph.fmt(pw - 1)}" '
                    f'height="{ph.fmt(panel_h - 1)}" rx="6" class="accd-s" stroke-width="1"/>')

    # pane-border title: "N Name" left, "[TAG] award" right, clipped to fit
    title_cols = int((pw - 2 * TITLE_INSET - 24) // (ph.CW * chrome))
    left = fit(f"{index} {ship.name}", 24)
    tag = f"[{ship.tag}]"
    award = fit(award_label(ship), max(title_cols - len(left) - len(tag) - 1 - 4, 3))
    tag_cls = ("acc" if ship.tag == "WIN" else "mu") + ("!" if active else "")
    body.append(border_title(px0 + TITLE_INSET, px0 + pw - TITLE_INSET, TITLE_Y, left,
                             [(tag, tag_cls), (" ", ""), (award, "")], active, chrome))

    flaky = flaky and mode == "dark"  # safe mode never animates
    defs, display = led_module(ship.name, tx, DOT_TOP, rx - tx, flaky=flaky)
    body.append(display)

    if ship.payload:
        for k, line in enumerate(balanced_wrap(ship.payload, cols, payload_lines)):
            body.append(ph.text(tx, y_pay + k * lh, line, "fg", size))
    else:  # a gap in the data gets an in-fiction excuse, never a made-up payload
        body.append(ph.text(tx, y_pay, fit("no payload on file. it shipped anyway.", cols), "mu", size))

    for k, (label, value) in enumerate(rows):
        room = cols - 7
        parts, used = [], 0
        for chunk, cls in value:
            chunk = fit(chunk, room - used)
            parts.append((chunk, cls))
            used += len(chunk)
            if used >= room:
                break
        body.append(ph.runs(tx, y_rows + k * lh, [(label, "mu"), (" " * (7 - len(label)), "")] + parts, size))

    # bottom row: the prompt, the cursor (active pane only), repo stats (desktop).
    # The path gets what "$ " and " <cursor> " leave next to the stats.
    def path_room(stats_text: str) -> int:
        return cols - 2 - (len(stats_text) + 3 if stats_text else 2)

    path = f"cd ~/ships/{ship.slug}"
    right = "" if phone else stats
    if right and len(path) > path_room(right) and ship.stars is not None:
        right = ph.plural(ship.stars, "star")  # long slug: drop forks before clipping the path
    path = fit(path, path_room(right))
    body.append(ph.runs(tx, y_prompt, [("$", "acc!"), (" ", ""), (path, "fg")], size))
    if active:
        blink = " blink" if mode == "dark" else ""  # safe mode never animates
        cap = round(size * 0.85)
        body.append(f'<rect x="{ph.fmt(tx + (len(path) + 3) * cw)}" y="{ph.fmt(y_prompt - cap)}" '
                    f'width="{ph.fmt(cw)}" height="{ph.fmt(size + 1)}" class="acc{blink}"/>')
    if right:
        body.append(ph.text(rx, y_prompt, right, "mu" if ship.repo else "warn", size, anchor="end"))

    return ph.svg(width, height, "".join(body), pane_label(ship, index, active), mode,
                  extra_css=FLICKER_CSS if flaky else "", defs=defs)


# --- README markup -------------------------------------------------------------


def alt_text(ship: Ship) -> str:
    award = ship.award or verdict(ship)
    text = f"{ship.name}: {award} at {ship.event}, {ship.date}."
    if ship.payload:
        text += " " + ship.payload.rstrip(".") + "."
    return text


def pane_markup(ship: Ship, prefix: str) -> str:
    esc = lambda s: html.escape(s, quote=True)  # noqa: E731
    base = f"{prefix}/{ship.slug}"
    picture = (
        f'<picture><source media="(max-width: 600px)" srcset="{esc(base)}-phone.svg">'
        f'<source media="(prefers-color-scheme: light)" srcset="{esc(base)}-light.svg">'
        f'<img src="{esc(base)}.svg" width="{PANE_W}" align="top" alt="{esc(alt_text(ship))}"></picture>'
    )
    if ship.repo:
        return f'<a href="https://github.com/{esc(ship.repo)}">{picture}</a>'
    return picture


def block_markup(ships: list[Ship], prefix: str) -> str:
    rows = ["".join(pane_markup(s, prefix) for s in ships[i:i + 2]) for i in range(0, len(ships), 2)]
    content = '<p align="center">' + "<br>\n".join(rows) + "</p>"
    if START in content or END in content:
        raise ValueError("rendered markup unexpectedly contained README markers")
    return content


def asset_prefix(readme: Path, out_dir: Path) -> str:
    """Relative path from the README's folder to the pane SVGs, so a lab README
    in .preview/<key>/ gets ../../assets/ships and the real one assets/ships."""
    rel = os.path.relpath(out_dir.resolve(), readme.resolve().parent)
    return Path(rel).as_posix()


# --- main ----------------------------------------------------------------------


def render(ships: list[Ship]) -> dict[str, str]:
    """Every SVG for the given ships, in memory. Keys are file names."""
    files: dict[str, str] = {}
    # Desktop panes sit side by side, so the whole set shares one height.
    # Phone panes always stack, so each keeps its own (no blank payload rows).
    desk_lines = payload_lines_needed(ships, PANE_W - GUTTER, DESK_TYPE[0])
    for index, ship in enumerate(ships):
        phone_lines = payload_lines_needed([ship], ph.WP, PHONE_TYPE[0])
        active = index == 0  # the newest ship is the active pane
        flaky = len(ships) > 1 and index == len(ships) - 1  # the oldest display has a tired LED
        files[f"{ship.slug}.svg"] = pane_svg(ship, index, active, "dark",
                                             payload_lines=desk_lines, flaky=flaky)
        files[f"{ship.slug}-light.svg"] = pane_svg(ship, index, active, "light",
                                                   payload_lines=desk_lines)
        files[f"{ship.slug}-phone.svg"] = pane_svg(ship, index, active, "dark", phone=True,
                                                   payload_lines=phone_lines, flaky=flaky)
    return files


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--readme", default="README.md")
    parser.add_argument("--log", default=DEFAULT_LOG)
    parser.add_argument("--ships", default=DEFAULT_SHIPS, help="hand-maintained repo records (read only)")
    parser.add_argument("--out-dir", default=DEFAULT_OUT, help="where the pane SVGs go")
    parser.add_argument("--offline", action="store_true", help="skip the GitHub API; use ships.json stats")
    parser.add_argument("--dry-run", action="store_true", help="print what would change; write nothing")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):  # a cp1252 console must not crash on a non-ASCII name
        sys.stdout.reconfigure(errors="replace")

    out_dir, readme = Path(args.out_dir), Path(args.readme)
    try:
        ships = newest(parse_log(Path(args.log).read_text(encoding="utf-8-sig").splitlines()))
        if not ships:
            raise ValueError("hackathons.log has no entries")
        attach_records(ships, load_records(Path(args.ships)))
        if not args.offline:
            fetch_live(ships, os.environ.get("GITHUB_TOKEN", "").strip())
        files = render(ships)
        for name, content in files.items():  # validate everything before writing anything
            ET.fromstring(content)
        content = block_markup(ships, asset_prefix(readme, out_dir))
    except Exception as error:  # never blank: any failure keeps the old files
        print(f"WARNING: hacklog not rendered: {error}")
        return

    for ship in ships:
        source = "live" if ship.live else ("ships.json" if ship.repo else "no record")
        print(f"{ship.date}  {ship.tag:<4}  {ship.name:<14} {ship.repo or '-':<28} "
              f"{ship.lang or '-':<16} {stats_line(ship) or '-':<18} [{source}]")
    if args.dry_run:
        for name, svg_text in files.items():
            print(f"would write {out_dir / name} ({len(svg_text.encode('utf-8'))} bytes)")
        print("--- HACKLOG ---")
        print(content)
        return

    changed = 0
    try:
        for name, svg_text in files.items():
            changed += ph.write_svg(out_dir / name, svg_text)
    except (OSError, ValueError) as error:
        print(f"WARNING: ship panes not written: {error}")
        return
    print(f"ships: {changed} of {len(files)} pane file(s) changed in {out_dir}")

    try:
        updated = replace_block(str(readme), START, END, content)
    except (ValueError, OSError) as error:
        print(f"WARNING: skipped HACKLOG block: {error}")
        return
    print("Updated HACKLOG block" if updated else "HACKLOG block already current")

    # Panes for ships that scrolled out of the newest four are no longer
    # referenced. Only files this script drew are touched, so a stray
    # --out-dir can never take other SVGs with it.
    for stale in sorted(out_dir.glob("*.svg")):
        if stale.name in files:
            continue
        try:
            if PANE_SIGNATURE in stale.read_text(encoding="utf-8", errors="replace")[:600]:
                stale.unlink()
                print(f"removed stale pane {stale}")
        except OSError as error:
            print(f"WARNING: could not prune {stale}: {error}")


if __name__ == "__main__":
    main()
