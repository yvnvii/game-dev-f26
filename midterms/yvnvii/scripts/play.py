"""Play in the terminal, or watch two agents play.

Run from midterms/<github-login>/:
  python scripts/play.py                          # you (X) vs minimax baseline
  python scripts/play.py --you O --opponent greedy
  python scripts/play.py --watch model minimax    # watch: model (X) vs minimax (O), no human input
  python scripts/play.py --watch minimax greedy --delay 0.5
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from c4d.engine import Connect3D  # noqa: E402
from c4d.players import GreedyPlayer, MinimaxPlayer, RandomPlayer  # noqa: E402
from c4d.runner import Limits, run_episode  # noqa: E402
from c4d.players import Player  # noqa: E402


def make(kind, seed, model, history):
    if kind == "model":
        from c4d.model_player import ModelPlayer
        return ModelPlayer(model=model, history_mode=history)
    return {"minimax": lambda: MinimaxPlayer(3, seed), "greedy": lambda: GreedyPlayer(seed),
            "random": lambda: RandomPlayer(seed)}[kind]()


class Human(Player):
    name = "human"

    def choose(self, obs, legal, feedback=None, history=None):
        print("\n" + obs["board_text"])
        if obs["last_move"]:
            print(f"Opponent played {obs['last_move']}.")
        while True:
            a = input(f"You are {obs['your_symbol']}. Your move (A1..D4, q to quit): ").strip().upper()
            if a == "Q":
                sys.exit(0)
            if a in legal:
                return {"action": a}
            print(f"  '{a}' is not legal. Legal: {', '.join(legal)}")


class Watched(Player):
    """Wraps a player to print the board before each of its moves (watch mode)."""

    def __init__(self, inner, delay):
        self.inner, self.delay = inner, delay
        self.name, self.is_model = inner.name, inner.is_model

    def choose(self, obs, legal, feedback=None, history=None):
        print("\n" + obs["board_text"])
        res = self.inner.choose(obs, legal, feedback=feedback, history=history)
        tag = "model" if self.is_model else "baseline"
        print(f"{obs['your_symbol']} ({self.name}, {tag}) chooses {res.get('action')}"
              + (f"  [latency {res['latency_s']}s]" if "latency_s" in res else ""))
        time.sleep(self.delay)
        return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--you", default="X", choices=["X", "O"])
    ap.add_argument("--opponent", default="minimax", choices=["minimax", "greedy", "random", "model"])
    ap.add_argument("--watch", nargs=2, metavar=("PLAYER_X", "PLAYER_O"))
    ap.add_argument("--model", default="gemini-3.5-flash-lite")
    ap.add_argument("--history", default="none", choices=["none", "moves"])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--delay", type=float, default=0.0)
    ap.add_argument("--trace", default=None, help="write a JSONL trace to this path")
    args = ap.parse_args()

    if args.watch:
        players = {i + 1: Watched(make(k, args.seed + i, args.model, args.history), args.delay)
                   for i, k in enumerate(args.watch)}
        limits = Limits()
    else:
        me = 1 if args.you == "X" else 2
        players = {me: Human(), 3 - me: make(args.opponent, args.seed, args.model, args.history)}
        limits = Limits(episode_timeout_s=24 * 3600)
    r = run_episode(players, seed=args.seed, limits=limits, trace_path=args.trace)
    print("\n" + r["final_board"])
    o = r["outcome"]
    who = "nobody" if o["winner"] is None else f"{'X' if o['winner'] == 1 else 'O'} ({r['players'][o['winner']]['name']})"
    print(f"\nGame over: {o['reason']}. Winner: {who}. Moves: {r['steps']}.")
    for p in (1, 2):
        s = r["players"][p]
        if s["fallback_moves"] or s["illegal_attempts"] or s["failed_calls"]:
            print(f"  {s['name']}: fallbacks={s['fallback_moves']} illegal={s['illegal_attempts']} "
                  f"failed_calls={s['failed_calls']}")


if __name__ == "__main__":
    main()
