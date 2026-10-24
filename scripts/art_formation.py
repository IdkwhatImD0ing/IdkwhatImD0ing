"""The art of 护宗大阵, the Grand Sect-Protecting Formation (the 破阵 game).

Pure drawing: no README, no state files, no network. scripts/artemis_ops.py
decides where the traps are and builds the `view`; this module only draws.

The board is a formation lattice of 81 nodes, assembled in the README from
static tiles (assets/formation/tiles/{dark,light}/<name>.svg). Every tile
paints its whole box in the slab colour and carries its piece of the lattice,
so abutting tiles fuse into one array. Each node is a stone at a crossing:
  hidden   a raised stone with a jade rune (you can act here)
  c0       a spent node, nothing near
  c1..c8   the number of killing traps touching the node
  mine     杀 (kill): a killing trap, dormant (dead boards only)
  panic    the trap that struck back (反噬, backlash)
The status panel beside the board (panel-<seq>.svg) is redrawn every move.

The board is 268 px wide on purpose (see artemis_ops.py): rows are runs of
inline images, and a row wider than the column wraps and shreds the grid.
"""

from __future__ import annotations

import re

import ink

TILE, RAIL_L, RAIL_R, RAIL_TOP, RAIL_BOTTOM = 28, 10, 6, 34, 6
COLS = "ABCDEFGHI"
ROWS = "123456789"
BOARD_W = RAIL_L + len(COLS) * TILE + RAIL_R    # 268
BOARD_H = RAIL_TOP + len(ROWS) * TILE + RAIL_BOTTOM  # 292
PANEL_W, PANEL_H = 500, BOARD_H                 # never taller than the board
GONG_W, GONG_H, RELAY_W = 220, 48, 256
PHONE_GAP = 14
DIR = "assets/formation"
TILE_DIR = "assets/formation/tiles"

RAIL_TITLES = {"cols": ("81 nodes", "mu"), "cols-panic": ("BACKLASH", "dg"), "cols-clean": ("broken", "au")}
TILE_NAMES = ("hidden", "c0", *(f"c{n}" for n in range(1, 9)), "panic", "mine", *RAIL_TITLES,
              *(f"r{r}" for r in ROWS), "edge", "base")

RESULT_LABELS = {
    "ok": "node holds",
    "dup": "re-read (noop)",
    "panic": "BACKLASH",
    "clean": "FORMATION BROKEN",
    "reformat": "new formation",
    "refused": "re-lay refused",
    "press": "gong silent",
}
RESULT_CLASSES = {"ok": "tx", "dup": "mu", "panic": "dg", "clean": "au", "reformat": "tx",
                  "refused": "mu", "press": "mu"}

HELP = {
    "active": ("▸ click a node, submit the petition as-is. eyes = received.",
               "▸ the board redraws in ~1 min. the first step is always safe."),
    "panicked": ("▸ the formation struck back. press 重布 below to re-lay it.",
                 "▸ red 杀 marks: the killing traps, dormant."),
    "cleaned": ("▸ every safe node read. the sect remembers you.",
                "▸ press 重布 below to go again."),
}
HELP_ACT = ("click a node", "press 重布")  # the jade words: where the visitor can act

SIZE = 13      # panel body
LH = 18        # panel line height


def result_label(result: str) -> str:
    """The ledger's words for an engine result (<= 16 characters)."""
    if result in RESULT_LABELS:
        return RESULT_LABELS[result]
    cleaned = re.sub(r"[^a-z0-9 ()-]", "", str(result).lower())[:16]
    return cleaned or "?"


def fits(svg: str, width: float) -> bool:
    """Every run of text sits inside [0, width - 8]."""
    for x0, x1 in re.findall(r'data-run="(-?[\d.]+) (-?[\d.]+)"', svg):
        if float(x0) < -0.01 or float(x1) > width - 8 + 0.01:
            return False
    return True


# --- tiles --------------------------------------------------------------------------------

MID = TILE / 2


def _slab(w: float, h: float) -> str:
    return ink.rect(0, 0, w, h, "bg")


