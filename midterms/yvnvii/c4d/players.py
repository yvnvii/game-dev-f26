"""Players. Every player sees only observe() output and legal_actions(); none gets the engine.

- RandomPlayer: uniform random legal move (sanity floor only).
- GreedyPlayer: win now if possible, else block an immediate loss, else random. Used as the
  shared reference opponent.
- MinimaxPlayer: the baseline. Depth-limited negamax with alpha-beta and an open-line heuristic.
- ModelPlayer: an LLM chooses the move from a text prompt (see c4d/model_player.py).
"""
from __future__ import annotations

import random

from .engine import LINES, SIZE, parse_action

# The search players rebuild a private copy of the board from the observation.
# They never touch the runner's authoritative game.


def _board_from_obs(obs):
    return [[list(col) for col in plane] for plane in obs["board"]]


def _height(board, x, y):
    col = board[x][y]
    h = 0
    while h < SIZE and col[h]:
        h += 1
    return h


def _winner(board):
    for ln in LINES:
        a = board[ln[0][0]][ln[0][1]][ln[0][2]]
        if a and all(board[x][y][z] == a for x, y, z in ln[1:]):
            return a
    return 0


def _center_order(actions):
    # inner 2x2 shafts first; they touch the most lines
    def key(a):
        x, y = parse_action(a)
        return abs(x - 1.5) + abs(y - 1.5)
    return sorted(actions, key=key)


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
        me = obs["you_are"]
        board = _board_from_obs(obs)
        for who in (me, 3 - me):          # first: can I win? then: must I block?
            for a in legal:
                x, y = parse_action(a)
                z = _height(board, x, y)
                board[x][y][z] = who
                w = _winner(board)
                board[x][y][z] = 0
                if w == who:
                    return {"action": a}
        return {"action": self.rng.choice(legal)}


WEIGHTS = {1: 1, 2: 6, 3: 40}


def evaluate(board, me):
    """Open-line heuristic: lines containing only one player's pieces score for that player."""
    s = 0
    opp = 3 - me
    for ln in LINES:
        mine = theirs = 0
        for x, y, z in ln:
            v = board[x][y][z]
            if v == me:
                mine += 1
            elif v == opp:
                theirs += 1
        if mine and not theirs:
            s += WEIGHTS[mine]
        elif theirs and not mine:
            s -= WEIGHTS[theirs]
    return s


class MinimaxPlayer(Player):
    name = "minimax"

    def __init__(self, depth: int = 3, seed: int = 0):
        self.depth = depth
        self.rng = random.Random(seed)
        self.nodes = 0

    def choose(self, obs, legal, feedback=None, history=None):
        me = obs["you_are"]
        board = _board_from_obs(obs)
        self.nodes = 0
        best, best_val = [], -10**9
        alpha, beta = -10**9, 10**9
        for a in _center_order(legal):
            x, y = parse_action(a)
            z = _height(board, x, y)
            board[x][y][z] = me
            # Window ends at alpha-1, not alpha: a move that TIES the best is searched exactly,
            # and a pruned move's bound is strictly below best (see tests/test_regression.py).
            v = -self._negamax(board, 3 - me, self.depth - 1, -beta, -(alpha - 1), (x, y, z))
            board[x][y][z] = 0
            if v > best_val:
                best, best_val = [a], v
            elif v == best_val:
                best.append(a)
            alpha = max(alpha, v)
        return {"action": self.rng.choice(best), "search_value": best_val, "nodes": self.nodes}

    def _negamax(self, board, to_move, depth, alpha, beta, last):
        self.nodes += 1
        # did the previous mover just win?
        lx, ly, lz = last
        prev = board[lx][ly][lz]
        for ln in LINES:
            if last in ln and all(board[x][y][z] == prev for x, y, z in ln):
                return -100000 - depth          # prefer faster wins / slower losses
        moves = [(x, y) for x in range(SIZE) for y in range(SIZE) if _height(board, x, y) < SIZE]
        if not moves:
            return 0
        if depth == 0:
            return evaluate(board, to_move)
        moves.sort(key=lambda m: abs(m[0] - 1.5) + abs(m[1] - 1.5))
        best = -10**9
        for x, y in moves:
            z = _height(board, x, y)
            board[x][y][z] = to_move
            v = -self._negamax(board, 3 - to_move, depth - 1, -beta, -alpha, (x, y, z))
            board[x][y][z] = 0
            if v > best:
                best = v
            alpha = max(alpha, v)
            if alpha >= beta:
                break
        return best


class ScriptedPlayer(Player):
    """Replays a fixed list of raw responses. Used by tests in place of a live model."""
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
