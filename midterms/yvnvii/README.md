# Tilt Four: 3D gravity Connect Four (midterm)

> **TODO before submitting:** replace every `yvnvii` with your lowercase GitHub login, add the
> recording link, and rewrite the scope statement in your own words.

**Recording:** TODO link (3–5 min) · **Evaluation:** [EVALUATION.md](EVALUATION.md) ·
**Agent team log:** [AGENT-TEAM.md](AGENT-TEAM.md) · **Playtest notes:** [PLAYTEST.md](PLAYTEST.md)

## Scope statement

**In scope (this build):** two-player Connect Four on a 4×4×4 cube. Each turn a player drops a piece into
one of 16 vertical shafts (A1–D4), and it falls to the lowest empty cell. Four in a straight line in any
of the 76 lines of the cube wins (rows, columns, shafts, and all diagonals, including ones that cross all
four layers). A full board with no line is a draw. Text interface, a machine-playable five-operation
interface, a minimax baseline, and a Gemini player.

**Planned next (rotation rules, specified, not yet built):** on your turn, instead of dropping, you may
tilt the cube left or right; all pieces then fall toward the new bottom. A tilt uses your whole turn. If
a tilt creates four-in-a-row for both players, the player who tilted wins. Each player has 2 tilts per game.

**Excluded:** 3D graphics, sound, network play, Pop Out and other Hasbro variants, boards other than 4×4×4.
**First cut if time runs out:** the rotation rules (the drop-only game is complete on its own).

## Setup, play, test, evaluate

Every command runs from **`midterms/yvnvii/`** in a fresh clone.

```bash
# setup (Python 3.11+)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# play: you vs the minimax baseline (type moves like B3)
python scripts/play.py
python scripts/play.py --you O --opponent greedy

# watch two agents play, no human input
python scripts/play.py --watch minimax greedy --delay 0.5
python scripts/play.py --watch model minimax --trace traces/demo.jsonl    # needs Vertex setup below

# deterministic tests (what CI runs; no network, no credentials)
python -m pytest -v

# evaluation on the declared suite (suite.json)
python scripts/evaluate.py --candidate minimax --opponent greedy --run baseline-vs-greedy
python scripts/evaluate.py --candidate model   --opponent greedy --run model-vs-greedy
python scripts/summarize.py > results/TABLE.md
```

**Live model setup (Vertex AI):** `gcloud auth application-default login`, then
`export GOOGLE_CLOUD_PROJECT=<your-project-id>` (optionally `GOOGLE_CLOUD_LOCATION`, default `global`).
No key is stored in the repository.

## Machine-playable interface (`c4d/engine.py`)

| Operation | What it does |
|---|---|
| `reset(seed, opening=())` | Empty board, X to move; `opening` replays fixed moves to create a suite position. |
| `observe(player_id)` | A **copy** of the full board plus text rendering, your symbol, move number, last move. |
| `legal_actions(player_id)` | Non-full shafts in fixed order A1…D4, and `[]` if it is not your turn. No ranking. |
| `step(player_id, action)` | Validates and applies one drop. An invalid action returns an error and changes nothing. |
| `outcome()` | `ongoing`, or `terminal` with reason (`connect_four`, `board_full`, or a runner limit), winner, score. |

**Information boundary:** Connect Four is fully observed, so both roles may see the whole board; there is
no secret for the legal-action list to leak. The boundary that matters is that players get a copy, never
the engine (`tests/test_engine.py::test_observation_is_a_copy...`), and the model's prompt contains only
the observation and legal moves. The runner (`c4d/runner.py`) holds the only authoritative game.

## Rule/source map

| # | Rule | Label | Locator / rationale |
|---|---|---|---|
| R1 | Two players alternate turns, one piece per turn | manual | Hasbro Connect 4 instructions, [PDF](https://instructions.hasbro.com/api/download/01081_en-us_connect-4-game-instructions.pdf). Code: `engine.py` `step()` |
| R2 | A piece dropped in a column falls to the lowest empty cell | manual | Hasbro PDF (as above). Code: `engine.py` `height()`, `step()`; test `test_gravity_pieces_stack_from_the_bottom` |
| R3 | X (player 1) always moves first | design | Fixed for reproducible evaluation; the suite plays each case with the candidate as X and as O to cancel first-move advantage |
| R4 | Board is 4×4×4: 16 vertical shafts, 4 layers | design | Replaces Connect Four's 7×6 vertical grid. 4 is the smallest size where four-in-a-row fits; reference: Score Four (1967, A. P. Nienstaedt and H. Heller), a 3D four-in-a-row game ([analog.games](https://www.analog.games/gameItem/show/419cd83f96e69db70196e70053f5021a/score-four?lang=EN)) |
| R5 | Four in a line wins, in any of the 76 lines: rows, columns, shafts, planar and space diagonals | design | Extends Connect Four's horizontal/vertical/diagonal win (manual, Hasbro PDF) to 3D as in Score Four's "any level or angle" (that page is a database description, not a rulebook). Code: `engine.py` `LINES`; tests `test_cube_has_76_winning_lines...`, `test_space_diagonal_win...` |
| R6 | A full board with no line is a draw | assumed | **TODO:** confirm in the Hasbro PDF, then relabel `manual` with the page. Code: `engine.py` `step()`; test `test_full_board_without_line_is_draw` |
| R7 | An illegal action (full shaft, malformed, wrong turn, game over) is rejected and changes nothing | design | Lets the runner count illegal attempts and give feedback. Code: `engine.py` `step()`; tests in `test_engine.py` |
| R8 | Episode limits: 64 accepted moves, 48 model calls per model player (failed calls count), 60 s per call, 30 min per episode, 2 attempts per turn then a labeled fallback | design | Code: `runner.py` `Limits`, `run_episode()`; tests in `test_runner.py` |
| R9 | *(planned)* Tilt left/right instead of dropping; pieces re-fall | design | Decided 2026-11-05 |
| R10 | *(planned)* A tilt uses the whole turn | design | Decided 2026-11-05: keeps one action per turn, simpler for players and the interface |
| R11 | *(planned)* If a tilt makes lines for both players, the tilter wins | design | Decided 2026-11-05: rewards the risk of tilting |
| R12 | *(planned)* Each player has 2 tilts per game | design | Decided 2026-11-05: prevents endless back-and-forth tilting |

## Sources and reuse terms

- **Connect Four**, designed by Howard Wexler and Ned Strongin, published by Milton Bradley (1974), now Hasbro. Only the
  rules are used; no text, art, or trademarked assets are copied. Rules are referenced from Hasbro's public
  instruction sheet (linked above).
- **Score Four** (1967): referenced for the 3D four-in-a-row idea only.
- All code in this folder is original, written for this midterm with an AI implementation agent (see AGENT-TEAM.md).
- Python dependency: [`google-genai`](https://pypi.org/project/google-genai/) (Apache-2.0), installed via pip and not vendored. `pytest` (MIT) for tests.
