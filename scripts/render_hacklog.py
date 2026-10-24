"""Render the Shipped cards: the four newest hackathon builds, one quiet card each.

Source of truth is var/log/hackathons.log (Bill appends one line per event):

    YYYY-MM-DD  EVENT  [TAG]  NAME — AWARD

The newest four entries (by date) each become one card SVG in assets/forge/
(<slug>.svg dark, <slug>-light.svg for light mode, <slug>-phone.svg for
phones), drawn by scripts/art_forge.py, and the HACKLOG marker block in
README.md becomes a left-aligned 2x2 grid of those cards, each linked to its
repo. (The folder and the "forged artifact" signature keep their old names on
purpose: they are invisible to readers.)

var/lib/ships.json (hand-maintained) maps NAME -> {"repo": "owner/name",
"payload": one line, "lang": str, "stars": int, "forks": int}. The cards show
only the name, the payload and the award line; stars, forks and language are
still refreshed from the GitHub REST API (GITHUB_TOKEN optional) for the run
log, and on any failure the ships.json values are used. This script never
writes ships.json. A log entry with no ships.json record still renders, just
without a link. A missing or unparseable ships.json is a failed render, not
an empty one: one bad hand edit must not strip every link.

Never blank: everything renders in memory first; on any failure the script
warns, keeps the old files and exits 0. Missing markers warn and exit 0.
Only files carrying art_forge.SIGNATURE are ever pruned.
Run from the repo root: python scripts/render_hacklog.py [--offline] [--dry-run]
"""

from __future__ import annotations

import argparse
import dataclasses
import html
import http.client
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import art_forge as af
import ink
from readme_blocks import replace_block

START = "<!-- HACKLOG:START -->"
END = "<!-- HACKLOG:END -->"
DEFAULT_LOG = "var/log/hackathons.log"
DEFAULT_SHIPS = "var/lib/ships.json"
DEFAULT_OUT = "assets/forge"
SHOW = 4
API = "https://api.github.com/repos/"
API_TIMEOUT = 10

# The log is typed by hand: any run of spaces separates fields (the [TAG] marks
# where the event ends), and the canonical em dash beats looser separators, so
# "Tic - Tac - Toe — Grand Prize" keeps its name intact.
LOG_LINE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})\s+(?P<event>.+?)\s+\[(?P<tag>[A-Za-z0-9+-]{1,12})\]\s+(?P<rest>.+)$"
)
AWARD_SEPS = ("—", "–", "--", "-")
REPO_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})/(?!\.\.?$)[A-Za-z0-9._-]{1,100}$")
CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f​-‏ -‮⁦-⁩﻿]")


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
    """Raises (so main keeps the old artifacts) when the file is missing or broken."""
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
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "sect-forge",
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



# --- small facts -----------------------------------------------------------------


def plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def stats_line(ship: Ship) -> str:
    if not ship.repo:
        return "no remote"
    if ship.stars is None or ship.forks is None:
        return ""
    return f"{plural(ship.stars, 'star')}  {plural(ship.forks, 'fork')}"


def verdict(ship: Ship) -> str:
    return {"WIN": "won", "SHIP": "shipped"}.get(ship.tag, ship.tag.lower())


# --- README markup -------------------------------------------------------------


def alt_text(ship: Ship) -> str:
    """'TalkTuahBank: Overall 1st Place at HackUTD 2024, November 2024. Voice-first
    banking for the people banks forgot. Opens the source on GitHub.'"""
    record = dataclasses.asdict(ship)
    award = ship.award or verdict(ship)
    text = f"{ship.name}: {award} at {ship.event}, {af.month(record, long=True)}."
    if ship.payload:
        text += " " + af.one_liner(record) + "."
    if ship.repo:
        text += " Opens the source on GitHub."
    return text


