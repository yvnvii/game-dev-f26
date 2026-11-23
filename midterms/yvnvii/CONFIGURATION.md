# Twist Four — Configuration Document (Initial, G1)

**Owner:** Yuki Ogawa (Tech Lead, Design Lead; Creative Director approval retained) · **Gate approver:** instructor · **Version:** config v0.1, 2026-11-23
**Companion docs:** [GDD.md](GDD.md) · [PROJECT-PLAN.md](PROJECT-PLAN.md) · [RULES.md](RULES.md) · [AGENT-TEAM.md](AGENT-TEAM.md) (midterm agent log)

This document describes (1) how production roles are covered by me and my AI agent team, and (2) how the in-game AI opponent agent behaves: what it can see, what it can do, its limits, and how it is tested.

### Status labels

| Label | Meaning |
|---|---|
| **[VERIFIED]** | Built and checked by a named test, script or measurement. |
| **[IMPLEMENTED]** | Built in the repository, not yet checked beyond running it. |
| **[PLANNED]** | Decided, not built yet. |
| **[OPEN]** | Not decided yet; listed again in section 8. |

---

## 1. Artifact locations

| Artifact | Path | Status |
|---|---|---|
| Rules (pure functions) | `c4d/rules.py` | [VERIFIED: tests] |
| Authoritative game, five-operation interface | `c4d/engine.py` | [VERIFIED: tests] |
| Episode runner (limits, fallbacks, traces) | `c4d/runner.py` | [VERIFIED: `tests/test_runner.py`] |
| Scripted players: random, greedy, minimax | `c4d/players.py` | [IMPLEMENTED] |
| Midterm Gemini player | `c4d/model_player.py` | [IMPLEMENTED] |
| 3D browser version | `web/index.html` | [IMPLEMENTED]; rules [VERIFIED: `scripts/crosscheck_web.py`] |
| Candidate builder (tags legal moves) | `c4d/candidates.py` | [PLANNED] |
| Personality opponent agent | `c4d/persona_player.py` | [PLANNED] |
| Scripted personality baselines | `c4d/scripted_personas.py` | [PLANNED] |
| Persona cards | `agents/opponent/personas/*.yaml` | [PLANNED] |
| System instructions | `agents/opponent/system.md` | [PLANNED] |
| Function declaration (`choose_move`) | `agents/opponent/choose_move.json` | [PLANNED] |
| **Extension manifest** | `agents/opponent/manifest.yaml` | [PLANNED] |
| Production-role instructions | `agents/roles/*.md` | [PLANNED] |
| Evaluation suite | `suite.json` | [IMPLEMENTED] |
| Traces | `traces/*.jsonl` | [IMPLEMENTED] |
| CI workflow | `.github/workflows/ci.yml` | [OPEN: confirm the path the midterm CI uses] |

## 2. Production-role coverage

I hold the three accountable roles. AI agents do delegated work and hand it back to me; nothing merges or ships without my approval.

**Human roles (me):** **Creative Director**: final say on vision, pillars and cuts. **Design Lead**: owns GDD.md, persona cards and balance. **Tech Lead**: owns CONFIGURATION.md, architecture, merges and spending.

**Agent roles** [PLANNED unless marked]. Coding agent tool: [OPEN: the tool used in the midterm, from AGENT-TEAM.md].

| Role | Executable artifact | Purpose | Context | Tools / permissions | Outputs | Recipient → handoff | Evaluation | Human approval boundary |
|---|---|---|---|---|---|---|---|---|
| **Producer** | `agents/roles/producer.md` | Keep the plan and task list current | PROJECT-PLAN.md, gate dates, Asana export | Read repo; write PROJECT-PLAN.md only | Weekly plan updates, task drafts | Me → I paste approved tasks into Asana | Plan matches gate dates; tasks have done-when | I approve every task and date |
| **Rules / Engine Engineer** | `agents/roles/engine.md` | Change rules and engine safely | RULES.md, `c4d/rules.py`, `c4d/engine.py`, tests | Edit `c4d/`, `tests/`; run pytest; no network | Pull requests with tests | Me → review, then merge | All tests pass; crosscheck 0 mismatches | I approve every rule change and merge |
| **Opponent AI Engineer** | `agents/roles/opponent-ai.md` | Build candidate builder, persona agent, baselines | This document §3, GDD §8–9, persona cards | Edit `c4d/`, `agents/opponent/`; run eval with a spend cap | Pull requests; eval tables in `results/` | Me → review; Design Lead checks persona fit | Style metrics (§3.12); on-list rate ≥ 95% | I approve persona cards, prompts, model changes, any spend above cap |
| **Frontend / 3D Engineer** | `agents/roles/frontend.md` | Select screen, portraits, glow, assist | GDD §10–11, `web/index.html` | Edit `web/`; run crosscheck; no new CDN libraries | Pull requests with screenshots | Me → review in browser | Crosscheck 0 mismatches; manual UI check | I approve every visual and dependency change |
| **QA / Test** | `agents/roles/qa.md` | Write and run tests; find regressions | RULES.md, tests, traces | Edit `tests/`; run pytest and crosscheck; read-only elsewhere | Test files; bug reports | Me + the relevant engineer agent | New code has tests; CI green | I decide which bugs block a gate |
| **Playtest Analyst** | `agents/roles/playtest.md` | Turn playtest notes and traces into findings | PLAYTEST.md, traces, survey answers (no names) | Read-only; write `results/playtest-*.md` | Findings tables, blind-ID accuracy | Me → GDD update | Numbers reproduce from raw data | I decide what the findings mean for design |
| **Character Art** | [OPEN] | Portraits for the five opponents | GDD §8 persona descriptions | [OPEN: depends on tool] | Images in `web/art/` | Me → Creative Director approval | Matches persona; terms recorded | I approve every image and its terms |

