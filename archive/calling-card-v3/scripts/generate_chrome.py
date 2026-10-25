"""Draw the page's static dress: the three section headings and the seal.

These never change between runs, so CI does not call this. Re-run it by hand
after touching ink.py or the copy below, and commit the assets.
Run from the repo root: python scripts/generate_chrome.py

  assets/banners/<name>.svg, -light, -phone         846 x 80 (phone 360 x 64) section
                                                    headings: a word and a hairline on
                                                    a transparent ground. The top 40 px
                                                    are empty on purpose: the section gap.
  assets/seal/emblem.svg, emblem-light.svg          64 x 64, the footer seal
  assets/seal/seal-riyue.svg, seal-riyue-light.svg  96 x 96, the same seal, bigger (not on
                                                    the page; kept for anyone who links it)

The design rules (one accent, six sizes, an 8 px grid) are in CLAUDE.md. No
brush lettering or cloud corners here: those belong to the map screen and the
footer. The map screen (its gold Enter key included) is drawn by
generate_map.py; the four keys that used to sit under the hero are in
archive/calling-card-v2/.

The seal is the site's logo, the carved seal Bill picked on 2026-10-24 (ported
in ink.logo_markup): a paper crescent cradling a gold sun, cut out of cinnabar.
The light files are a real print of it: the crescent is a hole, so the page
shows through. If the site's logo changes, port the new geometry into ink.py
and re-run this script; file names and sizes stay.
"""

from __future__ import annotations

from pathlib import Path

import ink

# (file, heading) in README order.
BANNERS = (
    ("shipped", "Shipped"),
    ("work", "Work"),
    ("now", "Now"),
)
BANNER_W, BANNER_H = ink.W, 80
PHONE_W, PHONE_H = ink.WP, 64


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


SEAL_LABEL = "日月, the sun and the moon: the seal of the Sun Moon Divine Sect"


def emblem_svg(mode: str) -> str:
    return ink.doc(64, 64, ink.logo(0, 0, 64, variant=mode), SEAL_LABEL, mode)


def seal_svg(mode: str) -> str:
    return ink.doc(96, 96, ink.logo(0, 0, 96, variant=mode), SEAL_LABEL, mode)


def render_all() -> dict[str, str]:
    files: dict[str, str] = {}
    for mode, suffix in ink.MODES:
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
