"""Cut 黑木令, the Black Wood Token, as an ASCII STL (assets/relics/heimuling.stl).

In The Smiling, Proud Wanderer the Black Wood Token is the command token of
日月神教: whoever holds it speaks for the Sect Leader. This one is a chamfered
tablet with a raised frame, and on its face the sect's emblem: a large
crescent moon cradling a small sun (the same geometry as the site's logo).
GitHub draws an ```stl fence as a 3D viewer; the README's back shelves paste
this file into one, so a visitor can turn the token with the mouse.

Stdlib only. Every facet's normal points out of its solid; under 200 facets,
every line at most 72 characters. Run from the repo root:
    python scripts/generate_token_stl.py
"""

from __future__ import annotations

import math
from pathlib import Path

OUT = Path("assets/relics/heimuling.stl")

Vec = tuple[float, float, float]
Tri = tuple[Vec, Vec, Vec]

W, H, T = 40.0, 60.0, 6.0      # the tablet, mm
CHAMFER = 7.0
FRAME_OUT, FRAME_IN, FRAME_H = 2.2, 4.4, 1.0
RELIEF_H = 2.2


def area(poly: list[tuple[float, float]]) -> float:
    return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1])) / 2


def ccw(poly: list[tuple[float, float]]) -> list[tuple[float, float]]:
    return poly if area(poly) > 0 else poly[::-1]


def octagon(inset: float) -> list[tuple[float, float]]:
    """The tablet's outline, inset by `inset`: a rectangle with chamfered corners."""
    hw, hh, c = W / 2 - inset, H / 2 - inset, CHAMFER - inset * 0.41
    return [(-hw + c, -hh), (hw - c, -hh), (hw, -hh + c), (hw, hh - c),
            (hw - c, hh), (-hw + c, hh), (-hw, hh - c), (-hw, -hh + c)]


def sides(poly: list[tuple[float, float]], z0: float, z1: float) -> list[Tri]:
    """Walls of a CCW loop (outward normals); pass a CW loop for a hole's walls."""
    out = []
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        a, b, c, d = (x0, y0, z0), (x1, y1, z0), (x1, y1, z1), (x0, y0, z1)
        out += [(a, b, c), (a, c, d)]
    return out


def caps(tris2d: list[tuple], z0: float, z1: float) -> list[Tri]:
    """Top (CCW, +z) and bottom (reversed, -z) faces from 2D triangles."""
    out = []
    for p, q, r in tris2d:
        if abs((q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])) < 1e-9:
            continue  # degenerate
        if (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]) < 0:
            q, r = r, q
        out.append(((*p, z1), (*q, z1), (*r, z1)))
        out.append(((*p, z0), (*r, z0), (*q, z0)))
    return out


def fan(poly: list[tuple[float, float]]) -> list[tuple]:
    return [(poly[0], poly[i], poly[i + 1]) for i in range(1, len(poly) - 1)]


def prism(poly: list[tuple[float, float]], z0: float, z1: float) -> list[Tri]:
    poly = ccw(poly)
    return caps(fan(poly), z0, z1) + sides(poly, z0, z1)


def ring(outer: list[tuple[float, float]], inner: list[tuple[float, float]], z0: float, z1: float) -> list[Tri]:
    """A raised frame: the band between two loops with the same vertex count."""
    outer, inner = ccw(outer), ccw(inner)
    n = len(outer)
    band = []
    for i in range(n):
        j = (i + 1) % n
        band += [(outer[i], outer[j], inner[j]), (outer[i], inner[j], inner[i])]
    return caps(band, z0, z1) + sides(outer, z0, z1) + sides(inner[::-1], z0, z1)


def arc(cx: float, cy: float, r: float, a0: float, a1: float, n: int) -> list[tuple[float, float]]:
    return [(cx + r * math.cos(a0 + (a1 - a0) * k / n), cy + r * math.sin(a0 + (a1 - a0) * k / n))
            for k in range(n + 1)]


