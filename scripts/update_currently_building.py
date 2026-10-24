"""The steward: posts what Bill is working on now, twice a week.

The steward is an LLM call. It reads Bill's real public GitHub activity, picks
the three repos he is working on, and writes one short line for each, like a
good commit message. Those three lines are the README's Now section (the NOW
block) and live in assets/status.json:

    {"missions": [{"repo": "owner/name", "pushed": "YYYY-MM-DD", "line": "Added ..."}],
     "updated": "YYYY-MM-DDTHH:MM:SSZ"}

Voice filter. Every line, from the model or kept from an earlier run, goes
through voice_tells(): em dashes, semicolons, colons, "not just", "X, not Y",
"rather than", rhetorical triplets, question-then-answer, trailing "-ing"
clauses, chatbot phrases, vague filler and a list of words that read as
machine-written. A line with any of them is swapped for the plain line for that
repo: a recent commit subject that passes the same test, else the repo
description, else "Pushed new commits."

Honesty rules. Candidates are only repos Bill pushed to, from the public
events feed, never the profile repo itself. The LLM may only pick from that
list; one repo outside it rejects the whole payload. The date on each line is
Bill's newest push, from the feed, never from the model. With fewer than 3
candidates the list is topped up from his public repos by last push (no forks,
nothing archived).

When the model is unreachable or returns junk, the previous status.json is
kept (its dates refreshed from the feed, any line with a tell swapped for the
plain line); only when there is no usable previous one, or with
--fallback-only, the plain lines from the same candidates take over. With
fewer than 3 repos in hand the NOW block is left alone.

--dates-only (the Saturday moon watch): no LLM. Re-read the feed, move each
posted repo's date forward if Bill pushed again, re-render the NOW block.
status.json is rewritten only if a date moved; BUILD_PLATE is not touched.

Also owns the BUILD_PLATE block: one HTML comment ("steward run N, from SHA"),
invisible on the page. It changes every normal run, so the Mon/Thu run always
commits: that commit is the keepalive that stops GitHub from switching off the
scheduled workflows.

Contract: never blank anything. status.json is only rewritten after the whole
payload validated; a missing marker is a warning, not a crash; any API failure
warns and exits 0. Run from the repo root:
    python scripts/update_currently_building.py --fallback-only
    python scripts/update_currently_building.py --dates-only
    python scripts/update_currently_building.py --readme .preview/README.md --status .preview/status.json
    python scripts/update_currently_building.py --self-test
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import unicodedata
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

from readme_blocks import replace_block

USERNAME = "IdkwhatImD0ing"
PROFILE_REPO = f"{USERNAME}/{USERNAME}"
# Personal repos (trip budgets and the like) never become a Now line.
SKIP_REPOS = {"idkwhatimd0ing/travel"}
API = "https://api.github.com"
PLATE_START = "<!-- BUILD_PLATE:START -->"
PLATE_END = "<!-- BUILD_PLATE:END -->"
NOW_START = "<!-- NOW:START -->"
NOW_END = "<!-- NOW:END -->"
# Generated text may never smuggle in a README marker, live or retired.
MARKER_RE = re.compile(r"<!--\s*[A-Z_]+:(?:START|END)\s*-->")

STATUS_PATH = "assets/status.json"

MISSIONS = 3
MAX_CANDIDATES = 6
SUBJECTS_PER_REPO = 5
LINE_MAX = 64
REPO_RE = re.compile(r"^[A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}$")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

NO_NOTES = "Pushed new commits."
# The sect's story stays out of the Now lines (the work itself may still be
# about a sect scene, so the bare word "sect" is allowed).
FICTION_WORDS = re.compile(r"\b(steward|elders?|disciples?|cultivat\w*|qi|sect leader|bill)\b", re.I)
SCOPE_TAG = re.compile(r"^(?:[\w./-]+(?:\([^)]*\))?!?):\s+")

# --- the voice filter ----------------------------------------------------------------
# The tells that make a line read as machine-written (CLAUDE.md, "Voice"). Words
# match as whole words, any case.
TELL_WORDS = (
    # words models use far more than people do
    "delve", "delves", "delving", "delved", "tapestry", "testament", "pivotal", "crucial",
    "underscore", "underscores", "showcase", "showcases", "showcasing", "vibrant", "intricate",
    "landscape", "foster", "fosters", "robust", "seamless", "seamlessly", "leverage", "leverages",
    "leveraged", "leveraging", "multifaceted", "quietly", "genuinely", "genuine", "honest",
    "honestly", "deliberate", "deliberately", "load-bearing", "seam", "seams", "meticulous",
    "meticulously", "realm", "journey", "elevate", "elevates", "elevating", "empower", "empowers",
    "cutting-edge", "game-changer", "game-changing", "revolutionize", "revolutionizing", "unlock",
    "unlocks", "harness", "harnessing", "ever-evolving", "arguably", "deeply", "fundamentally",
    "truly", "boasts",
    # vague filler: says less than the commit did
    "enhance", "enhances", "enhanced", "enhancing", "enhancement", "enhancements", "various",
    "elements", "streamline", "streamlined", "streamlining", "overall",
    # chatbot residue
    "certainly", "absolutely",
)
TELL_PHRASES = (
    "not just", "not only", "more than just", "rather than", "the shape of", "earns its keep",
    "matters because", "single most", "every single", "serves as", "stands as", "to the repository",
    "to the repo", "look and feel", "great question", "i hope", "let me know", "in the world of",
    "at the heart of", "under the hood",
)
TELL_SHAPES = (
    ("em dash", re.compile(r"[—―]|\s–\s|--")),
    ("semicolon", re.compile(r";")),
    ("colon", re.compile(r":\s")),
    ("X, not Y", re.compile(r",\s*not\b", re.I)),
    ("it's not X, it's Y", re.compile(r"\b(?:it'?s|is|was|are|isn'?t|wasn'?t)\s+not\b.*\b(?:it'?s|but)\b", re.I)),
    ("not X but Y", re.compile(r"\bnot\s+(?:a\s+|an\s+|the\s+)?\w+\s*,?\s+but\b", re.I)),
    ("less X, more Y", re.compile(r"\bless\s+\w+,?\s+(?:and\s+)?more\b", re.I)),
    ("rhetorical triplet", re.compile(r"\b[\w-]+(?:\s[\w-]+)?,\s+[\w-]+(?:\s[\w-]+)?,?\s+and\s+[\w-]+", re.I)),
    ("question, then answer", re.compile(r"\?\s+\S")),
    ("trailing -ing clause", re.compile(
        r",\s+(?:ensuring|highlighting|showcasing|reflecting|underscoring|making|allowing|enabling|"
        r"providing|creating|bringing|paving|marking|signaling|setting)\b", re.I)),
    ("vague new X", re.compile(r"\b(?:new|some|minor|several|general)\s+(?:visual\s+)?"
                               r"(?:features|improvements|updates|changes|tweaks|stuff)\b", re.I)),
)
_TELL_WORD_RE = re.compile(r"(?<![\w-])(?:" + "|".join(re.escape(w) for w in TELL_WORDS) + r")(?![\w-])", re.I)


def voice_tells(text: str) -> list[str]:
    """Why `text` reads as machine-written; an empty list means it is clean.
    Run it on the raw text as well: sanitize_line folds an em dash into '-'."""
    text = str(text or "")
    found = [name for name, pattern in TELL_SHAPES if pattern.search(text)]
    found += [f"word {m.group(0).lower()!r}" for m in _TELL_WORD_RE.finditer(text)]
    low = text.lower()
    found += [f"phrase {p!r}" for p in TELL_PHRASES if p in low]
    return found


@dataclass
class Candidate:
    repo: str
    pushed: str                 # YYYY-MM-DD, Bill's newest push
    subjects: list[str] = field(default_factory=list)
    description: str = ""
    topped_up: bool = False     # from the repo list, not the push feed


# --- GitHub ------------------------------------------------------------------------


def request_json(url: str, token: str | None = None) -> object:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "github-profile-readme-updater",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_push_dates(token: str | None) -> dict[str, str]:
    """repo -> Bill's newest public push (YYYY-MM-DD, UTC), newest repo first."""
    events = request_json(f"{API}/users/{USERNAME}/events/public?per_page=100", token)
    if not isinstance(events, list):
        raise ValueError("events feed is not a list")
    newest: dict[str, str] = {}
    for event in events:
        if not isinstance(event, dict) or event.get("type") != "PushEvent":
            continue
        if (event.get("actor") or {}).get("login", USERNAME) != USERNAME:
            continue
        repo = str((event.get("repo") or {}).get("name", ""))
        stamp = str(event.get("created_at", ""))
        if repo == PROFILE_REPO or repo.casefold() in SKIP_REPOS or not REPO_RE.match(repo) \
                or not ISO_DATE.match(stamp[:10]):
            continue
        if stamp > newest.get(repo, ""):
            newest[repo] = stamp
    ordered = sorted(newest.items(), key=lambda kv: kv[1], reverse=True)
    return {repo: stamp[:10] for repo, stamp in ordered}


