"""Model-driven player. The model gets a text prompt (rules + observation + legal moves) and
returns text. It has no tools: no files, no shell, no access to the engine or runner.
The runner, not this class, validates the move and enforces budgets.
"""
from __future__ import annotations

import os
import re
import time

from .players import Player

RULES = """You are playing Twist Four: Connect Four inside a 4x4x4 cube whose slices can turn like a Rubik's Cube.

The cube
- Columns A-D run left to right, rows 1-4 run front to back (row 1 is nearest you), layers L1-L4 run
  bottom to top. A shaft is a vertical stack of 4 cells, named like B3.
- Gravity: pieces always rest at the bottom of their shaft. No piece ever floats.

On your turn, take exactly ONE action:
1. Drop: put your piece in a shaft that is not full; it falls to the lowest empty cell.
   Text: "drop B3"
2. Twist: turn one slice of 16 cells by 90 degrees; the pieces in it move with it. Then gravity pulls
   every piece in the cube down its shaft.
   - "twist layer K cw" / "twist layer K ccw": turn layer K (1-4) clockwise / counter-clockwise, seen from above.
   - "twist col C fwd" / "twist col C back": turn the vertical slab of column C (A-D) so its top rolls
     toward row 1 / toward row 4.
   - "twist row R left" / "twist row R right": turn the vertical slab of row R (1-4) so its top rolls
     toward column A / toward column D.
   A twist must change the board, and you may not exactly undo the twist your opponent just made.

Winning
- Four of your pieces in a straight line wins: along a row, a column, a shaft, or any diagonal,
  including diagonals through all four layers (76 lines in total).
- After a twist: if it makes a line for both players, the player who twisted wins; if it makes a line
  only for the opponent, the opponent wins.
- No winner after 100 turns (drops and twists both count): draw."""

PROMPT_VERSIONS = ("v1", "v2")

# v2 (2026-11-08, tuned on T1-T3 only; see EVALUATION.md "Prompt v2"). Only a restatement of the
# observation and a generic checking order: no move is evaluated or singled out for the model.
CHECK_ROUTINE = ("Before answering, check in this order: (1) every legal action, twists included, for one that "
                 "gives you four in a line right now (remember gravity settles every shaft after a twist); "
                 "(2) every drop or twist your opponent could make next turn that would win, and stop it; "
                 "(3) only then build toward your own lines. Do not ignore twists.")

_SYM = {0: ".", 1: "X", 2: "O"}
_COLS = "ABCD"


def board_listing(obs: dict) -> list[str]:
    """v2 board reading aid: the observed board re-listed shaft by shaft, then each side's cells.
    Pure re-formatting of obs["board"] (board[x][y][z]); the model misread the layer grids in v1."""
    b, n = obs["board"], len(obs["board"])
    me = obs["you_are"]
    lines, mine, theirs = ["Shafts (bottom to top):"], [], []
    for y in range(n):                       # same order as the drop actions: A1, B1, C1, D1, A2, ...
        for x in range(n):
            name = f"{_COLS[x]}{y + 1}"
            stack = [b[x][y][z] for z in range(n) if b[x][y][z]]
            lines.append(f"{name}: " + (" ".join(_SYM[v] for v in stack) if stack else "empty"))
            for z in range(n):
                if b[x][y][z]:
                    (mine if b[x][y][z] == me else theirs).append(f"{name} L{z + 1}")
    lines.append("Your pieces: " + (", ".join(mine) if mine else "none"))
    lines.append("Opponent's pieces: " + (", ".join(theirs) if theirs else "none"))
    return lines


MOVE_RE = re.compile(r"MOVE:[ \t]*([^\n]+)", re.IGNORECASE)


