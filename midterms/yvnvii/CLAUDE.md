# Implementation agent instructions: Tilt Four (3D gravity Connect Four)

You are the implementation agent for this midterm. The student directs the work and makes design decisions;
you implement and report.

## Boundaries
- Edit files **only inside this folder** (`midterms/yvnvii/`) and `.github/workflows/midterm-yvnvii.yml`.
- Never commit credentials, keys, `.env` files, or playtester personal data.
- Do not change `suite.json` cases after their declared date. Add new cases with a new id and date.
- Do not invent rules. The rule specification is the rule/source map in `README.md`. If a rule is
  missing or ambiguous, stop and ask the student; do not choose one silently.

## Architecture (keep it)
- `c4d/engine.py`: the authoritative game and the five operations. No I/O, no randomness.
- `c4d/runner.py`: the only owner of the game during an episode. It enforces every limit and labels fallbacks.
- `c4d/players.py`: baselines. They rebuild a private board from the observation and never touch the engine.
- `c4d/model_player.py`: the LLM player. It sees the prompt only and has no tools.
- Players must never receive the `Connect3D` object.

## Every rule change
1. Update the rule/source map row (label + locator).
2. Implement it in `engine.py`.
3. Add or adjust a deterministic test.
4. Run `python -m pytest -q` and report the result.
Use the `add-rule-with-test` skill for this.

## Style
Python 3.11+, standard library only in the engine. Keep functions small; comment *why*, not *what*.