def fetch_subjects(repo: str, token: str | None) -> list[str]:
    """Bill's recent commit subjects in `repo`, newest first, merges skipped.
    The push feed no longer carries commit messages, so they come from here."""
    try:
        commits = request_json(f"{API}/repos/{repo}/commits?author={USERNAME}&per_page=10", token)
    except (urllib.error.URLError, OSError, ValueError) as error:
        print(f"WARNING: {repo}: commit subjects unavailable ({error})")
        return []
    subjects = []
    for commit in commits if isinstance(commits, list) else []:
        message = str(((commit or {}).get("commit") or {}).get("message", ""))
        subject = message.splitlines()[0].strip() if message.strip() else ""
        if subject and not subject.startswith("Merge "):
            subjects.append(subject)
    return subjects[:SUBJECTS_PER_REPO]


def fetch_repo(repo: str, token: str | None) -> dict | None:
    """The repo's public record; None when it is gone or private now (so the
    page never links to a 404). A network error keeps it with no description."""
    try:
        data = request_json(f"{API}/repos/{repo}", token)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        print(f"WARNING: {repo}: repo details unavailable ({error})")
        return {}
    except (urllib.error.URLError, OSError, ValueError) as error:
        print(f"WARNING: {repo}: repo details unavailable ({error})")
        return {}
    if not isinstance(data, dict) or data.get("private") or data.get("archived"):
        return None
    return data


