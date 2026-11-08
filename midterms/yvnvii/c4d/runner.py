"""Episode runner. Holds the authoritative game and enforces every limit in code:

Rule E1 (RULES.md "Episode limits", decided 2026-11-08):
- per-player clock: thinking time inside that player's choose() calls, retries included
                                                       -> that player LOSES, reason "timeout"
  (a move returned after the clock ran out is discarded; model calls are cut at the time left)
- model-call limit per model player (failed calls count) -> that player LOSES, reason "call_limit"
- per-call timeout (60 s, or less if the clock has less) -> the call counts as failed
- step limit (accepted moves), a backstop              -> no winner, reason "step_limit"
- invalid actions: the model gets `max_attempts_per_turn` tries (with the rejection reason
  as feedback); after that the runner plays a labeled FALLBACK move (first legal shaft in
  centre-first order, else the first legal action). Fallbacks are never counted as model moves.
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import time
from dataclasses import asdict, dataclass, field

from .engine import TwistFour
from .players import fallback_action


@dataclass
class Limits:
    step_limit: int = 100             # backstop; the rules already end the game after 100 turns (R12)
    call_limit: int = 110             # per model player, failed calls included (~50 own turns x 2 attempts + margin)
    call_timeout_s: float = 60.0
    clock_s: float = 900.0            # per player, whole episode (E1); blame goes to whoever used the time
    max_attempts_per_turn: int = 2


@dataclass
class PlayerStats:
    name: str
    moves: int = 0             # moves the player itself chose and the engine accepted
    fallback_moves: int = 0    # moves the runner substituted
    calls: int = 0             # model calls attempted (incl. failed)
    failed_calls: int = 0      # timeouts / API errors
    illegal_attempts: int = 0  # unparseable or rejected actions
    input_tokens: int = 0
    output_tokens: int = 0
    clock_used_s: float = 0.0  # time inside this player's choose() calls (E1)
    latencies: list = field(default_factory=list)


def _call_with_timeout(fn, timeout):
    ex = cf.ThreadPoolExecutor(max_workers=1)
    fut = ex.submit(fn)
    try:
        return fut.result(timeout=timeout)
    finally:
        ex.shutdown(wait=False, cancel_futures=True)


def run_episode(players: dict, opening=(), seed: int = 0, limits: Limits | None = None,
                case_id: str = "", trace_path: str | None = None, verbose: bool = False,
                meta: dict | None = None) -> dict:
    limits = limits or Limits()
    game = TwistFour()
    game.reset(seed, list(opening))
    stats = {p: PlayerStats(name=players[p].name) for p in (1, 2)}
    events = []
    t_start = time.monotonic()

    def log(ev):
        events.append(ev)
        if verbose:
            print(json.dumps(ev))

    def lose(p, reason):
        """E1: a limit ending is a loss for the player who hit it."""
        log({"type": "limit", "player": p, "reason": reason,
             "clock_used_s": round(stats[p].clock_used_s, 3)})
        game.force_end(reason, winner=3 - p)

    log({"type": "start", "case": case_id, "seed": seed, "opening": list(opening),
         "players": {p: players[p].name for p in (1, 2)}, "limits": asdict(limits), **(meta or {})})
    steps = 0

    while game.outcome()["status"] == "ongoing":
        if steps >= limits.step_limit:
            game.force_end("step_limit")
            break
        p = game.to_move
        player, st = players[p], stats[p]
        obs = game.observe(p)
        legal = game.legal_actions(p)
        history = [a for _, a in game.history]

        if not player.is_model:
            # Baseline/human calls can't be interrupted, so the clock is checked when they return.
            t0 = time.monotonic()
            res = player.choose(obs, legal, history=history)
            dt = time.monotonic() - t0
            st.latencies.append(dt)
            st.clock_used_s += dt
            if st.clock_used_s >= limits.clock_s:     # late move is discarded, even a winning one
                lose(p, "timeout")
                break
            r = game.step(p, res["action"])
            if not r["ok"]:  # should never happen for scripted baselines; treat as a bug
                raise RuntimeError(f"{player.name} played illegal move {res['action']}: {r['error']}")
            st.moves += 1
            steps += 1
            log({"type": "move", "n": steps, "player": p, "source": "baseline", "action": r["action"],
                 "placed": r["placed"], **{k: v for k, v in res.items() if k in ("search_value", "nodes")}})
            continue

        # ---- model player ----------------------------------------------------
        feedback, accepted, attempts, forfeit = None, False, 0, None
        while attempts < limits.max_attempts_per_turn:
            if st.calls >= limits.call_limit:
                forfeit = "call_limit"
                break
            left = limits.clock_s - st.clock_used_s
            if left <= 0:
                forfeit = "timeout"
                break
            capped = left < limits.call_timeout_s     # the clock, not the 60 s limit, cuts this call
            st.calls += 1
            attempts += 1
            fb = feedback
            t0 = time.monotonic()
            try:
                res = _call_with_timeout(lambda: player.choose(obs, legal, feedback=fb, history=history),
                                         min(limits.call_timeout_s, left))
            except cf.TimeoutError:
                st.clock_used_s += time.monotonic() - t0
                st.failed_calls += 1
                log({"type": "call_failed", "player": p, "error": "timeout"})
                if capped:   # timer granularity can leave a hair of clock; the call was cut because time was up
                    st.clock_used_s = max(st.clock_used_s, limits.clock_s)
                    forfeit = "timeout"
                    break
                feedback = None
                continue
            except Exception as e:  # API error, network, quota...
                st.clock_used_s += time.monotonic() - t0
                st.failed_calls += 1
                log({"type": "call_failed", "player": p, "error": f"{type(e).__name__}: {e}"[:300]})
                feedback = None
                continue
            st.clock_used_s += time.monotonic() - t0
            if st.clock_used_s >= limits.clock_s:     # reply arrived after the clock ran out: discarded
                forfeit = "timeout"
                break
            st.input_tokens += res.get("input_tokens", 0) or 0
            st.output_tokens += res.get("output_tokens", 0) or 0
            if "latency_s" in res:
                st.latencies.append(res["latency_s"])
            action = res.get("action")
            if action is None:
                st.illegal_attempts += 1
                feedback = "no line of the form 'MOVE: <shaft>' was found"
                log({"type": "illegal", "player": p, "reason": feedback, "raw": res.get("raw"),
                     "finish_reason": res.get("finish_reason")})
                continue
            r = game.step(p, action)
            if not r["ok"]:
                st.illegal_attempts += 1
                feedback = f"{action}: {r['error']}"
                log({"type": "illegal", "player": p, "action": action, "reason": r["error"],
                     "finish_reason": res.get("finish_reason")})
                continue
            accepted = True
            st.moves += 1
            steps += 1
            log({"type": "move", "n": steps, "player": p, "source": "model", "action": r["action"],
                 "placed": r["placed"], "latency_s": res.get("latency_s"),
                 "input_tokens": res.get("input_tokens"), "output_tokens": res.get("output_tokens"),
                 "finish_reason": res.get("finish_reason"), "raw": res.get("raw")})
            break

        if accepted:
            continue
        if forfeit:
            lose(p, forfeit)
            break
        fb_action = fallback_action(legal)
        r = game.step(p, fb_action)
        st.fallback_moves += 1
        steps += 1
        log({"type": "move", "n": steps, "player": p, "source": "fallback", "action": r["action"],
             "placed": r["placed"]})

    out = game.outcome()
    result = {
        "case": case_id, "seed": seed, "outcome": out, "steps": steps,
        "wall_s": round(time.monotonic() - t_start, 2),
        "players": {p: {**asdict(stats[p]), "latencies": None,
                        "clock_used_s": round(stats[p].clock_used_s, 3),
                        "mean_latency_s": (round(sum(stats[p].latencies) / len(stats[p].latencies), 3)
                                           if stats[p].latencies else None)} for p in (1, 2)},
        "final_board": game.render(),
        "winning_line": game.winning_line(),
        "clock_used_s": {p: round(stats[p].clock_used_s, 3) for p in (1, 2)},
    }
    log({"type": "end", **{k: result[k] for k in ("outcome", "winning_line", "steps", "wall_s",
                                               "clock_used_s", "players")}})
    if trace_path:
        with open(trace_path, "w") as f:
            for ev in events:
                f.write(json.dumps(ev) + "\n")
    result["events"] = events
    return result
