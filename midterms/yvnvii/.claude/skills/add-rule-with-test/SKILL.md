---
name: add-rule-with-test
description: Add or change one game rule in Tilt Four, with its rule/source map row and a deterministic test. Use whenever a rule is added, changed, or found to be wrong.
---

# Add a rule with its test

Input: one rule, stated by the student in a sentence (e.g. "a tilt uses the whole turn").

1. **Restate the rule** precisely: initial condition, legal action(s), state transition, effect on
   outcome(). List any ambiguity as a question to the student and stop until it is answered.
2. **Rule/source map:** add or edit one row in `README.md`. Label it `code`, `manual`, `observed`,
   `assumed`, or `design`, with a locator (a manual page/URL, a file and function, or "Decided <date>: <why>").
   Use `assumed` only for an unverified claim about a source game.
3. **Write the test first** in `tests/` and run `python -m pytest -q` to confirm it fails for the right reason.
4. **Implement** in `c4d/engine.py`. If the rule adds actions, update `legal_actions()` and the action
   parser, and check that the legal list still reveals nothing beyond the rules.
5. **Update the model prompt** (`RULES` in `c4d/model_player.py`) if the rule changes what a player may do.
6. Run the full suite: `python -m pytest -q`. Report: the rule, the map row, the test name(s), and the pass count.
