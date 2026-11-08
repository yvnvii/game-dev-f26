# Twist Four: rule specification

Twist Four is Connect Four played inside a 4 × 4 × 4 cube whose slices can be twisted like a
Rubik's Cube. Pieces always fall to the bottom of their shaft, so every twist is followed by gravity.

Rule IDs (R1, R2, …) are the ones the rule/source map in `README.md` points to.
Rules decided by me are dated; the interactive demo (`web/index.html`) implements this spec.

---

## 1. Board and coordinates

**R1. The board** is a cube of 4 × 4 × 4 = 64 cells. A cell is `(x, y, z)`, each 0–3:

| Coordinate | Meaning | Names |
|---|---|---|
| `x` | column, left → right | A, B, C, D |
| `y` | row, front → back | 1, 2, 3, 4 (row 1 faces the player) |
| `z` | layer, bottom → top | L1 (bottom) … L4 (top) |

A **shaft** is the vertical stack of 4 cells with the same `(x, y)`, named like `B3`.
There are 16 shafts. Each cell is empty, X, or O.

**R2. Initial state.** All cells empty. X moves first. Turn counter = 1. No previous action.

## 2. Gravity

**R3. Gravity.** No piece may float. After any change to the board, every shaft is
*settled*: its pieces keep their bottom-to-top order and move down to fill the lowest cells.

## 3. Actions

On your turn you take exactly **one** action: a drop or a twist.

**R4. Drop.** Choose a shaft that is not full. Your piece goes into the lowest empty cell of
that shaft. Action text: `drop B3`. (16 possible drops.)

**R5. Twist.** Choose a **slice** of 16 cells and turn it 90°. Pieces in the slice move with
it; every other piece stays put. Then gravity (R3) settles the whole board. (24 possible twists.)

| Slice | Which cells | Directions | Action text |
|---|---|---|---|
| Layer `k` (L1–L4) | all cells with `z = k` | `cw` / `ccw`: clockwise / counter-clockwise, seen from above | `twist layer 2 cw` |
| Column slab (A–D) | all cells with `x = k` | `fwd`: top rolls toward row 1 · `back`: top rolls toward row 4 | `twist col B fwd` |
| Row slab (1–4) | all cells with `y = k` | `left`: top rolls toward A · `right`: top rolls toward D | `twist row 3 left` |

Exact cell mapping, where a piece in the slice at `(x, y, z)` moves to:

| Direction | New cell |
|---|---|
| layer `cw` | `(y, 3 − x, z)` |
| layer `ccw` | `(3 − y, x, z)` |
| col `fwd` | `(x, 3 − z, y)` |
| col `back` | `(x, z, 3 − y)` |
| row `left` | `(3 − z, y, x)` |
| row `right` | `(z, y, 3 − x)` |

Each pair (`cw`/`ccw`, `fwd`/`back`, `left`/`right`) are exact inverses of each other.

*Decided 2026-11-08: both horizontal and vertical slices can turn, as many times per game as players like.*

**R6. A twist must change the board.** A twist whose result (after gravity) is identical to the
current board is illegal. *Decided 2026-11-08: prevents using a twist to pass.*

**R7. No instant undo.** You may not make the exact inverse of the twist your opponent made on
the immediately previous turn (same slice, opposite direction). *Decided 2026-11-08: prevents
endless back-and-forth twisting.* Twisting the same slice the same way again is allowed.

**R8. Illegal actions** (full shaft, malformed text, wrong turn, game over, or a twist barred by
R6/R7) are rejected and change nothing.

## 4. Winning and ending

**R9. Lines.** A *line* is 4 cells in a straight row in any direction through the cube: along a
row, a column, a shaft, a planar diagonal, or one of the 4 space diagonals. There are **76** lines.

**R10. Winning by a drop.** If your drop completes a line of your pieces, you win.
(A drop can only complete lines for the player who dropped.)

**R11. Winning by a twist.** After a twist and gravity, check lines for both players:
- only yours → **you win**;
- **both players' → you (the twister) win**. *Decided 2026-11-08: rewards the risk of twisting.*
- only your opponent's → **your opponent wins**. *Decided 2026-11-08: a twist that hands the
  opponent a line loses.*

**R12. Turn limit.** If nobody has won after **100 turns** (drops and twists both count), the game
is a **draw**. *Decided 2026-11-08: twists are unlimited, so the game needs a guaranteed end.*

**R13. No legal action.** If the player to move has no legal action (only possible on a full board
where every twist is barred by R6/R7), the game is a **draw**.

**Scoring:** win = +1, loss = −1, draw = 0. Outcome reasons: `connect_four`, `turn_limit`,
`no_legal_actions`, plus the episode limits below (`timeout`, `call_limit`, `step_limit`).

### Episode limits

**E1. Episode limits** (enforced by the runner, not part of the board game). *Decided 2026-11-08,
after the independent review, before any Twist Four model run: blame must go to the player who used
the time.* This replaces the earlier single 30-minute episode timeout, which ended the game with no
winner whoever was slow.
- **Clock:** each player has **15 minutes** of thinking time for the whole episode. It counts the time
  inside that player's own move calls, retries included. If it runs out, that player **loses**
  (reason `timeout`). A move that arrives after the clock ran out is discarded, even a winning one.
  A model call is cut off at 60 s or at the time left on the clock, whichever is shorter.
- **Call limit:** a model player that has used its **110 calls** (failed calls count) **loses**
  (reason `call_limit`).
- **Per call:** 60 s. A call that times out counts as a failed call.
- **Attempts:** 2 per turn. After that the runner plays a labeled fallback move (most central legal
  drop) for that player.
- **Step limit:** 100 accepted actions, a backstop behind R12. It ends the game with **no winner**
  (reason `step_limit`).
- Human games (`scripts/play.py`) use a clock of a year, so people are never timed out.

## 5. What each player knows

**R14. Fully observed.** Both players see the whole board, whose turn it is, the turn counter, and
the previous action (needed for R7). There is no hidden information, so the legal-action list
reveals nothing a player could not work out from the board.

---

## Worked examples

**Layer twist.** X has pieces at A1 L1 and A1 L2; O has B1 L1. X twists `layer 1 cw`.
The two L1 pieces move: A1 → A4, B1 → A3. The piece left at A1 L2 has nothing under it and falls to
A1 L1. Result: X at A1 L1, O at A3 L1, X at A4 L1.

**Slab twist.** Same starting board, X twists `col A fwd`. Shaft A1 (row 1) lies down along the
bottom of slab A with its top end at the front: A1 L1 → A4 L1 and A1 L2 → A3 L1.
O at B1 is not in slab A and stays.

## Credits

- **Connect Four** (Howard Wexler and Ned Strongin; Milton Bradley, 1974; now Hasbro): drop and gravity, four in a row.
- **Score Four** (1967): four in a row in a 4 × 4 × 4 grid.
- **Rubik's Cube** (Ernő Rubik, 1974): turning slices of a cube. Used as an idea only; no names,
  logos or artwork are copied, and the game is not affiliated with the Rubik's brand.
