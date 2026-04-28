from datetime import datetime
import json
from pathlib import Path
import os
import shutil
import tempfile
import urllib.request
from zoneinfo import ZoneInfo


OUTPUT = Path("assets/terminal-hero.gif")
TIMEZONE = ZoneInfo("America/Los_Angeles")
USERNAME = "IdkwhatImD0ing"

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


def fetch_github_stats() -> dict[str, str]:
    fallback = {
        "public_repos": "many",
        "followers": "builders",
        "stars": "shipping",
        "top_languages": "TypeScript, Python, JavaScript",
        "recent_activity": "active",
    }
    token = os.environ.get("GITHUB_TOKEN")

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
        }
    except Exception as error:
        print(f"WARNING: GitHub stats unavailable: {error}")
        return fallback


def main() -> None:
    import gifos

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    github_stats = fetch_github_stats()

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
            terminal.gen_text(f"Copyright (C) {year}, {RED}Bill Zhang Labs{RESET}", 2)
            terminal.gen_text(f"{BLUE}GitHub Profile ReadMe Terminal, Whitebox Rev 5080{RESET}", 4)
            terminal.gen_text("Krypton(tm) GIFCPU - 250Hz", 6)
            terminal.gen_text("Board: ROG Strix B550 White", 8)
            terminal.gen_text("CPU:   AMD Ryzen 7 9800X3D", 9)
            terminal.gen_text("GPU:   ASUS ROG Astral GeForce RTX 5080 White", 10)
            terminal.gen_text(
                f"Press {BLUE}DEL{RESET} to enter SETUP, {BLUE}ESC{RESET} to skip memory test",
                terminal.num_rows,
            )

            for memory in range(0, 98305, 8192):
                terminal.delete_row(12)
                terminal.gen_text(f"Memory Test: {memory:>6} MB", 12, count=2 if memory < 32768 else 1, contin=True)
            terminal.delete_row(12)
            terminal.gen_text("Memory Test:  98304 MB OK", 12, count=8, contin=True)
            terminal.gen_text("NVMe: Samsung 990-class boot volume detected", 14, count=4)
            terminal.gen_text("USB:  Voice clone interface online", 15, count=4)
            terminal.gen_text("Boot device: GitHub profile README", 17, count=4)
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
            for line in gifos.effects.text_scramble_effect_lines(os_logo, 4, include_special=False):
                terminal.delete_row(mid_row)
                terminal.gen_text(f"{YELLOW}{line}{RESET}", mid_row, mid_col)
            terminal.clone_frame(10)

            terminal.clear_frame()
            terminal.clone_frame(5)
            terminal.toggle_show_cursor(False)
            terminal.gen_text(f"{YELLOW}ART3M1S OS v2.8.04 (tty1){RESET}", 1, count=5)
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

    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
