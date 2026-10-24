"""Minesweeper you play by opening GitHub issues, plus the gong and the sandwich reply.

Visitors play minesweeper against the 护宗大阵, the Grand Sect-Protecting
Formation, by opening issues. This module is the engine, the title router and
the README block renderer.

Usage (always from the repo root):

    python scripts/artemis_ops.py init
    python scripts/artemis_ops.py process --title STR --actor LOGIN --issue INT
    python scripts/artemis_ops.py render
    python scripts/artemis_ops.py tiles
    python scripts/artemis_ops.py self-test

Titles (prefixes are case-sensitive; the cell letter is not):

    sect|zhen|C4      read one node        (legacy: artemis|fsck|C4)
    sect|zhen|relay   re-lay the formation (legacy: artemis|fsck|reformat)
    sect|gong         strike the gong      (legacy: artemis|button)
    sudo make me a sandwich

The legacy titles are the sect's previous life (a machine called tianni);
they keep working so old links and open issues never break.

Contract for `process`: stdout is EXACTLY the plain issue-comment reply
(nothing else), and the exit code is always 0. Diagnostics go to stderr.

Presentation: the board is one drawn device assembled from static tiles in
assets/formation/tiles/{dark,light}/, with a status panel floated beside it.
All drawing lives in scripts/art_formation.py (tiles, keys, panel); this file
builds the README markup around it. The panel SVGs
(assets/formation/panel-<seq>*.svg) are redrawn on every render; their file
names carry the stats.json `seq` counter, because GitHub's /raw/ redirect
drops query strings (a ?n= cache-buster would not survive) and the raw CDN
caches each path for five minutes.

Anti-cheat: trap (mine) positions are never persisted for an active board.
They are recomputed on demand from HMAC(FSCK_SALT, board_number:first_cell);
the state file only stores revealed cells with their adjacency digits (public
info a player has already earned). Without the FSCK_SALT repo secret the
engine falls back to a public salt and the panel says the mines can be found
in the source. Never change DEFAULT_SALT, the HMAC message,
place_mines, MINE_COUNT, the state/stats JSON keys or the data/fsck/ paths:
any of them silently corrupts the live board. Stats keep logging the old op
names (`fsck C4`, `reformat`, `button`); the view maps them for display.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import html
import json
import os
import random
import re
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus

from readme_blocks import display_cols, replace_block

try:  # the reply never depends on the drawing: a broken art module costs a redraw, not an answer
    import art_formation as af
    import ink
except Exception as _art_error:  # noqa: BLE001
    af = ink = None
    ART_ERROR = f"{type(_art_error).__name__}: {_art_error}"
else:
    ART_ERROR = ""


USERNAME = "IdkwhatImD0ing"
REPO_URL = f"https://github.com/{USERNAME}/{USERNAME}"
STATE_PATH = Path("data/fsck/state.json")
STATS_PATH = Path("data/fsck/stats.json")
ONELINERS_PATH = Path("scripts/data/oneliners.txt")

FSCK_START = "<!-- FSCK:START -->"
FSCK_END = "<!-- FSCK:END -->"
ONELINER_START = "<!-- BOOT_ONELINER:START -->"
ONELINER_END = "<!-- BOOT_ONELINER:END -->"

COLS = "ABCDEFGHI"
ROWS = "123456789"
ALL_CELLS = tuple(f"{col}{row}" for row in ROWS for col in COLS)
MINE_COUNT = 10
CLEAN_TOTAL = len(ALL_CELLS) - MINE_COUNT  # 71

DEFAULT_SALT = "artemis-believes-in-open-source"

CMD_RE = re.compile(
    r"^(?:sect\|(?:zhen\|(?:(?P<cell>[A-Ia-i][1-9])|(?P<relay>relay))|(?P<gong>gong))"
    r"|artemis\|(?:fsck\|(?:(?P<legacy_cell>[A-Ia-i][1-9])|(?P<reformat>reformat))|(?P<button>button)))$"
)
SCAN_TITLE = "sect|zhen|{cell}"
RELAY_TITLE = "sect|zhen|relay"
GONG_TITLE = "sect|gong"
SANDWICH_TITLE = "sudo make me a sandwich"
SANDWICH_REPLY = "Okay."  # xkcd 149
GONG_REPLY = "Nothing happened."
INTERNAL_FAULT = "Something went wrong on my end. Try again in a minute."

OPS_LOG_LIMIT = 12
OPS_SHOWN = 4
HALL_ROWS = 3
OP_COLS = 10      # the panel's op column: "step C4", "re-lay", "gong"
RESULT_COLS = 16  # the longest result label: "FORMATION BROKEN"
PHONE_W = 360
RESULTS = ("ok", "dup", "panic", "clean", "reformat", "refused", "press")

SCAN_BODY = "Submit this issue to open {cell}. The board on my profile updates in about a minute."
RELAY_BODY = "Submit this issue to start a new board. It only works once the current game is won or lost."
GONG_BODY = ":)"


def warn(message: str) -> None:
    print(f"[artemis_ops] {message}", file=sys.stderr)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sanitize_login(login: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9-]", "", login or "")[:39]
    return cleaned or "anonymous"


def sanitize_fragment(text: str) -> str:
    """Strip markdown-dangerous characters (and '@', so the bot never mentions
    anyone on a visitor's behalf) from untrusted text and cap its length."""
    return re.sub(r"[\[\]<>`|@]", "", text or "").strip()[:60]


# --- salt / mine derivation -------------------------------------------------


def current_salt() -> str:
    return os.environ.get("FSCK_SALT") or DEFAULT_SALT


def salt_fingerprint(salt: str) -> str:
    return hashlib.sha256(salt.encode("utf-8")).hexdigest()[:8]


def is_sealed(salt: str) -> bool:
    return salt != DEFAULT_SALT


def derive_seed(salt: str, board_number: int, first_cell: str) -> int:
    digest = hmac.new(salt.encode("utf-8"), f"board:{board_number}:first:{first_cell}".encode("utf-8"), hashlib.sha256)
    return int.from_bytes(digest.digest()[:8], "big")


# --- board engine -----------------------------------------------------------


def neighbors(cell: str) -> list[str]:
    col = COLS.index(cell[0])
    row = int(cell[1]) - 1
    result: list[str] = []
    for dc in (-1, 0, 1):
        for dr in (-1, 0, 1):
            if dc == 0 and dr == 0:
                continue
            nc, nr = col + dc, row + dr
            if 0 <= nc < 9 and 0 <= nr < 9:
                result.append(f"{COLS[nc]}{nr + 1}")
    return result


def place_mines(salt: str, board_number: int, first_cell: str) -> list[str]:
    """Derive mine positions, keeping the first-scanned cell and its neighbors safe."""
    excluded = {first_cell, *neighbors(first_cell)}
    pool = [cell for cell in ALL_CELLS if cell not in excluded]
    seed = derive_seed(salt, board_number, first_cell)
    return sorted(random.Random(seed).sample(pool, MINE_COUNT))


def adjacency(cell: str, mines: set[str]) -> int:
    return sum(1 for n in neighbors(cell) if n in mines)


def flood_reveal(cell: str, mines: set[str], revealed: dict[str, int]) -> int:
    """Reveal `cell`, caching adjacency digits; zero-adjacency cells open their
    neighbors too. Returns how many cells were opened."""
    stack = [cell]
    opened = 0
    while stack:
        current = stack.pop()
        if current in revealed:
            continue
        digit = adjacency(current, mines)
        revealed[current] = digit
        opened += 1
        if digit == 0:
            stack.extend(n for n in neighbors(current) if n not in revealed)
    return opened


def new_state(board_number: int, salt: str) -> dict:
    return {
        "board_number": board_number,
        "first_cell": None,
        "revealed": {},
        "status": "active",
        "salt_fp": salt_fingerprint(salt),
        "mines_exposed": None,
        "panic_cell": None,
        "created_utc": utc_now(),
        "last_op": None,
    }


def board_mines(state: dict, salt: str) -> set[str] | None:
    """Mines for the current board, or None before the first scan."""
    if state["status"] != "active" and state.get("mines_exposed"):
        return set(state["mines_exposed"])
    if state.get("first_cell") is None:
        return None
    return set(place_mines(salt, state["board_number"], state["first_cell"]))


def can_reformat(state: dict) -> bool:
    return state["status"] in ("panicked", "cleaned")


def apply_scan(state: dict, cell: str, actor: str, salt: str) -> tuple[dict, dict]:
    """Apply one scan. Returns (new state, info dict). Auto-reformats a dead or
    salt-mismatched board first."""
    cell = cell.upper()
    auto_reformatted = False
    if state["status"] != "active":
        state = new_state(state["board_number"] + 1, salt)
        auto_reformatted = True
    elif state.get("salt_fp") != salt_fingerprint(salt):
        # The controller key changed under a live board; cached digits would no
        # longer match the derived layout, so the disk gets swapped wholesale.
        warn("salt fingerprint mismatch on an active board; auto-reformatting")
        state = new_state(state["board_number"] + 1, salt)
        auto_reformatted = True

    if state["first_cell"] is None:
        state["first_cell"] = cell

    mines = set(place_mines(salt, state["board_number"], state["first_cell"]))
    revealed: dict[str, int] = dict(state["revealed"])
    opened = 0

    if cell in revealed:
        result = "dup"
    elif cell in mines:
        state["status"] = "panicked"
        state["mines_exposed"] = sorted(mines)
        state["panic_cell"] = cell
        result = "panic"
    else:
        opened = flood_reveal(cell, mines, revealed)
        state["revealed"] = dict(sorted(revealed.items()))
        if len(revealed) >= CLEAN_TOTAL:
            state["status"] = "cleaned"
            state["mines_exposed"] = sorted(mines)
            result = "clean"
        else:
            result = "ok"

    state["last_op"] = {"login": actor, "op": f"fsck {cell}", "result": result, "cell": cell, "utc": utc_now()}
    info = {
        "result": result,
        "cell": cell,
        "opened": opened,
        "adj": revealed.get(cell) if result in ("ok", "clean") else None,
        "auto_reformatted": auto_reformatted,
    }
    return state, info


# --- persistence ------------------------------------------------------------


def empty_stats() -> dict:
    return {
        "users": {},
        "ops_log": [],
        "totals": {"scans": 0, "panics": 0, "cleans": 0, "presses": 0, "reformats": 0},
    }


def load_json(path: Path, fallback: dict) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        warn(f"could not read {path} ({error}); starting fresh")
        return fallback


def save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def load_state(salt: str) -> dict:
    return load_json(STATE_PATH, new_state(1, salt))


def load_stats() -> dict:
    return load_json(STATS_PATH, empty_stats())


def record_op(stats: dict, login: str, counters: list[str], op: str, result: str) -> None:
    user = stats["users"].setdefault(login, {"scans": 0, "panics": 0, "cleans": 0, "presses": 0})
    for counter in counters:
        user[counter] = user.get(counter, 0) + 1
        stats["totals"][counter] = stats["totals"].get(counter, 0) + 1
    stats["ops_log"].append({"login": login, "op": op, "result": result, "utc": utc_now()})
    stats["ops_log"] = stats["ops_log"][-OPS_LOG_LIMIT:]
    # Versions the status panel's file name: every recorded op gives it a new
    # URL, so GitHub's image cache can never show a panel older than the board.
    stats["seq"] = panel_seq(stats) + 1


def panel_seq(stats: dict) -> int:
    """The stats.json `seq` counter. A mangled value restarts it rather than
    failing the op: the counter only exists to bust an image cache."""
    try:
        return max(int(stats.get("seq", 0)), 0)
    except (TypeError, ValueError):
        return 0


def load_oneliners() -> list[str]:
    try:
        raw = ONELINERS_PATH.read_text(encoding="utf-8")
    except OSError as error:
        warn(f"could not read {ONELINERS_PATH} ({error})")
        return []
    return [line.strip() for line in raw.splitlines() if line.strip()]


def pick_oneliner(issue_number: int, current: str, lines: list[str]) -> str | None:
    pool = [line for line in lines if line != current]
    if not pool:
        return None
    return random.Random(issue_number).choice(pool)



# --- petitions (issue links) -----------------------------------------------------


def issue_url(title: str, body: str = "") -> str:
    url = f"{REPO_URL}/issues/new?title={quote_plus(title)}"
    if body:
        url += f"&body={quote_plus(body)}"
    return url


def scan_url(cell: str) -> str:
    return issue_url(SCAN_TITLE.format(cell=cell), SCAN_BODY.format(cell=cell))


def relay_url() -> str:
    return issue_url(RELAY_TITLE, RELAY_BODY)


def gong_url() -> str:
    return issue_url(GONG_TITLE, GONG_BODY)


# --- the view: everything the panel shows, as plain sanitized facts -------------------


def short_date(stamp: object) -> str:
    """MM-DD from an ISO stamp, or ??-?? when the stamp is unreadable."""
    match = re.match(r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])T", str(stamp or ""))
    return f"{match.group(1)}-{match.group(2)}" if match else "??-??"