def fetch_candidates(token: str | None) -> list[Candidate]:
    """Repos Bill pushed to, newest first, topped up to 3 from his repo list."""
    candidates: list[Candidate] = []
    for repo, pushed in fetch_push_dates(token).items():
        record = fetch_repo(repo, token)
        if record is None:
            continue
        candidates.append(Candidate(repo=repo, pushed=pushed, subjects=fetch_subjects(repo, token),
                                    description=str(record.get("description") or "")))
        if len(candidates) == MAX_CANDIDATES:
            break
    if len(candidates) < MISSIONS:
        try:
            repos = request_json(f"{API}/users/{USERNAME}/repos?sort=pushed&per_page=30&type=owner", token)
        except (urllib.error.URLError, OSError, ValueError) as error:
            print(f"WARNING: repo list unavailable ({error})")
            repos = []
        taken = {c.repo.casefold() for c in candidates}
        for repo in repos if isinstance(repos, list) else []:
            if len(candidates) >= MISSIONS:
                break
            if not isinstance(repo, dict) or repo.get("fork") or repo.get("archived") or repo.get("private"):
                continue
            name = str(repo.get("full_name", ""))
            pushed = str(repo.get("pushed_at", ""))[:10]
            if name == PROFILE_REPO or name.casefold() in SKIP_REPOS or name.casefold() in taken \
                    or not REPO_RE.match(name) \
                    or not ISO_DATE.match(pushed):
                continue
            taken.add(name.casefold())
            candidates.append(Candidate(repo=name, pushed=pushed, description=str(repo.get("description") or ""),
                                        topped_up=True))
    return candidates


# --- sanitizers ----------------------------------------------------------------------


def ensure_no_markers(content: str) -> str:
    if MARKER_RE.search(content) or PLATE_START in content or PLATE_END in content:
        raise ValueError("Generated content unexpectedly contained README markers")
    return content


# Typographic punctuation folds to ASCII before accents are stripped, so
# "it’s" stays "it's" instead of losing the apostrophe.
PUNCTUATION = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"',
                             "–": "-", "—": "-", "…": "..."})


