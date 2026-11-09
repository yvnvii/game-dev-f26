"""Run one candidate player against one opponent on the declared suite.

Each case is played twice: candidate as X (player 1) and candidate as O (player 2).
Writes one JSONL trace per episode and a summary.json under results/<run-name>/.

Examples (run from midterms/yvnvii/):
  python scripts/evaluate.py --candidate minimax --opponent greedy --run baseline-vs-greedy
  python scripts/evaluate.py --candidate model --opponent greedy --run model-vs-greedy
  python scripts/evaluate.py --candidate model --opponent minimax --run model-vs-minimax --cases S1-empty
  python scripts/evaluate.py --candidate model --history moves --opponent greedy --run model-hist-vs-greedy
  python scripts/evaluate.py --candidate model --prompt v2 --cases tuning --opponent greedy --run model-v2-vs-greedy
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import zlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from c4d.players import GreedyPlayer, MinimaxPlayer, RandomPlayer  # noqa: E402
from c4d.runner import Limits, run_episode  # noqa: E402


def make_player(kind, seed, args):
    if kind == "minimax":
        return MinimaxPlayer(depth=args.depth, seed=seed)
    if kind == "greedy":
        return GreedyPlayer(seed=seed)
    if kind == "random":
        return RandomPlayer(seed=seed)
    if kind == "model":
        from c4d.model_player import ModelPlayer
        return ModelPlayer(model=args.model, history_mode=args.history,
                           prompt_version=args.prompt, max_output_tokens=args.max_output_tokens)
    raise SystemExit(f"unknown player kind {kind}")


def git_version():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True,
                                       stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "unknown"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", required=True, choices=["model", "minimax", "greedy", "random"])
    ap.add_argument("--opponent", default="greedy", choices=["model", "minimax", "greedy", "random"])
    ap.add_argument("--suite", default="suite.json")
    ap.add_argument("--cases", default="all", help="comma-separated case ids, 'all', 'tuning' or 'heldout'")
    ap.add_argument("--run", required=True, help="name of the results folder")
    ap.add_argument("--depth", type=int, default=3, help="minimax search depth")
    ap.add_argument("--model", default="gemini-3.5-flash-lite")
    ap.add_argument("--history", default="none", choices=["none", "moves"])
    ap.add_argument("--prompt", default="v1", choices=["v1", "v2"],
                    help="model prompt version; v2 was tuned on T1-T3 only (EVALUATION.md)")
    ap.add_argument("--max-output-tokens", type=int, default=4096,
                    help="model output limit; run model-vs-greedy (2026-11-08) used 1024")
    ap.add_argument("--call-limit", type=int, default=110)
    ap.add_argument("--call-timeout", type=float, default=60.0)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    suite = json.load(open(args.suite))
    cases = suite["cases"]
    if args.cases == "tuning":
        cases = [c for c in cases if not c["heldout"]]
    elif args.cases == "heldout":
        cases = [c for c in cases if c["heldout"]]
    elif args.cases != "all":
        want = args.cases.split(",")
        cases = [c for c in cases if c["id"] in want]

    out_dir = os.path.join("results", args.run)
    os.makedirs(out_dir, exist_ok=True)
    limits = Limits(call_limit=args.call_limit, call_timeout_s=args.call_timeout)
    meta = {"game_version": git_version(), "run": args.run,
            "date": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            "candidate": args.candidate, "opponent": args.opponent, "minimax_depth": args.depth,
            "model": args.model if "model" in (args.candidate, args.opponent) else None,
            "history": args.history,
            "prompt_version": args.prompt if "model" in (args.candidate, args.opponent) else None,
            "max_output_tokens": args.max_output_tokens if "model" in (args.candidate, args.opponent) else None}
    episodes = []
    for case in cases:
        for trial, cand_side in enumerate(case.get("candidate_sides", [1, 2])):
            seed = zlib.crc32(f"{case['id']}:{cand_side}:{trial}".encode())
            cand = make_player(args.candidate, seed, args)
            opp = make_player(args.opponent, seed + 1, args)
            players = {cand_side: cand, 3 - cand_side: opp}
            trace = os.path.join(out_dir, f"{case['id']}_t{trial + 1}_cand-as-{'X' if cand_side == 1 else 'O'}.jsonl")
            r = run_episode(players, opening=case["opening"], seed=seed, limits=limits,
                            case_id=case["id"], trace_path=trace, meta=meta)
            w = r["outcome"]["winner"]
            result = "win" if w == cand_side else "loss" if w == 3 - cand_side else "draw/none"
            row = {"case": case["id"], "trial": trial + 1, "heldout": case["heldout"], "candidate_side": cand_side,
                   "result": result, "reason": r["outcome"]["reason"], "steps": r["steps"],
                   "wall_s": r["wall_s"], "candidate": r["players"][cand_side],
                   "opponent": r["players"][3 - cand_side], "trace": trace}
            episodes.append(row)
            if not args.quiet:
                c = row["candidate"]
                print(f"{case['id']:15s} cand as {'X' if cand_side == 1 else 'O'}: {result:9s} "
                      f"({row['reason']}, {row['steps']} moves) illegal={c['illegal_attempts']} "
                      f"fallback={c['fallback_moves']} failed_calls={c['failed_calls']} "
                      f"tokens={c['input_tokens']}+{c['output_tokens']}", flush=True)
    json.dump({"meta": meta, "episodes": episodes}, open(os.path.join(out_dir, "summary.json"), "w"),
              indent=2)
    print(f"wrote {out_dir}/summary.json")


if __name__ == "__main__":
    main()
