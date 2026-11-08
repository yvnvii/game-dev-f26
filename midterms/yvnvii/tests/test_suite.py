"""The declared suite (suite.json) still describes real positions under the current rules (review finding 5)."""
import json
from pathlib import Path

import pytest

from c4d import rules
from c4d.engine import TwistFour

SUITE = json.loads((Path(__file__).resolve().parent.parent / "suite.json").read_text())
CASES = {c["id"]: c for c in SUITE["cases"]}


def position(case_id):
    g = TwistFour()
    g.reset(0, CASES[case_id]["opening"])   # raises on an illegal opening or one that ends the game
    return g


def immediate_wins(g):
    """Action texts that win at once for the side to move (drops and twists, R10/R11)."""
    p = g.to_move
    return [rules.action_text(a) for a, _, res in rules.children(g.state) if res and res["winner"] == p]


@pytest.mark.parametrize("case_id", sorted(CASES))
def test_every_suite_opening_replays_legally_and_leaves_the_game_ongoing(case_id):
    g = position(case_id)
    assert len(g.history) == len(CASES[case_id]["opening"])
    assert g.outcome()["status"] == "ongoing"


def test_T3_side_to_move_has_exactly_one_immediate_win_and_it_is_a_twist():
    g = position("T3-twist-win")
    assert g.to_move == 2                                  # O, as suite.json states
    assert immediate_wins(g) == ["twist col D fwd"]


@pytest.mark.parametrize("case_id", ["T2-centre", "H1-twisted"])
def test_side_to_move_has_no_immediate_win(case_id):
    assert immediate_wins(position(case_id)) == []
