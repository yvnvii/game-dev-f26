"""Rule invariants, legal/illegal actions, terminal outcomes, and the information boundary."""
import itertools

from c4d.engine import ALL_ACTIONS, LINES, SIZE, Connect3D


def fresh(opening=()):
    g = Connect3D()
    g.reset(0, list(opening))
    return g


# ---- rule invariants ----------------------------------------------------------
def test_cube_has_76_winning_lines_each_of_four_distinct_collinear_cells():
    assert len(LINES) == 76
    for ln in LINES:
        assert len(set(ln)) == 4
        d = [ln[1][i] - ln[0][i] for i in range(3)]
        for k in range(4):
            assert all(ln[k][i] == ln[0][i] + k * d[i] for i in range(3))


def test_initial_state():
    g = fresh()
    assert g.to_move == 1
    assert all(g.board[x][y][z] == 0 for x, y, z in itertools.product(range(SIZE), repeat=3))
    assert g.legal_actions(1) == ALL_ACTIONS and len(ALL_ACTIONS) == 16
    assert g.outcome()["status"] == "ongoing"


def test_gravity_pieces_stack_from_the_bottom():
    g = fresh()
    assert g.step(1, "B2")["placed"] == [1, 1, 0]
    assert g.step(2, "B2")["placed"] == [1, 1, 1]
    assert g.step(1, "b2")["placed"] == [1, 1, 2]  # case-insensitive


def test_no_floating_pieces_and_turns_alternate_through_random_play():
    import random
    rng = random.Random(7)
    for _ in range(30):
        g = fresh()
        expected = 1
        while g.outcome()["status"] == "ongoing":
            assert g.to_move == expected
            g.step(g.to_move, rng.choice(g.legal_actions(g.to_move)))
            expected = 3 - expected
            for x, y in itertools.product(range(SIZE), repeat=2):
                col = g.board[x][y]
                assert all(col[z] != 0 for z in range(g.height(x, y)))     # filled below
                assert all(col[z] == 0 for z in range(g.height(x, y), SIZE))  # empty above
        counts = [sum(v == p for plane in g.board for col in plane for v in col) for p in (1, 2)]
        assert counts[0] - counts[1] in (0, 1)


# ---- legal and illegal actions ------------------------------------------------
def test_full_shaft_is_not_legal_and_is_rejected():
    g = fresh(["A1", "A1", "A1", "A1"])
    assert "A1" not in g.legal_actions(1)
    r = g.step(1, "A1")
    assert not r["ok"] and "full" in r["error"]
    assert g.to_move == 1 and len(g.history) == 4  # nothing changed


def test_malformed_and_out_of_turn_actions_are_rejected_without_state_change():
    g = fresh()
    for bad in ["E1", "A5", "A0", "", "drop A1", None, "A11"]:
        r = g.step(1, bad)
        assert not r["ok"], bad
    r = g.step(2, "A1")
    assert not r["ok"] and "not your turn" in r["error"]
    assert g.legal_actions(2) == []
    assert g.history == []


# ---- terminal outcomes --------------------------------------------------------
def test_horizontal_win_on_bottom_layer():
    g = fresh(["A1", "A2", "B1", "B2", "C1", "C2"])
    r = g.step(1, "D1")
    assert r["outcome"] == {"status": "terminal", "reason": "connect_four", "winner": 1,
                            "score": {1: 1, 2: -1}}
    assert g.legal_actions(1) == [] and g.legal_actions(2) == []
    assert not g.step(2, "D2")["ok"]


def test_vertical_win_in_one_shaft():
    g = fresh(["C3", "A1", "C3", "A1", "C3", "A1"])
    assert g.step(1, "C3")["outcome"]["winner"] == 1


def _load(g, cells, to_move, n_moves):
    """Set up a position directly (test-only), bypassing move-by-move play."""
    for (x, y, z), v in cells.items():
        g.board[x][y][z] = v
    g.history = [(0, "setup")] * n_moves
    g.to_move = to_move


def test_space_diagonal_win_across_all_four_layers():
    # X on (0,0,0) (1,1,1) (2,2,2); supports below them; X completes (3,3,3) by dropping in D4.
    g = fresh()
    _load(g, {(0, 0, 0): 1,
              (1, 1, 0): 2, (1, 1, 1): 1,
              (2, 2, 0): 2, (2, 2, 1): 2, (2, 2, 2): 1,
              (3, 3, 0): 1, (3, 3, 1): 2, (3, 3, 2): 1,
              (3, 0, 0): 2}, to_move=1, n_moves=10)
    r = g.step(1, "D4")
    assert r["placed"] == [3, 3, 3]
    assert r["outcome"]["reason"] == "connect_four" and r["outcome"]["winner"] == 1


# A full 4x4x4 board with no line of four (found by local search; 32 X, 32 O).
# Order: z-major, then y, then x.
DRAWN = "XXOOOOOXXOOXXOXOXXOXXOOOXXXOOOXXOOXOOXXXOXXOXXOOXXOOOXOXOXOOXOXX"


def test_full_board_without_line_is_draw():
    cells = {}
    i = 0
    for z in range(SIZE):
        for y in range(SIZE):
            for x in range(SIZE):
                cells[(x, y, z)] = 1 if DRAWN[i] == "X" else 2
                i += 1
    assert not any(len({cells[c] for c in ln}) == 1 for ln in LINES)
    last = (3, 3, 3)
    mover = cells.pop(last)
    g = fresh()
    _load(g, cells, to_move=mover, n_moves=63)
    r = g.step(mover, "D4")
    assert r["ok"] and r["outcome"]["status"] == "terminal"
    assert r["outcome"]["reason"] == "board_full" and r["outcome"]["winner"] is None


# ---- information boundary -----------------------------------------------------
def test_observation_is_a_copy_not_a_handle_to_authoritative_state():
    g = fresh(["A1"])
    obs = g.observe(2)
    obs["board"][0][0][0] = 2
    obs["board"][1][1][0] = 2
    assert g.board[0][0][0] == 1 and g.board[1][1][0] == 0


def test_fully_observed_both_roles_see_same_board_and_legal_list_has_no_ranking():
    g = fresh(["A1", "B1", "C1"])
    o1, o2 = g.observe(1), g.observe(2)
    assert o1["board"] == o2["board"] and o1["board_text"] == o2["board_text"]
    # legal list is the fixed shaft order filtered by "not full": it carries no hint of quality
    legal = g.legal_actions(2)
    assert legal == [a for a in ALL_ACTIONS if a in legal]