def _lattice(cls: str = "ln", opacity: float = 1.0) -> str:
    op = f' stroke-opacity="{ink.fmt(opacity)}"' if opacity < 1 else ""
    return f'<path d="M0 {MID}H{TILE}M{MID} 0V{TILE}" class="{cls}" stroke-width="1"{op}/>'


def _stone(r: float, fill: str, ring: str, ring_opacity: float = 1.0) -> str:
    op = f' stroke-opacity="{ink.fmt(ring_opacity)}"' if ring_opacity < 1 else ""
    return (f'<circle cx="{MID}" cy="{MID}" r="{ink.fmt(r)}" class="{fill}"/>'
            f'<circle cx="{MID}" cy="{MID}" r="{ink.fmt(r - 0.5)}" class="{ring}" stroke-width="1"{op}/>')


def _frame_d(w: float, h: float, sides: str, r: float = 4) -> str:
    """Hairline frame segments for a rail tile: 't' top (rounded corners),
    'b' bottom (rounded), 'l' left, 'r' right."""
    x0, x1 = 0.5, w - 0.5
    if sides == "t":
        return f"M{x0} {h}V{r + 0.5}Q{x0} {x0} {r + 0.5} {x0}H{ink.fmt(x1 - r)}Q{x1} {x0} {x1} {r + 0.5}V{h}"
    if sides == "b":
        y = h - 0.5
        return f"M{x0} 0V{ink.fmt(y - r)}Q{x0} {y} {r + 0.5} {y}H{ink.fmt(x1 - r)}Q{x1} {y} {x1} {ink.fmt(y - r)}V0"
    if sides == "l":
        return f"M{x0} 0V{h}"
    return f"M{x1} 0V{h}"


def tile_svg(name: str, mode: str) -> str:
    w, h, label, css = TILE, TILE, "", ""
    if name == "hidden":
        body = (_slab(w, h) + _lattice() + _stone(9.5, "rs", "au-s", 0.85)
                + f'<path d="M{MID} {MID - 3}L{MID + 3} {MID}L{MID} {MID + 3}L{MID - 3} {MID}Z" class="jd"/>')
        label = "an unread node of the formation: a raised stone with a jade rune"
    elif name == "c0":
        body = (_slab(w, h) + _lattice("ln", 0.55)
                + f'<circle cx="{MID}" cy="{MID}" r="3" class="ln" stroke-width="1"/>')
        label = "a read node, no traps touching it"
    elif re.fullmatch(r"c[1-8]", name):
        n = int(name[1])
        cls = "au" if n <= 2 or mode == "light" else "em"
        body = (_slab(w, h) + _lattice("ln", 0.55) + _stone(9.5, "bg", "ln")
                + ink.text(MID, MID + 5.4, str(n), 15, "medium", cls, anchor="middle"))
        label = f"a read node, {ink.plural(n, 'trap')} touching it"
    elif name == "panic":
        flick = ' class="pk"' if mode == "dark" else ""
        body = (_slab(w, h) + _lattice("dg-s", 0.7) + f"<g{flick}>"
                + f'<circle cx="{MID}" cy="{MID}" r="11.5" class="dg"/>'
                + ink.glyph_centred("杀", MID, MID, 17, "brush", "bg") + "</g>")
        if mode == "dark":
            css = (".pk{animation:fmpk 4.7s steps(1) 1.2s infinite}"
                   "@keyframes fmpk{0%{opacity:1}90%{opacity:.35}92%{opacity:1}94%{opacity:.5}96%,100%{opacity:1}}")
        label = "反噬, backlash: the killing trap that struck back"
    elif name == "mine":
        body = (_slab(w, h) + _lattice("ln", 0.55)
                + f'<g opacity=".72">{ink.glyph_centred("杀", MID, MID, 16, "brush", "dg")}</g>')
        label = "杀, a killing trap, dormant"
    elif name in RAIL_TITLES:
        w, h = BOARD_W, RAIL_TOP
        state, cls = RAIL_TITLES[name]
        frame_cls = "dg-s" if name == "cols-panic" else "ln"
        body = (_slab(w, h) + f'<path d="{_frame_d(w, h, "t")}" class="{frame_cls}" stroke-width="1"/>'
                + ink.corner(3, 3, 13, cls="au-s") + ink.corner(w - 3, 3, 13, flip_x=True, cls="au-s")
                + ink.text(20, 19, "护宗大阵", 14, "brush", "au")
                + ink.text(w - 20, 18, state, 11, "medium", cls, anchor="end", tracking=0.04)
                + "".join(ink.text(RAIL_L + i * TILE + MID, 31, col, 9.5, "mono", "mu", anchor="middle")
                          for i, col in enumerate(COLS)))
        label = f"护宗大阵, the grand sect-protecting formation ({state.lower()}), columns A to I"
    elif re.fullmatch(r"r[1-9]", name):
        w = RAIL_L
        body = (_slab(w, h) + f'<path d="{_frame_d(w, h, "l")}" class="ln" stroke-width="1"/>'
                + ink.text(5.6, MID + 3.4, name[1], 9.5, "mono", "mu", anchor="middle"))
        label = f"row {name[1]}"
    elif name == "edge":
        w = RAIL_R
        body = _slab(w, h) + f'<path d="{_frame_d(w, h, "r")}" class="ln" stroke-width="1"/>'
        label = "the formation's edge"
    elif name == "base":
        w, h = BOARD_W, RAIL_BOTTOM
        body = (f'<path d="M0 0H{w}V{h - 4}Q{w} {h} {w - 4} {h}H4Q0 {h} 0 {h - 4}Z" class="bg"/>'
                f'<path d="{_frame_d(w, h, "b")}" class="ln" stroke-width="1"/>')
        label = "the formation's edge"
    else:
        raise ValueError(f"unknown tile {name}")
    return ink.doc(w, h, body, label, mode, extra_css=css)


