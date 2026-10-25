"""Render the Shipped journal: one spread for the star build and a page for each of the others.

Source of truth is var/log/hackathons.log (Bill appends one line per event):

    YYYY-MM-DD  EVENT  [TAG]  NAME — AWARD

The newest four entries (by date) are drawn by scripts/art_journal.py into
assets/journal/: the one with a "spread" record in ships.json (else the newest
win) gets the big spread (<slug>-spread.svg, -spread-light.svg,
-spread-phone.svg), the others a page each (<slug>.svg, <slug>-light.svg), in
log order, newest first. The HACKLOG marker block in README.md becomes the
spread, then the three pages side by side, each linked to its repo.

var/lib/ships.json (hand-maintained, never written here) maps NAME -> {
  "repo": "owner/name", "payload": one line, "lang", "stars", "forks",
  "quote": {"text": one of Bill's real commit subjects, "sha": its full hash,
            "when": its author time with the offset Bill's clock had},
  "spread": {"rows": [[label, value], ...], "words": one sentence from our own
             write-up, "words_from", "rows_from", "photo": a photos key in
             scripts/data/journal/prints.json}}

The quote check: every quote shown must be a real commit by IdkwhatImD0ing.
Before anything is drawn, each quote's commit is fetched from the GitHub API
(/repos/{repo}/commits/{sha}); its subject (the first line of its message)
must equal the quote exactly, typos included, and its author time must be the
same moment as "when". One quote that fails, or one that cannot be checked,
and nothing is drawn: the old files stay. A commit that passed once is noted
in var/lib/quotes-checked.json (a hash names one commit forever), so --offline
and a day the API is down can still draw quotes that were checked before, and
never one that was not.

Stars, forks and the language are still refreshed from the API for the run
log. A missing or unparseable ships.json is a failed render, not an empty one.

Never blank: everything renders in memory first; on any failure the script
warns, keeps the old files and exits 0. Missing markers warn and exit 0.
Only files carrying art_journal.SIGNATURE are ever pruned.
Run from the repo root: python scripts/render_hacklog.py [--offline] [--dry-run]
"""

from __future__ import annotations

import argparse
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
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

import art_journal as aj
import ink
from readme_blocks import replace_block

START = "<!-- HACKLOG:START -->"
END = "<!-- HACKLOG:END -->"
DEFAULT_LOG = "var/log/hackathons.log"
DEFAULT_SHIPS = "var/lib/ships.json"
DEFAULT_CHECKED = "var/lib/quotes-checked.json"
DEFAULT_OUT = "assets/journal"
SHOW = 4
OWNER = "IdkwhatImD0ing"
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
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
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
    quote: dict = field(default_factory=dict)
    spread: dict = field(default_factory=dict)
    checked: str = ""      # "live", "earlier" or "" (no quote)


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
    """Raises (so main keeps the old files) when the file is missing or broken."""
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))  # -sig: PowerShell 5.1 writes a BOM
    except (OSError, ValueError) as error:
        raise ValueError(f"{path} unreadable ({error})") from error
    if not isinstance(data, dict):
        raise ValueError(f"{path} is not a JSON object")
    return {str(k): v for k, v in data.items() if isinstance(v, dict)}


def parse_quote(raw: object, name: str) -> dict:
    """{"text", "sha", "when"}, or {} when there is none. A malformed quote
    raises: a typo in ships.json must not quietly drop the check."""
    if not raw:
        return {}
    if not isinstance(raw, dict):
        raise ValueError(f"{name}: quote must be an object")
    text = CONTROL.sub("", str(raw.get("text") or ""))
    sha = str(raw.get("sha") or "").strip().lower()
    when = str(raw.get("when") or "").strip()
    if not text or len(text) > 80 or text != text.strip():
        raise ValueError(f"{name}: quote text must be one line of 1-80 characters")
    if not SHA_RE.match(sha):
        raise ValueError(f"{name}: quote sha must be the full 40-character hash")
    try:
        moment = datetime.fromisoformat(when)
    except ValueError as error:
        raise ValueError(f"{name}: quote when is not an ISO time ({error})") from error
    if moment.tzinfo is None:
        raise ValueError(f"{name}: quote when needs its offset, e.g. -07:00")
    return {"text": text, "sha": sha, "when": when}


