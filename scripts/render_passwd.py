"""Render the PASSWD block: the disciple register, newest four entries.

The block lives inside an HTML <pre> in README.md, right after its heading:

    <pre><b>弟子名册 the disciple register · newest four</b><!-- PASSWD:START -->
    ...rendered here...
    <!-- PASSWD:END --></pre>

Starring the repo initiates you as a 外门弟子, an outer disciple. Each
stargazer gets a register number (1000 + their position in the star list),
their login linked to their profile, and the day they were initiated (the
star date). The register opens with a few fixed entries, so the newest four
are always four lines even while there are fewer than four stargazers. A last
line names the next free number.

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
import sys
import urllib.request

from readme_blocks import display_cols, replace_block

START = "<!-- PASSWD:START -->"
END = "<!-- PASSWD:END -->"
REPO = "IdkwhatImD0ing/IdkwhatImD0ing"
PER_PAGE = 100
TAIL_COUNT = 4
FIRST_NUMBER = 1000
MAX_WIDTH = 72  # display columns per line (links do not count, their text does)
NUMBER_WIDTH = 4
LOGIN_WIDTH = 9
SAFE_LOGIN = re.compile(r"[^A-Za-z0-9-]")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
UNKNOWN_DATE = "????-??-??"  # an entry without a usable starred_at

# The head of the register, in file order. Disciples are entered after these,
# so the fixed entries only show while there are fewer than four stargazers.
SYSTEM_ENTRIES = (
    (65534, "nobody", "the wind. owns nothing"),
    (997, "sleep", "never initiated. optional dependency"),
    (998, "steward", "keeps the mission hall. not a person"),
    (999, "bill", "教主, Sect Leader. here since 2021-09-21"),
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
    the newest disciples. Returns (global_index, entry) pairs, oldest to newest."""
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


def head(number: int, login: str) -> tuple[str, str]:
    """('no. 1000  ', 'login    ') : the number and the padded login column."""
    return f"no. {number:>{NUMBER_WIDTH}}  ", login.ljust(LOGIN_WIDTH) + "  "


def fit_description(prefix_cols: int, candidates: tuple[str, ...]) -> str:
    """The first description that keeps the line inside MAX_WIDTH. Long logins
    shed words: the initiation date is the point of the line, so the rank goes
    first and the date last."""
    for text in candidates:
        if prefix_cols + display_cols(text) <= MAX_WIDTH:
            return text
    return ""


def disciple_line(entry: dict, number: int) -> str | None:
    login = clean_login(entry)
    if not login:
        return None
    date = star_date(entry)
    number_part, padded = head(number, login)
    gap = padded[len(login):]
    description = fit_description(
        display_cols(number_part) + len(login) + len(gap),
        (f"外门 outer disciple. initiated {date}", f"outer disciple. initiated {date}",
         f"initiated {date}", date),
    )
    line = f'{html.escape(number_part, quote=False)}<a href="https://github.com/{login}">{login}</a>'
    if description:
        line += html.escape(gap + description, quote=False)
    return line


def system_line(number: int, login: str, description: str) -> str:
    number_part, login_part = head(number, login)
    return html.escape(number_part + login_part + description, quote=False)


def render(stargazers: list[tuple[int, dict]], total: int, repo: str = REPO) -> str:
    if total > 0 and not stargazers:
        raise ValueError("API reported stars but returned no stargazers")
    rows = [system_line(*entry) for entry in SYSTEM_ENTRIES]
    for index, entry in stargazers[-TAIL_COUNT:]:
        line = disciple_line(entry, FIRST_NUMBER + index)
        if line:
            rows.append(line)
    if total > 0 and len(rows) == len(SYSTEM_ENTRIES):
        raise ValueError("no renderable stargazers")

    closing = (
        f"the next number, {FIRST_NUMBER + total}, is unclaimed. "
        f'<a href="https://github.com/{html.escape(repo)}">star this repo</a> to be initiated.'
    )
    lines = rows[-TAIL_COUNT:] + [closing]

    content = "\n".join(lines)
    for line in lines:
        width = display_cols(html.unescape(re.sub(r"<[^>]+>", "", line)))
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
    if hasattr(sys.stdout, "reconfigure"):  # a cp1252 console must not crash on 外门
        sys.stdout.reconfigure(errors="replace")

    token = os.environ.get("GITHUB_TOKEN")
    if not token:  # the stargazers endpoint 401s without auth, for every media type
        print("WARNING: register not rendered: GITHUB_TOKEN is not set (the stargazers API needs auth)")
        return
    try:
        total = fetch_total(args.repo, token)
        content = render(fetch_recent_stargazers(args.repo, token, total), total, args.repo)
    except Exception as error:  # Offline or bad API day: leave the block untouched.
        print(f"WARNING: register not rendered: {error}")
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
    print("Updated register block" if changed else "Register block already current")


if __name__ == "__main__":
    main()
