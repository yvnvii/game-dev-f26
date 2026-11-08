"""Episode limits and model-player handling, using scripted (mocked) model outputs only."""
import time

from c4d.players import GreedyPlayer, MinimaxPlayer, RandomPlayer, ScriptedPlayer
from c4d.runner import Limits, run_episode
from c4d.model_player import build_prompt, parse_move
from c4d.engine import TwistFour


def moves_by(result, source):
    return [e for e in result["events"] if e["type"] == "move" and e["source"] == source]


# ---- terminal outcome through the runner -------------------------------------
def test_baseline_vs_random_reaches_a_terminal_outcome():
    r = run_episode({1: MinimaxPlayer(2, 0), 2: RandomPlayer(0)}, seed=0)
    assert r["outcome"]["status"] == "terminal"
    assert r["outcome"]["reason"] in ("connect_four", "turn_limit", "no_legal_actions")
    assert r["events"][-1]["type"] == "end"


def test_scripted_model_wins_on_bottom_row():
    model = ScriptedPlayer(["drop A1", "drop B1", "drop C1", "drop D1"])
    r = run_episode({1: model, 2: ScriptedPlayer(["drop A2", "drop B2", "drop C2"])}, seed=0)
    assert r["outcome"]["winner"] == 1 and r["outcome"]["reason"] == "connect_four"
    assert len(moves_by(r, "model")) == 7


# ---- episode limits ------------------------------------------------------------
def test_step_limit_ends_episode_with_explicit_reason():
    r = run_episode({1: RandomPlayer(1), 2: RandomPlayer(2)}, seed=0, limits=Limits(step_limit=5))
    assert r["steps"] == 5
    assert r["outcome"] == {"status": "terminal", "reason": "step_limit", "winner": None,
                            "score": {1: 0, 2: 0}}


def test_call_limit_counts_failed_calls_and_ends_episode():
    boom = [RuntimeError("API down")] * 10
    r = run_episode({1: ScriptedPlayer(boom), 2: GreedyPlayer(0)}, seed=0,
                    limits=Limits(call_limit=3, max_attempts_per_turn=2))
    st = r["players"][1]
    assert st["calls"] == 3 and st["failed_calls"] == 3
    assert r["outcome"]["reason"] == "call_limit"


def test_timeout_counts_as_failed_call_then_fallback_is_labeled():
    def slow(obs, legal):
        time.sleep(0.5)
        return {"action": "drop A1"}
    r = run_episode({1: ScriptedPlayer([slow, slow]), 2: GreedyPlayer(0)}, seed=0,
                    limits=Limits(call_timeout_s=0.05, max_attempts_per_turn=2, step_limit=2))
    st = r["players"][1]
    assert st["failed_calls"] == 2 and st["moves"] == 0 and st["fallback_moves"] == 1
    fb = moves_by(r, "fallback")
    assert len(fb) == 1 and fb[0]["player"] == 1
    assert moves_by(r, "model") == []          # a fallback is never reported as a model move


def test_illegal_actions_are_counted_retried_with_feedback_then_fallback():
    seen_feedback = []

    class Spy(ScriptedPlayer):
        def choose(self, obs, legal, feedback=None, history=None):
            seen_feedback.append(feedback)
            return super().choose(obs, legal, feedback, history)

    model = Spy(["drop Z9", "I think...", "drop B2"])
    r = run_episode({1: model, 2: GreedyPlayer(0)}, seed=0,
                    limits=Limits(max_attempts_per_turn=2, step_limit=3))
    st = r["players"][1]
    assert st["illegal_attempts"] == 2 and st["fallback_moves"] == 1
    assert seen_feedback[0] is None and seen_feedback[1] is not None   # retry got the reason
    assert moves_by(r, "model")[0]["action"] == "drop B2"                # next turn: model move


def test_episode_timeout():
    def slow(obs, legal):
        time.sleep(0.1)
        return {"action": legal[0]}
    r = run_episode({1: ScriptedPlayer([slow] * 40), 2: RandomPlayer(0)}, seed=0,
                    limits=Limits(episode_timeout_s=0.15))
    assert r["outcome"]["reason"] == "episode_timeout"


# ---- model I/O: parsing and prompt boundary -------------------------------------
def test_parse_move_takes_last_move_line():
    assert parse_move("maybe MOVE: drop A1\n... no wait.\nMOVE: twist col B fwd") == "twist col B fwd"
    assert parse_move("**MOVE:** `drop C2`.") == "drop C2"
    assert parse_move("I pick B2") is None


def test_prompt_contains_only_observation_and_legal_moves():
    g = TwistFour()
    g.reset(0, ["drop A1", "drop B1", "twist layer 1 cw"])
    obs = g.observe(2)
    p = build_prompt(obs, g.legal_actions(2), None, None)
    assert obs["board_text"] in p
    assert "Legal actions: " + ", ".join(g.legal_actions(2)) in p
    assert 'X played "twist layer 1 cw"' in p           # the model can see which twist R7 bars
    # no search scores, no engine internals
    assert "search_value" not in p and "_terminal" not in p


def test_cut_off_model_reply_is_counted_illegal_and_labeled():
    """Observed 2026-11-08 (run model-vs-greedy): with a 1024-token output limit, 27 Gemini replies
    stopped mid-reasoning before their MOVE line. Such replies must count as illegal attempts, and the
    trace must say they were cut off (finish_reason MAX_TOKENS), so they can't be mistaken for
    replies that merely ignored the format."""
    cut = lambda obs, legal: {"action": None, "raw": "Let's trace B2 heights: z=1 X, z=2", "finish_reason": "MAX_TOKENS"}
    r = run_episode({1: ScriptedPlayer([cut, "drop B2"]), 2: GreedyPlayer(0)}, seed=0,
                    limits=Limits(max_attempts_per_turn=2, step_limit=1))
    ill = [e for e in r["events"] if e["type"] == "illegal"]
    assert len(ill) == 1 and ill[0]["finish_reason"] == "MAX_TOKENS"
    assert r["players"][1]["illegal_attempts"] == 1
    assert moves_by(r, "model")[0]["action"] == "drop B2"


def test_model_twist_is_accepted_and_a_barred_twist_gets_the_rule_as_feedback():
    """A twist is an ordinary model action; an instant undo (R7) is rejected with the reason."""
    seen = []

    class Spy(ScriptedPlayer):
        def choose(self, obs, legal, feedback=None, history=None):
            seen.append(feedback)
            return super().choose(obs, legal, feedback, history)

    x = Spy(["drop A1", "drop A1", "twist layer 1 ccw", "drop D4"])
    o = ScriptedPlayer(["drop B1", "twist layer 1 cw", "drop C4"])
    r = run_episode({1: x, 2: o}, seed=0, limits=Limits(step_limit=5))
    model_moves = [e["action"] for e in r["events"] if e["type"] == "move" and e["player"] == 2]
    assert "twist layer 1 cw" in model_moves
    ill = [e for e in r["events"] if e["type"] == "illegal"]
    assert ill and "R7" in ill[0]["reason"] and "R7" in seen[3]


def test_fallback_uses_a_legal_drop_and_is_never_a_model_move():
    r = run_episode({1: ScriptedPlayer(["nonsense", "more nonsense"]), 2: GreedyPlayer(0)}, seed=0,
                    limits=Limits(max_attempts_per_turn=2, step_limit=1))
    fb = moves_by(r, "fallback")
    assert len(fb) == 1 and fb[0]["action"] == "drop B2"        # most central drop on an empty board
    assert r["players"][1]["moves"] == 0 and r["players"][1]["fallback_moves"] == 1
