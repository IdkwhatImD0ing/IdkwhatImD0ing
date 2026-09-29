"""ART3M1S issue-ops: the fsck minigame engine, command router, and README renderer.

Usage (always from the repo root):

    python scripts/artemis_ops.py init
    python scripts/artemis_ops.py process --title STR --actor LOGIN --issue INT
    python scripts/artemis_ops.py render
    python scripts/artemis_ops.py tiles
    python scripts/artemis_ops.py self-test

Contract for `process`: stdout is EXACTLY the in-character issue-comment reply
(nothing else), and the exit code is always 0. Diagnostics go to stderr.

Presentation: the board is one drawn device (a slab of raised keys) assembled
from static tiles in assets/fsck/tiles/{dark,light}/ (written by `tiles`), with
a status panel floated beside it. The panel SVGs (assets/fsck/panel-<seq>*.svg)
are redrawn on every render; their file names carry the stats.json `seq` counter,
because GitHub's /raw/ redirect drops query strings (a ?n= cache-buster would not
survive) and the raw CDN caches each path for five minutes.

Anti-cheat: mine positions are never persisted for an active board. They are
recomputed on demand from HMAC(FSCK_SALT, board_number:first_cell); the state
file only stores revealed cells with their adjacency digits (public info a
player has already earned). Without the FSCK_SALT repo secret the engine falls
back to a public salt and the board admits, in fiction, that it is derivable.
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

import phosphor as ph
from readme_blocks import replace_block


USERNAME = "IdkwhatImD0ing"
REPO_URL = f"https://github.com/{USERNAME}/{USERNAME}"
STATE_PATH = Path("data/fsck/state.json")
STATS_PATH = Path("data/fsck/stats.json")
ONELINERS_PATH = Path("scripts/data/oneliners.txt")
FSCK_DIR = "assets/fsck"
TILE_DIR = f"{FSCK_DIR}/tiles"

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

CMD_RE = re.compile(r"^artemis\|(?:fsck\|(?:(?P<cell>[A-Ia-i][1-9])|(?P<reformat>reformat))|(?P<button>button))$")
SANDWICH_TITLE = "sudo make me a sandwich"
SANDWICH_REPLY = "bill is not in the sudoers file. This incident will be reported."
BUTTON_REPLY = "nothing happened."

OPS_LOG_LIMIT = 12
SMART_ROWS = 4
HALL_ROWS = 3

RESULT_LABELS = {
    "ok": "sector clean",
    "dup": "re-scan (noop)",
    "panic": "KERNEL PANIC",
    "clean": "BOARD CLEANED",
    "reformat": "new disk online",
    "refused": "reformat refused",
    "press": "nothing happened",
}

SCAN_BODY = (
    "Submit this issue as-is to scan sector {cell} of /dev/sda1.\n"
    "The single-threaded fsck daemon will ack with an eyes reaction and redraw the board in about a minute."
)
REFORMAT_BODY = (
    "Submit this issue as-is to reformat /dev/sda1 and bring up a fresh board.\n"
    "Only honored when the current board is panicked or cleaned; the daemon refuses mid-shift."
)


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


# --- presentation: the fsck device --------------------------------------------
#
# One sector is a 28px tile: a 24px key (or pressed-in cell) inside a 2px
# gutter of slab, so neighbouring tiles leave 4px gaps and the grid reads as a
# single slab of keys. Bezel tiles close the slab into one device: a column
# rail on top (pane title + letters), row labels on the left, an edge on the
# right and a base below.
#
# The board is 268px wide on purpose: rows are runs of inline images, and a
# row wider than the column wraps and shreds the grid. GitHub's README column
# is 279px on a 360px Android, 309px on a 390px iPhone, and 311px beside the
# 500px panel (+20px float padding) on a 1280px desktop. 268 clears them all.

TILE = 28
KEY = TILE - 4
RAIL_L = 10
RAIL_R = 6
RAIL_TOP = 34
RAIL_BOTTOM = 6
BOARD_W = RAIL_L + len(COLS) * TILE + RAIL_R  # 268
BOARD_H = RAIL_TOP + len(ROWS) * TILE + RAIL_BOTTOM  # 292
PANEL_W = 500
PHONE_GAP = 14
PANEL_H = BOARD_H  # never taller than the board: tops and bottoms line up, no clearing gap
BUTTON_W, BUTTON_H = 220, 48
MKFS_W = 256
MODES = (("dark", ""), ("light", "-light"))
# The bezel title is the one part of the device that shows state at a glance.
BOARD_TITLES = {"cols": "81 sectors", "cols-panic": "kernel panic", "cols-clean": "clean"}
PANEL_TITLE = ("1 fsck.art3m1s 5.8", "/dev/sda1")
BUTTON_BODY = "Submit this issue as-is. You were told."

# A corrupted sector, drawn as a 7x7 burst (the same mark, lit or dormant).
BURST = ("...#...", ".#.#.#.", "..###..", "#######", "..###..", ".#.#.#.", "...#...")

RESULT_CLASSES = {"ok": "fg", "dup": "mu", "panic": "red", "clean": "acc", "reformat": "fg",
                  "refused": "warn", "press": "mu"}
OP_COLS = 10  # S.M.A.R.T. op column: "fsck C4", "reformat", "button"
RESULT_COLS = max(len(label) for label in RESULT_LABELS.values())  # 16

TILE_GLOW = (
    f'<filter id="tglow" filterUnits="userSpaceOnUse" x="0" y="0" width="{TILE}" height="{TILE}">'
    '<feGaussianBlur stdDeviation="1.2" result="b"/>'
    '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
)


def issue_url(title: str, body: str = "") -> str:
    url = f"{REPO_URL}/issues/new?title={quote_plus(title)}"
    if body:
        url += f"&body={quote_plus(body)}"
    return url


def reformat_url() -> str:
    return issue_url("artemis|fsck|reformat", REFORMAT_BODY)


def button_url() -> str:
    return issue_url("artemis|button", BUTTON_BODY)


# --- tiles (static; written by `tiles`) ---------------------------------------


def _slab(w: float, h: float) -> str:
    return f'<rect width="{ph.fmt(w)}" height="{ph.fmt(h)}" class="pn"/>'


def _key_cap(face: str = "key", bevel: bool = True) -> str:
    """A raised key: 1px lit top edge, 3px shadow underneath."""
    top = f'<rect x="2" y="2" width="{KEY}" height="{KEY - 3}" rx="3" class="khi"/>' if bevel else ""
    return (f'<rect x="2" y="2" width="{KEY}" height="{KEY}" rx="3" class="klo"/>{top}'
            f'<rect x="2" y="3" width="{KEY}" height="{KEY - 4}" rx="3" class="{face}"/>')


def _flat_cell() -> str:
    """A pressed-in, verified cell: flush with the canvas, hairline edge."""
    box = f'x="2.5" y="2.5" width="{KEY - 1}" height="{KEY - 1}" rx="3"'
    return f'<rect {box} class="flat"/><rect {box} class="fl-s" stroke-width="1"/>'


def _pixels(rows: tuple[str, ...], x: float, y: float, px: float, cls: str, dot: float, extra: str = "") -> str:
    rects = "".join(
        f'<rect x="{ph.fmt(x + c * px)}" y="{ph.fmt(y + r * px)}" width="{ph.fmt(dot)}" height="{ph.fmt(dot)}"/>'
        for r, row in enumerate(rows) for c, bit in enumerate(row) if bit == "#"
    )
    return f'<g class="{cls}"{extra}>{rects}</g>'


def _burst(cls: str, cy: float, extra: str = "") -> str:
    """The corrupted-sector mark: a 7x7 burst on the 2px pixel grid."""
    return _pixels(BURST, TILE / 2 - 7, cy - 7, 2, cls, 2, extra)


def _glow(body: str, mode: str) -> str:
    return f'<g filter="url(#tglow)">{body}</g>' if mode == "dark" else body


def tile_svg(name: str, mode: str) -> str:
    """One board tile. Every tile paints its full box with the slab colour so
    abutting tiles fuse into one device. Digits and marks are drawn on a 2px
    pixel grid (the 5x7 display face, solid), so they are identical on every OS."""
    w, h, label, css = TILE, TILE, "", ""
    mid = TILE / 2
    if name == "hidden":
        body = (_slab(w, h) + _key_cap()
                + f'<rect x="{mid - 1.5}" y="{mid - 2.5}" width="3" height="3" rx="0.5" class="accd"/>')
        label = "unscanned sector: a raised key"
    elif name == "c0":
        body = _slab(w, h) + _flat_cell() + f'<rect x="{mid - 1}" y="{mid - 1}" width="2" height="2" class="ln-f"/>'
        label = "verified sector, no corrupted neighbours"
    elif re.fullmatch(r"c[1-8]", name):
        n = int(name[1])
        cls = "acc" if n <= 2 else "warn"
        digit = ph.dot_text(str(n), mid - 5, mid - 7, 2, on=cls, off=None, dot=2)
        body = _slab(w, h) + _flat_cell() + _glow(digit, mode)
        label = f"verified sector, {n} corrupted neighbour{'s' if n > 1 else ''}"
    elif name == "panic":
        flicker = ' class="pk"' if mode == "dark" else ""
        body = _slab(w, h) + f"<g{flicker}>" + _key_cap("red", bevel=False) + _burst("ink", mid - 1) + "</g>"
        if mode == "dark":
            # A failing tube: solid red, then a double flicker every few seconds.
            css = (".pk{animation:fspk 4.7s steps(1) 1.2s infinite}"
                   "@keyframes fspk{0%{opacity:1}90%{opacity:.3}92%{opacity:1}94%{opacity:.45}96%,100%{opacity:1}}")
        label = "the corrupted sector that panicked the kernel"
    elif name == "mine":
        body = _slab(w, h) + _flat_cell() + _burst("red", mid, ' opacity="0.5"')
        label = "corrupted sector, dormant"
    elif name in BOARD_TITLES:
        w, h = BOARD_W, RAIL_TOP
        body = f'<rect width="{w}" height="{h + 8}" rx="6" class="pn"/>'
        title = ph.pane_title(0, w, 12, "0 disk map", BOARD_TITLES[name], active=True, inset=6)
        if name == "cols-panic":  # red is the kernel panic's colour, and only its
            title = title.replace('class="acc-s"', 'class="red-s"').replace('class="acc"', 'class="red"')
        body += title
        body += "".join(ph.text(RAIL_L + i * TILE + mid, 30, col, "mu", 11, anchor="middle")
                        for i, col in enumerate(COLS))
        label = f"disk map ({BOARD_TITLES[name]}), columns A to I"
    elif re.fullmatch(r"r[1-9]", name):
        w = RAIL_L
        body = _slab(w, h) + ph.text(RAIL_L / 2 + 0.5, mid + 4, name[1], "mu", 11, anchor="middle")
        label = f"row {name[1]}"
    elif name == "edge":
        w = RAIL_R
        body = _slab(w, h)
        label = "disk map bezel"
    elif name == "base":
        w, h = BOARD_W, RAIL_BOTTOM
        body = f'<rect y="-8" width="{w}" height="{h + 8}" rx="6" class="pn"/>'
        label = "disk map bezel"
    else:
        raise ValueError(f"unknown tile {name}")
    return ph.svg(w, h, body, label, mode, extra_css=css, defs=TILE_GLOW if mode == "dark" else "")


TILE_NAMES = (("hidden", "c0", *(f"c{n}" for n in range(1, 9)), "panic", "mine", *BOARD_TITLES,
               *(f"r{r}" for r in ROWS), "edge", "base"))


def _hardware_key(w: float, h: float, inset: float) -> str:
    """The raised keycap shared by DO NOT PRESS and mkfs: same plastic as the board."""
    x, kw, kh = inset, w - 2 * inset, h - 2 * inset
    return (f'<rect x="{x}" y="{x}" width="{ph.fmt(kw)}" height="{ph.fmt(kh)}" rx="4" class="klo"/>'
            f'<rect x="{x}" y="{x}" width="{ph.fmt(kw)}" height="{ph.fmt(kh - 3)}" rx="4" class="khi"/>'
            f'<rect x="{x}" y="{x + 1}" width="{ph.fmt(kw)}" height="{ph.fmt(kh - 4)}" rx="4" class="key"/>')


def button_svg(mode: str) -> str:
    """DO NOT PRESS: a keycap in an amber hazard collar. Amber means 'you can act
    here' on this machine; red is reserved for the kernel panic it does not cause."""
    w, h = BUTTON_W, BUTTON_H
    defs = ('<pattern id="hz" width="10" height="10" patternUnits="userSpaceOnUse" '
            'patternTransform="rotate(45)"><rect width="5" height="10" class="warn"/>'
            '<rect x="5" width="5" height="10" class="ink"/></pattern>')
    cy = h / 2 - 1
    led = f'<circle cx="23" cy="{ph.fmt(cy)}" r="3.5" class="warn{" led" if mode == "dark" else ""}"/>'
    body = (f'<rect width="{w}" height="{h}" rx="6" fill="url(#hz)"/>' + _hardware_key(w, h, 6)
            + (f'<g class="glow">{led}</g>' if mode == "dark" else led)
            + ph.text(w / 2 + 8, cy + 5.2, "DO NOT PRESS", "fg", 15, anchor="middle", bold=True))
    css = ""
    if mode == "dark":
        css = ".led{animation:fsled 2.4s ease-in-out infinite}@keyframes fsled{0%,100%{opacity:1}50%{opacity:.35}}"
    return ph.svg(w, h, body, "DO NOT PRESS", mode, extra_css=css, defs=defs)


