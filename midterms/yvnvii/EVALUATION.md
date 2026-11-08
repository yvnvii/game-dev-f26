# Evaluation

> Sections marked **(you)** must be written in your own words before submitting.

## Declared suite (Twist Four, fixed 2026-11-08, before any prompt tuning)

Defined in [`suite.json`](suite.json). Two trials per case. `H1-twisted` is **held out**: it is never used
while adjusting the model prompt.

| Case | Opening | Purpose | Candidate plays |
|---|---|---|---|
| T1-empty | (none) | Full game from the start, including when to twist | X, then O |
| T2-centre | drop B2, C3, C2, B3, B2, C3 | Mid-game reading, no twists yet | X, then O |
| T3-twist-win | 13 actions incl. 6 twists (see suite.json) | O can win at once **only by a twist** (`twist col D fwd`) | O, twice |
| H1-twisted* | 8 actions incl. 6 twists | Held out: a position reached through twists | X, then O |

T3 always gives the candidate the side to move: as X it would be a forced loss that says nothing about
the candidate. I fixed this on 2026-11-08 after the first baseline run showed it, before any model run.

## Experimental design

- **Players compared:** the model player (`gemini-3.5-flash-lite`, temperature 0.2, max 4096 output tokens,
  observation-only prompt) vs. the baseline (negamax depth 3 with alpha-beta over all 40 actions,
  open-line heuristic, `c4d/players.py`).
- **Why depth 3:** in 6-game matches, depth 3 beat greedy 6–0 and depth 2 6–0 at about 1 s per game;
  depth 4 took about 50 s per game and was not stronger in 2 games (1 win, 1 draw for depth 3).
- **Shared reference opponent:** `greedy` (takes any immediate win including twists, blocks a winning drop,
  otherwise a random safe drop). Both candidates play the same cases, sides and opponent seeds.
- **Head-to-head:** model vs. minimax on the same cases.
- **Memory/history:** the game is fully observed, and the last action (needed for rule R7) is part of the
  observation. Test `--history none` vs. `--history moves` on the tuning cases, or explain the omission.
- **Same information for every player:** all players receive only `observe()` and `legal_actions()`.
  Compute is asymmetric and disclosed: minimax searches roughly 10³–10⁴ positions per move; the model
  makes 1–2 calls per move.
- **Fallback policy:** after 2 rejected or failed attempts in one turn, the runner plays the most central
  legal drop. It is labeled `fallback` in the trace and never counted as a model move.

## Results

Paste the output of `python scripts/summarize.py` here. Price date: `prices.json`.

TODO: table

Traces: `results/<run>/<case>_t<trial>_cand-as-<side>.jsonl` (one JSON event per line).

### Pilot on the drop-only version (2026-11-05 to 2026-11-08)

Before adding twists I evaluated the drop-only game (suite declared 2026-11-05, see git history):

| Run | W / D / L | Illegal attempts | Fallbacks | Note |
|---|---|---|---|---|
| minimax (depth 3) vs greedy | 8 / 0 / 0 | 0 | 0 | |
| Gemini vs greedy | 1 / 0 / 7 | 41 | 7 | 27 of the 41 were replies cut off at the 1024-token output limit before the MOVE line; 14 chose a full shaft |

The cut-off replies were a harness problem, not only a model problem. I raised the limit to 4096 and
started recording each reply's finish reason (`tests/test_runner.py::test_cut_off_model_reply...`).

## CI evidence

TODO: link to the green `midterm-yvnvii` workflow run on the PR for the submitted commit.
Checks (`python -m pytest -v`): rule invariants and legal/illegal actions (`tests/test_engine.py`),
terminal outcomes (`test_engine.py`, `test_runner.py`), observed regression (`tests/test_regression.py`), and
episode limits (`tests/test_runner.py`). Model outputs are scripted; CI makes no live calls.

## Interpretation **(you)**

TODO: what the numbers show, either way. Do not claim statistical certainty from 8 episodes per run.

## Limitations **(you)**

TODO: include at least the small sample, one model at one temperature, asymmetric compute, the text-only
board (the model must picture twists in 3D from flattened layers), and what the playtest found.
