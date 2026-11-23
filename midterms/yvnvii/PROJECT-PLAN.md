# Twist Four — Initial Project Plan (G1)

**Owner:** Yuki Ogawa · **Version:** Initial, 2026-11-23
After G1 this plan moves into Asana, where owners, acceptance criteria, dependencies and the full Risk Register follow at G2/G3.

## Gate dates

| Gate | Question | Date | Status |
|---|---|---|---|
| G1 Concept pitch | Is the idea clear and achievable enough for prototype work? | Post due Nov 15; review Nov 16 | Submitted late, Nov [__] (instructor emailed Nov 23) |
| G2 | [from syllabus] | [date] | Upcoming |
| G3 | [from syllabus] | [date] | — |
| G4 Final | [from syllabus] | [date] | — |

## First tasks through G2

Owner: **Y** = Yuki (me). Agent roles are defined in [CONFIGURATION.md](CONFIGURATION.md) §2; I approve all agent work.

### Week 1 · Nov 23–29: finish G1, start the agent

| # | Task | Owner | Done when | Depends on |
|---|---|---|---|---|
| 1 | Record the pitch (3–5 min) and post the G1 thread with all links | Y | Thread posted with recording, deck, GDD, Config Doc, plan | — |
| 2 | Email the instructor about late G1 and the missed replies | Y | Email sent | — |
| 3 | Write the five persona cards | Y (Design Lead) | 5 YAML files in `agents/opponent/personas/` | — |
| 4 | Build the candidate builder with tags | Opponent AI Engineer agent | `c4d/candidates.py` + `tests/test_candidates.py` pass in CI | — |
| 5 | Confirm the model id and the current Vertex price | Y | Budget numbers updated in GDD §14 | — |

### Week 2 · Nov 30–Dec 6: the opponent works

| # | Task | Owner | Done when | Depends on |
|---|---|---|---|---|
| 6 | Build the personality opponent (`choose_move`, validator, fallback) | Opponent AI Engineer agent | `tests/test_persona_player.py` passes with a fake model | 3, 4 |
| 7 | Build the five scripted baselines | Opponent AI Engineer agent | `c4d/scripted_personas.py`; each persona plays a full game | 4 |
| 8 | Add latency and cost logging to traces | Opponent AI Engineer agent | Trace lines include latency, tokens, cost | 6 |
| 9 | **Measure latency and cost** on 50 calls | Y | p50/p95 and cost per game in `results/`; budgets confirmed or revised | 6, 8 |
| 10 | Write the manifest and confirm the syllabus fields | Y (Tech Lead) | `agents/opponent/manifest.yaml` complete | 6 |

### Week 3 · Dec 7–13: personas are different, players can pick

| # | Task | Owner | Done when | Depends on |
|---|---|---|---|---|
| 11 | Style-metrics evaluation: 20 games per persona vs. greedy | Opponent AI Engineer agent → Y reviews | Table in `results/`; personas differ as expected (GDD §9), or a fix is planned | 6, 7 |
| 12 | Opponent-select screen and placeholder portraits in the web version | Frontend / 3D agent | Player can pick any persona in the browser; crosscheck still 0 mismatches | 6 |
| 13 | Changed-line glow and assist mode | Frontend / 3D agent | Both toggle on/off; manual check | — |
| 14 | Character art direction (names, looks, method, terms) | Y (Creative Director) | GDD §8 and §16 filled in | — |

### Before G2: playtest and gate materials

| # | Task | Owner | Done when | Depends on |
|---|---|---|---|---|
| 15 | Blind-ID playtest: 6 players, agent vs. scripted baseline | Y, with Playtest Analyst agent | Accuracy and “felt like a character” ratings in `results/playtest-g2.md` | 11, 12 |
| 16 | Move plan into Asana; start the full Risk Register | Y, with Producer agent | Asana project with owners, acceptance criteria, dependencies | — |
| 17 | Update GDD and Configuration Document to “Update (G2)” | Y | Statuses changed from PLANNED to IMPLEMENTED or VERIFIED where true | 9–15 |

## If time runs short (cut order, from GDD §13)

1. Cast from 5 to 3 (Greedy, Careful, Adventurous).
2. One still image per character instead of reactions.
3. Vertical-slab twists (keep the 4 layer twists).

## Top risks to watch before G2

- **Technology (High):** the agent can’t show personality or stay fast → tasks 9 and 11 come early so I find out first.
- **Genre / Mechanics (High):** personas look the same on a twisting board → task 11 checks it before the playtest.