def mkfs_svg(mode: str) -> str:
    """The reformat key: only drawn into the README once the board is dead."""
    w, h = MKFS_W, BUTTON_H
    cy = h / 2 - 1
    parts = [("mkfs /dev/sda1", "fg!"), ("  (reformat)", "mu")]
    cols = sum(len(chunk) for chunk, _ in parts)
    x = (w - cols * ph.CW * ph.SIZE) / 2
    body = (f'<rect width="{w}" height="{h}" rx="6" class="pn"/>'
            f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="6" class="warn-s" stroke-width="1"/>'
            + _hardware_key(w, h, 6) + ph.runs(x, cy + 4.5, parts))
    return ph.svg(w, h, body, "mkfs /dev/sda1 (reformat)", mode)


def static_assets() -> dict[str, str]:
    """Every static fsck asset, rendered in memory: {path: svg}."""
    out: dict[str, str] = {}
    for mode, suffix in MODES:
        for name in TILE_NAMES:
            out[f"{TILE_DIR}/{mode}/{name}.svg"] = tile_svg(name, mode)
        out[f"{FSCK_DIR}/button{suffix}.svg"] = button_svg(mode)
        out[f"{FSCK_DIR}/mkfs{suffix}.svg"] = mkfs_svg(mode)
    return out


