"""The steward: posts what Bill is working on now, twice a week.

The steward is an LLM. It reads Bill's real public GitHub activity, picks the
three repos he is working on, and writes one plain sentence for each. Those
three lines are the README's Now section (the NOW block) and live in
assets/status.json:

    {"obsession": "2-4 words",
     "missions": [{"repo": "owner/name", "pushed": "YYYY-MM-DD", "line": "Building ..."}],
     "updated": "YYYY-MM-DDTHH:MM:SSZ"}

"obsession" (what the Sect Leader is in closed-door cultivation on) is read by
generate_ansi_card.py for bill.ansi; it never shows on the page.

Honesty rules. Candidates are only repos Bill pushed to, from the public
events feed, never the profile repo itself. The LLM may only pick from that
list; one repo outside it rejects the whole payload. The date on each line is
Bill's newest push, from the feed, never from the model. With fewer than 3
candidates the list is topped up from his public repos by last push (no forks,
nothing archived).

When the model is unreachable or returns junk, the previous status.json is
kept (its dates refreshed from the feed); only when there is no usable
previous one, or with --fallback-only, a deterministic fallback built from the
same candidates takes over (each line: a recent commit subject, else the repo
description, else an excuse). With fewer than 3 repos in hand the NOW block
is left alone.

--dates-only (the Saturday moon watch): no LLM. Re-read the feed, move each
posted repo's date forward if Bill pushed again, re-render the NOW block.
status.json is rewritten only if a date moved; BUILD_PLATE is not touched.

Also owns the BUILD_PLATE block: one plain line inside the Play fold's <pre>.
It changes every normal run, so the Mon/Thu run always commits: that commit is
the keepalive that stops GitHub from switching off the scheduled workflows.

Contract: never blank anything. status.json is only rewritten after the whole
payload validated; a missing marker is a warning, not a crash; any API failure
warns and exits 0. Run from the repo root:
    python scripts/update_currently_building.py --fallback-only
    python scripts/update_currently_building.py --dates-only
    python scripts/update_currently_building.py --readme .preview/README.md --status .preview/status.json
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
OBSESSION_MAX = 48
REPO_RE = re.compile(r"^[A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}$")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

FALLBACK_OBSESSION = "voice agents"
NO_NOTES = "the steward has no notes on this one yet."
# The steward's own fiction stays out of the Now lines (the work itself may
# still be about a sect scene, so the bare word "sect" is allowed).
FICTION_WORDS = re.compile(r"\b(steward|elders?|disciples?|cultivat\w*|qi|sect leader|bill)\b", re.I)
SCOPE_TAG = re.compile(r"^(?:[\w./-]+(?:\([^)]*\))?!?):\s+")


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


def clean_obsession(value: str) -> str:
    """At most 4 whole words and OBSESSION_MAX chars (never cut mid-word)."""
    kept: list[str] = []
    for word in sanitize_line(value, 240).split()[:4]:
        if len(" ".join(kept + [word])) > OBSESSION_MAX:
            break
        kept.append(word)
    return " ".join(kept) or sanitize_line(value, OBSESSION_MAX)


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


def parse_llm_payload(raw: str, candidates: list[Candidate]) -> dict:
    """The model's JSON, checked against the candidate list. Any repo outside
    the list, a duplicate, or a line that breaks the rules rejects it all."""
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
        line = fit_line(line)
        first = line.split(" ", 1)[0].lower()
        if not first.endswith("ing"):
            raise ValueError(f"line does not start with an -ing verb: {line!r}")
        if FICTION_WORDS.search(line):
            raise ValueError(f"line uses the steward's fiction or a name: {line!r}")
        candidate = by_name[repo.strip().casefold()]
        picked.append({"repo": candidate.repo, "pushed": candidate.pushed, "line": line})
    obsession = data.get("obsession")
    if not isinstance(obsession, str) or not obsession.strip():
        raise ValueError("LLM payload obsession missing")
    return {"missions": finalize_missions(picked), "obsession": clean_obsession(obsession) or FALLBACK_OBSESSION}


def fallback_line(candidate: Candidate) -> str:
    if not candidate.topped_up:
        for subject in candidate.subjects:
            if subject.startswith("Merge "):
                continue
            line = commit_line(subject)
            if 12 <= len(line) <= LINE_MAX and not line.endswith("..."):
                return line
    return fit_line(candidate.description) or NO_NOTES


def fallback_payload(candidates: list[Candidate], obsession: str) -> dict:
    """The newest three candidates, in plain words, no LLM."""
    missions = [{"repo": c.repo, "pushed": c.pushed, "line": fallback_line(c)} for c in candidates[:MISSIONS]]
    return {"missions": finalize_missions(missions), "obsession": clean_obsession(obsession) or FALLBACK_OBSESSION}


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
    prompt = f"""
