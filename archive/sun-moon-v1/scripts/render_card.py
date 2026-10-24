"""Render the Heart-Mirror card and the Mission Hall board (replaces render_hero.py).

Writes six SVGs, all drawn through scripts/ink.py:
  assets/mirror/card.svg, card-light.svg, card-phone.svg
      心镜台, the Heart-Mirror Terrace: a bronze heart-mirror holding tonight's
      real moon, the name and its red seal, and the facts: what the Sect
      Leader is cultivating, the arena record, when he joined, the moon,
      his tools and (with a token) a year of contributions, the same total
      GitHub shows on the profile. With a token, a ridge of mountains along
      the bottom is drawn from that calendar's last 52 weeks. No data, no
      ridge: never a fake one. The moon is read for 21:00 on Bill's calendar
      day, so every render on one day agrees.
  assets/hall/board.svg, board-light.svg, board-phone.svg
      任务殿, the Mission Hall: the missions the steward (an LLM) posted from
      assets/status.json, its note, the notices (real events only, oldest
      first), and one stick of incense that burns down while you read.

The weekly omen (seeded by Bill's ISO week, so every redraw in a week agrees):
1-in-8 qi_deviation (走火入魔: a danger notice, and the seal cracks), else
clear, mist (a band of mist drifts over the card, dark only) or meteor (one
meteor crosses the card's sky on load, dark only).

Every input is optional. Everything renders in memory first; files are
written only if all six parse, and only when they changed. Any failure warns
and exits 0. Run from the repo root:
    python scripts/render_card.py                 # write the six SVGs
    python scripts/render_card.py --dry-run       # print the inputs, write nothing
    python scripts/render_card.py --omen qi_deviation --out-dir .preview/card --offline
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import ink
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

TITLE = "Software Engineer II, Pinterest"
FOCUS = "LLM agent systems · voice-first AI · San Francisco"
TOOLS = "TypeScript · Python · React · FastAPI · Postgres"

OMENS = ("clear", "mist", "meteor")
ALL_OMENS = OMENS + ("qi_deviation",)
DEVIATION_ODDS = 8
STEWARD_SUBJECT = re.compile(r"^(?:artemis-build|steward) (\d{1,9}):")
SAFE_LOGIN = re.compile(r"[^A-Za-z0-9-]")
SAFE_CELL = re.compile(r"^[A-I][1-9]$")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


# =====================================================================================
# inputs
# =====================================================================================


@dataclass
class Notice:
    """One line on the notice board: `Mon DD unit: message`."""
    when: datetime | None
    unit: str
    msg: str
    cls: str = "tx"
    unit_cls: str = "au"
    label: str = ""   # replaces the date ("now")


@dataclass
class Inputs:
    now: datetime
    seed: int
    week: str
    omen: str
    obsession: str
    motd: str
    processes: list[dict]
    status_updated: datetime | None
    commits: int | None = None
    weeks: list[int] = field(default_factory=list)   # 52 weekly contribution totals, oldest first
    stargazer: tuple[str, datetime] | None = None
    formation: list[Notice] = field(default_factory=list)
    stewards: list[tuple[int, datetime]] = field(default_factory=list)  # newest first
    notes: list[str] = field(default_factory=list)


def parse_utc(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def pick_omen(seed: int) -> str:
    rng = random.Random(seed)
    if rng.randrange(DEVIATION_ODDS) == 0:
        return "qi_deviation"
    return rng.choice(OMENS)


def git(*args: str) -> str:
    try:
        result = subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8",
                                errors="replace", timeout=20, check=False)
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout if result.returncode == 0 else ""


def steward_commits(limit: int = 2) -> list[tuple[int, datetime]]:
    """The newest steward rewrites (`steward N:`, or the old `artemis-build N:`)."""
    found: list[tuple[int, datetime]] = []
    for line in git("log", "-n", "400", "--format=%cI%x1f%s").splitlines():
        stamp, _, subject = line.partition("\x1f")
        match = STEWARD_SUBJECT.match(subject)
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


def drawable(s: str, face: str = "body") -> str:
    """Text from outside (the LLM, logins) loses any character the glyph
    tables cannot draw, instead of sinking the whole render."""
    out = []
    for ch in s:
        try:
            ink.check(ch, face)
            out.append(ch)
        except ink.MissingGlyph:
            continue
    return re.sub(r"\s+", " ", "".join(out)).strip()


def read_status(path: Path, notes: list[str]) -> tuple[str, str, list[dict], datetime | None]:
    data = read_json(path)
    if not isinstance(data, dict):
        notes.append(f"{path} unreadable; the steward's standing missions are posted instead")
        data = {}
    obsession = drawable(clean_obsession(str(data.get("obsession", "")))) or FALLBACK_OBSESSION
    motd = drawable(fit_motd(str(data.get("motd", "")))) or FALLBACK_MOTD
    raw = data.get("processes")
    processes = clean_processes(raw if isinstance(raw, list) else [])
    if len(processes) < 3:
        notes.append("fewer than 3 missions in status.json; topping up with the standing missions")
        have = {p["command"] for p in processes}
        processes += [p for p in clean_processes(list(SEED_PROCESSES)) if p["command"] not in have]
        processes = sorted(processes, key=lambda p: -p["cpu"])[:4]
    for p in processes:
        p["command"] = drawable(p["command"], "mono") or "mission"
        p["flags"] = drawable(p["flags"], "mono")
    return obsession, motd, processes, parse_utc(data.get("updated"))


def request_json(url: str, token: str, accept: str = "application/vnd.github+json",
                 body: dict | None = None) -> object:
    headers = {"Accept": accept, "User-Agent": "sun-moon-sect-moon-watch",
               "X-GitHub-Api-Version": "2022-11-28", "Authorization": f"Bearer {token}"}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_practice(token: str) -> tuple[int | None, list[int]]:
    """(contributions in the last year, 52 weekly contribution totals oldest
    first). Both come from the one contribution calendar, so the total is the
    number on the GitHub profile and agrees with the ridge."""
    query = ("query($login: String!) { user(login: $login) { contributionsCollection {"
             " contributionCalendar { totalContributions"
             " weeks { contributionDays { contributionCount } } } } } }")
    try:
        data = request_json("https://api.github.com/graphql", token,
                            body={"query": query, "variables": {"login": USERNAME}})
        coll = data["data"]["user"]["contributionsCollection"]  # type: ignore[index]
        commits = int(coll["contributionCalendar"]["totalContributions"])
        weeks = [sum(int(d["contributionCount"]) for d in w["contributionDays"])
                 for w in coll["contributionCalendar"]["weeks"]]
    except Exception as error:
        print(f"WARNING: contributions unavailable: {error}")
        return None, []
    commits_ok = commits if 0 < commits < 10**7 else None
    weeks = [max(0, min(w, 10**5)) for w in weeks][-52:]
    return commits_ok, (weeks if len(weeks) >= 26 and any(weeks) else [])


def fetch_newest_stargazer(token: str) -> tuple[str, datetime] | None:
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


def formation_notices() -> list[Notice]:
    """The last three formation events (steps, backlashes, breaks, re-lays).
    Gong strikes are left out: the gong must never crowd the game out."""
    stats = read_json(FSCK_STATS)
    state = read_json(FSCK_STATE)
    log = stats.get("ops_log") if isinstance(stats, dict) else None
    if not isinstance(log, list):
        return []
    ops = [op for op in log if isinstance(op, dict)]
    board = state.get("board_number") if isinstance(state, dict) else None
    relays = [i for i, op in enumerate(ops) if op.get("result") == "reformat"]
    story = [i for i, op in enumerate(ops) if op.get("result") in ("ok", "panic", "clean", "reformat")]
    out = []
    for i in story[-3:]:
        op = ops[i]
        when = parse_utc(op.get("utc"))
        if not when:
            continue
        login = SAFE_LOGIN.sub("", str(op.get("login", "")))[:39] or "someone"
        cell = str(op.get("op", "")).replace("fsck", "").strip().upper()
        cell = cell if SAFE_CELL.match(cell) else ""
        result = op.get("result")
        if result == "panic" and cell:
            out.append(Notice(when, "formation", f"BACKLASH at {cell}", cls="dg", unit_cls="dg"))
        elif result == "clean":
            out.append(Notice(when, "formation", f"broken. {login} did that."))
        elif result == "reformat":
            if isinstance(board, int) and not isinstance(board, bool) and relays and i == relays[-1]:
                out.append(Notice(when, "formation", f"#{board} laid, 10 traps"))
            else:
                out.append(Notice(when, "formation", "re-laid by the elders"))
        elif result == "ok" and cell:
            out.append(Notice(when, "formation", f"{cell} read by {login}"))
    return out


def gather(omen: str | None, status_path: Path, offline: bool) -> Inputs:
    notes: list[str] = []
    seed, week = ink.week_seed()
    obsession, motd, processes, updated = read_status(status_path, notes)
    token = "" if offline else os.environ.get("GITHUB_TOKEN", "")
    if not token:
        notes.append("no GITHUB_TOKEN: no stargazer, no contribution count, no ridge")
    inp = Inputs(now=datetime.now(timezone.utc), seed=seed, week=week, omen=omen or pick_omen(seed),
                 obsession=obsession, motd=motd, processes=processes, status_updated=updated, notes=notes)
    if token:
        inp.commits, inp.weeks = fetch_practice(token)
        inp.stargazer = fetch_newest_stargazer(token)
    inp.formation = formation_notices()
    inp.stewards = steward_commits(2)
    return inp


# =====================================================================================
# words
# =====================================================================================


def joined(now: datetime) -> str:
    start = ink.ACCOUNT_CREATED
    months = (now.year - start.year) * 12 + (now.month - start.month) - (1 if now.day < start.day else 0)
    years, months = divmod(max(months, 0), 12)
    return f"{start:%Y-%m-%d}, {years}y {months}m in the sect"


def moon_time(now: datetime) -> datetime:
    """Tonight: 21:00 on Bill's calendar day (America/Los_Angeles, else UTC).
    Reading the moon at a fixed hour keeps two renders on one day identical."""
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("America/Los_Angeles")
    except Exception:
        tz = timezone.utc
    return now.astimezone(tz).replace(hour=21, minute=0, second=0, microsecond=0)


def moon_words(now: datetime) -> tuple[str, float, bool]:
    illum, waxing, name = ink.moon_phase(moon_time(now))
    return f"{name}, {round(illum * 100)}% lit", illum, waxing


def card_rows(inp: Inputs) -> list[tuple[str, str, str, str]]:
    """(chinese label, english gloss, value, value class)."""
    pct = round(100 * ink.WON / ink.ENTERED)
    rows = [("闭关", "cultivating", inp.obsession, "au"),
            ("论剑", "arena", f"{ink.WON} won of {ink.ENTERED} entered ({pct}%)", "tx"),
            ("入门", "joined", joined(inp.now), "tx"),
            ("月相", "moon", moon_words(inp.now)[0], "tx"),
            ("法宝", "tools", TOOLS, "tx")]
    if inp.commits:
        rows.append(("修为", "practice", f"{inp.commits:,} contributions in the last year", "tx"))
    return rows


def notices(inp: Inputs, light: bool) -> list[Notice]:
    """Real events oldest first, then this render's own lines, then the visitor."""
    dated: list[Notice] = []
    if inp.stargazer:
        login, when = inp.stargazer
        dated.append(Notice(when, "register", f"{login} was initiated, outer disciple"))
    dated += inp.formation
    for i, (number, when) in enumerate(reversed(inp.stewards)):
        again = " again." if i or len(inp.stewards) == 1 else ""
        dated.append(Notice(when, f"steward[{number}]", "reposted the missions." + again))
    dated.sort(key=lambda n: n.when or inp.now)
    omen = []
    if inp.omen == "qi_deviation":
        omen.append(Notice(inp.now, "omen", "qi deviation in the Sect Leader's meridians. recovered. mostly.",
                           cls="dg", unit_cls="dg"))
    if light:
        return dated + omen + [
            Notice(inp.now, "daylight", "the incense is not lit by day.", cls="mu"),
            Notice(inp.now, "hint", "the sect is best seen at night.", cls="mu"),
            Notice(None, "gate", "a visitor has arrived. squinting.", cls="jd", unit_cls="jd", label="now"),
        ]
    return dated + [Notice(inp.now, "moon-watch", f"the moon was read for {inp.week}")] + omen + [
        Notice(inp.now, "pigeons", "the loft is open. building something odd? 飞鸽."),
        Notice(None, "gate", "a visitor has arrived. greetings.", cls="jd", unit_cls="jd", label="now"),
    ]


