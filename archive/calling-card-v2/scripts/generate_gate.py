"""山门, the Mountain Gate: the hero, a still picture of art3m1s.me.

Stills only. The profile has no animated images (CLAUDE.md, "Stills only"):
every file this script writes is a single-frame WebP, and it checks that
before it finishes. The old animated heroes are kept in archive/calling-card-v1/assets/gate/.

Local only (needs Pillow; CI never runs it). Three commands:

  python scripts/generate_gate.py titles
      Writes the title overlays, drawn through ink.py like every other SVG:
      assets/gate/title.svg (dark, 1200 x 600), title-light.svg, title-phone.svg
      (720 x 720). "Bill Zhang" is the biggest text on the page, with his line
      under it; 日月神教 is a small mark with its seal and English gloss in the
      corner. They are not referenced by the README; they are kept so a
      re-capture can composite the same titles.

  python scripts/generate_gate.py encode --frames DIR --overlays DIR --paper PATH
      DIR holds captured frames (g000.jpg ... in flight order, 1280 x 720) and
      the overlays rasterised to PNG with a transparent background (title.png,
      title-light.png, title-phone.png). Writes three stills:
        assets/gate/hero-still.webp        1200 x 600, frame --hold, <= 400 KB
        assets/gate/hero-light.webp        1200 x 600, frame --hold as an ink-wash
                                           print on paper, <= 600 KB
        assets/gate/hero-phone-still.webp  720 x 720, frame --phone-hold, <= 250 KB
      --hold defaults to 46: the gate centred at the top of the stair, with the
      moon fully clear at top right. --phone-hold defaults to the last frame
      (the gate up close; the square crop cuts the moon at any distance).

  python scripts/generate_gate.py pick --anim PATH --frame N
      Rebuilds hero-still.webp from frame N of an old animated hero (its title
      is already composited in), smoothing the flat sky where the animation's
      encoder left blocks. This is how the current hero-still.webp was made:
      --anim archive/calling-card-v1/assets/gate/hero.webp --frame 46.

How frames are captured (Playwright, viewport 1280 x 720): open
https://art3m1s.me, wait for the scene, hide every page element except the
WebGL canvas with injected CSS
    body *{visibility:hidden!important} canvas{visibility:visible!important}
(so no name, label or old text from the site's interface is in the picture),
then scroll from 0 to 900 px in 96 steps, one screenshot per step. The camera
reaches the gate near step 75. Never run Blender for this.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import ink

OUT = Path("assets/gate")
W, H = 1200, 600
PW = 720

# ---------------------------------------------------------------------------------------
# titles (stdlib: drawn through ink.py)
# ---------------------------------------------------------------------------------------


def _shadow_defs(mode: str) -> str:
    colour = "#0E0C14" if mode == "dark" else "#F4ECDC"
    return (f'<filter id="sh" x="-20%" y="-40%" width="140%" height="180%">'
            f'<feGaussianBlur in="SourceAlpha" stdDeviation="6"/>'
            f'<feFlood flood-color="{colour}" flood-opacity=".9"/><feComposite operator="in" in2="SourceAlpha"/>'
            f'<feGaussianBlur stdDeviation="5"/><feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter>')


def _band(w: float, h: float, top: float, mode: str) -> tuple[str, str]:
    colour = "#0E0C14" if mode == "dark" else "#F4ECDC"
    defs = (f'<linearGradient id="band" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{colour}" stop-opacity="0"/>'
            f'<stop offset=".55" stop-color="{colour}" stop-opacity=".62"/>'
            f'<stop offset="1" stop-color="{colour}" stop-opacity=".9"/></linearGradient>')
    return defs, f'<rect x="0" y="{ink.fmt(top)}" width="{ink.fmt(w)}" height="{ink.fmt(h - top)}" fill="url(#band)"/>'


NAME_LINE = "builds voice-first LLM agents · Pinterest"
GLOSS = ink.SECT_EN.upper()
GLOSS_TRACK = 0.22


def title_svg(mode: str) -> str:
    """Two rows on one grid. Left: the name (the biggest text on the page) over
    his line. Right, like a painter's inscription and seal: 日月神教 and the 神
    seal over the English gloss."""
    defs, band = _band(W, H, 300, mode)
    right = W - 56
    body = [band, '<g filter="url(#sh)">']
    body.append(ink.text(56, 506, ink.NAME, 92, "display", "tx"))
    line_size = 35
    gloss_x = right - ink.measure(GLOSS, 17, "medium", GLOSS_TRACK)
    while 58 + ink.measure(NAME_LINE, line_size, "medium") + 40 > gloss_x and line_size > 30:
        line_size -= 2      # the spec's one step down: 35, then 33
    body.append(ink.text(58, 556, NAME_LINE, line_size, "medium", "tx"))
    seal_size = 28
    seal_x = right - seal_size
    body.append(ink.text(seal_x - 8, 506, ink.SECT_ZH, 35, "brush", "tx", anchor="end"))
    body.append(ink.seal(seal_x, 476, seal_size, "神"))
    body.append(ink.text(right, 556, GLOSS, 17, "medium", "mu", anchor="end", tracking=GLOSS_TRACK))
    body.append("</g>")
    label = (f"Title for the gate: {ink.NAME}, {NAME_LINE}; the mark {ink.SECT_ZH}, "
             f"{ink.SECT_EN}, with its seal")
    return ink.doc(W, H, "".join(body), label, mode, defs=defs + _shadow_defs(mode))


def title_phone_svg() -> str:
    """The same three things, centred, for a square phone hero."""
    defs, band = _band(PW, PW, 360, "dark")
    body = [band, '<g filter="url(#sh)">']
    body.append(ink.text(PW / 2, 588, ink.NAME, 112, "display", "tx", anchor="middle"))
    line_size = 29.0
    while ink.measure(NAME_LINE, line_size, "medium") > 640 and line_size > 20:
        line_size -= 0.5
    body.append(ink.text(PW / 2, 636, NAME_LINE, line_size, "medium", "tx", anchor="middle"))
    zw = ink.measure(ink.SECT_ZH, 30, "brush")
    gw = ink.measure(GLOSS, 20, "medium", GLOSS_TRACK)
    seal_size = 22
    total = zw + 8 + seal_size + 16 + gw
    x = (PW - total) / 2
    body.append(ink.text(x, 690, ink.SECT_ZH, 30, "brush", "tx"))
    x += zw + 8
    body.append(ink.seal(x, 690 - seal_size - 2, seal_size, "神"))
    x += seal_size + 16
    body.append(ink.text(x, 690, GLOSS, 20, "medium", "mu", tracking=GLOSS_TRACK))
    body.append("</g>")
    label = f"Title for the gate on phones: {ink.NAME}, {NAME_LINE}; {ink.SECT_ZH}, {ink.SECT_EN}"
    return ink.doc(PW, PW, "".join(body), label, "dark", defs=defs + _shadow_defs("dark"))


def write_titles() -> None:
    files = {"title.svg": title_svg("dark"), "title-light.svg": title_svg("light"),
             "title-phone.svg": title_phone_svg()}
    changed = sum(ink.write_svg(OUT / name, svg) for name, svg in files.items())
    print(f"gate titles: {changed} of {len(files)} changed in {OUT.as_posix()}")


# ---------------------------------------------------------------------------------------
# encoding (Pillow)
# ---------------------------------------------------------------------------------------


def assert_still(path: Path) -> None:
    """Stills only: refuse to leave an animated file behind."""
    from PIL import Image

    with Image.open(path) as im:
        if getattr(im, "n_frames", 1) != 1 or getattr(im, "is_animated", False):
            path.unlink()
            raise SystemExit(f"{path.as_posix()} came out animated; removed it (stills only)")


def save_still(path: Path, im, budget: int, q: int = 86) -> None:
    """One frame, the best quality that fits the byte budget."""
    while True:
        im.save(path, quality=q, method=6)
        size = path.stat().st_size
        if size <= budget or q <= 40:
            print(f"{path.as_posix()}: q{q}, {size / 1e3:.0f} KB")
            break
        q -= 4
    assert_still(path)


def clean_blocks(im):
    """Smooth the flat parts of a frame (sky, mist) where a lossy encoder left
    8 px blocks, and keep every edge (gate, trees, the title) as it was."""
    from PIL import Image, ImageFilter, ImageOps

    grey = ImageOps.grayscale(im)
    detail = grey.filter(ImageFilter.GaussianBlur(1.2)).filter(ImageFilter.FIND_EDGES)
    detail = detail.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.GaussianBlur(4))
    flat = detail.point(lambda v: 255 if v < 5 else (0 if v > 11 else int(255 * (11 - v) / 6)))
    out = Image.composite(im.filter(ImageFilter.GaussianBlur(7)), im, flat)
    band = 430                      # the title band stays exactly as composited
    out.paste(im.crop((0, band, im.width, im.height)), (0, band))
    return out


def pick(anim: Path, frame: int) -> None:
    """hero-still.webp from one frame of an old animated hero."""
    from PIL import Image, ImageSequence

    with Image.open(anim) as im:
        frames = getattr(im, "n_frames", 1)
        if not 0 <= frame < frames:
            raise SystemExit(f"{anim} has {frames} frames; frame {frame} is out of range")
        chosen = next(f for i, f in enumerate(ImageSequence.Iterator(im)) if i == frame).convert("RGB")
    if chosen.size != (W, H):
        raise SystemExit(f"expected a {W} x {H} hero, got {chosen.size}")
    OUT.mkdir(parents=True, exist_ok=True)
    save_still(OUT / "hero-still.webp", clean_blocks(chosen), 400_000, q=90)


def encode(frames_dir: Path, overlays: Path, paper: Path, hold: int, phone_hold: int) -> None:
    from PIL import Image, ImageChops, ImageEnhance, ImageFilter, ImageOps

    frames = sorted(frames_dir.glob("g*.jpg"))
    if len(frames) < 60:
        raise SystemExit(f"expected the captured flight in {frames_dir} (g000.jpg ...), found {len(frames)}")
    gate_frame = frames[min(hold, len(frames) - 1)]
    phone_frame = frames[phone_hold if 0 <= phone_hold < len(frames) else -1]

    def desk(path: Path) -> Image.Image:
        im = Image.open(path).convert("RGB")
        return im.crop((0, 30, 1280, 670)).resize((W, H), Image.LANCZOS)

    def square(path: Path) -> Image.Image:
        im = Image.open(path).convert("RGB")
        return im.crop((280, 0, 1000, 720)).resize((PW, PW), Image.LANCZOS)

    def over(base: Image.Image, overlay: Image.Image) -> Image.Image:
        out = base.convert("RGBA")
        out.alpha_composite(overlay)
        return out.convert("RGB")

    OUT.mkdir(parents=True, exist_ok=True)
    title = Image.open(overlays / "title.png").convert("RGBA").resize((W, H), Image.LANCZOS)
    title_light = Image.open(overlays / "title-light.png").convert("RGBA").resize((W, H), Image.LANCZOS)
    title_phone = Image.open(overlays / "title-phone.png").convert("RGBA").resize((PW, PW), Image.LANCZOS)

    save_still(OUT / "hero-still.webp", over(desk(gate_frame), title), 400_000)
    save_still(OUT / "hero-phone-still.webp", over(square(phone_frame), title_phone), 250_000)

    # the day print: the gate as an ink-wash print on aged paper
    gate = desk(gate_frame)
    grey = ImageOps.autocontrast(ImageOps.grayscale(gate), cutoff=1)
    grey = ImageEnhance.Contrast(grey).enhance(1.25)
    bleed = grey.filter(ImageFilter.GaussianBlur(1.6))
    grey = Image.blend(grey, bleed, 0.45)
    ink_rgb, paper_rgb = (31, 26, 23), (244, 236, 220)
    lut = []
    for c in range(3):
        lut += [round(ink_rgb[c] + (paper_rgb[c] - ink_rgb[c]) * (v / 255) ** 0.72) for v in range(256)]
    toned = Image.merge("RGB", (grey, grey, grey)).point(lut)
    if paper.exists():
        tile = Image.open(paper).convert("RGB")
        sheet = Image.new("RGB", (W, H))
        for ty in range(0, H, tile.height):
            for tx in range(0, W, tile.width):
                sheet.paste(tile, (tx, ty))
        toned = ImageChops.multiply(toned, ImageEnhance.Brightness(sheet).enhance(1.04))
    fibre = Image.effect_noise((W, H), 22).filter(ImageFilter.GaussianBlur(0.6)).convert("L")
    fibre = ImageOps.autocontrast(fibre).point(lambda v: 255 - (255 - v) // 9)
    toned = ImageChops.multiply(toned, Image.merge("RGB", (fibre, fibre, fibre)))
    save_still(OUT / "hero-light.webp", over(toned, title_light), 600_000)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Mountain Gate hero (stills only).")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("titles", help="write the title overlay SVGs")
    enc = sub.add_parser("encode", help="encode the three hero stills from captured frames")
    enc.add_argument("--frames", required=True, type=Path)
    enc.add_argument("--overlays", required=True, type=Path, help="title.png, title-light.png, title-phone.png")
    enc.add_argument("--paper", default=Path("../PortfolioV5/client/src/app/sect/assets/paper.webp"), type=Path)
    enc.add_argument("--hold", type=int, default=46, help="the frame for the desktop and light stills")
    enc.add_argument("--phone-hold", type=int, default=-1, help="the frame for the phone still (-1: the last)")
    pk = sub.add_parser("pick", help="hero-still.webp from one frame of an old animated hero")
    pk.add_argument("--anim", required=True, type=Path)
    pk.add_argument("--frame", type=int, default=46)
    args = parser.parse_args()
    if args.cmd == "titles":
        write_titles()
    elif args.cmd == "pick":
        pick(args.anim, args.frame)
    else:
        encode(args.frames, args.overlays, args.paper, args.hold, args.phone_hold)


if __name__ == "__main__":
    sys.exit(main())
