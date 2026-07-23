"""Render assets/neofetch.svg: a fake neofetch card for bill@whitebox.

Left pane is ASCII art of the GitHub avatar (Pillow + network, with an
offline hand-drawn fallback); right pane is the classic key: value layout
fed by live GitHub stats when the API cooperates and known constants when
it does not. Run from the repo root: python scripts/generate_neofetch.py
"""

import argparse
import json
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

USERNAME = "IdkwhatImD0ing"
AVATAR_URL = f"https://github.com/{USERNAME}.png"
API_USER_URL = f"https://api.github.com/users/{USERNAME}"
API_REPOS_URL = f"https://api.github.com/users/{USERNAME}/repos?per_page=100"
ACCOUNT_CREATED = date(2021, 9, 21)
FALLBACK_STATS = {"repos": 81, "followers": 173, "stars": 83}

WIDTH, HEIGHT = 820, 400
BG = "#0D1117"
GREEN = "#00FF41"
DIM_TEXT = "#8bd5a0"
FONT = "ui-monospace, 'Cascadia Code', Menlo, Consolas, monospace"

ART_COLS, ART_ROWS = 40, 20
CHAR_RAMP = " .:-=+*#%@"
GREEN_SHADES = ("#0f5323", "#149238", "#00c837", "#00FF41")

TITLE_BAR_H = 28
ART_X, ART_FONT, ART_LINE_H = 24, 12, 14
INFO_X, INFO_FONT, INFO_LINE_H = 348, 13, 15
INFO_TOP = 58
CHAR_W = 0.602  # monospace advance width per glyph, in em

PALETTE = (
    "#21262d", "#ff5555", "#00FF41", "#ffb000",
    "#58a6ff", "#bd93f9", "#39c5cf", "#c9d1d9",
)

FALLBACK_ART = """\
   .==================================.
   |  o  WHITEBOX              [pwr]  |
   |==================================|
   |   .------------------------.     |
   |   |  ART3M1S OS  Rev 5080  |     |
   |   '------------------------'     |
   |                                  |
   |   RTX 5080 :: Astral White       |
   |   [########]    [########]       |
   |   9800X3D  :: 96GB @ 6000MT      |
   |                                  |
   |   fans: 7   rgb: off  vibes: on  |
   |                                  |
   |   >_ avatar offline; picture     |
   |      a guy shipping demos        |
   |                                  |
   |   ..............................  |
   |   ::::::::::::::::::::::::::::::  |
   '=================================='
"""

Cell = tuple[str, int]  # (character, shade index into GREEN_SHADES)


def fetch_bytes(url: str, timeout: float) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "whitebox-neofetch"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def fetch_json(url: str, timeout: float):
    return json.loads(fetch_bytes(url, timeout).decode("utf-8"))


def fetch_stats() -> dict[str, int]:
    """Live repos/followers/stars, or the known constants on any failure."""
    stats = dict(FALLBACK_STATS)
    try:
        user = fetch_json(API_USER_URL, timeout=5)
        stats["repos"] = int(user["public_repos"])
        stats["followers"] = int(user["followers"])
    except Exception as error:
        print(f"warning: user stats unavailable ({error}); using fallback")
        return stats
    try:
        repos = fetch_json(API_REPOS_URL, timeout=5)
        stats["stars"] = sum(int(repo.get("stargazers_count", 0)) for repo in repos)
    except Exception as error:
        print(f"warning: star count unavailable ({error}); using fallback")
    return stats


def ensure_pillow() -> bool:
    try:
        import PIL  # noqa: F401
        return True
    except ImportError:
        pass
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--user", "pillow"],
            check=True, capture_output=True, timeout=120,
        )
        import PIL  # noqa: F401
        return True
    except Exception as error:
        print(f"warning: pillow unavailable ({error})")
        return False


def avatar_ascii() -> list[list[Cell]] | None:
    """Avatar -> 40x20 shaded ASCII grid, or None if anything is missing."""
    if not ensure_pillow():
        return None
    try:
        raw = fetch_bytes(AVATAR_URL, timeout=3)
    except Exception as error:
        print(f"warning: avatar fetch failed ({error})")
        return None
    try:
        from io import BytesIO

        from PIL import Image

        image = Image.open(BytesIO(raw)).convert("RGBA")
        backdrop = Image.new("RGBA", image.size, (13, 17, 23, 255))
        backdrop.alpha_composite(image)
        gray = backdrop.convert("L").resize((ART_COLS, ART_ROWS))
        pixels = list(gray.tobytes())
        lo, hi = min(pixels), max(pixels)
        span = max(hi - lo, 1)
        grid: list[list[Cell]] = []
        for row in range(ART_ROWS):
            cells: list[Cell] = []
            for col in range(ART_COLS):
                level = (pixels[row * ART_COLS + col] - lo) / span
                char = CHAR_RAMP[min(int(level * len(CHAR_RAMP)), len(CHAR_RAMP) - 1)]
                shade = min(int(level * len(GREEN_SHADES)), len(GREEN_SHADES) - 1)
                cells.append((char, shade))
            grid.append(cells)
        return grid
    except Exception as error:
        print(f"warning: avatar conversion failed ({error})")
        return None


def fallback_ascii() -> list[list[Cell]]:
    grid: list[list[Cell]] = []
    for line in FALLBACK_ART.splitlines():
        padded = line.ljust(ART_COLS)[:ART_COLS]
        grid.append([(char, 3 if char.isalnum() else 1) for char in padded])
    return grid


