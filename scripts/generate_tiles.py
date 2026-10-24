"""Write the static formation assets: every board tile (dark and light), the
勿敲 gong and the 重布 re-lay key. They never change between runs, so CI does
not call this; re-run it by hand after touching art_formation.py or ink.py.
(`python scripts/artemis_ops.py tiles` does the same thing.)

Run from the repo root: python scripts/generate_tiles.py
"""

from __future__ import annotations

from pathlib import Path

import art_formation
import ink


def main() -> None:
    files = art_formation.static_assets()  # all in memory first: a missing glyph writes nothing
    changed = sum(ink.write_svg(Path(path), svg) for path, svg in files.items())
    print(f"formation: {changed} of {len(files)} static file(s) changed")


if __name__ == "__main__":
    main()
