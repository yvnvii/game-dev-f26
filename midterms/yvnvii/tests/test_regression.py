"""Observed regression (found 2026-11-05 while running minimax vs greedy, seed 5).

Bug: the minimax baseline collected root moves "tied for best", but alpha-beta returns only a
bound for a pruned move. A losing move whose bound equalled the best score joined the tie list
and could be chosen. In the observed game, O (minimax depth 3) played A2 with search value +101
while X threatened C3 to complete the bottom row C1-C2-C3-C4; X played C3 and won.

Fix: search later root moves with the window (-beta, -(alpha - 1)) so any move that ties the
best value is evaluated exactly, and a pruned move always scores strictly below the best.
This test failed before the fix (minimax chose A2 for several seeds) and passes after.
"""
from c4d.engine import Connect3D
from c4d.players import MinimaxPlayer

OBSERVED_MOVES = "A3 A4 D3 D4 A1 B3 C4 B4 D2 B3 B1 B3 B3 D1 C2 C2 D4 C2 C1".split()


def test_minimax_blocks_bottom_row_threat_from_observed_game():
    g = Connect3D()
    g.reset(0, OBSERVED_MOVES)
    assert g.to_move == 2
    for depth in (2, 3):
        for seed in range(10):
            choice = MinimaxPlayer(depth, seed).choose(g.observe(2), g.legal_actions(2))
            assert choice["action"] == "C3", (depth, seed, choice)