# --- the gong and the re-lay key -------------------------------------------------------------


def gong_svg(mode: str) -> str:
    """勿敲 DO NOT STRIKE: a bronze gong on its plate. In the dark it shivers
    now and then, as if someone nearly struck it."""
    w, h = GONG_W, GONG_H
    gx, gy, r = 27, 25, 14
    gong = (f'<path d="M{gx - 9} 3L{gx - 5} {gy - r + 2}M{gx + 9} 3L{gx + 5} {gy - r + 2}" class="sl-s" '
            'stroke-width="1.4" stroke-linecap="round"/>'
            f'<circle cx="{gx}" cy="{gy}" r="{r}" class="em"/>'
            f'<circle cx="{gx}" cy="{gy}" r="{r - 3.5}" class="au-s" stroke-opacity=".55" stroke-width="1"/>'
            f'<circle cx="{gx}" cy="{gy}" r="{r - 7}" class="au-s" stroke-opacity=".4" stroke-width="1"/>'
            f'<circle cx="{gx}" cy="{gy}" r="3.6" class="au"/>')
    css = ""
    if mode == "dark":
        gong = (f'<g class="gong">{gong}</g>'
                f'<circle cx="{gx}" cy="{gy}" r="{r + 2}" class="rip au-s" stroke-width="1"/>')
        css = (f".gong{{transform-origin:{gx}px 3px;animation:fmgong 6.4s ease-in-out 1.6s infinite}}"
               "@keyframes fmgong{0%,84%,100%{transform:rotate(0)}87%{transform:rotate(4deg)}"
               "90%{transform:rotate(-3deg)}93%{transform:rotate(1.5deg)}96%{transform:rotate(-.5deg)}}"
               f".rip{{opacity:0;transform-origin:{gx}px {gy}px;animation:fmrip 6.4s ease-out 1.6s infinite}}"
               "@keyframes fmrip{0%,85%{opacity:0;transform:scale(1)}87%{opacity:.7;transform:scale(1)}"
               "100%{opacity:0;transform:scale(1.5)}}")
    body = (ink.plate(0, 0, w, h, corner=0, fill="rs", frame="em-s", rx=4)
            + ink.rect(4.5, 4.5, w - 9, h - 9, "ln", 2, ' stroke-width="1"')
            + gong
            + ink.text(52, 31.5, "勿敲", 20, "brush", "tx")
            + ink.text(100, 29.5, "DO NOT STRIKE", 12.5, "medium", "tx", tracking=0.09))
    return ink.doc(w, h, body, "勿敲 DO NOT STRIKE", mode, extra_css=css)


