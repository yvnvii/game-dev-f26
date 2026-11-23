# Twist Four — Game Design Document (Initial, G1)

**Owner:** Yuki Ogawa (Creative Director, Design Lead) · **Gate approver:** instructor · **Version:** Initial, 2026-11-23
**Companion docs:** [CONFIGURATION.md](CONFIGURATION.md) (agents and roles) · [PROJECT-PLAN.md](PROJECT-PLAN.md) · [RULES.md](RULES.md) (full rules R1–R14, E1)

### Status labels used in this document

| Label | Meaning |
|---|---|
| **[VERIFIED]** | Built and checked by a test, a script or a playtest; the evidence is named. |
| **[IMPLEMENTED]** | Built in the repository, not yet checked beyond running it. |
| **[PLANNED]** | Decided, not built yet. |
| **[OPEN]** | Not decided yet. Every open question is also listed in section 17. |

---

## 1. Summary

**The X:** The player drops pieces or twists layers of a 4 × 4 × 4 cube to make four in a row, and should feel they are competing with a rival, not a machine.

Twist Four is Connect Four inside a 4 × 4 × 4 cube whose slices turn like a Rubik’s Cube. On each turn you either drop a piece into one of 16 shafts or twist one of 12 slices a quarter turn, and gravity re-settles every piece. Four in a line wins. The midterm built the complete game, a minimax opponent and one Gemini player. G1 adds a **cast of five AI opponents with personalities** that the player picks from, each with its own character design.

## 2. Player, genre, platform

| | |
|---|---|
| **Player** | Strategy and puzzle players who know Connect Four and enjoy a short head-to-head game, from beginners to people who want a real fight. |
| **Motivation** | The thrill of a twist that wins out of nowhere, and of learning how a rival thinks and using it against them. |
| **Observable hypothesis** | If the game works, playtesters (1) pause before a twist and predict out loud where pieces will land, (2) block a new threat on their very next turn, (3) describe opponents by personality (“Adventurous always twists”), and (4) choose a different opponent for the rematch. [PLANNED: measured in the G2 playtest] |
| **Genre** | Abstract strategy, two-player, perfect information, turn-based. |
| **Platform** | Desktop web browser (`web/index.html`, three.js, no install) [IMPLEMENTED]. Terminal version (`scripts/play.py`) [IMPLEMENTED], kept for testing and evaluation. |
| **Session length** | One game takes about 5–10 minutes [OPEN: measure]; a session is about 3 games. |

## 3. Intended aesthetics (MDA)

1. **Challenge:** outthinking an opponent on a board that can flip in one move.
2. **Fantasy (rivalry):** opponents feel like characters with a style, not difficulty levels.
3. **Discovery:** learning each opponent’s habits and the strange geometry of twists.

**Pillars**
1. **Every turn can flip the board.** A single twist can move up to 16 pieces and make or break several of the 76 lines.
2. **Chaos you can read.** After any twist the player can take their time, rotate the cube and see what changed.
3. **Assist.** Predicting a twist is very hard, so an optional mode lights up potential threats.

## 4. Core loop

| Step | What happens |
|---|---|
| **Act** | Drop a piece into one of 16 shafts, or twist one of 12 slices a quarter turn. |
| **Respond** | Gravity re-settles every piece. The AI opponent answers in character; its portrait reacts. |
| **Interpret** | Changed lines glow. The player scans for rows waiting for “one more” and reads the opponent’s move as personality. |
| **Next action** | Block the new threat, set up a twist that completes your own line, or exploit the opponent’s habit. |

Outer loop: pick an opponent → play → see the result and your record against that opponent → pick again.

## 5. A valid play session (walkthrough)

