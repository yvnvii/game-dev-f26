"""Model prompt versions (scripted, no live calls).

v1 is frozen: tests/data/prompt_v1_*.txt were written from build_prompt on 2026-11-08 *before* v2 was
added, so any byte change to v1 fails here. v2 (tuned on T1-T3 only) may only re-list the observed
board and add a generic checking routine; it must not evaluate or single out any action.
"""
import json
from pathlib import Path

import pytest

from c4d.engine import TwistFour
from c4d.model_player import CHECK_ROUTINE, ModelPlayer, board_listing, build_prompt

HERE = Path(__file__).resolve().parent
SUITE = {c["id"]: c for c in json.loads((HERE.parent / "suite.json").read_text())["cases"]}


def t3_position():
    """T3-twist-win, O to move (a tuning case; H1-twisted is never used for prompt work)."""
    g = TwistFour()
    g.reset(0, SUITE["T3-twist-win"]["opening"])
    return g, g.observe(2), g.legal_actions(2)


def test_v1_prompt_is_byte_for_byte_unchanged_and_still_the_default():
    g, obs, legal = t3_position()
    gold = (HERE / "data" / "prompt_v1_T3_O.txt").read_text()
    assert build_prompt(obs, legal, None, None) == gold
    assert build_prompt(obs, legal, None, None, "v1") == gold
    gold_hf = (HERE / "data" / "prompt_v1_T3_O_history_feedback.txt").read_text()
    assert build_prompt(obs, legal, [t for _, t in g.history], "shaft A1 is full") == gold_hf


def test_v2_lists_every_shaft_bottom_to_top_and_both_sides_pieces():
    # T3 board, checked by hand against the layer grids: L1 has O at A1 D1 B2 C3 and X at C1 A3 D4;
    # L2 has X at A1. B2 holds an O (v1 trial: the model called it "empty").
    _, obs, legal = t3_position()
    expected = [
        "Shafts (bottom to top):",
        "A1: O X", "B1: empty", "C1: X", "D1: O",
        "A2: empty", "B2: O", "C2: empty", "D2: empty",
        "A3: X", "B3: empty", "C3: O", "D3: empty",
        "A4: empty", "B4: empty", "C4: empty", "D4: X",
        "Your pieces: A1 L1, D1 L1, B2 L1, C3 L1",
        "Opponent's pieces: A1 L2, C1 L1, A3 L1, D4 L1",
    ]
    assert board_listing(obs) == expected
    p = build_prompt(obs, legal, None, None, "v2")
    assert obs["board_text"] + "\n\n" + "\n".join(expected) + "\n\nLegal actions: " in p
    assert p.index(CHECK_ROUTINE) < p.index("MOVE: <one legal action")


def test_v2_piece_lists_follow_the_observer():
    g, _, _ = t3_position()
    as_x = board_listing(g.observe(1))
    assert as_x[-2] == "Your pieces: A1 L2, C1 L1, A3 L1, D4 L1"
    assert as_x[-1] == "Opponent's pieces: A1 L1, D1 L1, B2 L1, C3 L1"
    empty = TwistFour()
    assert board_listing(empty.observe(1))[-2:] == ["Your pieces: none", "Opponent's pieces: none"]


@pytest.mark.parametrize("history,feedback", [(None, None), (["drop D1"], "shaft A1 is full")])
def test_v2_adds_only_the_listing_and_routine_with_no_per_action_annotations(history, feedback):
    """No answer key: v2 = v1 + board_listing + CHECK_ROUTINE, and no added line names an action."""
    _, obs, legal = t3_position()
    v1 = build_prompt(obs, legal, history, feedback).split("\n")
    v2 = build_prompt(obs, legal, history, feedback, "v2").split("\n")
    assert [l for l in v2 if l not in v1] == board_listing(obs) + [CHECK_ROUTINE]
    # cutting the two added blocks (each with its blank separator) out of v2 gives v1 exactly
    listing = board_listing(obs) + [""]
    i = v2.index(listing[0])
    rest = v2[:i] + v2[i + len(listing):]
    j = rest.index(CHECK_ROUTINE)
    assert rest[:j - 1] + rest[j + 1:] == v1
    legal_line = "Legal actions: " + ", ".join(legal)
    assert legal_line in v2                                 # the action list itself is untouched
    for line in board_listing(obs) + [CHECK_ROUTINE]:
        assert not any(a in line for a in legal), line      # e.g. "twist col D fwd" never appears
    for word in ("score", "threat:", "winning move", "best", "recommended"):
        assert word not in " ".join(board_listing(obs) + [CHECK_ROUTINE]).lower()


def test_model_player_records_prompt_version_in_its_name():
    assert ModelPlayer().name == "model:gemini-3.5-flash-lite:none:v1"
    p = ModelPlayer(prompt_version="v2")
    assert p.prompt_version == "v2" and p.name == "model:gemini-3.5-flash-lite:none:v2"
    with pytest.raises(ValueError):
        ModelPlayer(prompt_version="v3")


def test_model_reply_is_logged_in_full_not_cut_to_600_chars(monkeypatch, tmp_path):
    """Logging change 2026-11-08: traces keep the whole reply (earlier runs kept the last 600 chars).
    The client and SDK module are stubs: no live call, no google-genai needed in CI."""
    import sys
    import types as pytypes

    from c4d.players import GreedyPlayer
    from c4d.runner import Limits, run_episode

    fake_types = pytypes.SimpleNamespace(GenerateContentConfig=lambda **kw: kw)
    genai = pytypes.ModuleType("google.genai"); genai.types = fake_types
    monkeypatch.setitem(sys.modules, "google", pytypes.ModuleType("google"))
    monkeypatch.setitem(sys.modules, "google.genai", genai)
    monkeypatch.setitem(sys.modules, "google.genai.types", fake_types)

    reply = "Checking twists first. " + "x" * 2000 + "\nMOVE: drop B2"
    resp = pytypes.SimpleNamespace(text=reply, usage_metadata=None, candidates=[], model_version="stub")
    player = ModelPlayer(prompt_version="v2")
    player._client = pytypes.SimpleNamespace(
        models=pytypes.SimpleNamespace(generate_content=lambda **kw: resp))

    trace = tmp_path / "t.jsonl"
    run_episode({1: player, 2: GreedyPlayer(0)}, seed=0, limits=Limits(step_limit=1), trace_path=str(trace))
    moves = [json.loads(l) for l in trace.read_text().splitlines()]
    moves = [e for e in moves if e.get("type") == "move" and e.get("source") == "model"]
    assert moves[0]["action"] == "drop B2" and moves[0]["raw"] == reply
