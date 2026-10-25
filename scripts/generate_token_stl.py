"""Cut 黑木令, the Black Wood Token, as an ASCII STL (assets/relics/heimuling.stl).

In The Smiling, Proud Wanderer the Black Wood Token is the command token of
日月神教: whoever holds it speaks for the Sect Leader. This one is a chamfered
tablet with a raised frame, and on its face the sect's carved seal: a square
stone with the crescent cut down through it to the wood and the sun standing
on it as a boss. The seal's numbers come from ink.py (LOGO_GRID, LOGO_MASTER,
the same geometry as the site's lib/sect/logo.ts), so when the logo changes,
re-run this script. GitHub draws an ```stl fence as a 3D viewer; the README's
back shelf holds a copy of this file in one, so a visitor can turn the token
with the mouse. `--readme` pastes the new file into that fence; without it the
script warns when the fence and the file differ.

Stdlib only. Every shell is closed and every facet's normal points out of its
solid (check() proves it on the written text); under 200 facets, every line
at most 72 characters. Run from the repo root:
    python scripts/generate_token_stl.py [--readme]
"""

from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path

import ink

OUT = Path("assets/relics/heimuling.stl")
README = Path("README.md")
FENCE = re.compile(r"(```stl\n)(.*?)(```)", re.S)
MAX_FACETS = 200

Vec = tuple[float, float, float]
Tri = tuple[Vec, Vec, Vec]
P = tuple[float, float]

W, H, T = 40.0, 60.0, 6.0      # the tablet, mm
CHAMFER = 7.0
FRAME_OUT, FRAME_IN, FRAME_H = 2.2, 4.4, 1.0

# The carved seal on the face: a square of 41 modules (ink.LOGO_GRID), lifted a
# little above the middle. The stone stands SEAL_H off the wood; the crescent
# is cut down through it to the wood; the sun stands SUN_H on the stone.
SEAL = 26.0
SEAL_AT = (0.0, 2.0)
SEAL_H, SUN_H = 1.6, 0.8
# Facets are scarce (the fence wants fewer than 200): 9 straight runs on the
# moon's rim and 6 on the bite's give runs of about 8 modules each; the sun is
# an octagon.
MOON_RUNS, BITE_RUNS, SUN_RUNS = 9, 6, 8


def area(poly: list[P]) -> float:
    return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1])) / 2


def ccw(poly: list[P]) -> list[P]:
    return poly if area(poly) > 0 else poly[::-1]


def octagon(inset: float) -> list[P]:
    """The tablet's outline, inset by `inset`: a rectangle with chamfered corners."""
    hw, hh, c = W / 2 - inset, H / 2 - inset, CHAMFER - inset * 0.41
    return [(-hw + c, -hh), (hw - c, -hh), (hw, -hh + c), (hw, hh - c),
            (hw - c, hh), (-hw + c, hh), (-hw, hh - c), (-hw, -hh + c)]


def sides(poly: list[P], z0: float, z1: float) -> list[Tri]:
    """Walls of a CCW loop (outward normals); pass a CW loop for a hole's walls."""
    out = []
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        a, b, c, d = (x0, y0, z0), (x1, y1, z0), (x1, y1, z1), (x0, y0, z1)
        out += [(a, b, c), (a, c, d)]
    return out


def cross(p: P, q: P, r: P) -> float:
    return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])


def caps(tris2d: list[tuple], z0: float, z1: float) -> list[Tri]:
    """Top (CCW, +z) and bottom (reversed, -z) faces from 2D triangles."""
    out = []
    for p, q, r in tris2d:
        c = cross(p, q, r)
        if abs(c) < 1e-9:
            raise ValueError(f"flat triangle {p} {q} {r}")
        if c < 0:
            q, r = r, q
        out.append(((*p, z1), (*q, z1), (*r, z1)))
        out.append(((*p, z0), (*r, z0), (*q, z0)))
    return out


def fan(poly: list[P]) -> list[tuple]:
    return [(poly[0], poly[i], poly[i + 1]) for i in range(1, len(poly) - 1)]


def prism(poly: list[P], z0: float, z1: float) -> list[Tri]:
    poly = ccw(poly)
    return caps(fan(poly), z0, z1) + sides(poly, z0, z1)


def ring(outer: list[P], inner: list[P], z0: float, z1: float) -> list[Tri]:
    """A raised frame: the band between two loops with the same vertex count."""
    outer, inner = ccw(outer), ccw(inner)
    n = len(outer)
    band = []
    for i in range(n):
        j = (i + 1) % n
        band += [(outer[i], outer[j], inner[j]), (outer[i], inner[j], inner[i])]
    return caps(band, z0, z1) + sides(outer, z0, z1) + sides(inner[::-1], z0, z1)


# --- a face with a hole: a bridge, then ear clipping ------------------------------------


def inside_tri(s: P, p: P, q: P, r: P) -> bool:
    """s inside or on the CCW triangle pqr."""
    e = -1e-9
    return cross(p, q, s) >= e and cross(q, r, s) >= e and cross(r, p, s) >= e