def clip(text: str, width: int) -> str:
    """Truncate like top(1): the last visible character becomes '+'."""
    return text if len(text) <= width else text[: max(width - 1, 0)] + "+"


def board_sealed(state: dict, salt: str) -> bool:
    """Whether THIS board's trap map is sealed. The board records the
    fingerprint of the salt it was born under, so a local render without the
    secret still tells the truth about the live board."""
    fp = state.get("salt_fp")
    if not fp:
        return is_sealed(salt)
    return fp != salt_fingerprint(DEFAULT_SALT)


def as_count(value: object) -> int:
    """A counter from stats.json; a hand-edited non-number reads as 0, never a crash."""
    try:
        return max(int(value), 0)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def stats_part(stats: dict, key: str, kind: type) -> dict | list:
    value = stats.get(key)
    return value if isinstance(value, kind) else kind()


def top_users(stats: dict, key: str) -> list[tuple[str, int]]:
    ranked = [
        (sanitize_login(login), as_count(counts.get(key)))
        for login, counts in stats_part(stats, "users", dict).items()
        if isinstance(counts, dict) and as_count(counts.get(key)) > 0
    ]
    ranked.sort(key=lambda item: (-item[1], item[0]))
    return ranked[:HALL_ROWS]


def display_op(op: object) -> str:
    """The stored op name in plain words: 'fsck C4' -> 'open C4',
    'reformat' -> 'reset', 'button' -> 'gong'. A hand edit is sanitized and
    clipped, so it can never push the result column off the panel."""
    text = str(op or "")
    match = re.fullmatch(r"fsck ([A-Ia-i][1-9])", text)
    if match:
        return f"open {match.group(1).upper()}"
    if text == "reformat":
        return "reset"
    if text == "button":
        return "gong"
    return clip(sanitize_fragment(text) or "?", OP_COLS)


