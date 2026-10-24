"""山门, the Mountain Gate: the hero, made from a real flight through art3m1s.me.

Local only (needs Pillow; CI never runs it). Two steps:

  python scripts/generate_gate.py titles
      Writes the title overlays, drawn through ink.py like every other SVG:
      assets/gate/title.svg (dark, 1200 x 600), title-light.svg, title-phone.svg
      (720 x 720). They are not referenced by the README; they are kept so a
      re-capture can composite the same titles.

  python scripts/generate_gate.py encode --frames DIR --overlays DIR --paper PATH
      DIR holds the captured frames (g000.jpg ... in flight order, 1280 x 720)
      and the overlays rasterised to PNG with a transparent background
      (title.png, title-light.png, title-phone.png). Writes:
        assets/gate/hero.webp              1200 x 600 animated, <= 6 MB
        assets/gate/hero-still.webp        1200 x 600, the gate, <= 400 KB
        assets/gate/hero-light.webp        1200 x 600, an ink-wash print on paper, <= 600 KB
        assets/gate/hero-phone.webp        720 x 720 animated, <= 3 MB
        assets/gate/hero-phone-still.webp  720 x 720, <= 250 KB

How the frames are captured (Playwright, viewport 1280 x 720): open
https://art3m1s.me, wait for the scene, hide every page element except the
WebGL canvas with injected CSS
    body *{visibility:hidden!important} canvas{visibility:visible!important}
(so no name, label or old text from the site's interface is in the picture),
then scroll from 0 to 900 px in 96 steps with a trapezoid speed profile, one
screenshot per step, then 24 more at rest while banners wave and motes drift.
The camera reaches the gate near step 75; the rest is the gate at rest.
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


def _chip(x: float, y: float, label: str, size: float, anchor: str = "start") -> str:
    """The site's HUD chip: letterspaced gold capitals in a hairline frame."""
    tw = ink.measure(label, size, "medium", 0.22)
    pad = 12
    x0 = x if anchor == "start" else x - tw - 2 * pad if anchor == "end" else x - tw / 2 - pad
    return (f'<rect x="{ink.fmt(x0)}" y="{ink.fmt(y - size - 8)}" width="{ink.fmt(tw + 2 * pad)}" '
            f'height="{ink.fmt(size + 16)}" rx="2" class="bg" opacity=".55"/>'
            f'<rect x="{ink.fmt(x0 + 0.5)}" y="{ink.fmt(y - size - 7.5)}" width="{ink.fmt(tw + 2 * pad - 1)}" '
            f'height="{ink.fmt(size + 15)}" rx="2" class="au-s" stroke-opacity=".7" stroke-width="1"/>'
            + ink.text(x0 + pad, y + 0.5, label, size, "medium", "au", tracking=0.22))


def title_svg(mode: str) -> str:
    defs, band = _band(W, H, 330, mode)
    name_cls = "tx"
    body = [band, '<g filter="url(#sh)">']
    body.append(ink.text(52, 528, ink.SECT_ZH, 70, "brush", name_cls))
    sx = 52 + ink.measure(ink.SECT_ZH, 70, "brush") + 8
    body.append(ink.seal(sx, 470, 34, "神"))
    body.append(ink.text(W - 52, 520, ink.NAME, 58, "display", name_cls, anchor="end"))
    body.append("</g>")
    body.append(_chip(52, 568, ink.SECT_EN.upper(), 14))
    body.append(ink.text(W - 52, 566, "AI ENGINEER  ·  ART3M1S.ME", 15, "medium", "au", anchor="end", tracking=0.2))
    label = "Title for the gate: 日月神教, Sun Moon Divine Sect; Bill Zhang, AI engineer, art3m1s.me"
    return ink.doc(W, H, "".join(body), label, mode, defs=defs + _shadow_defs(mode))


def title_phone_svg() -> str:
    defs, band = _band(PW, PW, 380, "dark")
    body = [band, '<g filter="url(#sh)">']
    zw = ink.measure(ink.SECT_ZH, 84, "brush")
    zx = (PW - zw - 44) / 2
    body.append(ink.text(zx, 600, ink.SECT_ZH, 84, "brush", "tx"))
    body.append(ink.seal(zx + zw + 6, 532, 38, "神"))
    body.append("</g>")
    body.append(_chip(PW / 2, 650, ink.SECT_EN.upper(), 17, anchor="middle"))
    body.append(ink.text(PW / 2, 696, "BILL ZHANG  ·  ART3M1S.ME", 18, "medium", "au", anchor="middle", tracking=0.2))
    label = "Title for the gate on phones: 日月神教, Sun Moon Divine Sect; Bill Zhang, art3m1s.me"
    return ink.doc(PW, PW, "".join(body), label, "dark", defs=defs + _shadow_defs("dark"))