def inside_poly(s: P, poly: list[P]) -> bool:
    hit = False
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        if (y0 > s[1]) != (y1 > s[1]) and s[0] < x0 + (s[1] - y0) * (x1 - x0) / (y1 - y0):
            hit = not hit
    return hit


def crosses(a: P, b: P, p: P, q: P) -> bool:
    """Segments ab and pq cross or touch."""
    d1, d2, d3, d4 = cross(p, q, a), cross(p, q, b), cross(a, b, p), cross(a, b, q)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)):
        return True
    return any(abs(d) < 1e-12 for d in (d1, d2, d3, d4))


def ears(loop: list[P]) -> list[tuple[P, P, P]]:
    """Cut a CCW loop (it may run along a bridge twice) into triangles, ear by ear."""
    idx = list(range(len(loop)))
    tris = []
    while len(idx) > 3:
        for k in range(len(idx)):
            p, q, r = loop[idx[k - 1]], loop[idx[k]], loop[idx[(k + 1) % len(idx)]]
            if cross(p, q, r) <= 1e-9:
                continue                            # a reflex or flat corner is no ear
            if any(inside_tri(loop[j], p, q, r) for j in idx if loop[j] not in (p, q, r)):
                continue
            tris.append((p, q, r))
            idx.pop(k)
            break
        else:
            raise ValueError("no ear left to cut")
    tris.append(tuple(loop[i] for i in idx))
    return tris


def with_hole(outer: list[P], hole: list[P]) -> list[tuple[P, P, P]]:
    """Triangles covering `outer` minus `hole`: the hole joins the outer loop by
    the shortest bridge that crosses no edge and stays out of the hole."""
    outer, hole = ccw(outer), ccw(hole)[::-1]
    edges = list(zip(outer, outer[1:] + outer[:1])) + list(zip(hole, hole[1:] + hole[:1]))
    pairs = sorted(((i, j) for i in range(len(outer)) for j in range(len(hole))),
                   key=lambda ij: math.dist(outer[ij[0]], hole[ij[1]]))
    for i, j in pairs:
        a, b = outer[i], hole[j]
        if any(crosses(a, b, p, q) for p, q in edges if a not in (p, q) and b not in (p, q)):
            continue
        near_b = (b[0] + (a[0] - b[0]) * 1e-3, b[1] + (a[1] - b[1]) * 1e-3)
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        if inside_poly(near_b, hole) or inside_poly(mid, hole):
            continue
        break
    else:
        raise ValueError("no bridge from the hole to the edge")
    return ears(outer[:i + 1] + hole[j:] + hole[:j + 1] + outer[i:])


# --- the carved seal ----------------------------------------------------------------------


def seal_plan() -> tuple[list[P], list[P], list[P]]:
    """The seal's square, the crescent's loop and the sun, in mm on the token's
    face (y up), from the logo's circles in modules (y down)."""
    g = ink.logo_circles(ink.LOGO_GRID)
    u, half = SEAL / ink.LOGO_GRID, ink.LOGO_GRID / 2

    def face(x: float, y: float) -> P:
        return SEAL_AT[0] + (x - half) * u, SEAL_AT[1] - (y - half) * u

    (mx, my, r), (bx, by, rb), (sx, sy, sr) = g["moon"], g["bite"], g["sun"]
    d = math.hypot(bx - mx, by - my)
    ax, ay = (bx - mx) / d, (by - my) / d          # the mouth's axis

    def turn(cx: float, cy: float, rad: float, s: float) -> P:
        """The point at angle s from the axis on the circle at (cx, cy)."""
        ux, uy = ax * math.cos(s) - ay * math.sin(s), ax * math.sin(s) + ay * math.cos(s)
        return face(cx + ux * rad, cy + uy * rad)

    horn = math.acos((r * r - rb * rb + d * d) / (2 * d * r))
    # the moon's rim from one horn round the belly to the other, then the bite's
    # rim back through the belly side (the long way round, as in ink.crescent_path)
    rim = [turn(mx, my, r, horn + (2 * math.pi - 2 * horn) * i / MOON_RUNS) for i in range(MOON_RUNS + 1)]
    tip = math.atan2(r * math.sin(horn), r * math.cos(horn) - d)
    bite = [turn(bx, by, rb, -tip - (2 * math.pi - 2 * tip) * j / BITE_RUNS) for j in range(1, BITE_RUNS)]
    crescent = rim + bite
    square = [face(0, ink.LOGO_GRID), face(ink.LOGO_GRID, ink.LOGO_GRID), face(ink.LOGO_GRID, 0), face(0, 0)]
    sun = [turn(sx, sy, sr, 2 * math.pi * k / SUN_RUNS) for k in range(SUN_RUNS)]
    return square, crescent, sun


