# Human playtest notes

- **Date / build (commit):**
2026-11-08, web version (web/index.html)

- **Player:**
Player: a friend who had never played 3D Connect Four but has played normal (2D, non-rotating) Connect Four.

- **Setup:** 
I watched without helping. They played X (red, first) against the computer at Medium and Easy.

- **What they did:**
At first they played it like a normal Connect Four. They only dropped pieces and did not twist. Then the AI twisted and won, and they realized they had to rotate to win. After that they took more time to think before placing a piece, and they started thinking about where the pieces would end up if they rotated.

- **Where they hesitated or guessed:**
After they understood twists, they slowed down before each move, because they had to imagine how the board would look after a twist (which pieces move, and where gravity drops them).

- **What I changed, or would change:**
I made twisting in the web version more intuitive. Players can drag across the cube to twist a slice, like a real Rubik's Cube, and the slice follows their finger before they let go. This makes it easier to simulate and see how the board will look if they rotate before committing to the twist.

- **What I learned:**
The twist mechanic is not obvious to a new player, even one who knows Connect Four, but it is learnable from one game. The Gemini player also played it like a normal Connect Four and almost never twisted (about 2% of its moves), but unlike my friend it did not learn from losing, because each model call starts fresh.
