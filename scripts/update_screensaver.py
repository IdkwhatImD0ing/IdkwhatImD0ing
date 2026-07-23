from datetime import date, timezone, datetime

from readme_blocks import replace_block


START = "<!-- SCREENSAVER:START -->"
END = "<!-- SCREENSAVER:END -->"
RAW_BASE = "https://raw.githubusercontent.com/IdkwhatImD0ing/IdkwhatImD0ing/output"

QUIPS = {
    "snake": "screensaver of the week: snake — a classic. the predator rotates. come back next week.",
    "pacman": "screensaver of the week: pacman — the ghosts are also eating my commits. rotates weekly.",
}


def pick_predator(week: int) -> str:
    return "snake" if week % 2 == 0 else "pacman"


def render(predator: str) -> str:
    return (
        f'<div align="center">\n'
        f'  <img src="{RAW_BASE}/{predator}.svg" alt="contribution graph screensaver ({predator})" width="820">\n'
        f"</div>\n\n"
        f"`{QUIPS[predator]}`"
    )


def main() -> None:
    week = date.today().isocalendar()[1]
    predator = pick_predator(week)
    changed = replace_block("README.md", START, END, render(predator))
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"[{stamp}] screensaver -> {predator} (ISO week {week}, {'updated' if changed else 'already current'})")


if __name__ == "__main__":
    main()
