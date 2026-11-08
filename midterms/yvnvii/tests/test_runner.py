"""Episode limits and model-player handling, using scripted (mocked) model outputs only."""
import time

from c4d.players import GreedyPlayer, MinimaxPlayer, RandomPlayer, ScriptedPlayer
from c4d.runner import Limits, run_episode
from c4d.model_player import build_prompt, parse_move
from c4d.engine import Connect3D


def moves_by(result, source):
    return [e for e in result["events"] if e["type"] == "move" and e["source"] == source]


# ---- terminal outcome through the runner -------------------------------------
def test_baseline_vs_random_reaches_a_terminal_outcome():
    r = run_episode({1: MinimaxPlayer(2, 0), 2: RandomPlayer(0)}, seed=0)
    assert r["outcome"]["status"] == "terminal"
    assert r["outcome"]["reason"] in ("connect_four", "board_full")
    assert r["events"][-1]["type"] == "end"


def test_scripted_model_wins_on_bottom_row():
    model = ScriptedPlayer(["A1", "B1", "C1", "D1"])
    r = run_episode({1: model, 2: ScriptedPlayer(["A2", "B2", "C2"])}, seed=0)
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
        return {"action": "A1"}
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

    model = Spy(["Z9", "I think...", "B2"])
    r = run_episode({1: model, 2: GreedyPlayer(0)}, seed=0,
                    limits=Limits(max_attempts_per_turn=2, step_limit=3))
    st = r["players"][1]
    assert st["illegal_attempts"] == 2 and st["fallback_moves"] == 1
    assert seen_feedback[0] is None and seen_feedback[1] is not None   # retry got the reason
    assert moves_by(r, "model")[0]["action"] == "B2"                     # next turn: model move


def test_episode_timeout():
    def slow(obs, legal):
        time.sleep(0.1)
        return {"action": legal[0]}
    r = run_episode({1: ScriptedPlayer([slow] * 40), 2: RandomPlayer(0)}, seed=0,
                    limits=Limits(episode_timeout_s=0.15))
    assert r["outcome"]["reason"] == "episode_timeout"


# ---- model I/O: parsing and prompt boundary -------------------------------------
def test_parse_move_takes_last_move_line():
    assert parse_move("maybe MOVE: A1 ... no wait.\nMOVE: c4") == "C4"
    assert parse_move("I pick B2") is None


def test_prompt_contains_only_observation_and_legal_moves():
    g = Connect3D()
    g.reset(0, ["A1", "B1"])
    obs = g.observe(1)
    p = build_prompt(obs, g.legal_actions(1), None, None)
    assert obs["board_text"] in p
    assert "Legal moves: " + ", ".join(g.legal_actions(1)) in p
    # no search scores, no engine internals
    assert "search_value" not in p and "_terminal" not in p


def test_truncated_reply_without_move_line_is_illegal_and_traced_with_finish_reason():
    """From run results/model-vs-greedy (2026-11-08): 27 of 41 illegal attempts were replies cut off
    at max_output_tokens before the MOVE line. Such a reply must count as one illegal attempt, its
    trace event must carry finish_reason MAX_TOKENS, and the model's retry must still be accepted."""
    def truncated(obs, legal):
        return {"action": None, "raw": "Looking at the centre shafts, B2 would block the",
                "finish_reason": "MAX_TOKENS", "input_tokens": 0, "output_tokens": 0}

    def valid(obs, legal):
        return {"action": "B2", "raw": "MOVE: B2", "finish_reason": "STOP",
                "input_tokens": 0, "output_tokens": 0}

    r = run_episode({1: ScriptedPlayer([truncated, valid]), 2: GreedyPlayer(0)}, seed=0,
                    limits=Limits(max_attempts_per_turn=2, step_limit=1))
    st = r["players"][1]
    assert st["illegal_attempts"] == 1 and st["fallback_moves"] == 0
    illegal = [e for e in r["events"] if e["type"] == "illegal"]
    assert len(illegal) == 1 and illegal[0]["finish_reason"] == "MAX_TOKENS"
    accepted = moves_by(r, "model")
    assert len(accepted) == 1 and accepted[0]["action"] == "B2"
    assert accepted[0]["finish_reason"] == "STOP"
