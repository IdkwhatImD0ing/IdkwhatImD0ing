"""Render the hero: ART3M1S reboots tianni, then re-attaches the tmux session.

Writes three SVGs (all drawn through scripts/phosphor.py):
  assets/hero.svg        desktop, dark, 846 wide, reboot-on-arrival animation
  assets/hero-light.svg  desktop, safe mode (light), no animation at all
  assets/hero-phone.svg  phone, dark, 360 wide, same reboot with a shorter POST

The session has four panes: 0 whoami (the name in dot matrix and the only
copy of the hackathon record on the page), 1 htop (the LLM daemon's process
table from assets/status.json), 2 clock-mode (time since you attached) and
3 journalctl -f (real events only: stargazers, fsck ops, the bot's own
commits, the MOTD, plus a few fixed jokes that never pretend to be events).

Motion contract: t=0 IS the finished session. At ~0.6s it jitters, the CRT
power-cycles (curtains whose default opacity is 0), the BIOS POSTs on the dark
tube, and at ~3.2s the panes re-attach. With reduced motion or a frozen
renderer you get the finished session and a `--:--` clock.

Boot program (seeded like the old gifos hero, so a SHA always boots the same
way): 1-in-8 kernel_panic, else standard / memtest+ / scramble.

Every input is optional: missing data drops a journal line or falls back to
seed values. All three SVGs render in memory first; files are written only if
every render succeeded, and only when they changed.

Run from the repo root:
    python scripts/render_hero.py                      # write all three SVGs
    python scripts/render_hero.py --dry-run            # print the plan, write nothing
    python scripts/render_hero.py --program kernel_panic --out-dir .preview/hero/out
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import subprocess
import textwrap
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import phosphor as ph
from update_currently_building import (
    FALLBACK_MOTD,
    FALLBACK_OBSESSION,
    SEED_PROCESSES,
    clean_obsession,
    clean_processes,
    fit_motd,
    stable_pid,
)

USERNAME = "IdkwhatImD0ing"
REPO = "IdkwhatImD0ing/IdkwhatImD0ing"
STATUS_PATH = Path("assets/status.json")
FSCK_STATS = Path("data/fsck/stats.json")
FSCK_STATE = Path("data/fsck/state.json")
OUT_DIR = Path("assets")

ACCOUNT_CREATED = datetime(2021, 9, 21, tzinfo=timezone.utc)
WON, ENTERED = 35, 58
TAGLINE = "AI-first builder · hackathon operator · ships fast"
STACK = "ts python react fastapi pg"
MEMORY_MB = 98304  # 2x48GB Dominator Platinum: the POST fallback without a token

BOOT_PROGRAMS = ("standard", "memtest+", "scramble")
PROGRAMS = BOOT_PROGRAMS + ("kernel_panic",)
PANIC_ODDS = 8  # kernel_panic fires on exactly 1-in-8 seeds
PANIC_TRACE = (
    "KERNEL PANIC: caffeine buffer underrun in module sleep.ko",
    "Call trace:",
    "  at hackathon.sleep() -- not implemented",
    "  at demo.rehearse(skipped=True)",
    "  at scope.creep(features=+3) 12 min before judging",
    "  at bill.estimate_time(actual=x3)",
    "end trace: state dumped to /dev/hackathons",
)

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
SAFE_LOGIN = re.compile(r"[^A-Za-z0-9-]")
SAFE_CELL = re.compile(r"^[A-I][1-9]$")
BUILD_SUBJECT = re.compile(r"^artemis-build (\d{1,9}):")

# tmux clock-mode font, verbatim from tmux/clock.c (plus a dash for "--:--").
CLOCK_FONT = {
    "0": ("11111", "10001", "10001", "10001", "11111"),
    "1": ("00001", "00001", "00001", "00001", "00001"),
    "2": ("11111", "00001", "11111", "10000", "11111"),
    "3": ("11111", "00001", "11111", "00001", "11111"),
    "4": ("10001", "10001", "11111", "00001", "00001"),
    "5": ("11111", "10000", "11111", "00001", "11111"),
    "6": ("11111", "10000", "11111", "10001", "11111"),
    "7": ("11111", "00001", "00001", "00001", "00001"),
    "8": ("11111", "10001", "11111", "10001", "11111"),
    "9": ("11111", "10001", "11111", "00001", "11111"),
    ":": ("00000", "00100", "00000", "00100", "00000"),
    "-": ("00000", "00000", "11111", "00000", "00000"),
}

# --- the reboot timeline (seconds after the image loads) ---------------------------
T_JIT = 0.58      # the session jitters
T_OFF = 0.74      # CRT power-off: the picture collapses toward a line
T_DARK = 0.86     # tube fully dark
T_HOLD = 0.90     # attach-time elements go dark underneath from here
T_POST = 1.12     # first POST line
ATTACH = 3.20     # curtains open, panes re-attach (memtest+ and panic run later)
T_OPEN = 0.12     # how long the picture takes to re-expand


# ================================================================================
# inputs
# ================================================================================


@dataclass
class Entry:
    """One journal line: `Mon DD unit: message`."""
    when: datetime | None
    unit: str
    msg: str
    cls: str = "fg"
    unit_cls: str = "acc"
    label: str = ""  # replaces the date column ("now")


@dataclass
class Inputs:
    now: datetime
    seed: int
    seed_label: str
    seed_source: str
    program: str
    stamp: str
    obsession: str
    motd: str
    processes: list[dict]
    status_updated: datetime | None
    contributions: int | None
    stargazer: tuple[str, datetime] | None
    fsck: list[Entry] = field(default_factory=list)
    builds: list[tuple[int, datetime]] = field(default_factory=list)  # newest first
    notes: list[str] = field(default_factory=list)

    @property
    def panic(self) -> bool:
        return self.program == "kernel_panic"


def parse_utc(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def local_now() -> datetime:
    """The weekly seed follows Bill's week (America/Los_Angeles) when tzdata exists."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Los_Angeles"))
    except Exception:
        return datetime.now(timezone.utc)


def derive_seed() -> tuple[int, str, str]:
    """(seed, label, source): GITHUB_SHA's first 8 hex, else ISO year*100+week."""
    sha = os.environ.get("GITHUB_SHA", "")
    if re.fullmatch(r"[0-9a-fA-F]{8,40}", sha):
        return int(sha[:8], 16), sha[:7].lower(), "GITHUB_SHA"
    year, week, _ = local_now().isocalendar()
    return year * 100 + week, f"{year}-W{week:02d}", "iso-week"


def pick_program(seed: int) -> str:
    rng = random.Random(seed)
    if rng.randrange(PANIC_ODDS) == 0:
        return "kernel_panic"
    return rng.choice(BOOT_PROGRAMS)


def git(*args: str) -> str:
    try:
        result = subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8",
                                errors="replace", timeout=20, check=False)
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout if result.returncode == 0 else ""


def build_stamp() -> str:
    sha = os.environ.get("GITHUB_SHA", "")
    if re.fullmatch(r"[0-9a-fA-F]{7,40}", sha):
        return sha[:7].lower()
    head = git("rev-parse", "--short=7", "HEAD").strip()
    return head if re.fullmatch(r"[0-9a-f]{7,12}", head) else "local"


def build_commits(limit: int = 2) -> list[tuple[int, datetime]]:
    """Newest `artemis-build N:` commits (the LLM daemon's twice-weekly self-rewrite),
    newest first. A shallow clone just yields fewer (or none)."""
    found: list[tuple[int, datetime]] = []
    for line in git("log", "-n", "400", "--format=%cI%x1f%s").splitlines():
        stamp, _, subject = line.partition("\x1f")
        match = BUILD_SUBJECT.match(subject)
        when = parse_utc(stamp)
        if match and when:
            found.append((int(match.group(1)), when))
            if len(found) == limit:
                break
    return found