def display_result(result: object) -> str:
    """A known result key as-is (art_formation.result_label names it), anything
    else sanitized and clipped to the label column."""
    text = str(result or "")
    return text if text in RESULTS else clip(sanitize_fragment(text) or "?", RESULT_COLS)


def fsck_view(state: dict, stats: dict, salt: str) -> dict:
    """Everything the panel shows, sanitized, as plain facts (the contract with
    art_formation.panel_svg / panel_phone_svg / panel_alt)."""
    status = state.get("status", "active")
    if status not in ("active", "panicked", "cleaned"):
        status = "active"
    board = int(state.get("board_number") or 1)
    done = min(len(state.get("revealed") or {}), CLEAN_TOTAL)
    last = state.get("last_op")
    last = last if isinstance(last, dict) else {}
    panic_cell = str(state.get("panic_cell") or "??")
    if not re.fullmatch(r"[A-I][1-9]", panic_cell):
        panic_cell = "??"
    totals = stats_part(stats, "totals", dict)
    log = [entry for entry in stats_part(stats, "ops_log", list) if isinstance(entry, dict)]
    ops = [{
        "date": short_date(entry.get("utc")),
        "login": sanitize_login(str(entry.get("login", ""))),
        "op": display_op(entry.get("op")),
        "result": display_result(entry.get("result")),
    } for entry in list(reversed(log))[:OPS_SHOWN]]
    return {
        "status": status,
        "board": board,
        "created": short_date(state.get("created_utc")),
        "last": short_date(last.get("utc")),
        "done": done,
        "total": CLEAN_TOTAL,
        "pct": done * 100 // CLEAN_TOTAL,
        "panic_cell": panic_cell,
        "sealed": board_sealed(state, salt),
        "traps": MINE_COUNT,
        "disciples": len(stats_part(stats, "users", dict)),
        "steps": as_count(totals.get("scans")),
        "backlashes": as_count(totals.get("panics")),
        "breaks": as_count(totals.get("cleans")),
        "ops": ops,
        "fame": top_users(stats, "cleans"),
        "shame": top_users(stats, "panics"),
        "seq": panel_seq(stats),
    }


# --- status panels (drawn by art_formation, versioned by seq) ----------------------


PANEL_FILE_RE = re.compile(r"^panel(?:-(\d+))?(?:-light|-phone)?\.svg$")


def panel_paths(seq: int) -> dict[str, str]:
    """The three panel files for one board version (dark, light, phone)."""
    return {
        "dark": f"{af.DIR}/panel-{seq}.svg",
        "light": f"{af.DIR}/panel-{seq}-light.svg",
        "phone": f"{af.DIR}/panel-{seq}-phone.svg",
    }


def render_panels(state: dict, stats: dict, salt: str) -> dict[str, str]:
    view = fsck_view(state, stats, salt)
    paths = panel_paths(view["seq"])
    return {
        paths["dark"]: af.panel_svg(view, "dark"),
        paths["light"]: af.panel_svg(view, "light"),
        paths["phone"]: af.panel_phone_svg(view),
    }


def prune_panels(seq: int, root: Path = Path(".")) -> None:
    """Delete panel files older than the previous version. The previous set stays,
    so a page rendered just before this commit never shows a broken image."""
    for path in (root / af.DIR).glob("panel*.svg"):
        match = PANEL_FILE_RE.match(path.name)
        if match and (match.group(1) is None or int(match.group(1)) < seq - 1):
            try:
                path.unlink()
            except OSError as error:
                warn(f"could not prune {path} ({error})")


# --- README block -----------------------------------------------------------------
#
# The board is rows of inline images, 268px wide on purpose: a row wider than
# the column wraps and shreds the grid. GitHub's README column is 279px on a
# 360px Android, 309px on a 390px iPhone, and 311px beside the 500px panel
# (+20px float padding) on a 1280px desktop. 268 clears them all.


def tile_pic(name: str, width: int, height: int, alt: str, title: str = "") -> str:
    """A tile in a bare <picture>: light twin via <source>, no auto-link to the raw file."""
    extra = f' title="{html.escape(title)}"' if title else ""
    dark = f"{af.TILE_DIR}/dark/{name}.svg"
    return (f'<picture><source media="(max-width: 600px)" srcset="{dark}">'
            f'<source media="(prefers-color-scheme: light)" srcset="{af.TILE_DIR}/light/{name}.svg">'
            f'<img src="{dark}" width="{width}" height="{height}" align="top" '
            f'alt="{alt}"{extra}></picture>')


def digit_pic(cell: str, digit: object) -> str:
    n = max(0, min(8, int(digit)))
    return tile_pic(f"c{n}", af.TILE, af.TILE, f"{cell}: {n}")


def render_cell(state: dict, cell: str, mines: set[str] | None) -> str:
    status = state["status"]
    revealed = state["revealed"]
    if status == "active":
        if cell in revealed:
            return digit_pic(cell, revealed[cell])
        url = html.escape(scan_url(cell))
        return f'<a href="{url}">{tile_pic("hidden", af.TILE, af.TILE, f"open {cell}")}</a>'
    # A finished game (lost or cleared): everything is face-up, nothing is clickable.
    mines = mines or set()
    if cell in mines:
        if status == "panicked" and cell == state.get("panic_cell"):
            return tile_pic("panic", af.TILE, af.TILE, f"{cell}: the mine that was hit")
        return tile_pic("mine", af.TILE, af.TILE, f"{cell}: mine")
    return digit_pic(cell, revealed[cell] if cell in revealed else adjacency(cell, mines))