def notice_date(n: Notice) -> str:
    return n.label or (f"{MONTHS[n.when.month - 1]} {n.when.day:02d}" if n.when else "")


# =====================================================================================
# drawing: the heart-mirror card
# =====================================================================================


def mirror(cx: float, cy: float, r: float, inp: Inputs, mode: str, uid: str) -> str:
    """A round bronze heart-mirror: a rim ticked with the 28 lunar mansions,
    and in its face tonight's moon."""
    _, illum, waxing = moon_words(inp.now)
    out = [f'<circle cx="{ink.fmt(cx)}" cy="{ink.fmt(cy)}" r="{ink.fmt(r)}" class="em" opacity="{".22" if mode == "dark" else ".3"}"/>',
           f'<circle cx="{ink.fmt(cx)}" cy="{ink.fmt(cy)}" r="{ink.fmt(r - 0.75)}" class="au-s" stroke-width="1.5"/>',
           f'<circle cx="{ink.fmt(cx)}" cy="{ink.fmt(cy)}" r="{ink.fmt(r * 0.86)}" class="{"bg" if mode == "dark" else "tk"}"/>',
           f'<circle cx="{ink.fmt(cx)}" cy="{ink.fmt(cy)}" r="{ink.fmt(r * 0.86)}" class="au-s" stroke-opacity=".6" stroke-width="1"/>']
    ticks = []
    for i in range(28):
        a = i / 28 * math.tau
        r0, r1 = r * (0.89 if i % 7 else 0.875), r * 0.965
        ticks.append(f"M{ink.fmt(cx + math.cos(a) * r0)} {ink.fmt(cy + math.sin(a) * r0)}"
                     f"L{ink.fmt(cx + math.cos(a) * r1)} {ink.fmt(cy + math.sin(a) * r1)}")
    out.append(f'<path d="{"".join(ticks)}" class="au-s" stroke-width="1.2" stroke-opacity=".75"/>')
    mr = r * 0.56
    if mode == "dark":
        out.append(f'<circle cx="{ink.fmt(cx)}" cy="{ink.fmt(cy)}" r="{ink.fmt(mr * 1.35)}" fill="url(#{uid}halo)"/>')
    out.append(ink.moon(cx, cy, mr, illum, waxing, mode, uid=uid))
    return "".join(out)


