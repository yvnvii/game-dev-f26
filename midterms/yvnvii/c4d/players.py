"""Players. Every player sees only observe() output and legal_actions(); none gets the engine.

- RandomPlayer: uniform random legal action (sanity floor).
- GreedyPlayer: take a win now (drop or twist); else block the opponent's winning drop; else a random
  drop that does not hand the opponent a line. The shared reference opponent.
- MinimaxPlayer: the baseline. Depth-limited negamax with alpha-beta over drops AND twists, scored by
  an open-line heuristic.
- ScriptedPlayer: replays fixed responses; used by tests in place of a live model.
"""
from __future__ import annotations

import random

from . import rules
from .rules import LINES, SIZE, State, action_text, parse_action


def state_from_obs(obs) -> State:
    """Rebuild a private rules.State from an observation (never touches the engine)."""
    nb = obs["board"]
    board = tuple(nb[x][y][z] for z in range(SIZE) for y in range(SIZE) for x in range(SIZE))
    last = parse_action(obs["last_action"]) if obs.get("last_action") else None
    return State(board, obs["you_are"], obs["turn"], last)


def fallback_action(legal: list[str]) -> str:
    """The runner's labeled fallback: the most central legal drop, else the first legal action."""
    for a in rules.CENTRE_DROPS:
        t = action_text(a)
        if t in legal:
            return t
    return legal[0]


class Player:
    name = "player"
    is_model = False

    def choose(self, obs: dict, legal: list[str], feedback: str | None = None, history=None) -> dict:
        """Return {"action": str, ...metadata}."""
        raise NotImplementedError


class RandomPlayer(Player):
    name = "random"

    def __init__(self, seed: int = 0):
        self.rng = random.Random(seed)

    def choose(self, obs, legal, feedback=None, history=None):
        return {"action": self.rng.choice(legal)}


class GreedyPlayer(Player):
    name = "greedy"

    def __init__(self, seed: int = 0):
        self.rng = random.Random(seed)

    def choose(self, obs, legal, feedback=None, history=None):
        s = state_from_obs(obs)
        me = s.to_move
        kids = rules.children(s)
        for a, _, res in kids:                                   # 1. win now
            if res and res["winner"] == me:
                return {"action": action_text(a)}
        as_opp = State(s.board, 3 - me, s.turn, None)            # 2. block the opponent's winning drop
        for a, _, res in rules.children(as_opp):
            if a[0] == "drop" and res and res["winner"] == 3 - me:
                return {"action": action_text(a)}
        safe = [a for a, _, res in kids if a[0] == "drop" and not (res and res["winner"] == 3 - me)]
        pool = safe or [a for a, _, _ in kids]
        return {"action": action_text(self.rng.choice(pool))}


WEIGHTS = (0, 1, 6, 40)
WIN = 100000


def evaluate(board, me: int) -> int:
    """Open-line heuristic: a line holding only one player's pieces scores for that player."""
    s, opp = 0, 3 - me
    for ln in LINES:
        m = t = 0
        for i in ln:
            v = board[i]
            if v == me:
                m += 1
            elif v == opp:
                t += 1
        if m and not t:
            s += WEIGHTS[m]
        elif t and not m:
            s -= WEIGHTS[t]
    return s


def _terminal_value(res, me: int, depth: int) -> int:
    if res["winner"] is None:
        return 0
    return WIN + depth if res["winner"] == me else -(WIN + depth)   # prefer faster wins, slower losses


class MinimaxPlayer(Player):
    name = "minimax"

    def __init__(self, depth: int = 3, seed: int = 0):
        self.depth = depth
        self.rng = random.Random(seed)
        self.nodes = 0

    def choose(self, obs, legal, feedback=None, history=None):
        s = state_from_obs(obs)
        me = s.to_move
        self.nodes = 0
        best, best_val, alpha, beta = [], -10**9, -10**9, 10**9
        for a, nxt, res in rules.children(s):
            if res:
                v = _terminal_value(res, me, self.depth)
            else:
                # Window ends at alpha-1, not alpha: an action that TIES the best is searched exactly,
                # so a pruned action's bound is always strictly below best (tests/test_regression.py).
                v = -self._negamax(nxt, self.depth - 1, -beta, -(alpha - 1))
            if v > best_val:
                best, best_val = [a], v
            elif v == best_val:
                best.append(a)
            alpha = max(alpha, v)
        return {"action": action_text(self.rng.choice(best)), "search_value": best_val, "nodes": self.nodes}

    def _negamax(self, s: State, depth: int, alpha: int, beta: int) -> int:
        self.nodes += 1
        me = s.to_move
        if depth == 0:
            return evaluate(s.board, me)
        kids = rules.children(s)
        if not kids:                                             # R13
            return 0
        best = -10**9
        for _, nxt, res in kids:
            v = _terminal_value(res, me, depth) if res else -self._negamax(nxt, depth - 1, -beta, -alpha)
            if v > best:
                best = v
            alpha = max(alpha, v)
            if alpha >= beta:
                break
        return best


class ScriptedPlayer(Player):
    """Replays fixed responses. Used by tests in place of a live model."""
    name = "scripted"
    is_model = True

    def __init__(self, responses):
        self.responses = list(responses)

    def choose(self, obs, legal, feedback=None, history=None):
        if not self.responses:
            raise RuntimeError("scripted player ran out of responses")
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        if callable(r):
            return r(obs, legal)
        return {"action": r, "input_tokens": 0, "output_tokens": 0}
