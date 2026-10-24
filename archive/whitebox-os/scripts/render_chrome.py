"""Render the static chrome: tmux status bars (section headers) and the F-key bar.

These never change between runs, so CI does not call this. Re-run it by hand
after touching phosphor.py or the window list, and commit assets/chrome/.
Run from the repo root: python scripts/render_chrome.py
"""

from __future__ import annotations

from pathlib import Path

import phosphor as ph

OUT = Path("assets/chrome")

# Window index -> the command "running" in it (tmux shows the pane title on the right).
PANE_TITLES = {
    1: "sort -r /var/log/hackathons.log | head -4",
    2: "fsck -n /dev/sda1",
    3: "crontab -l; tail /etc/passwd",
}

# F-key bar under the hero: contact, in the form of a TUI function-key row.
# (label, where it goes). The README wraps each key in a link; order is the key number.
FKEYS = (
    ("help", "man/bill.1.md"),
    ("agent", "https://art3m1s.me"),
    ("mail", "mailto:jzhang71@usc.edu"),
    ("linkedin", "https://linkedin.com/in/bill-zhang1"),
    ("playbook", "https://thehackathonplaybook.dev"),
    ("youtube", "https://www.youtube.com/@hackable-projects"),
    ("discord", "https://discord.com/users/185544015314288641"),
)
# 7 keys x 118 = 826px: one row even in a maximized 1280px window (831px column).
KEY_W, KEY_H = 118, 32


# Desktop bars are fluid (1:1 at any column width); the pane title bows out
# when the column is too narrow to hold it beside the window list.
NARROW_CSS = "@media (max-width: 720px){.rt{display:none}}"


def bar(index: int, mode: str, phone: bool) -> str:
    label = f"tmux window {index}:{ph.WINDOWS[index]}. click for the next window."
    if phone:
        body = ph.status_bar(index, ph.WP, compact=True, size=11)
        return ph.svg(ph.WP, 28, body, label, mode)
    body = ph.status_bar(index, ph.W, right=PANE_TITLES[index], fluid=True)
    return ph.svg(ph.W, 28, body, label, mode, extra_css=NARROW_CSS, fluid=True)


def fkey(number: int, label: str, mode: str) -> str:
    size = ph.SIZE_CHROME
    cw = ph.CW * size
    chip = f"F{number}"
    chip_w = len(chip) * cw + 10
    body = [
        f'<rect x="1" y="1" width="{KEY_W - 2}" height="{KEY_H - 2}" rx="6" class="pn"/>',
        f'<rect x="1.5" y="1.5" width="{KEY_W - 3}" height="{KEY_H - 3}" rx="6" class="ln"/>',
        f'<rect x="7" y="7" width="{ph.fmt(chip_w)}" height="{KEY_H - 14}" rx="2" class="chip"/>',
        ph.text(12, KEY_H / 2 + 4.2, chip, "ink", size, bold=True),
        ph.text(7 + chip_w + 8, KEY_H / 2 + 4.2, label, "fg", size),
    ]
    return ph.svg(KEY_W, KEY_H, "".join(body), f"{chip} {label}", mode)


def main() -> None:
    changed = 0
    for index in PANE_TITLES:
        for mode, suffix in (("dark", ""), ("light", "-light")):
            changed += ph.write_svg(OUT / f"bar-{index}{suffix}.svg", bar(index, mode, phone=False))
        changed += ph.write_svg(OUT / f"bar-{index}-phone.svg", bar(index, "dark", phone=True))
    for number, (label, _) in enumerate(FKEYS, start=1):
        for mode, suffix in (("dark", ""), ("light", "-light")):
            changed += ph.write_svg(OUT / f"key-f{number}{suffix}.svg", fkey(number, label, mode))
    print(f"chrome: {changed} file(s) changed in {OUT}")


if __name__ == "__main__":
    main()
