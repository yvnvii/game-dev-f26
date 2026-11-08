# Twist Four (midterm, yvnvii)

Connect Four inside a 4 × 4 × 4 cube whose slices turn like a Rubik's Cube. On your turn you either
drop a piece into one of 16 shafts, or twist a layer or slab 90° and let gravity re-settle every piece.
Four in a line wins.

**Recording:** TODO link (3–5 min) · **Rules:** [RULES.md](RULES.md) · **Evaluation:** [EVALUATION.md](EVALUATION.md) ·
**Agent team log:** [AGENT-TEAM.md](AGENT-TEAM.md) · **Playtest notes:** [PLAYTEST.md](PLAYTEST.md)

## Scope statement

> **TODO (you): rewrite this section in your own words.**

**In scope:** the complete game in [RULES.md](RULES.md): drops, 24 twists (4 layers and 8 vertical slabs,
both directions), gravity after every twist, the 76 winning lines, the twist rules R6, R7 and R11, and a
100-turn limit. A machine-playable five-operation interface, a minimax baseline, a Gemini player, an
evaluation on a declared suite, and two ways for humans to play: a 3D browser version with drag-to-twist
(`web/index.html`) and a terminal version.

**Changed from my Week 3 scope:** I first planned 3D gravity Connect Four with tilting, built the
drop-only version first (pilot, 2026-11-05), then replaced tilting with Rubik's-style twists (2026-11-08).

**Excluded:** boards other than 4 × 4 × 4, half-turns or 180° twists, a limit on the number of twists,
network play, sound.
**First cut if time runs out:** vertical-slab twists (keep layer twists only).

## Setup, play, test, evaluate

Every command runs from **`midterms/yvnvii/`** in a fresh clone.

```bash
# setup (Python 3.11+)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# play in 3D: open this file in a browser (no install, no server)
open web/index.html            # macOS; or double-click it

# play in the terminal: you vs the minimax baseline (type B3 to drop, or e.g. "twist layer 2 cw"; ? lists all)
python scripts/play.py
python scripts/play.py --you O --opponent greedy

# watch two agents play, no human input
python scripts/play.py --watch minimax greedy --delay 0.5
python scripts/play.py --watch model minimax --trace traces/demo.jsonl     # needs the Vertex setup below

# deterministic tests (what CI runs; no network, no credentials)
python -m pytest -v

# evaluation on the declared suite (suite.json)
python scripts/evaluate.py --candidate minimax --opponent greedy --run baseline-vs-greedy
python scripts/evaluate.py --candidate model   --opponent greedy --run model-vs-greedy
python scripts/evaluate.py --candidate model   --opponent minimax --run model-vs-minimax
python scripts/summarize.py > results/TABLE.md
```

**Manual check, not in CI: web rules vs Python rules.** `python scripts/crosscheck_web.py --games 300`
plays random games with `c4d/rules.py`, runs the JavaScript between the `rules` and `computer` markers in
`web/index.html` with Node (needs `node`; no browser, no npm packages), replays every action with the JS
`apply()`, and compares board, side to move, turn and result after every step. Run it after any rule change.
Last run (2026-11-08, seed 0): 300 games, 10,609 steps, 0 rule mismatches. In 2 steps a twist completed two
lines for the winner and the two versions named different (both valid) lines; the script counts those
separately.

**Live model setup (Vertex AI):** `gcloud auth application-default login`, then
`export GOOGLE_CLOUD_PROJECT=<your-project-id>` (optionally `GOOGLE_CLOUD_LOCATION`, default `global`).
No key is stored in the repository.

## Code map

| File | Role |
|---|---|
| `RULES.md` | The rule specification (R1–R14). |
| `c4d/rules.py` | The rules as pure functions: board, twists, gravity, lines, legality. |
| `c4d/engine.py` | `TwistFour`: the authoritative game behind the five operations. |
| `c4d/runner.py` | Runs an episode; holds the only game; enforces limits; labels fallbacks; writes traces. |
| `c4d/players.py` | Random, greedy, and the minimax baseline. They rebuild a private copy of the board from observations. |
| `c4d/model_player.py` | The Gemini player: prompt in, one action text out. No tools. |
| `web/index.html` | 3D browser version for people (playtest, recording). Same rules, in JavaScript; cross-checked against `c4d/rules.py` by `scripts/crosscheck_web.py` (see below). |

## Machine-playable interface (`c4d/engine.py`)

| Operation | What it does |
|---|---|
| `reset(seed, opening=())` | Empty cube, X to move; `opening` replays fixed actions to build a suite position. |
| `observe(player_id)` | A **copy** of the whole board, a text rendering, turn number, and the previous action (needed for R7). |
| `legal_actions(player_id)` | Legal action texts in a fixed order (16 drops, then 24 twists), or `[]` if it is not your turn. No ranking. |
| `step(player_id, action)` | Validates and applies one action text; an illegal one returns the reason and changes nothing. |
| `outcome()` | `ongoing`, or `terminal` with reason (`connect_four`, `turn_limit`, `no_legal_actions`, or a runner limit), winner, score. |

**Action vocabulary:** `drop B3`, `twist layer 2 cw|ccw`, `twist col B fwd|back`, `twist row 3 left|right`
(40 actions). I chose readable text over numbered actions so the model's reply and the trace say what
happened, and so the same strings work for people in the terminal.

