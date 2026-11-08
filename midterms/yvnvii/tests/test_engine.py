"""Twist Four rules (RULES.md): invariants, legal/illegal actions, terminal outcomes, information boundary."""
import random

import pytest

from c4d import rules
from c4d.engine import ALL_ACTIONS, TwistFour
from c4d.rules import COLS, LINES, State, idx, xyz


def fresh(opening=()):
    g = TwistFour()
    g.reset(0, list(opening))
    return g


def decode(s):
    """64-char string in index order (x fastest, then y, then z): '.', 'X', 'O'."""
    return tuple(".XO".index(ch) for ch in s)


def pieces(g):
    """Map 'B2 L1' -> 'X'/'O' for occupied cells."""
    return {f"{COLS[x]}{y + 1} L{z + 1}": ".XO"[v] for i, v in enumerate(g.state.board) if v
            for x, y, z in [xyz(i)]}


# ---- rule invariants (R1, R3, R5, R9) ---------------------------------------------------------
def test_cube_has_76_lines_of_four_distinct_collinear_cells():
    assert len(LINES) == 76
    for ln in LINES:
        pts = [xyz(i) for i in ln]
        d = [pts[1][k] - pts[0][k] for k in range(3)]
        assert all(pts[j][k] == pts[0][k] + j * d[k] for j in range(4) for k in range(3))


def test_initial_state_R2():
    g = fresh()
    assert g.to_move == 1 and g.turn == 1 and g.history == []
    assert all(v == 0 for v in g.state.board)
    # empty board: every drop is legal, no twist is (R6: nothing to turn)
    assert g.legal_actions(1) == [a for a in ALL_ACTIONS if a.startswith("drop")]
    assert len(ALL_ACTIONS) == 40


def test_every_twist_permutes_its_slice_and_its_inverse_undoes_it():
    for _, axis, k, d in rules.TWISTS:
        perm = rules.PERM[(axis, k, d)]
        assert sorted(perm) == list(range(64))
        inv = rules.PERM[(axis, k, rules.INVERSE[d])]
        for i in range(64):
            assert inv[perm[i]] == i
            if not rules.in_slice(*xyz(i), axis, k):
                assert perm[i] == i                      # cells outside the slice never move
            else:
                assert rules.in_slice(*xyz(perm[i]), axis, k)


def test_gravity_and_piece_counts_hold_through_random_play_with_twists():
    rng = random.Random(11)
    for _ in range(25):
        g = fresh()
        drops = {1: 0, 2: 0}
        while g.outcome()["status"] == "ongoing":
            p = g.to_move
            a = rng.choice(g.legal_actions(p))
            assert g.step(p, a)["ok"]
            if a.startswith("drop"):
                drops[p] += 1
            b = g.state.board
            for x in range(4):
                for y in range(4):
                    h = rules.height(b, x, y)
                    assert all(b[idx(x, y, z)] for z in range(h))            # R3: no gaps ...
                    assert not any(b[idx(x, y, z)] for z in range(h, 4))     # ... and nothing floats
            assert sum(v == 1 for v in b) == drops[1] and sum(v == 2 for v in b) == drops[2]
        assert g.outcome()["reason"] in ("connect_four", "turn_limit", "no_legal_actions")


# ---- worked examples from RULES.md -------------------------------------------------------------
def test_worked_example_layer_twist():
    g = fresh(["drop A1", "drop B1", "drop A1"])          # X A1 L1, O B1 L1, X A1 L2
    assert g.step(2, "twist layer 1 cw")["ok"]
    assert pieces(g) == {"A1 L1": "X", "A3 L1": "O", "A4 L1": "X"}


def test_worked_example_slab_twist():
    g = fresh(["drop A1", "drop B1", "drop A1"])
    assert g.step(2, "twist col A fwd")["ok"]
    assert pieces(g) == {"A4 L1": "X", "A3 L1": "X", "B1 L1": "O"}


def test_drop_lands_on_top_of_its_shaft_R4():
    g = fresh()
    assert g.step(1, "drop B2")["placed"] == [1, 1, 0]
    assert g.step(2, "drop B2")["placed"] == [1, 1, 1]
    assert g.step(1, "DROP  b2")["placed"] == [1, 1, 2]   # case and spacing are ignored


# ---- legal and illegal actions (R6, R7, R8) ----------------------------------------------------
def test_no_op_twist_is_illegal_R6():
    g = fresh(["drop B2"])
    # layer 2 is empty, so turning it changes nothing
    assert "twist layer 2 cw" not in g.legal_actions(2)
    r = g.step(2, "twist layer 2 cw")
    assert not r["ok"] and "R6" in r["error"]


def test_instant_undo_is_illegal_but_repeating_is_legal_R7():
    g = fresh(["drop A1", "drop B1", "drop A1", "twist layer 1 cw"])   # O just twisted
    assert "twist layer 1 ccw" not in g.legal_actions(1)
    r = g.step(1, "twist layer 1 ccw")
    assert not r["ok"] and "R7" in r["error"]
    assert "twist layer 1 cw" in g.legal_actions(1)
    assert g.step(1, "twist layer 1 cw")["ok"]
    # after a DROP in between, the old twist may be reversed again
    g2 = fresh(["drop A1", "drop B1", "drop A1", "twist layer 1 cw", "drop D4"])
    assert "twist layer 1 ccw" in g2.legal_actions(2)


