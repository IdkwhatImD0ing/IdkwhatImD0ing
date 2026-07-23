import argparse
import hashlib
import json
import math
import os
import re
import textwrap
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from readme_blocks import replace_block
from update_playbook_posts import DEFAULT_RSS_URL, fetch_rss, parse_posts


USERNAME = "IdkwhatImD0ing"
START = "<!-- CURRENTLY_BUILDING:START -->"
END = "<!-- CURRENTLY_BUILDING:END -->"
MOTD_START = "<!-- MOTD:START -->"
MOTD_END = "<!-- MOTD:END -->"
PLATE_START = "<!-- BUILD_PLATE:START -->"
PLATE_END = "<!-- BUILD_PLATE:END -->"
ALL_MARKERS = (START, END, MOTD_START, MOTD_END, PLATE_START, PLATE_END)

STATUS_PATH = "assets/status.json"
ACCOUNT_CREATED = datetime(2021, 9, 21, tzinfo=timezone.utc)

# Synodic month math: reference new moon 2000-01-06 18:14 UTC. ART3M1S tracks
# the actual moon — Artemis is a moon program, after all.
NEW_MOON_EPOCH = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)
SYNODIC_DAYS = 29.530588853

GITHUB_REPO_URL = re.compile(r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/?$")
REPO_IN_SUMMARY = re.compile(r"\b([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\b")

FALLBACK_OBSESSION = "voice agents"
FALLBACK_MOTD = "all daemons nominal. the human keeps taking credit for my commits."
FALLBACK_FLAGS = ("--ship-it", "--no-sleep", "--demo", "--prod", "--caffeine")
SEED_PROCESSES = (
    {"command": "voice-agent", "flags": "--realtime --demo", "repo_url": "", "cpu": 97},
    {"command": "hackathon-playbook", "flags": "--draft", "repo_url": "", "cpu": 71},
    {"command": "art3m1s", "flags": "--introspect", "repo_url": "", "cpu": 42},
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


def ensure_no_markers(content: str) -> str:
    if any(marker in content for marker in ALL_MARKERS):
        raise ValueError("Generated content unexpectedly contained README markers")
    return content


def sanitize_line(value: str, limit: int = 80) -> str:
    """Strip markdown/HTML-active characters from untrusted text and cap length."""
    text = re.sub(r"[\[\]|<>`]", "", value or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit].rstrip()


def sanitize_summary(content: str) -> str:
    content = re.sub(r"```(?:markdown)?|```", "", content).strip()
    ensure_no_markers(content)

    lines = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        if stripped.lower().strip(":") in {"currently building", "currently building:"}:
            continue
        lines.append(stripped)

    if not lines:
        raise ValueError("Generated content was empty after sanitization")

    return "\n".join(lines)


def stable_pid(command: str) -> int:
    digest = hashlib.sha256(command.encode("utf-8")).hexdigest()
    return int(digest, 16) % 9000 + 1000


def fake_cpu_time(pid: int) -> str:
    return f"{pid % 120 + 3}:{pid % 60:02d}"


def render_ps_table(processes: list[dict]) -> str:
    rows = []
    seen: set[str] = set()
    for proc in sorted(processes, key=lambda p: -float(p.get("cpu", 0))):
        command = sanitize_line(str(proc.get("command", "")), 40)
        flags = sanitize_line(str(proc.get("flags", "")), 40)
        if not command or command in seen:
            continue
        seen.add(command)

        pid = stable_pid(command)
        cpu = min(max(float(proc.get("cpu", 50)), 1.0), 99.9)
        invocation = f"{command} {flags}".strip()
        repo_url = str(proc.get("repo_url", "")).strip()
        if GITHUB_REPO_URL.match(repo_url):
            cell = f"[`{invocation}`]({repo_url})"
        else:
            cell = f"`{invocation}`"
        rows.append(f"| {pid} | {cpu:.1f} | {fake_cpu_time(pid)} | {cell} |")

    if not rows:
        raise ValueError("No renderable processes")

    lines = [
        "| PID | %CPU | TIME | COMMAND |",
        "| --: | --: | --: | :-- |",
        *rows[:5],
    ]
    return ensure_no_markers("\n".join(lines))


def compute_uptime(now: datetime) -> str:
    months = (now.year - ACCOUNT_CREATED.year) * 12 + (now.month - ACCOUNT_CREATED.month)
    if now.day < ACCOUNT_CREATED.day:
        months -= 1
    years, months = divmod(max(months, 0), 12)
    since = ACCOUNT_CREATED.strftime("%Y-%m-%d")
    return f"uptime: {years} years, {months} months (since {since})"


def moon_phase(now: datetime) -> str:
    age_days = ((now - NEW_MOON_EPOCH).total_seconds() / 86400.0) % SYNODIC_DAYS
    fraction = age_days / SYNODIC_DAYS
    illumination = (1 - math.cos(2 * math.pi * fraction)) / 2 * 100
    # Name follows the illumination so the two never contradict each other
    # (a "first quarter" at 67% would get us letters from astronomers).
    waxing = fraction < 0.5
    if illumination < 2:
        name = "new moon"
    elif illumination > 98:
        name = "full moon"
    elif 46 <= illumination <= 54:
        name = "first quarter" if waxing else "last quarter"
    elif illumination < 46:
        name = "waxing crescent" if waxing else "waning crescent"
    else:
        name = "waxing gibbous" if waxing else "waning gibbous"
    return f"artemis.target: {name} ({illumination:.0f}% illuminated)"


def render_motd(quip: str, now: datetime) -> str:
    lines = [
        "```text",
        "$ cat /etc/motd",
        sanitize_line(quip, 80) or FALLBACK_MOTD,
        compute_uptime(now),
        moon_phase(now),
        f"motd.d regenerated: {now.strftime('%Y-%m-%d')}",
        "```",
    ]
    return ensure_no_markers("\n".join(lines))


def render_build_plate() -> str:
    sha = os.environ.get("GITHUB_SHA", "")
    sha = sha[:7] if re.fullmatch(r"[0-9a-f]{7,40}", sha) else ""
    run = os.environ.get("GITHUB_RUN_NUMBER", "")
    run = run if re.fullmatch(r"\d{1,9}", run or "") else "0"
    line = (
        f"<sub>compiled from `{sha or 'local'}` · build {run} · "
        "this page rebuilds itself; the human is a contributor</sub>"
    )
    return ensure_no_markers(line)


def fallback_payload(activity: list[str]) -> dict:
    processes: list[dict] = []
    seen: set[str] = set()
    for summary in activity:
        if summary.startswith("Starred "):
            continue  # starring a repo is not building it
        match = REPO_IN_SUMMARY.search(summary)
        if not match:
            continue
        full_name = match.group(1)
        if "/" not in full_name or full_name == "unknown/repo":
            continue
        command = full_name.split("/", 1)[1].lower()
        if not command or command in seen:
            continue
        seen.add(command)
        pid = stable_pid(command)
        processes.append(
            {
                "command": command,
                "flags": FALLBACK_FLAGS[pid % len(FALLBACK_FLAGS)],
                "repo_url": f"https://github.com/{full_name}",
                "cpu": pid % 55 + 40,
            }
        )
        if len(processes) == 5:
            break

    if len(processes) < 3:
        for seed in SEED_PROCESSES:
            if seed["command"] not in seen:
                processes.append(dict(seed))
                seen.add(seed["command"])
            if len(processes) >= 3:
                break

    return {"processes": processes, "motd": FALLBACK_MOTD, "obsession": FALLBACK_OBSESSION}


def parse_llm_payload(raw: str) -> dict:
    ensure_no_markers(raw)
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError("LLM payload is not a JSON object")

    processes = data.get("processes")
    if not isinstance(processes, list) or not 3 <= len(processes) <= 5:
        raise ValueError("LLM payload needs 3-5 processes")

    validated = []
    for proc in processes:
        if not isinstance(proc, dict):
            raise ValueError("process entry is not an object")
        command = proc.get("command")
        flags = proc.get("flags", "")
        repo_url = proc.get("repo_url", "")
        cpu = proc.get("cpu")
        if not isinstance(command, str) or not command.strip():
            raise ValueError("process command missing")
        if not isinstance(flags, str) or not isinstance(repo_url, str):
            raise ValueError("process flags/repo_url must be strings")
        if not isinstance(cpu, (int, float)) or isinstance(cpu, bool):
            raise ValueError("process cpu must be a number")
        validated.append({"command": command, "flags": flags, "repo_url": repo_url, "cpu": cpu})

    motd = data.get("motd")
    obsession = data.get("obsession")
    if not isinstance(motd, str) or not motd.strip():
        raise ValueError("LLM payload motd missing")
    if not isinstance(obsession, str) or not obsession.strip():
        raise ValueError("LLM payload obsession missing")

    obsession = " ".join(sanitize_line(obsession, 48).split()[:4])
    return {"processes": validated, "motd": motd, "obsession": obsession}


def call_openai(activity: list[str], posts: list[str], api_key: str) -> str:
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    prompt = f"""
You maintain the process table of a fictional machine that renders Bill Zhang's
GitHub profile. Return STRICT JSON only — no prose, no code fences.

Schema:
{{"processes": [{{"command": "voice-agent", "flags": "--elevenlabs --demo", "repo_url": "https://github.com/owner/repo or empty string", "cpu": 97}}], "motd": "one dry line", "obsession": "2-4 words"}}

Rules:
- 3 to 5 processes, each grounded in the context below. Do not invent projects.
- command: short lowercase daemon-style name derived from a real repo/project.
- flags: 0-3 plausible CLI flags reflecting what the work actually is.
- repo_url: a full https://github.com/owner/repo URL taken from the context, else "".
- cpu: integer 1-99; higher means more current obsession.
- motd: one deadpan sysadmin line about the current work, max 80 characters.
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


def safe_replace_block(readme_path: str, start: str, end: str, content: str, label: str) -> None:
    try:
        changed = replace_block(readme_path, start, end, content)
    except (ValueError, OSError) as error:
        print(f"WARNING: skipped {label} block: {error}")
        return
    print(f"Updated {label} block" if changed else f"{label} block already current")


def write_status_json(obsession: str, now: datetime, path: str = STATUS_PATH) -> None:
    status = {"obsession": obsession, "updated": now.strftime("%Y-%m-%dT%H:%M:%SZ")}
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {path}: {status}")


def write_github_output(obsession: str) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    run = os.environ.get("GITHUB_RUN_NUMBER", "")
    run = run if re.fullmatch(r"\d{1,9}", run or "") else "0"
    message = sanitize_line(
        f"artemis-build {run}: rewrote own bio around {obsession}, kept the good parts", 100
    )
    try:
        with open(output_path, "a", encoding="utf-8") as handle:
            handle.write(f"msg={message}\n")
    except OSError as error:
        print(f"WARNING: could not write GITHUB_OUTPUT: {error}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--readme", default="README.md")
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
            payload = parse_llm_payload(call_openai(activity, posts, openai_key))
        except Exception as error:
            print(f"WARNING: OpenAI generation rejected ({error}); using fallback")
    elif require_openai:
        raise RuntimeError("OPENAI_API_KEY is required when REQUIRE_OPENAI=1")

    if payload is None:
        payload = fallback_payload(activity)

    ps_block = render_ps_table(payload["processes"])
    motd_block = render_motd(payload["motd"], now)
    plate_block = render_build_plate()

    for label, block in (
        ("CURRENTLY_BUILDING", ps_block),
        ("MOTD", motd_block),
        ("BUILD_PLATE", plate_block),
    ):
        print(f"--- {label} ---")
        print(textwrap.indent(block, "  "))

    safe_replace_block(args.readme, START, END, ps_block, "CURRENTLY_BUILDING")
    safe_replace_block(args.readme, MOTD_START, MOTD_END, motd_block, "MOTD")
    safe_replace_block(args.readme, PLATE_START, PLATE_END, plate_block, "BUILD_PLATE")
    write_status_json(payload["obsession"], now)
    write_github_output(payload["obsession"])


if __name__ == "__main__":
    main()