def read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def read_status(path: Path, notes: list[str]) -> tuple[str, str, list[dict], datetime | None, int | None]:
    data = read_json(path)
    if not isinstance(data, dict):
        notes.append(f"{path} unreadable; using seed values")
        data = {}
    obsession = clean_obsession(str(data.get("obsession", ""))) or FALLBACK_OBSESSION
    motd = fit_motd(str(data.get("motd", ""))) or FALLBACK_MOTD
    raw = data.get("processes")
    processes = clean_processes(raw if isinstance(raw, list) else [])
    if len(processes) < 3:
        notes.append("status.json has fewer than 3 processes; topping up with seed processes")
        have = {p["command"] for p in processes}
        processes += [p for p in clean_processes(list(SEED_PROCESSES)) if p["command"] not in have]
        processes = sorted(processes, key=lambda p: -p["cpu"])[:4]
    build = data.get("build")
    if not (isinstance(build, int) and not isinstance(build, bool) and 0 < build < 10**9):
        build = None
    return obsession, motd, processes, parse_utc(data.get("updated")), build


def request_json(url: str, token: str, accept: str = "application/vnd.github+json",
                 body: dict | None = None) -> object:
    headers = {
        "Accept": accept,
        "User-Agent": "github-profile-readme-hero",
        "X-GitHub-Api-Version": "2022-11-28",
        "Authorization": f"Bearer {token}",
    }
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_contributions(token: str) -> int | None:
    """Commit contributions (public + private) over the last year: the POST memory test."""
    query = ("query($login: String!) { user(login: $login) { contributionsCollection {"
             " totalCommitContributions restrictedContributionsCount } } }")
    try:
        data = request_json("https://api.github.com/graphql", token,
                            body={"query": query, "variables": {"login": USERNAME}})
        coll = data["data"]["user"]["contributionsCollection"]  # type: ignore[index]
        total = int(coll["totalCommitContributions"]) + int(coll["restrictedContributionsCount"])
    except Exception as error:
        print(f"WARNING: contribution count unavailable: {error}")
        return None
    return total if 0 < total < 10**7 else None


def fetch_newest_stargazer(token: str) -> tuple[str, datetime] | None:
    """star+json (with starred_at) 401s without auth, so this only runs with a token."""
    try:
        repo = request_json(f"https://api.github.com/repos/{REPO}", token)
        total = int(repo.get("stargazers_count", 0))  # type: ignore[union-attr]
        if total < 1:
            return None
        page = (total + 99) // 100
        batch = request_json(f"https://api.github.com/repos/{REPO}/stargazers?per_page=100&page={page}",
                             token, accept="application/vnd.github.star+json")
        entry = batch[-1]  # type: ignore[index]
        login = SAFE_LOGIN.sub("", str(entry["user"]["login"]))[:39]
        when = parse_utc(entry.get("starred_at"))
    except Exception as error:
        print(f"WARNING: stargazers unavailable: {error}")
        return None
    return (login, when) if login and when else None


def fsck_entries() -> list[Entry]:
    """The last three real fsck ops (scans, panics, cleans, reformats, button
    presses), so the journal tells the story that led to the current board."""
    stats = read_json(FSCK_STATS)
    state = read_json(FSCK_STATE)
    log = stats.get("ops_log") if isinstance(stats, dict) else None
    if not isinstance(log, list):
        return []
    ops = [op for op in log if isinstance(op, dict)]
    board = state.get("board_number") if isinstance(state, dict) else None
    notable = [i for i, op in enumerate(ops) if op.get("result") in ("panic", "clean", "reformat")]
    # the latest notable op plus what led up to it (or any scan/press since): the last 3 real ops
    story = [i for i, op in enumerate(ops) if op.get("result") in ("ok", "panic", "clean", "reformat", "press")]
    picks = story[-3:]

    entries = []
    for i in picks:
        op = ops[i]
        when = parse_utc(op.get("utc"))
        if not when:
            continue
        login = SAFE_LOGIN.sub("", str(op.get("login", "")))[:39] or "someone"
        cell = str(op.get("op", "")).replace("fsck", "").strip().upper()
        cell = cell if SAFE_CELL.match(cell) else ""
        result = op.get("result")
        if result == "panic" and cell:
            entries.append(Entry(when, "fsck", f"{cell} KERNEL PANIC", cls="red"))
        elif result == "clean":
            entries.append(Entry(when, "fsck", f"/dev/sda1 clean. {login} did that."))
        elif result == "reformat":
            if isinstance(board, int) and not isinstance(board, bool) and notable and i == notable[-1]:
                # the newest reformat is the one that brought up the current board
                entries.append(Entry(when, "mkfs", f"board #{board} online, 10 corrupt"))
            else:
                entries.append(Entry(when, "mkfs", "/dev/sda1 reformatted"))
        elif result == "ok" and cell:
            entries.append(Entry(when, "fsck", f"{cell} verified by {login}"))
        elif result == "press":
            entries.append(Entry(when, "button", f"{login} pressed it. nothing happened."))
    return entries


def gather(program: str | None, status_path: Path, offline: bool) -> Inputs:
    notes: list[str] = []
    now = datetime.now(timezone.utc)
    seed, seed_label, seed_source = derive_seed()
    obsession, motd, processes, updated, status_build = read_status(status_path, notes)
    token = "" if offline else os.environ.get("GITHUB_TOKEN", "")
    if not token:
        notes.append("no GITHUB_TOKEN: skipping the stargazer and contribution lookups")
    inp = Inputs(
        now=now, seed=seed, seed_label=seed_label, seed_source=seed_source,
        program=program or pick_program(seed), stamp=build_stamp(),
        obsession=obsession, motd=motd, processes=processes, status_updated=updated,
        contributions=fetch_contributions(token) if token else None,
        stargazer=fetch_newest_stargazer(token) if token else None,
        notes=notes,
    )
    inp.fsck = fsck_entries()
    builds = build_commits(2)
    # status.json is written before the bot commits, so it can be one build ahead of git log.
    if status_build and updated and (not builds or status_build > builds[0][0]):
        builds = [(status_build, updated)] + builds[:1]
    inp.builds = builds
    return inp


# ================================================================================
# the journal
# ================================================================================


def journal(inp: Inputs, safe: bool) -> list[Entry]:
    """Dated events oldest first, then this render's own lines (safe mode: the
    safe-mode jokes instead), then the visitor."""
    dated: list[Entry] = []
    if inp.stargazer:
        login, when = inp.stargazer
        dated.append(Entry(when, "passwd", f"{login} created an account"))
    dated += inp.fsck
    for i, (number, when) in enumerate(reversed(inp.builds)):
        again = " again." if i or len(inp.builds) == 1 else ""
        dated.append(Entry(when, f"cron[{number}]", "rewrote own bio." + again))
    if inp.motd and inp.status_updated:  # no timestamp, no event: never date a fallback as news
        dated.append(Entry(inp.status_updated, "motd", inp.motd))
    dated.sort(key=lambda e: e.when or inp.now)
    panic: list[Entry] = []
    if inp.panic:
        panic.append(Entry(inp.now, "kernel", "panic in sleep.ko. recovered. mostly.", cls="red", unit_cls="red"))

    def visitor(msg: str) -> Entry:
        return Entry(None, "tty2", f"1 visitor attached. {msg}", cls="warn", unit_cls="warn!", label="now")

    if safe:
        # Safe mode never POSTs, so the jokes replace this render's own lines (the boot
        # line, and the F3 CTA the F-key bar repeats right below): every real event fits.
        return dated + panic + [
            Entry(inp.now, "video", "LIGHT MODE detected. phosphor integrity: compromised.", cls="warn"),
            Entry(inp.now, "hint", "the real BIOS only POSTs in the dark.", cls="warn"),
            visitor("squinting."),
        ]
    boot = Entry(inp.now, "boot", f"POST re-rendered, seed {inp.seed_label}")
    postfix = Entry(inp.now, "postfix", "port 25 open. building something weird? F3.")
    return dated + [boot] + panic + [postfix, visitor("hello, you.")]


def balanced_wrap(text: str, width: int) -> list[str]:
    """textwrap, except a two-line wrap is split as evenly as possible (no widows)."""
    chunks = textwrap.wrap(text, width, break_long_words=True) or [""]
    if len(chunks) != 2:
        return chunks
    words = text.split()
    splits = []
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        if len(a) <= width and len(b) <= width and len(a) >= len(b):
            splits.append((len(a) - len(b), a, b))
    return list(min(splits)[1:]) if splits else chunks


