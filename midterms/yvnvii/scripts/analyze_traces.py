"""Count, for each run, how often the model missed a win in one move, and how often it left the
opponent a win in one when a safe move existed. Run from midterms/yvnvii/:
    python scripts/analyze_traces.py model-vs-greedy model-v2-vs-greedy model-vs-minimax
"""
import glob, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from c4d import rules as R
from c4d.engine import TwistFour

def analyze(run):
    t = {"turns": 0, "missed": 0, "missed_twist_only": 0, "blunders": 0, "opp_win_drop": 0, "opp_win_twist": 0}
    for f in sorted(glob.glob(f"results/{run}/*.jsonl")):
        ev = [json.loads(l) for l in open(f)]
        g = TwistFour(); g.reset(0, ev[0]["opening"]); cand = 1 if "_cand-as-X" in f else 2
        moves = [x for x in ev if x["type"] == "move"]
        for e in moves:
            s = g.state
            if e["player"] == cand and e["source"] == "model":
                t["turns"] += 1
                kids = R.children(s)
                wins = [a for a, _, r in kids if r and r["winner"] == cand]
                opp_wins = lambda n: any(r and r["winner"] == 3 - cand for _, _, r in R.children(n))
                safe = [a for a, n, r in kids if (r and r["winner"] == cand) or (not r and not opp_wins(n))]
                a = R.parse_action(e["action"])
                if wins and a not in wins:
                    t["missed"] += 1
                    if all(w[0] == "twist" for w in wins):
                        t["missed_twist_only"] += 1
                elif safe and a not in safe:
                    t["blunders"] += 1
            g.step(e["player"], e["action"])
        if moves and moves[-1]["player"] != cand and g.outcome()["winner"] == 3 - cand:
            t["opp_win_twist" if moves[-1]["action"].startswith("twist") else "opp_win_drop"] += 1
    return t

for run in sys.argv[1:]:
    print(run, analyze(run))
