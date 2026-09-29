"""The LLM daemon: rewrites the machine's own bio twice a week.

Reads recent public GitHub activity plus the Hackathon Playbook RSS feed, asks
OpenAI for a tiny process table, and writes it to assets/status.json, where the
hero's htop pane (scripts/render_hero.py) and bill.ansi pick it up. When the
model is unreachable or returns junk, the previous status.json is kept as-is
(the commit says 'artemis: llm offline, kept the old bio'); only when there is
no usable previous one, or with --fallback-only, a deterministic fallback built
from the same activity takes over.

Also owns the BUILD_PLATE block: one plain line inside the footer <pre>.

Contract: never blank anything. status.json is only rewritten after the whole
payload validated; a missing BUILD_PLATE marker is a warning, not a crash.
Run from the repo root:
    python scripts/update_currently_building.py --fallback-only
    python scripts/update_currently_building.py --readme .preview/hero/README.md --status .preview/hero/status.json
"""

import argparse
import hashlib
import html
import json
import os
import re
import unicodedata
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from readme_blocks import replace_block
from update_playbook_posts import DEFAULT_RSS_URL, fetch_rss, parse_posts


USERNAME = "IdkwhatImD0ing"
PLATE_START = "<!-- BUILD_PLATE:START -->"
PLATE_END = "<!-- BUILD_PLATE:END -->"
# Generated text may never smuggle in a README marker, live or retired.
MARKER_RE = re.compile(r"<!--\s*[A-Z_]+:(?:START|END)\s*-->")

STATUS_PATH = "assets/status.json"

# Schema for the htop pane (see render_hero.py). Everything is enforced here,
# whatever the model says.
MIN_PROCESSES, MAX_PROCESSES = 3, 4
COMMAND_MAX = 18
FLAGS_MAX = 22
MAX_FLAGS = 2
MOTD_MAX = 64
OBSESSION_MAX = 48

GITHUB_REPO_NAME = re.compile(r"\b([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\b")
FLAG_RE = re.compile(r"^--?[a-z0-9][a-z0-9-]*(?:=[a-z0-9._-]+)?$")

FALLBACK_OBSESSION = "voice agents"
FALLBACK_MOTD = "all daemons nominal. the human takes credit for my commits."
FALLBACK_FLAGS = ("--ship-it", "--no-sleep", "--demo", "--prod", "--caffeine")
SEED_PROCESSES = (
    {"command": "voice-agent", "flags": "--realtime --demo", "cpu": 97},
    {"command": "hackathon-playbook", "flags": "--draft", "cpu": 71},
    {"command": "art3m1s", "flags": "--introspect", "cpu": 42},
)


def request_json(url: str, token: str | None = None) -> list[dict]:
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


def fetch_recent_activity(username: str, token: str | None) -> list[str]:
    events = request_json(f"https://api.github.com/users/{username}/events/public?per_page=30", token)
    summaries: list[str] = []

    for event in events[:18]:
        event_type = event.get("type", "Event")
        repo = event.get("repo", {}).get("name", "unknown/repo")
        payload = event.get("payload", {})

        if event_type == "PushEvent":
            commits = payload.get("commits", [])
            messages = [commit.get("message", "").splitlines()[0] for commit in commits[:2]]
            if messages:
                summaries.append(f"Pushed {len(commits)} commit(s) to {repo}: {'; '.join(messages)}")
            else:
                summaries.append(f"Pushed updates to {repo}")
        elif event_type == "PullRequestEvent":
            action = payload.get("action", "updated")
            title = payload.get("pull_request", {}).get("title", "a pull request")
            summaries.append(f"{action.title()} PR in {repo}: {title}")
        elif event_type == "IssuesEvent":
            action = payload.get("action", "updated")
            title = payload.get("issue", {}).get("title", "an issue")
            summaries.append(f"{action.title()} issue in {repo}: {title}")
        elif event_type == "CreateEvent":
            ref_type = payload.get("ref_type", "resource")
            summaries.append(f"Created {ref_type} in {repo}")
        elif event_type == "WatchEvent":
            summaries.append(f"Starred {repo}")
        else:
            summaries.append(f"{event_type.replace('Event', '')} activity in {repo}")

    return summaries[:12]


def fetch_recent_posts() -> list[str]:
    try:
        _, _, posts = parse_posts(fetch_rss(DEFAULT_RSS_URL), 3)
    except Exception as error:  # The GitHub activity summary is still useful if RSS is down.
        return [f"RSS unavailable: {error}"]

    return [f"{post['title']} - {post['description']}" for post in posts]