def relay_svg(mode: str) -> str:
    """重布 re-lay the formation: only drawn into the README on a dead board."""
    w, h = RELAY_W, GONG_H
    body = (ink.plate(0, 0, w, h, corner=12, fill="rs", frame="jd-s", corner_cls="jd-s", rx=4)
            + ink.enso(30, 24, 11, "jd")
            + ink.text(52, 31.5, "重布", 20, "brush", "jd")
            + ink.text(98, 29.5, "re-lay the formation", 13, "body", "tx"))
    return ink.doc(w, h, body, "重布 re-lay the formation: bring up a fresh one", mode)


def static_assets() -> dict[str, str]:
    """Every static formation asset, both modes: {relative path: svg}."""
    out: dict[str, str] = {}
    for mode, suffix in ink.MODES:
        for name in TILE_NAMES:
            out[f"{TILE_DIR}/{mode}/{name}.svg"] = tile_svg(name, mode)
        out[f"{DIR}/gong{suffix}.svg"] = gong_svg(mode)
        out[f"{DIR}/relay{suffix}.svg"] = relay_svg(mode)
    return out


# --- the status panel -------------------------------------------------------------------------


def _n(view: dict, key: str) -> int:
    try:
        return max(int(view.get(key) or 0), 0)
    except (TypeError, ValueError):
        return 0


def _login(value: object) -> str:
    return re.sub(r"[^A-Za-z0-9-]", "", str(value or ""))[:39] or "someone"


def state_words(view: dict) -> list[tuple]:
    """The headline, as coloured parts."""
    if view.get("status") == "panicked":
        return [("反噬 ", "dg", "serif"), ("BACKLASH", "dg", "medium"),
                (f" at {view.get('panic_cell', '??')}. the formation struck back.", "dg")]
    if view.get("status") == "cleaned":
        return [("阵破 ", "au", "serif"), ("the formation is broken.", "au", "medium")]
    return [("the formation holds", "tx", "medium"), (" (no limit)", "mu")]


def board_line(view: dict) -> str:
    board = _n(view, "board") or 1
    if view.get("status") == "panicked":
        return f"#{board}, struck back {view.get('last', '??-??')} at {view.get('panic_cell', '??')}"
    if view.get("status") == "cleaned":
        return f"#{board}, broken {view.get('last', '??-??')}"
    return f"#{board}, laid {view.get('created', '??-??')}"


def trap_lines(view: dict) -> list[tuple[str, str]]:
    traps = _n(view, "traps") or 10
    if view.get("sealed"):
        return [(f"{traps} killing traps, positions sealed (hmac)", "tx")]
    # The pause before the admission is the joke: it gets its own line.
    return [(f"{traps} killing traps. the map is derivable from source.", "tx"), ("honor system.", "em")]


def record_text(view: dict) -> str:
    return (f"{ink.plural(_n(view, 'disciples'), 'disciple')}, {ink.plural(_n(view, 'steps'), 'step')}, "
            f"{ink.plural(_n(view, 'backlashes'), 'backlash', 'backlashes')}, "
            f"{ink.plural(_n(view, 'breaks'), 'break')}")


def _ops(view: dict) -> list[dict]:
    out = []
    for op in (view.get("ops") or [])[:4]:
        if not isinstance(op, dict):
            continue
        result = str(op.get("result", ""))
        out.append({"date": str(op.get("date", "??-??"))[:5], "login": _login(op.get("login")),
                    "op": re.sub(r"[^A-Za-z0-9 #|-]", "", str(op.get("op", "?")))[:10] or "?",
                    "label": result_label(result), "cls": RESULT_CLASSES.get(result, "mu")})
    return out


