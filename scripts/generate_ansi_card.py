"""Render bill.ansi: Bill's business card, as raw ANSI escapes for the terminal.

Meant to be consumed with:
    curl -sL https://raw.githubusercontent.com/IdkwhatImD0ing/IdkwhatImD0ing/main/bill.ansi

Stdlib only, no figlet: the block-letter banner font lives in this file.
Colours follow the sect's design system (scripts/ink.py), mapped to the
nearest xterm-256 entries so the card looks the same in every terminal that
has 256 colours (truecolor is not assumed): gold for the name and what is
lit or won, jade for what he is working on now, the terminal's
own foreground for body text and links, greys for everything else. No
Chinese in the card: a wide glyph would push the right border out. The
"now" line lists the repos in the README's Now section (assets/status.json).
Run from the repo root: python scripts/generate_ansi_card.py
"""

import argparse
import json
import re
import unicodedata
from pathlib import Path

from ink import ENTERED, WON  # the hackathon record lives in one place

ESC = "\x1b"
RESET = f"{ESC}[0m"
BOLD = f"{ESC}[1m"
UNDERLINE = f"{ESC}[4m"
CSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

MAX_WIDTH = 72
INNER_WIDTH = 66  # content columns between the two border pipes


def fg256(code: int) -> str:
    return f"{ESC}[38;5;{code}m"


# Design token -> xterm-256 colour (the 256 entry's hex in the comment).
GOLD = fg256(222)         # gold   #E9C77E -> #ffd787  the name, lit, won
BRONZE = fg256(179)       # gold, dimmed     #d7af5f  borders, separators
EMBER = fg256(173)        # ember  #C98A4B -> #d7875f
JADE = fg256(115)         # jade   #8FE3C8 -> #87d7af  "you can act here", qi
SEAL = fg256(167)         # seal   #B8412D -> #d75f5f
INK = f"{ESC}[39m"        # text   the terminal's own foreground, so body text
#                           never vanishes on a light-background terminal
MUTED = fg256(246)        # muted  #A89F91 -> #949494  labels, secondary text
FAINT = fg256(242)        #        #6c6c6c             asides, the fine print

# Banner rows, top to bottom: paper-white gold fading down into bronze,
# like gilt catching the moon.
GRADIENT = (223, 222, 179, 137, 95)

BORDER = BRONZE
LABEL = MUTED
# Contact links: the terminal's own foreground, underlined like a hyperlink,
# so they read on dark and light terminals alike.
LINK = INK + UNDERLINE

STATUS_PATH = "assets/status.json"
DEFAULT_STATUS = "voice agents"
STATUS_MAX_LEN = 52  # the value column: INNER_WIDTH minus the 13-column label, with room to centre

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
    """The repos in the Now section, comma-joined and cut to whole names that
    fit the value column; DEFAULT_STATUS when there is nothing usable."""
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return DEFAULT_STATUS
    missions = payload.get("missions") if isinstance(payload, dict) else None
    names: list[str] = []
    for mission in missions if isinstance(missions, list) else []:
        repo = mission.get("repo") if isinstance(mission, dict) else None
        if isinstance(repo, str) and "/" in repo:
            name = sanitize(repo.split("/", 1)[1])
            if name and len(", ".join(names + [name])) <= STATUS_MAX_LEN:
                names.append(name)
    return ", ".join(names) or DEFAULT_STATUS


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


def field(label: str, value: str, style: str, bold: bool = False, width: int = 0) -> str:
    """label, value, and trailing padding to `width` so a block of fields
    centres as one column."""
    return paint(label.ljust(13), LABEL) + paint(value, style, bold) + " " * max(0, width - len(value))


def build_card(status: str) -> str:
    dot = paint(" · ", BRONZE)
    col = max(len("linkedin.com/in/bill-zhang1"), len(status))
    content: list[str] = [""]
    for shade, row in zip(GRADIENT, banner_rows("BILL ZHANG")):
        content.append(paint(row, fg256(shade), bold=True))
    content += [
        "",
        paint("Software Engineer", INK) + dot + paint("Pinterest", INK) + dot + paint("LLM agents", INK),
        paint(f"{WON} hackathons won", GOLD, bold=True) + paint(f" out of {ENTERED} entered", MUTED),
        "",
        field("site", "https://art3m1s.me", LINK, width=col),
        field("email", "billzhangsc@gmail.com", LINK, width=col),
        field("github", "github.com/IdkwhatImD0ing", LINK, width=col),
        field("linkedin", "linkedin.com/in/bill-zhang1", LINK, width=col),
        "",
        field("working on", status, JADE, bold=True, width=col),
        "",
    ]
    lines = boxed(content)
    lines.append(RESET)
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
    parser.add_argument("--status", default=STATUS_PATH, help="status.json to read the Now repos from")
    args = parser.parse_args()

    card = build_card(read_status(args.status))
    validate(card)

    out = Path(args.out)
    out.write_text(card, encoding="utf-8", newline="\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
