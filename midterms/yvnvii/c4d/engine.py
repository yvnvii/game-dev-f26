"""3D gravity Connect Four on a 4x4x4 cube.

The engine holds the authoritative state and exposes the five operations:
reset(seed), observe(player_id), legal_actions(player_id), step(player_id, action), outcome().

Coordinates: board[x][y][z], x = column letter A-D, y = row 1-4, z = height 0 (bottom) to 3 (top).
An action "B3" drops the mover's piece into the vertical shaft at x=B, y=3; it falls to the
lowest empty height (gravity, as in Connect Four / Score Four).
"""
from __future__ import annotations

import itertools

SIZE = 4
PLAYERS = (1, 2)
SYMBOL = {0: ".", 1: "X", 2: "O"}
COLS = "ABCD"


def action_name(x: int, y: int) -> str:
    return f"{COLS[x]}{y + 1}"


def parse_action(action: str) -> tuple[int, int] | None:
    """Return (x, y) for a well-formed action string like 'B3', else None."""
    if not isinstance(action, str):
        return None
    a = action.strip().upper()
    if len(a) != 2 or a[0] not in COLS or a[1] not in "1234":
        return None
    return COLS.index(a[0]), int(a[1]) - 1


ALL_ACTIONS = [action_name(x, y) for y in range(SIZE) for x in range(SIZE)]


def _winning_lines() -> list[tuple[tuple[int, int, int], ...]]:
    """All straight lines of 4 cells inside the cube (76 for a 4x4x4 cube)."""
    lines = set()
    dirs = [d for d in itertools.product((-1, 0, 1), repeat=3) if d != (0, 0, 0)]
    for x, y, z in itertools.product(range(SIZE), repeat=3):
        for dx, dy, dz in dirs:
            cells = [(x + i * dx, y + i * dy, z + i * dz) for i in range(SIZE)]
            if all(0 <= c < SIZE for cell in cells for c in cell):
                lines.add(tuple(sorted(cells)))
    return sorted(lines)


LINES = _winning_lines()
LINES_THROUGH = {
    cell: [ln for ln in LINES if cell in ln]
    for cell in itertools.product(range(SIZE), repeat=3)
}


class Connect3D:
    """Authoritative game state. Players never receive this object, only observe() output."""

    def __init__(self) -> None:
        self.reset(0)

    # ---- operation 1 -------------------------------------------------------
    def reset(self, seed: int = 0, opening: list[str] | tuple[str, ...] = ()) -> dict:
        """Start an episode. The rules are deterministic; `seed` is recorded for the
        trace and used by randomized players. `opening` replays a fixed list of moves
        to create a declared starting situation."""
        self.seed = seed
        self.board = [[[0] * SIZE for _ in range(SIZE)] for _ in range(SIZE)]
        self.to_move = 1
        self.history: list[tuple[int, str]] = []
        self._terminal: dict | None = None
        for a in opening:
            r = self.step(self.to_move, a)
            if not r["ok"]:
                raise ValueError(f"illegal opening move {a!r}: {r['error']}")
            if self._terminal:
                raise ValueError("opening ends the game; choose a shorter opening")
        return self.observe(self.to_move)

    # ---- helpers -----------------------------------------------------------
    def height(self, x: int, y: int) -> int:
        """Number of pieces in shaft (x, y) == index of the next free z."""
        col = self.board[x][y]
        h = 0
        while h < SIZE and col[h] != 0:
            h += 1
        return h

    def render(self) -> str:
        """Four horizontal layers side by side, bottom layer first."""
        rows = ["      " + "        ".join("A B C D" for _ in range(SIZE))]
        for y in range(SIZE - 1, -1, -1):
            parts = []
            for z in range(SIZE):
                parts.append(" ".join(SYMBOL[self.board[x][y][z]] for x in range(SIZE)))
            rows.append(f"  {y + 1}   " + "        ".join(parts))
        title = "      " + "".join(f"layer z={z + 1}".ljust(15) for z in range(SIZE))
        return title + "  (z=1 is the bottom)\n" + "\n".join(rows)

    # ---- operation 2 -------------------------------------------------------
    def observe(self, player_id: int) -> dict:
        """Connect Four is fully observed: both players may see the whole board.
        The observation is a fresh copy, never a handle to the authoritative state."""
        return {
            "you_are": player_id,
            "your_symbol": SYMBOL[player_id],
            "to_move": self.to_move if self._terminal is None else None,
            "move_number": len(self.history) + 1,
            "board_text": self.render(),
            "board": [[list(col) for col in plane] for plane in self.board],
            "last_move": self.history[-1][1] if self.history else None,
            "status": self.outcome()["status"],
        }

    # ---- operation 3 -------------------------------------------------------
    def legal_actions(self, player_id: int) -> list[str]:
        """Non-full shafts, only for the player to move. No ranking, no hints."""
        if self._terminal is not None or player_id != self.to_move:
            return []
        return [a for a in ALL_ACTIONS if self.height(*parse_action(a)) < SIZE]

    # ---- operation 4 -------------------------------------------------------
    def step(self, player_id: int, action: str) -> dict:
        """Validate and apply one move. Invalid moves change nothing."""
        if self._terminal is not None:
            return {"ok": False, "error": "game is over"}
        if player_id != self.to_move:
            return {"ok": False, "error": f"not your turn (player {self.to_move} to move)"}
        xy = parse_action(action)
        if xy is None:
            return {"ok": False, "error": f"unrecognized action {action!r}; use a column like A1..D4"}
        x, y = xy
        z = self.height(x, y)
        if z >= SIZE:
            return {"ok": False, "error": f"shaft {action_name(x, y)} is full"}
        self.board[x][y][z] = player_id
        name = action_name(x, y)
        self.history.append((player_id, name))
        if self._completes_line((x, y, z), player_id):
            self._terminal = {"reason": "connect_four", "winner": player_id}
        elif len(self.history) == SIZE ** 3:
            self._terminal = {"reason": "board_full", "winner": None}
        else:
            self.to_move = 3 - player_id
        return {"ok": True, "placed": [x, y, z], "action": name, "outcome": self.outcome()}

    def _completes_line(self, cell, p) -> bool:
        return any(all(self.board[a][b][c] == p for a, b, c in ln) for ln in LINES_THROUGH[cell])

    # ---- operation 5 -------------------------------------------------------
    def outcome(self) -> dict:
        if self._terminal is None:
            return {"status": "ongoing", "reason": None, "winner": None, "score": {1: 0, 2: 0}}
        w = self._terminal["winner"]
        score = {1: 0, 2: 0} if w is None else {w: 1, 3 - w: -1}
        return {"status": "terminal", "reason": self._terminal["reason"], "winner": w, "score": score}

    def force_end(self, reason: str, winner: int | None = None) -> None:
        """Used only by the runner to end an episode for a limit (step/call/timeout/invalid)."""
        if self._terminal is None:
            self._terminal = {"reason": reason, "winner": winner}
