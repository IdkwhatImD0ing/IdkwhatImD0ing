"""Make the Shipped journal's prints: each winning build's object from my site's forge, printed on paper.

On art3m1s.me every winning project floats around the forge's cauldron as an
object (lib/sect/artifacts.ts): DispatchAI is a command flag (令旗),
TalkTuahBank a treasure bowl (聚宝盆), AdaptEd bamboo slips (竹简), SlugLoop a
wind fire wheel (风火轮). The journal shows those real objects, captured from the
live site and printed in ink with a light colour wash, like the woodblock
plates in Black Myth: Wukong's journal. Local only: needs Pillow and numpy. CI
never runs this; scripts/art_journal.py embeds the JPEGs it writes.

  python scripts/generate_prints.py cut --cap <folder of captures>
      crop each object from its capture into scripts/data/journal/cap-<slug>.jpg
      (the capture file and box per object are in prints.json)
  python scripts/generate_prints.py photo --site ../PortfolioV5/client
      the site's project poster for a tipped-in photo: photo-<slug>.jpg
  python scripts/generate_prints.py
      cap-<slug>.jpg -> print-<slug>-spread.jpg and print-<slug>-leaf.jpg

How a print is made from a capture: the forge ring's glowing orbit line runs
through every object (they ride on it), so its cyan pixels are found and filled
in from the pixels just above and below them (the line runs across). Then the
object is kept at full strength, the courtyard behind it fades toward paper,
edges get an ink line, and the edge of the print bleeds into the paper.

Captures (re-take them after a new scene bake): open
https://art3m1s.me/?frame=352&ui=0&tier=high at 2560x1600 and device scale 1.5,
wait for body[data-sect-ready], and screenshot every 1.5 s while the ring turns
(scripts/capture_forge.cjs does exactly that). Pick one frame per object where
it faces the camera, set its file and box in prints.json, then run `cut` and
this script. Never run Blender for this.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

DATA = Path("scripts/data/journal")
SPEC = DATA / "prints.json"

# The print frames, in CSS px (the files are drawn at 2x). art_journal.py reads
# the same numbers from prints.json, so the two never disagree.
SCALE = 2
PAPER = np.array([0.925, 0.878, 0.776], np.float32)     # the print's paper, a touch lighter than the map scroll
INK = np.array([0.15, 0.12, 0.10], np.float32)


def load_spec() -> dict:
    return json.loads(SPEC.read_text(encoding="utf-8"))


# --- 1. the orbit line -----------------------------------------------------------------


def dilate(mask: np.ndarray, size: int) -> np.ndarray:
    if size <= 1:
        return mask
    img = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(size | 1))
    return np.asarray(img) > 127


def circles(shape: tuple[int, int], items: list) -> np.ndarray:
    h, w = shape
    img = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(img)
    for x, y, r in items:
        draw.ellipse((x - r, y - r, x + r, y + r), fill=255)
    return np.asarray(img) > 127


def orbit_mask(a: np.ndarray, keep: list, grow: int) -> np.ndarray:
    """The ring's glowing line: bright cyan, its white core and its halo."""
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    cyan = (g - r > 0.10) & (b - r > 0.06) & (g > 0.42)
    core = (r > 0.88) & (g > 0.94) & (b > 0.92) & dilate(cyan, 7)
    m = cyan | core
    if keep:
        m &= ~circles(m.shape, keep)
    return dilate(m, grow)