def entry_rows(e: Entry, width: int) -> list[list[tuple[str, str]]]:
    """Wrap one entry to `width` columns; continuation lines hang under the message."""
    date = e.label or (f"{MONTHS[e.when.month - 1]} {e.when.day:2d}" if e.when else "")
    prefix = f"{e.unit}: "
    indent = 7 + len(prefix)
    chunks = balanced_wrap(e.msg, max(width - indent, 8))
    rows = [[(f"{date:<7}", "mu"), (prefix, e.unit_cls), (chunks[0], e.cls)]]
    rows += [[(" " * indent, "mu"), (chunk, e.cls)] for chunk in chunks[1:]]
    return rows


def fit_journal(entries: list[Entry], width: int, max_rows: int, keep_tail: int,
                cursor_row: bool = True) -> list[list[list[tuple[str, str]]]]:
    """Drop the oldest entries until everything (plus the cursor row) fits."""
    entries = list(entries)
    while entries:
        wrapped = [entry_rows(e, width) for e in entries]
        if sum(len(w) for w in wrapped) + cursor_row <= max_rows or len(entries) <= keep_tail:
            return wrapped
        entries.pop(0)
    return []


# ================================================================================
# drawing helpers (candidates for phosphor.py)
# ================================================================================


def n(v: float) -> str:
    return ph.fmt(round(v, 2) if isinstance(v, float) else v)


def secs(v: float) -> str:
    return f"{v:.3f}".rstrip("0").rstrip(".") + "s"


class Motion:
    """Emits the animation attributes. Off (safe mode) = every helper returns ''.

    Timing travels as CSS custom properties so each animated element costs a few
    bytes: .rv (dark under the CRT, then flick in at --t), .hk (dark until the
    hold ends), .pl (hidden except for a window of --w seconds starting at --t),
    .sc (one scramble frame at --t). Every class's un-animated style is the
    final frame, except .pl/.sc which only exist during the boot.
    """

    def __init__(self, on: bool):
        self.on = on

    def style(self, *anims: tuple[str, float, float, str]) -> str:
        if not self.on:
            return ""
        parts = ",".join(f"{name} {secs(dur)} {timing} {secs(delay)}" for name, dur, delay, timing in anims)
        return f' style="animation:{parts}"'

    def reveal(self, t: float, dur: float | None = None) -> str:
        if not self.on:
            return ""
        extra = f";--d:{secs(dur)}" if dur else ""
        return f' class="rv" style="--h:{secs(t - T_HOLD)};--t:{secs(t)}{extra}"'

    def dark_until(self, t: float) -> str:
        return f' class="hk" style="--h:{secs(t - T_HOLD)}"' if self.on else ""

    def window(self, t0: float, t1: float) -> str:
        if not self.on:
            return ""
        return f' class="pl" style="--t:{secs(t0)};--w:{secs(t1 - t0)}"'


def css_animations() -> str:
    """Keyframes and timing classes shared by the animated (dark) heroes."""
    hold = secs(T_HOLD)
    return (
        ".pl,.ov,.bl,.sc{opacity:0}"
        f".rv{{animation:wbhold var(--h) linear {hold},wbflick var(--d,.22s) linear var(--t)}}"
        f".hk{{animation:wbhold var(--h) linear {hold}}}"
        ".pl{animation:wbshow var(--w) steps(1) var(--t)}"
        ".sc{animation:wbshow .07s steps(1) var(--t)}"
        "@keyframes wbhold{from,to{opacity:0}}"
        "@keyframes wbshow{from,to{opacity:1}}"
        "@keyframes wbflick{0%{opacity:0}16%{opacity:1}30%{opacity:.12}48%{opacity:1}66%{opacity:.45}100%{opacity:1}}"
        "@keyframes wbjit{0%{transform:translate(6px,0)}17%{transform:translate(-5px,1px)}"
        "34%{transform:translate(3px,-1px) skewX(-3deg)}51%{transform:translate(-7px,0)}"
        "68%{transform:translate(4px,1px) skewX(2deg)}85%{transform:translate(-2px,0)}100%{transform:none}}"
        "@keyframes wbsq{from{transform:scaleY(1)}to{transform:scaleY(.004)}}"
        "@keyframes wbunsq{from{transform:scaleY(.004)}to{transform:scaleY(1)}}"
        "@keyframes wbloff{0%{opacity:1;transform:scaleX(1)}55%{opacity:1;transform:scaleX(.012)}"
        "100%{opacity:0;transform:scaleX(.012)}}"
        "@keyframes wblon{0%{opacity:1;transform:scaleX(.012)}100%{opacity:1;transform:scaleX(1)}}"
        "@keyframes wbtype{from{transform:translateX(0)}}"
        "@keyframes wbfl{0%,58%{opacity:1}59%,100%{opacity:.18}}"
        ".fl{animation:wbfl 1.7s steps(1) infinite}"
        ".sess,.bl{transform-box:fill-box;transform-origin:50% 50%}"
        ".ovt{transform-box:fill-box;transform-origin:50% 0}"
        ".ovb{transform-box:fill-box;transform-origin:50% 100%}"
    )


def crt_css(attach: float) -> str:
    """Curtains: close T_OFF..T_DARK, hold, open attach..attach+T_OPEN."""
    total = attach + T_OPEN - T_OFF
    shut = (T_DARK - T_OFF) / total * 100
    reopen = (attach - T_OFF) / total * 100
    frames = (f"0%{{opacity:1;transform:scaleY(0)}}{shut:.2f}%{{opacity:1;transform:scaleY(1)}}"
              f"{reopen:.2f}%{{opacity:1;transform:scaleY(1)}}100%{{opacity:1;transform:scaleY(0)}}")
    return (f"@keyframes wbcrt{{{frames}}}"
            f".ovt,.ovb{{animation:wbcrt {secs(total)} cubic-bezier(.6,0,.4,1) {secs(T_OFF)}}}")


def session_style(motion: Motion, attach: float) -> str:
    """Jitter, collapse to a line, and (after the POST) expand back."""
    return motion.style(("wbjit", 0.15, T_JIT, "steps(1)"), ("wbsq", T_DARK - T_OFF, T_OFF, "ease-in"),
                        ("wbunsq", T_OPEN, attach, "ease-out"))


def cell_d(x: float, y: float, w: float, h: float | None = None) -> str:
    return f"M{n(x)} {n(y)}h{n(w)}v{n(w if h is None else h)}h-{n(w)}z"


def dots_d(cells: list[tuple[float, float]], size: float) -> str:
    return "".join(cell_d(x, y, size) for x, y in cells)


def glyph_cells(ch: str, x: float, y: float, px: float, lit: bool = True,
                tear_rows: tuple[int, ...] = (), tear: float = 0.0) -> list[tuple[float, float]]:
    rows = ph.GLYPHS.get(ch.upper(), ph.GLYPHS[" "])
    out = []
    for ry, row in enumerate(rows):
        dx = tear if (lit and ry in tear_rows) else 0.0
        for rx, bit in enumerate(row):
            if (bit == "#") == lit:
                out.append((x + rx * px + dx, y + ry * px))
    return out


def moon_paths(cx: float, cy: float, r: int, px: float, illum: float, waxing: bool,
               lit: str = "acc", limb: str = "accd", dark: str = "gh") -> str:
    """A pixel disc with an elliptical terminator (tonight's real phase), drawn as
    one path per class instead of one rect per pixel."""
    groups: dict[str, list[str]] = {lit: [], limb: [], dark: []}
    k = 1 - 2 * illum
    for gy in range(-r, r + 1):
        for gx in range(-r, r + 1):
            x, y = (gx + 0.5) / (r + 0.5), (gy + 0.5) / (r + 0.5)
            if x * x + y * y > 1:
                continue
            half = math.sqrt(max(0.0, 1 - y * y))
            on = (x if waxing else -x) > k * half
            cls = (limb if x * x + y * y > 0.62 else lit) if on else dark
            groups[cls].append(cell_d(cx + gx * px, cy + gy * px, px - 1))
    return "".join(f'<path class="{cls}" d="{"".join(d)}"/>' for cls, d in groups.items() if d)


