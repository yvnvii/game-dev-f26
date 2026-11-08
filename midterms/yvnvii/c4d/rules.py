"""Twist Four rules as pure functions (no I/O, no randomness). Rule IDs refer to RULES.md.

A board is a tuple of 64 ints (0 empty, 1 = X, 2 = O); cell (x, y, z) is index x + 4y + 16z.
x = column A-D, y = row 1-4 (row 1 at the front), z = layer L1-L4 (L1 at the bottom).

Actions are tuples:
    ("drop", x, y)                 text: "drop B3"
    ("twist", axis, k, direction)  text: "twist layer 2 cw", "twist col B fwd", "twist row 3 left"
"""
from __future__ import annotations

import itertools
from typing import NamedTuple

SIZE = 4
COLS = "ABCD"
TURN_LIMIT = 100                     # R12
EMPTY = (0,) * 64


def idx(x: int, y: int, z: int) -> int:
    return x + 4 * y + 16 * z


def xyz(i: int) -> tuple[int, int, int]:
    return i % 4, (i // 4) % 4, i // 16


# ---- R9: the 76 lines -------------------------------------------------------------------
def _lines():
    found = set()
    dirs = [d for d in itertools.product((-1, 0, 1), repeat=3) if d != (0, 0, 0)]
    for x, y, z in itertools.product(range(SIZE), repeat=3):
        for dx, dy, dz in dirs:
            cells = [(x + k * dx, y + k * dy, z + k * dz) for k in range(SIZE)]
            if all(0 <= c < SIZE for cell in cells for c in cell):
                found.add(tuple(sorted(idx(*c) for c in cells)))
    return sorted(found)


LINES: list[tuple[int, int, int, int]] = _lines()
LINES_THROUGH = [[ln for ln in LINES if i in ln] for i in range(64)]
SHAFTS = [tuple(idx(x, y, z) for z in range(SIZE)) for y in range(SIZE) for x in range(SIZE)]

# ---- R5: twists -------------------------------------------------------------------------
AXES = ("layer", "col", "row")
DIRS = {"layer": ("cw", "ccw"), "col": ("fwd", "back"), "row": ("left", "right")}
INVERSE = {"cw": "ccw", "ccw": "cw", "fwd": "back", "back": "fwd", "left": "right", "right": "left"}


def in_slice(x: int, y: int, z: int, axis: str, k: int) -> bool:
    return (z if axis == "layer" else x if axis == "col" else y) == k


def turn_cell(x: int, y: int, z: int, direction: str) -> tuple[int, int, int]:
    """Where a piece of the turning slice goes (table in RULES.md, R5)."""
    return {
        "cw": (y, 3 - x, z), "ccw": (3 - y, x, z),          # layer, seen from above
        "fwd": (x, 3 - z, y), "back": (x, z, 3 - y),        # column slab: top rolls to row 1 / row 4
        "left": (3 - z, y, x), "right": (z, y, 3 - x),      # row slab: top rolls to A / D
    }[direction]


# precomputed permutation for each twist: new index of every cell
PERM = {}
for _axis in AXES:
    for _k in range(SIZE):
        for _d in DIRS[_axis]:
            PERM[(_axis, _k, _d)] = tuple(
                idx(*turn_cell(*xyz(i), _d)) if in_slice(*xyz(i), _axis, _k) else i for i in range(64))

DROPS = [("drop", x, y) for y in range(SIZE) for x in range(SIZE)]              # A1, B1, ... D4
TWISTS = [("twist", a, k, d) for a in AXES for k in range(SIZE) for d in DIRS[a]]
ALL_ACTIONS = DROPS + TWISTS                                                     # 16 + 24 = 40
CENTRE_DROPS = sorted(DROPS, key=lambda a: abs(a[1] - 1.5) + abs(a[2] - 1.5))


def settle(cells) -> tuple:
    """R3 gravity: each shaft keeps its order and drops to the bottom."""
    out = [0] * 64
    for shaft in SHAFTS:
        w = 0
        for i in shaft:
            v = cells[i]
            if v:
                out[shaft[w]] = v
                w += 1
    return tuple(out)


def twist_board(board, axis: str, k: int, direction: str) -> tuple:
    perm = PERM[(axis, k, direction)]
    t = [0] * 64
    for i, v in enumerate(board):
        if v:
            t[perm[i]] = v
    return settle(t)


def height(board, x: int, y: int) -> int:
    h = 0
    while h < SIZE and board[idx(x, y, h)]:
        h += 1
    return h


def line_for(board, p: int):
    for ln in LINES:
        if board[ln[0]] == p and board[ln[1]] == p and board[ln[2]] == p and board[ln[3]] == p:
            return ln
    return None


# ---- action text --------------------------------------------------------------------------
def action_text(a) -> str:
    if a[0] == "drop":
        return f"drop {COLS[a[1]]}{a[2] + 1}"
    _, axis, k, d = a
    name = str(k + 1) if axis != "col" else COLS[k]
    return f"twist {axis} {name} {d}"


_TEXT_TO_ACTION = {action_text(a): a for a in ALL_ACTIONS}


def parse_action(text):
    """Canonical action text -> action tuple, or None. Case and extra spaces are ignored."""
    if not isinstance(text, str):
        return None
    norm = " ".join(text.strip().strip("`'\".").lower().split())
    for key, a in _TEXT_TO_ACTION.items():
        if key.lower() == norm:
            return a
    return None


# ---- state and transitions -------------------------------------------------------------------
class State(NamedTuple):
    board: tuple
    to_move: int
    turn: int
    last: tuple | None


INITIAL = State(EMPTY, 1, 1, None)                                                # R2


def is_instant_undo(last, a) -> bool:
    """R7: the exact inverse of the opponent's immediately previous twist."""
    return (last is not None and last[0] == "twist" and a[0] == "twist"
            and last[1] == a[1] and last[2] == a[2] and INVERSE[last[3]] == a[3])


def why_illegal(s: State, a) -> str | None:
    if a[0] == "drop":
        return None if height(s.board, a[1], a[2]) < SIZE else f"shaft {COLS[a[1]]}{a[2] + 1} is full"
    if is_instant_undo(s.last, a):
        return f"{action_text(a)} would undo your opponent's last twist (rule R7)"
    if twist_board(s.board, *a[1:]) == s.board:
        return f"{action_text(a)} would not change the board (rule R6)"
    return None


def apply(s: State, a):
    """Return (next_state, result) or None if illegal. result is None or
    {"winner": 1|2|None, "line": tuple|None, "reason": str}."""
    p, q = s.to_move, 3 - s.to_move
    result = None
    if a[0] == "drop":                                                            # R4, R10
        z = height(s.board, a[1], a[2])
        if z >= SIZE:
            return None
        i = idx(a[1], a[2], z)
        b = list(s.board)
        b[i] = p
        b = tuple(b)
        for ln in LINES_THROUGH[i]:
            if b[ln[0]] == p and b[ln[1]] == p and b[ln[2]] == p and b[ln[3]] == p:
                result = {"winner": p, "line": ln, "reason": "connect_four"}
                break
    else:                                                                         # R5-R7, R11
        if is_instant_undo(s.last, a):
            return None
        b = twist_board(s.board, *a[1:])
        if b == s.board:
            return None
        mine, theirs = line_for(b, p), line_for(b, q)
        if mine:
            result = {"winner": p, "line": mine, "reason": "connect_four"}        # only mine, or both
        elif theirs:
            result = {"winner": q, "line": theirs, "reason": "connect_four"}      # only theirs
    turn = s.turn + 1
    if result is None and turn > TURN_LIMIT:                                      # R12
        result = {"winner": None, "line": None, "reason": "turn_limit"}
    return State(b, p if result else q, turn, a), result


def legal(s: State) -> list:
    return [a for a in ALL_ACTIONS if why_illegal(s, a) is None]


def children(s: State):
    """(action, next_state, result) for every legal action; centre drops first, then twists."""
    out = []
    for a in CENTRE_DROPS + TWISTS:
        r = apply(s, a)
        if r is not None:
            out.append((a, r[0], r[1]))
    return out