def fill_across(a: np.ndarray, m: np.ndarray, max_run: int = 120) -> np.ndarray:
    """Fill each masked run in a column from the pixels just above and below it
    (the orbit line runs across the picture, so this keeps upright things such
    as a flag pole whole). Very long runs fall back to a soft average."""
    out = a.copy()
    h, w = m.shape
    long_runs = np.zeros_like(m)
    for x in range(w):
        col = m[:, x]
        if not col.any():
            continue
        edges = np.flatnonzero(np.diff(np.concatenate(([0], col.astype(np.int8), [0]))))
        for s, e in zip(edges[::2], edges[1::2]):
            if e - s > max_run or (s == 0 and e == h):
                long_runs[s:e, x] = True
                continue
            top = out[max(0, s - 3):s, x].mean(axis=0) if s > 0 else None
            bot = out[e:min(h, e + 3), x].mean(axis=0) if e < h else None
            top = bot if top is None else top
            bot = top if bot is None else bot
            t = ((np.arange(s, e) - (s - 1)) / (e - s + 1))[:, None]
            out[s:e, x] = top * (1 - t) + bot * t
    # soften the filled band so it reads as paper grain, not as stripes
    soft = np.asarray(Image.fromarray((out * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.4))) / 255.0
    band = dilate(m, 3)[..., None]
    out = np.where(band, soft, out)
    if long_runs.any():
        blur = np.asarray(Image.fromarray((out * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(12))) / 255.0
        out = np.where(long_runs[..., None], blur, out)
    return out.astype(np.float32)


# --- 2. the print -------------------------------------------------------------------------


def noise(shape: tuple[int, int], cells: int, amp: float, rng: np.random.Generator) -> np.ndarray:
    h, w = shape
    z = rng.normal(0, 1, (max(2, cells), max(2, cells))).astype(np.float32)
    img = Image.fromarray(((z * amp + 0.5).clip(0, 1) * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
    return np.asarray(img).astype(np.float32) / 255.0 - 0.5


def paper(shape: tuple[int, int], rng: np.random.Generator) -> np.ndarray:
    """Aged paper: the base colour, slow blotches, fine fibre and a darker edge."""
    h, w = shape
    fib = 1.0 - 0.05 * noise(shape, max(h, w) // 3, 0.5, rng) - 0.035 * noise(shape, 7, 0.6, rng)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h * 0.46) / (h / 2)) ** 2)
    edge = 1.0 - 0.10 * np.clip((d - 0.72) / 0.6, 0, 1) ** 1.5
    return PAPER[None, None, :] * (fib * edge)[..., None]


def object_mask(shape: tuple[int, int], spec: dict) -> Image.Image:
    h, w = shape
    img = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(img)
    for poly in spec.get("poly", []):
        draw.polygon([tuple(p) for p in poly], fill=255)
    for x, y, rx, ry in spec.get("ell", []):
        draw.ellipse((x - rx, y - ry, x + rx, y + ry), fill=255)
    for x0, y0, x1, y1, width in spec.get("stroke", []):
        draw.line((x0, y0, x1, y1), fill=255, width=int(width))
    return img


def place(src: Image.Image, frame: tuple[int, int], at: dict, resample=Image.LANCZOS, fill=0) -> Image.Image:
    """Scale the crop and set it in the frame: `at` gives the crop point that
    lands on the frame's (cx, cy) fraction and the scale (frame px per crop px)."""
    fw, fh = frame
    k = at["scale"]
    sw, sh = max(1, round(src.width * k)), max(1, round(src.height * k))
    scaled = src.resize((sw, sh), resample)
    out = Image.new(src.mode, (fw, fh), fill)
    ox = round(at["cx"] * fw - at["x"] * k)
    oy = round(at["cy"] * fh - at["y"] * k)
    out.paste(scaled, (ox, oy))
    return out


def make_print(cap: Image.Image, spec: dict, kind: str, frame_css: tuple[int, int]) -> Image.Image:
    frame = (frame_css[0] * SCALE, frame_css[1] * SCALE)
    rng = np.random.default_rng(spec.get("seed", 7))
    a = np.asarray(cap.convert("RGB")).astype(np.float32) / 255.0
    line = orbit_mask(a, spec.get("keep", []), spec.get("grow", 9))
    a = fill_across(a, line)
    filled = Image.fromarray((a * 255).astype(np.uint8))
    om = object_mask(a.shape[:2], spec).filter(ImageFilter.GaussianBlur(spec.get("feather", 10)))
    inside = Image.new("L", cap.size, 255)

    at = dict(spec["place"][kind])
    at["scale"] *= SCALE
    img = np.asarray(place(filled, frame, at, fill=(236, 224, 198))).astype(np.float32) / 255.0
    obj = np.asarray(place(om, frame, at, Image.BILINEAR)).astype(np.float32) / 255.0
    valid = np.asarray(place(inside, frame, at, Image.BILINEAR)).astype(np.float32) / 255.0

    shape = img.shape[:2]
    L = 0.299 * img[..., 0] + 0.587 * img[..., 1] + 0.114 * img[..., 2]
    Lb = np.asarray(Image.fromarray((L * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2 * SCALE / 2)))
    Lb = Lb.astype(np.float32) / 255.0
    gx = np.zeros_like(Lb)
    gy = np.zeros_like(Lb)
    gx[:, 1:-1] = Lb[:, 2:] - Lb[:, :-2]
    gy[1:-1, :] = Lb[2:, :] - Lb[:-2, :]
    edge = np.clip((np.sqrt(gx * gx + gy * gy) - 0.03) / 0.15, 0, 1) ** 0.8

    bg = spec.get("bg", 0.18)
    weight = bg + (1 - bg) * obj
    grey = L[..., None]
    col = grey + (img - grey) * spec.get("tint", 0.62)        # the colour wash: muted, never neon
    col = np.clip(0.16 + col * 0.92, 0, 1)
    col = 1 - (1 - col) * weight[..., None]                   # the courtyard fades toward paper
    P = paper(shape, rng)
    O = P * col
    dens = np.clip(edge * 0.85, 0, 1) * weight
    O = O * (1 - dens[..., None]) + INK[None, None, :] * dens[..., None]

    # the bled edge: the object's shape grown and roughened, so the print fades into paper.
    # `halo` widens thin parts first (a flag pole would otherwise fade out with the blur).
    halo = round(spec.get("halo", 0) * at["scale"])
    shape_img = Image.fromarray((obj * 255).astype(np.uint8))
    if halo > 1:
        shape_img = shape_img.filter(ImageFilter.MaxFilter(halo | 1))
    grown = shape_img.filter(ImageFilter.GaussianBlur(spec.get("bleed", 46) * SCALE / 2))
    big = np.asarray(grown).astype(np.float32) / 255.0
    rough = big + 0.20 * noise(shape, 9, 0.35, rng) + 0.07 * noise(shape, 48, 0.4, rng)
    alpha = np.clip((rough - 0.16) / 0.16, 0, 1)
    alpha = alpha * alpha * (3 - 2 * alpha) * valid
    out = P * (1 - alpha[..., None]) + O * alpha[..., None]
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8), "RGB")


# --- commands -------------------------------------------------------------------------------


def cmd_cut(args: argparse.Namespace) -> None:
    spec = load_spec()
    cap_dir = Path(args.cap)
    for slug, item in spec["prints"].items():
        src = cap_dir / item["capture"]
        if not src.exists():
            raise SystemExit(f"{slug}: capture {src} not found")
        box = tuple(item["box"])
        Image.open(src).convert("RGB").crop(box).save(DATA / f"cap-{slug}.jpg", quality=92, optimize=True)
        print(f"cap-{slug}.jpg  from {item['capture']} box {box}")


def cmd_photo(args: argparse.Namespace) -> None:
    spec = load_spec()
    site = Path(args.site)
    for slug, item in spec.get("photos", {}).items():
        src = site / item["poster"]
        w, h = item["size"]
        img = Image.open(src).convert("RGB")
        k = max(w * SCALE / img.width, h * SCALE / img.height)
        img = img.resize((round(img.width * k), round(img.height * k)), Image.LANCZOS)
        left, top = (img.width - w * SCALE) // 2, (img.height - h * SCALE) // 2
        img.crop((left, top, left + w * SCALE, top + h * SCALE)).save(DATA / f"photo-{slug}.jpg", quality=88,
                                                                         optimize=True)
        print(f"photo-{slug}.jpg  from {item['poster']}")


def cmd_print(_args: argparse.Namespace) -> None:
    spec = load_spec()
    frames = {kind: tuple(size) for kind, size in spec["frames"].items()}
    for slug, item in spec["prints"].items():
        cap = Image.open(DATA / f"cap-{slug}.jpg")
        for kind in item["place"]:
            out = make_print(cap, item, kind, frames[kind])
            target = DATA / f"print-{slug}-{kind}.jpg"
            out.save(target, quality=86, optimize=True, progressive=True)
            print(f"{target.name}  {out.width}x{out.height}  {target.stat().st_size // 1024} KB")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd")
    cut = sub.add_parser("cut", help="crop the objects from fresh captures")
    cut.add_argument("--cap", required=True, help="folder holding the capture PNGs named in prints.json")
    photo = sub.add_parser("photo", help="the tipped-in photos, from the site's project posters")
    photo.add_argument("--site", required=True, help="PortfolioV5's client folder (read only)")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    {"cut": cmd_cut, "photo": cmd_photo}.get(args.cmd, cmd_print)(args)


if __name__ == "__main__":
    main()
