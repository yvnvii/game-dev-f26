"""Observed regression: the minimax baseline chose a losing move because of an alpha-beta tie bug.

Found 2026-11-05 in the drop-only version of this game (minimax vs greedy, seed 5): minimax (depth 3)
played A2 with search value +101 while X threatened C3 to complete the bottom row C1-C2-C3-C4, and lost.
Cause: root moves "tied for best" were collected, but alpha-beta returns only a BOUND for a pruned move,
so a losing move whose bound equalled the best value joined the tie list and could be picked.
Fix: search later root moves with the window (-beta, -(alpha - 1)), so a tie is searched exactly and a
pruned move always scores strictly below the best. The original test (move must be C3) failed before the
fix and passed after; see this file's git history.

In Twist Four the same bug class is checked directly: every action minimax returns must be truly optimal
at its depth, compared with a plain negamax that never prunes. With the alpha-1 fix removed, this test
fails (checked 2026-11-08).
"""
import random

import pytest

from c4d import rules
from c4d.engine import TwistFour
from c4d.players import MinimaxPlayer, _terminal_value, evaluate

OBSERVED_DROPS = "A3 A4 D3 D4 A1 B3 C4 B4 D2 B3 B1 B3 B3 D1 C2 C2 D4 C2 C1".split()


def exact(s, depth):
    """Negamax value for the player to move, no pruning."""
    if depth == 0:
        return evaluate(s.board, s.to_move)
    kids = rules.children(s)
    if not kids:
        return 0
    return max(_terminal_value(res, s.to_move, depth) if res else -exact(nxt, depth - 1)
               for _, nxt, res in kids)


def exact_root_values(s, depth):
    return {rules.action_text(a): (_terminal_value(res, s.to_move, depth) if res else -exact(nxt, depth - 1))
            for a, nxt, res in rules.children(s)}


def positions():
    """The observed position (O to move) plus a few seeded mid-game positions with twists."""
    g = TwistFour()
    g.reset(0, ["drop " + m for m in OBSERVED_DROPS])
    yield g
    rng = random.Random(3)
    made = 0
    while made < 4:
        g = TwistFour()
        g.reset(0)
        for _ in range(rng.randrange(8, 16)):
            if g.outcome()["status"] != "ongoing":
                break
            g.step(g.to_move, rng.choice(g.legal_actions(g.to_move)))
        if g.outcome()["status"] == "ongoing":
            made += 1
            yield g


@pytest.mark.parametrize("g", list(positions()), ids=lambda g: f"turn{g.turn}")
def test_minimax_always_returns_an_optimal_action(g):
    s = g.state
    values = exact_root_values(s, 2)
    best = max(values.values())
    for seed in range(4):
        choice = MinimaxPlayer(2, seed).choose(g.observe(s.to_move), g.legal_actions(s.to_move))
        assert values[choice["action"]] == best, (choice, best)


def test_observed_position_minimax_takes_an_immediate_win():
    """In Twist Four, O can win at once in the observed position by a twist; minimax must take it."""
    g = TwistFour()
    g.reset(0, ["drop " + m for m in OBSERVED_DROPS])
    for depth in (2, 3):
        a = MinimaxPlayer(depth, 0).choose(g.observe(2), g.legal_actions(2))["action"]
        _, res = rules.apply(g.state, rules.parse_action(a))
        assert res and res["winner"] == 2, a