# --- status panel (redrawn every render) ----------------------------------------


def short_date(stamp: object) -> str:
    """MM-DD from an ISO stamp, or ??-?? when the stamp is unreadable."""
    match = re.match(r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])T", str(stamp or ""))
    return f"{match.group(1)}-{match.group(2)}" if match else "??-??"


def clip(text: str, width: int) -> str:
    """Truncate like top(1): the last visible character becomes '+'."""
    return text if len(text) <= width else text[: max(width - 1, 0)] + "+"


def board_sealed(state: dict, salt: str) -> bool:
    """Whether THIS board's corruption map is sealed. The board records the
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


def fsck_view(state: dict, stats: dict, salt: str) -> dict:
    """Everything the panel shows, sanitized, as plain facts."""
    status = state.get("status", "active")
    if status not in ("active", "panicked", "cleaned"):
        status = "active"
    board = int(state.get("board_number") or 1)
    done = min(len(state.get("revealed") or {}), CLEAN_TOTAL)
    last = state.get("last_op") or {}
    panic_cell = str(state.get("panic_cell") or "??")
    if not re.fullmatch(r"[A-I][1-9]", panic_cell):
        panic_cell = "??"
    if status == "panicked":
        board_line = f"#{board}, lost {short_date(last.get('utc'))} at {panic_cell}"
    elif status == "cleaned":
        board_line = f"#{board}, cleaned {short_date(last.get('utc'))}"
    else:
        board_line = f"#{board}, online since {short_date(state.get('created_utc'))}"
    totals = stats_part(stats, "totals", dict)
    ops = []
    log = [entry for entry in stats_part(stats, "ops_log", list) if isinstance(entry, dict)]
    for entry in list(reversed(log))[:SMART_ROWS]:
        result = str(entry.get("result", ""))
        # The engine only logs short ops ("fsck C4", "reformat") and known
        # results; anything longer is a hand edit, clipped so it cannot push
        # the result column off the panel.
        ops.append({
            "date": short_date(entry.get("utc")),
            "login": sanitize_login(str(entry.get("login", ""))),
            "op": clip(sanitize_fragment(str(entry.get("op", "?"))) or "?", OP_COLS),
            "label": clip(RESULT_LABELS.get(result, sanitize_fragment(result) or "?"), RESULT_COLS),
            "cls": RESULT_CLASSES.get(result, "mu"),
        })
    return {
        "status": status,
        "board": board,
        "board_line": board_line,
        "done": done,
        "pct": done * 100 // CLEAN_TOTAL,
        "panic_cell": panic_cell,
        "sealed": board_sealed(state, salt),
        "operators": len(stats_part(stats, "users", dict)),
        "scans": as_count(totals.get("scans")),
        "panics": as_count(totals.get("panics")),
        "cleans": as_count(totals.get("cleans")),
        "ops": ops,
        "fame": top_users(stats, "cleans"),
        "shame": top_users(stats, "panics"),
        "seq": panel_seq(stats),
    }


def totals_text(view: dict) -> str:
    return (f"{ph.plural(view['operators'], 'operator')}, {ph.plural(view['scans'], 'scan')}, "
            f"{ph.plural(view['panics'], 'panic')}, {ph.plural(view['cleans'], 'clean')}")


def corrupt_lines(view: dict) -> list[tuple[str, str]]:
    if view["sealed"]:
        return [(f"{MINE_COUNT} sectors, map sealed (hmac)", "fg")]
    # The honor system gets its own line: the pause is the joke.
    return [(f"{MINE_COUNT} sectors. map derivable from source.", "fg"), ("honor system.", "warn")]


HallItem = tuple[str, str, str]  # ("1. ", login, " x3")


def hall_width(row: list[HallItem]) -> int:
    return sum(len(rank) + len(login) + len(count) for rank, login, count in row) + 2 * (len(row) - 1)


def hall_line(row: list[HallItem], width: int) -> str:
    """One hall line. If it is too long, the longest logins give way first,
    one character at a time."""
    caps = [len(login) for _, login, _ in row]
    fixed = hall_width(row) - sum(caps)
    while fixed + sum(caps) > width and max(caps) > 1:
        caps[caps.index(max(caps))] -= 1
    return "  ".join(f"{rank}{clip(login, cap)}{count}" for (rank, login, count), cap in zip(row, caps))


def hall_lines(entries: list[tuple[str, int]], width: int, max_lines: int) -> list[str]:
    """Ranked entries on as few lines as possible, but a hall exists to give
    credit: a tighter packing is only used when every login fits it whole.
    Logins are clipped only when even the loosest packing that max_lines
    allows cannot hold them."""
    if not entries:
        return ["(vacant)"]
    items = [(f"{i + 1}. ", login, f" x{count}") for i, (login, count) in enumerate(entries)]

    def pack(per_line: int) -> list[list[HallItem]]:
        return [items[k:k + per_line] for k in range(0, len(items), per_line)]

    loosest = -(-len(items) // max_lines)  # fewest items per line within the line budget
    per_line = len(items)
    while per_line > loosest and any(hall_width(row) > width for row in pack(per_line)):
        per_line -= 1
    return [hall_line(row, width) for row in pack(per_line)]


def hall_rows(view: dict, width: int, max_lines: int) -> list[tuple[str, list[tuple[str, str]]]]:
    """(label, parts) rows for the hall of fame / hall of shame block."""
    rows = []
    for key, name, cls in (("fame", "fame  ", "acc"), ("shame", "shame ", "warn")):
        for i, text in enumerate(hall_lines(view[key], width - len(name), max_lines)):
            label = "hall of" if key == "fame" and i == 0 else ""
            rows.append((label, [(name if i == 0 else " " * len(name), "mu"), (text, cls if view[key] else "mu")]))
    return rows


def help_lines(view: dict, phone: bool = False) -> list[list[tuple[str, str]]]:
    """Short how-to lines in the voice of a shell comment (amber = act here).
    Desktop gets two lines of <= 60 columns; phones get three of <= 46."""
    act = "warn"
    if view["status"] == "panicked":
        if phone:
            return [[("# the disk is lost. ", "mu"), ("press mkfs", act), (" below.", "mu")],
                    [("# red marks: corrupted sectors, dormant.", "mu")]]
        return [[("# the disk is lost. ", "mu"), ("press mkfs", act), (" below for a new one.", "mu")],
                [("# red marks are the corrupted sectors, now dormant.", "mu")]]
    if view["status"] == "cleaned":
        if phone:
            return [[("# every sector verified.", "mu")], [("# the machine remembers you.", "mu")],
                    [("# ", "mu"), ("press mkfs", act), (" below to go again.", "mu")]]
        return [[("# every sector verified. the machine remembers you.", "mu")],
                [("# ", "mu"), ("press mkfs", act), (" below to reformat and go again.", "mu")]]
    if phone:
        return [[("# ", "mu"), ("tap a sector", act), (", submit the issue as-is.", "mu")],
                [("# eyes = ack. the board redraws in ~1 min.", "mu")],
                [("# the first scan is always safe.", "mu")]]
    return [[("# ", "mu"), ("click a sector", act), (", submit the issue as-is. eyes = ack.", "mu")],
            [("# the board redraws in ~1 min. first scan is always safe.", "mu")]]


BOUNCE = (1, 2, 3, 2, 1, 0)  # systemd's asterisks, ping-ponging in a 6-wide field
BOUNCE_CSS = (
    ".bf{animation:fsbf 1.2s steps(1) infinite;opacity:0}.bf0{opacity:1}"
    + "".join(f".bf{i}{{animation-delay:{i * 0.2:.1f}s}}" for i in range(1, len(BOUNCE)))
    + "@keyframes fsbf{0%{opacity:1}16.66%,100%{opacity:0}}"
)


def state_line(view: dict, x: float, y: float, size: float, animate: bool) -> str:
    """The systemd status column: [ *** ] / [FAILED] / [  OK  ]."""
    if view["status"] == "panicked":
        return ph.runs(x, y, [("[", "mu"), ("FAILED", "red!"), ("] ", "mu"),
                              (f"kernel panic at {view['panic_cell']}", "red")], size)
    if view["status"] == "cleaned":
        return ph.runs(x, y, [("[", "mu"), ("  OK  ", "acc!"), ("] ", "mu"), ("/dev/sda1 is clean", "acct")], size)
    cw = ph.CW * size
    out = [ph.runs(x, y, [("[", "mu"), ("      ", "mu"), ("] ", "mu"), ("a start job is running", "fg"),
                          (" (no limit)", "mu")], size)]
    frames = BOUNCE if animate else BOUNCE[:1]
    for i, pos in enumerate(frames):
        cls = f"warn bf bf{i}" if animate else "warn"
        out.append(ph.text(x + (1 + pos) * cw, y, "***", cls, size, bold=True))
    return "".join(out)


def pct_class(view: dict) -> str:
    """Phosphor means lit: a disk with nothing verified reads muted."""
    return "acc" if view["done"] else "mu"


def verified_meter(view: dict, x: float, y: float, width: float, height: float = 11) -> str:
    """One cell per clean sector: 71 cells, lit as they are verified."""
    gap = 1.0
    cell = (width - gap * (CLEAN_TOTAL - 1)) / CLEAN_TOTAL
    return ph.meter(x, y, CLEAN_TOTAL, view["done"], cell=round(cell, 2), gap=gap, height=height)


def smart_rows(view: dict, width: int) -> list[list[tuple[str, str]]]:
    """S.M.A.R.T. rows: MM-DD login op result, columns aligned, logins clipped."""
    if not view["ops"]:
        return [[("no ops recorded. the disk sits in silence.", "mu")]]
    op_w = max(len(op["op"]) for op in view["ops"])
    res_w = max(len(op["label"]) for op in view["ops"])
    login_w = max(4, min(max(len(op["login"]) for op in view["ops"]), width - 5 - op_w - res_w - 3))
    rows = []
    for op in view["ops"]:
        rows.append([(op["date"] + " ", "mu"), (clip(op["login"], login_w).ljust(login_w) + " ", "fg"),
                     (op["op"].ljust(op_w) + " ", "mu"), (op["label"], op["cls"] + ("!" if op["cls"] == "red" else ""))])
    return rows


def panel_svg(view: dict, mode: str) -> str:
    """Desktop status panel: 500 wide, exactly as tall as the board beside it.
    If a crowded disk would not fit, the oldest S.M.A.R.T. rows give way; the
    render never fails over layout."""
    w, h = PANEL_W, PANEL_H
    size, lh, x0, label_cols, gap = ph.SIZE, 18, 16, 11, 6
    cw = ph.CW * size
    vx = x0 + label_cols * cw
    value_cols = int((w - x0 - vx) / cw)
    animate = mode == "dark" and view["status"] == "active"

    count = f"{view['done']}/{CLEAN_TOTAL}"
    facts = [("board", [(view["board_line"], "fg")]), ("verified", [(count, "fg")])]
    facts += [("corrupt" if i == 0 else "", [(text, cls)]) for i, (text, cls) in enumerate(corrupt_lines(view))]
    facts.append(("totals", [(totals_text(view), "fg")]))
    halls = hall_rows(view, value_cols, 2)  # at most two lines a hall: the panel height is fixed
    smart = smart_rows(view, value_cols)
    top = 60.0                      # first fact baseline
    help_y = h - 12 - lh            # help lines are pinned to the bottom edge
    while len(smart) > 1 and top + (len(facts) + len(smart) + len(halls) - 1) * lh + 2 * gap > help_y - lh - 4:
        smart.pop()

    out = [ph.panel(0, 0, w, h), ph.pane_title(0, w, 12, PANEL_TITLE[0], PANEL_TITLE[1], inset=6),
           state_line(view, x0, 37, size, animate)]
    y = top
    for block, first_label in ((facts, None), (smart, "S.M.A.R.T."), (halls, None)):
        for i, item in enumerate(block):
            label, parts = (first_label if i == 0 else "", item) if first_label else item
            out.append(ph.text(x0, y, label, "mu", size))
            out.append(ph.runs(vx, y, parts, size))
            if label == "verified":
                pct = f"{view['pct']}%"
                mx = vx + (len(count) + 2) * cw
                out.append(ph.text(w - x0, y, pct, pct_class(view), size, anchor="end"))
                out.append(verified_meter(view, mx, y - 10, w - x0 - len(pct) * cw - 10 - mx))
            y += lh
        y += gap
    for i, parts in enumerate(help_lines(view)):
        out.append(ph.runs(x0, help_y + i * lh, parts, size))
    return ph.svg(w, h, "".join(out), panel_alt(view), mode, extra_css=BOUNCE_CSS if animate else "")


def wrap_words(text: str, width: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}" if line else word
    return lines + ([line] if line else [])


def panel_phone_svg(view: dict) -> str:
    """Phone status panel: 360 wide, dark, stacked; as tall as it needs."""
    w = ph.WP
    size, lh, x0, label_cols = ph.SIZE_CHROME, 18, 12, 11
    cw = ph.CW * size
    vx = x0 + label_cols * cw
    value_cols = int((w - x0 - vx) / cw)
    full_cols = int((w - 2 * x0) / cw)
    out: list[str] = []
    y = 37.0
    out.append(state_line(view, x0, y, size, view["status"] == "active"))

    def row(label: str, parts: list[tuple[str, str]]) -> None:
        nonlocal y
        out.append(ph.text(x0, y, label, "mu", size))
        out.append(ph.runs(vx, y, parts, size))
        y += lh

    y += 24
    for i, text in enumerate(wrap_words(view["board_line"], value_cols)):
        row("board" if i == 0 else "", [(text, "fg")])
    out.append(ph.text(w - x0, y, f"{view['pct']}%", pct_class(view), size, anchor="end"))
    row("verified", [(f"{view['done']}/{CLEAN_TOTAL}", "fg")])
    out.append(verified_meter(view, x0, y - 11, w - 2 * x0, 10))
    y += lh
    first = True
    for text, cls in corrupt_lines(view):
        for sentence in re.split(r"(?<=\.)\s+", text):  # break at full stops first: deadpan needs pauses
            for piece in wrap_words(sentence, value_cols):
                row("corrupt" if first else "", [(piece, cls)])
                first = False
    items = totals_text(view).split(", ")
    for i in range(0, len(items), 2):  # pairs, so a count never loses its noun
        tail = "," if i + 2 < len(items) else ""
        row("totals" if i == 0 else "", [(", ".join(items[i:i + 2]) + tail, "fg")])

    y += 6
    out.append(ph.text(x0, y, "S.M.A.R.T.", "mu", size))
    y += lh
    for parts in smart_rows(view, full_cols):
        out.append(ph.runs(x0, y, parts, size))
        y += lh

    y += 6
    for label, parts in hall_rows(view, value_cols, HALL_ROWS):  # the phone panel grows instead
        row(label, parts)

    y += 8
    for parts in help_lines(view, phone=True):
        out.append(ph.runs(x0, y, parts, size))
        y += lh
    h = y - lh + 14
    body = ph.panel(0, 0, w, h) + ph.pane_title(0, w, 12, PANEL_TITLE[0], PANEL_TITLE[1], size=11, inset=6)
    css = BOUNCE_CSS if view["status"] == "active" else ""
    # On phones the float spans the column and the board stacks under it; the
    # transparent strip below the slab is the gap between the two.
    return ph.svg(w, h + PHONE_GAP, body + "".join(out), panel_alt(view), "dark", extra_css=css)


def panel_alt(view: dict) -> str:
    """The whole panel in words: what a sighted visitor reads, in reading order."""
    if view["status"] == "panicked":
        head = f"FAILED: kernel panic at {view['panic_cell']}."
    elif view["status"] == "cleaned":
        head = "OK: /dev/sda1 is clean."
    else:
        head = "a start job is running (no limit)."
    ops = "; ".join(f"{op['date']} {op['login']} {op['op']}: {op['label']}" for op in view["ops"]) or "none"
    fame = ", ".join(f"{login} x{n}" for login, n in view["fame"]) or "vacant"
    shame = ", ".join(f"{login} x{n}" for login, n in view["shame"]) or "vacant"
    corrupt = " ".join(text for text, _ in corrupt_lines(view)).rstrip(".") + "."
    helps = " ".join("".join(chunk for chunk, _ in parts).lstrip("# ") for parts in help_lines(view))
    return (f"fsck status for /dev/sda1: {head} board {view['board_line']}. "
            f"{view['done']} of {CLEAN_TOTAL} sectors verified ({view['pct']}%). corrupt: {corrupt} "
            f"totals: {totals_text(view)}. last ops: {ops}. hall of fame: {fame}. hall of shame: {shame}. {helps}")


PANEL_FILE_RE = re.compile(r"^panel(?:-(\d+))?(?:-light|-phone)?\.svg$")


def panel_paths(seq: int) -> dict[str, str]:
    """The three panel files for one board version (dark, light, phone)."""
    return {
        "dark": f"{FSCK_DIR}/panel-{seq}.svg",
        "light": f"{FSCK_DIR}/panel-{seq}-light.svg",
        "phone": f"{FSCK_DIR}/panel-{seq}-phone.svg",
    }


def render_panels(state: dict, stats: dict, salt: str) -> dict[str, str]:
    view = fsck_view(state, stats, salt)
    paths = panel_paths(view["seq"])
    return {
        paths["dark"]: panel_svg(view, "dark"),
        paths["light"]: panel_svg(view, "light"),
        paths["phone"]: panel_phone_svg(view),
    }


def prune_panels(seq: int, root: Path = Path(".")) -> None:
    """Delete panel files older than the previous version. The previous set stays,
    so a page rendered just before this commit never shows a broken image."""
    for path in (root / FSCK_DIR).glob("panel*.svg"):
        match = PANEL_FILE_RE.match(path.name)
        if match and (match.group(1) is None or int(match.group(1)) < seq - 1):
            try:
                path.unlink()
            except OSError as error:
                warn(f"could not prune {path} ({error})")


# --- README block -----------------------------------------------------------------


def tile_pic(name: str, width: int, height: int, alt: str, title: str = "") -> str:
    """A tile in a bare <picture>: light twin via <source>, no auto-link to the raw file."""
    extra = f' title="{title}"' if title else ""
    dark = f"{TILE_DIR}/dark/{name}.svg"
    return (f'<picture><source media="(max-width: 600px)" srcset="{dark}">'
            f'<source media="(prefers-color-scheme: light)" srcset="{TILE_DIR}/light/{name}.svg">'
            f'<img src="{dark}" width="{width}" height="{height}" align="top" '
            f'alt="{alt}"{extra}></picture>')


def digit_pic(cell: str, digit: object) -> str:
    n = max(0, min(8, int(digit)))
    return tile_pic(f"c{n}", TILE, TILE, f"{cell}: {n}")


def render_cell(state: dict, cell: str, mines: set[str] | None) -> str:
    status = state["status"]
    revealed = state["revealed"]
    if status == "active":
        if cell in revealed:
            return digit_pic(cell, revealed[cell])
        url = html.escape(issue_url(f"artemis|fsck|{cell}", SCAN_BODY.format(cell=cell)))
        return f'<a href="{url}">{tile_pic("hidden", TILE, TILE, f"scan {cell}", f"fsck {cell}")}</a>'
    # Dead board (panicked or cleaned): everything is face-up, nothing is clickable.
    mines = mines or set()
    if cell in mines:
        if status == "panicked" and cell == state.get("panic_cell"):
            return tile_pic("panic", TILE, TILE, f"{cell}: KERNEL PANIC")
        return tile_pic("mine", TILE, TILE, f"{cell}: corrupted (dormant)")
    return digit_pic(cell, revealed[cell] if cell in revealed else adjacency(cell, mines))


def render_board(state: dict, salt: str) -> str:
    mines = board_mines(state, salt) if state["status"] != "active" else None
    rail = {"panicked": "cols-panic", "cleaned": "cols-clean"}.get(state["status"], "cols")
    rows = [tile_pic(rail, BOARD_W, RAIL_TOP, "")]
    for row in ROWS:
        cells = "".join(render_cell(state, f"{col}{row}", mines) for col in COLS)
        rows.append(tile_pic(f"r{row}", RAIL_L, TILE, "") + cells + tile_pic("edge", RAIL_R, TILE, ""))
    rows.append(tile_pic("base", BOARD_W, RAIL_BOTTOM, ""))
    return "<br>\n".join(rows)


def panel_pic(view: dict) -> str:
    paths = panel_paths(view["seq"])
    return (f'<picture><source media="(max-width: 600px)" srcset="{paths["phone"]}">'
            f'<source media="(prefers-color-scheme: light)" srcset="{paths["light"]}">'
            f'<img align="right" src="{paths["dark"]}" width="{PANEL_W}" '
            f'alt="{html.escape(panel_alt(view))}"></picture>')


def key_link(url: str, name: str, width: int, alt: str, title: str) -> str:
    return (f'<a href="{html.escape(url)}"><picture>'
            f'<source media="(max-width: 600px)" srcset="{FSCK_DIR}/{name}.svg">'
            f'<source media="(prefers-color-scheme: light)" srcset="{FSCK_DIR}/{name}-light.svg">'
            f'<img src="{FSCK_DIR}/{name}.svg" width="{width}" height="{BUTTON_H}" align="top" alt="{alt}" '
            f'title="{title}"></picture></a>')


def render_fsck_block(state: dict, stats: dict, salt: str) -> str:
    """Panel (floated right) + board in one paragraph, so their tops align; then
    the keys. Pure: returns markup, touches nothing."""
    view = fsck_view(state, stats, salt)
    keys = [key_link(button_url(), "button", BUTTON_W, "DO NOT PRESS", "nothing happens. probably.")]
    if can_reformat(state):
        keys.append(key_link(reformat_url(), "mkfs", MKFS_W,
                             "mkfs /dev/sda1 (reformat): bring up a fresh board", "wipe /dev/sda1, seed a new board"))
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
    try:
        panels = render_panels(state, stats, salt)
        block = render_fsck_block(state, stats, salt)
    except Exception:  # noqa: BLE001 - never blank the block over a drawing bug
        warn("fsck render failed; panel and README left as they were\n" + traceback.format_exc())
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
            ph.write_svg(root / path, content)
    except (OSError, ValueError) as error:
        warn(f"could not write the status panel ({error}); README left as it was")
        return False
    if not safe_replace(readme, FSCK_START, FSCK_END, block):
        return False
    prune_panels(panel_seq(stats), root)
    return True


def write_static_assets(root: Path = Path(".")) -> int:
    """Render every tile and key in memory, then write them; retire the old flat
    tiles (assets/fsck/tiles/*.svg) that the markdown-table board used."""
    assets = static_assets()
    changed = sum(ph.write_svg(root / path, content) for path, content in assets.items())
    for stale in sorted((root / TILE_DIR).glob("*.svg")):
        stale.unlink()
        changed += 1
    return changed


# --- command handling -------------------------------------------------------


def parse_command(title: str) -> tuple[str, str | None] | None:
    """Return ("scan", CELL) | ("reformat", None) | ("button", None) | ("sandwich", None) | None."""
    title = (title or "").strip()
    if title == SANDWICH_TITLE:
        return ("sandwich", None)
    match = CMD_RE.match(title)
    if not match:
        return None
    if match.group("cell"):
        return ("scan", match.group("cell").upper())
    if match.group("reformat"):
        return ("reformat", None)
    return ("button", None)


def scan_reply(state: dict, info: dict, actor: str) -> str:
    board = state["board_number"]
    done = len(state["revealed"])
    result = info["result"]
    prefix = ""
    if info["auto_reformatted"]:
        prefix = f"mkfs.art3m1s: previous board was dead; auto-reformatted. board #{board} is online.\n"

    if result == "dup":
        return prefix + (
            f"fsck: sector {info['cell']} was already verified on board #{board}. "
            "the daemon logs your enthusiasm and returns to idle."
        )
    if result == "panic":
        return prefix + (
            f"KERNEL PANIC: sector {info['cell']} was corrupted. read head destroyed on contact.\n"
            f"board #{board} is lost at {done}/{CLEAN_TOTAL} sectors verified. "
            f"the incident has been logged against operator {actor}.\n"
            "file `artemis|fsck|reformat` to requisition a fresh disk."
        )
    if result == "clean":
        return prefix + (
            f"fsck complete: /dev/sda1 is CLEAN. all {CLEAN_TOTAL} sectors of board #{board} verified.\n"
            f"operator {actor} takes the credit. the daemon nods, almost imperceptibly.\n"
            "file `artemis|fsck|reformat` whenever you feel like doing it all again."
        )
    return prefix + (
        f"fsck: sector {info['cell']} verified. {info['adj']}/8 adjacent sectors report corruption.\n"
        f"{info['opened']} sector(s) opened this pass — {done}/{CLEAN_TOTAL} verified on board #{board}. "
        "carry on, operator."
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
            "mkfs.art3m1s: refused. fsck in progress; finish your shift, operator.\n"
            f"(board #{state['board_number']} stands at {done}/{CLEAN_TOTAL} sectors verified. "
            "the disk outlives us all.)"
        )
    state = new_state(state["board_number"] + 1, salt)
    record_op(stats, actor, ["reformats"], "reformat", "reformat")
    save_json(STATE_PATH, state)
    save_json(STATS_PATH, stats)
    render_readme(readme, state, stats, salt)
    return (
        f"mkfs.art3m1s: wiping /dev/sda1... done. board #{state['board_number']} is online, "
        f"{MINE_COUNT} corrupted sectors seeded.\n"
        "the first scan is always safe. after that you are on your own, operator."
    )


def swap_oneliner(issue_number: int, readme: str) -> None:
    """Silently rotate the boot one-liner. Never surfaces in the reply.

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
        warn("boot one-liner markers missing; skipped swap")
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
    return BUTTON_REPLY


def handle_process(title: str, actor: str, issue_number: int, readme: str) -> str:
    actor = sanitize_login(actor)
    command = parse_command(title)
    if command is None:
        # Echo the command the visitor typed, not the router prefix: "artemis|fsck|Z9"
        # reads back as "fsck Z9", the way a shell would name it.
        typed = re.sub(r"^\s*artemis\s*\|", "", title or "", flags=re.IGNORECASE).replace("|", " ")
        shown = sanitize_fragment(typed) or "(empty)"
        return (
            f"artemis: {shown}: command not found\n"
            "available: `artemis|fsck|A1`..`artemis|fsck|I9`, `artemis|fsck|reformat`, `artemis|button`"
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
    salt = "test-salt"

    # Geometry.
    assert set(neighbors("A1")) == {"B1", "A2", "B2"}
    assert set(neighbors("I9")) == {"H9", "I8", "H8"}
    assert len(neighbors("E5")) == 8

    # First-scan safety + determinism, without persisting mines.
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

    # The persisted state of an ACTIVE board must not disclose mines or a seed.
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

    # Dup scan is a no-op on the board and does not count as a scan.
    before = dict(state["revealed"])
    state, info = apply_scan(state, "e5", "tester", salt)
    assert info["result"] == "dup" and state["revealed"] == before

    # Panic path exposes mines only after death.
    boom = new_state(2, salt)
    boom, _ = apply_scan(boom, "A1", "tester", salt)
    target = sorted(board_mines(boom, salt))[0]
    boom, info = apply_scan(boom, target, "tester", salt)
    assert info["result"] == "panic" and boom["status"] == "panicked"
    assert boom["mines_exposed"] and boom["panic_cell"] == target

    # Reformat gate: refused mid-game, allowed when dead; scanning a dead board
    # auto-reformats and the fresh first scan is safe again.
    assert not can_reformat(state) and can_reformat(boom)
    boom, info = apply_scan(boom, "E5", "tester", salt)
    assert info["auto_reformatted"] and boom["board_number"] == 3
    assert boom["status"] == "active" and info["result"] == "ok"

    # Salt rotation mid-board auto-reformats instead of corrupting.
    rotated, info = apply_scan(dict(state), "A1", "tester", "rotated-salt")
    assert info["auto_reformatted"] and rotated["salt_fp"] == salt_fingerprint("rotated-salt")

    # Clean path: reveal every clean sector but one, then scan the last one.
    final = new_state(4, salt)
    final, _ = apply_scan(final, "E5", "tester", salt)
    final_mines = board_mines(final, salt)
    clean = [cell for cell in ALL_CELLS if cell not in final_mines]
    target = next(cell for cell in clean if cell not in final["revealed"])
    final["revealed"] = {cell: adjacency(cell, final_mines) for cell in clean if cell != target}
    final, info = apply_scan(final, target, "tester", salt)
    assert info["result"] == "clean" and final["status"] == "cleaned"
    assert len(final["revealed"]) == CLEAN_TOTAL and final["mines_exposed"]

    # Router.
    assert parse_command("artemis|fsck|c4") == ("scan", "C4")
    assert parse_command("artemis|fsck|I9") == ("scan", "I9")
    assert parse_command("artemis|fsck|reformat") == ("reformat", None)
    assert parse_command("artemis|button") == ("button", None)
    assert parse_command(SANDWICH_TITLE) == ("sandwich", None)
    assert parse_command("artemis|fsck|J4") is None
    assert parse_command("artemis|fsck|A0") is None
    assert parse_command("artemis|sudo") is None
    assert parse_command("ARTEMIS|BUTTON") is None
    assert parse_command("") is None
    unknown = handle_process("artemis|fsck|Z9", "tester", 1, "no-readme-needed.md")
    assert unknown.startswith("artemis: fsck Z9: command not found"), unknown
    mention = handle_process("artemis| @someone look", "tester", 1, "no-readme-needed.md")
    assert "@" not in mention.splitlines()[0], "the bot never mentions anyone on a visitor's behalf"

    # Sanitizers.
    assert sanitize_login("evil/../user<img>") == "eviluserimg"
    assert sanitize_login("") == "anonymous"
    assert sanitize_fragment("a[b]c<d>`e`|f") == "abcdef"

    # Button pool swap: deterministic per issue number, never repeats the current line.
    lines = load_oneliners()
    assert len(lines) >= 12, "oneliners.txt should ship with a full pool"
    assert all(len(line) <= 72 for line in lines), "one-liners live in the footer <pre>: 72 columns max"
    pick = pick_oneliner(20, lines[0], lines)
    assert pick is not None and pick != lines[0]
    assert pick == pick_oneliner(20, lines[0], lines)
    assert pick_oneliner(20, "not in pool", lines) in lines

    # Rendering: the board is one device; only unscanned keys on a live board are links.
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

    active_block = render_fsck_block(state, stats, salt)
    unscanned = [cell for cell in ALL_CELLS if cell not in state["revealed"]]
    links = re.findall(r'<a href="([^"]+)">(.*?)</a>', active_block)
    scan_links = [(url, inner) for url, inner in links if re.search(r"artemis%7Cfsck%7C[A-I][1-9]&", url)]
    assert len(scan_links) == len(unscanned) > 0
    assert all("tiles/dark/hidden.svg" in inner and "tiles/light/hidden.svg" in inner for _, inner in scan_links)
    assert active_block.count('<img src="assets/fsck/tiles/dark/hidden.svg"') == len(unscanned), "hidden keys appear only as links"
    assert all(f"artemis%7Cfsck%7C{cell}&amp;" in active_block for cell in unscanned)
    assert not any(f"artemis%7Cfsck%7C{cell}&amp;" in active_block for cell in state["revealed"])
    assert all(f'alt="{cell}: {digit}"' in active_block for cell, digit in state["revealed"].items())
    assert active_block.count("<br>") == len(ROWS) + 1 and 'br clear="all"' in active_block
    assert "artemis%7Cbutton" in active_block and "assets/fsck/button.svg" in active_block
    assert "assets/fsck/mkfs.svg" not in active_block, "mkfs only appears on a dead board"
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
    assert panic_block.count('<img src="assets/fsck/tiles/dark/panic.svg"') == 1
    assert "tiles/dark/cols-panic.svg" in panic_block and "tiles/dark/cols.svg" in active_block
    assert "tiles/dark/cols-clean.svg" in clean_block
    assert panic_block.count('<img src="assets/fsck/tiles/dark/mine.svg"') == MINE_COUNT - 1
    assert clean_block.count('<img src="assets/fsck/tiles/dark/mine.svg"') == MINE_COUNT and "tiles/dark/panic.svg" not in clean_block
    for dead in (panic_block, clean_block):
        assert "tiles/dark/hidden.svg" not in dead
        assert not re.search(r"artemis%7Cfsck%7C[A-I][1-9]", dead), "dead boards have no scan links"
        assert "artemis%7Cfsck%7Creformat" in dead and "assets/fsck/mkfs.svg" in dead
        assert dead.count("<a href=") == 2, "only DO NOT PRESS and mkfs are clickable"
        assert "[!" not in dead and "<sub>" not in dead

    # Status panels: parseable, state-true, sized to sit beside the board.
    def animated(svg: str) -> bool:
        # ph.css ships the shared blink keyframes in every SVG; what matters is
        # whether anything here defines or uses motion of its own.
        return bool(re.search(r"@keyframes fs|class=\"[^\"]*\b(?:blink|bf|pk|led)\b", svg))

    def text_fits(svg: str, width: float) -> bool:
        for node in ET.fromstring(svg).iter("{http://www.w3.org/2000/svg}text"):
            x, span = float(node.get("x")), float(node.get("textLength", 0))
            if node.get("text-anchor") == "end":
                x -= span
            if x < 0 or x + span > width - 8:
                return False
        return True

    for board_state in (state, panic_state, final):
        panels = render_panels(board_state, stats, salt)
        paths = panel_paths(panel_seq(stats))
        assert set(panels) == set(paths.values())
        for path, content in panels.items():
            ET.fromstring(content)
            assert text_fits(content, PANEL_W if "phone" not in path else ph.WP), f"text overflows {path}"
        assert not animated(panels[paths["light"]]), "safe mode never animates"
        assert f'height="{PANEL_H}"' in panels[paths["dark"]]

    def dark_panel(board_state: dict, board_stats: dict, board_salt: str) -> str:
        return render_panels(board_state, board_stats, board_salt)[panel_paths(panel_seq(board_stats))["dark"]]

    assert "a start job is running" in dark_panel(state, stats, salt)
    assert "FAILED" in dark_panel(panic_state, stats, salt)
    assert "is clean" in dark_panel(final, stats, salt)
    assert "scan again" not in dark_panel(panic_state, stats, salt), "a dead board has nothing to scan"
    assert BOARD_W <= 279 and BOARD_W + 20 + PANEL_W <= 831, "board must fit a 360px phone and a 1280px desktop"

    # Worst case still fits: four long logins, full halls, unsealed map.
    crowded = empty_stats()
    for i in range(OPS_LOG_LIMIT):
        who = f"a-very-long-github-login-number-{i:02d}xx"
        record_op(crowded, who, ["scans", "panics", "cleans"], "reformat", "refused")
    open_board = new_state(9, DEFAULT_SALT)
    open_board, _ = apply_scan(open_board, "E5", "tester", DEFAULT_SALT)
    for path, content in render_panels(open_board, crowded, DEFAULT_SALT).items():
        assert text_fits(content, PANEL_W if "phone" not in path else ph.WP), f"crowded text overflows {path}"

    # A hand-edited log (long op, unknown result, broken stamp) is clipped, never overflows.
    hostile = empty_stats()
    evil = "<script>&amp;\"'`|[x](y)" + "W" * 200
    hostile["ops_log"] = [{"login": evil, "op": evil, "result": evil, "utc": "2026-13-45T99:99:99Z"}] * 4
    hostile["users"] = {evil: {"scans": 1, "panics": 999999, "cleans": 12345}}
    for path, content in render_panels(open_board, hostile, DEFAULT_SALT).items():
        assert text_fits(content, PANEL_W if "phone" not in path else ph.WP), f"hostile text overflows {path}"
        assert "<script" not in content and "??-??" in content
    hostile_block = render_fsck_block(open_board, hostile, DEFAULT_SALT)
    assert "<script" not in hostile_block and "&lt;script" not in hostile_block

    # Halls give credit: ordinary logins are never cut down to stubs.
    names = [("disk-whisperer", 2), ("night-shift-ops", 1), ("IdkwhatImD0ing", 1)]
    assert hall_lines(names, 43, 2) == ["1. disk-whisperer x2  2. night-shift-ops x1", "3. IdkwhatImD0ing x1"]
    crew = empty_stats()
    crew["users"] = {login: {"cleans": n, "panics": n} for login, n in names}
    desk = dark_panel(state, crew, salt)
    assert all(f"{login} x{n}" in desk for login, n in names), "desktop halls keep ordinary logins whole"
    assert hall_lines(names[:2], 30, 2) == ["1. disk-whisperer x2", "2. night-shift-ops x1"]
    assert hall_lines([("bob", 2), ("al", 1)], 30, 2) == ["1. bob x2  2. al x1"]
    squeezed = hall_lines([("a" * 39, 1), ("bob", 1), ("b" * 39, 1)], 30, 2)
    assert len(squeezed) == 2 and all(len(line) <= 30 for line in squeezed), squeezed
    assert squeezed[0].endswith("+ x1  2. bob x1"), "only the longest login gives way"
    assert hall_lines([], 30, 2) == ["(vacant)"]

    # The unsealed wink shows only on a board born without the secret salt.
    wink = "honor system"
    assert wink in dark_panel(open_board, stats, DEFAULT_SALT)
    assert wink in render_fsck_block(open_board, stats, DEFAULT_SALT)
    assert wink not in dark_panel(state, stats, salt)
    assert wink not in render_fsck_block(state, stats, salt)
    assert wink not in render_fsck_block(state, stats, DEFAULT_SALT), "a local render tells the live board's truth"

    # Static assets: every tile and key, both modes, valid XML; safe mode is still.
    assets = static_assets()
    assert len(assets) == 2 * (len(TILE_NAMES) + 2)
    assert animated(assets[f"{TILE_DIR}/dark/panic.svg"]) and animated(assets[f"{FSCK_DIR}/button.svg"])
    assert animated(dark_panel(state, stats, salt)), "the detector must see real motion"
    for path, content in assets.items():
        ET.fromstring(content)
        if "/light/" in path or path.endswith("-light.svg"):
            assert not animated(content), f"{path} animates in safe mode"

    # End to end on a scratch README: panels written, block replaced, never blanked.
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        readme = root / "README.md"
        readme.write_text(
            f"# lab\n{FSCK_START}\nstale-block\n{FSCK_END}\n<pre>{ONELINER_START}\n`{lines[0]}`\n{ONELINER_END}</pre>\n",
            encoding="utf-8",
        )
        (root / FSCK_DIR).mkdir(parents=True, exist_ok=True)
        for legacy in ("panel.svg", "panel-light.svg", "panel-0.svg", "panel-0-phone.svg"):
            (root / FSCK_DIR / legacy).write_text("<svg/>", encoding="utf-8")
        assert render_readme(str(readme), state, stats, salt, root=root)
        for path in panel_paths(2).values():
            ET.parse(root / path)
        text = readme.read_text(encoding="utf-8")
        assert "stale-block" not in text and panel_paths(2)["dark"] in text and "tiles/dark/hidden.svg" in text
        record_op(stats, "tester", ["scans"], "fsck E5", "dup")
        render_readme(str(readme), state, stats, salt, root=root)
        assert panel_paths(3)["dark"] in readme.read_text(encoding="utf-8"), "a new op must change the panel URL"
        left = sorted(path.name for path in (root / FSCK_DIR).glob("panel*.svg"))
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
        before = sorted(path.name for path in (root / FSCK_DIR).glob("panel*.svg"))
        record_op(stats, "tester", ["scans"], "fsck E5", "dup")
        assert not render_readme(str(bare), state, stats, salt, root=root)
        assert sorted(path.name for path in (root / FSCK_DIR).glob("panel*.svg")) == before, \
            "a README without markers gets no panel files"
        swap_oneliner(40, str(bare))
        assert bare.read_text(encoding="utf-8") == "no markers here\n"
        assert not render_readme(str(root / "MISSING.md"), state, stats, salt, root=root)

    # Hand-edited stats never take the renderer down.
    junk = {"users": {"x": {"panics": "n/a"}, "y": "str"}, "totals": {"scans": "?"}, "ops_log": ["bad", 3]}
    view = fsck_view(state, junk, salt)
    assert view["scans"] == 0 and view["ops"] == [] and view["shame"] == []
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
    sealed = "sealed" if is_sealed(salt) else "UNSEALED (set FSCK_SALT to seal the corruption map)"
    print(f"initialized board #1 ({sealed}) in {STATE_PATH.parent}")


def cmd_process(args: argparse.Namespace) -> None:
    try:
        reply = handle_process(args.title, args.actor, args.issue, args.readme)
    except Exception:  # The reply is the contract; a bad day never breaks the bot.
        warn(traceback.format_exc())
        reply = "artemis: internal fault. a core dump was written to /dev/null. the daemon shrugs and carries on."
    print(reply)


def cmd_render(args: argparse.Namespace) -> None:
    salt = current_salt()
    if render_readme(args.readme, load_state(salt), load_stats(), salt):
        print("rendered fsck block", file=sys.stderr)


def cmd_tiles(_args: argparse.Namespace) -> None:
    try:
        changed = write_static_assets()
    except (OSError, ValueError) as error:
        warn(f"tiles not written: {error}")
        return
    print(f"fsck tiles: {changed} file(s) changed in {FSCK_DIR}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="ART3M1S issue-ops engine")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="fresh board + empty stats")
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

    p_tiles = sub.add_parser("tiles", help="write the static board tiles and keys to assets/fsck/")
    p_tiles.set_defaults(func=cmd_tiles)

    p_test = sub.add_parser("self-test", help="deterministic assertion suite")
    p_test.set_defaults(func=lambda _args: self_test())

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