def write_titles() -> None:
    files = {"title.svg": title_svg("dark"), "title-light.svg": title_svg("light"),
             "title-phone.svg": title_phone_svg()}
    changed = sum(ink.write_svg(OUT / name, svg) for name, svg in files.items())
    print(f"gate titles: {changed} of {len(files)} changed in {OUT.as_posix()}")


# ---------------------------------------------------------------------------------------
# encoding (Pillow)
# ---------------------------------------------------------------------------------------


def encode(frames_dir: Path, overlays: Path, paper: Path, quality: int, phone_quality: int) -> None:
    from PIL import Image, ImageChops, ImageEnhance, ImageFilter, ImageOps

    frames = sorted(frames_dir.glob("g*.jpg"))
    if len(frames) < 60:
        raise SystemExit(f"expected the captured flight in {frames_dir} (g000.jpg ...), found {len(frames)}")
    rest = 75                    # the camera reaches the gate here
    flight = frames[:rest + 1]
    held = frames[rest + 1::2]   # the gate at rest, every other frame
    last = held[-1]

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

    def timeline(make, overlay: Image.Image) -> tuple[list[Image.Image], list[int]]:
        imgs, durs = [], []
        imgs.append(over(make(flight[0]), overlay))
        durs.append(1100)                       # a breath on the stair before the climb
        for i, path in enumerate(flight[1:], start=1):
            imgs.append(over(make(path), overlay))
            ease = max(0, i - (rest - 5))       # the last few frames slow into the stop
            durs.append(72 + ease * ease * 9)
        for path in held:
            imgs.append(over(make(path), overlay))
            durs.append(115)
        first, end = imgs[0], imgs[-1]
        for k in range(1, 7):                   # crossfade back to the stair: a clean loop
            imgs.append(Image.blend(end, first, k / 7))
            durs.append(80)
        return imgs, durs

    def save_anim(path: Path, imgs: list, durs: list[int], q: int, budget: int) -> None:
        while True:
            imgs[0].save(path, save_all=True, append_images=imgs[1:], duration=durs, loop=0,
                         quality=q, method=6, minimize_size=True, allow_mixed=False)
            size = path.stat().st_size
            print(f"{path.as_posix()}: {len(imgs)} frames, {sum(durs) / 1000:.1f} s, q{q}, {size / 1e6:.2f} MB")
            if size <= budget or q <= 30:
                return
            q -= 6

    def save_still(path: Path, im: Image.Image, budget: int, q: int = 86) -> None:
        while True:
            im.save(path, quality=q, method=6)
            size = path.stat().st_size
            if size <= budget or q <= 40:
                print(f"{path.as_posix()}: q{q}, {size / 1e3:.0f} KB")
                return
            q -= 4

    OUT.mkdir(parents=True, exist_ok=True)
    title = Image.open(overlays / "title.png").convert("RGBA").resize((W, H), Image.LANCZOS)
    title_light = Image.open(overlays / "title-light.png").convert("RGBA").resize((W, H), Image.LANCZOS)
    title_phone = Image.open(overlays / "title-phone.png").convert("RGBA").resize((PW, PW), Image.LANCZOS)

    # stills first (cheap)
    save_still(OUT / "hero-still.webp", over(desk(last), title), 400_000)
    save_still(OUT / "hero-phone-still.webp", over(square(last), title_phone), 250_000)

    # the day print: the gate as an ink-wash print on aged paper
    gate = desk(last)
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

    imgs, durs = timeline(desk, title)
    save_anim(OUT / "hero.webp", imgs, durs, quality, 6_000_000)
    imgs, durs = timeline(square, title_phone)
    save_anim(OUT / "hero-phone.webp", imgs, durs, phone_quality, 3_000_000)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Mountain Gate hero.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("titles", help="write the title overlay SVGs")
    enc = sub.add_parser("encode", help="encode the five hero WebPs from captured frames")
    enc.add_argument("--frames", required=True, type=Path)
    enc.add_argument("--overlays", required=True, type=Path, help="title.png, title-light.png, title-phone.png")
    enc.add_argument("--paper", default=Path("../PortfolioV5/client/src/app/sect/assets/paper.webp"), type=Path)
    enc.add_argument("--quality", type=int, default=76)
    enc.add_argument("--phone-quality", type=int, default=68)
    args = parser.parse_args()
    if args.cmd == "titles":
        write_titles()
    else:
        encode(args.frames, args.overlays, args.paper, args.quality, args.phone_quality)


if __name__ == "__main__":
    sys.exit(main())