You are the steward of the Sun Moon Divine Sect, a fictional sect whose grounds are
Bill Zhang's GitHub profile. Twice a week you post what Bill is working on, from his
real public activity. Return STRICT JSON only.

Schema: {{"missions": [{{"repo": "owner/name", "line": "..."}}], "obsession": "2-4 words"}}

Rules:
- missions: exactly 3, each repo copied exactly from the candidate list below.
- line: one plain sentence, at most 64 characters, starting with an -ing verb, saying
  what the work in that repo is, grounded in its commit messages. No jokes, no names,
  no sect words. Plain ASCII. Ends with a period.
  Example: "Adding barge-in to a realtime voice agent."
- obsession: 2-4 words: what the sect leader is in closed-door cultivation on.
- English only. No emoji. No private data. Never invent a repo.

Candidates (repo, newest push, recent commit subjects):
{chr(10).join(rows)}
""".strip()

    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": ("You output strict JSON for the Now section of a developer's "
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
    """One plain line for inside the Play fold's <pre> (so: html-escaped, no markdown)."""
    sha = os.environ.get("GITHUB_SHA", "")
    sha = sha[:7] if re.fullmatch(r"[0-9a-f]{7,40}", sha) else "local"
    line = f"sealed by the steward · run {run_number()} · from {sha} · the human contributes"
    return ensure_no_markers(html.escape(line, quote=False))


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
    payload = {"missions": missions,
               "obsession": clean_obsession(str(data.get("obsession", ""))) or FALLBACK_OBSESSION}
    if isinstance(data.get("updated"), str):
        payload["updated"] = data["updated"]
    return payload


def write_status_json(payload: dict, now: datetime | None, path: str = STATUS_PATH) -> None:
    """now=None writes no fresh timestamp: reused lines keep their own, and a
    canned fallback gets none."""
    status = {"obsession": payload["obsession"], "missions": payload["missions"]}
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
    """The commit message. Only a real rewrite starts with 'steward N:'."""
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--readme", default="README.md")
    parser.add_argument("--status", default=STATUS_PATH, help="where to read and write status.json (testing)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--fallback-only", action="store_true", help="no LLM: the deterministic lines")
    mode.add_argument("--dates-only", action="store_true", help="no LLM: only move the posted dates forward")
    args = parser.parse_args()

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
    message = f"steward {run_number()}: reposted the missions around {{obsession}}, kept the good ones"
    if payload is None and not args.fallback_only:
        payload = load_previous_status(args.status)
        stamp = None
        message = f"steward: the ink ran dry, kept the old missions (run {run_number()})"
        if payload is not None:
            refresh_dates(payload["missions"], {c.repo: c.pushed for c in candidates if not c.topped_up})
    if payload is None:
        stamp = None
        previous_obsession = str(read_status(args.status).get("obsession", ""))
        try:
            payload = fallback_payload(candidates, previous_obsession)
            message = f"steward: the ink ran dry, posted the standing missions (run {run_number()})"
        except ValueError as error:
            print(f"WARNING: no fallback ({error}); the NOW block and status.json are left alone")
            message = f"steward: the ink ran dry, kept the old missions (run {run_number()})"

    plate = render_build_plate()
    print(f"--- BUILD_PLATE ---\n  {plate}")
    safe_replace_block(args.readme, PLATE_START, PLATE_END, plate, "BUILD_PLATE")
    if payload is not None:
        now_block = render_now(payload["missions"], today)
        print(f"--- NOW ---\n{now_block}")
        safe_replace_block(args.readme, NOW_START, NOW_END, now_block, "NOW")
        write_status_json(payload, stamp, args.status)
        message = message.format(obsession=payload["obsession"])
    write_github_output(message.replace("{obsession}", FALLBACK_OBSESSION))


if __name__ == "__main__":
    main()
