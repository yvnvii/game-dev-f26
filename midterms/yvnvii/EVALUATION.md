# Evaluation

> Sections marked **(you)** must be written in your own words before submitting.

## Declared suite (Twist Four, fixed 2026-11-08, before any prompt tuning)

Defined in [`suite.json`](suite.json). Two trials per case. `H1-twisted` is **held out**: it is never used
while adjusting the model prompt.

| Case | Opening | Purpose | Candidate plays |
|---|---|---|---|
| T1-empty | (none) | Full game from the start, including when to twist | X, then O |
| T2-centre | drop B2, C3, C2, B3, B2, C3 | Mid-game reading, no twists yet | X, then O |
| T3-twist-win | 13 actions incl. 5 twists (see suite.json) | O can win at once **only by a twist** (`twist col D fwd`) | O, twice |
| H1-twisted* | 8 actions incl. 5 twists | Held out: a position reached through twists | X, then O |

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
- **Limit endings (rule E1):** each player has a 15-minute clock for its own thinking time; a model player
  also has 110 calls. A player whose clock runs out (`timeout`) or who uses up its calls (`call_limit`)
  **loses**, and the result counts as a loss for that player and a win for its opponent in W/D/L. Only the
  `step_limit` backstop ends with no winner. I decided this on 2026-11-08, after the independent review
  (`review.md`) pointed out that limit endings were scored as draws, and **before any Twist Four model
  run**. The summary table shows timeout and call-limit endings in their own column.
- **Retry feedback:** when a reply has no MOVE line, the feedback now names the Twist Four format (`MOVE: <action>`, e.g. `MOVE: drop B3`) instead of the drop-only `MOVE: <shaft>`; fixed 2026-11-08 (review.md), before any Twist Four model run.

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

### Prompt v2 (2026-11-08)

Prompt v1 is unchanged and is still the default. v2 is chosen with `--prompt v2` (`scripts/evaluate.py`,
`scripts/play.py`). The run meta records `prompt_version`, and the player name ends in it, e.g.
`model:gemini-3.5-flash-lite:none:v2`.

- **Tuned on:** the tuning cases T1-T3 only, using the v1 run `results/model-vs-greedy`. I did not look at
  the held-out case H1-twisted while tuning.
- **Why:** two failures in the v1 run:
  1. In both T3-twist-win trials, `twist col D fwd` wins at once. But in the saved end of its reasoning
     (the last 600 characters) no twist is mentioned, and it chose a drop (`drop B2` both times).
  2. In T3 trial 1 it called shaft B2 "empty" while its own reading showed an O there. It misreads the
     3D board from the layer grids.
- **What changed (v2 = v1 + two additions, built only from the observation):**
  1. After the layer grids comes a list of every shaft, A1 to D4, from bottom to top (`B2: O X`,
     `C4: empty`). Then come `Your pieces:` and `Opponent's pieces:` as cell names (`B2 L1`).
  2. Just before the MOVE instruction comes a checking order: (1) any action that wins now, twists
     included, remembering gravity; (2) any opponent drop or twist that would win next turn, and stop
     it; (3) only then build. Ends with "Do not ignore twists."
- **What v2 does not do:** it computes nothing for the model. There is no list of winning moves, no
  threat detection, no scores, and no note on any single action. `tests/test_prompt.py` checks three
  things: v1 is byte-for-byte unchanged, the listing is correct, and no added line names a legal action.
- **Trace logging (same date, logging only, the prompt is unchanged):** traces now store each model
  reply in full. Runs before this change (`results/model-vs-greedy`, `model-vs-minimax`,
  `model-history-vs-greedy`, `pilot-drop-only`) kept only the last 600 characters of each reply.

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
