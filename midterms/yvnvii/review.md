# Review

- Date: 2026-11-08
- Commit: 106660f
- Reviewer: rules-reviewer subagent, read-only tools (Read, Grep, Glob), not instructed to approve.

---

# Review: Twist Four (midterms/yvnvii), commit 106660f

I read the code but did not run it. I had no shell, so I did not run `python -m pytest`. Any claim that depends on running code is marked **unverified**. Paths below are relative to `/Users/yukiogawa/Desktop/game/game-dev-f26/midterms/yvnvii/`.

**Overall:** I found no critical or high-severity defects. The rules engine, the Python/JS twist mapping, the information boundary and the fallback labelling all match the spec. The issues are mostly enforcement gaps in the runner, stale or wrong documentation, and a few claims that no test pins down.

---

## 1. Rules vs. specification

**Findings (ranked)**

1. **Medium: RULES.md names a file that doesn't exist.** `RULES.md:7` says the demo is `web/twist-four.html`. The actual file is `web/index.html` (README.md:18, 71; CLAUDE.md).
2. **Medium: the two `manual` rules have no page or section reference.** README.md:103 (R4) and README.md:109 (R10) still say "TODO: add page/section". These are the only rows labelled `manual`.
3. **Low: the code produces an outcome reason the spec doesn't list.** The runner can end a game with `step_limit` (`c4d/runner.py:74`, also documented at README.md:114 as E1). RULES.md:92-93 lists only `call_limit` and `episode_timeout` as runner reasons. Under default limits `step_limit` can't fire, because R12 always ends the game first (`rules.py:193`, step_limit=100 at `runner.py:24`). It is still a reachable code path and is tested (`tests/test_runner.py:30`).
4. **Low: the parser accepts more than the spec's action text.** `rules.parse_action` (`rules.py:126-134`) ignores case, extra spaces, and surrounding backticks, quotes and periods. RULES.md R4/R5 give only canonical text. This is input tolerance rather than a game rule, but R8 ("malformed text is rejected") doesn't define "malformed". One sentence in R8 would settle it.
5. **Low: some locators are vague.** README.md:104 (R5) says only "worked-example tests". README.md:112 (R13) points to a test that monkeypatches `rules.legal` (`tests/test_engine.py:191-195`), so it checks how the engine reports R13, not the rule itself.

**Checked, no issue found**
- **R1 and R9:** `idx`/`xyz` (`rules.py:21-26`) and `_lines()` (`rules.py:30-38`) produce 76 lines.
- **R2:** `INITIAL` (`rules.py:145`).
- **R3:** `settle` (`rules.py:78-88`), applied after every twist (`rules.py:97`).
- **R4:** `rules.py:169-176`.
- **R5:** `turn_cell`/`PERM` (`rules.py:55-70`).
- **R6:** `rules.py:159-160, 185-186`.
- **R7:** `is_instant_undo` (`rules.py:148-151`). It applies only to the immediately previous action, and repeating a twist is allowed.
- **R8:** `engine.step` (`engine.py:97-108`) rejects without mutating.
- **R10:** a drop only checks the lines through the placed cell (`rules.py:177-180`). This is correct, because a prior line would already have ended the game.
- **R11:** `rules.py:187-191`. The mover's line wins first, which covers both "only mine" and "both"; otherwise the opponent's line wins.
- **R12:** `rules.py:193`. The turn starts at 1, so the draw comes after the 100th action, and a win on turn 100 still counts.
- **R13:** `engine.py:118-119`.
- **R14:** `engine.observe` (`engine.py:71-86`) includes `last_action`.
- **Rule/source map:** every one of R1-R14 and E1 has a row (README.md:98-114). Labels are sensible: R2/R3/R9 as `design` adaptations of Connect Four; R6/R7/R11/R12 as dated design decisions.
- **Twist cell mapping table vs `turn_cell` (`RULES.md:49-56`, `rules.py:57-61`):** all six rows match.
  - **Directions:** layer `cw` is clockwise seen from above (x right, y away). `fwd`: z=3 goes to y=0 (row 1). `back`: z=3 goes to y=3 (row 4). `left`: z=3 goes to x=0 (A). `right`: z=3 goes to x=3 (D).
  - **Inverses:** each pair is an exact inverse, which I checked algebraically.
  - **Worked examples:** both reproduce by hand. The layer twist sends A1 to A4 and B1 to A3; `col A fwd` sends A1 L1 to A4 L1 and A1 L2 to A3 L1.