1. The player opens `web/index.html`. The **opponent-select screen** [PLANNED] shows five portraits with name, personality and difficulty, plus the player’s record against each.
2. The player picks **Greedy** and chooses to play X (first) or O.
3. X drops into shaft B3; the piece falls to the lowest empty cell (R4).
4. Greedy’s portrait shows a “thinking” pose while the agent chooses (≤ 3 s target). Greedy drops to start its own line.
5. On turn 7 the player twists layer 2 clockwise. All pieces in that layer rotate 90°, then gravity settles every piece (R5, R3). The changed lines glow.
6. Greedy sees a move that builds its own three-in-a-row and takes it, leaving the player’s threat open (its signature habit).
7. The player completes four in a row and wins (R10). The end screen shows the winning line, the result, and the updated record. The player picks **Careful** for the rematch.

## 6. Mechanics (rules summary)

The full specification is in [RULES.md](RULES.md); the rules are implemented as pure functions in `c4d/rules.py` and enforced by tests in `tests/`. **[VERIFIED: `python -m pytest -v`; web and Python rules cross-checked on 300 games, 10,609 steps, 0 mismatches, 2026-11-08]**

| Rule | Summary |
|---|---|
| R1 | 4 × 4 × 4 cube: 16 shafts, 4 layers. |
| R2 | Empty start; X moves first. |
| R3 | Gravity: pieces fall to the bottom of their shaft, also after every twist. |
| R4 | Drop into a non-full shaft; the piece lands on top. |
| R5 | Twist one layer or vertical slab 90°, then gravity. 24 twists (4 layers + 8 slabs, both directions). |
| R6 | A twist must change the board (no passing). |
| R7 | No exact undo of the opponent’s previous twist. |
| R8 | Illegal actions are rejected and change nothing. |
| R9 | Four in a straight line in any of the 76 lines. |
| R10 | A drop that completes your line wins. |
| R11 | After a twist: your line only → you win; both players’ lines → the twister wins; opponent’s only → opponent wins. |
| R12 | No winner after 100 turns → draw. |
| R13 | No legal action → draw. |
| R14 | Fully observed; the previous action is visible. |

**New in G1 [PLANNED]:** opponent selection, five personality opponents, character portraits, assist highlighting, per-opponent records.

## 7. Dynamics (what play should look like)

- **Threat chains:** a twist can create several threats at once, so players start looking for “double threat” twists.
- **Bait:** players leave a line open on purpose to lure Greedy, or play slowly to out-wait Conservative.
- **Board reading:** players rotate the cube after each opponent twist before moving. If they stop doing this and just move, the board has become too hard to read (see risk in section 15).
- **Style differences:** against Adventurous, games are short and swingy; against Careful and Conservative, long and tight. [OPEN: verify with style metrics, section 9]

## 8. The opponents (content)

Each opponent is a **persona card** (a short text description plus a signature habit) used by the AI agent. How the agent works is in [CONFIGURATION.md](CONFIGURATION.md).

| Opponent | Personality | Signature habit (visible within ~3 turns) | Difficulty | Character design |
|---|---|---|---|---|
| **Dumb** | Misses threats, sometimes plays almost at random. | Ignores a threat you set up on turn 3–5. | 1 (easiest) | [OPEN: name, look] |
| **Conservative** | Rarely twists; prefers drops and a stable board. | Drops on its first several turns. | 2 | [OPEN: name, look] |
| **Greedy** | Always grabs the move that builds its own line fastest, even if it leaves a hole. | Builds its own line instead of blocking yours. | 3 | [OPEN: name, look] |
| **Adventurous** | Loves big twists that shake up the cube, even risky ones. | Twists on its first or second turn. | 3 | [OPEN: name, look] |
| **Careful** | Blocks every threat before it attacks. | Always blocks an open three-in-a-row. | 4 (hardest) | [OPEN: name, look] |

**Character design [PLANNED]:** one portrait per opponent, with three states: idle, thinking, and reacting (after a win, loss, or big twist). Cut-first version: one still image per character. [OPEN: art made by hand or with a tool; if a tool, record its terms in section 16.]