def render_board(state: dict, salt: str) -> str:
    mines = board_mines(state, salt) if state["status"] != "active" else None
    rail = {"panicked": "cols-panic", "cleaned": "cols-clean"}.get(state["status"], "cols")
    rows = [tile_pic(rail, af.BOARD_W, af.RAIL_TOP, "")]
    for row in ROWS:
        cells = "".join(render_cell(state, f"{col}{row}", mines) for col in COLS)
        rows.append(tile_pic(f"r{row}", af.RAIL_L, af.TILE, "") + cells + tile_pic("edge", af.RAIL_R, af.TILE, ""))
    rows.append(tile_pic("base", af.BOARD_W, af.RAIL_BOTTOM, ""))
    return "<br>\n".join(rows)


def panel_pic(view: dict) -> str:
    paths = panel_paths(view["seq"])
    return (f'<picture><source media="(max-width: 600px)" srcset="{paths["phone"]}">'
            f'<source media="(prefers-color-scheme: light)" srcset="{paths["light"]}">'
            f'<img align="right" src="{paths["dark"]}" width="{af.PANEL_W}" '
            f'alt="{html.escape(af.panel_alt(view))}"></picture>')


def key_link(url: str, name: str, width: int, alt: str) -> str:
    return (f'<a href="{html.escape(url)}"><picture>'
            f'<source media="(max-width: 600px)" srcset="{af.DIR}/{name}.svg">'
            f'<source media="(prefers-color-scheme: light)" srcset="{af.DIR}/{name}-light.svg">'
            f'<img src="{af.DIR}/{name}.svg" width="{width}" height="{af.GONG_H}" align="top" alt="{alt}">'
            f'</picture></a>')


def render_fsck_block(state: dict, stats: dict, salt: str) -> str:
    """Panel (floated right) + board in one paragraph, so their tops align; then
    the keys: the gong always, the new-board key only after a game ends.
    Pure: returns markup, touches nothing."""
    view = fsck_view(state, stats, salt)
    keys = [key_link(gong_url(), "gong", af.GONG_W, "勿敲 DO NOT STRIKE")]
    if can_reformat(state):
        keys.append(key_link(relay_url(), "relay", af.RELAY_W, "重布 (re-lay): start a new board"))
    return ("<p>\n" + panel_pic(view) + render_board(state, salt) + '<br clear="all">\n</p>\n\n'
            + "<p>\n" + "\n".join(keys) + "\n</p>")


def safe_replace(readme: str, start: str, end: str, content: str) -> bool:
    """replace_block, but a missing README or missing markers is a warning, not
    a crash. Returns whether the block is now in place."""
    try:
        replace_block(readme, start, end, content)
    except (OSError, ValueError) as error:
        warn(f"skipped block update ({start}): {error}")
        return False
    return True


def render_readme(readme: str, state: dict, stats: dict, salt: str, root: Path = Path(".")) -> bool:
    """Draw panels and block in memory; write only when all of it rendered. A
    presentation fault never costs the visitor their reply. Returns whether
    the README block was rendered."""
    if af is None or ink is None:
        warn(f"formation art unavailable ({ART_ERROR}); panel and README left as they were")
        return False
    try:
        panels = render_panels(state, stats, salt)
        block = render_fsck_block(state, stats, salt)
    except Exception:  # noqa: BLE001 - never blank the block over a drawing bug
        warn("formation render failed; panel and README left as they were\n" + traceback.format_exc())
        return False
    try:
        text = Path(readme).read_text(encoding="utf-8")
    except OSError as error:
        warn(f"skipped block update ({FSCK_START}): {error}")
        return False
    if FSCK_START not in text or FSCK_END not in text:
        # Checked before any panel is written: files nothing references would pile up.
        warn(f"skipped block update ({FSCK_START}): markers missing; no panel written")
        return False
    try:
        for path, content in panels.items():
            ink.write_svg(root / path, content)
    except (OSError, ValueError) as error:
        warn(f"could not write the status panel ({error}); README left as it was")
        return False
    if not safe_replace(readme, FSCK_START, FSCK_END, block):
        return False
    prune_panels(panel_seq(stats), root)
    return True


def write_static_assets(root: Path = Path(".")) -> int:
    """Render every tile and key in memory (art_formation.static_assets, the
    same files generate_tiles.py writes), then write them."""
    assets = af.static_assets()
    return sum(bool(ink.write_svg(root / path, content)) for path, content in assets.items())


# --- command handling -------------------------------------------------------


def parse_command(title: str) -> tuple[str, str | None] | None:
    """Return ("scan", CELL) | ("reformat", None) | ("button", None) | ("sandwich", None) | None.
    New and legacy titles map to the same verbs, so stats keep their old names."""
    title = (title or "").strip()
    if title == SANDWICH_TITLE:
        return ("sandwich", None)
    match = CMD_RE.match(title)
    if not match:
        return None
    cell = match.group("cell") or match.group("legacy_cell")
    if cell:
        return ("scan", cell.upper())
    if match.group("relay") or match.group("reformat"):
        return ("reformat", None)
    return ("button", None)


def squares(n: int) -> str:
    return f"{n} square" if n == 1 else f"{n} squares"


def scan_reply(state: dict, info: dict, actor: str) -> str:
    """Plain and short: what happened, the score, and what to do next only when
    the game is over. The board itself shows the rest."""
    board = state["board_number"]
    done = len(state["revealed"])
    result = info["result"]
    prefix = ""
    if info["auto_reformatted"]:
        prefix = f"The last game was over, so this started board #{board}.\n"

    if result == "dup":
        return prefix + f"{info['cell']} is already open on board #{board}."
    if result == "panic":
        return prefix + (
            f"{info['cell']} was a mine, so board #{board} is over at {done}/{CLEAN_TOTAL}.\n"
            f"Open an issue titled `{RELAY_TITLE}` to start a new one."
        )
    if result == "clean":
        return prefix + (
            f"That was the last safe square. {actor} cleared board #{board}!\n"
            f"Open an issue titled `{RELAY_TITLE}` to start a new one."
        )
    return prefix + (
        f"{info['cell']} is safe. It opened {squares(info['opened'])}, "
        f"and board #{board} is at {done}/{CLEAN_TOTAL}."
    )


def handle_scan(cell: str, actor: str, readme: str) -> str:
    salt = current_salt()
    state = load_state(salt)
    stats = load_stats()
    state, info = apply_scan(state, cell, actor, salt)
    counters = {"ok": ["scans"], "dup": [], "panic": ["scans", "panics"], "clean": ["scans", "cleans"]}
    record_op(stats, actor, counters[info["result"]], f"fsck {info['cell']}", info["result"])
    save_json(STATE_PATH, state)
    save_json(STATS_PATH, stats)
    render_readme(readme, state, stats, salt)
    return scan_reply(state, info, actor)


def handle_reformat(actor: str, readme: str) -> str:
    salt = current_salt()
    state = load_state(salt)
    stats = load_stats()
    if not can_reformat(state):
        done = len(state["revealed"])
        record_op(stats, actor, [], "reformat", "refused")
        save_json(STATS_PATH, stats)
        render_readme(readme, state, stats, salt)
        return (
            f"Board #{state['board_number']} is still going ({done}/{CLEAN_TOTAL}). "
            "A new board can only start once this one is won or lost."
        )
    state = new_state(state["board_number"] + 1, salt)
    record_op(stats, actor, ["reformats"], "reformat", "reformat")
    save_json(STATE_PATH, state)
    save_json(STATS_PATH, stats)
    render_readme(readme, state, stats, salt)
    return f"Started board #{state['board_number']}. It has {MINE_COUNT} mines."


