"""Render bill.ansi: a raw ANSI-escape business card for the terminal.

Meant to be consumed with:
    curl -sL https://raw.githubusercontent.com/IdkwhatImD0ing/IdkwhatImD0ing/main/bill.ansi

Stdlib only, no figlet: the block-letter banner font lives in this file.
Run from the repo root: python scripts/generate_ansi_card.py
"""

import argparse
import json
import re
import sys
from pathlib import Path

ESC = "\x1b"
RESET = f"{ESC}[0m"
DIM = f"{ESC}[2m"
BOLD = f"{ESC}[1m"
CSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

MAX_WIDTH = 72
INNER_WIDTH = 66  # content columns between the two border pipes

# 256-color green -> cyan gradient, one entry per banner row.
GRADIENT = (46, 47, 48, 50, 51)
GREEN = f"{ESC}[38;5;46m"
CYAN = f"{ESC}[38;5;51m"
LABEL = f"{ESC}[38;5;108m"
BORDER = f"{ESC}[38;5;41m"

STATUS_PATH = "assets/status.json"
DEFAULT_STATUS = "building voice agents; the agents are also building"
STATUS_MAX_LEN = 46

# 5-row block font, only the glyphs the banner needs.
BLOCK_FONT: dict[str, tuple[str, ...]] = {
    "B": ("███ ", "█  █", "███ ", "█  █", "███ "),
    "I": ("███", " █ ", " █ ", " █ ", "███"),
    "L": ("█  ", "█  ", "█  ", "█  ", "███"),
    "Z": ("████", "  █ ", " █  ", "█   ", "████"),
    "H": ("█  █", "█  █", "████", "█  █", "█  █"),
    "A": (" ██ ", "█  █", "████", "█  █", "█  █"),
    "N": ("█  █", "██ █", "█ ██", "█  █", "█  █"),
    "G": (" ███", "█   ", "█ ██", "█  █", " ███"),
    " ": ("  ", "  ", "  ", "  ", "  "),
}


def visible_len(line: str) -> int:
    return len(CSI_RE.sub("", line))


def sanitize(text: str) -> str:
    """Strip markup-ish and control characters from untrusted text, cap length."""
    cleaned = "".join(ch for ch in text if ch.isprintable() and ch not in "[]|<>`\\")
    return cleaned.strip()[:STATUS_MAX_LEN]


def banner_rows(word: str) -> list[str]:
    rows = []
    for row in range(5):
        rows.append(" ".join(BLOCK_FONT[letter][row] for letter in word))
    return rows


def read_status(path: str = STATUS_PATH) -> str:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return DEFAULT_STATUS
    if isinstance(payload, dict):
        for key in ("obsession", "status", "text", "message", "current", "building"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                cleaned = sanitize(value)
                if cleaned:
                    return cleaned
    elif isinstance(payload, str) and payload.strip():
        cleaned = sanitize(payload)
        if cleaned:
            return cleaned
    return DEFAULT_STATUS


def boxed(content_lines: list[str]) -> list[str]:
    """Wrap colored content lines in a rounded border, centered padding."""
    top = f"{BORDER}╭{'─' * (INNER_WIDTH + 2)}╮{RESET}"
    bottom = f"{BORDER}╰{'─' * (INNER_WIDTH + 2)}╯{RESET}"
    lines = [top]
    for line in content_lines:
        width = visible_len(line)
        left = (INNER_WIDTH - width) // 2
        right = INNER_WIDTH - width - left
        lines.append(
            f"{BORDER}│{RESET} {' ' * left}{line}{RESET}{' ' * right} {BORDER}│{RESET}"
        )
    lines.append(bottom)
    return lines


def build_card(status: str) -> str:
    content: list[str] = [""]
    for shade, row in zip(GRADIENT, banner_rows("BILL ZHANG")):
        content.append(f"{ESC}[38;5;{shade}m{BOLD}{row}{RESET}")
    content += [
        "",
        f"{CYAN}AI-first builder · hackathon operator · 35/58{RESET}",
        "",
        f"{LABEL}site{RESET}      {GREEN}https://art3m1s.me{RESET}",
        f"{LABEL}github{RESET}    {GREEN}github.com/IdkwhatImD0ing{RESET}",
        f"{LABEL}linkedin{RESET}  {GREEN}linkedin.com/in/bill-zhang1{RESET}",
        "",
        f"{LABEL}status{RESET}    {CYAN}{status}{RESET}",
        "",
        f"{DIM}works on my machine; my machine has 96GB of RAM{RESET}",
        "",
    ]
    lines = boxed(content)

    lines += [""] * 12
    lines += [
        f"{DIM}$ bill --help{RESET}",
        f"{DIM}  bill --hire     opens calendar, closes excuses{RESET}",
        f"{DIM}  bill --demo     ships a prototype before the meeting ends{RESET}",
        f"{DIM}  bill --coffee   required input voltage{RESET}",
        RESET,
    ]
    return "\n".join(lines) + "\n"


def validate(card: str) -> None:
    for line in card.splitlines():
        assert visible_len(line) <= MAX_WIDTH, f"line too wide: {line!r}"
    escapes = card.count(ESC)
    well_formed = len(CSI_RE.findall(card))
    assert escapes == well_formed, f"{escapes - well_formed} malformed escape sequence(s)"
    assert card.rstrip("\n").endswith(RESET), "card must end with a full SGR reset"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the bill.ansi business card.")
    parser.add_argument("--out", default="bill.ansi", help="output path")
    args = parser.parse_args()

    card = build_card(read_status())
    validate(card)

    out = Path(args.out)
    out.write_text(card, encoding="utf-8", newline="\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
