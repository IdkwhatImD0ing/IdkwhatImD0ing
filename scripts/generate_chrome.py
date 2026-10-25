"""Draw the page's static dress: the three section title cards and the seal.

These never change between runs, so CI does not call this. Re-run it by hand
after touching ink.py, art_map.STOPS or the copy below, and commit the assets.
Run from the repo root: python scripts/generate_chrome.py

  assets/banners/<name>.svg, -light, -phone         846 x 80 (phone 360 x 64) section
                                                    title cards. The top 40 px are empty
                                                    on purpose: the section gap.
  assets/seal/emblem.svg, emblem-light.svg          64 x 64, the footer seal
  assets/seal/seal-riyue.svg, seal-riyue-light.svg  96 x 96, the same seal, bigger (not on
                                                    the page; kept for anyone who links it)

A title card is the map legend's row for that section, set as a heading: the
place's name in the brush hand, the section's name, and on the right the
place's English name and its stop number, so each section reads as a stop of
the map above it (and of art3m1s.me). A dry brush rule runs between them, as
under every title on the site. The names and numbers come from art_map.STOPS,
the one list the map and these cards share. Phones get the dark file in both
themes, so the phone card carries its own ground.

The seal is the site's logo, the carved seal Bill picked on 2026-10-24 (ported
in ink.logo_markup): a paper crescent cradling a gold sun, cut out of cinnabar.
The light files are a real print of it: the crescent is a hole, so the page
shows through. If the site's logo changes, port the new geometry into ink.py
and re-run this script; file names and sizes stay.
"""

from __future__ import annotations

from pathlib import Path

import art_map
import ink

# (file, the map stop it is) in README order.
BANNERS = (
    ("shipped", "forge"),
    ("work", "mission"),
    ("now", "abode"),
)
BANNER_W, BANNER_H = ink.W, 80
PHONE_W, PHONE_H = ink.WP, 64


def stop(sid: str) -> tuple[int, str, str, str]:
    """(number, Chinese name, English name, section) of a map stop."""
    _sid, n, zh, en, section, *_ = next(s for s in art_map.STOPS if s[0] == sid)
    return n, zh, en, section


def label(sid: str) -> str:
    n, zh, en, section = stop(sid)
    return f"Stop {n:02d} of {len(art_map.STOPS)} on the map, {zh} ({en}): {section}"


def banner_svg(sid: str, mode: str) -> str:
    """A section starts: the place in the brush hand, the section's name, a dry
    brush rule, and the place's English name and stop number on the right."""
    n, zh, en, section = stop(sid)
    size, base = 30, 66
    body = [ink.text(0, base + 1, zh, size, "brush", "tx")]
    x = ink.measure(zh, size, "brush") + 14
    body.append(ink.text(x, base, section, size, "display", "tx"))
    x += ink.measure(section, size, "display") + 22
    tag = f"{en.upper()}  ·  STOP {n:02d} OF {len(art_map.STOPS)}"
    tag_w = ink.measure(tag, 12, "medium", 0.16)
    body.append(ink.text(BANNER_W, base - 1, tag, 12, "medium", "au", anchor="end", tracking=0.16,
                         extra=' opacity=".9"'))
    body.append(ink.brush_rule(x, base - 9, BANNER_W - tag_w - 22 - x, 5, "au", extra=' opacity=".38"'))
    return ink.doc(BANNER_W, BANNER_H, "".join(body), label(sid), mode)


def banner_phone_svg(sid: str) -> str:
    """Phones always get this dark file, light theme too, so it carries its own ground."""
    n, zh, _en, section = stop(sid)
    body = [ink.rect(0, 12, PHONE_W, 52, "bg", 4),
            ink.text(16, 48, zh, 22, "brush", "tx")]
    x = 16 + ink.measure(zh, 22, "brush") + 10
    body.append(ink.text(x, 47, section, 26, "display", "tx"))
    body.append(ink.text(PHONE_W - 16, 46, f"STOP {n:02d}", 11, "medium", "au", anchor="end", tracking=0.16,
                         extra=' opacity=".9"'))
    return ink.doc(PHONE_W, PHONE_H, "".join(body), label(sid), "dark")


SEAL_LABEL = "日月, the sun and the moon: the seal of the Sun Moon Divine Sect"


def emblem_svg(mode: str) -> str:
    return ink.doc(64, 64, ink.logo(0, 0, 64, variant=mode), SEAL_LABEL, mode)


def seal_svg(mode: str) -> str:
    return ink.doc(96, 96, ink.logo(0, 0, 96, variant=mode), SEAL_LABEL, mode)


def render_all() -> dict[str, str]:
    files: dict[str, str] = {}
    for mode, suffix in ink.MODES:
        for name, sid in BANNERS:
            files[f"assets/banners/{name}{suffix}.svg"] = banner_svg(sid, mode)
        files[f"assets/seal/emblem{suffix}.svg"] = emblem_svg(mode)
        files[f"assets/seal/seal-riyue{suffix}.svg"] = seal_svg(mode)
    for name, sid in BANNERS:
        files[f"assets/banners/{name}-phone.svg"] = banner_phone_svg(sid)
    return files


def main() -> None:
    files = render_all()  # everything in memory first: a missing glyph writes nothing
    changed = sum(ink.write_svg(Path(path), svg) for path, svg in files.items())
    print(f"chrome: {changed} of {len(files)} file(s) changed")


if __name__ == "__main__":
    main()