**Information boundary:** Twist Four is fully observed (R14). Both roles may see the whole board, so there
is no secret for the legal-action list to leak; it only filters the fixed vocabulary by rules that follow from
the visible board and the visible last action. Players get a copy, never the engine
(`tests/test_engine.py::test_observation_is_a_copy_not_a_handle`), and the model's prompt contains only the
rules, the observation and the legal actions.

## Rule/source map

Labels: `manual` = from a published rulebook; `design` = my own rule or a deliberate adaptation;
locators point to the rulebook, to [RULES.md](RULES.md), and to the code and tests that enforce the rule.

| Rule | Summary | Label | Locator / rationale |
|---|---|---|---|
| R1 | 4 × 4 × 4 cube: 16 shafts, 4 layers | design | RULES.md §1. Replaces Connect Four's 7 × 6 grid; 4 is the smallest size that fits four in a row. Reference: Score Four (1967). `rules.py` |
| R2 | Empty start, X moves first | design | Adapts the Hasbro sheet, p. 2, "How to Play" step 1 ("Decide who's going first"). I fixed X first for reproducible evaluation; the suite plays both sides. `test_initial_state_R2` |
| R3 | Gravity: pieces fall to the bottom of their shaft, also after every twist | design | Extends Connect Four's gravity (manual, Hasbro sheet) to twists. `rules.settle`; `test_gravity_and_piece_counts_hold...` |
| R4 | Drop into a non-full shaft; the piece lands on top | manual + observed | [Hasbro sheet](https://instructions.hasbro.com/api/download/01081_en-us_connect-4-game-instructions.pdf), p. 2, "How to Play" step 2 ("Drop one of your counters down ANY of the slots"). Landing on the lowest empty space is not stated in words; it is how the physical grid behaves. `test_drop_lands_on_top_of_its_shaft_R4` |
| R5 | Twist one layer or slab 90°, then gravity; exact cell mapping in RULES.md | design | RULES.md §3, decided 2026-11-08. Idea from the Rubik's Cube (Ernő Rubik, 1974). `rules.turn_cell`, `PERM`; worked-example tests |
| R6 | A twist must change the board | design | Decided 2026-11-08: no passing. `test_no_op_twist_is_illegal_R6` |
| R7 | No exact undo of the opponent's previous twist | design | Decided 2026-11-08: stops endless back-and-forth. `test_instant_undo_is_illegal_but_repeating_is_legal_R7` |
| R8 | Illegal actions are rejected and change nothing | design | Lets the runner count illegal attempts and give feedback. `test_full_shaft_malformed_and_out_of_turn...` |
| R9 | Four in a straight line in any of 76 lines | design | Extends Connect Four's four-in-a-row (manual, Hasbro sheet) to 3D, as Score Four does. `test_cube_has_76_lines...`, `test_space_diagonal_win...` |
| R10 | A drop that completes your line wins | manual | Hasbro sheet, p. 2, objective ("4 ... in a row - horizontally, vertically or diagonally") and "How to Play" step 3. `test_drop_completes_a_line_R10` |
| R11 | After a twist: your line only → you win; both → twister wins; opponent's only → opponent wins | design | Decided 2026-11-08. `test_twist_making_both_lines...`, `test_twist_making_only_the_opponents_line_loses_R11` |
| R12 | No winner after 100 turns → draw | design | Decided 2026-11-08: twists are unlimited, so the game needs an end. `test_turn_limit_draw_R12` |
| R13 | No legal action → draw | design | Completes the spec for a rare stalemate. `test_no_legal_action_is_a_draw_R13` |
| R14 | Fully observed; the previous action is visible | design | Needed so players can know which twist R7 bars. `test_both_roles_see_the_same_board...` |
| E1 | Episode limits: 15 min clock per player (time in its own calls, retries included) → that player loses (`timeout`); 110 model calls per model player (failed calls count) → that player loses (`call_limit`); 60 s per call (capped at the time left); 2 attempts per turn then a labeled fallback; 100 accepted actions as a backstop with no winner (`step_limit`) | design | RULES.md "Episode limits". Decided 2026-11-08 after review.md (limit endings scored as draws): blame must go to the player who used the time. Replaces the 30 min episode timeout. `runner.py` `Limits`, `run_episode`; `tests/test_runner.py` `test_*_E1` |

`manual + observed` = the rulebook covers the action, and the rest is how the physical game behaves rather than anything the rulebook states in words (R4: the counter lands on the lowest empty space).

## Sources and reuse terms

- **Connect Four** (Howard Wexler and Ned Strongin; Milton Bradley, 1974; now Hasbro): drop, gravity,
  four in a row. Only the rules are used; no text, art or trademarked assets are copied. Rules sheet:
  [Hasbro PDF](https://instructions.hasbro.com/api/download/01081_en-us_connect-4-game-instructions.pdf)
  (the file at this link is the UK edition, (c) 2008, code 01081, which is the one cited).
- **Score Four** (1967; [analog.games entry](https://www.analog.games/gameItem/show/419cd83f96e69db70196e70053f5021a/score-four?lang=EN)):
  four in a row in a 4 × 4 × 4 grid.
- **Rubik's Cube** (Ernő Rubik, 1974): the idea of turning slices of a cube. No names, logos or artwork
  are used, and the game is not affiliated with the Rubik's brand.
- All code in this folder is original, written for this midterm with AI agents under my direction (see AGENT-TEAM.md).
- Dependencies: [`google-genai`](https://pypi.org/project/google-genai/) (Apache-2.0) and `pytest` (MIT), installed with pip, not vendored.
  The browser version loads [three.js](https://github.com/mrdoob/three.js) 0.160.0 (MIT) from the jsDelivr CDN.
