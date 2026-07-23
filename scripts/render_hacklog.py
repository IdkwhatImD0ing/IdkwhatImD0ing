import argparse
import re
from pathlib import Path

from readme_blocks import replace_block


START = "<!-- HACKLOG:START -->"
END = "<!-- HACKLOG:END -->"
DEFAULT_LOG_PATH = "var/log/hackathons.log"
TAIL_COUNT = 6
MAX_LINE = 72

# The log only holds entries since the fictional 2026-01 rotation; lifetime
# totals come from the human and are labeled as such. Never fake command output.
TOTALS_LINE = "# log rotated — lifetime: 35 wins / 58 entered (source: the human)"


def read_log(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def entry_lines(lines: list[str]) -> list[str]:
    return [line.rstrip() for line in lines if line.strip() and not line.lstrip().startswith("#")]


def count_wins(lines: list[str]) -> int:
    return sum(1 for line in lines if "[WIN]" in line)


def clamp(line: str) -> str:
    line = re.sub(r"\s+$", "", line)
    return line if len(line) <= MAX_LINE else line[: MAX_LINE - 3] + "..."


def render(lines: list[str]) -> str:
    entries = entry_lines(lines)
    tail = entries[-TAIL_COUNT:]
    if not tail:
        raise ValueError("hackathons.log has no entries")

    out = [
        "```text",
        f"$ grep -v '^#' /var/log/hackathons.log | tail -n {TAIL_COUNT}",
        *[clamp(line) for line in tail],
        "",
        "$ grep -c '\\[WIN\\]' hackathons.log*",
        str(count_wins(lines)),
        clamp(TOTALS_LINE),
        "```",
    ]
    content = "\n".join(out)
    if START in content or END in content:
        raise ValueError("Rendered content unexpectedly contained README markers")
    return content


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--readme", default="README.md")
    parser.add_argument("--log", default=DEFAULT_LOG_PATH)
    args = parser.parse_args()

    log_path = Path(args.log)
    try:
        lines = read_log(log_path)
        content = render(lines)
    except (OSError, ValueError) as error:
        print(f"WARNING: hacklog not rendered: {error}")
        return

    print("--- HACKLOG ---")
    print(content)

    try:
        changed = replace_block(args.readme, START, END, content)
    except (ValueError, OSError) as error:
        print(f"WARNING: skipped HACKLOG block: {error}")
        return
    print("Updated hacklog block" if changed else "Hacklog block already current")


if __name__ == "__main__":
    main()