def parse_spread(raw: object, name: str) -> dict:
    if not raw:
        return {}
    if not isinstance(raw, dict):
        raise ValueError(f"{name}: spread must be an object")
    rows = []
    for row in raw.get("rows") or []:
        if not (isinstance(row, list) and len(row) == 2):
            raise ValueError(f"{name}: each spread row is [label, value]")
        rows.append([clean(row[0], 16), clean(row[1], 48)])
    return {"rows": rows[:5], "words": clean(raw.get("words"), 240), "photo": clean(raw.get("photo"), 32)}


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
        ship.quote = parse_quote(record.get("quote"), ship.name)
        ship.spread = parse_spread(record.get("spread"), ship.name)
        if ship.quote and not ship.repo:
            raise ValueError(f"{ship.name}: a quote needs the repo its commit is in")


def api_get(path: str, token: str) -> object:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "sect-journal",
               "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(API + path, headers=headers), timeout=API_TIMEOUT) as r:
        return json.load(r)


def fetch_live(ships: list[Ship], token: str) -> None:
    """Refresh stars/forks/language per repo. Each failure falls back quietly
    to the ships.json values for that repo only."""
    for ship in ships:
        if not ship.repo:
            continue
        try:
            data = api_get(ship.repo, token)
        except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError) as error:
            print(f"WARNING: {ship.repo}: live stats unavailable ({error}); using ships.json")
            continue
        if not isinstance(data, dict):
            continue
        stars, forks = to_count(data.get("stargazers_count")), to_count(data.get("forks_count"))
        if stars is None or forks is None:
            continue
        ship.stars, ship.forks, ship.live = stars, forks, True
        lang = clean(data.get("language"), 24)
        if lang:
            ship.lang = lang


# --- the quote check -----------------------------------------------------------------