## 9. Progression, scoring, balance

**Progression [PLANNED]:** no campaign. Opponents are ordered by difficulty on the select screen. The player’s win/draw/loss record against each opponent is saved locally in the browser. [OPEN: unlock order, or all five open from the start?]

**Scoring:** win = 1, draw = 0.5, loss = 0 (the midterm `outcome()` score) [IMPLEMENTED].

**Win / failure conditions**
- Win: four in a row by a drop (R10) or by a twist (R11).
- Loss: the opponent makes four in a row, or your twist completes only the opponent’s line (R11).
- Draw: 100 turns without a winner (R12), or no legal action (R13).

**Balance targets [OPEN: to measure, then tune]**
- A new player should beat Dumb in most games and rarely beat Careful.
- **Style metrics** per opponent, over 20 games against the greedy bot on the declared suite (`suite.json`):

| Metric | Expected pattern |
|---|---|
| Twist rate (twists ÷ moves) | Adventurous highest; Conservative lowest. |
| Block rate (blocks ÷ turns facing an open three) | Careful near 100%; Greedy and Dumb low. |
| Threat-creation rate | Greedy highest. |
| Risky-move rate (moves that give the opponent a threat) | Adventurous and Dumb highest; Careful lowest. |

## 10. Controls

| Platform | Action | Control |
|---|---|---|
| Web | Drop | Click a shaft on the top of the cube [IMPLEMENTED; OPEN: confirm the exact control in `web/index.html`] |
| Web | Twist | Drag a layer or slab (drag-to-twist) [IMPLEMENTED] |
| Web | Look around | Drag empty space to rotate the camera [IMPLEMENTED] |
| Web | Assist on/off | Toggle button [PLANNED] |
| Web | Pick opponent | Click a portrait on the select screen [PLANNED] |
| Terminal | Drop / twist | Type `B3`, `twist layer 2 cw`, `twist col B fwd`, `twist row 3 left`; `?` lists all [IMPLEMENTED] |

## 11. Feedback

- Pieces animate as they fall and as slices turn [IMPLEMENTED].
- The last action is shown in text (needed for R7) [IMPLEMENTED].
- Changed lines glow after a twist [PLANNED].
- Assist mode: open three-in-a-rows glow for both players [PLANNED].
- Opponent portrait: thinking pose while the agent chooses, reaction after big moments [PLANNED].
- An illegal move shows the engine’s reason (e.g. “shaft B3 is full”, “that twist undoes the last one”) and changes nothing [IMPLEMENTED].
- End screen: the winning line is highlighted; record updates [PLANNED].

## 12. Edge cases

| Case | Handling |
|---|---|
| A twist completes lines for both players | The twister wins (R11). [VERIFIED: `test_twist_making_both_lines...`] |
| A twist completes only the opponent’s line | The opponent wins (R11). [VERIFIED] |
| A twist completes two lines for the winner | Valid; either line may be shown. The cross-check counts these separately. [VERIFIED: crosscheck, 2 cases] |
| A twist that changes nothing | Illegal (R6). [VERIFIED] |
| Undoing the opponent’s last twist | Illegal (R7); repeating it later is legal. [VERIFIED] |
| Full shaft, malformed text, out-of-turn move | Rejected with a reason; nothing changes (R8). [VERIFIED] |
| 100 turns, no winner | Draw (R12). [VERIFIED] |
| No legal action | Draw (R13). [VERIFIED] |
| AI opponent is slow or gives an invalid answer | In play: the scripted version of that personality moves instead, and the move is labeled as a fallback in the trace. In evaluation: E1 limits apply. [PLANNED] |
| Network or API unavailable | The whole game switches to the scripted personalities; a small notice tells the player. [PLANNED] |

## 13. Content scope

**Included:** the complete midterm game; five personality opponents with persona cards; the candidate builder; scripted baselines for each persona; an opponent-select screen; five character portraits with simple reactions; assist highlighting; logging of moves, latency and cost.

