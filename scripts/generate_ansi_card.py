"""Render bill.ansi: a raw ANSI-escape business card for the terminal.

Meant to be consumed with:
    curl -sL https://raw.githubusercontent.com/IdkwhatImD0ing/IdkwhatImD0ing/main/bill.ansi

Stdlib only, no figlet: the block-letter banner font lives in this file.
Colors follow the phosphor design system (scripts/phosphor.py), mapped
to the nearest xterm-256 entries so the card looks the same in every terminal
that has 256 colors (truecolor is not assumed): phosphor green for lit and
active things, amber only where the reader can act, the terminal's own
foreground for body text and links, grays for everything else.
Run from the repo root: python scripts/generate_ansi_card.py
"""

import argparse
import json
import re
import unicodedata
from pathlib import Path

from render_hero import ENTERED, WON  # the hackathon record lives in one place

ESC = "\x1b"
RESET = f"{ESC}[0m"
BOLD = f"{ESC}[1m"
UNDERLINE = f"{ESC}[4m"
CSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

MAX_WIDTH = 72
INNER_WIDTH = 66  # content columns between the two border pipes


def fg256(code: int) -> str:
    return f"{ESC}[38;5;{code}m"


# Design token -> xterm-256 color (the 256 entry's hex in the comment).
PHOSPHOR = fg256(47)      # acc  #00FF41 -> #00ff5f  lit, won, active
DIM_PHOSPHOR = fg256(28)  # accd #149238 -> #008700  borders, separators
#                           (29 is nearer on paper but reads teal beside the banner)
AMBER = fg256(214)        # warn #FFB000 -> #ffaf00  "you can act here"
INK = f"{ESC}[39m"        # fg   the terminal's own foreground, so body text
#                           never vanishes on a light-background terminal
MUTED = fg256(246)        # mu   #9198A1 -> #949494  labels, secondary text
FAINT = fg256(242)        #      #6c6c6c             asides, the fine print

# Banner rows, top to bottom: phosphor at full beam, fading down the tube
# into the pure-green ramp (the 47/41/35/29 column drifts teal when dim).
GRADIENT = (47, 47, 41, 34, 28)

BORDER = DIM_PHOSPHOR
LABEL = MUTED
# Contact links: the terminal's own foreground, underlined like a hyperlink.
# Pale phosphor looked right on black but vanished on light terminals, and
# these three rows are the whole point of the card.
LINK = INK + UNDERLINE

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


def paint(text: str, style: str, bold: bool = False) -> str:
    return f"{style}{BOLD if bold else ''}{text}{RESET}"


def visible_len(line: str) -> int:
    return len(CSI_RE.sub("", line))


def single_width(char: str) -> bool:
    """True if the glyph takes exactly one terminal column (no CJK, no emoji,
    no combining marks), so visible_len() is the real on-screen width."""
    return not unicodedata.combining(char) and unicodedata.east_asian_width(char) not in "WF"


def sanitize(text: str) -> str:
    """Untrusted text: fold accents to ASCII (cafe, not caf?) and drop the rest,
    so wide glyphs and emoji cannot push the right border out. No control or
    markup-ish characters. Whitespace collapsed, length capped."""
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    cleaned = "".join(ch if ch.isprintable() else " " for ch in folded)
    cleaned = "".join(ch for ch in cleaned if ch not in "[]|<>`\\")
    return " ".join(cleaned.split())[:STATUS_MAX_LEN].rstrip()


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
    top = paint(f"╭{'─' * (INNER_WIDTH + 2)}╮", BORDER)
    bottom = paint(f"╰{'─' * (INNER_WIDTH + 2)}╯", BORDER)
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


def field(label: str, value: str, style: str, bold: bool = False) -> str:
    return paint(label.ljust(10), LABEL) + paint(value, style, bold)


def build_card(status: str) -> str:
    dot = paint(" · ", DIM_PHOSPHOR)
    content: list[str] = [""]
    for shade, row in zip(GRADIENT, banner_rows("BILL ZHANG")):
        content.append(paint(row, fg256(shade), bold=True))
    content += [
        "",
        paint("AI-first builder", INK) + dot + paint("hackathon operator", INK) + dot
        + paint(f"{WON}/{ENTERED}", PHOSPHOR, bold=True),
        "",
        field("site", "https://art3m1s.me", LINK),
        field("github", "github.com/IdkwhatImD0ing", LINK),
        field("linkedin", "linkedin.com/in/bill-zhang1", LINK),
        "",
        field("status", status, PHOSPHOR, bold=True),
        "",
        paint("works on my machine; my machine has 96GB of RAM", FAINT),
        "",
    ]
    lines = boxed(content)

    def option(flag: str, text: str) -> str:
        return "  " + paint("bill ", MUTED) + paint(flag.ljust(11), AMBER) + paint(text, MUTED)

    lines += [""] * 12
    lines += [
        paint("$ ", PHOSPHOR, bold=True) + paint("bill --help", INK, bold=True),
        option("--hire", "opens calendar, closes excuses"),
        option("--demo", "ships a prototype before the meeting ends"),
        option("--coffee", "required input voltage"),
        RESET,
    ]
    return "\n".join(lines) + "\n"


def validate(card: str) -> None:
    for line in card.splitlines():
        assert visible_len(line) <= MAX_WIDTH, f"line too wide: {line!r}"
        assert all(map(single_width, CSI_RE.sub("", line))), f"wide or combining glyph: {line!r}"
    escapes = card.count(ESC)
    well_formed = len(CSI_RE.findall(card))
    assert escapes == well_formed, f"{escapes - well_formed} malformed escape sequence(s)"
    assert card.rstrip("\n").endswith(RESET), "card must end with a full SGR reset"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the bill.ansi business card.")
    parser.add_argument("--out", default="bill.ansi", help="output path")
    parser.add_argument("--status", default=STATUS_PATH, help="status.json to read the obsession from")
    args = parser.parse_args()

    card = build_card(read_status(args.status))
    validate(card)

    out = Path(args.out)
    out.write_text(card, encoding="utf-8", newline="\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
