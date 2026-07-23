import argparse
import re
from pathlib import Path

from readme_blocks import replace_block


START = "<!-- CRONTAB:START -->"
END = "<!-- CRONTAB:END -->"
WORKFLOWS_DIR = ".github/workflows"

# Only the comments are hardcoded; workflows may appear or disappear freely.
COMMENTS = {
    "metrics.yaml": "repaint own dashboards",
    "profile-summary.yaml": "an LLM rewrites this page",
    "terminal-hero.yaml": "reroll boot (1-in-8: panic)",
    "screensaver.yaml": "rotate the predator",
    "artemis-ops.yaml": "on visitor input",
    "snake.yaml": "release the snake",
}
DEFAULT_COMMENT = "undocumented daemon"
CLOSING_COMMENTS = (
    "# the LLM's drafts go unreviewed. quality has improved.",
    "# this machine stays alive by committing to itself. so can you.",
)
MAX_WIDTH = 72

CRON_PATTERN = re.compile(r"""cron:\s*["']?([0-9*,/\- ]+?)["']?\s*(?:#.*)?$""", re.MULTILINE)
SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]")


def parse_workflows(directory: Path) -> list[tuple[str, str]]:
    """Return (schedule, filename) pairs; event-driven workflows get @reboot."""
    entries: list[tuple[str, str]] = []
    for path in sorted(directory.glob("*.y*ml")):
        filename = SAFE_NAME.sub("", path.name)[:40]
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        crons = [cron.strip() for cron in CRON_PATTERN.findall(text) if cron.strip()]
        if crons:
            entries.extend((cron[:24], filename) for cron in crons)
        else:
            entries.append(("@reboot", filename))
    return entries


def render(entries: list[tuple[str, str]]) -> str:
    if not entries:
        raise ValueError("no workflow files found")

    sched_width = max(len("# m h dom mon dow"), *(len(sched) for sched, _ in entries))
    name_width = max(len("command"), *(len(name) for _, name in entries))

    lines = ["```text", f"{'# m h dom mon dow'.ljust(sched_width)}  {'command'.ljust(name_width)}  comment"]
    for sched, name in entries:
        comment = COMMENTS.get(name, DEFAULT_COMMENT)
        row = f"{sched.ljust(sched_width)}  {name.ljust(name_width)}  # {comment}"
        lines.append(row[:MAX_WIDTH])
    lines.extend(CLOSING_COMMENTS)
    lines.append("```")

    links = " · ".join(
        f"[{name}]({WORKFLOWS_DIR}/{name})" for name in dict.fromkeys(name for _, name in entries)
    )
    lines.append("")
    lines.append(f"<sub>daemon sources: {links}</sub>")

    content = "\n".join(lines)
    if START in content or END in content:
        raise ValueError("Rendered content unexpectedly contained README markers")
    return content


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--readme", default="README.md")
    parser.add_argument("--workflows", default=WORKFLOWS_DIR)
    args = parser.parse_args()

    try:
        content = render(parse_workflows(Path(args.workflows)))
    except (OSError, ValueError) as error:
        print(f"WARNING: crontab not rendered: {error}")
        return

    print("--- CRONTAB ---")
    print(content)

    try:
        changed = replace_block(args.readme, START, END, content)
    except (ValueError, OSError) as error:
        print(f"WARNING: skipped CRONTAB block: {error}")
        return
    print("Updated crontab block" if changed else "Crontab block already current")


if __name__ == "__main__":
    main()
