# Evaluation

> Sections marked **(you)** must be written in your own words before submitting.

## Declared suite (fixed 2026-11-05, before any prompt tuning)

Defined in [`suite.json`](suite.json). Each case is played twice: candidate as X, candidate as O.
`H1-diagonal` is **held out**: it is never used while adjusting the model prompt.

| Case | Opening | Purpose |
|---|---|---|
| S1-empty | (none) | Full game from the standard start |
| S2-midgame | B2 C3 C2 B3 B2 C3 | Stacked centre: mid-game reading |
| S3-must-block | A1 A2 B1 B2 C1 | X threatens D1; as O the candidate must block at once |
| H1-diagonal* | A1 D4 B2 D1 B2 C3 C3 A4 | Held out: diagonal pressure across layers |

## Experimental design

- **Players compared:** the model player (`gemini-3.5-flash-lite`, temperature 0.2, observation-only prompt)
  vs. the baseline (depth-3 negamax with alpha-beta and an open-line heuristic, `c4d/players.py`).
- **Shared reference opponent:** `greedy` (wins if it can, blocks an immediate loss, otherwise random).
  Both candidates play the same cases, same sides, same opponent seeds.
- **Head-to-head:** model vs. minimax on the same cases.
- **Memory/history experiment:** the game is fully observed, so the board already contains everything.
  Test `--history none` vs. `--history moves` (last 16 moves listed) on the tuning cases.
- **Same information for every player:** all players receive only `observe()` and `legal_actions()`.
  Compute is asymmetric and disclosed: minimax searches ~10²–10⁴ nodes per move, while the model makes 1–2 calls per move.
- **Fallback policy:** after 2 rejected or failed attempts in one turn, the runner plays the first legal
  shaft in centre-first order. It is labeled `fallback` in the trace and never counted as a model move.

## Results

Paste the output of `python scripts/summarize.py` here. Price date: `prices.json`.

TODO: table

Traces: `results/<run>/<case>_cand-as-X.jsonl` (one JSON event per line).

## CI evidence

TODO: link to the green `midterm-yvnvii` workflow run on the PR for the submitted commit.
Checks (`python -m pytest -v`): rule invariants and legal/illegal actions (`tests/test_engine.py`), terminal
outcomes (`test_engine.py`, `test_runner.py`), observed regression (`tests/test_regression.py`), and
episode limits (step, call, timeout, fallback) (`tests/test_runner.py`). Model outputs are scripted; CI makes
no live calls.

## Interpretation **(you)**

TODO: what the numbers show, either way. Do not claim statistical certainty from 8 episodes per run.

## Limitations **(you)**

TODO: include at least the small sample, the single model and temperature, asymmetric compute, the text-only
board (the model must reason in 3D from flattened layers), the rotation rules not yet built (if so), and what
the playtest found.