**My decisions vs. agent recommendations.** Design choices are mine; agents recommend. Each recommendation I accept or reject is logged in AGENT-TEAM.md with the date. G1 decisions that were mine: a cast of personality opponents (not a coach); the agent picks and the engine validates; five personas, cut to three if needed. [OPEN: list what the agent team recommended at G1.]

## 3. In-game agent: Personality Opponent

### 3.1 Purpose
Play Twist Four against a human **in character**, as one of five personas (Greedy, Careful, Dumb, Conservative, Adventurous), so the player feels they are reading a rival with a style (GDD pillar 2, agent hypothesis). [PLANNED]

### 3.2 Executable extension artifact
The opponent ships as a **function-calling interface**: the model can only answer by calling one function, `choose_move`, declared in `agents/opponent/choose_move.json`.

```json
{
  "name": "choose_move",
  "description": "Choose your next move from the candidate list, in character.",
  "parameters": {
    "type": "object",
    "properties": {
      "candidate_id": { "type": "string", "enum": ["C1","C2","C3","C4","C5","C6","C7","C8"] },
      "style_note":   { "type": "string", "description": "Max 15 words: why this fits your personality. Logged only, never shown to the player." }
    },
    "required": ["candidate_id"]
  }
}
```

The `enum` is rebuilt each turn to list only the candidate ids actually offered.

**Common manifest** (`agents/opponent/manifest.yaml`) [PLANNED; OPEN: confirm the syllabus’s required fields and add any missing]:

```yaml
name: twist-four-personality-opponent
version: 0.1.0
owner: Yuki Ogawa
purpose: Play Twist Four in character as one of five personas.
type: function-calling interface
entrypoint: c4d/persona_player.py:PersonaPlayer
native_config:
  function: agents/opponent/choose_move.json
  system_instructions: agents/opponent/system.md
  personas: agents/opponent/personas/
model: [OPEN: Gemini Flash-class model id on Vertex AI]
tools: [choose_move]
permissions: choose one offered candidate; no other actions
prohibited: calling engine.step(); inventing moves; network access other than the model call
limits: { timeout_s: 8, attempts_per_turn: 2, calls_per_game: 50 }
fallback: c4d/scripted_personas.py (same persona)
tests: tests/test_persona_player.py
evaluation: scripts/evaluate.py --candidate persona:<name>
```

### 3.3 Tools, permissions, prohibited actions

| | |
|---|---|
| **Tool** | `choose_move(candidate_id, style_note)` only. |
| **Permitted** | Pick one of the offered candidates. |
| **Prohibited** | Calling the engine (`step`, `reset`) or holding a reference to it; inventing a move not on the list; seeing or changing another player’s data; any tool other than `choose_move`; any text shown to the player. |
| **Who acts** | The runner (`c4d/runner.py`) turns the chosen candidate into an action and calls `engine.step()`. The agent never acts on the game itself. |

### 3.4 Named context sources (what goes into each call)

1. `agents/opponent/system.md`: shared system instructions.
2. `agents/opponent/personas/<name>.yaml`: the persona card.
3. A short rules summary (generated from RULES.md, ~800 tokens).
4. `engine.observe()` output: a **copy** of the board as text, turn number, last action.
5. The last 6 actions of this game.
6. The candidate list from `c4d/candidates.py`: up to 8 legal moves, each with engine-computed tags.

### 3.5 Knowledge boundary: world state vs. what the agent knows