def right_runs(x_right: float, y: float, parts: list[tuple[str, str]], size: float = ph.SIZE) -> str:
    total = sum(len(s) for s, _ in parts)
    return ph.runs(x_right - total * ph.CW * size, y, parts, size)


def fit_command(command: str, flags: str, width: int) -> tuple[str, str]:
    """Drop whole trailing flags until `command flags` fits; never cut mid-word."""
    words = flags.split()
    while words and len(command) + 1 + len(" ".join(words)) > width:
        words.pop()
    return command[:width], " ".join(words)


def clock_defs(pw: float, pixel_h: float, cell_w: float, cell_h: float) -> str:
    ids = {":": "ckc", "-": "ckd"}
    out = []
    for key, rows in CLOCK_FONT.items():
        d = "".join(cell_d(c * pw, r * pixel_h, cell_w, cell_h)
                    for r, row in enumerate(rows) for c, bit in enumerate(row) if bit == "1")
        out.append(f'<path id="{ids.get(key, "ck" + key)}" d="{d}"/>')
    return "".join(out)


def clock_face(x0: float, y0: float, pw: float, pixel_h: float, animated: bool) -> tuple[str, str]:
    """mm:ss since the image loaded, as CSS steps() digit strips. Returns (svg, css).
    Reduced motion (or safe mode) shows `--:--`."""
    gh = 5 * pixel_h
    step = gh + 24
    adv = 6 * pw
    dashes = "".join(f'<use href="#{g}" x="{n(x0 + i * adv)}" y="{n(y0)}"/>'
                     for i, g in enumerate(("ckd", "ckd", "ckc", "ckd", "ckd")))
    if not animated:
        return f'<g class="acc">{dashes}</g>', ""
    body, css = [], []
    for i, pos in enumerate((("m10", 6, 3600), ("m1", 10, 600), None, ("s10", 6, 60), ("s1", 10, 10))):
        x = x0 + i * adv
        if pos is None:
            body.append(f'<use href="#ckc" x="{n(x)}" y="{n(y0)}"/>')
            continue
        name, count, period = pos
        body.append(f'<clipPath id="cl{name}"><rect x="{n(x - 1)}" y="{n(y0 - 1)}" '
                    f'width="{n(adv)}" height="{n(gh + 2)}"/></clipPath>')
        strip = "".join(f'<use href="#ck{k}" x="{n(x)}" y="{n(y0 + k * step)}"/>' for k in range(count))
        body.append(f'<g clip-path="url(#cl{name})"><g class="ck{name}">{strip}</g></g>')
        css.append(f".ck{name}{{animation:ph{name} {period}s steps({count},end) infinite}}"
                   f"@keyframes ph{name}{{to{{transform:translateY(-{n(count * step)}px)}}}}")
    css.append(".clkrm{display:none}"
               "@media (prefers-reduced-motion: reduce){.clk{display:none}.clkrm{display:inline}}")
    return (f'<g class="acc glow clk">{"".join(body)}</g><g class="acc glow clkrm">{dashes}</g>', "".join(css))


# ================================================================================
# the POST (dark heroes only)
# ================================================================================


@dataclass
class Post:
    rows: list[tuple[float, list[tuple[str, str]]]]      # (time shown, parts); [] = blank row
    count: tuple[int, float, float, str] | None          # (row, t0, t1, label) of the memory test
    type_row: int                                        # the `tmux attach` row, -1 in panic
    type_at: float
    end: float                                           # the POST screen clears
    panic_rows: list[tuple[float, list[tuple[str, str]], bool]]  # (t, parts, is_bar)
    attach: float


def post_script(inp: Inputs, phone: bool) -> Post:
    memtest = inp.program == "memtest+"
    t = T_POST
    rows: list[tuple[float, list[tuple[str, str]]]] = []

    def add(parts: list[tuple[str, str]], dt: float = 0.06) -> None:
        nonlocal t
        rows.append((t, parts))
        t += dt if parts else 0.0

    if phone:
        add([("ART3M1S Modular BIOS v2.8.04", "acc!")])
        add([("(C) 2021-2026, Bill Zhang Labs", "acc")])
        add([(f"{ph.MACHINE}  build ", "acc"), (inp.stamp, "fg")], 0.1)
        add([])
        add([("CPU  ", "acc"), ("AMD Ryzen 7 9800X3D", "fg")])
        add([("GPU  ", "acc"), ("ROG Astral RTX 5080 White", "fg")])
        label = "Mem  "
    else:
        add([("ART3M1S Modular BIOS v2.8.04", "acc!"), (", an Energy Drink Ally", "acc")])
        add([("Copyright (C) 2021-2026, Bill Zhang Labs", "acc")])
        add([(f"{ph.MACHINE}   build ", "acc"), (inp.stamp, "fg")], 0.1)
        add([])
        add([("Main Processor : ", "acc"), ("AMD Ryzen 7 9800X3D", "fg")])
        add([("Graphics       : ", "acc"), ("ASUS ROG Astral RTX 5080 White", "fg")])
        label = "Memory Test    : "
    count = (len(rows), t, t + 0.42, label)
    rows.append((t, [(label, "acc")]))
    t += 0.5
    if memtest:
        if phone:
            add([("/dev/hackathons: ", "acc"), (f"{WON} of {ENTERED} flagged TROPHY", "fg")], 0.12)
        else:
            add([("/dev/hackathons: ", "acc"), (f"{ENTERED} volumes scanned, {WON} flagged TROPHY", "fg")], 0.12)
    add([])
    lead = 30 if phone else 36
    if not phone:
        add([(" Bus Dev  Device" + " " * (lead - 12) + "Status", "mu")], 0.08)
    devices = (("heaven defying bead", "bound to bill", "acc"),
               ("voice clone interface", "online", "acc"),
               ("cold brew controller", "draining", "fg"),
               ("sleep.ko", "NOT FOUND", "warn!"))
    last = len(devices) - 1
    for i, (dev, status, cls) in enumerate(devices):
        bus = "" if phone else (f" 00  0{i}   " if i < last else " 01  00   ")
        add([(bus, "mu"), (dev + " ", "fg"), ("." * (lead - len(dev) - 2) + " ", "mu"), (status, cls)],
            0.08 if i < last else 0.12)
    if inp.panic:
        end = t + 0.06
        pt = end
        width = 46 if phone else 100
        panic_rows: list[tuple[float, list[tuple[str, str]], bool]] = []
        for chunk in textwrap.wrap(PANIC_TRACE[0], width):
            panic_rows.append((pt, [(chunk, "ink!")], True))
        pt += 0.12
        panic_rows.append((pt, [], False))
        for line in PANIC_TRACE[1:]:
            pieces = [line]
            if len(line) > width:
                pieces = textwrap.wrap(line, width, subsequent_indent="       ")
            for piece in pieces:
                panic_rows.append((pt, [(piece, "red")], False))
            pt += 0.06
        panic_rows.append((pt, [], False))
        pt += 0.14
        panic_rows.append((pt, [("rebooting...", "warn!")], False))
        return Post(rows, count, -1, 0.0, end, panic_rows, pt + 0.42)
    add([])
    type_row = len(rows)
    rows.append((t + 0.1, []))
    type_at = t + 0.16
    attach = max(ATTACH, type_at + 0.36 + 0.18)
    return Post(rows, count, type_row, type_at, attach, [], attach)