def _halls(view: dict) -> list[tuple[str, list[tuple[str, int]], str]]:
    return [("breakers", list(view.get("fame") or []), "au"),
            ("struck", list(view.get("shame") or []), "dg")]


def hall_text(entries: list[tuple[str, int]]) -> str:
    if not entries:
        return "(vacant)"
    return "  ".join(f"{i + 1}. {_login(login)} x{int(n)}" for i, (login, n) in enumerate(entries[:3]))


def _help_parts(line: str) -> list[tuple]:
    for act in HELP_ACT:
        if act in line:
            head, tail = line.split(act, 1)
            return [(head, "mu"), (act, "jd"), (tail, "mu")]
    return [(line, "mu")]


def _qi_dots(x: float, y: float, animate: bool) -> tuple[str, str]:
    """Three jade qi dots after 'the formation holds', bouncing in turn."""
    dots = "".join(f'<circle cx="{ink.fmt(x + i * 9)}" cy="{ink.fmt(y)}" r="2.6" class="jd{f" qd qd{i}" if animate else ""}"/>'
                   for i in range(3))
    css = ""
    if animate:
        css = (".qd{animation:fmqi 1.5s ease-in-out infinite}.qd1{animation-delay:.18s}.qd2{animation-delay:.36s}"
               "@keyframes fmqi{0%,60%,100%{transform:translateY(0);opacity:1}30%{transform:translateY(-4px);opacity:.55}}")
    return dots, css


def _meter(x: float, y: float, width: float, view: dict, height: float = 9) -> str:
    total = _n(view, "total") or 71
    done = min(_n(view, "done"), total)
    gap = 1.0
    cell = (width - gap * (total - 1)) / total
    lit = "".join(f"M{ink.fmt(x + i * (cell + gap))} {ink.fmt(y)}h{ink.fmt(cell)}v{height}h-{ink.fmt(cell)}z"
                  for i in range(done))
    off = "".join(f"M{ink.fmt(x + i * (cell + gap))} {ink.fmt(y)}h{ink.fmt(cell)}v{height}h-{ink.fmt(cell)}z"
                  for i in range(done, total))
    return (f'<path d="{off}" class="tk"/>' if off else "") + (f'<path d="{lit}" class="au"/>' if lit else "")