def halo_defs(uid: str, mode: str) -> str:
    if mode != "dark":
        return ""
    return (f'<radialGradient id="{uid}halo"><stop offset="55%" stop-color="#F5ECDC" stop-opacity=".16"/>'
            '<stop offset="100%" stop-color="#F5ECDC" stop-opacity="0"/></radialGradient>')


def ridge(x0: float, x1: float, base: float, height: float, weeks: list[int]) -> str:
    """A mountain range from 52 weeks of contributions: one peak per week,
    smoothed, as an ink-wash silhouette along the bottom of the card."""
    if not weeks:
        return ""
    top = max(weeks) or 1
    n = len(weeks)
    pts = [(x0 + (x1 - x0) * i / (n - 1), base - 4 - (height - 4) * (w / top) ** 0.7) for i, w in enumerate(weeks)]
    d = f"M{ink.fmt(x0)} {ink.fmt(base)}L{ink.fmt(pts[0][0])} {ink.fmt(pts[0][1])}"
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        mx = (ax + bx) / 2
        d += f"Q{ink.fmt(ax)} {ink.fmt(ay)} {ink.fmt(mx)} {ink.fmt((ay + by) / 2)}"
    d += f"L{ink.fmt(pts[-1][0])} {ink.fmt(pts[-1][1])}L{ink.fmt(x1)} {ink.fmt(base)}Z"
    return f'<path d="{d}" class="au" opacity=".09"/><path d="{d}" class="au-s" stroke-opacity=".28" stroke-width="1"/>'