Twist Four is fully observed (R14), so the agent sees the same board as the player. The boundary is about the engine and the search, not hidden pieces.

| Information | World state (engine) | Agent |
|---|---|---|
| Full board, side to move, last action | ✓ | ✓ (a copy, as text) |
| Full move history | ✓ | Last 6 actions only |
| All 40 legal actions | ✓ | Up to 8 candidates, chosen by the candidate builder |
| Tags (wins, blocks, opens a risk…) | Computed by engine | ✓ (as labels on candidates) |
| Minimax search tree and scores | ✓ | ✗ |
| What the human will play next | ✗ | ✗ |
| The engine object | ✓ | ✗ (enforced by `test_observation_is_a_copy_not_a_handle` [VERIFIED, midterm]) |
| Player identity, records, other games | Browser local storage | ✗ |

### 3.6 Memory policy
No memory between games. Within a game, only the last 6 actions are re-sent each turn. Nothing about the player is stored by the agent. Traces store moves and timings, no personal data. [PLANNED]

### 3.7 Model and settings [OPEN: confirm after the first latency test]

| Setting | Value | Reason |
|---|---|---|
| Model | Gemini Flash-class on Vertex AI [OPEN: exact id] | Low latency and cost |
| Temperature | 0.7 (Dumb: 1.0) | Some variety, so personas don’t feel mechanical |
| Max output tokens | 64 | One function call only |
| Function calling mode | Forced (`ANY`, only `choose_move`) | The model cannot answer in free text |
| Auth | `gcloud auth application-default login`; `GOOGLE_CLOUD_PROJECT` env var | No key in the repository [IMPLEMENTED, midterm] |

### 3.8 System instructions (draft, `agents/opponent/system.md`)

```text
You are an opponent in Twist Four, a 3D Connect Four game where layers of
a 4x4x4 cube can twist. You play as the character described in your
persona card. Stay in character: choose the move this personality would
choose, not always the strongest move.

Each turn you get the board, the last moves, and a list of candidate moves
with tags. You must call choose_move with exactly one candidate_id from the
list. Never invent a move. Tags are computed by the game engine and are
always correct; trust them over your own reading of the board.
```

**Persona card example** (`agents/opponent/personas/greedy.yaml`):

```yaml
name: Greedy
display_name: "[OPEN]"
difficulty: 3
description: >
  You always want your own four in a row as fast as possible. You love
  moves that build your lines and you get careless about defense.
signature: Prefer THREAT and WIN tags. Block only if you would lose next turn.
expected_metrics: { threat_rate: highest, block_rate: low }
```

### 3.9 Candidate builder (`c4d/candidates.py`) [PLANNED]
Each turn the engine scores every legal action with a shallow minimax search and tags it:

| Tag | Meaning |
|---|---|
| `WIN` | Wins immediately. |
| `BLOCK` | Stops an opponent line that would win next turn. |
| `THREAT` | Makes a new three-in-a-row with an open fourth cell. |
| `OPENS_RISK` | Gives the opponent a three-in-a-row with an open fourth cell. |
| `SHAKE_UP` | A twist that moves 6 or more pieces [OPEN: threshold]. |
| `QUIET` | None of the above. |

The list has up to 8 candidates: the best-scored moves, plus at least 2 drops and 2 twists when legal, so every persona has real options. For **Dumb**, the list is 8 random legal moves with tags hidden except `WIN`.

### 3.10 Validation and fallback
1. The model must return a `choose_move` call whose `candidate_id` is on this turn’s list.
2. If not (no call, wrong id, error, timeout), retry once with the reason added.
3. If the second attempt also fails, the **scripted version of the same persona** (`c4d/scripted_personas.py`) chooses the move. The trace labels it `fallback`.
4. The runner validates the final action with `engine.step()` as always (R8).

### 3.11 Limits: timeout, retry, spending

| Limit | Play mode | Evaluation mode (midterm E1) |
|---|---|---|
| Timeout per call | 8 s | 60 s (capped at time left) |
| Attempts per turn | 2, then scripted fallback | 2, then labeled fallback |
| Calls per game | 50 | 110 per model player |
| Clock per player | none | 15 min → loss (timeout) |
| Spend | ≈ $0.015 per game target; hard stop at 50 calls | Each eval run logs total tokens and cost; [OPEN: per-run dollar cap] |

### 3.12 Failure modes