def panel_svg(view: dict, mode: str) -> str:
    """Desktop status panel, 500 x 292, as tall as the board beside it. If a
    busy formation would not fit, the oldest ledger rows give way."""
    w, h = PANEL_W, PANEL_H
    x0, vx = 18, 104
    vw = w - x0 - vx
    animate = mode == "dark" and view.get("status", "active") == "active"
    out = [ink.plate(0, 0, w, h, corner=14)]
    out.append(ink.text(x0, 30, "破阵", 18, "brush", "au"))
    out.append(ink.text(x0 + 42, 28.5, "break the formation", 12, "body", "mu", tracking=0.02))
    out.append(ink.text(w - x0, 28.5, f"formation #{_n(view, 'board') or 1}", 12, "mono", "mu", anchor="end"))
    out.append(ink.hline(x0, w - x0, 39, "ln"))
    css = ""
    if view.get("status", "active") == "active":
        # three jade qi dots sit between "holds" and "(no limit)"
        hold_w = ink.measure("the formation holds", SIZE, "medium")
        dots, css = _qi_dots(x0 + hold_w + 10, 54.5, animate)
        out += [ink.text(x0, 59, "the formation holds", SIZE, "medium", "tx"), dots,
                ink.text(x0 + hold_w + 38, 59, "(no limit)", SIZE, "body", "mu")]
    else:
        out.append(ink.runs(x0, 59, state_words(view), SIZE)[0])

    total = _n(view, "total") or 71
    facts: list[tuple[str, list[tuple]]] = [("formation", [(board_line(view), "tx")]),
                                             ("read", [(f"{_n(view, 'done')}/{total}", "tx", "mono")])]
    facts += [("traps" if i == 0 else "", [(t, c)]) for i, (t, c) in enumerate(trap_lines(view))]
    facts.append(("record", [(record_text(view), "tx")]))
    ops = _ops(view)
    halls = _halls(view)
    help_y = h - 18 - LH
    top = 84.0

    def rows_needed(n_ops: int) -> float:
        return top + (len(facts) + max(n_ops, 1) + len(halls) - 1) * LH + 12

    while len(ops) > 1 and rows_needed(len(ops)) > help_y - LH + 2:
        ops.pop()

    y = top
    for label, parts in facts:
        out.append(ink.text(x0, y, label, SIZE, "body", "mu"))
        out.append(ink.runs(vx, y, [(ink.fit(p[0], vw, SIZE, p[2] if len(p) > 2 else "body"), *p[1:])
                                    for p in parts], SIZE)[0])
        if label == "read":
            pct = f"{_n(view, 'pct')}%"
            mx = vx + ink.measure(f"{_n(view, 'done')}/{total}", SIZE, "mono") + 12
            out.append(ink.text(w - x0, y, pct, SIZE, "mono", "au" if _n(view, "done") else "mu", anchor="end"))
            out.append(_meter(mx, y - 9, w - x0 - ink.measure(pct, SIZE, "mono") - 10 - mx, view))
        y += LH
    y += 6
    out.append(ink.text(x0, y, "ledger", SIZE, "body", "mu"))
    if not ops:
        out.append(ink.text(vx, y, "no petitions yet. the formation waits.", SIZE, "body", "mu"))
        y += LH
    for op in ops:
        date_w = ink.measure("00-00 ", 12, "mono")
        label_w = ink.measure(op["label"], SIZE, "medium" if op["cls"] in ("dg", "au") else "body")
        op_w = ink.measure("step C4  ", 12, "mono") + 6
        login_room = vw - date_w - op_w - label_w - 10
        out.append(ink.text(vx, y, op["date"], 12, "mono", "mu"))
        out.append(ink.text(vx + date_w, y, ink.fit(op["login"], login_room, SIZE), SIZE, "body", "tx"))
        out.append(ink.text(w - x0 - label_w - op_w, y, op["op"], 12, "mono", "mu"))
        out.append(ink.text(w - x0, y, op["label"], SIZE, "medium" if op["cls"] in ("dg", "au") else "body",
                            op["cls"], anchor="end"))
        y += LH
    y += 6
    for name, entries, cls in halls:
        out.append(ink.text(x0, y, name, SIZE, "body", "mu"))
        out.append(ink.text(vx, y, ink.fit(hall_text(entries), vw, SIZE), SIZE, "body", cls if entries else "mu"))
        y += LH
    for i, line in enumerate(HELP.get(view.get("status", "active"), HELP["active"])):
        out.append(ink.runs(x0, help_y + i * LH, _help_parts(line), 12.5)[0])
    return ink.doc(w, h, "".join(out), panel_alt(view), mode, extra_css=css)