def omen_layer(inp: Inputs, w: float, h: float, mode: str) -> tuple[str, str]:
    """(svg, css) for mist or a meteor; dark only, invisible when still."""
    if mode != "dark" or inp.omen not in ("mist", "meteor"):
        return "", ""
    if inp.omen == "mist":
        band = "".join(f'<ellipse cx="{ink.fmt(cx)}" cy="{ink.fmt(cy)}" rx="{ink.fmt(rx)}" ry="{ink.fmt(ry)}"/>'
                       for cx, cy, rx, ry in ((w * 0.2, h * 0.55, 220, 26), (w * 0.5, h * 0.6, 260, 22),
                                              (w * 0.8, h * 0.52, 200, 24)))
        svg = f'<g class="mist tx" filter="url(#mistblur)">{band}</g>'
        css = (".mist{opacity:0;animation:cdmist 26s ease-in-out 1s infinite}"
               "@keyframes cdmist{0%{opacity:0;transform:translateX(-120px)}25%{opacity:.07}"
               "75%{opacity:.07}100%{opacity:0;transform:translateX(120px)}}")
        return svg, css
    svg = (f'<g class="meteor"><path d="M0 0L-90 -34" stroke="url(#meteorg)" stroke-width="1.6" '
           f'stroke-linecap="round" fill="none" transform="translate({ink.fmt(w * 0.62)} {ink.fmt(h * 0.18)})"/></g>')
    css = (".meteor{opacity:0;animation:cdmet 1.4s ease-in 2.2s 1 both}"
           "@keyframes cdmet{0%{opacity:0;transform:translate(-160px,-60px)}15%{opacity:1}"
           "100%{opacity:0;transform:translate(160px,60px)}}")
    return svg, css


def omen_defs(inp: Inputs, mode: str) -> str:
    if mode != "dark":
        return ""
    if inp.omen == "mist":
        return '<filter id="mistblur" x="-20%" y="-200%" width="140%" height="500%"><feGaussianBlur stdDeviation="14"/></filter>'
    if inp.omen == "meteor":
        return ('<linearGradient id="meteorg" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#F5ECDC"/>'
                '<stop offset="1" stop-color="#F5ECDC" stop-opacity="0"/></linearGradient>')
    return ""


def card_label(inp: Inputs) -> str:
    facts = "; ".join(f"{zh} {gloss}: {value}" for zh, gloss, value, _ in card_rows(inp))
    omen = {"qi_deviation": " This week's omen: a qi deviation; the seal is cracked.",
            "mist": " This week's omen: mist drifts over the terrace.",
            "meteor": " This week's omen: a meteor crosses the sky."}.get(inp.omen, "")
    ridge_words = (" Along the bottom, a mountain ridge drawn from 52 weeks of GitHub contributions."
                   if inp.weeks else "")
    return (f"心镜台, the Heart-Mirror Terrace. A bronze heart-mirror holds tonight's moon. "
            f"{ink.NAME}, with the red seal 神. {TITLE}. {FOCUS.replace(' · ', ', ')}. {facts}.{ridge_words}{omen}")


