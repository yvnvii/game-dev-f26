"""Twist Four engine: the authoritative game behind the five operations.

    reset(seed, opening) -> observation of the player to move
    observe(player_id)   -> what that player may know (everything: the game is fully observed, R14)
    legal_actions(pid)   -> canonical action texts, fixed order, [] when it is not pid's turn
    step(pid, action)    -> validated transition; an illegal action changes nothing (R8)
    outcome()            -> ongoing, or terminal with reason, winner and score

Rules live in c4d/rules.py and are specified in RULES.md.
"""
from __future__ import annotations

from . import rules
from .rules import COLS, SIZE, TURN_LIMIT, action_text, parse_action

SYMBOL = {0: ".", 1: "X", 2: "O"}
ALL_ACTIONS = [action_text(a) for a in rules.ALL_ACTIONS]


class TwistFour:
    """Players never receive this object, only observe() output."""

    def __init__(self) -> None:
        self.reset(0)

    # ---- operation 1 -------------------------------------------------------
    def reset(self, seed: int = 0, opening=()) -> dict:
        """Start an episode. The rules are deterministic; `seed` is recorded for the trace and
        used by randomized players. `opening` replays fixed action texts to build a suite position."""
        self.seed = seed
        self.state = rules.INITIAL
        self.history: list[tuple[int, str]] = []
        self._terminal: dict | None = None
        for a in opening:
            r = self.step(self.to_move, a)
            if not r["ok"]:
                raise ValueError(f"illegal opening action {a!r}: {r['error']}")
            if self._terminal:
                raise ValueError("opening ends the game; choose a shorter opening")
        return self.observe(self.to_move)

    # ---- helpers -----------------------------------------------------------
    @property
    def to_move(self) -> int:
        return self.state.to_move

    @property
    def turn(self) -> int:
        return self.state.turn

    @property
    def board(self) -> list:
        """Nested copy board[x][y][z]."""
        b = self.state.board
        return [[[b[rules.idx(x, y, z)] for z in range(SIZE)] for y in range(SIZE)] for x in range(SIZE)]

    def height(self, x: int, y: int) -> int:
        return rules.height(self.state.board, x, y)

    def render(self) -> str:
        """Four horizontal layers side by side, bottom layer first; row 1 is printed last (nearest you)."""
        b = self.state.board
        lines = ["      " + "".join(f"layer L{z + 1}".ljust(15) for z in range(SIZE)) + "  (L1 is the bottom)",
                 "      " + "        ".join("A B C D" for _ in range(SIZE))]
        for y in range(SIZE - 1, -1, -1):
            parts = [" ".join(SYMBOL[b[rules.idx(x, y, z)]] for x in range(SIZE)) for z in range(SIZE)]
            lines.append(f"  {y + 1}   " + "        ".join(parts))
        return "\n".join(lines)

    # ---- operation 2 -------------------------------------------------------
    def observe(self, player_id: int) -> dict:
        """Fully observed (R14): both players may see everything. Always a fresh copy."""
        last = self.history[-1][1] if self.history else None
        return {
            "you_are": player_id,
            "your_symbol": SYMBOL[player_id],
            "to_move": self.to_move if self._terminal is None else None,
            "turn": self.turn,
            "turn_limit": TURN_LIMIT,
            "move_number": len(self.history) + 1,
            "board_text": self.render(),
            "board": self.board,
            "last_action": last,
            "last_action_by": SYMBOL[self.history[-1][0]] if self.history else None,
            "status": self.outcome()["status"],
        }

    # ---- operation 3 -------------------------------------------------------
    def legal_actions(self, player_id: int) -> list[str]:
        """Legal action texts in the fixed order of ALL_ACTIONS (drops A1..D4, then twists).
        No ranking or hints; everything here follows from the visible board and last action."""
        if self._terminal is not None or player_id != self.to_move:
            return []
        return [action_text(a) for a in rules.legal(self.state)]

    # ---- operation 4 -------------------------------------------------------
    def step(self, player_id: int, action) -> dict:
        if self._terminal is not None:
            return {"ok": False, "error": "game is over"}
        if player_id != self.to_move:
            return {"ok": False, "error": f"not your turn (player {self.to_move} to move)"}
        a = parse_action(action)
        if a is None:
            return {"ok": False, "error": f"unrecognized action {action!r}; use e.g. 'drop B3', "
                                          f"'twist layer 2 cw', 'twist col B fwd', 'twist row 3 left'"}
        why = rules.why_illegal(self.state, a)
        if why:
            return {"ok": False, "error": why}
        placed = None
        if a[0] == "drop":
            placed = [a[1], a[2], rules.height(self.state.board, a[1], a[2])]
        nxt, result = rules.apply(self.state, a)
        self.state = nxt
        text = action_text(a)
        self.history.append((player_id, text))
        if result:
            self._terminal = {"reason": result["reason"], "winner": result["winner"], "line": result["line"]}
        elif not rules.legal(self.state):                                     # R13
            self._terminal = {"reason": "no_legal_actions", "winner": None, "line": None}
        return {"ok": True, "action": text, "placed": placed, "outcome": self.outcome()}

    # ---- operation 5 -------------------------------------------------------
    def outcome(self) -> dict:
        if self._terminal is None:
            return {"status": "ongoing", "reason": None, "winner": None, "score": {1: 0, 2: 0}}
        w = self._terminal["winner"]
        score = {1: 0, 2: 0} if w is None else {w: 1, 3 - w: -1}
        return {"status": "terminal", "reason": self._terminal["reason"], "winner": w, "score": score}

    def winning_line(self):
        """Cells of the winning line as names like 'B2 L1', or None."""
        if not self._terminal or not self._terminal.get("line"):
            return None
        return [f"{COLS[x]}{y + 1} L{z + 1}" for x, y, z in map(rules.xyz, self._terminal["line"])]

    def force_end(self, reason: str, winner: int | None = None) -> None:
        """Used only by the runner to end an episode for a limit (step/call/timeout)."""
        if self._terminal is None:
            self._terminal = {"reason": reason, "winner": winner, "line": None}


Connect3D = TwistFour   # earlier name, kept so old imports keep working