def swap_oneliner(issue_number: int, readme: str) -> None:
    """Silently rotate the footer one-liner. Never surfaces in the reply.

    The line lives inside the footer <pre>, so it is written as plain,
    html-escaped text. A legacy `backticked` line is still recognised."""
    lines = load_oneliners()
    if not lines:
        return
    try:
        text = Path(readme).read_text(encoding="utf-8")
    except OSError as error:
        warn(f"could not read {readme} ({error})")
        return
    if ONELINER_START not in text or ONELINER_END not in text:
        warn("footer one-liner markers missing; skipped swap")
        return
    current = text[text.index(ONELINER_START) + len(ONELINER_START):text.index(ONELINER_END)].strip()
    current = html.unescape(current).strip("`").strip()
    choice = pick_oneliner(issue_number, current, lines)
    if choice is None:
        return
    safe_replace(readme, ONELINER_START, ONELINER_END, html.escape(choice, quote=False))


def handle_button(actor: str, issue_number: int, readme: str) -> str:
    salt = current_salt()
    stats = load_stats()
    record_op(stats, actor, ["presses"], "button", "press")
    save_json(STATS_PATH, stats)
    if issue_number % 10 == 0:
        swap_oneliner(issue_number, readme)
    render_readme(readme, load_state(salt), stats, salt)
    return GONG_REPLY


def handle_process(title: str, actor: str, issue_number: int, readme: str) -> str:
    actor = sanitize_login(actor)
    command = parse_command(title)
    if command is None:
        # Echo the art the visitor named, not the router prefix: "sect|zhen|Z9"
        # reads back as "zhen Z9", "artemis|fsck|Z9" as "fsck Z9".
        typed = re.sub(r"^\s*(?:sect|artemis)\s*\|", "", title or "", flags=re.IGNORECASE).replace("|", " ")
        shown = sanitize_fragment(typed) or "(empty)"
        return (
            f"Unknown command `{shown}`.\n"
            f"Titles that work: `{SCAN_TITLE.format(cell='A1')}` to `{SCAN_TITLE.format(cell='I9')}`, "
            f"`{RELAY_TITLE}`, `{GONG_TITLE}`"
        )
    verb, cell = command
    if verb == "sandwich":
        return SANDWICH_REPLY
    if verb == "scan":
        return handle_scan(cell, actor, readme)
    if verb == "reformat":
        return handle_reformat(actor, readme)
    return handle_button(actor, issue_number, readme)


# --- self-test --------------------------------------------------------------