**Excluded:** opponents that talk or chat; animated characters; voice and sound; network play; boards other than 4 × 4 × 4; 180° twists.

**Cut first, in order:** (1) cast from 5 to 3 (Greedy, Careful, Adventurous); (2) one still image per character instead of reactions; (3) vertical-slab twists (keep the 4 layer twists).

## 14. Budgets

| Budget | Target | Basis |
|---|---|---|
| Latency per opponent move | ≤ 3 s at p95; fallback after 8 s | A person takes a few seconds per move, and the thinking pose covers the wait. [OPEN: not measured yet] |
| Cost per session | ≈ $0.05 for 3 games; cap 50 calls per game | ~20 opponent moves per game × ~2,000 input + 30 output tokens ≈ $0.015 per game at $0.30 / $2.50 per million tokens. [OPEN: check current Vertex price] |

## 15. Risk summary

The full Risk Register moves to Asana at G2/G3. Summary from the G1 pitch:

| Dimension | Rating | Evidence | Mitigation |
|---|---|---|---|
| IP / Concept | Low | Rules and ideas only; every source attributed. | Keep the attribution table current; record art terms. |
| Business / Audience | Medium | Niche audience; no evidence yet that players care about personality. | Early 5–6 player playtest. |
| Technology | **High** | LLMs often misread 3D grids. | Agent picks only from engine-checked, tagged candidates; validator; scripted fallback. |
| Team | Medium | Solo developer with an AI agent team. | Clear role coverage (CONFIGURATION.md §2). |
| Genre / Mechanics | **High** | One twist can move up to 16 pieces, which can hide personality. | Each persona gets a signature habit visible within 3 turns; merge or cut personas players can’t tell apart. |
| Timeline | Low | Most of the game is already built. | Cut list in section 13. |

**The two Highs share one cause:** the board after a twist is hard to read, for the model and for the player.

## 16. References and attribution

| Source | Borrowed (specific) | Changed | Terms |
|---|---|---|---|
| Connect Four (Howard Wexler and Ned Strongin; Milton Bradley 1974, now Hasbro) | Rules sheet (UK edition, © 2008, code 01081), p. 2 “How to Play” step 2: drop into any slot; gravity; four in a row | 3D cube, twists, gravity after twists, R11 | Rules only; no text, art or trademarks |
| Score Four (1967) | Four in a row in a 4 × 4 × 4 grid (76 lines) | Adds gravity and twisting slices | Idea only |
| Rubik’s Cube (Ernő Rubik, 1974) | Turning one slice of a cube 90° | 12 slices only; pieces fall after each turn | No name, logo or art; not affiliated |
| [OPEN: a game with opponent selection by personality] | [the specific moment] | [what changes] | Idea only |
| three.js 0.160.0 | 3D rendering (CDN) | Not modified | MIT |
| google-genai | Gemini API client | Not modified | Apache-2.0 |
| pytest | Tests | Not modified | MIT |
| Character art | [OPEN] | — | [OPEN] |

All code is original, written with my AI agent team under my direction (see CONFIGURATION.md and AGENT-TEAM.md).

## 17. Open questions

1. **[OPEN]** Character names and looks; how the art is made, and its terms.
2. **[OPEN]** Are all five opponents available from the start, or unlocked in order?
3. **[OPEN]** Can a cheap Flash-class model show personality clearly enough for players to tell opponents apart? (G2 blind-ID playtest)
4. **[OPEN]** Real latency per opponent move (first prototype task: measure p50/p95 on 50 calls).
5. **[OPEN]** Average game length in turns; this changes the cost estimate.
6. **[OPEN]** Will Careful and Conservative look different enough, or should one be merged or replaced?
7. **[OPEN]** Is assist mode on by default for new players?
8. **[OPEN]** Which game is the reference for picking a rival by personality?