def sanitize_line(value: str, limit: int = 80) -> str:
    """Strip markdown/HTML-active and control characters from untrusted text, fold it
    to plain ASCII (no emoji), cap length."""
    text = str(value or "").translate(PUNCTUATION)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = "".join(ch if ch.isprintable() else " " for ch in text)
    text = re.sub(r"<[^<>]*>", " ", text)  # whole tags first, so '<b>x</b>' leaves 'x', not 'bx/b'
    text = re.sub(r"[\[\]|<>`\\{}*_#]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit].rstrip()


def fit_line(value: str) -> str:
    """One sentence for a Now line: first letter up, at most LINE_MAX
    characters, ending in a full stop (or '...' when it had to be cut)."""
    text = re.sub(r"\s+([.,;:!?])", r"\1", sanitize_line(value, 240))
    if not text:
        return ""
    text = text[0].upper() + text[1:]
    if len(text) <= LINE_MAX:
        return text if text[-1] in ".!?" else text.rstrip(",;:- ") + "."
    first = re.split(r"(?<=[.!?])\s", text, maxsplit=1)[0]
    if 12 <= len(first) <= LINE_MAX:
        return first
    cut = text[:LINE_MAX - 3].rsplit(" ", 1)[0].rstrip(",;:-. ")
    return f"{cut}..."


def commit_line(subject: str) -> str:
    """A commit subject as a Now line: scope tags like '/sect:' or 'docs:' dropped."""
    return fit_line(SCOPE_TAG.sub("", sanitize_line(subject, 240)))


def show_date(iso: str, today: date) -> str:
    """'2026-10-24' -> 'Oct 24' this year, 'Oct 2025' for an older year."""
    d = date.fromisoformat(iso)
    return f"{MONTHS[d.month - 1]} {d.day}" if d.year == today.year else f"{MONTHS[d.month - 1]} {d.year}"


# --- payloads ------------------------------------------------------------------------


def finalize_missions(missions: list) -> list[dict]:
    """The only gate to disk and to the page: exactly MISSIONS clean entries."""
    out: list[dict] = []
    seen: set[str] = set()
    for mission in missions if isinstance(missions, list) else []:
        if not isinstance(mission, dict):
            raise ValueError("mission is not an object")
        repo = str(mission.get("repo", ""))
        pushed = str(mission.get("pushed", ""))
        line = fit_line(str(mission.get("line", "")))
        if not REPO_RE.match(repo) or repo == PROFILE_REPO or repo.casefold() in seen:
            raise ValueError(f"bad mission repo {repo!r}")
        if not ISO_DATE.match(pushed):
            raise ValueError(f"bad mission date {pushed!r}")
        date.fromisoformat(pushed)
        if not line:
            raise ValueError(f"empty line for {repo}")
        seen.add(repo.casefold())
        out.append({"repo": repo, "pushed": pushed, "line": line})
    if len(out) != MISSIONS:
        raise ValueError(f"need {MISSIONS} missions, got {len(out)}")
    ensure_no_markers(json.dumps(out))
    return out


CHANGE_VERBS = frozenset("""
add adds adjust align allow apply build builds bump cache change check clean compress convert copy crop cut
delete disable document drop enable extract fetch finish fix fixes format generate give handle hide implement
improve include install keep let link load lower make makes merge migrate move open polish port publish put
raise read rebuild record redo redraw reduce refactor remove rename render replace reset resize restore revert
rework rewrite run save scale send set ship show shorten simplify sort split start store swap switch test tidy
trim try tune turn tweak update upgrade use wrap write
built drew gave hid kept let made put ran rebuilt redid rewrote set shown wrote
""".split())


def says_what_changed(line: str) -> bool:
    """A Now line should open with what was done ('Added ...', 'Fix ...'), not
    with scenery ('Ice-Fire Island's steam rises ...')."""
    first = re.sub(r"[^a-z]", "", line.split(" ", 1)[0].lower())
    return first in CHANGE_VERBS or (len(first) > 3 and first.endswith("ed"))


def plain_line(candidate: Candidate) -> str:
    """The plain line for a repo: a recent commit subject that fits, opens with
    what was done and has no tell, else the repo description (no tell), else
    NO_NOTES."""
    def clean(raw: str, line: str) -> bool:
        return bool(line) and not voice_tells(raw) and not voice_tells(line) and not FICTION_WORDS.search(line)

    if not candidate.topped_up:
        for subject in candidate.subjects:
            if subject.startswith("Merge "):
                continue
            line = commit_line(subject)
            bare = SCOPE_TAG.sub("", subject)  # 'docs: fix x' is a scope tag, not a colon lead-in
            if 12 <= len(line) <= LINE_MAX and not line.endswith("...") and clean(bare, line) \
                    and says_what_changed(line):
                return line
    description = fit_line(candidate.description)
    return description if clean(candidate.description, description) else NO_NOTES


def parse_llm_payload(raw: str, candidates: list[Candidate]) -> dict:
    """The model's JSON, checked against the candidate list. Any repo outside
    the list or a duplicate rejects it all. A line with a tell (voice_tells) or
    the sect's story is swapped for that repo's plain line."""
    ensure_no_markers(raw)
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError("LLM payload is not a JSON object")
    missions = data.get("missions")
    if not isinstance(missions, list) or len(missions) < MISSIONS:
        raise ValueError(f"LLM payload needs {MISSIONS} missions, got "
                         f"{len(missions) if isinstance(missions, list) else 'none'}")
    by_name = {c.repo.casefold(): c for c in candidates}
    picked = []
    for mission in missions[:MISSIONS]:
        if not isinstance(mission, dict):
            raise ValueError("mission entry is not an object")
        repo, line = mission.get("repo"), mission.get("line")
        if not isinstance(repo, str) or repo.strip().casefold() not in by_name:
            raise ValueError(f"LLM picked a repo outside the candidates: {sanitize_line(str(repo), 60)!r}")
        if not isinstance(line, str) or not line.strip():
            raise ValueError("mission line missing")
        candidate = by_name[repo.strip().casefold()]
        tells = voice_tells(line) + voice_tells(fit_line(line))
        if FICTION_WORDS.search(line):
            tells.append("the sect's story or a name")
        if tells:
            plain = plain_line(candidate)
            print(f"WARNING: {candidate.repo}: model line dropped ({', '.join(sorted(set(tells)))}); "
                  f"using {plain!r}")
            line = plain
        picked.append({"repo": candidate.repo, "pushed": candidate.pushed, "line": fit_line(line)})
    return {"missions": finalize_missions(picked)}


def fallback_payload(candidates: list[Candidate]) -> dict:
    """The newest three candidates, in plain words, no LLM."""
    missions = [{"repo": c.repo, "pushed": c.pushed, "line": plain_line(c)} for c in candidates[:MISSIONS]]
    return {"missions": finalize_missions(missions)}


def scrub_missions(missions: list[dict], candidates: list[Candidate]) -> int:
    """Swap any kept line that has a tell (written before the filter existed, or
    edited by hand) for its repo's plain line. Returns how many were swapped."""
    by_name = {c.repo.casefold(): c for c in candidates}
    swapped = 0
    for mission in missions:
        tells = voice_tells(mission["line"])
        if FICTION_WORDS.search(mission["line"]):
            tells.append("the sect's story or a name")
        if not tells:
            continue
        candidate = by_name.get(mission["repo"].casefold())
        plain = plain_line(candidate) if candidate else NO_NOTES
        print(f"WARNING: {mission['repo']}: kept line dropped ({', '.join(tells)}); using {plain!r}")
        mission["line"] = plain
        swapped += 1
    return swapped


def refresh_dates(missions: list[dict], pushes: dict[str, str]) -> bool:
    """Move each posted repo's date forward if Bill pushed again. True if any moved."""
    moved = False
    for mission in missions:
        newer = pushes.get(mission["repo"])
        if newer and newer > mission["pushed"]:
            mission["pushed"] = newer
            moved = True
    return moved


def call_openai(candidates: list[Candidate], api_key: str) -> str:
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    rows = []
    for c in candidates:
        notes = "; ".join(sanitize_line(s, 100) for s in c.subjects) or (
            f"no commit subjects; repo description: {sanitize_line(c.description, 140) or 'none'}")
        rows.append(f"- {c.repo} (newest push {c.pushed}): {notes}")
    banned = ", ".join(TELL_WORDS[:40])
    prompt = f"""
Write the Now section of Bill Zhang's GitHub profile: one line for each of three repos he
pushed to recently, saying what he did there, from his real commit messages.
Return JSON only.

Schema: {{"missions": [{{"repo": "owner/name", "line": "..."}}]}}

Rules:
- missions: exactly 3, each repo copied exactly from the candidate list below.
- line: one short sentence, at most 64 characters, past tense, like a good commit
  message. Say the concrete thing that changed and name the real part of the project.
  Good: "Swapped the homepage MCP prompt for an install dropdown."
  Good: "Added barge-in to the realtime voice agent."
  Bad: "Updating sect background look with new visual elements." (vague)
  Bad: "Adding the PARANOIA music video to the repository." (filler)
- Plain words, the way a student tells a friend what he built. No jokes, no names, no
  hype, no metaphors, no story voice.
- Never use: em dashes, semicolons, colons, "not just", "X, not Y", "not X but Y",
  "rather than", lists of three, a question, a trailing ", making ..." clause, or these
  words: {banned}.
- English, plain ASCII, ends with a period. No emoji. Never invent a repo.

Candidates (repo, newest push, recent commit subjects):
{chr(10).join(rows)}
""".strip()

    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": ("You write short, plain changelog lines for a developer's "
                                           "GitHub profile. JSON only.")},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
        "response_format": {"type": "json_object"},
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "github-profile-readme-updater",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload["choices"][0]["message"]["content"]


