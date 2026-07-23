import argparse
import json
import os
import re
import urllib.error
import urllib.request

from readme_blocks import replace_block


START = "<!-- PASSWD:START -->"
END = "<!-- PASSWD:END -->"
REPO = "IdkwhatImD0ing/IdkwhatImD0ing"
PER_PAGE = 100
TAIL_COUNT = 8
SAFE_LOGIN = re.compile(r"[^A-Za-z0-9-]")


def request_json(url: str, token: str | None, accept: str = "application/vnd.github.star+json") -> object:
    headers = {
        "Accept": accept,
        "User-Agent": "github-profile-readme-updater",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_total(repo: str, token: str | None) -> int:
    data = request_json(f"https://api.github.com/repos/{repo}", token)
    total = data.get("stargazers_count") if isinstance(data, dict) else None
    if not isinstance(total, int):
        raise ValueError("Unexpected repo response shape")
    return total


def fetch_recent_stargazers(repo: str, token: str | None, total: int) -> list[tuple[int, dict]]:
    """The stargazers API pages oldest-first, so fetch the LAST page(s) to get
    the newest accounts. Returns (global_index, entry) pairs, oldest to newest."""
    last_page = max((total + PER_PAGE - 1) // PER_PAGE, 1)
    pages = [last_page] if last_page == 1 else [last_page - 1, last_page]
    collected: list[tuple[int, dict]] = []
    for page in pages:
        url = f"https://api.github.com/repos/{repo}/stargazers?per_page={PER_PAGE}&page={page}"
        try:
            batch = request_json(url, token)
        except urllib.error.HTTPError as error:
            if error.code != 401 or token:
                raise
            # The star+json media type (starred_at) requires auth; fall back to
            # the plain shape and live without star dates.
            batch = request_json(url, token, accept="application/vnd.github+json")
            if isinstance(batch, list):
                batch = [{"user": entry, "starred_at": ""} for entry in batch if isinstance(entry, dict)]
        if not isinstance(batch, list):
            raise ValueError("Unexpected stargazers response shape")
        for offset, entry in enumerate(batch):
            if isinstance(entry, dict):
                collected.append(((page - 1) * PER_PAGE + offset, entry))
    return collected


def passwd_line(entry: dict, uid: int) -> str | None:
    login = SAFE_LOGIN.sub("", str(entry.get("user", {}).get("login", "")))[:32]
    if not login:
        return None
    starred = str(entry.get("starred_at", ""))[:10] or "unknown"
    return f"{login}:x:{uid}:100:starred {starred}:/home/{login}:/usr/bin/zsh"


def render(stargazers: list[tuple[int, dict]], total: int) -> str:
    lines = [f"$ tail -n {TAIL_COUNT} /etc/passwd"]
    for index, entry in stargazers[-TAIL_COUNT:]:
        line = passwd_line(entry, 1000 + index)
        if line:
            lines.append(line)

    if len(lines) == 1:
        raise ValueError("no renderable stargazers")

    noun = "user" if total == 1 else "users"
    lines.append(f"# {total} {noun} registered — star this repo to create your account.")
    content = "\n".join(["```text", *lines, "```"])
    if START in content or END in content:
        raise ValueError("Rendered content unexpectedly contained README markers")
    return content


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--readme", default="README.md")
    parser.add_argument("--repo", default=REPO)
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    try:
        total = fetch_total(args.repo, token)
        content = render(fetch_recent_stargazers(args.repo, token, total), total)
    except Exception as error:  # Offline or bad API day: leave the block untouched.
        print(f"WARNING: passwd not rendered: {error}")
        return

    print("--- PASSWD ---")
    print(content)

    try:
        changed = replace_block(args.readme, START, END, content)
    except (ValueError, OSError) as error:
        print(f"WARNING: skipped PASSWD block: {error}")
        return
    print("Updated passwd block" if changed else "Passwd block already current")


if __name__ == "__main__":
    main()
