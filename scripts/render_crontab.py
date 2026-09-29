"""Render the CRONTAB block: `crontab -l`, then the machine's own git receipts.

The block lives inside an HTML <pre> in README.md, right after the first prompt:

    <pre><b>bill@tianni:~$ crontab -l</b><!-- CRONTAB:START -->
    ...rendered here...
    <!-- CRONTAB:END --></pre>

Every workflow in .github/workflows becomes one crontab line (event-driven ones
are @reboot), its file name linked to the source. Then the newest
`artemis-build` commits, straight from `git log`, each hash linked to the
commit. The typed pipeline is shown in full and its output is emulated exactly
(same git query, same two sed substitutions), so nothing on the screen is
invented. If git is unavailable the receipts are left out and the crontab
still renders.

Run from the repo root: python scripts/render_crontab.py [--readme PATH]
"""

from __future__ import annotations

import argparse
import html
import re
import subprocess
from pathlib import Path
from typing import NamedTuple

from readme_blocks import replace_block
import phosphor as ph

START = "<!-- CRONTAB:START -->"
END = "<!-- CRONTAB:END -->"
WORKFLOWS_DIR = ".github/workflows"
REPO_URL = "https://github.com/IdkwhatImD0ing/IdkwhatImD0ing"
PROMPT = ph.PROMPT
PS2 = "> "
MAX_WIDTH = 72  # visible columns per line (links do not count, their text does)

# Only the comments are hardcoded; workflows may appear or disappear freely.
COMMENTS = {
    "artemis-ops.yaml": "visitor input: fsck, the button",
    "profile-summary.yaml": "an LLM rewrites the boot screen",
    "terminal-hero.yaml": "reroll the POST (1-in-8: panic)",
}
DEFAULT_COMMENT = "undocumented daemon"
TIMEZONE_LINE = "CRON_TZ=UTC"  # GitHub Actions cron is always UTC; say so like a real crontab

# The receipts pipeline, exactly as typed (a trailing | continues on PS2).
RECEIPT_COUNT = 4
RECEIPT_GREP = "^artemis-build"
SED_RULES = (("artemis-", ""), (", kept the good parts", ""))  # s/// without g: first match only
RECEIPT_COMMAND = (
    f'git log --oneline -{RECEIPT_COUNT} --grep "{RECEIPT_GREP}" |',
    "sed 's/artemis-//; s/, kept the good parts//'",
)
CLOSING_COMMENT = "# nobody reviews these. quality has improved."

CRON_PATTERN = re.compile(r"""cron:\s*["']?([0-9*,/\- ]+?)["']?\s*(?:#.*)?$""", re.MULTILINE)
SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]")
HEX = re.compile(r"[0-9a-f]+")

# A screen line is a list of (text, href) segments; href None means plain text.
Segment = tuple[str, "str | None"]


class Line(NamedTuple):
    segments: list[Segment]
    typed: bool = False  # keyboard input (prompt + command): drawn bold


def typed(text: str) -> Line:
    return Line([(text, None)], typed=True)


# --- crontab -------------------------------------------------------------------


def parse_workflows(directory: Path) -> list[tuple[str, str]]:
    """Return (schedule, filename) pairs; event-driven workflows get @reboot."""
    entries: list[tuple[str, str]] = []
    for path in sorted(directory.glob("*.y*ml")):
        filename = SAFE_NAME.sub("", path.name)[:40]
        if not filename.strip("."):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        crons = [" ".join(cron.split()) for cron in CRON_PATTERN.findall(text) if cron.strip()]
        if crons:
            entries.extend((cron[:24], filename) for cron in crons)
        else:
            entries.append(("@reboot", filename))
    return entries


def fit_comment(prefix_len: int, comment: str) -> str:
    """Trim a comment on word boundaries so the row stays inside MAX_WIDTH."""
    words = comment.split()
    while words and prefix_len + len("# " + " ".join(words)) > MAX_WIDTH:
        words.pop()
    return "# " + " ".join(words) if words else ""


def crontab_lines(entries: list[tuple[str, str]]) -> list[Line]:
    if not entries:
        raise ValueError("no workflow files found")
    sched_width = max(len(sched) for sched, _ in entries)
    name_width = max(len(name) for _, name in entries)
    lines = [Line([(TIMEZONE_LINE, None)])]
    for sched, name in entries:
        comment = fit_comment(sched_width + 2 + name_width + 2, COMMENTS.get(name, DEFAULT_COMMENT))
        pad = " " * (name_width - len(name))
        segments: list[Segment] = [
            (sched.ljust(sched_width) + "  ", None),
            (name, f"{WORKFLOWS_DIR}/{name}"),
        ]
        if comment:
            segments.append((pad + "  " + comment, None))
        lines.append(Line(segments))
    return lines


# --- git receipts ---------------------------------------------------------------