- **JS parity:** `web/index.html:277-284` (turnCell), 312-317 (R6/R7), 319-339 (apply, R11, R12) and 746 (R13) match the Python logic line for line.
- **Cross-check claim:** README.md:71 says the JS and Python versions were cross-checked on 300 games. **Unverified:** no cross-check script is in the repo, so it can't be reproduced. Low.

---

## 2. Information boundary

**Findings**
1. **Low: human moves are logged as `baseline`.** In terminal play, `Human` is a non-model player, so the runner logs its moves as `source: "baseline"` (`runner.py:94`, `scripts/play.py:30`). This affects trace labelling only, not the boundary.

**Checked, no issue found**
- **What the runner passes to players:** only `obs` from `game.observe(p)`, `legal` from `game.legal_actions(p)` and a fresh `history` list of action strings (`runner.py:81-83, 87, 108`). The `TwistFour` object is never passed.
- **The observation is a copy:** `observe()` builds a new dict on every call. `board` is a fresh nested list (`engine.py:52-55`), and everything else is an immutable str, int or None. Covered by `tests/test_engine.py:204-209`.
- **`legal_actions` reveals nothing extra:** it is a fresh list in fixed vocabulary order with no ranking (`engine.py:89-94`), tested at `tests/test_engine.py:212-218`. Because the game is fully observed, it leaks nothing.
- **Baselines build their own state:** they rebuild a private `State` from the observation (`players.py:18-23`). No player module imports the engine.
- **Model prompt:** `build_prompt` (`model_player.py:42-58`) uses only the RULES text, observation fields, `legal` and an optional bounded history. The model has no tools. Tested at `tests/test_runner.py:92-101`. That test is weak: it only checks that two strings are absent.

---

## 3. Runner limits

**Findings (ranked)**
1. **Medium: the episode timeout is only checked between turns.** The check is at `runner.py:76`, at the top of the turn loop. One model turn can run up to `max_attempts_per_turn × call_timeout_s` (2 × 60 s = 120 s) past the deadline. Baseline `choose()` calls (`runner.py:87`) have no timeout at all, so a slow minimax or a human can exceed `episode_timeout_s` without bound until it returns.
2. **Medium: an episode can end with an uncaught exception instead of an explicit reason.**
   - If a baseline returns an illegal move, the runner raises `RuntimeError` (`runner.py:90-91`).
   - Any exception from a baseline's `choose()` propagates.
   - In both cases no `end` event is logged and no trace is written (the trace is only written at `runner.py:170-173`).
   - The fallback step result is not checked either (`runner.py:153-157`). If `step` failed, `r["action"]` would raise a `KeyError`; this can't happen while `legal` is non-empty.
3. **Low/Medium: the feedback sent to the model is out of date.** When no MOVE line is found, the feedback reads `"no line of the form 'MOVE: <shaft>' was found"` (`runner.py:127`). This wording is left over from the drop-only pilot. It reaches the model through `build_prompt` (`model_player.py:54-55`) and suggests only shaft drops are allowed. Changing it alters prompt content after the declared date, so the student must approve the change and it has to be reported.
4. **Low: timed-out calls keep running.** `_call_with_timeout` (`runner.py:44-50`) abandons the worker thread but does not stop it. A hung API call keeps running, and the non-daemon pool thread can delay interpreter exit.
5. **Low (informational): the call limit can't bind under default settings.** `call_limit=110` (`runner.py:25`) is higher than the most a model can use: 50 own turns × 2 attempts = 100 calls. The limit works (it is tested), but in real runs it never triggers.

