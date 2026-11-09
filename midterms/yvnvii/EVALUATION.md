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
  observation. I tested `--history moves` (all actions so far) against `--history none` on the tuning cases
  T1-T3 vs greedy: 0-6 with history, 0-6 without, games no longer, and more tokens per call. With a fully
  observed board, the move list added cost but no measurable benefit in this small sample.
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

| run | cases | episodes | W / D-none / L | terminal reasons | limit losses (E1) | illegal attempts | fallbacks | failed calls | calls | mean latency (s) | candidate clock used, max (s) | tokens in / out | est. cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline-vs-greedy (minimax vs greedy, v1959f17, 2026-11-08) | H1-twisted*, T1-empty, T2-centre, T3-twist-win | 8 | 8 / 0 / 0 | connect_four:8 | none | 0 | 0 | 0 | 0 | 0.268 | 1.6 | 0 / 0 | $0 |
| model-history-vs-greedy (model vs greedy, v6cd1cb2, 2026-11-08) | T1-empty, T2-centre, T3-twist-win | 6 | 0 / 0 / 6 | connect_four:6 | none | 2 | 0 | 0 | 34 | 2.228 | 42.4 | 30648 / 17361 | $0.0526 |
| model-v2-vs-greedy (model vs greedy, v1959f17, 2026-11-08) | H1-twisted*, T1-empty, T2-centre, T3-twist-win | 8 | 0 / 0 / 8 | connect_four:8 | none | 0 | 0 | 2 | 62 | 2.804 | 98.6 | 65191 / 37462 | $0.1132 |
| model-vs-greedy (model vs greedy, v6cd1cb2, 2026-11-08) | H1-twisted*, T1-empty, T2-centre, T3-twist-win | 8 | 0 / 0 / 8 | connect_four:8 | none | 1 | 0 | 0 | 64 | 2.234 | 29.2 | 54049 / 29940 | $0.0911 |
| model-vs-minimax (model vs minimax, v6cd1cb2, 2026-11-08) | H1-twisted*, T1-empty, T2-centre, T3-twist-win | 8 | 0 / 0 / 8 | connect_four:8 | none | 0 | 0 | 0 | 28 | 1.718 | 8.3 | 22954 / 5959 | $0.0218 |

`*` = held-out case. W/D/L are from the candidate's side. Under rule E1 (decided 2026-11-08), `timeout` and `call_limit` endings are losses for the player who ran out and are counted in W/L; 'limit losses' says which side ('cand' or 'opp') lost that way. 'D-none' is draws plus the `step_limit` backstop. Runs before E1 (e.g. the drop-only pilot) may show `episode_timeout`, which had no winner.

Traces: `results/<run>/<case>_t<trial>_cand-as-<side>.jsonl` (one JSON event per line).

### Pilot on the drop-only version (2026-11-05 to 2026-11-08)

Before adding twists I evaluated the drop-only game (suite declared 2026-11-05, see git history):

| Run | W / D / L | Illegal attempts | Fallbacks | Note |
|---|---|---|---|---|
| minimax (depth 3) vs greedy | 8 / 0 / 0 | 0 | 0 | |
| Gemini vs greedy | 1 / 0 / 7 | 41 | 7 | 27 of the 41 were replies cut off at the 1024-token output limit before the MOVE line; 14 chose a full shaft |

The cut-off replies were a harness problem, not only a model problem. I raised the limit to 4096 and
started recording each reply's finish reason (`tests/test_runner.py::test_cut_off_model_reply...`).

Runs `model-vs-greedy`, `model-vs-minimax` and `model-history-vs-greedy` use prompt v1 (code 6cd1cb2);
`model-v2-vs-greedy` and `baseline-vs-greedy` use code 1959f17. The game rules are identical in both;
only prompt v2 and full-reply logging changed. The two failed calls in the v2 run were a 429 rate limit and
a 60 s timeout; both were retried with no fallback. Total live cost for Twist Four: about $0.28.
The baseline run produced identical games on two different machines.

### Why Gemini loses (`python scripts/analyze_traces.py <run>`)
| Run | Gemini turns | A win-in-one was available but not played | ...of which only a twist would win | Gave the opponent a win-in-one when a safe move existed |
|---|---|---|---|---|
| model-vs-greedy | 63 | 25 | 25 | 4 |
| model-v2-vs-greedy | 60 | 27 | 27 | 4 |
| model-history-vs-greedy | 32 | 18 | 18 | 3 |
| model-vs-minimax | 28 | 2 | 2 | 7 |

These count turns, not separate chances: greedy does not block twist threats, so one missed twist win can
stay available for several turns. Twist use: Gemini 4 twists in 183 moves (about 2%); minimax 8 in 32 (25%).


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

## Interpretation
The suite separates the players, as minimax beat greedy 8–0, while Gemini lost every game (0–30 across all runs) against greedy. The traces show that Gemini almost never twists, and on every turn where it had a win in one move, that win needed a twist. It plays Twist Four as if it were plain 3D Connect Four. Neither the clearer board listing and checklist (v2) nor the move history changed this. This model couldn’t simulate a twist plus gravity from a text board.

## Limitations
the small sample (6–8 games per run), so no statistical claims; minimax uses an exact rules simulator while Gemini only imagines twists from text, which might be way more difficult.
