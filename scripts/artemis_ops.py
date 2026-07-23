"""ART3M1S issue-ops: the fsck minigame engine, command router, and README renderer.

Usage (always from the repo root):

    python scripts/artemis_ops.py init
    python scripts/artemis_ops.py process --title STR --actor LOGIN --issue INT
    python scripts/artemis_ops.py render
    python scripts/artemis_ops.py self-test

Contract for `process`: stdout is EXACTLY the in-character issue-comment reply
(nothing else), and the exit code is always 0. Diagnostics go to stderr.

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
import json
import os
import random
import re
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus

from readme_blocks import replace_block


USERNAME = "IdkwhatImD0ing"
REPO_URL = f"https://github.com/{USERNAME}/{USERNAME}"
STATE_PATH = Path("data/fsck/state.json")
STATS_PATH = Path("data/fsck/stats.json")
ONELINERS_PATH = Path("scripts/data/oneliners.txt")
TILE_DIR = "assets/fsck/tiles"

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
SMART_ROWS = 6
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
    """Strip markdown-dangerous characters from untrusted text and cap its length."""
    return re.sub(r"[\[\]<>`|]", "", text or "").strip()[:60]


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


# --- README rendering -------------------------------------------------------


def issue_url(title: str, body: str = "") -> str:
    url = f"{REPO_URL}/issues/new?title={quote_plus(title)}"
    if body:
        url += f"&body={quote_plus(body)}"
    return url


def tile_img(name: str, alt: str) -> str:
    return f'<img src="{TILE_DIR}/{name}.svg" width="22" height="22" alt="{alt}">'


def scan_link(cell: str) -> str:
    url = issue_url(f"artemis|fsck|{cell}", SCAN_BODY.format(cell=cell))
    return f"[{tile_img('hidden', cell)}]({url})"


def reformat_url() -> str:
    return issue_url("artemis|fsck|reformat", REFORMAT_BODY)


def render_cell(state: dict, cell: str, mines: set[str] | None) -> str:
    status = state["status"]
    revealed = state["revealed"]
    if status == "active":
        if cell in revealed:
            return tile_img(f"c{revealed[cell]}", str(revealed[cell]))
        return scan_link(cell)
    # Dead board (panicked or cleaned): everything is face-up, nothing is clickable.
    mines = mines or set()
    if cell in mines:
        if status == "panicked" and cell == state.get("panic_cell"):
            return tile_img("panic", "corrupted sector")
        return tile_img("mine-dim", "corrupted sector (dormant)")
    if cell in revealed:
        return tile_img(f"c{revealed[cell]}", str(revealed[cell]))
    return tile_img(f"c{adjacency(cell, mines)}", str(adjacency(cell, mines)))


def render_board(state: dict, salt: str) -> str:
    mines = board_mines(state, salt) if state["status"] != "active" else None
    lines = [
        "| | " + " | ".join(f"**{col}**" for col in COLS) + " |",
        "|:-:|" + ":-:|" * len(COLS),
    ]
    for row in ROWS:
        cells = " | ".join(render_cell(state, f"{col}{row}", mines) for col in COLS)
        lines.append(f"| **{row}** | {cells} |")
    return "\n".join(lines)


def render_alert(state: dict) -> str:
    board = state["board_number"]
    done = len(state["revealed"])
    if state["status"] == "panicked":
        cell = state.get("panic_cell") or "??"
        return (
            "> [!CAUTION]\n"
            f"> **KERNEL PANIC** — sector {cell} was corrupted and somebody scanned it anyway. "
            f"board #{board} is lost at {done}/{CLEAN_TOTAL} sectors verified. "
            f"[requisition a fresh disk]({reformat_url()}) to reformat."
        )
    if state["status"] == "cleaned":
        return (
            "> [!NOTE]\n"
            f"> **fsck complete: `/dev/sda1` is CLEAN.** all {CLEAN_TOTAL} sectors of board #{board} verified. "
            "the machine remembers who did this. "
            f"[reformat and go again]({reformat_url()})."
        )
    return (
        "> [!WARNING]\n"
        f"> **filesystem check required.** {MINE_COUNT} corrupted sectors detected on `/dev/sda1` "
        f"(board #{board}, {done}/{CLEAN_TOTAL} verified). any operator may run `fsck` — "
        "click a sector below to scan it. scanning a corrupted sector panics the kernel."
    )


def render_smart_log(stats: dict) -> str:
    entries = list(reversed(stats.get("ops_log", [])))[:SMART_ROWS]
    if not entries:
        return "**S.M.A.R.T. log** — no operations recorded. the disk sits in silence."
    lines = [
        f"**S.M.A.R.T. log** — last {len(entries)} operation(s)",
        "",
        "| operator | op | result |",
        "|:--|:--|:--|",
    ]
    for entry in entries:
        login = sanitize_login(entry.get("login", ""))
        op = sanitize_fragment(entry.get("op", "?"))
        result = RESULT_LABELS.get(entry.get("result", ""), sanitize_fragment(entry.get("result", "?")))
        avatar = f'<img src="https://github.com/{login}.png?size=20" width="20" height="20" alt="">'
        lines.append(f"| {avatar} {login} | `{op}` | {result} |")
    return "\n".join(lines)


def top_users(stats: dict, key: str) -> list[tuple[str, int]]:
    ranked = [
        (sanitize_login(login), counts.get(key, 0))
        for login, counts in stats.get("users", {}).items()
        if counts.get(key, 0) > 0
    ]
    ranked.sort(key=lambda item: (-item[1], item[0]))
    return ranked[:HALL_ROWS]


def render_halls(stats: dict) -> str:
    fame = top_users(stats, "cleans")
    shame = top_users(stats, "panics")
    depth = max(len(fame), len(shame), 1)
    lines = [
        "| hall of fame — disks cleaned | hall of shame — kernel panics caused |",
        "|:--|:--|",
    ]
    vacant = "*(vacant)*"
    for i in range(depth):
        left = f"{i + 1}. {fame[i][0]} ×{fame[i][1]}" if i < len(fame) else vacant
        right = f"{i + 1}. {shame[i][0]} ×{shame[i][1]}" if i < len(shame) else vacant
        lines.append(f"| {left} | {right} |")
    return "\n".join(lines)


def render_fsck_block(state: dict, stats: dict, salt: str) -> str:
    latency = (
        "<sub>scans are handled by a single-threaded fsck daemon: submitting an issue queues your scan, "
        "the eyes reaction means ack, and the board redraws about a minute later. refresh gently.</sub>"
    )
    footer = f"<sub>ART3M1S accepts other commands. they are [not documented]({issue_url(SANDWICH_TITLE)}).</sub>"
    parts = [
        render_alert(state),
        render_board(state, salt),
        latency,
        render_smart_log(stats),
        render_halls(stats),
        footer,
    ]
    if not is_sealed(salt):
        parts.insert(3, (
            "<sub>disk encryption: none. the corruption map is technically derivable from source. "
            "the daemon believes in open source and in honor systems.</sub>"
        ))
    return "\n\n".join(parts)


def safe_replace(readme: str, start: str, end: str, content: str) -> None:
    """replace_block, but a missing README or missing markers is a warning, not a crash."""
    try:
        replace_block(readme, start, end, content)
    except (OSError, ValueError) as error:
        warn(f"skipped block update ({start}): {error}")


def render_readme(readme: str, state: dict, stats: dict, salt: str) -> None:
    safe_replace(readme, FSCK_START, FSCK_END, render_fsck_block(state, stats, salt))


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
    """Silently rotate the boot one-liner. Never surfaces in the reply."""
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
    wrapped = len(current) >= 2 and current.startswith("`") and current.endswith("`")
    choice = pick_oneliner(issue_number, current.strip("`"), lines)
    if choice is None:
        return
    safe_replace(readme, ONELINER_START, ONELINER_END, f"`{choice}`" if wrapped else choice)


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
        shown = sanitize_fragment(title) or "(empty)"
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

    # Sanitizers.
    assert sanitize_login("evil/../user<img>") == "eviluserimg"
    assert sanitize_login("") == "anonymous"
    assert sanitize_fragment("a[b]c<d>`e`|f") == "abcdef"

    # Button pool swap: deterministic per issue number, never repeats the current line.
    lines = load_oneliners()
    assert len(lines) >= 12, "oneliners.txt should ship with a full pool"
    assert all(len(line) <= 80 for line in lines)
    pick = pick_oneliner(20, lines[0], lines)
    assert pick is not None and pick != lines[0]
    assert pick == pick_oneliner(20, lines[0], lines)
    assert pick_oneliner(20, "not in pool", lines) in lines

    # Rendering: active board is clickable, dead boards are face-up.
    stats = empty_stats()
    record_op(stats, "tester", ["scans"], "fsck E5", "ok")
    active_block = render_fsck_block(state, stats, salt)
    assert "[!WARNING]" in active_block and "tiles/hidden.svg" in active_block
    assert "artemis%7Cfsck%7C" in active_block  # pipe is URL-encoded in prefill links
    assert "sudo+make+me+a+sandwich" in active_block or "sudo%20make%20me%20a%20sandwich" in active_block
    assert "disk encryption: none" not in active_block, "sealed salt must not show the wink"
    unsealed_block = render_fsck_block(state, stats, DEFAULT_SALT)
    assert "disk encryption: none" in unsealed_block

    panic_state = new_state(5, salt)
    panic_state, _ = apply_scan(panic_state, "A1", "tester", salt)
    panic_state, _ = apply_scan(panic_state, sorted(board_mines(panic_state, salt))[0], "tester", salt)
    panic_block = render_fsck_block(panic_state, stats, salt)
    assert panic_block.count("tiles/panic.svg") == 1
    assert panic_block.count("tiles/mine-dim.svg") == MINE_COUNT - 1
    assert "tiles/hidden.svg" not in panic_block and "[!CAUTION]" in panic_block

    clean_block = render_fsck_block(final, stats, salt)
    assert clean_block.count("tiles/mine-dim.svg") == MINE_COUNT
    assert "CLEAN" in clean_block and "tiles/hidden.svg" not in clean_block

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
    render_readme(args.readme, load_state(salt), load_stats(), salt)
    print("rendered fsck block", file=sys.stderr)


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

    p_render = sub.add_parser("render", help="re-render the README block from current state")
    p_render.add_argument("--readme", default="README.md")
    p_render.set_defaults(func=cmd_render)

    p_test = sub.add_parser("self-test", help="deterministic assertion suite")
    p_test.set_defaults(func=lambda _args: self_test())

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