**Checked, no issue found**
- **Step limit:** `runner.py:73-75`.
- **Call limit:** checked before each call, `runner.py:101-103`, ending with `call_limit` at `runner.py:149-151`.
- **Per-call timeout:** `runner.py:108-114`.
- **Episode timeout:** `runner.py:76-78`, with the gap noted above.
- **Failed calls count toward the budget:** `st.calls += 1` happens before the call (`runner.py:104`). Timeouts and exceptions increment `failed_calls` (`runner.py:111, 116`).
- **Explicit end reasons:** every normal loop exit is either an engine terminal reason (`connect_four` / `turn_limit` / `no_legal_actions`) or a `force_end` reason, logged in the `end` event (`runner.py:169`).
- **Fallbacks are labelled and never counted as model moves:** they are logged with `source: "fallback"`, increment only `fallback_moves` (`runner.py:154-156`), and never `moves`, which is incremented only on an accepted model move (`runner.py:139`).

---

## 4. Tests

**Findings (ranked)**
1. **Medium: the regression guard is unverified.**
   - The original observed regression ("O must play C3") has been replaced by `test_minimax_always_returns_an_optimal_action` (`tests/test_regression.py:61-68`). It compares minimax against unpruned negamax at depth 2 on 5 positions.
   - The docstring claims this test fails with the alpha-1 fix removed (`tests/test_regression.py:11-13`). I could not confirm that without running it.
   - `test_observed_position_minimax_takes_an_immediate_win` (`tests/test_regression.py:71-78`) would **not** catch the tie bug, because root-level wins are scored without searching. So the first test is the only guard.
2. **Medium: the T3 suite claim has no test.** `suite.json:44` and `EVALUATION.md:14` say "O can win at once ONLY with `twist col D fwd`". No test checks this, so a rule change could silently invalidate the case. A two-line test using `rules.children` would pin it.
3. **Low: R13 is only tested through a monkeypatch.** `tests/test_engine.py:191-195` replaces `rules.legal`, so it checks how the engine reports a stuck player, not real R13 detection. Minimax's `if not kids: return 0` (`players.py:137-138`) is untested.
4. **Low: R6/R7 rejections aren't checked for side effects.** `tests/test_engine.py:101-118` asserts the twist is rejected but not that the state and history are unchanged. The R8 test at `tests/test_engine.py:121-130` does check that, but only for malformed or full-shaft input.
5. **Low: twist directions are only pinned indirectly.**
   - The inverse test (`tests/test_engine.py:46-56`) would still pass if `left`/`right` or `fwd`/`back` were swapped consistently.
   - Only `layer cw` and `col fwd` have worked-example tests. `row right` and `layer cw` are pinned only through the fixed R11 positions.
   - A direct check of each row of the mapping table would close this gap.

**Checked: each item has at least one test that would fail if the behaviour broke**
- **Rule invariants:**
  - 76 lines: `test_engine.py:29`.
  - Twist permutations and inverses: `:46`.
  - Gravity and piece counts through random play with twists: `:59`.
  - Initial state: `:37`.
  - Worked examples: `:81, :87`.
- **Legal actions:**
  - Drop placement: `:93`.
  - Repeating a twist is legal: `:114-118`.
  - A model twist is accepted: `test_runner.py:118`.
- **Illegal actions:** R6 at `:101`, R7 at `:109`, R8 at `:121`; a rejected opening at `:198`.
- **Terminal outcomes:**
  - R10: `:134`.
  - Space diagonal: `:143`.
  - R11 "both lines" for each mover: `:163`.
  - R11 "opponent only": `:172`.
  - R12, including a win on turn 100: `:180`.
  - R13: `:191`.
  - Through the runner: `test_runner.py:15, :22`.
- **Episode limits:**
  - Step limit: `test_runner.py:30`.
  - Call limit with failed calls: `:37`.
  - Per-call timeout and fallback label: `:46`.
  - Episode timeout: `:76`.
  - Illegal retry with feedback: `:59`.
  - Cut-off reply (`MAX_TOKENS` observation): `:104`.
  - Fallback move: `:136`.
- **Test count:** 38 test items as declared in the commit message: 20 in `test_engine`, 12 in `test_runner`, 6 in `test_regression`.
- **CI:** `.github/workflows/midterm-yvnvii.yml` runs `pytest -v` with no secrets or model SDK.