def token() -> list[Tri]:
    tris = prism(octagon(0), 0, T)
    tris += ring(octagon(FRAME_OUT), octagon(FRAME_IN), T, T + FRAME_H)
    square, crescent, sun = seal_plan()
    top = T + SEAL_H
    tris += caps(with_hole(square, crescent), T, top) + sides(ccw(square), T, top) + sides(ccw(crescent)[::-1], T, top)
    tris += prism(sun, top, top + SUN_H)
    return tris


# --- the file -------------------------------------------------------------------------------


def normal(t: Tri) -> Vec:
    (ax, ay, az), (bx, by, bz), (cx, cy, cz) = t
    ux, uy, uz = bx - ax, by - ay, bz - az
    vx, vy, vz = cx - ax, cy - ay, cz - az
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    m = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return nx / m, ny / m, nz / m


def num(v: float) -> str:
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def stl(tris: list[Tri]) -> str:
    lines = ["solid heimuling"]
    for t in tris:
        lines.append("facet normal " + " ".join(num(c) for c in normal(t)))
        lines.append("  outer loop")
        lines += ["    vertex " + " ".join(num(c) for c in v) for v in t]
        lines.append("  endloop")
        lines.append("endfacet")
    lines.append("endsolid heimuling")
    return "\n".join(lines) + "\n"


def parse(text: str) -> list[Tri]:
    """The facets as written (rounded to the file's 3 decimals)."""
    vs = [tuple(float(c) for c in line.split()[1:]) for line in text.splitlines() if line.strip().startswith("vertex")]
    return [tuple(vs[i:i + 3]) for i in range(0, len(vs), 3)]


def check(tris: list[Tri]) -> list[str]:
    """Prove the token is closed: every edge is shared by exactly two facets that
    run it in opposite directions, no facet is flat, and every shell (a connected
    set of facets) encloses a positive volume, so all normals point out."""
    assert len(tris) < MAX_FACETS, f"{len(tris)} facets; the README fence wants fewer than {MAX_FACETS}"
    edges: dict[tuple[Vec, Vec], int] = {}
    for n, t in enumerate(tris):
        assert len(set(t)) == 3 and math.hypot(*_cross3(t)) > 1e-9, f"facet {n} is flat"
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            assert (a, b) not in edges, f"edge {a} {b} is used twice in one direction"
            edges[(a, b)] = n
    open_edges = [e for e in edges if (e[1], e[0]) not in edges]
    assert not open_edges, f"{len(open_edges)} open edge(s), first {open_edges[0]}"
    # shells: facets joined by shared edges
    parent = list(range(len(tris)))

    def root(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for (a, b), n in edges.items():
        parent[root(n)] = root(edges[(b, a)])
    shells: dict[int, list[int]] = {}
    for n in range(len(tris)):
        shells.setdefault(root(n), []).append(n)
    report = []
    for members in sorted(shells.values(), key=len, reverse=True):
        vol = sum(_det(tris[n]) for n in members) / 6
        assert vol > 0, f"a shell of {len(members)} facets has volume {vol:.3f} (normals point in)"
        verts = {v for n in members for v in tris[n]}
        e = len({frozenset(e) for n in members for e in ((tris[n][0], tris[n][1]), (tris[n][1], tris[n][2]),
                                                         (tris[n][2], tris[n][0]))})
        genus = (2 - (len(verts) - e + len(members))) // 2
        report.append(f"{len(members)} facets, {vol:.1f} mm3, {genus} hole(s)")
    return report


def _cross3(t: Tri) -> Vec:
    (ax, ay, az), (bx, by, bz), (cx, cy, cz) = t
    ux, uy, uz = bx - ax, by - ay, bz - az
    vx, vy, vz = cx - ax, cy - ay, cz - az
    return uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx


def _det(t: Tri) -> float:
    (ax, ay, az), (bx, by, bz), (cx, cy, cz) = t
    return ax * (by * cz - bz * cy) - ay * (bx * cz - bz * cx) + az * (bx * cy - by * cx)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--readme", action="store_true", help="paste the file into README.md's ```stl fence")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    tris = token()
    check(tris)
    text = stl(tris)
    shells = check(parse(text))                    # the file as written, rounding and all
    assert max(len(line) for line in text.splitlines()) <= 72
    OUT.parent.mkdir(parents=True, exist_ok=True)
    old = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
    if old != text:
        OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"{OUT.as_posix()}: {len(tris)} facets, {len(text.splitlines())} lines"
          f"{'' if old != text else ' (unchanged)'}; closed shells: " + "; ".join(shells))
    readme = README.read_text(encoding="utf-8") if README.exists() else ""
    fences = FENCE.findall(readme)
    if len(fences) != 1:
        print(f"warning: README.md has {len(fences)} ```stl fences, expected 1; left alone")
    elif fences[0][1] != text:
        if args.readme:
            README.write_text(FENCE.sub(lambda m: m.group(1) + text + m.group(3), readme, count=1),
                              encoding="utf-8", newline="\n")
            print("README.md: pasted the token into the ```stl fence")
        else:
            print("warning: README.md's ```stl fence is not this file; run with --readme to paste it")


if __name__ == "__main__":
    main()
