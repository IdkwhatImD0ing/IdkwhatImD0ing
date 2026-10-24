"""Draw the sect's static dress: talisman keys, section banners, the emblem and the seal.

These never change between runs, so CI does not call this. Re-run it by hand
after touching ink.py or the copy below, and commit the assets.
Run from the repo root: python scripts/generate_chrome.py

  assets/keys/<key>.svg, <key>-light.svg            118 x 40 talisman keys under the gate
  assets/banners/<nn-name>.svg, -light, -phone      846 x 56 (phone 360 x 48) section banners
  assets/seal/emblem.svg, emblem-light.svg          64 x 64, the sect's 日月 logo
  assets/seal/seal-riyue.svg, seal-riyue-light.svg  96 x 96, the full seal

The emblem and the seal are the site's own logo (PortfolioV5
client/src/lib/sect/logo.ts, ported in ink.logo_markup): a sun cradled in a
crescent moon on the cinnabar seal. If the site's logo changes, port the new
geometry into ink.py and re-run this script; file names and sizes stay.
"""

from __future__ import annotations

from pathlib import Path

import ink

KEY_W, KEY_H = 118, 40
BANNER_W, BANNER_H = ink.W, 56
PHONE_W, PHONE_H = ink.WP, 48

# (file, brush label, gloss) in README order; the README wraps each in its link.
KEYS = (
    ("site", "入山", "enter"),
    ("mail", "飞鸽", "mail"),
    ("linkedin", "名帖", "linkedin"),
    ("playbook", "秘籍", "playbook"),
    ("youtube", "留影", "youtube"),
    ("discord", "传讯", "discord"),
    ("dossier", "卷宗", "dossier"),
)

# (file, number, Chinese name, English name, gloss, what the right end says)
BANNERS = (
    ("02-mirror", "02", "心镜台", "Heart-Mirror Terrace", "about", "fly on"),
    ("03-forge", "03", "炼器峰", "Artifact Forge Peak", "projects", "fly on"),
    ("04-arena", "04", "论剑台", "Sword-Discussion Arena", "hackathons", "fly on"),
    ("05-mission", "05", "任务殿", "Mission Hall", "experience", "fly on"),
    ("06-library", "06", "藏经阁", "Scripture Pavilion", "education", "fly on"),
    ("07-steles", "07", "碑林", "Stele Forest", "skills", "fly on"),
    ("08-formation", "08", "护宗大阵", "Grand Sect-Protecting Formation", "the game", "fly on"),
    ("09-abode", "09", "洞府", "Cave Abode", "off duty", "fly on"),
    ("10-summit", "10", "望月台", "Moon-Gazing Terrace", "contact", "return to the gate"),
)
SHORT_NAMES = {"Grand Sect-Protecting Formation": "Sect-Protecting Formation",
               "Sword-Discussion Arena": "Sword Arena"}


def key_svg(name: str, brush: str, gloss: str, mode: str) -> str:
    primary = name == "site"
    brush_cls = "jd" if primary else "au"
    frame = "jd-s" if primary else "ln"
    bsize, gsize = 17, 12.5
    bw = ink.measure(brush, bsize, "brush")
    gw = ink.measure(gloss, gsize, "body")
    total = bw + 9 + gw
    x = (KEY_W - total) / 2
    body = (ink.plate(0, 0, KEY_W, KEY_H, corner=9, frame=frame, corner_cls="jd-s" if primary else "au-s",
                      fill="rs" if primary else "bg", rx=3)
            + ink.text(x, 26.5, brush, bsize, "brush", brush_cls)
            + ink.text(x + bw + 9, 25, gloss, gsize, "body", "tx"))
    return ink.doc(KEY_W, KEY_H, body, f"{brush}, {gloss}", mode)