def test_full_shaft_malformed_and_out_of_turn_actions_change_nothing_R8():
    g = fresh(["drop A1", "drop A1", "drop A1", "drop A1"])
    before = (g.state, list(g.history))
    for bad in ["drop A1", "drop E1", "drop A5", "A1", "twist layer 5 cw", "twist col E fwd",
                "twist row 2 fwd", "twist layer 1 up", "", None, 7]:
        assert not g.step(1, bad)["ok"], bad
    assert not g.step(2, "drop B1")["ok"]                      # not O's turn
    assert (g.state, list(g.history)) == before
    assert g.legal_actions(2) == []
    assert "drop A1" not in g.legal_actions(1)


# ---- terminal outcomes (R10, R11, R12, R13) -------------------------------------------------------
def test_drop_completes_a_line_R10():
    g = fresh(["drop A1", "drop A2", "drop B1", "drop B2", "drop C1", "drop C2"])
    r = g.step(1, "drop D1")
    assert r["outcome"] == {"status": "terminal", "reason": "connect_four", "winner": 1, "score": {1: 1, 2: -1}}
    assert g.winning_line() == ["A1 L1", "B1 L1", "C1 L1", "D1 L1"]
    assert g.legal_actions(1) == g.legal_actions(2) == []
    assert not g.step(2, "drop D2")["ok"]


def test_space_diagonal_win_through_all_four_layers():
    # X on A1 L1, B2 L2, C3 L3 with supports underneath; D4 holds 3 pieces, so X's drop lands on D4 L4.
    cells = {(0, 0, 0): 1, (1, 1, 0): 2, (1, 1, 1): 1, (2, 2, 0): 2, (2, 2, 1): 2, (2, 2, 2): 1,
             (3, 3, 0): 1, (3, 3, 1): 2, (3, 3, 2): 1, (3, 0, 0): 2}
    b = [0] * 64
    for (x, y, z), v in cells.items():
        b[idx(x, y, z)] = v
    g = fresh()
    g.state = State(tuple(b), 1, 11, None)
    r = g.step(1, "drop D4")
    assert r["placed"] == [3, 3, 3] and r["outcome"]["winner"] == 1
    assert g.winning_line() == ["A1 L1", "B2 L2", "C3 L3", "D4 L4"]


# A position with no lines in which 'twist row 1 right' makes lines for BOTH players (found by search).
BOTH = "OXO.OOXXXOX.XOXOO.O.XOXOX...XX......OXXO....OO.................."
# A position with no lines in which 'twist layer 1 cw' makes a line only for O.
ONLY_O = ".OOO.OOO.XXOO.O..OOO.XXX..OX..X..O....XX..X...X................."


@pytest.mark.parametrize("mover", [1, 2])
def test_twist_making_both_lines_is_won_by_the_twister_R11(mover):
    b = decode(BOTH)
    assert rules.line_for(b, 1) is None and rules.line_for(b, 2) is None
    nxt, res = rules.apply(State(b, mover, 20, None), rules.parse_action("twist row 1 right"))
    assert rules.line_for(nxt.board, 1) and rules.line_for(nxt.board, 2)
    assert res["winner"] == mover and res["reason"] == "connect_four"


def test_twist_making_only_the_opponents_line_loses_R11():
    b = decode(ONLY_O)
    assert rules.line_for(b, 1) is None and rules.line_for(b, 2) is None
    nxt, res = rules.apply(State(b, 1, 20, None), rules.parse_action("twist layer 1 cw"))  # X twists
    assert rules.line_for(nxt.board, 2) and not rules.line_for(nxt.board, 1)
    assert res["winner"] == 2


def test_turn_limit_draw_R12():
    g = fresh(["drop A1"])
    g.state = g.state._replace(turn=rules.TURN_LIMIT)          # turn 100 is the last one played
    r = g.step(2, "drop D4")
    assert r["outcome"]["reason"] == "turn_limit" and r["outcome"]["winner"] is None
    # but a win on turn 100 still counts
    g = fresh(["drop A1", "drop A2", "drop B1", "drop B2", "drop C1", "drop C2"])
    g.state = g.state._replace(turn=rules.TURN_LIMIT)
    assert g.step(1, "drop D1")["outcome"]["reason"] == "connect_four"


def test_no_legal_action_is_a_draw_R13(monkeypatch):
    g = fresh()
    monkeypatch.setattr(rules, "legal", lambda s: [])           # pretend the next player is stuck
    r = g.step(1, "drop A1")
    assert r["outcome"]["reason"] == "no_legal_actions" and r["outcome"]["winner"] is None


def test_opening_that_ends_the_game_is_rejected():
    with pytest.raises(ValueError):
        fresh(["drop A1", "drop A2", "drop B1", "drop B2", "drop C1", "drop C2", "drop D1"])


# ---- information boundary (R14) -------------------------------------------------------------------
def test_observation_is_a_copy_not_a_handle():
    g = fresh(["drop A1"])
    obs = g.observe(2)
    obs["board"][0][0][0] = 2
    obs["board"][1][1][0] = 2
    assert g.state.board[idx(0, 0, 0)] == 1 and g.state.board[idx(1, 1, 0)] == 0


def test_both_roles_see_the_same_board_and_legal_list_is_unranked():
    g = fresh(["drop A1", "drop B1", "twist layer 1 cw"])
    o1, o2 = g.observe(1), g.observe(2)
    assert o1["board"] == o2["board"] and o1["board_text"] == o2["board_text"]
    assert o1["last_action"] == "twist layer 1 cw"           # needed to know which twist is barred (R7)
    legal = g.legal_actions(2)
    assert legal == [a for a in ALL_ACTIONS if a in legal]    # fixed vocabulary order, no ranking