def utc(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone(timezone.utc)


def commit_facts(data: object) -> dict:
    """What the API says about a commit: subject, author time (UTC) and login."""
    if not isinstance(data, dict) or not isinstance(data.get("commit"), dict):
        raise ValueError("unexpected answer")
    commit = data["commit"]
    author = commit.get("author") or {}
    login = (data.get("author") or {}).get("login") or ""
    message = str(commit.get("message") or "")
    return {"subject": message.split("\n", 1)[0].rstrip("\r"), "date": str(author.get("date") or ""),
            "login": str(login)}


def mismatch(quote: dict, facts: dict) -> str:
    """'' when the commit backs the quote, else what is wrong."""
    if facts.get("subject") != quote["text"]:
        return f"the commit says {facts.get('subject')!r}, the quote says {quote['text']!r}"
    if str(facts.get("login", "")).casefold() != OWNER.casefold():
        return f"the commit is by {facts.get('login') or 'an unknown account'}, not {OWNER}"
    try:
        same = utc(facts["date"]) == datetime.fromisoformat(quote["when"]).astimezone(timezone.utc)
    except (KeyError, ValueError):
        same = False
    if not same:
        return f"the commit was made at {facts.get('date')}, the quote says {quote['when']}"
    return ""


def load_checked(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def check_quotes(ships: list[Ship], token: str, offline: bool, checked: dict) -> dict:
    """Raise ValueError if any quote is not backed by its commit. Returns the
    updated record of checked commits."""
    record = dict(checked)
    for ship in ships:
        if not ship.quote:
            continue
        key = f"{ship.repo}@{ship.quote['sha']}"
        facts = None
        if not offline:
            try:
                facts = commit_facts(api_get(f"{ship.repo}/commits/{ship.quote['sha']}", token))
                ship.checked = "live"
            except urllib.error.HTTPError as error:
                if error.code in (404, 422):
                    raise ValueError(f"{ship.name}: no commit {ship.quote['sha'][:7]} in {ship.repo}") from error
                print(f"WARNING: {ship.name}: commit not checked live ({error})")
            except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError) as error:
                print(f"WARNING: {ship.name}: commit not checked live ({error})")
        if facts is None:
            facts = record.get(key)
            if not isinstance(facts, dict):
                raise ValueError(f"{ship.name}: the quote's commit has never been checked; run online")
            ship.checked = "earlier"
        wrong = mismatch(ship.quote, facts)
        if wrong:
            raise ValueError(f"{ship.name}: quote refused, {wrong}")
        if ship.checked == "live":
            record[key] = {"subject": facts["subject"], "date": facts["date"], "login": facts["login"]}
    return record


# --- README markup -------------------------------------------------------------


def star_of(ships: list[Ship]) -> Ship:
    """The build that gets the spread: the one with a spread record, else the newest win."""
    with_spread = [s for s in ships if s.spread]
    if len(with_spread) > 1:
        print(f"WARNING: {len(with_spread)} builds have a spread record; using {with_spread[0].name}")
    if with_spread:
        return with_spread[0]
    return next((s for s in ships if s.tag == "WIN"), ships[0])


def picture(base: str, alt: str, width: str, phone: bool) -> str:
    """phone=True: the spread's own phone file. phone=False (a page): phones get
    the dark page in both themes, like every other drawing on the profile."""
    esc = lambda s: html.escape(s, quote=True)  # noqa: E731
    phone_file = f"{base}-phone.svg" if phone else f"{base}.svg"
    sources = f'<source media="(max-width: 600px)" srcset="{esc(phone_file)}">'
    sources += f'<source media="(prefers-color-scheme: light)" srcset="{esc(base)}-light.svg">'
    return (f"<picture>{sources}<img src=\"{esc(base)}.svg\" width=\"{width}\" align=\"top\" "
            f"alt=\"{esc(alt)}\"></picture>")


def linked(ship: Ship, pic: str) -> str:
    if ship.repo:
        return f'<a href="https://github.com/{html.escape(ship.repo, quote=True)}">{pic}</a>'
    return pic


def block_markup(star: Ship, leaves: list[Ship], prefix: str) -> str:
    spread = linked(star, picture(f"{prefix}/{star.slug}-spread", aj.spread_alt(asdict(star)), "100%", True))
    pages = "".join(linked(s, picture(f"{prefix}/{s.slug}", aj.leaf_alt(asdict(s)), str(aj.LEAF_W), False))
                    for s in leaves)
    content = "<p>" + spread + ("<br>\n" + pages if pages else "") + "</p>"
    if START in content or END in content:
        raise ValueError("rendered markup unexpectedly contained README markers")
    return content


def asset_prefix(readme: Path, out_dir: Path) -> str:
    """Relative path from the README's folder to the SVGs, so a lab README in
    .preview/<key>/ gets ../../assets/journal and the real one assets/journal."""
    rel = os.path.relpath(out_dir.resolve(), readme.resolve().parent)
    return Path(rel).as_posix()


# --- main ----------------------------------------------------------------------


def render(star: Ship, leaves: list[Ship]) -> dict[str, str]:
    """Every SVG, in memory. Keys are file names."""
    files: dict[str, str] = {}
    s = asdict(star)
    files[f"{star.slug}-spread.svg"] = aj.spread_svg(s, "dark")
    files[f"{star.slug}-spread-light.svg"] = aj.spread_svg(s, "light")
    files[f"{star.slug}-spread-phone.svg"] = aj.spread_svg(s, "dark", phone=True)
    records = [asdict(x) for x in leaves]
    lines = aj.leaf_layout(records)       # the pages sit side by side, so they share one height
    for ship, record in zip(leaves, records):
        files[f"{ship.slug}.svg"] = aj.leaf_svg(record, "dark", lines)
        files[f"{ship.slug}-light.svg"] = aj.leaf_svg(record, "light", lines)
    return files


def self_test() -> None:
    """Offline checks of the quote check and the drawing (no network, writes nothing)."""
    def refused(fn, *a) -> bool:
        try:
            fn(*a)
        except ValueError:
            return True
        return False

    sha = "75485b726a305eb47246623883a653b766cbb7f7"
    good = {"text": "TRNASFERS WPORKSASDASDASDASDASAD", "sha": sha, "when": "2024-06-23T05:23:05-07:00"}
    facts = {"subject": good["text"], "date": "2024-06-23T12:23:05Z", "login": OWNER}
    assert parse_quote(good, "t") == good
    assert parse_quote(None, "t") == {}
    assert refused(parse_quote, dict(good, sha=sha[:7]), "t"), "a short hash must be refused"
    assert refused(parse_quote, dict(good, when="2024-06-23T05:23:05"), "t"), "a time with no offset must be refused"
    assert refused(parse_quote, dict(good, text="x" * 81), "t")
    assert mismatch(good, facts) == ""
    assert mismatch(dict(good, when="2024-06-23T14:23:05+02:00"), facts) == "", "the same moment in another zone"
    assert mismatch(dict(good, text="TRANSFERS WORKS"), facts), "a cleaned-up typo is not the commit"
    assert mismatch(dict(good, text=good["text"] + "!"), facts)
    assert mismatch(good, dict(facts, login="someone-else")), "a quote must be Bill's own commit"
    assert mismatch(good, dict(facts, date="2024-06-23T12:24:05Z")), "the time must match to the second"
    assert commit_facts({"commit": {"message": "Yay frontend works\n\nmore", "author": {"date": "x"}},
                         "author": {"login": OWNER}})["subject"] == "Yay frontend works"

    ship = Ship(date="2024-06-22", event="UC Berkeley AI Hackathon", tag="WIN", name="DispatchAI",
                award="Grand Prize", order=0, slug="dispatchai", repo="IdkwhatImD0ing/DispatchAI",
                payload="sorts 911 calls", quote=dict(good))
    key = f"{ship.repo}@{sha}"
    assert refused(check_quotes, [ship], "", True, {}), "a quote never checked must be refused offline"
    assert check_quotes([ship], "", True, {key: facts}) == {key: facts}
    assert ship.checked == "earlier"
    assert refused(check_quotes, [ship], "", True, {key: dict(facts, subject="Fix typo")})

    other = Ship(date="2024-11-16", event="HackUTD 2024", tag="WIN", name="TalkTuahBank", award="Overall 1st Place",
                 order=1, slug="talktuahbank", repo="aurelisajuan/TalkTuahBank", payload="banking over a phone call")
    ship.spread = {"rows": [["After", "a startup"]], "words": "", "photo": ""}
    assert star_of([other, ship]) is ship
    files = render(ship, [other])
    for name, svg in files.items():
        ET.fromstring(svg)
        assert aj.SIGNATURE in svg[:600], name
        assert "@keyframes" not in svg and "<animate" not in svg, name
    block = block_markup(ship, [other], "assets/journal")
    assert block.count("<picture>") == 2 and START not in block and "TRNASFERS" in block
    assert '<source media="(max-width: 600px)" srcset="assets/journal/talktuahbank.svg">' in block, \
        "a phone gets the dark page in both themes"
    long_page = Ship(**dict(asdict(other), quote=dict(good, text="TRNASFERS WPORKSASDASDASDASDASAD" * 2)))
    assert refused(render, ship, [long_page]), "a quote too long for a page must not be drawn cut"
    odd = Ship(**dict(asdict(other), quote=dict(good, text="Yay frontend works ☃")))
    assert refused(render, ship, [odd]), "a quote with a character we cannot draw must not be drawn without it"
    print("self-test: all assertions passed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--readme", default="README.md")
    parser.add_argument("--log", default=DEFAULT_LOG)
    parser.add_argument("--ships", default=DEFAULT_SHIPS, help="hand-maintained repo records (read only)")
    parser.add_argument("--checked", default=DEFAULT_CHECKED, help="commits whose quotes passed the check")
    parser.add_argument("--out-dir", default=DEFAULT_OUT, help="where the journal SVGs go")
    parser.add_argument("--offline", action="store_true",
                        help="skip the GitHub API: stats from ships.json, quotes only if checked before")
    parser.add_argument("--dry-run", action="store_true", help="print what would change; write nothing")
    parser.add_argument("--self-test", action="store_true", help="check the quote check and the drawing, offline")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):  # a cp1252 console must not crash on a non-ASCII name
        sys.stdout.reconfigure(errors="replace")
    if args.self_test:
        self_test()
        return

    out_dir, readme, checked_path = Path(args.out_dir), Path(args.readme), Path(args.checked)
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    try:
        ships = newest(parse_log(Path(args.log).read_text(encoding="utf-8-sig").splitlines()))
        if not ships:
            raise ValueError("hackathons.log has no entries")
        attach_records(ships, load_records(Path(args.ships)))
        checked = check_quotes(ships, token, args.offline, load_checked(checked_path))
        if not args.offline:
            fetch_live(ships, token)
        star = star_of(ships)
        leaves = [s for s in ships if s is not star]
        files = render(star, leaves)
        for name, content in files.items():  # validate everything before writing anything
            ET.fromstring(content)
            if aj.SIGNATURE not in content[:600]:
                raise ValueError(f"{name} lacks the journal signature; pruning could never find it")
        content = block_markup(star, leaves, asset_prefix(readme, out_dir))
    except Exception as error:  # never blank: any failure keeps the old files
        print(f"WARNING: journal not rendered: {error}")
        return

    for ship in ships:
        source = "live" if ship.live else ("ships.json" if ship.repo else "no record")
        role = "spread" if ship is star else "page"
        quote = f"quote checked {ship.checked}" if ship.quote else "no quote"
        print(f"{ship.date}  {ship.tag:<4}  {ship.name:<14} {role:<6} {ship.repo or '-':<28} [{source}; {quote}]")
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
        print(f"WARNING: journal not written: {error}")
        return
    print(f"journal: {changed} of {len(files)} file(s) changed in {out_dir}")

    text = json.dumps(checked, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    try:
        if not checked_path.exists() or checked_path.read_text(encoding="utf-8") != text:
            checked_path.parent.mkdir(parents=True, exist_ok=True)
            checked_path.write_text(text, encoding="utf-8", newline="\n")
            print(f"noted {len(checked)} checked commit(s) in {checked_path}")
    except OSError as error:
        print(f"WARNING: could not note the checked commits: {error}")

    try:
        updated = replace_block(str(readme), START, END, content)
    except (ValueError, OSError) as error:
        print(f"WARNING: skipped HACKLOG block: {error}")
        return
    print("Updated HACKLOG block" if updated else "HACKLOG block already current")

    # Pages for builds that scrolled out of the newest four are no longer
    # referenced. Only files this script drew are touched, so a stray
    # --out-dir can never take other SVGs with it.
    for stale in sorted(out_dir.glob("*.svg")):
        if stale.name in files:
            continue
        try:
            if aj.SIGNATURE in stale.read_text(encoding="utf-8", errors="replace")[:600]:
                stale.unlink()
                print(f"removed stale page {stale}")
        except OSError as error:
            print(f"WARNING: could not prune {stale}: {error}")


if __name__ == "__main__":
    main()