def banner_svg(number: str, zh: str, en: str, gloss: str, right: str, mode: str) -> str:
    w, h = BANNER_W, BANNER_H
    body = [ink.plate(0, 0, w, h, corner=13)]
    x = 26
    body.append(ink.text(x, 33, number, 11, "mono", "mu", tracking=0.05))
    body.append(ink.vline(x + 24.5, 17, 39, "ln"))
    x += 38
    bsize = 30
    body.append(ink.text(x, 39.5, zh, bsize, "brush", "au"))
    x += ink.measure(zh, bsize, "brush") + 5
    body.append(ink.seal(x, 11, 17, "神"))
    x += 17 + 14
    body.append(ink.text(x, 36.5, en, 23, "display", "tx"))
    x += ink.measure(en, 23, "display") + 12
    body.append(ink.text(x, 35.5, gloss.upper(), 10.5, "medium", "mu", tracking=0.14))
    x += ink.measure(gloss.upper(), 10.5, "medium", 0.14) + 18
    rw = ink.measure(right, 12, "body")
    end = w - 26
    arrow = right == "fly on"
    tail = rw + (14 if arrow else 0)
    if end - tail - 18 - x > 40:
        body.append(ink.brush_rule(x, 28.5, end - tail - 18 - x, 6, "au", ' opacity=".42"'))
    if arrow:
        body.append(ink.text(end, 35, "▾", 12, "body", "jd", anchor="end"))
        body.append(ink.text(end - 14, 35, right, 12, "body", "jd", anchor="end"))
    else:
        body.append(ink.text(end, 35, right, 12, "body", "jd", anchor="end"))
    label = f"{zh}, {en}: {gloss}. " + ("Click to fly on to the next section." if arrow
                                         else "Click to return to the gate.")
    return ink.doc(w, h, "".join(body), label, mode)


def banner_phone_svg(number: str, zh: str, en: str, gloss: str, right: str) -> str:
    w, h = PHONE_W, PHONE_H
    body = [ink.plate(0, 0, w, h, corner=11)]
    x = 16
    body.append(ink.text(x, 29, number, 10, "mono", "mu"))
    x += 22
    bsize = 24
    body.append(ink.text(x, 33.5, zh, bsize, "brush", "au"))
    x += ink.measure(zh, bsize, "brush") + 4
    body.append(ink.seal(x, 10, 14, "神"))
    x += 14 + 10
    room = w - 16 - 14 - x
    name, size = en, 18.0
    while ink.measure(name, size, "display") > room and size > 15:
        size -= 0.5
    if ink.measure(name, size, "display") > room:
        name = SHORT_NAMES.get(en, en)
    name = ink.fit(name, room, size, "display")
    body.append(ink.text(x, 31.5, name, size, "display", "tx"))
    body.append(ink.text(w - 16, 30, "▾" if right == "fly on" else "▸", 12, "body", "jd", anchor="end"))
    label = f"{zh}, {en}: {gloss}."
    return ink.doc(w, h, "".join(body), label, "dark")


def emblem_svg(mode: str) -> str:
    return ink.doc(64, 64, ink.logo(0, 0, 64, bold=True),
                   "日月, the sun and the moon: the seal of the Sun Moon Divine Sect", mode)


def seal_svg(mode: str) -> str:
    return ink.doc(96, 96, ink.logo(0, 0, 96, bold=False),
                   "日月, the sun and the moon: the full seal of the Sun Moon Divine Sect", mode)


def render_all() -> dict[str, str]:
    files: dict[str, str] = {}
    for mode, suffix in ink.MODES:
        for name, brush, gloss in KEYS:
            files[f"assets/keys/{name}{suffix}.svg"] = key_svg(name, brush, gloss, mode)
        for name, number, zh, en, gloss, right in BANNERS:
            files[f"assets/banners/{name}{suffix}.svg"] = banner_svg(number, zh, en, gloss, right, mode)
        files[f"assets/seal/emblem{suffix}.svg"] = emblem_svg(mode)
        files[f"assets/seal/seal-riyue{suffix}.svg"] = seal_svg(mode)
    for name, number, zh, en, gloss, right in BANNERS:
        files[f"assets/banners/{name}-phone.svg"] = banner_phone_svg(number, zh, en, gloss, right)
    return files


def main() -> None:
    files = render_all()  # everything in memory first: a missing glyph writes nothing
    changed = sum(ink.write_svg(Path(path), svg) for path, svg in files.items())
    print(f"chrome: {changed} of {len(files)} file(s) changed")


if __name__ == "__main__":
    main()
