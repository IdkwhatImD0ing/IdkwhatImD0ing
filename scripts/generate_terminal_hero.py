import argparse
from datetime import datetime
from itertools import zip_longest
import json
from pathlib import Path
import os
import random
import shutil
import tempfile
import urllib.request
from zoneinfo import ZoneInfo


OUTPUT = Path("assets/terminal-hero.gif")
TIMEZONE = ZoneInfo("America/Los_Angeles")
USERNAME = "IdkwhatImD0ing"
GRAPHQL_URL = "https://api.github.com/graphql"

BOOT_PROGRAMS = ("standard", "memtest+", "scramble")
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

CYAN = "\x1b[96m"
BLUE = "\x1b[94m"
GREEN = "\x1b[92m"
YELLOW = "\x1b[93m"
RED = "\x1b[91m"
WHITE_BG = "\x1b[30;47m"
RESET = "\x1b[0m"


def request_json(url: str, token: str | None = None) -> dict | list:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "github-readme-terminal-hero",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_contributions(token: str | None) -> int | None:
    """Total commit contributions (public + private) over the last year, or None."""
    if not token:
        return None

    query = (
        "query($login: String!) { user(login: $login) { contributionsCollection {"
        " totalCommitContributions restrictedContributionsCount } } }"
    )
    payload = json.dumps({"query": query, "variables": {"login": USERNAME}}).encode("utf-8")
    request = urllib.request.Request(
        GRAPHQL_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "github-readme-terminal-hero",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
        collection = data["data"]["user"]["contributionsCollection"]
        return int(collection["totalCommitContributions"]) + int(collection["restrictedContributionsCount"])
    except Exception as error:
        print(f"WARNING: contribution count unavailable: {error}")
        return None


def fetch_github_stats() -> dict[str, str]:
    token = os.environ.get("GITHUB_TOKEN")
    contributions = fetch_contributions(token)
    contributions_str = str(contributions) if contributions is not None else ""

    fallback = {
        "public_repos": "many",
        "followers": "builders",
        "stars": "shipping",
        "top_languages": "TypeScript, Python, JavaScript",
        "recent_activity": "active",
        "contributions": contributions_str,
    }

    try:
        user = request_json(f"https://api.github.com/users/{USERNAME}", token)
        repos: list[dict] = []
        for page in range(1, 4):
            batch = request_json(
                f"https://api.github.com/users/{USERNAME}/repos?per_page=100&page={page}&sort=updated",
                token,
            )
            if not batch:
                break
            repos.extend(batch)

        stars = sum(repo.get("stargazers_count", 0) for repo in repos)
        language_counts: dict[str, int] = {}
        for repo in repos:
            language = repo.get("language")
            if language:
                language_counts[language] = language_counts.get(language, 0) + 1

        top_languages = ", ".join(
            language
            for language, _ in sorted(language_counts.items(), key=lambda item: item[1], reverse=True)[:4]
        )

        events = request_json(f"https://api.github.com/users/{USERNAME}/events/public?per_page=30", token)
        recent_repos = {
            event.get("repo", {}).get("name", "").split("/")[-1]
            for event in events
            if event.get("repo", {}).get("name")
        }

        return {
            "public_repos": str(user.get("public_repos", len(repos))),
            "followers": str(user.get("followers", 0)),
            "stars": str(stars),
            "top_languages": top_languages or fallback["top_languages"],
            "recent_activity": f"{len(recent_repos)} repos in recent public activity",
            "contributions": contributions_str,
        }
    except Exception as error:
        print(f"WARNING: GitHub stats unavailable: {error}")
        return fallback


def derive_seed() -> tuple[int, str]:
    """Seed from GITHUB_SHA when present, else stable per ISO year+week."""
    sha = os.environ.get("GITHUB_SHA", "")
    if len(sha) >= 8:
        try:
            return int(sha[:8], 16), "GITHUB_SHA"
        except ValueError:
            pass
    year, week, _ = datetime.now(TIMEZONE).isocalendar()
    return year * 100 + week, "iso-week"


def build_stamp() -> str:
    sha = os.environ.get("GITHUB_SHA", "")
    return sha[:7] if sha else "local"


def pick_boot_program(rng: random.Random) -> str:
    if rng.randrange(PANIC_ODDS) == 0:
        return "kernel_panic"
    return rng.choice(BOOT_PROGRAMS)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the terminal hero boot GIF.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print seed, boot program, and stats without importing gifos or rendering",
    )
    args = parser.parse_args()

    seed, seed_source = derive_seed()
    rng = random.Random(seed)
    program = pick_boot_program(rng)
    stamp = build_stamp()
    github_stats = fetch_github_stats()

    if args.dry_run:
        print(f"seed={seed} (source={seed_source})")
        print(f"boot_program={program}")
        print(f"build_stamp={stamp}")
        print(f"stats={json.dumps(github_stats, indent=2)}")
        return

    import gifos

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    old_cwd = Path.cwd()
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            os.chdir(tmpdir)
            Path("frames").mkdir(exist_ok=True)
            terminal = gifos.Terminal(width=900, height=700, xpad=16, ypad=16, line_spacing=5)
            terminal.set_fps(14)
            terminal.set_prompt("bill@whitebox:~$ ")
            terminal.set_bg_color("#0d1117")

            year = datetime.now(TIMEZONE).strftime("%Y")
            timestamp = datetime.now(TIMEZONE).strftime("%a %b %d %I:%M:%S %p %Z %Y")

            terminal.toggle_show_cursor(False)
            terminal.gen_text("ART3M1S Modular BIOS v2.8.04", 1)
            terminal.gen_text(f"Copyright (C) {year}, {RED}Bill Zhang Labs{RESET} build {stamp}", 2)
            terminal.gen_text(f"{BLUE}GitHub Profile ReadMe Terminal, Whitebox Rev 5080{RESET}", 4)
            terminal.gen_text("Krypton(tm) GIFCPU - 250Hz", 6)
            terminal.gen_text("Board: ROG Strix B550 White", 8)
            terminal.gen_text("CPU:   AMD Ryzen 7 9800X3D", 9)
            terminal.gen_text("GPU:   ASUS ROG Astral GeForce RTX 5080 White", 10)
            terminal.gen_text(
                f"Press {BLUE}DEL{RESET} to enter SETUP, {BLUE}ESC{RESET} to skip memory test",
                terminal.num_rows,
            )

            contributions = github_stats.get("contributions", "")
            if contributions.isdigit() and int(contributions) > 0:
                total = int(contributions)
                step = max(total // 12, 1)
                for value in range(0, total, step):
                    terminal.delete_row(12)
                    terminal.gen_text(f"Memory Test: {value:>6} contributions", 12, count=1, contin=True)
                terminal.delete_row(12)
                terminal.gen_text(f"Memory Test: {total} contributions OK", 12, count=8, contin=True)
            else:
                for memory in range(0, 98305, 8192):
                    terminal.delete_row(12)
                    terminal.gen_text(
                        f"Memory Test: {memory:>6} MB", 12, count=2 if memory < 32768 else 1, contin=True
                    )
                terminal.delete_row(12)
                terminal.gen_text("Memory Test:  98304 MB OK", 12, count=8, contin=True)

            if program == "memtest+":
                terminal.gen_text(
                    "/dev/hackathons: 58 volumes scanned, 35 flagged TROPHY", 13, count=6
                )

            terminal.gen_text("NVMe: Samsung 990-class boot volume detected", 14, count=4)
            terminal.gen_text("USB:  Voice clone interface online", 15, count=4)
            terminal.gen_text("Boot device: GitHub profile README", 17, count=4)

            if program == "kernel_panic":
                terminal.gen_text("System ready. Launching ART3M1S OS...", 19, count=6)
                terminal.clear_frame()
                terminal.gen_text(f"{RED}{PANIC_TRACE[0]}{RESET}", 1, count=4)
                for offset, line in enumerate(PANIC_TRACE[1:], start=2):
                    terminal.gen_text(f"{RED}{line}{RESET}", offset, count=2)
                terminal.gen_text(f"{YELLOW}rebooting...{RESET}", len(PANIC_TRACE) + 2, count=14)
            else:
                terminal.gen_text("System ready. Launching ART3M1S OS...", 19, count=28)

            terminal.clear_frame()
            terminal.toggle_show_cursor(True)
            terminal.gen_text("Initiating Boot Sequence ", 1, contin=True)
            terminal.gen_typing_text(".....", 1, contin=True)
            terminal.toggle_show_cursor(False)
            terminal.gen_text(f"{CYAN}Loading ART3M1S OS kernel modules{RESET}", 3, count=5)

            os_logo = "ART3M1S OS"
            mid_row = (terminal.num_rows + 1) // 2
            mid_col = max((terminal.num_cols - len(os_logo)) // 2, 1)
            if program == "scramble":
                logo_lines = list(
                    gifos.effects.text_scramble_effect_lines(os_logo, 5, include_special=True)
                )
                sub_logo = "WHITEBOX REV 5080"
                sub_lines = list(
                    gifos.effects.text_scramble_effect_lines(sub_logo, 3, include_special=True)
                )
                sub_col = max((terminal.num_cols - len(sub_logo)) // 2, 1)
                for logo_line, sub_line in zip_longest(logo_lines, sub_lines):
                    terminal.delete_row(mid_row)
                    terminal.delete_row(mid_row + 2)
                    terminal.gen_text(
                        f"{YELLOW}{logo_line if logo_line is not None else logo_lines[-1]}{RESET}",
                        mid_row,
                        mid_col,
                    )
                    terminal.gen_text(
                        f"{GREEN}{sub_line if sub_line is not None else sub_lines[-1]}{RESET}",
                        mid_row + 2,
                        sub_col,
                    )
            else:
                for line in gifos.effects.text_scramble_effect_lines(os_logo, 4, include_special=False):
                    terminal.delete_row(mid_row)
                    terminal.gen_text(f"{YELLOW}{line}{RESET}", mid_row, mid_col)
            terminal.clone_frame(10)

            terminal.clear_frame()
            terminal.clone_frame(5)
            terminal.toggle_show_cursor(False)
            terminal.gen_text(f"{YELLOW}ART3M1S OS 5.8 LTS (tty1){RESET}", 1, count=5)
            terminal.gen_text("login: ", 3, count=3)
            terminal.toggle_show_cursor(True)
            terminal.gen_typing_text("bill", 3, contin=True)
            terminal.toggle_show_cursor(False)
            terminal.gen_text("password: ", 4, count=3)
            terminal.toggle_show_cursor(True)
            terminal.gen_typing_text("************", 4, contin=True)
            terminal.toggle_show_cursor(False)
            terminal.gen_text(f"Last login: {timestamp} on tty1", 6, count=5)

            terminal.gen_prompt(8, count=4)
            prompt_col = terminal.curr_col
            terminal.toggle_show_cursor(True)
            terminal.gen_typing_text(f"{RED}clea", 8, contin=True)
            terminal.delete_row(8, prompt_col)
            terminal.gen_text(f"{GREEN}clear{RESET}", 8, count=3, contin=True)

            terminal.clear_frame()
            terminal.gen_prompt(1)
            prompt_col = terminal.curr_col
            terminal.clone_frame(8)
            terminal.toggle_show_cursor(True)
            terminal.gen_typing_text(f"{RED}fetch-prof", 1, contin=True)
            terminal.delete_row(1, prompt_col)
            terminal.gen_text(f"{GREEN}fetch-profile{RESET}", 1, contin=True)
            terminal.gen_typing_text(" --rig whitebox --voice-clone", 1, contin=True)
            terminal.toggle_show_cursor(False)

            rig_art = rf"""
{WHITE_BG}        {RESET}
{WHITE_BG}  /\    {RESET}
{WHITE_BG} /  \   {RESET}
{WHITE_BG}| [] |  {RESET}
{WHITE_BG}|    |  {RESET}
{WHITE_BG}| RTX|  {RESET}
{WHITE_BG}|____|  {RESET}
{WHITE_BG}  ||    {RESET}
"""
            profile_lines = f"""
{WHITE_BG} Bill Zhang @ GitHub {RESET}
---------------------
{CYAN}Role:       {YELLOW}AI builder, hackathon operator, full-stack shipper{RESET}
{CYAN}Voice:      {YELLOW}art3m1s.me{RESET}
{CYAN}Focus:      {YELLOW}voice AI demos, agentic workflows, useful products{RESET}

{WHITE_BG} Hackathon Stats {RESET}
---------------------
{CYAN}Won:        {YELLOW}35 hackathons{RESET}
{CYAN}Attended:   {YELLOW}58 hackathons{RESET}
{CYAN}Win Rate:   {YELLOW}60%{RESET}
{CYAN}Devpost:    {YELLOW}devpost.com/IdkwhatImD0ing{RESET}

{WHITE_BG} GitHub Stats {RESET}
---------------------
{CYAN}Repos:      {YELLOW}{github_stats["public_repos"]}{RESET}
{CYAN}Stars:      {YELLOW}{github_stats["stars"]}{RESET}
{CYAN}Followers:  {YELLOW}{github_stats["followers"]}{RESET}
{CYAN}Languages:  {YELLOW}{github_stats["top_languages"]}{RESET}
{CYAN}Activity:   {YELLOW}{github_stats["recent_activity"]}{RESET}

{WHITE_BG} Whitebox Rig {RESET}
---------------------
{CYAN}Board:      {YELLOW}ROG Strix B550 White{RESET}
{CYAN}CPU:        {YELLOW}AMD Ryzen 7 9800X3D{RESET}
{CYAN}Memory:     {YELLOW}Corsair Dominator 96GB White{RESET}
{CYAN}GPU:        {YELLOW}RTX 5080 Astral White{RESET}
"""
            terminal.gen_text(rig_art, 3, 2)
            terminal.gen_text(profile_lines, 3, 20, count=5, contin=True)
            terminal.gen_prompt(terminal.curr_row)
            terminal.toggle_show_cursor(True)
            terminal.gen_typing_text(
                f"{GREEN}# shipping fast, demoing loud, and building with AI{RESET}",
                terminal.curr_row,
                contin=True,
            )
            terminal.gen_text("", terminal.curr_row, count=70, contin=True)

            terminal.gen_gif()
            shutil.copyfile("output.gif", old_cwd / OUTPUT)
        finally:
            os.chdir(old_cwd)

    print(f"Wrote {OUTPUT} (program={program}, seed={seed}, build={stamp})")


if __name__ == "__main__":
    main()