def uptime_string(today: date) -> str:
    months = (today.year - ACCOUNT_CREATED.year) * 12 + today.month - ACCOUNT_CREATED.month
    if today.day < ACCOUNT_CREATED.day:
        months -= 1
    years, months = divmod(max(months, 0), 12)
    return f"{years} years, {months} months"


def art_text_rows(grid: list[list[Cell]]) -> list[str]:
    """One <text> per art row, consecutive same-shade cells merged into tspans."""
    rows: list[str] = []
    top = TITLE_BAR_H + 20 + max(0, (HEIGHT - TITLE_BAR_H - 40 - len(grid) * ART_LINE_H) // 2)
    for index, cells in enumerate(grid):
        y = top + index * ART_LINE_H
        spans: list[str] = []
        run, run_shade = "", cells[0][1]
        for char, shade in cells:
            if shade != run_shade:
                spans.append(f'<tspan fill="{GREEN_SHADES[run_shade]}">{escape(run)}</tspan>')
                run, run_shade = "", shade
            run += char
        spans.append(f'<tspan fill="{GREEN_SHADES[run_shade]}">{escape(run)}</tspan>')
        rows.append(
            f'<text x="{ART_X}" y="{y}" xml:space="preserve" font-family="{FONT}" '
            f'font-size="{ART_FONT}">{"".join(spans)}</text>'
        )
    return rows


def info_lines(stats: dict[str, int], uptime: str) -> list[tuple[str, str]]:
    return [
        ("OS", "ART3M1S OS 5.8 LTS x86_64"),
        ("Host", "Whitebox Rev 5080"),
        ("Kernel", "art3m1s 5.8.0-lts"),
        ("Uptime", uptime),
        ("Packages", f"{stats['repos']} (pacman), 35 (hackathon)"),
        ("Shell", "chaos 5.0.80"),
        ("Resolution", "35 wins x 58 entries"),
        ("DE", "tmux"),
        ("WM", "fzf"),
        ("Terminal", "the one you are reading"),
        ("CPU", "AMD Ryzen 7 9800X3D"),
        ("GPU", "RTX 5080 Astral White"),
        ("Memory", "96GB (mostly context windows)"),
        ("Followers", f"{stats['followers']} · Stars: {stats['stars']}"),
    ]


def build_svg(grid: list[list[Cell]], stats: dict[str, int], uptime: str) -> str:
    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="neofetch for bill@whitebox">',
        "<style>@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}"
        ".cursor{animation:blink 1.2s steps(1) infinite}</style>",
        f'<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{HEIGHT - 1}" rx="8" '
        f'fill="{BG}" stroke="{GREEN}" stroke-width="1"/>',
        f'<line x1="1" y1="{TITLE_BAR_H}" x2="{WIDTH - 1}" y2="{TITLE_BAR_H}" '
        f'stroke="{GREEN}" stroke-opacity="0.35" stroke-width="1"/>',
        '<circle cx="20" cy="14" r="5" fill="#ff5555"/>',
        '<circle cx="38" cy="14" r="5" fill="#ffb000"/>',
        '<circle cx="56" cy="14" r="5" fill="#00FF41"/>',
        f'<text x="{WIDTH // 2}" y="18" text-anchor="middle" font-family="{FONT}" '
        f'font-size="12" fill="{DIM_TEXT}">{escape("bill@whitebox: ~")}</text>',
    ]
    parts.extend(art_text_rows(grid))

    y = INFO_TOP
    header = "bill@whitebox"
    parts.append(
        f'<text x="{INFO_X}" y="{y}" font-family="{FONT}" font-size="{INFO_FONT}" '
        f'font-weight="bold" fill="{GREEN}">{escape(header)}</text>'
    )
    y += INFO_LINE_H
    parts.append(
        f'<text x="{INFO_X}" y="{y}" font-family="{FONT}" font-size="{INFO_FONT}" '
        f'fill="{DIM_TEXT}">{escape("-" * len(header))}</text>'
    )
    for key, value in info_lines(stats, uptime):
        y += INFO_LINE_H
        parts.append(
            f'<text x="{INFO_X}" y="{y}" xml:space="preserve" font-family="{FONT}" '
            f'font-size="{INFO_FONT}"><tspan font-weight="bold" fill="{GREEN}">'
            f'{escape(key)}:</tspan><tspan fill="{DIM_TEXT}"> {escape(value)}</tspan></text>'
        )

    y += INFO_LINE_H + 6
    for index, color in enumerate(PALETTE):
        parts.append(
            f'<rect x="{INFO_X + index * 26}" y="{y - 10}" width="24" height="13" fill="{color}"/>'
        )

    y += INFO_LINE_H + 8
    prompt = "bill@whitebox:~$"
    parts.append(
        f'<text x="{INFO_X}" y="{y}" font-family="{FONT}" font-size="{INFO_FONT}" '
        f'fill="{GREEN}">{escape(prompt)}</text>'
    )
    cursor_x = INFO_X + (len(prompt) + 1) * INFO_FONT * CHAR_W
    parts.append(
        f'<rect class="cursor" x="{cursor_x:.1f}" y="{y - 11}" width="8" height="14" fill="{GREEN}"/>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the neofetch SVG card.")
    parser.add_argument("--out", default="assets/neofetch.svg", help="output SVG path")
    args = parser.parse_args()

    grid = avatar_ascii() or fallback_ascii()
    svg = build_svg(grid, fetch_stats(), uptime_string(date.today()))
    ET.fromstring(svg)  # refuse to write malformed XML

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