def card_svg(inp: Inputs, mode: str) -> str:
    w = ink.W
    rows = card_rows(inp)
    lh = 23
    rows_y = 150
    h = int(rows_y + (len(rows) - 1) * lh + 34 + (26 if inp.weeks else 0))
    uid = "c"
    body = [ink.plate(0, 0, w, h, corner=30, large=True)]
    if inp.weeks:
        body.append(ridge(14, w - 14, h - 6, 44, inp.weeks))
    mcx, mcy, mr = 142, min(h / 2, 150), 104
    body.append(mirror(mcx, mcy, mr, inp, mode, uid))
    x = 284
    body.append(ink.text(x, 64, ink.NAME, 44, "display", "tx"))
    nx = x + ink.measure(ink.NAME, 44, "display") + 14
    body.append(ink.seal(nx, 28, 30, "神", crack=inp.omen == "qi_deviation"))
    body.append(ink.text(x, 92, TITLE, 15.5, "medium", "au"))
    body.append(ink.text(x, 113, FOCUS, 13, "body", "mu"))
    body.append(ink.brush_rule(x - 4, 124, w - x - 30, 6, "au", ' opacity=".4"'))
    vx = x + 118
    for k, (zh, gloss, value, cls) in enumerate(rows):
        y = rows_y + k * lh
        body.append(ink.text(x, y, zh, 13.5, "serif", "mu"))
        body.append(ink.text(x + 34, y, gloss, 12, "body", "mu"))
        body.append(ink.text(vx, y, ink.fit(value, w - vx - 30, 14), 14, "body", cls))
    omen_svg, omen_css = omen_layer(inp, w, h, mode)
    body.append(omen_svg)
    return ink.doc(w, h, "".join(body), card_label(inp), mode,
                   defs=halo_defs(uid, mode) + omen_defs(inp, mode), extra_css=omen_css)


def wrap_items(value: str, width: float, size: float) -> list[str]:
    """Wrap a ' · ' list between items, so no line starts with the dot."""
    if " · " not in value:
        return ink.wrap(value, width, size) or [""]
    lines, line = [], ""
    for item in value.split(" · "):
        trial = f"{line} · {item}" if line else item
        if line and ink.measure(trial + " ·", size) > width:
            lines.append(line + " ·")
            line = item
        else:
            line = trial
    return lines + [line]


def card_phone_svg(inp: Inputs) -> str:
    w = ink.WP
    mode = "dark"
    uid = "c"
    rows = card_rows(inp)
    mcx, mcy, mr = w / 2, 96, 76
    x = 18
    y = mcy + mr + 46
    body: list[str] = []
    name_w = ink.measure(ink.NAME, 34, "display")
    nx = (w - name_w - 32) / 2
    body.append(ink.text(nx, y, ink.NAME, 34, "display", "tx"))
    body.append(ink.seal(nx + name_w + 10, y - 27, 24, "神", crack=inp.omen == "qi_deviation"))
    y += 26
    body.append(ink.text(w / 2, y, TITLE, 14, "medium", "au", anchor="middle"))
    y += 20
    for line in ink.wrap(FOCUS, w - 2 * x, 12.5):
        body.append(ink.text(w / 2, y, line, 12.5, "body", "mu", anchor="middle"))
        y += 18
    body.append(ink.brush_rule(x, y - 4, w - 2 * x, 5, "au", ' opacity=".4"'))
    y += 22
    vx = x + 100
    for zh, gloss, value, cls in rows:
        lines = wrap_items(value, w - vx - x, 13)
        body.append(ink.text(x, y, zh, 12.5, "serif", "mu"))
        body.append(ink.text(x + 30, y, gloss, 11.5, "body", "mu"))
        for line in lines:
            body.append(ink.text(vx, y, line, 13, "body", cls))
            y += 19
        y += 3
    h = int(y + 6 + (26 if inp.weeks else 0))
    parts = [ink.plate(0, 0, w, h, corner=22, large=True)]
    if inp.weeks:
        parts.append(ridge(10, w - 10, h - 5, 34, inp.weeks))
    parts.append(mirror(mcx, mcy, mr, inp, mode, uid))
    omen_svg, omen_css = omen_layer(inp, w, h, mode)
    return ink.doc(w, h, "".join(parts + body) + omen_svg, card_label(inp), mode,
                   defs=halo_defs(uid, mode) + omen_defs(inp, mode), extra_css=omen_css)


# =====================================================================================
# drawing: the mission board
# =====================================================================================

DIGIT_SIZE = 30


def tablet(x: float, y: float, w: float, proc: dict, k: int) -> str:
    """One hanging mission tablet: name, tags, a ten-segment qi bar."""
    h = 44
    out = [f'<path d="M{ink.fmt(x + 26)} {ink.fmt(y - 9)}V{ink.fmt(y)}M{ink.fmt(x + w - 26)} {ink.fmt(y - 9)}V{ink.fmt(y)}" '
           'class="sl-s" stroke-width="1.2" stroke-opacity=".8"/>',
           ink.rect(x, y, w, h, "rs", 3),
           f'<rect x="{ink.fmt(x + 0.5)}" y="{ink.fmt(y + 0.5)}" width="{ink.fmt(w - 1)}" height="{h - 1}" rx="3" '
           'class="ln" stroke-width="1"/>']
    seg_w, gap = 5, 2.4
    bar_w = 10 * seg_w + 9 * gap
    bx = x + w - 14 - bar_w
    lit = max(1, min(10, int(proc["cpu"] / 10 + 0.5)))
    on = "".join(f"M{ink.fmt(bx + i * (seg_w + gap))} {ink.fmt(y + 18)}h{seg_w}v10h-{seg_w}z" for i in range(lit))
    off = "".join(f"M{ink.fmt(bx + i * (seg_w + gap))} {ink.fmt(y + 18)}h{seg_w}v10h-{seg_w}z" for i in range(lit, 10))
    out.append(f'<path d="{off}" class="tk"/>' if off else "")
    out.append(f'<path d="{on}" class="jd"/>')
    out.append(ink.text(bx - 8, y + 27.5, f"qi {proc['cpu']}", 11, "mono", "mu", anchor="end"))
    room = bx - 70 - (x + 14)
    out.append(ink.text(x + 14, y + 20, ink.fit(proc["command"], room, 14, "mono"), 14, "mono", "au"))
    if proc["flags"]:
        out.append(ink.text(x + 14, y + 36, ink.fit(proc["flags"], room, 11.5, "mono"), 11.5, "mono", "mu"))
    return "".join(out)