# --- outputs -------------------------------------------------------------------------


def run_number() -> str:
    run = os.environ.get("GITHUB_RUN_NUMBER", "")
    return run if re.fullmatch(r"\d{1,9}", run or "") else "0"


def render_build_plate() -> str:
    """One HTML comment, invisible on the page: which run last touched the README.
    Only digits and hex go in, so it can never close the comment early."""
    sha = os.environ.get("GITHUB_SHA", "")
    sha = sha[:7] if re.fullmatch(r"[0-9a-f]{7,40}", sha) else "local"
    return ensure_no_markers(f"<!-- steward run {run_number()}, from {sha} -->")


def render_now(missions: list[dict], today: date) -> str:
    """One <p>: three lines joined by <br>. Every URL is built here from a
    checked repo name; all text is escaped."""
    attr = lambda s: html.escape(s, quote=True)  # noqa: E731
    esc = lambda s: html.escape(s, quote=False)  # noqa: E731  (text: an apostrophe stays an apostrophe)
    lines = []
    for mission in finalize_missions(missions):
        owner, name = mission["repo"].split("/", 1)
        shown = name if owner == USERNAME else mission["repo"]
        url = f"https://github.com/{mission['repo']}"
        lines.append(f'<b><a href="{attr(url)}">{esc(shown)}</a></b> · {esc(show_date(mission["pushed"], today))}'
                     f' · {esc(mission["line"])}')
    return ensure_no_markers("<p>" + "<br>\n".join(lines) + "</p>")