def crescent(moon: tuple[float, float, float], bite: tuple[float, float, float], n: int,
             z0: float, z1: float) -> list[Tri]:
    """The moon disc with the bite taken out: a strip between the two arcs."""
    (x1, y1, r1), (x2, y2, r2) = moon, bite
    dx, dy = x2 - x1, y2 - y1
    d = math.hypot(dx, dy)
    a = (r1 * r1 - r2 * r2 + d * d) / (2 * d)
    h = math.sqrt(r1 * r1 - a * a)
    px, py = x1 + a * dx / d, y1 + a * dy / d
    pa = (px - h * dy / d, py + h * dx / d)
    pb = (px + h * dy / d, py - h * dx / d)
    ma = math.atan2(pa[1] - y1, pa[0] - x1)
    mb = math.atan2(pb[1] - y1, pb[0] - x1)
    ba = math.atan2(pa[1] - y2, pa[0] - x2)
    bb = math.atan2(pb[1] - y2, pb[0] - x2)
    # the moon's rim the long way round (away from the bite), the bite's rim the short way
    away = math.atan2(-dy, -dx)

    def sweep(s: float, e: float, through: float | None) -> tuple[float, float]:
        e1 = e if e > s else e + 2 * math.pi
        if through is None:
            return (s, e1) if e1 - s <= math.pi else (s, e1 - 2 * math.pi)
        t = through if through > s else through + 2 * math.pi
        return (s, e1) if t < e1 else (s, e1 - 2 * math.pi)

    m0, m1 = sweep(ma, mb, away)
    b0, b1 = sweep(ba, bb, None)
    outer = arc(x1, y1, r1, m0, m1, n)
    inner = arc(x2, y2, r2, b0, b1, n)
    outer[0], outer[-1], inner[0], inner[-1] = pa, pb, pa, pb
    strip = []
    for i in range(n):
        strip += [(outer[i], outer[i + 1], inner[i + 1]), (outer[i], inner[i + 1], inner[i])]
    loop = outer + inner[-2:0:-1]
    return caps(strip, z0, z1) + sides(ccw(loop), z0, z1)


def token() -> list[Tri]:
    tris = prism(octagon(0), 0, T)
    tris += ring(octagon(FRAME_OUT), octagon(FRAME_IN), T, T + FRAME_H)
    # the emblem, from the logo's 64-unit box (y down) to the token's face (y up)
    k, ox, oy = 0.74, -1.5, 3.0

    def place(c: tuple[float, float, float]) -> tuple[float, float, float]:
        return (ox + (c[0] - 32) * k, oy - (c[1] - 32) * k, c[2] * k)

    moon, bite, sun = place((29.6, 34.4, 16.6)), place((36.6, 27.4, 13.6)), place((39.4, 24.6, 5.0))
    tris += crescent(moon, bite, 9, T, T + RELIEF_H)
    tris += prism(arc(sun[0], sun[1], sun[2], 0, 2 * math.pi, 8)[:-1], T, T + RELIEF_H + 0.6)
    return tris


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


def check(tris: list[Tri]) -> None:
    assert len(tris) < 200, f"{len(tris)} facets; the README fence wants fewer than 200"
    edges: dict[tuple, int] = {}
    for t in tris:
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            key = (a, b)
            edges[key] = edges.get(key, 0) + 1
    # every directed edge is matched by its reverse in a closed, consistently wound solid
    open_edges = [e for e in edges if (e[1], e[0]) not in edges]
    assert not open_edges, f"{len(open_edges)} open edge(s)"


def main() -> None:
    tris = token()
    check(tris)
    text = stl(tris)
    assert max(len(line) for line in text.splitlines()) <= 72
    OUT.parent.mkdir(parents=True, exist_ok=True)
    old = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
    if old != text:
        OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"{OUT.as_posix()}: {len(tris)} facets, {len(text.splitlines())} lines"
          f"{'' if old != text else ' (unchanged)'}")


if __name__ == "__main__":
    main()