def clock(x: float, y: float, animated: bool) -> tuple[str, str, str]:
    """mm:ss since the picture loaded, as digit strips that step on in CSS.
    Reduced motion or daylight: '--:--'. Returns (svg, css, defs)."""
    size = DIGIT_SIZE
    cell = ink.measure("0", size, "mono")
    step = size * 1.25
    dashes = ink.text(x, y, "--:--", size, "mono", "au")
    if not animated:
        return dashes, "", ""
    body, css, defs = [], [], []
    for i, pos in enumerate((("m10", 6, 3600), ("m1", 10, 600), None, ("s10", 6, 60), ("s1", 10, 10))):
        dx = x + i * cell
        if pos is None:
            body.append(ink.text(dx, y, ":", size, "mono", "au"))
            continue
        name, count, period = pos
        defs.append(f'<clipPath id="ck{name}"><rect x="{ink.fmt(dx - 1)}" y="{ink.fmt(y - size * 0.8)}" '
                    f'width="{ink.fmt(cell + 2)}" height="{ink.fmt(size * 1.0)}"/></clipPath>')
        strip = "".join(ink.text(dx, y + n * step, str(n), size, "mono", "") for n in range(count))
        body.append(f'<g clip-path="url(#ck{name})"><g class="au ck{name}">{strip}</g></g>')
        css.append(f".ck{name}{{animation:cdk{name} {period}s steps({count},end) infinite}}"
                   f"@keyframes cdk{name}{{to{{transform:translateY(-{ink.fmt(count * step)}px)}}}}")
    css.append(".clkrm{display:none}"
               "@media (prefers-reduced-motion: reduce){.clk{display:none}.clkrm{display:inline}}")
    return (f'<g class="clk">{"".join(body)}</g><g class="clkrm">{dashes}</g>', "".join(css), "".join(defs))


def incense(x: float, base: float, height: float, lit: bool) -> tuple[str, str]:
    """A censer with one stick: it burns down over thirty minutes while you
    read, with a curl of smoke. Unlit by day; unburned when still."""
    out = [f'<path d="M{ink.fmt(x - 16)} {ink.fmt(base)}Q{ink.fmt(x)} {ink.fmt(base + 16)} {ink.fmt(x + 16)} {ink.fmt(base)}Z" class="em"/>',
           ink.rect(x - 18, base - 3, 36, 4, "em", 1.5),
           ink.rect(x - 8, base + 9, 16, 3, "em", 1)]
    stick = ink.rect(x - 1, base - height, 2, height, "mu")
    if not lit:
        out.append(stick)
        out.append(ink.rect(x - 1.6, base - height - 1, 3.2, 4, "mu"))
        return "".join(out), ""
    burn = height * 0.85
    tip = (f'<circle cx="{ink.fmt(x)}" cy="{ink.fmt(base - height)}" r="2.4" class="em glow"/>'
           f'<path d="M{ink.fmt(x)} {ink.fmt(base - height - 4)}c-5 -6 5 -11 0 -17c-4 -5 4 -9 1 -15" '
           'class="mu-s smoke" stroke-width="1.2" stroke-linecap="round" stroke-opacity=".5"/>')
    out.append(f'<g class="stick" style="transform-origin:{ink.fmt(x)}px {ink.fmt(base)}px">{stick}</g>')
    out.append(f'<g class="tip">{tip}</g>')
    css = (f".stick{{animation:cdburn 1800s linear forwards}}@keyframes cdburn{{to{{transform:scaleY({ink.fmt(1 - burn / height)})}}}}"
           f".tip{{animation:cdtip 1800s linear forwards}}@keyframes cdtip{{to{{transform:translateY({ink.fmt(burn)}px)}}}}"
           ".smoke{stroke-dasharray:6 5;animation:cdsmoke 3s linear infinite}"
           "@keyframes cdsmoke{to{stroke-dashoffset:-22}}")
    return "".join(out), css


def notice_rows(entries: list[Notice], width: float, size: float, max_rows: int,
                keep_tail: int) -> list[tuple[Notice, list[str]]]:
    """Wrap each notice; drop the oldest until everything fits."""
    date_w = ink.measure("Mon 00 ", 11, "mono") + 4
    entries = list(entries)
    while entries:
        wrapped = []
        for n in entries:
            prefix = ink.measure(f"{n.unit}: ", size, "medium")
            first = ink.wrap(n.msg, width - date_w - prefix, size) or [""]
            if len(first) > 1:  # continuation lines hang under the message
                rest = " ".join(first[1:])
                first = first[:1] + ink.wrap(rest, width - date_w - prefix, size)
            wrapped.append((n, first))
        if sum(len(lines) for _, lines in wrapped) <= max_rows or len(entries) <= keep_tail:
            return wrapped
        entries.pop(0)
    return []


