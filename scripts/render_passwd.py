"""Render the PASSWD block: the newest stargazers as /etc/passwd lines.

The block lives inside an HTML <pre> in README.md, right after the prompt:

    <pre><b>bill@tianni:~$ tail -n 4 /etc/passwd</b><!-- PASSWD:START -->
    ...rendered here...
    <!-- PASSWD:END --></pre>

Each stargazer is an account: uid 1000 + their position in the star list, the
star date in the GECOS field, the login linked to their profile. The file
starts with a few fixed system accounts, so `tail -n 4` still shows four lines
while there are fewer than four stargazers. Then a typed comment names the
next free uid.

The stargazers endpoint needs a token (it 401s anonymously), so run it as
GITHUB_TOKEN=... python scripts/render_passwd.py  (CI always has one).
No token, offline, or a bad API day: warn and leave the block untouched.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import urllib.request

from readme_blocks import replace_block
import phosphor as ph

START = "<!-- PASSWD:START -->"
END = "<!-- PASSWD:END -->"
REPO = "IdkwhatImD0ing/IdkwhatImD0ing"
PER_PAGE = 100
TAIL_COUNT = 4
FIRST_UID = 1000
MAX_WIDTH = 72  # visible columns per line (links do not count, their text does)
PROMPT = ph.PROMPT
SAFE_LOGIN = re.compile(r"[^A-Za-z0-9-]")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
UNKNOWN_DATE = "????-??-??"  # an entry without a usable starred_at

# The head of the fictional /etc/passwd, in file order. Stargazer accounts are
# appended after these, so they only show while there are < 4 stargazers.
SYSTEM_ACCOUNTS = (
    "nobody:x:65534:65534:nobody:/nonexistent:/usr/sbin/nologin",
    "sleep:x:997:997:optional dependency:/nonexistent:/usr/sbin/nologin",
    "artemis:x:998:998:ART3M1S daemon:/var/lib/artemis:/usr/sbin/nologin",
    "bill:x:999:100:Bill Zhang,,,:/home/bill:/usr/bin/zsh",
)


def request_json(url: str, token: str) -> object:
    headers = {
        "Accept": "application/vnd.github.star+json",  # adds starred_at to stargazers
        "Authorization": f"Bearer {token}",
        "User-Agent": "github-profile-readme-updater",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_total(repo: str, token: str) -> int:
    data = request_json(f"https://api.github.com/repos/{repo}", token)
    total = data.get("stargazers_count") if isinstance(data, dict) else None
    if not isinstance(total, int) or total < 0:
        raise ValueError("Unexpected repo response shape")
    return total


def fetch_recent_stargazers(repo: str, token: str, total: int) -> list[tuple[int, dict]]:
    """The stargazers API pages oldest-first, so fetch the LAST page(s) to get
    the newest accounts. Returns (global_index, entry) pairs, oldest to newest."""
    if total == 0:
        return []
    last_page = max((total + PER_PAGE - 1) // PER_PAGE, 1)
    pages = [last_page] if last_page == 1 else [last_page - 1, last_page]
    collected: list[tuple[int, dict]] = []
    for page in pages:
        url = f"https://api.github.com/repos/{repo}/stargazers?per_page={PER_PAGE}&page={page}"
        batch = request_json(url, token)
        if not isinstance(batch, list):
            raise ValueError("Unexpected stargazers response shape")
        for offset, entry in enumerate(batch):
            if isinstance(entry, dict):
                collected.append(((page - 1) * PER_PAGE + offset, entry))
    return collected


def clean_login(entry: dict) -> str:
    user = entry.get("user")
    login = user.get("login", "") if isinstance(user, dict) else ""
    return SAFE_LOGIN.sub("", str(login))[:39]


def star_date(entry: dict) -> str:
    raw = str(entry.get("starred_at") or "")[:10]
    return raw if DATE.fullmatch(raw) else UNKNOWN_DATE


def passwd_fields(login: str, uid: int, date: str) -> tuple[str, str]:
    """(login, rest-of-line). Long logins shed detail until the line fits.
    The star date is the point of the line, so boilerplate goes first:
    shorter shell, bare date, numbered home directory, and only then the date."""
    candidates = (
        f":x:{uid}:100:starred {date}:/home/{login}:/usr/bin/zsh",
        f":x:{uid}:100:starred {date}:/home/{login}:/bin/zsh",
        f":x:{uid}:100:{date}:/home/{login}:/bin/zsh",
        f":x:{uid}:100:starred {date}:/home/u{uid}:/bin/zsh",
        f":x:{uid}:100:{date}:/home/u{uid}:/bin/zsh",
        f":x:{uid}:100::/home/u{uid}:/bin/sh",
    )
    for rest in candidates:
        if len(login) + len(rest) <= MAX_WIDTH:
            return login, rest
    return login, candidates[-1][: max(MAX_WIDTH - len(login), 0)]


def stargazer_line(entry: dict, uid: int) -> str | None:
    login = clean_login(entry)
    if not login:
        return None
    login, rest = passwd_fields(login, uid, star_date(entry))
    return f'<a href="https://github.com/{login}">{login}</a>{html.escape(rest, quote=False)}'


def render(stargazers: list[tuple[int, dict]], total: int, repo: str = REPO) -> str:
    if total > 0 and not stargazers:
        raise ValueError("API reported stars but returned no stargazers")
    rows = [html.escape(line, quote=False) for line in SYSTEM_ACCOUNTS]
    for index, entry in stargazers[-TAIL_COUNT:]:
        line = stargazer_line(entry, FIRST_UID + index)
        if line:
            rows.append(line)
    if total > 0 and len(rows) == len(SYSTEM_ACCOUNTS):
        raise ValueError("no renderable stargazers")

    uid = FIRST_UID + total
    closing = (
        f"<b>{html.escape(PROMPT)}# uid {uid} is unclaimed. "
        f'<a href="https://github.com/{html.escape(repo)}">star this repo</a> to claim it.</b>'
    )
    lines = rows[-TAIL_COUNT:] + [closing]

    content = "\n".join(lines)
    for line in lines:
        width = len(html.unescape(re.sub(r"<[^>]+>", "", line)))
        if width > MAX_WIDTH:
            raise ValueError(f"line exceeds {MAX_WIDTH} columns: {line!r}")
    if START in content or END in content or "<!--" in content:
        raise ValueError("rendered content unexpectedly contained a comment marker")
    return content


def main() -> None:
    parser = argparse.ArgumentParser(description="Render the PASSWD block of README.md.")
    parser.add_argument("--readme", default="README.md")
    parser.add_argument("--repo", default=REPO)
    parser.add_argument("--dry-run", action="store_true", help="print the block, write nothing")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:  # the stargazers endpoint 401s without auth, for every media type
        print("WARNING: passwd not rendered: GITHUB_TOKEN is not set (the stargazers API needs auth)")
        return
    try:
        total = fetch_total(args.repo, token)
        content = render(fetch_recent_stargazers(args.repo, token, total), total, args.repo)
    except Exception as error:  # Offline or bad API day: leave the block untouched.
        print(f"WARNING: passwd not rendered: {error}")
        return

    print("--- PASSWD ---")
    print(content)
    if args.dry_run:
        return

    try:
        changed = replace_block(args.readme, START, END, content)
    except (ValueError, OSError) as error:
        print(f"WARNING: skipped PASSWD block: {error}")
        return
    print("Updated passwd block" if changed else "Passwd block already current")


if __name__ == "__main__":
    main()
