"""Draw the page's static dress: the four keys, the three section headings, the emblem and the seal.

These never change between runs, so CI does not call this. Re-run it by hand
after touching ink.py or the copy below, and commit the assets.
Run from the repo root: python scripts/generate_chrome.py

  assets/keys/<key>.svg, <key>-light.svg            the keys under the hero:
                                                    site 168 x 40 (the one jade key),
                                                    mail, linkedin, resume 104 x 40.
                                                    The right 8 px of each are clear
                                                    space: the gap to the next key.
  assets/banners/<name>.svg, -light, -phone         846 x 80 (phone 360 x 64) section
                                                    headings: a word and a hairline on
                                                    a transparent ground. The top 40 px
                                                    are empty on purpose: the section gap.
  assets/seal/emblem.svg, emblem-light.svg          64 x 64, the sect's 日月 logo
  assets/seal/seal-riyue.svg, seal-riyue-light.svg  96 x 96, the full seal

The design rules (one accent, six sizes, an 8 px grid) are in CLAUDE.md. Jade
fills exactly one key; nothing else on the page is jade. No brush lettering,
seals or cloud corners here: those belong to the hero and the footer.

The emblem and the seal are the site's own logo (PortfolioV5
client/src/lib/sect/logo.ts, ported in ink.logo_markup): a sun cradled in a
crescent moon on the cinnabar seal. If the site's logo changes, port the new
geometry into ink.py and re-run this script; file names and sizes stay.
"""

from __future__ import annotations

from pathlib import Path

import ink

GAP = 8                      # clear space baked into each key's right edge
KEY_H = 40
PRIMARY_W, SECONDARY_W = 168, 104
LABEL_SIZE = 14

# (file, label, accessible label) in README order; the README wraps each in its link.
PRIMARY = ("site", "Enter art3m1s.me", "Enter art3m1s.me")
SECONDARY = (
    ("mail", "Email", "Email"),
    ("linkedin", "LinkedIn", "LinkedIn"),
    ("resume", "Résumé", "Résumé"),
)

# (file, heading) in README order.
BANNERS = (
    ("shipped", "Shipped"),
    ("work", "Work"),
    ("now", "Now"),
)
BANNER_W, BANNER_H = ink.W, 80
PHONE_W, PHONE_H = ink.WP, 64


def _label_x(label: str, size: float, face: str, box_w: float) -> float:
    return (box_w - ink.measure(label, size, face)) / 2


def primary_key_svg(mode: str) -> str:
    """The one filled key: jade, with the label in the ground colour."""
    name, label, aria = PRIMARY
    w = PRIMARY_W - GAP
    body = (ink.rect(0, 0, w, KEY_H, "jd", 4)
            + ink.text(_label_x(label, LABEL_SIZE, "medium", w), 25, label, LABEL_SIZE, "medium", "bg"))
    return ink.doc(PRIMARY_W, KEY_H, body, aria, mode)


def secondary_key_svg(label: str, aria: str, mode: str) -> str:
    """A quiet key: ground fill, a 1 px hairline, the label in text colour."""
    w = SECONDARY_W - GAP
    body = (ink.rect(0, 0, w, KEY_H, "bg", 4)
            + f'<rect x="0.5" y="0.5" width="{w - 1}" height="{KEY_H - 1}" rx="4" class="ln" stroke-width="1"/>'
            + ink.text(_label_x(label, LABEL_SIZE, "body", w), 25, label, LABEL_SIZE, "body", "tx"))
    return ink.doc(SECONDARY_W, KEY_H, body, aria, mode)


def banner_svg(heading: str, mode: str) -> str:
    """A section start: the word, then a hairline to the column's edge."""
    size = 30
    body = [ink.text(0, 66, heading, size, "display", "tx")]
    x = ink.measure(heading, size, "display") + 20
    body.append(ink.hline(x, BANNER_W, 58.5, "ln"))
    return ink.doc(BANNER_W, BANNER_H, "".join(body), heading, mode)


def banner_phone_svg(heading: str) -> str:
    """Phones always get this dark file, light theme too, so it carries its own ground."""
    size = 26
    body = [ink.rect(0, 12, PHONE_W, 52, "bg", 4),
            ink.text(16, 47, heading, size, "display", "tx")]
    return ink.doc(PHONE_W, PHONE_H, "".join(body), heading, "dark")


def emblem_svg(mode: str) -> str:
    return ink.doc(64, 64, ink.logo(0, 0, 64, bold=True),
                   "日月, the sun and the moon: the seal of the Sun Moon Divine Sect", mode)


def seal_svg(mode: str) -> str:
    return ink.doc(96, 96, ink.logo(0, 0, 96, bold=False),
                   "日月, the sun and the moon: the full seal of the Sun Moon Divine Sect", mode)


def render_all() -> dict[str, str]:
    files: dict[str, str] = {}
    for mode, suffix in ink.MODES:
        files[f"assets/keys/{PRIMARY[0]}{suffix}.svg"] = primary_key_svg(mode)
        for name, label, aria in SECONDARY:
            files[f"assets/keys/{name}{suffix}.svg"] = secondary_key_svg(label, aria, mode)
        for name, heading in BANNERS:
            files[f"assets/banners/{name}{suffix}.svg"] = banner_svg(heading, mode)
        files[f"assets/seal/emblem{suffix}.svg"] = emblem_svg(mode)
        files[f"assets/seal/seal-riyue{suffix}.svg"] = seal_svg(mode)
    for name, heading in BANNERS:
        files[f"assets/banners/{name}-phone.svg"] = banner_phone_svg(heading)
    return files


def main() -> None:
    files = render_all()  # everything in memory first: a missing glyph writes nothing
    changed = sum(ink.write_svg(Path(path), svg) for path, svg in files.items())
    print(f"chrome: {changed} of {len(files)} file(s) changed")


if __name__ == "__main__":
    main()