| Failure | Detection | Response |
|---|---|---|
| Invalid or missing `candidate_id` | Validator | Retry once, then scripted fallback |
| Timeout / API error / no network | Runner timer, exception | Scripted fallback; if 3 in a row, switch the game to scripted mode and tell the player |
| Out of character (e.g. Conservative twisting a lot) | Style metrics over 20 games | Edit persona card; re-run eval |
| Personas look the same | Style metrics; blind-ID playtest | Strengthen signatures; merge or cut a persona |
| Too strong or too weak | Win rates vs. greedy bot and new players | Adjust candidate list or temperature |
| Cost overrun | Call counter, token log | Hard stop at 50 calls; fallback |

### 3.13 Evaluations [PLANNED]

| Evaluation | How | Pass |
|---|---|---|
| On-list rate | Share of turns answered validly on the first attempt | ≥ 95% |
| Latency | p50 / p95 over 50 calls | p95 ≤ 3 s |
| Style metrics | 20 games per persona vs. greedy on `suite.json`: twist, block, threat, risky-move rates | Personas differ in the expected direction (GDD §9) |
| Agent vs. scripted baseline (hypothesis test) | Blind-ID playtest: 6 players, 2 games each vs. an unnamed opponent, then match it to a persona | Agent matched correctly more often than baseline; plus “felt like a character” rating 1–5 |

**Scripted baseline** (`c4d/scripted_personas.py`): the same five personas as weighted minimax. Score = minimax value + weights × tags.

| Persona | Weights [OPEN: tune] |
|---|---|
| Greedy | THREAT +2.0, BLOCK +0.3 |
| Careful | BLOCK +3.0, OPENS_RISK −2.0 |
| Dumb | depth 1, 40% random move |
| Conservative | any twist −1.5 |
| Adventurous | any twist +1.0, SHAKE_UP +1.5 |

### 3.14 Logging
Every agent turn writes one line to `traces/<run>.jsonl`: game id, turn, persona, candidate list with tags, chosen id, `style_note`, attempts, fallback (yes/no), latency ms, input/output tokens, estimated cost. `scripts/summarize.py` builds the tables in `results/`. [PLANNED; trace format IMPLEMENTED in midterm]

### 3.15 Human override
- **Player:** can switch to scripted opponents at any time (setting on the select screen) [PLANNED].
- **Developer:** `--persona-mode scripted` forces the baseline; `--persona-mode agent` forces the model [PLANNED]. Removing the Vertex credentials also forces scripted mode.
- **Tech Lead (me):** approves every change to persona cards, system instructions, model id and limits; each change bumps the config version (§5).

## 4. Existing midterm agent: Gemini player [IMPLEMENTED]
`c4d/model_player.py`: prompt in, one action text out, no tools. Kept as a reference player for evaluation. It is replaced in play by the personality opponent.

## 5. Configuration versions

| Version | Date | Change | Approved by |
|---|---|---|---|
| midterm | 2026-11-08 | Gemini player; E1 limits | Yuki |
| v0.1 (this doc) | 2026-11-23 | Personality opponent design (planned) | Yuki |

Persona cards, `system.md` and `choose_move.json` each carry the config version in a header line, and every trace line records it.

## 6. Test commands and CI

```bash
# setup (Python 3.11+)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# deterministic tests: what CI runs (no network, no credentials)
python -m pytest -v

# web rules vs Python rules (manual, needs node)
python scripts/crosscheck_web.py --games 300

# evaluation (needs Vertex setup)
python scripts/evaluate.py --candidate minimax --opponent greedy --run baseline-vs-greedy
python scripts/evaluate.py --candidate persona:greedy --opponent greedy --run greedy-style   # [PLANNED]
python scripts/summarize.py > results/TABLE.md
```

**CI workflow:** `.github/workflows/ci.yml` [OPEN: confirm path] runs `python -m pytest -v` on every push. Planned new tests: `tests/test_candidates.py` (tags are correct), `tests/test_persona_player.py` (off-list answers fall back; agent never receives the engine), using a fake model so CI needs no network.

## 7. Production workflow
Agents work on branches; I review every pull request; CI must be green before merge. Agent recommendations and my decisions are logged in AGENT-TEAM.md.

## 8. Open questions

1. **[OPEN]** Exact Gemini model id, and its current price on Vertex AI.
2. **[OPEN]** The syllabus’s required manifest fields (§3.2).
3. **[OPEN]** Coding-agent tool used for the production roles, and the path of the midterm CI workflow.
4. **[OPEN]** Character art: tool or hand-made, and its terms.
5. **[OPEN]** `SHAKE_UP` threshold and baseline weights (tune after the first style-metrics run).
6. **[OPEN]** Per-run dollar cap for evaluation.
7. **[OPEN]** Is 8 candidates enough choice for personas to show, or too many for a fast model?