def artifact_markup(ship: Ship, prefix: str) -> str:
    esc = lambda s: html.escape(s, quote=True)  # noqa: E731
    base = f"{prefix}/{ship.slug}"
    picture = (
        f'<picture><source media="(max-width: 600px)" srcset="{esc(base)}-phone.svg">'
        f'<source media="(prefers-color-scheme: light)" srcset="{esc(base)}-light.svg">'
        f'<img src="{esc(base)}.svg" width="{af.PANE_W}" align="top" alt="{esc(alt_text(ship))}"></picture>'
    )
    if ship.repo:
        return f'<a href="https://github.com/{esc(ship.repo)}">{picture}</a>'
    return picture


def block_markup(ships: list[Ship], prefix: str) -> str:
    rows = ["".join(artifact_markup(s, prefix) for s in ships[i:i + 2]) for i in range(0, len(ships), 2)]
    content = "<p>" + "<br>\n".join(rows) + "</p>"
    if START in content or END in content:
        raise ValueError("rendered markup unexpectedly contained README markers")
    return content


def asset_prefix(readme: Path, out_dir: Path) -> str:
    """Relative path from the README's folder to the artifact SVGs, so a lab
    README in .preview/<key>/ gets ../../assets/forge and the real one assets/forge."""
    rel = os.path.relpath(out_dir.resolve(), readme.resolve().parent)
    return Path(rel).as_posix()


# --- main ----------------------------------------------------------------------


def render(ships: list[Ship]) -> dict[str, str]:
    """Every SVG for the given ships, in memory. Keys are file names."""
    files: dict[str, str] = {}
    records = [dataclasses.asdict(ship) for ship in ships]
    # Desktop cards sit side by side, so the whole set shares one height.
    # Phone cards always stack, so each keeps its own (no blank payload rows).
    desk_lines = af.payload_lines_needed(records, False)
    for index, (ship, record) in enumerate(zip(ships, records)):
        phone_lines = af.payload_lines_needed([record], True)
        files[f"{ship.slug}.svg"] = af.artifact_svg(record, index, mode="dark", payload_lines=desk_lines)
        files[f"{ship.slug}-light.svg"] = af.artifact_svg(record, index, mode="light", payload_lines=desk_lines)
        files[f"{ship.slug}-phone.svg"] = af.artifact_svg(record, index, mode="dark", phone=True,
                                                          payload_lines=phone_lines)
    return files


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--readme", default="README.md")
    parser.add_argument("--log", default=DEFAULT_LOG)
    parser.add_argument("--ships", default=DEFAULT_SHIPS, help="hand-maintained repo records (read only)")
    parser.add_argument("--out-dir", default=DEFAULT_OUT, help="where the artifact SVGs go")
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
            if af.SIGNATURE not in content[:600]:
                raise ValueError(f"{name} lacks the forge signature; pruning could never find it")
        content = block_markup(ships, asset_prefix(readme, out_dir))
    except Exception as error:  # never blank: any failure keeps the old files
        print(f"WARNING: forge not rendered: {error}")
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
            changed += bool(ink.write_svg(out_dir / name, svg_text))
    except (OSError, ValueError) as error:
        print(f"WARNING: artifacts not written: {error}")
        return
    print(f"forge: {changed} of {len(files)} artifact file(s) changed in {out_dir}")

    try:
        updated = replace_block(str(readme), START, END, content)
    except (ValueError, OSError) as error:
        print(f"WARNING: skipped HACKLOG block: {error}")
        return
    print("Updated HACKLOG block" if updated else "HACKLOG block already current")

    # Artifacts for ships that scrolled out of the newest four are no longer
    # referenced. Only files this script drew are touched, so a stray
    # --out-dir can never take other SVGs with it.
    for stale in sorted(out_dir.glob("*.svg")):
        if stale.name in files:
            continue
        try:
            if af.SIGNATURE in stale.read_text(encoding="utf-8", errors="replace")[:600]:
                stale.unlink()
                print(f"removed stale artifact {stale}")
        except OSError as error:
            print(f"WARNING: could not prune {stale}: {error}")


if __name__ == "__main__":
    main()
