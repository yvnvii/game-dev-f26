"""Manual check (not in CI): do the JavaScript rules in web/index.html agree with c4d/rules.py?

Plays N random games with the Python rules, then replays every action with the JavaScript apply()
from web/index.html (run by Node, no browser, no npm packages) and compares the board, side to move,
turn and result after every step.

A step counts as a rule mismatch if anything differs other than *which* winning line is reported.
When one action completes several lines for the winner, the two versions may name different ones
(Python sorts its line list, JavaScript keeps discovery order); those steps are counted separately,
after checking that both named lines really are complete lines of the winner on the shared board.

    python scripts/crosscheck_web.py --games 300 [--seed 0]

Needs `node` on PATH. Exit code 1 if anything differs.
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from c4d import rules  # noqa: E402

START = "/* ============================ rules"
END = "/* ============================ computer"

# Replays the games given in a JSON file and prints, per game, the state after every step.
DRIVER = r"""
const games = JSON.parse(require("fs").readFileSync(process.argv[2], "utf8"));
const out = games.map((actions) => {
  let pos = { b: new Int8Array(64), toMove: 1, turn: 1, last: null };
  const steps = [];
  for (const a of actions) {
    const n = apply(pos, a);
    if (!n) { steps.push(null); break; }          // JS says illegal: recorded as a mismatch
    steps.push({ board: Array.from(n.b), toMove: n.toMove, turn: n.turn,
                 result: n.result && { winner: n.result.winner, reason: n.result.reason,
                                       line: n.result.line && [...n.result.line].sort((p, q) => p - q) } });
    pos = n;
  }
  return steps;
});
process.stdout.write(JSON.stringify(out));
"""


def js_rules() -> str:
    html = (ROOT / "web" / "index.html").read_text()
    i, j = html.find(START), html.find(END)
    if i < 0 or j < i:
        sys.exit("could not find the rules/computer markers in web/index.html")
    return html[i:j]


def to_js(a) -> dict:
    if a[0] == "drop":
        return {"t": "drop", "x": a[1], "y": a[2]}
    return {"t": "twist", "axis": a[1], "k": a[2], "dir": a[3]}


def random_game(rng: random.Random):
    """Actions and the Python state after each one, until the game ends (R10-R13)."""
    s, actions, expected = rules.INITIAL, [], []
    while True:
        moves = rules.legal(s)
        if not moves:                                    # R13: nothing to replay
            return actions, expected
        a = rng.choice(moves)
        s, res = rules.apply(s, a)
        actions.append(a)
        expected.append({"board": list(s.board), "toMove": s.to_move, "turn": s.turn,
                         "result": res and {"winner": res["winner"], "reason": res["reason"],
                                            "line": res["line"] and sorted(res["line"])}})
        if res:
            return actions, expected


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--games", type=int, default=300)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    node = shutil.which("node")
    if not node:
        sys.exit("node is not installed (needed to run the JavaScript rules)")

    rng = random.Random(args.seed)
    games = [random_game(rng) for _ in range(args.games)]
    with tempfile.TemporaryDirectory() as tmp:
        script, data = Path(tmp) / "crosscheck.js", Path(tmp) / "games.json"
        script.write_text(js_rules() + "\n" + DRIVER)
        data.write_text(json.dumps([[to_js(a) for a in acts] for acts, _ in games]))
        proc = subprocess.run([node, str(script), str(data)], capture_output=True, text=True)
    if proc.returncode != 0:
        sys.exit(f"node failed:\n{proc.stderr}")
    js = json.loads(proc.stdout)

    steps = mismatches = other_line = 0
    endings: dict[str, int] = {}
    for g, ((actions, expected), got) in enumerate(zip(games, js)):
        r = expected[-1]["result"] if expected else None
        end = r["reason"] if r else "no_legal_actions"
        endings[end] = endings.get(end, 0) + 1
        for n, want in enumerate(expected):
            steps += 1
            have = got[n] if n < len(got) else None
            if have == want:
                continue
            if same_but_other_line(want, have):
                other_line += 1
                continue
            mismatches += 1
            if mismatches <= 5:
                print(f"MISMATCH game {g} step {n + 1} ({rules.action_text(actions[n])}):"
                      f"\n  python: {want}\n  js:     {have}")
    print(f"games: {len(games)}  steps: {steps}  rule mismatches: {mismatches}  "
          f"same result, other winning line named: {other_line}  endings: {endings}")
    return 1 if mismatches else 0


def same_but_other_line(want, have) -> bool:
    """Everything equal except the named line, and both named lines are full lines of the winner."""
    if not (have and want["result"] and have["result"]):
        return False
    if {**want, "result": None} != {**have, "result": None}:
        return False
    w, h = want["result"], have["result"]
    if (w["winner"], w["reason"]) != (h["winner"], h["reason"]):
        return False
    board = want["board"]
    return all(tuple(ln) in rules.LINES and all(board[i] == w["winner"] for i in ln)
               for ln in (w["line"], h["line"]))


if __name__ == "__main__":
    sys.exit(main())