def draw_notices(x: float, y: float, width: float, size: float, lh: float,
                 rows: list[tuple[Notice, list[str]]]) -> tuple[str, float]:
    date_w = ink.measure("Mon 00 ", 11, "mono") + 4
    out = []
    for n, lines in rows:
        out.append(ink.text(x, y, notice_date(n), 11, "mono", "jd" if n.label else "mu"))
        unit = f"{n.unit}: "
        uw = ink.measure(unit, size, "medium")
        out.append(ink.text(x + date_w, y, unit, size, "medium", n.unit_cls))
        for k, line in enumerate(lines):
            out.append(ink.text(x + date_w + uw, y + k * lh, line, size, "body", n.cls))
        y += len(lines) * lh
    return "".join(out), y


def board_label(inp: Inputs, light: bool) -> str:
    missions = "; ".join(f"{p['command']} {p['flags']}".strip() + f", qi {p['cpu']}" for p in inp.processes)
    when = f", {MONTHS[inp.status_updated.month - 1]} {inp.status_updated.day}" if inp.status_updated else ""
    lines = " / ".join(f"{notice_date(n)} {n.unit}: {n.msg}" for n in notices(inp, light))
    incense_words = ("The incense is not lit by day." if light
                     else "One stick of incense counts the minutes and seconds since you arrived, and burns down over half an hour.")
    return (f"任务殿, the Mission Hall. Posted missions: {missions}. The steward{when}: {inp.motd} "
            f"Notices: {lines}. {incense_words}")


def steward_note(inp: Inputs) -> str:
    when = f", {MONTHS[inp.status_updated.month - 1]} {inp.status_updated.day:02d}" if inp.status_updated else ""
    return f"the steward{when}:"


def board_svg(inp: Inputs, mode: str) -> str:
    w = ink.W
    light = mode == "light"
    h = 380
    body = [ink.plate(0, 0, w, h, corner=30, large=True)]
    css: list[str] = []
    defs: list[str] = []

    # left: the posted missions
    lx, lw = 26, 380
    body.append(ink.text(lx, 44, "任务榜", 22, "brush", "au"))
    body.append(ink.text(lx + 76, 41, "posted missions", 12.5, "body", "mu"))
    body.append(ink.hline(lx, lx + lw, 58, "ln", 1.5))
    procs = inp.processes[:4]
    ty = 70
    for k, proc in enumerate(procs):
        body.append(tablet(lx, ty, lw, proc, k))
        ty += 54
    note_y = ty + 14
    body.append(ink.text(lx, note_y, steward_note(inp), 12.5, "medium", "mu"))
    for k, line in enumerate(ink.wrap(inp.motd, lw, 13.5, max_lines=2)):
        body.append(ink.text(lx, note_y + 20 + k * 19, line, 13.5, "body", "tx"))

    # right: notices, then the incense
    rx, rw = 438, w - 26 - 438
    body.append(ink.vline(418, 30, h - 30, "ln"))
    body.append(ink.text(rx, 44, "告示", 22, "brush", "au"))
    body.append(ink.text(rx + 52, 41, "notices", 12.5, "body", "mu"))
    body.append(ink.hline(rx, rx + rw, 58, "ln", 1.5))
    rows = notice_rows(notices(inp, light), rw, 12.5, 9, keep_tail=3 if light else 1)
    svg, _ = draw_notices(rx, 80, rw, 12.5, 18, rows)
    body.append(svg)

    iy = 262
    body.append(ink.hline(rx, rx + rw, iy - 18, "ln"))
    body.append(ink.text(rx, iy + 8, "一炷香", 17, "brush", "au"))
    body.append(ink.text(rx + 60, iy + 6, "one stick of incense", 12, "body", "mu"))
    face, clock_css, clock_defs = clock(rx, iy + 54, animated=not light)
    body.append(face)
    css.append(clock_css)
    defs.append(clock_defs)
    cap = (("incense burned since you arrived.", "the elders are not judging. they are timing.") if not light
           else ("the incense is not lit by day.", "the elders are not judging. they are squinting."))
    body.append(ink.text(rx + ink.measure("00:00", DIGIT_SIZE, "mono") + 18, iy + 48, cap[0], 12.5, "body", "tx"))
    body.append(ink.text(rx, iy + 84, cap[1], 12.5, "body", "mu"))
    stick, stick_css = incense(rx + rw - 22, iy + 90, 64, lit=not light)
    body.append(stick)
    css.append(stick_css)
    return ink.doc(w, h, "".join(body), board_label(inp, light), mode, defs="".join(defs), extra_css="".join(css))