def panel_phone_svg(view: dict) -> str:
    """Phone status panel: 360 wide, dark, as tall as it needs."""
    w = ink.WP
    x0, vx = 14, 92
    vw = w - x0 - vx
    size = 12.5
    lh = 18
    animate = view.get("status", "active") == "active"
    out: list[str] = []
    out.append(ink.text(x0, 30, "破阵", 18, "brush", "au"))
    out.append(ink.text(x0 + 42, 28.5, "break the formation", 12, "body", "mu"))
    out.append(ink.text(w - x0, 28.5, f"#{_n(view, 'board') or 1}", 12, "mono", "mu", anchor="end"))
    out.append(ink.hline(x0, w - x0, 39, "ln"))
    y = 59.0
    css = ""
    if view.get("status", "active") == "active":
        hw = ink.measure("the formation holds", size, "medium")
        out.append(ink.text(x0, y, "the formation holds", size, "medium", "tx"))
        dots, css = _qi_dots(x0 + hw + 10, y - 4.5, animate)
        out.append(dots)
        y += lh
    else:
        words = "".join(p[0] for p in state_words(view))
        cls = "dg" if view.get("status") == "panicked" else "au"
        for line in ink.wrap(words, w - 2 * x0, size, "medium"):
            out.append(ink.text(x0, y, line, size, "medium", cls))
            y += lh
    y += 8

    def row(label: str, value: str, cls: str = "tx", face: str = "body") -> None:
        nonlocal y
        for i, line in enumerate(ink.wrap(value, vw, size, face) or [""]):
            if i == 0:
                out.append(ink.text(x0, y, label, size, "body", "mu"))
            out.append(ink.text(vx, y, line, size, face, cls))
            y += lh

    total = _n(view, "total") or 71
    row("formation", board_line(view))
    out.append(ink.text(w - x0, y, f"{_n(view, 'pct')}%", size, "mono", "au" if _n(view, "done") else "mu", anchor="end"))
    row("read", f"{_n(view, 'done')}/{total}", "tx", "mono")
    out.append(_meter(x0, y - 10, w - 2 * x0, view, 8))
    y += lh
    for i, (t, c) in enumerate(trap_lines(view)):
        row("traps" if i == 0 else "", t, c)
    items = record_text(view).split(", ")
    for i in range(0, len(items), 2):
        row("record" if i == 0 else "", ", ".join(items[i:i + 2]) + ("," if i + 2 < len(items) else ""))
    y += 6
    out.append(ink.text(x0, y, "ledger", size, "body", "mu"))
    y += lh
    ops = _ops(view)
    if not ops:
        out.append(ink.text(x0, y, "no petitions yet. the formation waits.", size, "body", "mu"))
        y += lh
    for op in ops:
        face = "medium" if op["cls"] in ("dg", "au") else "body"
        label_w = ink.measure(op["label"], size, face)
        date_w = ink.measure("00-00 ", 11.5, "mono")
        op_w = ink.measure("step C4 ", 11.5, "mono")
        room = w - 2 * x0 - date_w - op_w - label_w - 12
        out.append(ink.text(x0, y, op["date"], 11.5, "mono", "mu"))
        out.append(ink.text(x0 + date_w, y, ink.fit(op["login"], room, size), size, "body", "tx"))
        out.append(ink.text(w - x0 - label_w - op_w - 4, y, op["op"], 11.5, "mono", "mu"))
        out.append(ink.text(w - x0, y, op["label"], size, face, op["cls"], anchor="end"))
        y += lh
    y += 6
    for name, entries, cls in _halls(view):
        row(name, hall_text(entries), cls if entries else "mu")
    y += 6
    for line in HELP.get(view.get("status", "active"), HELP["active"]):
        for k, piece in enumerate(ink.wrap(line, w - 2 * x0 - 12, 12, "body")):
            out.append(ink.runs(x0 + (12 if k else 0), y, _help_parts(piece), 12)[0])
            y += lh
    h = y - lh + 18
    body = ink.plate(0, 0, w, h, corner=12) + "".join(out)
    # On phones the panel spans the column and the board stacks under it;
    # the transparent strip below the plate is the gap between the two.
    return ink.doc(w, h + PHONE_GAP, body, panel_alt(view), "dark", extra_css=css)


def panel_alt(view: dict) -> str:
    """The whole panel in words, in reading order."""
    status = view.get("status", "active")
    if status == "panicked":
        head = f"BACKLASH at {view.get('panic_cell', '??')}: the formation struck back."
    elif status == "cleaned":
        head = "the formation is broken."
    else:
        head = "the formation holds (no limit)."
    ops = "; ".join(f"{op['date']} {op['login']} {op['op']}: {op['label']}" for op in _ops(view)) or "none yet"
    halls = ". ".join(f"{name}: {hall_text(entries)}" for name, entries, _ in _halls(view))
    traps = " ".join(t for t, _ in trap_lines(view))
    helps = " ".join(line.lstrip("▸ ") for line in HELP.get(status, HELP["active"]))
    total = _n(view, "total") or 71
    return (f"破阵, break the formation. {head} formation {board_line(view)}. "
            f"{_n(view, 'done')} of {total} safe nodes read ({_n(view, 'pct')}%). traps: {traps} "
            f"record: {record_text(view)}. ledger: {ops}. {halls}. {helps}")