def post_layer(inp: Inputs, width: float, height: float, x0: float, y0: float, lh: float,
               size: float, motion: Motion, phone: bool) -> tuple[str, str, float]:
    """The CRT: curtains, the collapsing line, the POST text and scanlines on top.
    Returns (svg, css, attach time)."""
    script = post_script(inp, phone)
    cw = ph.CW * size
    attach = script.attach
    half = height / 2
    out = ['<g clip-path="url(#tube)">',
           f'<rect class="cv ov ovt" x="0" y="0" width="{n(width)}" height="{n(half + 1)}"/>',
           f'<rect class="cv ov ovb" x="0" y="{n(half - 1)}" width="{n(width)}" height="{n(half + 1)}"/>',
           # the picture collapsing into a line, then a dot (and the reverse on attach)
           f'<rect class="acct bl glow" x="8" y="{n(half - 1.5)}" width="{n(width - 16)}" height="3"'
           + motion.style(("wbloff", 0.3, T_DARK - 0.03, "ease-in"), ("wblon", 0.16, attach - 0.15, "ease-out"))
           + "/>",
           # scanlines on the dark tube, under the text so the POST stays crisp
           f'<rect x="0" y="0" width="{n(width)}" height="{n(height)}" fill="url(#scan)"'
           + motion.window(T_DARK, attach) + "/>"]

    text = ['<g class="glow">']
    unfiltered: list[str] = []
    # BIOS logo corner: tonight's moon (ART3M1S is a moon program)
    illum, waxing, _ = ph.moon_phase(inp.now)
    mr, mpx = (6, 3) if phone else (10, 4)
    mx = width - x0 - (mr + 0.5) * mpx - (4 if phone else 30)
    my = y0 - size + 2 + (mr + 0.5) * mpx
    logo = moon_paths(mx - mpx / 2, my - mpx / 2, mr, mpx, illum, waxing)
    if not phone:
        logo += ph.text(mx, my + (mr + 0.5) * mpx + 18, "SLEEP PREVENTER", "acc", 11, anchor="middle", bold=True)
    text.append(f"<g{motion.window(T_POST, script.end)}>{logo}</g>")
    for i, (t, parts) in enumerate(script.rows):
        if parts:
            text.append(f"<g{motion.window(t, script.end)}>{ph.runs(x0, y0 + i * lh, parts, size)}</g>")
    # memory test, counting up (to the year's contributions when the API answered)
    if script.count:
        row, t0, t1, label = script.count
        y = y0 + row * lh
        total = inp.contributions or MEMORY_MB
        unit = " contributions" if inp.contributions else " MB"
        vx = x0 + len(label) * cw
        steps = 12
        for k in range(steps):
            a, b = t0 + k * (t1 - t0) / steps, t0 + (k + 1) * (t1 - t0) / steps
            value = int(total * (k + 1) / (steps + 1))
            text.append(f"<g{motion.window(a, b)}>{ph.text(vx, y, f'{value:>{len(str(total))}}{unit}', 'fg', size)}</g>")
        text.append(f"<g{motion.window(t1, script.end)}>"
                    + ph.runs(vx, y, [(f"{total}{unit} ", "fg"), ("OK", "fg!")], size) + "</g>")
    # the typed command: a canvas-coloured cover slides right in steps; the cursor rides its edge
    if script.type_row >= 0:
        y = y0 + script.type_row * lh
        prompt = "$ " if phone else ph.PROMPT
        cmd = f"tmux attach -t {ph.HOST}"
        tw = len(cmd) * cw
        tx = x0 + len(prompt) * cw
        typer = (f'<g transform="translate({n(tw)} 0)"'
                 + motion.style(("wbtype", 0.36, script.type_at, f"steps({len(cmd)},end) backwards"))
                 + f'><rect class="cv" x="{n(tx)}" y="{n(y - size)}" width="{n(tw + cw + 2)}" height="{n(size * 1.5)}"/>'
                 f'<rect fill="url(#scan)" x="{n(tx)}" y="{n(y - size)}" width="{n(tw + cw + 2)}" height="{n(size * 1.5)}"/>'
                 f'<rect class="acc" x="{n(tx)}" y="{n(y - size + 2)}" width="{n(cw)}" height="{n(size + 1)}"/></g>')
        shown = motion.window(script.rows[script.type_row][0], script.end)
        text.append(f"<g{shown}>" + ph.runs(x0, y, [(prompt, "acc!"), (cmd, "fg")], size) + "</g>")
        unfiltered.append(f"<g{shown}>{typer}</g>")  # outside the glow: a blurred cover would show
    # the BIOS footer (bottom of the tube, like every POST screen of the 90s)
    stamp = inp.now.strftime("%m/%d/%y" if phone else "%m/%d/%Y")
    board = f"B850A-{ph.HOST.upper()}" if phone else f"B850A-{ph.HOST.upper()}-5080"  # ROG Strix B850-A
    footer = [[("Press ", "mu"), ("DEL", "fg!"), (" to enter SETUP", "mu")]
              + ([] if phone else [(", ", "mu"), ("ESC", "fg!"), (" to skip memory test", "mu")]),
              [(f"{stamp}-{board}-{inp.stamp[:4].upper()}", "mu")]]
    fy = height - 16 - lh
    text.append(f"<g{motion.window(T_POST + 0.02, script.end)}>"
                + "".join(ph.runs(x0, fy + j * lh, parts, size) for j, parts in enumerate(footer)) + "</g>")
    # kernel panic: the screen clears and the trace prints from the top
    for i, (t, parts, bar) in enumerate(script.panic_rows):
        if not parts:
            continue
        y = y0 + i * lh
        chunk = ph.runs(x0, y, parts, size)
        if bar:
            chunk = (f'<rect class="red" x="{n(x0 - 6)}" y="{n(y - size - 2)}" '
                     f'width="{n(len(parts[0][0]) * cw + 12)}" height="{n(size + 7)}"/>') + chunk
        if parts[0][1].startswith("warn"):
            chunk = f'<g class="blink">{chunk}</g>'
        text.append(f"<g{motion.window(t, attach)}>{chunk}</g>")
    text.append("</g>")
    out += text + unfiltered
    out.append("</g>")
    return "".join(out), crt_css(attach), attach


def tube_defs(width: float, height: float) -> str:
    return (f'<clipPath id="tube"><rect x="0" y="0" width="{n(width)}" height="{n(height)}" rx="6"/></clipPath>'
            '<pattern id="scan" width="8" height="3" patternUnits="userSpaceOnUse">'
            '<rect x="0" y="0" width="8" height="1" class="klo" opacity=".5"/></pattern>')


# ================================================================================
# panes
# ================================================================================


def name_block(words: list[tuple[str, float, float]], px: float, motion: Motion, inp: Inputs,
               attach: float, cursor_at: tuple[float, float], stagger: float = 0.03) -> tuple[str, str]:
    """Dot-matrix name. Unlit dots are always on; each lit glyph flickers in on
    attach (scramble: cycles through junk glyphs first). A lit 5x7 block is the
    cursor. words = [(text, x, y)]. Returns (svg, defs)."""
    dot = px - 1
    tear_rows = (2, 3) if inp.panic else ()
    tear = 5.0 if inp.panic else 0.0
    unlit: list[tuple[float, float]] = []
    glyphs: list[tuple[str, float, float]] = []
    for word, x, y in words:
        for i, ch in enumerate(word):
            if ch != " ":
                gx = x + i * 6 * px
                unlit += glyph_cells(ch, gx, y, px, lit=False)
                glyphs.append((ch, gx, y))
    out = [f'<path class="gh" d="{dots_d(unlit, dot)}"/>', '<g class="acc glow">']
    t0 = attach + 0.1
    defs = ""
    last = t0 + len(glyphs) * stagger
    if inp.program == "scramble" and motion.on:
        rng = random.Random(inp.seed ^ 0x5CA1AB1E)
        pool = "ABCDEFGHJKLMNOPQRSTUVWXYZ0123456789%/"
        used: set[str] = set()
        alts = []
        for k, (ch, gx, gy) in enumerate(glyphs):
            count = 6 + k
            for i in range(count):
                alt = rng.choice(pool.replace(ch, ""))
                used.add(alt)
                alts.append(f'<use href="#sg{ord(alt)}" x="{n(gx)}" y="{n(gy)}" class="sc" '
                            f'style="--t:{secs(t0 + i * 0.07)}"/>')
            reveal = t0 + count * 0.07
            last = max(last, reveal)
            cells = glyph_cells(ch, gx, gy, px, tear_rows=tear_rows, tear=tear)
            out.append(f'<path d="{dots_d(cells, dot)}"{motion.reveal(reveal, 0.2)}/>')
        out += alts
        defs = "".join(f'<path id="sg{ord(c)}" d="{dots_d(glyph_cells(c, 0, 0, px), dot)}"/>' for c in sorted(used))
    else:
        for k, (ch, gx, gy) in enumerate(glyphs):
            cells = glyph_cells(ch, gx, gy, px, tear_rows=tear_rows, tear=tear)
            out.append(f'<path d="{dots_d(cells, dot)}"{motion.reveal(t0 + k * stagger, 0.2)}/>')
    cx, cy = cursor_at
    block = [(cx + c * px, cy + r * px) for r in range(7) for c in range(5)]
    blink = ' class="blink"' if motion.on else ""
    out.append(f'<g{motion.reveal(last + 0.05, 0.12)}><path{blink} d="{dots_d(block, dot)}"/></g>')
    out.append("</g>")
    return "".join(out), defs