---

## 5. Evaluation fairness

**Findings (ranked)**
1. **Medium: limit endings score as draws.** `call_limit` and `episode_timeout` endings set `winner=None` (`runner.py:77, 150`). `evaluate.py:97` and `summarize.py:39` count them as "draw/none", so a model that fails on budget or time gets 0 instead of a loss. `summarize.py:46-47` discloses this, but it can flatter the model's W/D/L. Under defaults, `episode_timeout` (1800 s) is reachable: the worst case for a model is about 50 turns × 2 × 60 s.
2. **Medium: twist counts are wrong in the case descriptions.**
   - `EVALUATION.md:14` says T3 has "13 actions incl. 6 twists". The opening at `suite.json:28-42` has **5** twists.
   - `EVALUATION.md:15` says H1 has "8 actions incl. 6 twists". `suite.json:52-61` has **5** twists.
   - `suite.json:63` says H1 was reached "through four twists". It is **5**.
   - The suite is frozen, so fix EVALUATION.md and record the suite text error rather than editing the case.
3. **Low: stale case IDs and docstrings.**
   - `scripts/evaluate.py:3` says every case is played as X then O, which is not true for T3.
   - `scripts/evaluate.py:9` uses the pilot case id `S1-empty`.
4. **Low: compute is asymmetric.** The baseline has no per-move time limit, while the model has 60 s per call. This is disclosed at `EVALUATION.md:33-34`.
5. **Low: summary rows can be dropped.** `summarize.py:38-45` prints a placeholder row (`| ... |`) whenever no latencies were recorded. A model run where every call failed would lose its whole row from the table.

**Checked, no issue found**
- **Same cases:** both candidates run on the cases in `suite.json`, filtered the same way (`evaluate.py:67-75`).
- **Same sides:** `candidate_sides` default to `[1, 2]`; T3 is `[2, 2]` (`evaluate.py:88`).
- **Same opponent seeds:** the seed is `crc32("case:side:trial")`, which does not depend on the candidate type. The opponent gets `seed+1`, and fresh players are built per episode (`evaluate.py:89-92`).
- **Held-out cases are marked:** in `suite.json:62` (`"heldout": true`, with "HELD OUT" in the `why` text), in each episode row (`evaluate.py:98`), with `*` in the table (`summarize.py:37, 46`), and in `EVALUATION.md:7-8, 15`. A `--cases tuning` filter excludes them (`evaluate.py:69-70`). Keeping them out of prompt tuning is a process rule; nothing in the code enforces it.
- **Run metadata:** git version, date, depth, model and max tokens are recorded in each run's meta (`evaluate.py:80-85`).
- **Openings:** the T2 / T3 / H1 openings produce the side-to-move stated in `suite.json`: X, O and X respectively, by parity. **Unverified:** that each opening is legal. `reset` raises on an illegal opening (`engine.py:34-39`), but no test loads the suite.

---

## What I checked
- **Specification and maps:**
  - `RULES.md` (all of R1-R14, the mapping table and the worked examples).
  - `README.md` (rule/source map, code map, interface, information boundary).
  - `EVALUATION.md` and `suite.json`.
  - `CLAUDE.md` (scope and architecture rules).
- **Code:**
  - `c4d/rules.py`, `c4d/engine.py`, `c4d/runner.py`, `c4d/players.py` and `c4d/model_player.py`, read in full.
  - `scripts/evaluate.py`, `scripts/summarize.py` and `scripts/play.py`.
  - `web/index.html`: the rule core only, lines 249-340 and 746.
  - `/Users/yukiogawa/Desktop/game/game-dev-f26/.github/workflows/midterm-yvnvii.yml`.
- **Tests:** `tests/test_engine.py`, `tests/test_runner.py` and `tests/test_regression.py`, read in full.
- **Hand-verified:** all six twist mappings, inverse pairs and direction wording; both worked examples; the twist counts and side-to-move of each suite opening; the turn-limit off-by-one; the root window of the alpha-beta fix.
- **Not done:** running pytest, running the regression mutation check, verifying the T3 "only by twist" claim, and the 300-game JS/Python cross-check.