def build_prompt(obs: dict, legal: list[str], history: list[str] | None, feedback: str | None,
                 prompt_version: str = "v1") -> str:
    """v1 is frozen (byte-for-byte, tests/data/prompt_v1_*.txt). v2 adds board_listing() after the
    grids and CHECK_ROUTINE before the MOVE instruction; nothing else differs."""
    if prompt_version not in PROMPT_VERSIONS:
        raise ValueError(f"unknown prompt_version {prompt_version!r}")
    v2 = prompt_version == "v2"
    me, opp = obs["your_symbol"], ("O" if obs["your_symbol"] == "X" else "X")
    parts = [RULES, "",
             f"You are {me}. Your opponent is {opp}. Empty cells are '.'.",
             f"Turn {obs['turn']} of {obs['turn_limit']}.",
             "Last action: " + (f"{obs['last_action_by']} played \"{obs['last_action']}\"" if obs["last_action"] else "none (first turn)"),
             "", "Current board (each layer seen from above; row 1 is at the bottom of each grid):",
             obs["board_text"], ""]
    if v2:
        parts += board_listing(obs) + [""]
    if history is not None:
        parts.append("Actions so far (oldest first, X moved first): " + (", ".join(history) if history else "none"))
        parts.append("")
    parts.append("Legal actions: " + ", ".join(legal))
    if feedback:
        parts.append(f"\nYour previous reply was rejected: {feedback}")
    if v2:
        parts.append("\n" + CHECK_ROUTINE)
    parts.append("\nThink briefly, then end your reply with exactly one line of the form\n"
                 "MOVE: <one legal action, copied exactly>\nfor example\nMOVE: drop B3")
    return "\n".join(parts)


def parse_move(text: str) -> str | None:
    """The text after the last 'MOVE:' on its line, or None. The engine validates it."""
    found = MOVE_RE.findall(text or "")
    if not found:
        return None
    return found[-1].strip(" \t`*'\".") or None


class ModelPlayer(Player):
    """Gemini on Vertex AI via the google-genai SDK.

    Env: GOOGLE_CLOUD_PROJECT (required), GOOGLE_CLOUD_LOCATION (default 'global').
    history_mode: 'none' (observation only) or 'moves' (bounded move list, last `history_len` moves).
    prompt_version: 'v1' (default, untuned) or 'v2' (see build_prompt).
    """
    is_model = True

    def __init__(self, model: str = "gemini-3.5-flash-lite", history_mode: str = "none",
                 history_len: int = 16, temperature: float = 0.2, max_output_tokens: int = 4096,
                 prompt_version: str = "v1"):
        if prompt_version not in PROMPT_VERSIONS:
            raise ValueError(f"unknown prompt_version {prompt_version!r}")
        self.model = model
        self.history_mode = history_mode
        self.history_len = history_len
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.prompt_version = prompt_version
        self.name = f"model:{model}:{history_mode}:{prompt_version}"
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google import genai  # imported lazily so tests never need credentials
            self._client = genai.Client(
                vertexai=True,
                project=os.environ["GOOGLE_CLOUD_PROJECT"],
                location=os.environ.get("GOOGLE_CLOUD_LOCATION", "global"),
            )
        return self._client

    def choose(self, obs, legal, feedback=None, history=None):
        hist = None
        if self.history_mode == "moves":
            hist = (history or [])[-self.history_len:]
        prompt = build_prompt(obs, legal, hist, feedback, self.prompt_version)
        from google.genai import types
        t0 = time.monotonic()
        resp = self._get_client().models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=self.temperature,
                                               max_output_tokens=self.max_output_tokens),
        )
        latency = time.monotonic() - t0
        text = resp.text or ""
        um = getattr(resp, "usage_metadata", None)
        cands = getattr(resp, "candidates", None) or []
        finish = getattr(cands[0], "finish_reason", None) if cands else None
        finish = getattr(finish, "name", None) or (str(finish) if finish is not None else None)
        return {
            "action": parse_move(text),
            "raw": text,   # full reply (logging only); runs before 2026-11-08 v2 kept the last 600 chars
            "latency_s": round(latency, 3),
            "input_tokens": getattr(um, "prompt_token_count", 0) or 0,
            "output_tokens": (getattr(um, "candidates_token_count", 0) or 0)
                             + (getattr(um, "thoughts_token_count", 0) or 0),
            "model_version": getattr(resp, "model_version", None),
            "finish_reason": finish,   # "MAX_TOKENS" means the reply was cut off by the output limit
        }
