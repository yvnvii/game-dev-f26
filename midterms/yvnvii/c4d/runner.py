"""Episode runner. Holds the authoritative game and enforces every limit in code:

- step limit (accepted moves)                         -> terminal reason "step_limit"
- model-call limit per model player (failed calls count) -> terminal reason "call_limit"
- per-call timeout                                     -> the call counts as failed
- episode wall-clock timeout                           -> terminal reason "episode_timeout"
- invalid actions: the model gets `max_attempts_per_turn` tries (with the rejection reason
  as feedback); after that the runner plays a labeled FALLBACK move (first legal shaft in
  centre-first order). Fallbacks are never counted as model moves.
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import time
from dataclasses import asdict, dataclass, field

from .engine import Connect3D
from .players import _center_order


@dataclass
class Limits:
    step_limit: int = 64              # a 4x4x4 board is full after 64 moves
    call_limit: int = 48              # per model player, failed calls included
    call_timeout_s: float = 60.0
    episode_timeout_s: float = 1800.0
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
    game = Connect3D()
    game.reset(seed, list(opening))
    stats = {p: PlayerStats(name=players[p].name) for p in (1, 2)}
    events = []
    t_start = time.monotonic()

    def log(ev):
        events.append(ev)
        if verbose:
            print(json.dumps(ev))

    log({"type": "start", "case": case_id, "seed": seed, "opening": list(opening),
         "players": {p: players[p].name for p in (1, 2)}, "limits": asdict(limits), **(meta or {})})
    steps = 0

    while game.outcome()["status"] == "ongoing":
        if steps >= limits.step_limit:
            game.force_end("step_limit")
            break
        if time.monotonic() - t_start > limits.episode_timeout_s:
            game.force_end("episode_timeout")
            break
        p = game.to_move
        player, st = players[p], stats[p]
        obs = game.observe(p)
        legal = game.legal_actions(p)
        history = [a for _, a in game.history]

        if not player.is_model:
            t0 = time.monotonic()
            res = player.choose(obs, legal, history=history)
            st.latencies.append(time.monotonic() - t0)
            r = game.step(p, res["action"])
            if not r["ok"]:  # should never happen for scripted baselines; treat as a bug
                raise RuntimeError(f"{player.name} played illegal move {res['action']}: {r['error']}")
            st.moves += 1
            steps += 1
            log({"type": "move", "n": steps, "player": p, "source": "baseline", "action": r["action"],
                 "placed": r["placed"], **{k: v for k, v in res.items() if k in ("search_value", "nodes")}})
            continue

        # ---- model player ----------------------------------------------------
        feedback, accepted, attempts, out_of_budget = None, False, 0, False
        while attempts < limits.max_attempts_per_turn:
            if st.calls >= limits.call_limit:
                out_of_budget = True
                break
            st.calls += 1
            attempts += 1
            fb = feedback
            try:
                res = _call_with_timeout(lambda: player.choose(obs, legal, feedback=fb, history=history),
                                         limits.call_timeout_s)
            except cf.TimeoutError:
                st.failed_calls += 1
                log({"type": "call_failed", "player": p, "error": "timeout"})
                feedback = None
                continue
            except Exception as e:  # API error, network, quota...
                st.failed_calls += 1
                log({"type": "call_failed", "player": p, "error": f"{type(e).__name__}: {e}"[:300]})
                feedback = None
                continue
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
                 "raw": res.get("raw"), "finish_reason": res.get("finish_reason")})
            break

        if accepted:
            continue
        if out_of_budget:
            game.force_end("call_limit")
            break
        fb_action = _center_order(legal)[0]
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
                        "mean_latency_s": (round(sum(stats[p].latencies) / len(stats[p].latencies), 3)
                                           if stats[p].latencies else None)} for p in (1, 2)},
        "final_board": game.render(),
    }
    log({"type": "end", **{k: result[k] for k in ("outcome", "steps", "wall_s", "players")}})
    if trace_path:
        with open(trace_path, "w") as f:
            for ev in events:
                f.write(json.dumps(ev) + "\n")
    result["events"] = events
    return result