def self_test() -> None:
    if af is None or ink is None:
        raise SystemExit(f"self-test needs scripts/art_formation.py and scripts/ink.py ({ART_ERROR})")
    salt = "test-salt"

    # Geometry.
    assert set(neighbors("A1")) == {"B1", "A2", "B2"}
    assert set(neighbors("I9")) == {"H9", "I8", "H8"}
    assert len(neighbors("E5")) == 8

    # The mine derivation is frozen: changing it silently re-lays the live board.
    assert DEFAULT_SALT == "artemis-believes-in-open-source" and MINE_COUNT == 10 and CLEAN_TOTAL == 71
    assert place_mines(DEFAULT_SALT, 3, "E5") == place_mines(DEFAULT_SALT, 3, "E5")
    assert derive_seed("s", 1, "A1") == int.from_bytes(
        hmac.new(b"s", b"board:1:first:A1", hashlib.sha256).digest()[:8], "big")

    # First-step safety + determinism, without persisting traps.
    state = new_state(1, salt)
    state, info = apply_scan(state, "E5", "tester", salt)
    assert info["result"] in ("ok", "clean") and not info["auto_reformatted"]
    mines = board_mines(state, salt)
    assert mines is not None and len(mines) == MINE_COUNT
    assert not ({"E5", *neighbors("E5")} & mines)
    repeat = new_state(1, salt)
    repeat, _ = apply_scan(repeat, "E5", "tester", salt)
    assert board_mines(repeat, salt) == mines
    assert place_mines("other-salt", 1, "E5") != sorted(mines), "different salts must differ"

    # The persisted state of an ACTIVE board must not disclose traps or a seed.
    serialized = json.dumps(state)
    assert "mines_exposed" in state and state["mines_exposed"] is None
    assert "seed" not in state
    assert not any(mine in state["revealed"] for mine in mines)
    assert all(cell not in serialized or cell in state["revealed"] or cell == state["first_cell"]
               for cell in mines), "no mine coordinate may appear in active-state JSON"

    # Flood fill: E5 opened its zero-adjacency region; digits are cached.
    assert info["adj"] == 0 and info["opened"] > 1
    assert all(isinstance(d, int) and 0 <= d <= 8 for d in state["revealed"].values())
    assert not (set(state["revealed"]) & mines)

    # A repeated step is a no-op on the board and does not count as a step.
    before = dict(state["revealed"])
    state, info = apply_scan(state, "e5", "tester", salt)
    assert info["result"] == "dup" and state["revealed"] == before

    # Backlash exposes the traps only after the formation falls.
    boom = new_state(2, salt)
    boom, _ = apply_scan(boom, "A1", "tester", salt)
    target = sorted(board_mines(boom, salt))[0]
    boom, info = apply_scan(boom, target, "tester", salt)
    assert info["result"] == "panic" and boom["status"] == "panicked"
    assert boom["mines_exposed"] and boom["panic_cell"] == target

    # Re-lay gate: refused mid-game, allowed when spent; stepping on a spent
    # formation re-lays it and the fresh first step is safe again.
    assert not can_reformat(state) and can_reformat(boom)
    boom, info = apply_scan(boom, "E5", "tester", salt)
    assert info["auto_reformatted"] and boom["board_number"] == 3
    assert boom["status"] == "active" and info["result"] == "ok"

    # Salt rotation mid-board re-lays instead of corrupting.
    rotated, info = apply_scan(dict(state), "A1", "tester", "rotated-salt")
    assert info["auto_reformatted"] and rotated["salt_fp"] == salt_fingerprint("rotated-salt")

    # Breaking it: read every safe node but one, then the last one.
    final = new_state(4, salt)
    final, _ = apply_scan(final, "E5", "tester", salt)
    final_mines = board_mines(final, salt)
    clean = [cell for cell in ALL_CELLS if cell not in final_mines]
    target = next(cell for cell in clean if cell not in final["revealed"])
    final["revealed"] = {cell: adjacency(cell, final_mines) for cell in clean if cell != target}
    final, info = apply_scan(final, target, "tester", salt)
    assert info["result"] == "clean" and final["status"] == "cleaned"
    assert len(final["revealed"]) == CLEAN_TOTAL and final["mines_exposed"]

    # Router: the sect's titles and the previous life's, side by side.
    assert parse_command("sect|zhen|c4") == ("scan", "C4")
    assert parse_command("sect|zhen|I9") == ("scan", "I9")
    assert parse_command("sect|zhen|relay") == ("reformat", None)
    assert parse_command("sect|gong") == ("button", None)
    assert parse_command("artemis|fsck|c4") == ("scan", "C4")
    assert parse_command("artemis|fsck|I9") == ("scan", "I9")
    assert parse_command("artemis|fsck|reformat") == ("reformat", None)
    assert parse_command("artemis|button") == ("button", None)
    assert parse_command(SANDWICH_TITLE) == ("sandwich", None)
    assert parse_command(f"  {SANDWICH_TITLE} ") == ("sandwich", None)
    for bad in ("sect|zhen|J4", "sect|zhen|A0", "sect|zhen|reformat", "sect|fsck|C4", "sect|button",
                "artemis|zhen|C4", "artemis|gong", "artemis|fsck|relay", "artemis|fsck|J4", "artemis|fsck|A0",
                "artemis|sudo", "ARTEMIS|BUTTON", "SECT|GONG", "Sect|zhen|C4", "sect|gong|", "sect|zhen|C44",
                "sect|zhen|C4\nsect|gong", ""):
        assert parse_command(bad) is None, bad
    unknown = handle_process("sect|zhen|Z9", "tester", 1, "no-readme-needed.md")
    assert unknown.startswith("Unknown command `zhen Z9`."), unknown
    legacy_unknown = handle_process("artemis|fsck|Z9", "tester", 1, "no-readme-needed.md")
    assert legacy_unknown.startswith("Unknown command `fsck Z9`."), legacy_unknown
    assert "`sect|zhen|relay`" in unknown and "`sect|gong`" in unknown and "artemis" not in unknown
    mention = handle_process("sect| @someone look", "tester", 1, "no-readme-needed.md")
    assert "@" not in mention.splitlines()[0], "the bot never mentions anyone on a visitor's behalf"
    assert handle_process(SANDWICH_TITLE, "tester", 1, "no-readme-needed.md") == SANDWICH_REPLY
    for reply in (unknown, SANDWICH_REPLY, GONG_REPLY, INTERNAL_FAULT):
        assert not re.search(r"\bcults?\b", reply, re.IGNORECASE)

    # Replies: plain, short, and the new-board title they name is a real one.
    ok_reply = scan_reply(state, {"result": "ok", "cell": "E5", "opened": 3, "adj": 1, "auto_reformatted": True},
                          "tester")
    assert ok_reply.startswith("The last game was over, so this started board #")
    assert "E5 is safe. It opened 3 squares, and board #" in ok_reply
    one = scan_reply(state, {"result": "ok", "cell": "E5", "opened": 1, "adj": 1, "auto_reformatted": False}, "t")
    assert "opened 1 square," in one
    replies = [ok_reply, one]
    for result in ("panic", "clean", "dup"):
        reply = scan_reply(state, {"result": result, "cell": "E5", "opened": 0, "adj": None,
                                   "auto_reformatted": False}, "tester")
        replies.append(reply)
        if result != "dup":
            assert f"`{RELAY_TITLE}`" in reply and parse_command(RELAY_TITLE) == ("reformat", None)
    assert "tester cleared board #" in replies[3]
    # No sect story, dashes or semicolons in what the bot says to a visitor.
    for reply in replies + [unknown, SANDWICH_REPLY, GONG_REPLY, INTERNAL_FAULT, SCAN_BODY, RELAY_BODY, GONG_BODY]:
        assert not re.search(r"\b(?:disciples?|elders?|formations?|petitions?|nodes?|traps?)\b|[;—]",
                             reply, re.IGNORECASE), reply

    # Sanitizers.
    assert sanitize_login("evil/../user<img>") == "eviluserimg"
    assert sanitize_login("") == "anonymous"
    assert sanitize_fragment("a[b]c<d>`e`|f") == "abcdef"

    # Display names: stats keep the stored op names; the view uses plain words.
    assert display_op("fsck C4") == "open C4" and display_op("reformat") == "reset" and display_op("button") == "gong"
    assert len(display_op("x" * 80)) == OP_COLS and display_result("panic") == "panic"
    assert all(len(af.result_label(result)) <= RESULT_COLS for result in RESULTS)
    assert af.result_label("panic") == "MINE"

    # Gong pool swap: deterministic per issue number, never repeats the current line.
    lines = load_oneliners()
    assert len(lines) >= 12, "oneliners.txt should ship with a full pool"
    assert all(display_cols(line) <= 72 for line in lines), "one-liners live in the footer <pre>: 72 columns max"
    assert all(line.isascii() for line in lines), "the pool is plain ASCII: no emoji, no glyph fallbacks"
    assert not any(re.search(r"\bcults?\b", line, re.IGNORECASE) for line in lines)
    pick = pick_oneliner(20, lines[0], lines)
    assert pick is not None and pick != lines[0]
    assert pick == pick_oneliner(20, lines[0], lines)
    assert pick_oneliner(20, "not in pool", lines) in lines

    # Rendering: the board is one device; only unread nodes on a live formation are links.
    import tempfile
    import xml.etree.ElementTree as ET

    mangled = empty_stats()
    mangled["seq"] = "not-a-number"
    record_op(mangled, "tester", ["scans"], "fsck E5", "ok")
    assert mangled["seq"] == 1, "a mangled cache-buster restarts; it never fails the op"

    stats = empty_stats()
    record_op(stats, "tester", ["scans"], "fsck E5", "ok")
    assert stats["seq"] == 1
    record_op(stats, "tester", ["presses"], "button", "press")
    assert stats["seq"] == 2, "every recorded op must bump the panel cache-buster"
    view = fsck_view(state, stats, salt)
    assert [op["op"] for op in view["ops"]] == ["gong", "open E5"], "newest first, in plain words"
    assert view["total"] == CLEAN_TOTAL and view["traps"] == MINE_COUNT and view["disciples"] == 1

    hidden = f'<img src="{af.TILE_DIR}/dark/hidden.svg"'
    active_block = render_fsck_block(state, stats, salt)
    unread = [cell for cell in ALL_CELLS if cell not in state["revealed"]]
    links = re.findall(r'<a href="([^"]+)">(.*?)</a>', active_block)
    step_links = [(url, inner) for url, inner in links if re.search(r"sect%7Czhen%7C[A-I][1-9]&", url)]
    assert len(step_links) == len(unread) > 0
    assert all("tiles/dark/hidden.svg" in inner and "tiles/light/hidden.svg" in inner for _, inner in step_links)
    assert active_block.count(hidden) == len(unread), "hidden nodes appear only as links"
    assert all(f"sect%7Czhen%7C{cell}&amp;" in active_block for cell in unread)
    assert not any(f"sect%7Czhen%7C{cell}&amp;" in active_block for cell in state["revealed"])
    assert all(f'alt="open {cell}"' in active_block for cell in unread)
    assert ' title="' not in active_block, "no tooltips: the alt says it"
    assert all(f'alt="{cell}: {digit}"' in active_block for cell, digit in state["revealed"].items())
    assert quote_plus(SCAN_BODY.format(cell=unread[0])) in html.unescape(active_block)
    assert active_block.count("<br>") == len(ROWS) + 1 and 'br clear="all"' in active_block
    assert "sect%7Cgong&amp;" in active_block and f"{af.DIR}/gong.svg" in active_block
    assert 'alt="勿敲 DO NOT STRIKE"' in active_block
    assert "artemis%7C" not in active_block, "new links use the sect's titles"
    assert f"{af.DIR}/relay.svg" not in active_block, "the re-lay key only appears on a spent formation"
    assert all(path in active_block for path in panel_paths(2).values()), "panel file names carry seq"
    assert "?n=" not in active_block, "GitHub's /raw/ redirect drops query strings; version the path"
    assert active_block.count('media="(max-width: 600px)"') == active_block.count("<picture>"), \
        "phones always get the dark drawings"
    assert "[!" not in active_block and "<sub>" not in active_block and "|:-" not in active_block

    panic_state = new_state(5, salt)
    panic_state, _ = apply_scan(panic_state, "A1", "tester", salt)
    panic_state, _ = apply_scan(panic_state, sorted(board_mines(panic_state, salt))[0], "tester", salt)
    clean_block = render_fsck_block(final, stats, salt)
    panic_block = render_fsck_block(panic_state, stats, salt)
    assert panic_block.count(f'<img src="{af.TILE_DIR}/dark/panic.svg"') == 1
    assert f'alt="{panic_state["panic_cell"]}: the mine that was hit"' in panic_block
    assert "tiles/dark/cols-panic.svg" in panic_block and "tiles/dark/cols.svg" in active_block
    assert "tiles/dark/cols-clean.svg" in clean_block
    assert panic_block.count(f'<img src="{af.TILE_DIR}/dark/mine.svg"') == MINE_COUNT - 1
    assert clean_block.count(f'<img src="{af.TILE_DIR}/dark/mine.svg"') == MINE_COUNT
    assert "tiles/dark/panic.svg" not in clean_block and ': mine"' in clean_block
    for dead in (panic_block, clean_block):
        assert "tiles/dark/hidden.svg" not in dead
        assert not re.search(r"(?:sect%7Czhen|artemis%7Cfsck)%7C[A-I][1-9]", dead), "spent formations have no step links"
        assert "sect%7Czhen%7Crelay&amp;" in dead and f"{af.DIR}/relay.svg" in dead
        assert dead.count("<a href=") == 2, "only the gong and the re-lay key are clickable"
        assert "click a node" not in dead
        assert "[!" not in dead and "<sub>" not in dead

    # Status panels: parseable, state-true, sized to sit beside the board.
    def width_of(path: str) -> float:
        return PHONE_W if path.endswith("-phone.svg") else af.PANEL_W

    for board_state in (state, panic_state, final):
        panels = render_panels(board_state, stats, salt)
        paths = panel_paths(panel_seq(stats))
        assert set(panels) == set(paths.values())
        for path, content in panels.items():
            ET.fromstring(content)
            assert af.fits(content, width_of(path)), f"text overflows {path}"
            if "@keyframes" in content:
                assert "prefers-reduced-motion" in content, f"{path} animates without the reduced-motion rule"
        assert "@keyframes" not in panels[paths["light"]], "light panels never animate"
        assert f'height="{af.PANEL_H}"' in panels[paths["dark"]]
        if board_state["status"] != "active":
            assert all("click a node" not in content for content in panels.values())

    def dark_panel(board_state: dict, board_stats: dict, board_salt: str) -> str:
        return render_panels(board_state, board_stats, board_salt)[panel_paths(panel_seq(board_stats))["dark"]]

    assert "In progress" in dark_panel(state, stats, salt)
    assert "@keyframes" not in dark_panel(state, stats, salt), "stills only"
    assert "Game over" in dark_panel(panic_state, stats, salt)
    assert "Cleared" in dark_panel(final, stats, salt)
    for words in ("formation holds", "disciple", "petition", "killing trap", "node", "BACKLASH", "(no limit)"):
        assert words not in dark_panel(state, stats, salt) + dark_panel(panic_state, stats, salt), words
    assert af.PANEL_H <= af.BOARD_H, "the panel is never taller than the board beside it"
    assert af.BOARD_W <= 279 and af.BOARD_W + 20 + af.PANEL_W <= 831, \
        "board must fit a 360px phone and a 1280px desktop"

    # Worst case still fits: four long logins, full halls, unsealed map.
    crowded = empty_stats()
    for i in range(OPS_LOG_LIMIT):
        who = f"a-very-long-github-login-number-{i:02d}xx"
        record_op(crowded, who, ["scans", "panics", "cleans"], "reformat", "refused")
    open_board = new_state(9, DEFAULT_SALT)
    open_board, _ = apply_scan(open_board, "E5", "tester", DEFAULT_SALT)
    for path, content in render_panels(open_board, crowded, DEFAULT_SALT).items():
        assert af.fits(content, width_of(path)), f"crowded text overflows {path}"

    # A hand-edited log (long op, unknown result, broken stamp) is clipped, never overflows.
    hostile = empty_stats()
    evil = "<script>&amp;\"'`|[x](y)" + "W" * 200
    hostile["ops_log"] = [{"login": evil, "op": evil, "result": evil, "utc": "2026-13-45T99:99:99Z"}] * 4
    hostile["users"] = {evil: {"scans": 1, "panics": 999999, "cleans": 12345}}
    hostile_view = fsck_view(open_board, hostile, DEFAULT_SALT)
    assert all(op["date"] == "??-??" and len(op["op"]) <= OP_COLS and len(op["result"]) <= RESULT_COLS
               for op in hostile_view["ops"])
    for path, content in render_panels(open_board, hostile, DEFAULT_SALT).items():
        ET.fromstring(content)
        assert af.fits(content, width_of(path)), f"hostile text overflows {path}"
        assert "<script" not in content
    hostile_block = render_fsck_block(open_board, hostile, DEFAULT_SALT)
    assert "<script" not in hostile_block and "&lt;script" not in hostile_block

    # Halls give credit: top three, most first, ties by name.
    crew = empty_stats()
    crew["users"] = {login: {"cleans": n, "panics": n} for login, n in
                     (("night-shift", 1), ("disk-whisperer", 2), ("IdkwhatImD0ing", 1), ("zed", 1))}
    assert top_users(crew, "cleans") == [("disk-whisperer", 2), ("IdkwhatImD0ing", 1), ("night-shift", 1)]

    # The unsealed wink shows only on a formation laid without the secret salt.
    wink = "honor system"
    assert wink in dark_panel(open_board, stats, DEFAULT_SALT)
    assert wink not in dark_panel(state, stats, salt)
    assert wink not in render_fsck_block(state, stats, salt)
    assert wink not in render_fsck_block(state, stats, DEFAULT_SALT), "a local render tells the live board's truth"

    # Static assets: every tile and key, both modes, valid XML, all still.
    assets = af.static_assets()
    assert len(assets) == 2 * len(af.TILE_NAMES) + 4
    used = {"hidden", "panic", "mine", "cols", "cols-panic", "cols-clean", "edge", "base",
            *(f"c{n}" for n in range(9)), *(f"r{row}" for row in ROWS)}
    assert used <= set(af.TILE_NAMES), sorted(used - set(af.TILE_NAMES))
    for path, content in assets.items():
        ET.fromstring(content)
        assert "@keyframes" not in content and "<animate" not in content, f"{path} animates (stills only)"
    for key in ("gong", "gong-light", "relay", "relay-light"):
        assert f"{af.DIR}/{key}.svg" in assets, key

    # End to end on a scratch README: panels written, block replaced, never blanked.
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        readme = root / "README.md"
        readme.write_text(
            f"# lab\n{FSCK_START}\nstale-block\n{FSCK_END}\n<pre>{ONELINER_START}\n`{lines[0]}`\n{ONELINER_END}</pre>\n",
            encoding="utf-8",
        )
        (root / af.DIR).mkdir(parents=True, exist_ok=True)
        for legacy in ("panel.svg", "panel-light.svg", "panel-0.svg", "panel-0-phone.svg"):
            (root / af.DIR / legacy).write_text("<svg/>", encoding="utf-8")
        assert render_readme(str(readme), state, stats, salt, root=root)
        for path in panel_paths(2).values():
            ET.parse(root / path)
        text = readme.read_text(encoding="utf-8")
        assert "stale-block" not in text and panel_paths(2)["dark"] in text and "tiles/dark/hidden.svg" in text
        record_op(stats, "tester", ["scans"], "fsck E5", "dup")
        render_readme(str(readme), state, stats, salt, root=root)
        assert panel_paths(3)["dark"] in readme.read_text(encoding="utf-8"), "a new op must change the panel URL"
        left = sorted(path.name for path in (root / af.DIR).glob("panel*.svg"))
        kept = sorted(Path(path).name for path in (*panel_paths(2).values(), *panel_paths(3).values()))
        assert left == kept, f"only the current and previous panel sets survive, got {left}"

        # BOOT_ONELINER: plain html-escaped text for the footer <pre>, never the same line twice.
        swap_oneliner(20, str(readme))
        text = readme.read_text(encoding="utf-8")
        shown = text[text.index(ONELINER_START) + len(ONELINER_START):text.index(ONELINER_END)].strip()
        assert "`" not in shown and html.unescape(shown) in lines and html.unescape(shown) != lines[0]
        assert shown == html.escape(html.unescape(shown), quote=False)
        swap_oneliner(30, str(readme))
        again = readme.read_text(encoding="utf-8")
        assert again[again.index(ONELINER_START):].split("\n")[1] != shown

        # Missing markers are a warning, not a crash, and nothing is blanked.
        bare = root / "BARE.md"
        bare.write_text("no markers here\n", encoding="utf-8")
        before = sorted(path.name for path in (root / af.DIR).glob("panel*.svg"))
        record_op(stats, "tester", ["scans"], "fsck E5", "dup")
        assert not render_readme(str(bare), state, stats, salt, root=root)
        assert sorted(path.name for path in (root / af.DIR).glob("panel*.svg")) == before, \
            "a README without markers gets no panel files"
        swap_oneliner(40, str(bare))
        assert bare.read_text(encoding="utf-8") == "no markers here\n"
        assert not render_readme(str(root / "MISSING.md"), state, stats, salt, root=root)

    # Hand-edited stats never take the renderer down.
    junk = {"users": {"x": {"panics": "n/a"}, "y": "str"}, "totals": {"scans": "?"}, "ops_log": ["bad", 3]}
    view = fsck_view(state, junk, salt)
    assert view["steps"] == 0 and view["ops"] == [] and view["shame"] == []
    junk_state = dict(state, last_op="not-a-dict", created_utc=None)
    assert fsck_view(junk_state, junk, salt)["last"] == "??-??"
    render_panels(state, junk, salt)

    print("self-test: all assertions passed")