def board_phone_svg(inp: Inputs) -> str:
    w = ink.WP
    x, cw = 16, w - 32
    body: list[str] = []
    css: list[str] = []
    defs: list[str] = []
    body.append(ink.text(x, 40, "任务榜", 20, "brush", "au"))
    body.append(ink.text(x + 70, 37, "posted missions", 12, "body", "mu"))
    y = 62
    for k, proc in enumerate(inp.processes[:3]):
        body.append(tablet(x, y, cw, proc, k))
        y += 54
    y += 8
    body.append(ink.text(x, y, steward_note(inp), 12, "medium", "mu"))
    y += 19
    for line in ink.wrap(inp.motd, cw, 13, max_lines=3):
        body.append(ink.text(x, y, line, 13, "body", "tx"))
        y += 18
    y += 18
    body.append(ink.text(x, y, "一炷香", 16, "brush", "au"))
    body.append(ink.text(x + 56, y - 2, "one stick of incense", 11.5, "body", "mu"))
    y += 42
    face, clock_css, clock_defs = clock(x, y, animated=True)
    body.append(face)
    css.append(clock_css)
    defs.append(clock_defs)
    cx = x + ink.measure("00:00", DIGIT_SIZE, "mono") + 16
    body.append(ink.text(cx, y - 16, "incense burned", 12, "body", "tx"))
    body.append(ink.text(cx, y + 1, "since you arrived", 12, "body", "tx"))
    stick, stick_css = incense(w - 34, y + 12, 58, lit=True)
    body.append(stick)
    css.append(stick_css)
    y += 44
    body.append(ink.text(x, y, "告示", 20, "brush", "au"))
    body.append(ink.text(x + 48, y - 3, "notices", 12, "body", "mu"))
    y += 24
    entries = notices(inp, light=False)
    recent = [n for n in entries[:-1] if n.unit not in ("pigeons",)][-4:] + entries[-1:]
    rows = notice_rows(recent, cw, 12, 8, keep_tail=1)
    svg, y = draw_notices(x, y, cw, 12, 18, rows)
    body.append(svg)
    h = int(y + 6)
    plate = ink.plate(0, 0, w, h, corner=22, large=True)
    return ink.doc(w, h, plate + "".join(body), board_label(inp, False), "dark", defs="".join(defs),
                   extra_css="".join(css))


# =====================================================================================
# main
# =====================================================================================


def render_all(inp: Inputs) -> dict[str, str]:
    return {
        "mirror/card.svg": card_svg(inp, "dark"),
        "mirror/card-light.svg": card_svg(inp, "light"),
        "mirror/card-phone.svg": card_phone_svg(inp),
        "hall/board.svg": board_svg(inp, "dark"),
        "hall/board-light.svg": board_svg(inp, "light"),
        "hall/board-phone.svg": board_phone_svg(inp),
    }


def dry_run(inp: Inputs) -> None:
    print(f"week={inp.week} seed={inp.seed} omen={inp.omen}")
    print(f"obsession={inp.obsession!r}")
    print(f"motd={inp.motd!r} updated={inp.status_updated}")
    for p in inp.processes:
        print(f"  mission pid={stable_pid(p['command'])} qi={p['cpu']:>2}  {p['command']} {p['flags']}")
    print(f"commits={inp.commits} ridge_weeks={len(inp.weeks)} newest_disciple={inp.stargazer}")
    print(f"stewards={[(n, w.date().isoformat()) for n, w in inp.stewards]} formation_events={len(inp.formation)}")
    for note in inp.notes:
        print(f"note: {note}")
    for light in (False, True):
        print(f"--- notices, {'light' if light else 'dark'} ---")
        for n in notices(inp, light):
            print(f"  {notice_date(n):<7} {n.unit}: {n.msg}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Render the Heart-Mirror card and the Mission Hall board.")
    parser.add_argument("--dry-run", action="store_true", help="print the inputs and notices; write nothing")
    parser.add_argument("--omen", choices=ALL_OMENS, help="force this week's omen (testing)")
    parser.add_argument("--out-dir", default=str(OUT_DIR), help="writes OUT/mirror and OUT/hall (testing)")
    parser.add_argument("--status", default=str(STATUS_PATH), help="status.json to read (testing)")
    parser.add_argument("--offline", action="store_true", help="skip every network lookup")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):  # a cp1252 console must not crash on 飞鸽
        sys.stdout.reconfigure(errors="replace")

    try:
        inp = gather(args.omen, Path(args.status), args.offline)
        if args.dry_run:
            dry_run(inp)
            return
        rendered = render_all(inp)
        for content in rendered.values():
            ET.fromstring(content)  # all six parse, or nothing is written
    except Exception as error:  # a bad day must never take the card down
        print(f"WARNING: card render failed ({type(error).__name__}: {error}); keeping the old files")
        return
    out = Path(args.out_dir)
    for name, content in rendered.items():
        try:
            changed = ink.write_svg(out / name, content)
        except (ValueError, OSError) as error:
            print(f"WARNING: {name}: {error}")
            continue
        print(f"{(out / name).as_posix()}: {len(content.encode('utf-8')) / 1024:.1f} KB"
              f"{'' if changed else ' (unchanged)'}")
    print(f"card: omen={inp.omen} week={inp.week}")


if __name__ == "__main__":
    main()
