"""Cut the sect's type into glyph tables: scripts/ink_glyphs/<face>.json.

Every word inside the profile's SVGs is drawn as glyph outlines, never as
<text>, so GitHub shows the same letters on every OS and Chinese never falls
back to empty boxes. This script reads the five OFL fonts once (local only,
needs fontTools) and writes, per face, the outline of every character the
renderers can ask for. The CI renderers stay stdlib-only: they read the
tables through scripts/ink.py.

Faces (all SIL Open Font License 1.1, from github.com/google/fonts):
  brush     Ma Shan Zheng            Chinese display, 16 px and up
  serif     Noto Serif SC, wght 500  small Chinese labels
  display   Instrument Serif         "Bill Zhang", place names
  body      Geist, wght 400          sentences and labels
  medium    Geist, wght 500          emphasis
  mono      Geist Mono, wght 400     numbers, dates, missions

Which characters: printable ASCII, a few marks, and every Chinese character
that appears in any scripts/*.py file (the copy deck lives in the renderers,
so a new Chinese label only needs a re-run of this script).

The fonts are downloaded files: keep them in their own folder and run this
isolated, with fontTools found through an explicit path, e.g.

    python -I scripts/generate_glyphs.py --fonts <font dir> \\
        --site-packages <dir that holds fontTools> --repo .
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

FACES = {
    # name: (file name in --fonts, variable-font location, character set)
    "brush": ("mashanzheng__MaShanZheng-Regular.ttf", None, "cjk"),
    "serif": ("notoserifsc__NotoSerifSC[wght].ttf", {"wght": 500}, "cjk+marks"),
    "display": ("instrumentserif__InstrumentSerif-Regular.ttf", None, "latin"),
    "body": ("geist__Geist[wght].ttf", {"wght": 400}, "latin"),
    "medium": ("geist__Geist[wght].ttf", {"wght": 500}, "latin"),
    "mono": ("geistmono__GeistMono[wght].ttf", {"wght": 400}, "latin"),
}
LICENCES = {
    "mashanzheng__OFL.txt": "OFL-MaShanZheng.txt",
    "notoserifsc__OFL.txt": "OFL-NotoSerifSC.txt",
    "instrumentserif__OFL.txt": "OFL-InstrumentSerif.txt",
    "geist__OFL.txt": "OFL-Geist.txt",
    "geistmono__OFL.txt": "OFL-GeistMono.txt",
}

ASCII = "".join(chr(c) for c in range(0x20, 0x7F))
MARKS = "·éÉ▸▾–’‘“”…×°"
CJK_RE = re.compile(r"[　-〿㐀-䶿一-鿿＀-￯]")
CJK_PUNCT = "，。、：；！？「」《》（）"
# Chinese the renderers may need that is not (yet) a literal in a script.
EXTRA_CJK = "日月神教山门心镜台炼器峰论剑任务殿藏经阁碑林玉简护宗大阵洞府望月"


def cjk_chars(repo: Path) -> str:
    found = set(EXTRA_CJK)
    for path in sorted((repo / "scripts").glob("*.py")):
        found.update(CJK_RE.findall(path.read_text(encoding="utf-8", errors="replace")))
    # Only ideographs and real punctuation: a regex range like [　-〿]
    # written with literal characters must not smuggle its endpoints in.
    keep = {ch for ch in found
            if (unicodedata.category(ch) == "Lo" and "一" <= ch < "鿰") or ch in CJK_PUNCT}
    return "".join(sorted(keep))


def charset(kind: str, cjk: str) -> str:
    if kind == "cjk":
        return cjk
    if kind == "cjk+marks":
        return cjk + "·"
    return ASCII + MARKS


def synth_marks(table: dict, mono: bool) -> list[str]:
    """Geist has no small triangles; draw them on the x-height so help lines
    and fold marks can use them in every Latin face."""
    upm = table["upm"]
    adv = round(upm * 0.6) if mono else round(upm * 0.62)
    x0, x1 = round(adv * 0.22), round(adv * 0.78)
    made = []
    shapes = {
        "▸": f"M{x0} 80L{x1} 280L{x0} 480Z",
        "▾": f"M{x0} 400L{x1} 400L{(x0 + x1) // 2} 120Z",
    }
    boxes = {"▸": [x0, 80, x1, 480], "▾": [x0, 120, x1, 400]}
    for ch, d in shapes.items():
        if ch not in table["glyphs"]:
            table["glyphs"][ch] = [adv, d, boxes[ch]]
            made.append(ch)
    return made


def cut_face(path: Path, location: dict | None, chars: str) -> tuple[dict, list[str]]:
    from fontTools.pens.boundsPen import BoundsPen
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.ttLib import TTFont

    font = TTFont(str(path), lazy=False)
    cmap = font.getBestCmap()
    glyph_set = font.getGlyphSet(location=location) if location else font.getGlyphSet()
    hhea = font["hhea"]
    table = {
        "upm": font["head"].unitsPerEm,
        "asc": hhea.ascent,
        "desc": hhea.descent,
        "glyphs": {},
    }
    missing = []
    for ch in chars:
        name = cmap.get(ord(ch))
        if name is None:
            missing.append(ch)
            continue
        glyph = glyph_set[name]
        pen = SVGPathPen(glyph_set, ntos=lambda v: str(round(v)))
        glyph.draw(pen)
        bounds = BoundsPen(glyph_set)
        glyph.draw(bounds)
        box = [round(v) for v in bounds.bounds] if bounds.bounds else [0, 0, 0, 0]
        table["glyphs"][ch] = [round(glyph.width), pen.getCommands(), box]
    return table, missing


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--fonts", required=True, help="folder holding the downloaded TTFs")
    parser.add_argument("--site-packages", default="", help="where fontTools lives (python -I hides the user site)")
    parser.add_argument("--repo", default=".", help="profile repo root")
    args = parser.parse_args()
    if args.site_packages:
        sys.path.append(args.site_packages)

    repo = Path(args.repo).resolve()
    fonts = Path(args.fonts).resolve()
    out = repo / "scripts" / "ink_glyphs"
    out.mkdir(parents=True, exist_ok=True)
    cjk = cjk_chars(repo)
    print(f"chinese characters in the copy deck: {len(cjk)}")
    for face, (file_name, location, kind) in FACES.items():
        table, missing = cut_face(fonts / file_name, location, charset(kind, cjk))
        if kind == "latin":
            made = synth_marks(table, mono=face == "mono")
            missing = [ch for ch in missing if ch not in made]
        table["face"] = face
        table["source"] = file_name.split("__", 1)[1] + (f" at {location}" if location else "")
        text = json.dumps(table, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        target = out / f"{face}.json"
        target.write_text(text + "\n", encoding="utf-8", newline="\n")
        note = f", not in the font: {ascii(''.join(missing))}" if missing else ""
        print(f"{target.relative_to(repo).as_posix()}: {len(table['glyphs'])} glyphs, "
              f"{len(text) // 1024} KB{note}")
    for source, name in LICENCES.items():
        src = fonts / source
        if src.exists():
            (out / name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