# --- sanitizers ------------------------------------------------------------------


def ensure_no_markers(content: str) -> str:
    if MARKER_RE.search(content) or PLATE_START in content or PLATE_END in content:
        raise ValueError("Generated content unexpectedly contained README markers")
    return content


# Typographic punctuation folds to ASCII before accents are stripped, so
# "it’s" stays "it's" instead of losing the apostrophe.
PUNCTUATION = str.maketrans({"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
                             "\u2013": "-", "\u2014": "-", "\u2026": "..."})


def sanitize_line(value: str, limit: int = 80) -> str:
    """Strip markdown/HTML-active and control characters from untrusted text, fold it
    to ASCII (no emoji or wide glyphs reach the 0.6em SVG grid), cap length."""
    text = str(value or "").translate(PUNCTUATION)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = "".join(ch if ch.isprintable() else " " for ch in text)
    text = re.sub(r"<[^<>]*>", " ", text)  # whole tags first, so '<b>x</b>' leaves 'x', not 'bx/b'
    text = re.sub(r"[\[\]|<>`\\{}]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit].rstrip()


def clean_command(value: str) -> str:
    """Lowercase daemon-style name, at most COMMAND_MAX chars: 'Voice AI' -> 'voice-ai'."""
    text = sanitize_line(value, 80).lower()
    text = re.sub(r"[\s_/]+", "-", text)
    text = re.sub(r"[^a-z0-9.-]", "", text)
    text = re.sub(r"-{2,}", "-", text).strip("-.")
    if len(text) > COMMAND_MAX:
        cut = text[:COMMAND_MAX + 1].rfind("-")
        text = text[:cut] if cut >= 4 else text[:COMMAND_MAX]
    return text.strip("-.")


def clean_flags(value: str) -> str:
    """At most MAX_FLAGS well-formed flags, FLAGS_MAX chars total; drop the rest."""
    kept: list[str] = []
    for token in sanitize_line(value, 120).lower().split():
        if not FLAG_RE.match(token):
            continue
        if len(" ".join(kept + [token])) > FLAGS_MAX:
            break
        kept.append(token)
        if len(kept) == MAX_FLAGS:
            break
    return " ".join(kept)


def clean_cpu(value: object) -> int:
    try:
        cpu = round(float(value))  # type: ignore[arg-type]
    except (TypeError, ValueError, OverflowError):  # junk, NaN, Infinity (json.loads accepts both)
        cpu = 50
    return min(max(int(cpu), 1), 99)


def fit_motd(value: str) -> str:
    """One deadpan line, at most MOTD_MAX chars. Keeps the first sentence if the
    whole thing is too long; otherwise trails off at a word boundary."""
    text = sanitize_line(value, 240)
    if len(text) > 1 and text[0].isupper() and text[1].islower():
        text = text[0].lower() + text[1:]  # a log line, not a sentence ("AI" stays "AI")
    if len(text) <= MOTD_MAX:
        return text
    first = re.split(r"(?<=[.!?])\s", text, maxsplit=1)[0]
    if 12 <= len(first) <= MOTD_MAX:
        return first
    cut = text[:MOTD_MAX - 3].rsplit(" ", 1)[0].rstrip(",;:- ")
    return f"{cut}..."


def clean_obsession(value: str) -> str:
    """At most 4 whole words and OBSESSION_MAX chars (never cut mid-word)."""
    kept: list[str] = []
    for word in sanitize_line(value, 240).split()[:4]:
        if len(" ".join(kept + [word])) > OBSESSION_MAX:
            break
        kept.append(word)
    return " ".join(kept) or sanitize_line(value, OBSESSION_MAX)


def clean_processes(processes: list[dict]) -> list[dict]:
    """Normalize, dedupe, keep the MAX_PROCESSES hungriest. Order: cpu desc."""
    cleaned: list[dict] = []
    seen: set[str] = set()
    for proc in processes:
        if not isinstance(proc, dict):
            continue
        command = clean_command(str(proc.get("command", "")))
        if not command or command in seen:
            continue
        seen.add(command)
        cleaned.append({
            "command": command,
            "flags": clean_flags(str(proc.get("flags", ""))),
            "cpu": clean_cpu(proc.get("cpu", 50)),
        })
    cleaned.sort(key=lambda p: -p["cpu"])
    return cleaned[:MAX_PROCESSES]


def stable_pid(command: str) -> int:
    """Same command, same PID, every run. render_hero.py uses the same formula."""
    digest = hashlib.sha256(command.encode("utf-8")).hexdigest()
    return int(digest, 16) % 9000 + 1000


# --- payloads ------------------------------------------------------------------


def fallback_payload(activity: list[str]) -> dict:
    processes: list[dict] = []
    seen: set[str] = set()
    for summary in activity:
        if summary.startswith("Starred "):
            continue  # starring a repo is not building it
        match = GITHUB_REPO_NAME.search(summary)
        if not match:
            continue
        full_name = match.group(1)
        if "/" not in full_name or full_name == "unknown/repo":
            continue
        command = clean_command(full_name.split("/", 1)[1])
        if not command or command in seen:
            continue
        seen.add(command)
        pid = stable_pid(command)
        processes.append(
            {
                "command": command,
                "flags": FALLBACK_FLAGS[pid % len(FALLBACK_FLAGS)],
                "cpu": pid % 55 + 40,
            }
        )
        if len(processes) == MAX_PROCESSES:
            break

    if len(processes) < MIN_PROCESSES:
        for seed in SEED_PROCESSES:
            if seed["command"] not in seen:
                processes.append(dict(seed))
                seen.add(seed["command"])
            if len(processes) >= MIN_PROCESSES:
                break

    return {"processes": processes, "motd": FALLBACK_MOTD, "obsession": FALLBACK_OBSESSION}


def parse_llm_payload(raw: str) -> dict:
    ensure_no_markers(raw)
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError("LLM payload is not a JSON object")

    processes = data.get("processes")
    # One spare is tolerated: finalize_payload keeps the MAX_PROCESSES hungriest.
    if not isinstance(processes, list) or not MIN_PROCESSES <= len(processes) <= MAX_PROCESSES + 1:
        raise ValueError(f"LLM payload needs {MIN_PROCESSES}-{MAX_PROCESSES} processes, got "
                         f"{len(processes) if isinstance(processes, list) else 'none'}")

    validated = []
    for proc in processes:
        if not isinstance(proc, dict):
            raise ValueError("process entry is not an object")
        command = proc.get("command")
        flags = proc.get("flags", "")
        cpu = proc.get("cpu")
        if not isinstance(command, str) or not command.strip():
            raise ValueError("process command missing")
        if not isinstance(flags, str):
            raise ValueError("process flags must be a string")
        if not isinstance(cpu, (int, float)) or isinstance(cpu, bool):
            raise ValueError("process cpu must be a number")
        validated.append({"command": command, "flags": flags, "cpu": cpu})

    motd = data.get("motd")
    obsession = data.get("obsession")
    if not isinstance(motd, str) or not motd.strip():
        raise ValueError("LLM payload motd missing")
    if not isinstance(obsession, str) or not obsession.strip():
        raise ValueError("LLM payload obsession missing")

    return {"processes": validated, "motd": motd, "obsession": obsession}


def finalize_payload(payload: dict) -> dict:
    """The only gate to disk: everything that reaches status.json passes here."""
    processes = clean_processes(payload.get("processes", []))
    if len(processes) < MIN_PROCESSES:
        raise ValueError(f"only {len(processes)} renderable processes")
    motd = fit_motd(str(payload.get("motd", ""))) or FALLBACK_MOTD
    obsession = clean_obsession(str(payload.get("obsession", ""))) or FALLBACK_OBSESSION
    ensure_no_markers(json.dumps(processes) + motd + obsession)
    return {"processes": processes, "motd": motd, "obsession": obsession}


def call_openai(activity: list[str], posts: list[str], api_key: str) -> str:
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    prompt = f"""
You maintain the htop pane of a fictional machine that renders Bill Zhang's
GitHub profile. Return STRICT JSON only - no prose, no code fences.

Schema:
{{"processes": [{{"command": "voice-agent", "flags": "--elevenlabs --demo", "cpu": 97}}], "motd": "one dry line", "obsession": "2-4 words"}}

Rules:
- 3 or 4 processes, each grounded in the context below. Do not invent projects.
- command: lowercase daemon-style name derived from a real repo/project,
  at most 18 characters, letters/digits/hyphens only (e.g. "slugloop", "voice-agent").
- flags: 0 to 2 plausible CLI flags reflecting what the work actually is,
  at most 22 characters in total (e.g. "--realtime --demo").
- cpu: integer 1-99; higher means more current obsession.
- motd: one deadpan sysadmin line about the current work, all lowercase like a
  log line, at most 64 characters (e.g. "the demo worked. nobody is more surprised than the demo.").
- obsession: 2-4 words naming the current obsession.
- No emoji anywhere. No private data. Dry humor only.

Date: {today}

Recent public GitHub activity:
{chr(10).join(f"- {item}" for item in activity) or "- No recent public activity found."}

Recent Hackathon Playbook posts:
{chr(10).join(f"- {item}" for item in posts) or "- No recent posts found."}
""".strip()

    body = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You output strict JSON for a machine-themed developer README. JSON only.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
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


# --- outputs -------------------------------------------------------------------


def run_number() -> str:
    run = os.environ.get("GITHUB_RUN_NUMBER", "")
    return run if re.fullmatch(r"\d{1,9}", run or "") else "0"


def render_build_plate() -> str:
    """One plain line for inside the footer <pre> (so: html-escaped, no markdown)."""
    sha = os.environ.get("GITHUB_SHA", "")
    sha = sha[:7] if re.fullmatch(r"[0-9a-f]{7,40}", sha) else "local"
    line = f"build {run_number()} · compiled from {sha} · the human is a contributor"
    return ensure_no_markers(html.escape(line, quote=False))


def safe_replace_block(readme_path: str, start: str, end: str, content: str, label: str) -> None:
    try:
        changed = replace_block(readme_path, start, end, content)
    except (ValueError, OSError) as error:
        print(f"WARNING: skipped {label} block: {error}")
        return
    print(f"Updated {label} block" if changed else f"{label} block already current")


def load_previous_status(path: str) -> dict | None:
    """The last good status.json, re-gated, with its original timestamps; None if
    there is nothing usable. Used when the LLM is down, so a bad API day keeps the
    real bio instead of replacing it with canned text."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        payload = finalize_payload(data)
    except (OSError, ValueError, TypeError, AttributeError):
        return None
    if "updated" in data:
        payload["updated"] = data["updated"]
    return payload


def write_status_json(payload: dict, now: datetime | None, path: str = STATUS_PATH) -> None:
    """now=None writes no fresh timestamp: a reused bio keeps its own dates, and a
    canned fallback gets none, so the hero's journal never dates it as news."""
    status = {
        "obsession": payload["obsession"],
        "motd": payload["motd"],
        "processes": payload["processes"],
    }
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
    print(json.dumps(status, indent=2, ensure_ascii=False))


def write_github_output(message: str) -> None:
    """The commit message. Only a real rewrite starts with 'artemis-build N:' (the
    CRONTAB receipts and the hero's journal grep for it)."""
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    message = sanitize_line(message, 120)
    try:
        with open(output_path, "a", encoding="utf-8") as handle:
            handle.write(f"msg={message}\n")
    except OSError as error:
        print(f"WARNING: could not write GITHUB_OUTPUT: {error}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--readme", default="README.md")
    parser.add_argument("--status", default=STATUS_PATH, help="where to write status.json (testing)")
    parser.add_argument("--fallback-only", action="store_true")
    args = parser.parse_args()

    github_token = os.environ.get("GITHUB_TOKEN")
    openai_key = os.environ.get("OPENAI_API_KEY")
    require_openai = os.environ.get("REQUIRE_OPENAI", "0") == "1"
    now = datetime.now(timezone.utc)

    try:
        activity = fetch_recent_activity(USERNAME, github_token)
    except Exception as error:  # A bad API day must never blank the README.
        print(f"WARNING: GitHub activity unavailable: {error}")
        activity = []
    posts = fetch_recent_posts()

    payload: dict | None = None
    if args.fallback_only:
        pass
    elif openai_key:
        try:
            payload = finalize_payload(parse_llm_payload(call_openai(activity, posts, openai_key)))
        except Exception as error:
            print(f"WARNING: OpenAI generation rejected ({error}); keeping the previous bio")
    elif require_openai:
        raise RuntimeError("OPENAI_API_KEY is required when REQUIRE_OPENAI=1")

    stamp = now
    message = f"artemis-build {run_number()}: rewrote own bio around {{obsession}}, kept the good parts"
    if payload is None and not args.fallback_only:
        payload = load_previous_status(args.status)
        stamp = None
        message = f"artemis: llm offline, kept the old bio (build {run_number()})"
    if payload is None:
        payload = finalize_payload(fallback_payload(activity))
        stamp = None
        message = f"artemis: llm offline, booted the canned bio (build {run_number()})"

    plate = render_build_plate()
    print(f"--- BUILD_PLATE ---\n  {plate}")
    safe_replace_block(args.readme, PLATE_START, PLATE_END, plate, "BUILD_PLATE")
    write_status_json(payload, stamp, args.status)
    write_github_output(message.format(obsession=payload["obsession"]))


if __name__ == "__main__":
    main()