def hackathon_meter(x: float, y: float, cell: float, gap: float, height: float, per_row: int,
                    motion: Motion, attach: float) -> str:
    """/dev/hackathons: one cell per event entered, lit if won. Fills up on attach."""
    per_row = per_row or ENTERED
    cells = [(x + (i % per_row) * (cell + gap), y + (i // per_row) * (height + 3)) for i in range(ENTERED)]
    off = "".join(cell_d(cx, cy, cell, height) for cx, cy in cells[WON:])
    out = [f'<path class="tr" d="{off}"/>', '<g class="acc glow">']
    if motion.on:
        out += [f'<path d="{cell_d(cx, cy, cell, height)}"{motion.dark_until(attach + 0.16 + i * 0.009)}/>'
                for i, (cx, cy) in enumerate(cells[:WON])]
    else:
        out.append(f'<path d="{"".join(cell_d(cx, cy, cell, height) for cx, cy in cells[:WON])}"/>')
    out.append("</g>")
    return "".join(out)


def htop_cols(size: float, show_pid: bool) -> tuple[int, int, int, int, float, float]:
    """(cpu, '[', ']', command) columns plus segment width/gap, shared by header and rows."""
    cw = ph.CW * size
    seg_w = 3
    seg_gap = (6 * cw - 10 * seg_w - 1) / 9  # ten segments fill the 6 columns between [ and ]
    cpu = 6 if show_pid else 0
    open_ = cpu + 4
    close = open_ + 7
    return cpu, open_, close, close + 2, seg_w, seg_gap


def htop_header(x0: float, y: float, size: float, show_pid: bool) -> str:
    cpu, _, _, cmd, _, _ = htop_cols(size, show_pid)
    parts = [("  PID ", "acc!")] if show_pid else []
    parts += [("CPU%", "acc!"), (" " * (cmd - cpu - 4), "acc"), ("COMMAND", "acc!")]
    return ph.runs(x0, y, parts, size)


def htop_rows(x0: float, y0: float, lh: float, size: float, procs: list[dict], width_chars: int,
              motion: Motion, show_pid: bool = True) -> str:
    """PID, CPU%, a 10-segment meter (its top segments flicker) and the command."""
    cw = ph.CW * size
    col, open_col, close_col, cmd_col, seg_w, seg_gap = htop_cols(size, show_pid)
    out = []
    for k, proc in enumerate(procs):
        y = y0 + k * lh
        cpu = int(proc["cpu"])
        lit = max(1, min(10, int(cpu / 10 + 0.5)))  # half-up: round() would draw 75 and 85 the same
        if show_pid:
            out.append(ph.text(x0, y, f"{stable_pid(proc['command']):>5}", "mu", size))
        out.append(ph.text(x0 + col * cw, y, f"{cpu:>3}", "fg", size, bold=True))
        mx = x0 + open_col * cw
        out.append(ph.text(mx, y, "[", "mu", size))
        on, off, flick = [], [], []
        for i in range(10):
            d = cell_d(mx + cw + 0.5 + i * (seg_w + seg_gap), y - size * 0.8, seg_w, size * 0.92)
            if i >= lit:
                off.append(d)
            elif i >= lit - 2 and motion.on:
                flick.append(f'<path class="acc fl" d="{d}" style="animation-delay:{secs(0.23 * i + 0.41 * k)}"/>')
            else:
                on.append(d)
        out.append(f'<path class="tr" d="{"".join(off)}"/>' if off else "")
        out.append(f'<g class="glow"><path class="acc" d="{"".join(on)}"/>{"".join(flick)}</g>')
        out.append(ph.text(x0 + close_col * cw, y, "]", "mu", size))
        command, flags = fit_command(proc["command"], proc["flags"], width_chars - cmd_col)
        out.append(ph.runs(x0 + cmd_col * cw, y, [(command, "fg!"), (" " + flags if flags else "", "mu")], size))
    return "".join(out)


def journal_rows(x0: float, y0: float, lh: float, size: float, wrapped: list[list[list[tuple[str, str]]]],
                 motion: Motion, attach: float, cursor_inline: bool = False) -> str:
    """Entries tail in one by one after attach; `hello, you.` lands last, then the cursor."""
    out = []
    row = 0
    for k, rows in enumerate(wrapped):
        is_tail = k == len(wrapped) - 1
        t = attach + 0.75 if is_tail else attach + 0.2 + k * 0.05
        body = "".join(ph.runs(x0, y0 + (row + j) * lh, parts, size) for j, parts in enumerate(rows))
        out.append(f"<g{motion.reveal(t, 0.3 if is_tail else 0.16)}>{body}</g>")
        row += len(rows)
    cw = ph.CW * size
    if cursor_inline and wrapped:
        cx = x0 + (sum(len(s) for s, _ in wrapped[-1][-1]) + 1) * cw
        cy = y0 + (row - 1) * lh
    else:
        cx, cy = x0, y0 + row * lh
    cls = "acc blink" if motion.on else "acc"
    out.append(f'<g{motion.reveal(attach + 0.95, 0.1)}><rect class="{cls}" x="{n(cx)}" '
               f'y="{n(cy - size + 1)}" width="{n(cw)}" height="{n(size + 2)}"/></g>')
    return "".join(out)


def uptime(now: datetime) -> str:
    months = (now.year - ACCOUNT_CREATED.year) * 12 + (now.month - ACCOUNT_CREATED.month)
    if now.day < ACCOUNT_CREATED.day:
        months -= 1
    years, months = divmod(max(months, 0), 12)
    return f"{years}y {months}m, since {ACCOUNT_CREATED:%Y-%m-%d}"


def moon_text(now: datetime) -> tuple[str, float, bool]:
    illum, waxing, name = ph.moon_phase(now)
    return f"{name}, {round(illum * 100)}% lit", illum, waxing


def clip_words(text: str, width: int) -> str:
    """Cut at the last word boundary that fits, so a long value never leaves its pane."""
    if len(text) <= width:
        return text
    head = text[:width + 1]
    cut = head.rsplit(" ", 1)[0] if " " in head.strip() else text[:width]
    return cut.rstrip(" ,;:-")


def about_rows(inp: Inputs, width: int) -> tuple[list[tuple[str, str, str]], float, bool, str]:
    """(label, value, class) rows under the name; values are fitted to `width` - 8 columns."""
    mtext, illum, waxing = moon_text(inp.now)
    rows = [("now", inp.obsession, "acc"), ("uptime", uptime(inp.now), "fg"),
            ("moon", mtext, "fg"), ("stack", STACK, "fg")]
    return [(key, clip_words(value, width - 8), cls) for key, value, cls in rows], illum, waxing, mtext


# ================================================================================
# desktop: 846 wide, four panes
# ================================================================================

W = ph.W
PY = 38          # panel top: 28px status bar + 10px of air
XS = 464         # vertical split
YA = 318         # left split (whoami / htop)
YC = 206         # right split (clock / journal)
H = 526


def desktop(inp: Inputs, mode: str) -> str:
    safe = mode == "light"
    motion = Motion(not safe)
    size = ph.SIZE
    cw = ph.CW * size
    lh = ph.LINE
    x0 = 16
    css: list[str] = []
    defs: list[str] = []
    post_svg, attach = "", ATTACH
    if motion.on:
        post_svg, post_css, attach = post_layer(inp, W, H, 24, 40, lh, size, motion, phone=False)
        css += [css_animations(), post_css]
        defs.append(tube_defs(W, H))

    s: list[str] = []
    bar = ph.status_bar(0, W, right="" if inp.panic else "load: 3 concurrent demos")
    if inp.panic:  # a panic boot: the status line admits it, in amber
        bar += ph.text(W - 10, 14 + ph.SIZE_CHROME * 0.35, '"kernel panic on last boot"', "warn", ph.SIZE_CHROME,
                       anchor="end", bold=True)
    s.append(f"<g{motion.reveal(attach + 0.02, 0.2)}>{bar}</g>")
    s.append(ph.panel(0, PY, W, H - PY))

    # --- 0 whoami ------------------------------------------------------------------------
    p0 = [ph.pane_title(0, XS, PY + 14, "0 whoami", f"bill@{ph.HOST}"),
          ph.runs(x0, PY + 42, [("$ ", "acc!"), ("whoami", "fg")], size)]
    px = 7
    name_y = PY + 54
    zx = x0 + (4 * 6 - 1 + 3) * px            # BILL, then a 3-dot thin space
    name_svg, sdefs = name_block([("BILL", x0, name_y), ("ZHANG", zx, name_y)], px, motion, inp, attach,
                                 cursor_at=(zx + 5 * 6 * px, name_y))
    defs.append(sdefs)
    p0.append(name_svg)
    p0.append(ph.text(x0, PY + 128, TAGLINE, "fg", size))
    meter_w = ENTERED * 5 + (ENTERED - 1) * 2
    p0.append(ph.text(x0, PY + 160, "/dev/hackathons", "mu", size))
    p0.append(right_runs(x0 + meter_w, PY + 160, [(f"{WON} won", "acc!"), (f" / {ENTERED} entered · ", "fg"),
                                                  (f"{round(100 * WON / ENTERED)}%", "fg")], size))
    p0.append(hackathon_meter(x0, PY + 169, 5, 2, 11, 0, motion, attach))
    pane_chars = int((XS - 16 - x0) // cw)
    rows, illum, waxing, mtext = about_rows(inp, pane_chars)
    ry = PY + 206
    for k, (key, value, cls) in enumerate(rows):
        row = ph.runs(x0, ry + k * lh, [(f"{key:<8}", "mu"), (value, cls)], size)
        if key == "moon":
            row += moon_paths(x0 + (8 + len(mtext) + 2) * cw + 2, ry + k * lh - 5, 3, 3, illum, waxing)
        p0.append(f"<g{motion.reveal(attach + 0.3 + k * 0.05, 0.16)}>{row}</g>")
    s.append(f"<g{motion.reveal(attach + 0.04, 0.24)}>{''.join(p0)}</g>")

    # --- 1 htop --------------------------------------------------------------------------
    procs = inp.processes[:4]
    p1 = [ph.pane_title(0, XS, YA + 14, "1 htop", f"{len(procs)} tasks, {WON} won")]
    hy = YA + 27
    p1.append(f'<rect x="1" y="{hy}" width="{XS - 2}" height="20" class="tr"/>')
    p1.append(htop_header(x0, hy + 14.5, size, show_pid=True))
    p1.append(htop_rows(x0, hy + 42, lh, size, procs, pane_chars, motion))
    fy = hy + 42 + len(procs) * lh + 8
    foot = [[("load average: ", "mu"), ("3 concurrent demos", "fg")],
            [("last login:   ", "mu"), ("from a hackathon venue", "fg")],
            [("sleep:        ", "mu"), ("not installed (optional dep)", "warn")]]
    p1 += [ph.runs(x0, fy + j * lh, parts, size) for j, parts in enumerate(foot)]
    s.append(f"<g{motion.reveal(attach + 0.08, 0.24)}>{''.join(p1)}</g>")

    # --- 2 clock-mode ----------------------------------------------------------------------
    p2 = [ph.pane_title(XS, W, PY + 14, "2 clock-mode", "tty2")]
    pw, pixel_h = 9, 14
    defs.append(clock_defs(pw, pixel_h, pw - 1.5, pixel_h - 1.5))
    mid = XS + (W - XS) / 2
    face, clock_css = clock_face(mid - (29 * pw - 1.5) / 2, PY + 36, pw, pixel_h, animated=motion.on)
    css.append(clock_css)
    p2.append(face)
    caption = (("clock disabled in safe mode", "the daemon is not judging. it is squinting.") if safe
               else ("^ time since you attached", "the daemon is not judging. it is timing."))
    p2.append(ph.text(mid, PY + 136, caption[0], "fg", size, anchor="middle"))
    p2.append(ph.text(mid, PY + 156, caption[1], "mu", size, anchor="middle"))
    s.append(f"<g{motion.reveal(attach + 0.06, 0.24)}>{''.join(p2)}</g>")

    # --- 3 journalctl -f (the active pane) ------------------------------------------------------
    p3 = [ph.pane_title(XS, W, YC + 14, "3 journalctl -f", "artemis", active=True)]
    jx = XS + 16
    jy = YC + 42
    max_rows = int((H - 14 - jy) // lh) + 1
    wrapped = fit_journal(journal(inp, safe), int((W - 16 - jx) // cw), max_rows, keep_tail=3 if safe else 1)
    p3.append(journal_rows(jx, jy, lh, size, wrapped, motion, attach))
    s.append(f"<g{motion.reveal(attach + 0.1, 0.24)}>{''.join(p3)}</g>")
    # tmux paints the border next to the active pane in the active colour
    s.append(ph.vline(XS, PY, YC + 14, "ln") + ph.vline(XS, YC + 14, H, "acc-s"))

    session = "".join(s)
    if motion.on:
        session = f'<g class="sess"{session_style(motion, attach)}>{session}</g>'
    return ph.svg(W, H, session + post_svg, describe(inp, safe), mode,
                  extra_css="".join(css), defs="".join(defs))


# ================================================================================
# phone: 360 wide, panes stacked
# ================================================================================

WP = ph.WP


def phone(inp: Inputs) -> str:
    motion = Motion(True)
    size = 12
    cw = ph.CW * size
    lh = 18
    x0 = 14
    width_chars = int((WP - 2 * x0) // cw)
    css: list[str] = [css_animations()]
    defs: list[str] = []
    attach = post_script(inp, phone=True).attach
    s: list[str] = []
    panes: list[str] = []

    # --- 0 whoami: BILL over ZHANG, bigger dots -----------------------------------------------
    y = 38
    p0 = [ph.pane_title(0, WP, y + 14, "0 whoami", f"bill@{ph.HOST}", size=11),
          ph.runs(x0, y + 38, [("$ ", "acc!"), ("whoami", "fg")], size)]
    px = 9
    bill_y = y + 50
    zhang_y = bill_y + 8 * px
    name_svg, sdefs = name_block([("BILL", x0, bill_y), ("ZHANG", x0, zhang_y)], px, motion, inp, attach,
                                 cursor_at=(x0 + 5 * 6 * px, zhang_y), stagger=0.035)
    defs.append(sdefs)
    p0.append(name_svg)
    y = zhang_y + 7 * px + 18
    p0.append(ph.text(x0, y, "AI-first builder · hackathon operator ·", "fg", size))
    p0.append(ph.text(x0, y + lh, "ships fast", "fg", size))
    y += lh + 26
    cell, gap = 9, 2.5
    meter_w = 29 * cell + 28 * gap
    p0.append(ph.text(x0, y, "/dev/hackathons", "mu", size))
    p0.append(right_runs(x0 + meter_w, y, [(f"{WON} won", "acc!"), (f" / {ENTERED} · ", "fg"),
                                           (f"{round(100 * WON / ENTERED)}%", "fg")], size))
    p0.append(hackathon_meter(x0, y + 8, cell, gap, 9, 29, motion, attach))
    y += 8 + 2 * 9 + 3 + 22
    rows, illum, waxing, mtext = about_rows(inp, width_chars)
    for k, (key, value, cls) in enumerate(rows):
        row = ph.runs(x0, y + k * lh, [(f"{key:<8}", "mu"), (value, cls)], size)
        if key == "moon":
            row += moon_paths(x0 + (8 + len(mtext) + 2) * cw + 2, y + k * lh - 4.5, 3, 3, illum, waxing)
        p0.append(f"<g{motion.reveal(attach + 0.3 + k * 0.05, 0.16)}>{row}</g>")
    y += 3 * lh + 14
    panes.append(f"<g{motion.reveal(attach + 0.04, 0.24)}>{''.join(p0)}</g>")

    # --- 2 clock-mode: digits left, caption right --------------------------------------------------
    pw, pixel_h = 6, 9
    p2 = [ph.pane_title(0, WP, y + 14, "2 clock-mode", "tty2", size=11)]
    defs.append(clock_defs(pw, pixel_h, pw - 1, pixel_h - 1))
    face, clock_css = clock_face(x0 + 2, y + 32, pw, pixel_h, animated=True)
    css.append(clock_css)
    p2.append(face)
    cap_x = x0 + 2 + 29 * pw + 20
    p2.append(ph.text(cap_x, y + 32 + 18, "< time since", "fg", size))  # the clock is beside it here
    p2.append(ph.text(cap_x, y + 32 + 18 + lh, "you attached", "fg", size))
    y += 32 + 5 * pixel_h + 18
    panes.append(f"<g{motion.reveal(attach + 0.06, 0.24)}>{''.join(p2)}</g>")

    # --- 1 htop: 3 procs, no PID column --------------------------------------------------------------
    procs = inp.processes[:3]
    p1 = [ph.pane_title(0, WP, y + 14, "1 htop", f"{len(procs)} tasks, {WON} won", size=11)]
    hy = y + 26
    p1.append(f'<rect x="1" y="{hy}" width="{WP - 2}" height="18" class="tr"/>')
    p1.append(htop_header(x0, hy + 13, size, show_pid=False))
    p1.append(htop_rows(x0, hy + 36, lh, size, procs, width_chars, motion, show_pid=False))
    y = hy + 36 + len(procs) * lh + 2
    p1.append(ph.runs(x0, y, [("sleep: ", "mu"), ("not installed (optional dep)", "warn")], size))
    y += 14
    panes.append(f"<g{motion.reveal(attach + 0.08, 0.24)}>{''.join(p1)}</g>")

    # --- 3 journalctl -f (active): the last 4 events + hello, you -----------------------------------------
    p3 = [ph.pane_title(0, WP, y + 14, "3 journalctl -f", "artemis", active=True, size=11)]
    jy = y + 40
    entries = journal(inp, safe=False)
    recent = [e for e in entries[:-1] if e.unit != "postfix"][-4:]
    wrapped = fit_journal(recent + entries[-1:], width_chars, 6, keep_tail=1, cursor_row=False)
    p3.append(journal_rows(x0, jy, lh, size, wrapped, motion, attach, cursor_inline=True))
    panes.append(f"<g{motion.reveal(attach + 0.1, 0.24)}>{''.join(p3)}</g>")
    height = int(jy + (sum(len(w) for w in wrapped) - 1) * lh + 16)

    post_svg, post_css, _ = post_layer(inp, WP, height, x0 + 2, 42, lh, size, motion, phone=True)
    css.append(post_css)
    defs.append(tube_defs(WP, height))
    s.append(f"<g{motion.reveal(attach + 0.02, 0.2)}>{ph.status_bar(0, WP, compact=True, size=11)}</g>")
    s.append(ph.panel(0, 38, WP, height - 38))
    s += panes
    session = f'<g class="sess"{session_style(motion, attach)}>{"".join(s)}</g>'
    return ph.svg(WP, height, session + post_svg, describe(inp, safe=False), "dark",
                  extra_css="".join(css), defs="".join(defs))


# ================================================================================
# words (the accessible description carries the same facts as the picture)
# ================================================================================


def describe(inp: Inputs, safe: bool) -> str:
    procs = "; ".join(f"{p['command']} {p['flags']}".strip() + f" at {p['cpu']}% CPU" for p in inp.processes)
    moon, _, _ = moon_text(inp.now)
    if safe:
        boot = "Safe mode: the light theme gets the session without the boot animation."
    else:
        boot = ("On load the screen power-cycles like a CRT, the ART3M1S BIOS runs its POST"
                + (" and hits a kernel panic (caffeine buffer underrun in sleep.ko)" if inp.panic else "")
                + ", then the tmux session re-attaches.")
    events = []
    for e in journal(inp, safe):
        date = e.label or (f"{MONTHS[e.when.month - 1]} {e.when.day}" if e.when else "")
        events.append(f"{date} {e.unit}: {e.msg}")
    return (
        f"tmux session on {ph.HOST}, the machine that renders Bill Zhang's GitHub profile. {boot} "
        f"Pane whoami: BILL ZHANG in a dot-matrix font. {TAGLINE.replace(' · ', ', ')}. "
        f"/dev/hackathons: {WON} won of {ENTERED} entered ({round(100 * WON / ENTERED)}%). "
        f"Now: {inp.obsession}. Uptime {uptime(inp.now)}. Moon: {moon}. "
        "Stack: TypeScript, Python, React, FastAPI, Postgres. "
        f"Pane htop: {procs}. Load average: 3 concurrent demos. Sleep: not installed. "
        "Pane clock-mode: "
        + ("disabled in safe mode. " if safe else "counts the minutes and seconds since you arrived. ")
        + "Pane journal: " + " / ".join(events).rstrip(".") + "."
    )


# ================================================================================
# main
# ================================================================================


def render_all(inp: Inputs) -> dict[str, str]:
    return {
        "hero.svg": desktop(inp, "dark"),
        "hero-light.svg": desktop(inp, "light"),
        "hero-phone.svg": phone(inp),
    }


def dry_run(inp: Inputs) -> None:
    print(f"seed={inp.seed} label={inp.seed_label} (source={inp.seed_source})")
    print(f"boot_program={inp.program}  stamp={inp.stamp}")
    print(f"obsession={inp.obsession!r}")
    print(f"motd={inp.motd!r}")
    for p in inp.processes:
        print(f"  pid={stable_pid(p['command'])} cpu={p['cpu']:>2}  {p['command']} {p['flags']}")
    print(f"contributions={inp.contributions}  newest_stargazer={inp.stargazer}")
    print(f"builds={[(num, w.date().isoformat()) for num, w in inp.builds]}  fsck_events={len(inp.fsck)}")
    for note in inp.notes:
        print(f"note: {note}")
    for safe in (False, True):
        print(f"--- journal, {'safe mode' if safe else 'dark'} (before fitting to the pane) ---")
        for e in journal(inp, safe):
            for row in entry_rows(e, 44):
                print("  " + "".join(s for s, _ in row))


def main() -> None:
    parser = argparse.ArgumentParser(description="Render the ART3M1S hero SVGs.")
    parser.add_argument("--dry-run", action="store_true", help="print seed, program, inputs and journal; write nothing")
    parser.add_argument("--program", choices=PROGRAMS, help="force a boot program (testing)")
    parser.add_argument("--out-dir", default=str(OUT_DIR), help="where to write the SVGs (testing)")
    parser.add_argument("--status", default=str(STATUS_PATH), help="status.json to read (testing)")
    parser.add_argument("--offline", action="store_true", help="skip every network lookup")
    args = parser.parse_args()

    try:
        inp = gather(args.program, Path(args.status), args.offline)
        if args.dry_run:
            dry_run(inp)
            return
        rendered = render_all(inp)
        for content in rendered.values():
            ET.fromstring(content)  # all three parse, or nothing is written
    except Exception as error:  # a bad day must never take the hero down
        print(f"WARNING: hero render failed ({type(error).__name__}: {error}); keeping the old files")
        return
    out = Path(args.out_dir)
    for name, content in rendered.items():
        try:
            changed = ph.write_svg(out / name, content)
        except (ValueError, OSError) as error:
            print(f"WARNING: {name}: {error}")
            continue
        size_kb = len(content.encode("utf-8")) / 1024
        print(f"{(out / name).as_posix()}: {size_kb:.1f} KB{'' if changed else ' (unchanged)'}")
    print(f"hero: program={inp.program} seed={inp.seed_label}")


if __name__ == "__main__":
    main()