# --- CLI --------------------------------------------------------------------


def cmd_init(args: argparse.Namespace) -> None:
    salt = current_salt()
    state = new_state(1, salt)
    stats = empty_stats()
    save_json(STATE_PATH, state)
    save_json(STATS_PATH, stats)
    render_readme(args.readme, state, stats, salt)
    sealed = "sealed" if is_sealed(salt) else "UNSEALED (set FSCK_SALT to seal the trap map)"
    print(f"laid formation #1 ({sealed}) in {STATE_PATH.parent}")


def cmd_process(args: argparse.Namespace) -> None:
    try:
        reply = handle_process(args.title, args.actor, args.issue, args.readme)
    except Exception:  # The reply is the contract; a bad day never breaks the bot.
        warn(traceback.format_exc())
        reply = INTERNAL_FAULT
    if hasattr(sys.stdout, "reconfigure"):  # logins and titles can carry non-ASCII
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(reply)


def cmd_render(args: argparse.Namespace) -> None:
    salt = current_salt()
    if render_readme(args.readme, load_state(salt), load_stats(), salt):
        print("rendered the formation block", file=sys.stderr)


def cmd_tiles(_args: argparse.Namespace) -> None:
    if af is None or ink is None:
        warn(f"tiles not written: formation art unavailable ({ART_ERROR})")
        return
    try:
        changed = write_static_assets()
    except (OSError, ValueError) as error:
        warn(f"tiles not written: {error}")
        return
    print(f"formation tiles: {changed} file(s) changed in {af.DIR}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="Minesweeper by issues, the gong and the sandwich reply")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="fresh formation + empty stats")
    p_init.add_argument("--readme", default="README.md")
    p_init.set_defaults(func=cmd_init)

    p_process = sub.add_parser("process", help="route one issue title; stdout = the reply")
    p_process.add_argument("--title", required=True)
    p_process.add_argument("--actor", required=True)
    p_process.add_argument("--issue", type=int, required=True)
    p_process.add_argument("--readme", default="README.md")
    p_process.set_defaults(func=cmd_process)

    p_render = sub.add_parser("render", help="re-render the README block + status panels from current state")
    p_render.add_argument("--readme", default="README.md")
    p_render.set_defaults(func=cmd_render)

    p_tiles = sub.add_parser("tiles", help="write the static tiles and keys (same as generate_tiles.py)")
    p_tiles.set_defaults(func=cmd_tiles)

    p_test = sub.add_parser("self-test", help="deterministic assertion suite")
    p_test.set_defaults(func=lambda _args: self_test())

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