def clean_subject(subject: str) -> str:
    """Commit subjects are untrusted: printable ASCII only, whitespace collapsed.
    Anything else shows as '?', the way a terminal without the glyph would."""
    text = "".join(ch if " " <= ch <= "~" else ("?" if not ch.isspace() else " ") for ch in subject)
    return " ".join(text.split())[:200]


def apply_sed(subject: str) -> str:
    for pattern, replacement in SED_RULES:
        subject = subject.replace(pattern, replacement, 1)
    return subject


def git_receipts() -> list[tuple[str, str, str]]:
    """(full sha, abbreviated sha, subject after sed) for the newest build commits:
    the same query as RECEIPT_COMMAND, so the screen and the data cannot drift.
    Returns [] when git is missing, the repo is absent, or nothing matches."""
    command = ["git", "log", f"-{RECEIPT_COUNT}", f"--grep={RECEIPT_GREP}", "--format=%H%x09%h%x09%s"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                                errors="replace", timeout=30, check=True)
    except (OSError, subprocess.SubprocessError) as error:
        print(f"WARNING: git receipts skipped: {error}")
        return []
    receipts = []
    for raw in result.stdout.splitlines():
        parts = raw.split("\t", 2)
        if len(parts) != 3:
            continue
        full, short, subject = parts
        if len(full) != 40 or not HEX.fullmatch(full) or not HEX.fullmatch(short) or len(short) > 12:
            continue
        receipts.append((full, short, apply_sed(clean_subject(subject))))
    return receipts


def wrap(segments: list[Segment], width: int = MAX_WIDTH) -> list[Line]:
    """Soft-wrap output at the terminal edge, the way a 72-column tty would. Links
    stay whole (they only ever sit at the start of a line, well inside the width)."""
    out: list[list[Segment]] = [[]]
    col = 0
    for text, href in segments:
        if href is not None:
            out[-1].append((text, href))
            col += len(text)
            continue
        while text:
            room = width - col
            if room <= 0:
                out.append([])
                col, room = 0, width
            out[-1].append((text[:room], None))
            col += len(text[:room])
            text = text[room:]
    parts = [part for part in out if part]
    for part in parts:  # a wrap can leave an invisible trailing space; drop it
        body, href = part[-1]
        if href is None:
            part[-1] = (body.rstrip(), None)
    return [Line(part) for part in parts]


def receipt_lines(receipts: list[tuple[str, str, str]]) -> list[Line]:
    if not receipts:
        return []
    lines = [Line([]), typed(PROMPT + RECEIPT_COMMAND[0]), typed(PS2 + RECEIPT_COMMAND[1])]
    for full, short, subject in receipts:
        lines.extend(wrap([(short, f"{REPO_URL}/commit/{full}"), (" " + subject, None)]))
    lines.append(typed(PROMPT + CLOSING_COMMENT))
    return lines


# --- render --------------------------------------------------------------------


def visible(line: Line) -> str:
    return "".join(text for text, _ in line.segments)


def line_html(line: Line) -> str:
    out = []
    for text, href in line.segments:
        body = html.escape(text, quote=False)
        out.append(f'<a href="{html.escape(href)}">{body}</a>' if href else body)
    joined = "".join(out)
    # Typed input is bold (like a terminal's bright prompt); output stays plain.
    return f"<b>{joined}</b>" if line.typed else joined


def render(entries: list[tuple[str, str]], receipts: list[tuple[str, str, str]]) -> str:
    lines = crontab_lines(entries) + receipt_lines(receipts)
    for line in lines:
        if len(visible(line)) > MAX_WIDTH:
            raise ValueError(f"line exceeds {MAX_WIDTH} columns: {visible(line)!r}")
    content = "\n".join(line_html(line) for line in lines)
    if START in content or END in content or "<!--" in content:
        raise ValueError("rendered content unexpectedly contained a comment marker")
    return content


def main() -> None:
    parser = argparse.ArgumentParser(description="Render the CRONTAB block of README.md.")
    parser.add_argument("--readme", default="README.md")
    parser.add_argument("--workflows", default=WORKFLOWS_DIR)
    parser.add_argument("--no-git", action="store_true", help="render without the git receipts")
    parser.add_argument("--dry-run", action="store_true", help="print the block, write nothing")
    args = parser.parse_args()

    try:
        receipts = [] if args.no_git else git_receipts()
        content = render(parse_workflows(Path(args.workflows)), receipts)
    except (OSError, ValueError) as error:
        print(f"WARNING: crontab not rendered: {error}")
        return

    print("--- CRONTAB ---")
    print(content)
    if args.dry_run:
        return

    try:
        changed = replace_block(args.readme, START, END, content)
    except (ValueError, OSError) as error:
        print(f"WARNING: skipped CRONTAB block: {error}")
        return
    print("Updated crontab block" if changed else "Crontab block already current")


if __name__ == "__main__":
    main()