def safe_replace_block(readme_path: str, start: str, end: str, content: str, label: str) -> None:
    try:
        changed = replace_block(readme_path, start, end, content)
    except (ValueError, OSError) as error:
        print(f"WARNING: skipped {label} block: {error}")
        return
    print(f"Updated {label} block" if changed else f"{label} block already current")


def read_status(path: str) -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def load_previous_status(path: str) -> dict | None:
    """The last good status.json, re-gated, with its original timestamp; None if
    there is nothing usable (an older schema counts as nothing). Used when the
    LLM is down, so a bad API day keeps the real lines instead of canned ones."""
    data = read_status(path)
    try:
        missions = finalize_missions(data.get("missions"))
    except (ValueError, TypeError, AttributeError):
        return None
    payload: dict = {"missions": missions}
    if isinstance(data.get("updated"), str):
        payload["updated"] = data["updated"]
    return payload


def write_status_json(payload: dict, now: datetime | None, path: str = STATUS_PATH) -> None:
    """now=None writes no fresh timestamp: reused lines keep their own, and a
    plain fallback gets none."""
    status: dict = {"missions": payload["missions"]}
    if now is not None:
        status["updated"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    elif "updated" in payload:
        status["updated"] = payload["updated"]
    target = Path(path)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    except OSError as error:
        print(f"WARNING: could not write {path}: {error}")
        return
    print(f"Wrote {path}:")
    print(json.dumps(status, indent=2, ensure_ascii=True))


def write_github_output(message: str) -> None:
    """The commit message, plain like Bill's own: 'Update the Now section (steward run N)'."""
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    message = sanitize_line(message, 120)
    try:
        with open(output_path, "a", encoding="utf-8") as handle:
            handle.write(f"msg={message}\n")
    except OSError as error:
        print(f"WARNING: could not write GITHUB_OUTPUT: {error}")


def dates_only(args: argparse.Namespace, token: str | None, today: date) -> None:
    previous = load_previous_status(args.status)
    if previous is None:
        print("WARNING: no usable status.json; nothing to re-date")
        return
    try:
        pushes = fetch_push_dates(token)
    except Exception as error:  # a bad API day changes nothing
        print(f"WARNING: GitHub activity unavailable ({error}); dates left as they were")
        return
    moved = refresh_dates(previous["missions"], pushes)
    safe_replace_block(args.readme, NOW_START, NOW_END, render_now(previous["missions"], today), "NOW")
    if moved:
        write_status_json(previous, None, args.status)
    else:
        print("no posted repo was pushed again; status.json left as it was")


def self_test() -> None:
    """Offline checks of the voice filter and the line rules. No network, no files."""
    with_tells = (
        "Refined the hero — now it breathes.",
        "Reworked the board -- simpler and faster.",
        "Cleaned up the parser; tests pass now.",
        "The fix: a smaller cache.",
        "It's not a portfolio, it's a sect.",
        "Not a rewrite, but a polish of the agent.",
        "Swapped the cache, not the database.",
        "Less config, more defaults in the CLI.",
        "Added auth, rate limits, and logging.",
        "Why rewrite it? Speed.",
        "Moved search to Pinecone, making lookups fast.",
        "Updating sect background look with new visual elements.",
        "Adding PARANOIA music video to the repository.",
        "Quietly reworked the voice agent.",
        "Delved into the realtime API.",
        "Made the deploy seamless.",
        "Not just a bug fix for the board.",
        "Leveraged Retell for the phone agent.",
        "Added new features to the site.",
    )
    for line in with_tells:
        assert voice_tells(line), f"missed a tell: {line!r}"
    plain = (
        "Swapped the homepage MCP prompt for an install dropdown.",
        "Added barge-in to the realtime voice agent.",
        "Fixed funny bug if ingredient contained a comma.",
        "Made the sect gate load faster on phones.",
        "Added the PARANOIA music video.",
        "Moved the scene bake to a rented GPU.",
        "Basic model has 90% accuracy, forced to use that.",
        "Rebuilt the stair at the mountain gate.",
        "Real-time bus tracker for UCSC.",
        NO_NOTES,
    )
    for line in plain:
        assert not voice_tells(line), f"false alarm on {line!r}: {voice_tells(line)}"

    # A model line with a tell falls back to its repo's plain line; a clean one stays.
    cands = [Candidate("IdkwhatImD0ing/a", "2026-10-20", ["docs: add the install dropdown to the homepage"]),
             Candidate("IdkwhatImD0ing/b", "2026-10-19", ["/sect round 48 slice: the canopy grows; it is load-bearing"],
                       description="Voice agent for 911 dispatch"),
             Candidate("IdkwhatImD0ing/c", "2026-10-18", [], description="")]
    raw = json.dumps({"missions": [
        {"repo": "IdkwhatImD0ing/a", "line": "Quietly elevating the homepage — a seamless journey."},
        {"repo": "IdkwhatImD0ing/b", "line": "Added barge-in to the realtime voice agent."},
        {"repo": "IdkwhatImD0ing/c", "line": "Not just a demo, but a platform."},
    ]})
    lines = [m["line"] for m in parse_llm_payload(raw, cands)["missions"]]
    assert lines == ["Add the install dropdown to the homepage.", "Added barge-in to the realtime voice agent.",
                     NO_NOTES], lines
    # The plain line skips a commit subject with a tell and uses the description.
    assert plain_line(cands[1]) == "Voice agent for 911 dispatch.", plain_line(cands[1])
    # ... and a subject that is scenery rather than a change.
    scenery = Candidate("IdkwhatImD0ing/d", "2026-10-17", ["Ice-Fire Island's steam rises from the volcano's crater",
                                                           "Moved the steam vent onto the crater"])
    assert plain_line(scenery) == "Moved the steam vent onto the crater.", plain_line(scenery)
    # A repo outside the list still rejects the whole payload.
    try:
        parse_llm_payload(json.dumps({"missions": [{"repo": "someone/else", "line": "Added x."}] * 3}), cands)
    except ValueError:
        pass
    else:
        raise AssertionError("a repo outside the candidates must reject the payload")
    # Kept lines from before the filter are scrubbed the same way.
    kept = [{"repo": "IdkwhatImD0ing/a", "pushed": "2026-10-20",
             "line": "Updating sect background look with new visual elements."},
            {"repo": "IdkwhatImD0ing/b", "pushed": "2026-10-19", "line": "Added barge-in to the realtime voice agent."}]
    assert scrub_missions(kept, cands) == 1 and kept[0]["line"] == "Add the install dropdown to the homepage."
    # The build plate is an HTML comment that can never close early or carry a marker.
    plate = render_build_plate()
    assert plate.startswith("<!-- steward run ") and plate.endswith(" -->") and plate.count("--") == 2
    assert not MARKER_RE.search(plate)
    print("steward self-test: all assertions passed")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--readme", default="README.md")
    parser.add_argument("--status", default=STATUS_PATH, help="where to read and write status.json (testing)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--fallback-only", action="store_true", help="no LLM: the plain lines")
    mode.add_argument("--dates-only", action="store_true", help="no LLM: only move the posted dates forward")
    mode.add_argument("--self-test", action="store_true", help="check the voice filter and the line rules, offline")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return

    github_token = os.environ.get("GITHUB_TOKEN")
    openai_key = os.environ.get("OPENAI_API_KEY")
    require_openai = os.environ.get("REQUIRE_OPENAI", "0") == "1"
    now = datetime.now(timezone.utc)
    today = now.date()

    if args.dates_only:
        dates_only(args, github_token, today)
        return

    try:
        candidates = fetch_candidates(github_token)
    except Exception as error:  # A bad API day must never blank the README.
        print(f"WARNING: GitHub activity unavailable: {error}")
        candidates = []
    print(f"candidates: {', '.join(f'{c.repo} {c.pushed}' for c in candidates) or 'none'}")

    payload: dict | None = None
    if args.fallback_only:
        pass
    elif openai_key:
        if len(candidates) >= MISSIONS:
            try:
                payload = parse_llm_payload(call_openai(candidates, openai_key), candidates)
            except Exception as error:
                print(f"WARNING: OpenAI generation rejected ({error}); keeping the previous lines")
        else:
            print(f"WARNING: only {len(candidates)} candidate repos; the steward was not asked")
    elif require_openai:
        raise RuntimeError("OPENAI_API_KEY is required when REQUIRE_OPENAI=1")

    stamp: datetime | None = now
    message = f"Update the Now section (steward run {run_number()})"
    if payload is None and not args.fallback_only:
        payload = load_previous_status(args.status)
        stamp = None
        message = f"Keep the Now section, no LLM this time (steward run {run_number()})"
        if payload is not None:
            refresh_dates(payload["missions"], {c.repo: c.pushed for c in candidates if not c.topped_up})
            if scrub_missions(payload["missions"], candidates):
                message = f"Update the Now section from commit messages (steward run {run_number()})"
    if payload is None:
        stamp = None
        try:
            payload = fallback_payload(candidates)
            message = f"Update the Now section from commit messages (steward run {run_number()})"
        except ValueError as error:
            print(f"WARNING: no fallback ({error}); the NOW block and status.json are left alone")
            message = f"Keep the Now section, no LLM this time (steward run {run_number()})"

    plate = render_build_plate()
    print(f"--- BUILD_PLATE ---\n  {plate}")
    safe_replace_block(args.readme, PLATE_START, PLATE_END, plate, "BUILD_PLATE")
    if payload is not None:
        now_block = render_now(payload["missions"], today)
        print(f"--- NOW ---\n{now_block}")
        safe_replace_block(args.readme, NOW_START, NOW_END, now_block, "NOW")
        write_status_json(payload, stamp, args.status)
    write_github_output(message)


if __name__ == "__main__":
    main()
