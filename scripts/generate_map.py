"""The map screen at the top of the profile: cut the site's pictures, draw the tiles.

Local only; CI never runs it. Run from the repo root.

  python scripts/generate_map.py cut --site ../PortfolioV5/client
      Needs Pillow. Reads the site's painted map (public/sect/map/map_full.webp)
      and its opening poster (public/sect/poster/landscape.webp), read-only, and
      writes into scripts/data/map/:
        desk-<stop>.jpg, phone-<stop>.jpg   one painting strip per map row
        head-desk.jpg, head-desk-light.jpg  the header band (light: the same
        head-phone.jpg                      view as an ink-wash print on paper)
        strips.json                         where each strip sits
      Re-run it when the site's map or poster changes (the poster is a capture
      of the 3D scene, so a new bake means a new cut), then draw.

  python scripts/generate_map.py
      Stdlib. Draws every tile through art_map.py into assets/map/ (dark,
      -light, -phone, and the gate row's -still twins) and rewrites the MAP
      block in README.md. Everything is drawn in memory first: a missing glyph
      or a bad strip writes nothing, and the old files stay.

The stop positions and the route (scripts/data/map/stops.json) were measured on
the live map at art3m1s.me on 2026-10-24.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import art_map
import ink
from readme_blocks import replace_block

README = "README.md"
START, END = "<!-- MAP:START -->", "<!-- MAP:END -->"
QUALITY = 84
MAX_FILE = 1_000_000     # bytes per tile; GitHub's image proxy drops files near 5 MB, and phones pay for every byte

# The poster (1640 x 972) has pale tile seams in its corners (above y 140 and below y 820),
# so both bands stay inside its clean middle.
# The desk band leaves out the poster's right edge, so the gate sits between the line and the
# key and the moon clears the key.
POSTER_BOX = {"desk": (0, 270, 1460), "phone": (560, 232, 1500)}


def cut(site: Path) -> None:
    from PIL import Image

    painting = Image.open(site / "public/sect/map/map_full.webp").convert("RGB")
    poster = Image.open(site / "public/sect/poster/landscape.webp").convert("RGB")
    if painting.size != (art_map.MAP_W, art_map.MAP_H):
        raise SystemExit(f"map_full.webp is {painting.size}, expected {art_map.MAP_W} x {art_map.MAP_H}")
    art_map.DATA.mkdir(parents=True, exist_ok=True)

    def save(im: Image.Image, name: str) -> None:
        im.save(art_map.DATA / f"{name}.jpg", quality=QUALITY, optimize=True, progressive=True)

    rows: dict[str, dict] = {}
    for kind in art_map.KINDS:
        geo = art_map.layout(kind)
        R = geo["R"]
        box = (round(geo["u0"] * art_map.MAP_W), round(art_map.V0 * art_map.MAP_H),
               round(geo["u1"] * art_map.MAP_W), round(art_map.V1 * art_map.MAP_H))
        full = painting.crop(box).resize((round(geo["pw"] * R), round(geo["ph"] * R)), Image.LANCZOS)
        rows[kind] = {}
        for name in art_map.ORDER:
            a, b = art_map.strip_band(geo, name)
            px0 = max(0, round((a - geo["py"]) * R))
            px1 = min(full.height, round((b - geo["py"]) * R))
            save(full.crop((0, px0, full.width, px1)), f"{kind}-{name}")
            rows[kind][name] = {"px0": px0, "px1": px1}

    # the header band: the gate and the moon from the site's opening poster
    W, head = art_map.KINDS["desk"]["W"], art_map.KINDS["desk"]["head"]
    x0, y0, x1 = POSTER_BOX["desk"]
    h = round((x1 - x0) * head / W)
    desk = poster.crop((x0, y0, x1, y0 + h)).resize((W * 2, head * 2), Image.LANCZOS)
    save(desk, "head-desk")
    save(ink_wash(desk, site / "src/app/sect/assets/paper.webp"), "head-desk-light")
    pw, ph = art_map.KINDS["phone"]["W"], art_map.HEAD_PHONE_PICTURE
    px0, py0, px1 = POSTER_BOX["phone"]
    phone = poster.crop((px0, py0, px1, py0 + round((px1 - px0) * ph / pw)))
    save(phone.resize((round(pw * 2.5), round(ph * 2.5)), Image.LANCZOS), "head-phone")

    meta = {"source": "PortfolioV5 client/public/sect/map/map_full.webp and poster/landscape.webp",
            "quality": QUALITY, "rows": rows}
    (art_map.DATA / "strips.json").write_text(json.dumps(meta, indent=1) + "\n", encoding="utf-8")
    print(f"map: cut {sum(len(r) for r in rows.values())} strips and 3 header bands into {art_map.DATA}")


def ink_wash(im, paper: Path):
    """The day print: the same view as an ink-wash print on aged paper (the
    recipe the old light header used)."""
    from PIL import Image, ImageChops, ImageEnhance, ImageFilter, ImageOps

    grey = ImageOps.autocontrast(ImageOps.grayscale(im), cutoff=1)
    grey = ImageEnhance.Contrast(grey).enhance(1.2)
    grey = Image.blend(grey, grey.filter(ImageFilter.GaussianBlur(1.6)), 0.45)
    ink_rgb, paper_rgb = (31, 26, 23), (244, 236, 220)
    lut = []
    for c in range(3):
        lut += [round(ink_rgb[c] + (paper_rgb[c] - ink_rgb[c]) * (v / 255) ** 0.72) for v in range(256)]
    toned = Image.merge("RGB", (grey, grey, grey)).point(lut)
    if paper.exists():
        tile = Image.open(paper).convert("RGB")
        sheet = Image.new("RGB", toned.size)
        for ty in range(0, toned.height, tile.height):
            for tx in range(0, toned.width, tile.width):
                sheet.paste(tile, (tx, ty))
        toned = ImageChops.multiply(toned, ImageEnhance.Brightness(sheet).enhance(1.04))
    return toned


def draw() -> None:
    files = art_map.render_all()
    for path, svg in files.items():
        if len(svg.encode("utf-8")) > MAX_FILE:
            raise SystemExit(f"{path} is {len(svg.encode('utf-8'))} bytes, over {MAX_FILE}")
    changed = sum(ink.write_svg(Path(path), svg) for path, svg in files.items())
    print(f"map: {changed} of {len(files)} tile file(s) changed")
    try:
        if replace_block(README, START, END, art_map.readme_block()):
            print("map: README MAP block updated")
    except ValueError as error:
        print(f"map: {error}; README left alone", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="Cut and draw the map screen.")
    sub = parser.add_subparsers(dest="cmd")
    c = sub.add_parser("cut", help="cut the site's map and poster into strips (Pillow)")
    c.add_argument("--site", type=Path, default=Path("../PortfolioV5/client"))
    args = parser.parse_args()
    if args.cmd == "cut":
        cut(args.site)
    draw()


if __name__ == "__main__":
    main()
