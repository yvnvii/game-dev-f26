"""Model-driven player. The model gets a text prompt (rules + observation + legal moves) and
returns text. It has no tools: no files, no shell, no access to the engine or runner.
The runner, not this class, validates the move and enforces budgets.
"""
from __future__ import annotations

import os
import re
import time

from .players import Player

RULES = """You are playing 3D Connect Four on a 4x4x4 cube.
- The cube has 16 vertical shafts named A1..D4 (letter = column A-D, digit = row 1-4).
- On your turn you drop one piece into a shaft that is not full; it falls to the lowest empty layer.
- Layer z=1 is the bottom, z=4 the top.
- You win by making 4 of your pieces in a straight line in any direction: along a row, a column,
  a vertical shaft, or any diagonal, including diagonals that cross all four layers.
- If all 64 cells fill with no line, the game is a draw."""

MOVE_RE = re.compile(r"MOVE:\s*([A-Da-d][1-4])")


def build_prompt(obs: dict, legal: list[str], history: list[str] | None, feedback: str | None) -> str:
    parts = [RULES, "", f"You are {obs['your_symbol']} (player {obs['you_are']}). Opponent pieces are "
             f"{'O' if obs['your_symbol'] == 'X' else 'X'}. Empty cells are '.'.",
             f"Move number: {obs['move_number']}", "", "Current board:", obs["board_text"], ""]
    if history is not None:
        parts.append("Moves so far (oldest first): " + (", ".join(history) if history else "none"))
        parts.append("")
    parts.append("Legal moves: " + ", ".join(legal))
    if feedback:
        parts.append(f"\nYour previous reply was rejected: {feedback}")
    parts.append("\nThink briefly, then end your reply with exactly one line of the form  MOVE: <shaft>"
                 "  for example  MOVE: B3")
    return "\n".join(parts)


def parse_move(text: str) -> str | None:
    found = MOVE_RE.findall(text or "")
    return found[-1].upper() if found else None


class ModelPlayer(Player):
    """Gemini on Vertex AI via the google-genai SDK.

    Env: GOOGLE_CLOUD_PROJECT (required), GOOGLE_CLOUD_LOCATION (default 'global').
    history_mode: 'none' (observation only) or 'moves' (bounded move list, last `history_len` moves).
    """
    is_model = True

    def __init__(self, model: str = "gemini-3.5-flash-lite", history_mode: str = "none",
                 history_len: int = 16, temperature: float = 0.2, max_output_tokens: int = 1024):
        self.model = model
        self.history_mode = history_mode
        self.history_len = history_len
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.name = f"model:{model}:{history_mode}"
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
        prompt = build_prompt(obs, legal, hist, feedback)
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
        return {
            "action": parse_move(text),
            "raw": text[-600:],
            "latency_s": round(latency, 3),
            "input_tokens": getattr(um, "prompt_token_count", 0) or 0,
            "output_tokens": (getattr(um, "candidates_token_count", 0) or 0)
                             + (getattr(um, "thoughts_token_count", 0) or 0),
            "model_version": getattr(resp, "model_version", None),
        }
