"""Build the comparison table (Markdown) from results/*/summary.json.

Cost is computed from prices.json, which you fill in with the provider's published price on the
day you ran the evaluation (dated cost). Run from midterms/yvnvii/:
  python scripts/summarize.py > results/TABLE.md
"""
import glob
import json
import os

prices = json.load(open("prices.json")) if os.path.exists("prices.json") else {}


def cost(model, tin, tout):
    p = prices.get("models", {}).get(model or "")
    if not p or p.get("input_per_1m") is None:
        return "n/a"
    return f"${(tin * p['input_per_1m'] + tout * p['output_per_1m']) / 1e6:.4f}"


print(f"Prices from prices.json, dated {prices.get('date', 'NOT SET')}.\n")
LIMITS = ("timeout", "call_limit")    # rule E1: a loss for the player who hit the limit


def limit_endings(eps):
    """E1 endings per side, e.g. 'cand timeout:1; opp call_limit:2', so a limit loss never hides in W/L."""
    counts = {}
    for e in eps:
        if e["reason"] in LIMITS:
            who = "cand" if e["result"] == "loss" else "opp"
            key = f"{who} {e['reason']}"
            counts[key] = counts.get(key, 0) + 1
    return "; ".join(f"{k}:{v}" for k, v in sorted(counts.items())) or "none"


print("| run | cases | episodes | W / D-none / L | terminal reasons | limit losses (E1) | illegal attempts | "
      "fallbacks | failed calls | calls | mean latency (s) | candidate clock used, max (s) | tokens in / out "
      "| est. cost |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for path in sorted(glob.glob("results/*/summary.json")):
    s = json.load(open(path))
    m, eps = s["meta"], s["episodes"]
    if not eps:
        continue
    res = [e["result"] for e in eps]
    reasons = {}
    for e in eps:
        reasons[e["reason"]] = reasons.get(e["reason"], 0) + 1
    c = [e["candidate"] for e in eps]
    lat = [x["mean_latency_s"] for x in c if x["mean_latency_s"] is not None]
    clocks = [x["clock_used_s"] for x in c if x.get("clock_used_s") is not None]   # absent before E1
    tin, tout = sum(x["input_tokens"] for x in c), sum(x["output_tokens"] for x in c)
    cases = sorted({e["case"] + ("*" if e["heldout"] else "") for e in eps})
    # A run where every call failed has no latencies; print the row anyway, so its call_limit losses show.
    print(f"| {m['run']} ({m['candidate']} vs {m['opponent']}, v{m['game_version']}, {m['date'][:10]}) "
          f"| {', '.join(cases)} | {len(eps)} | {res.count('win')} / {res.count('draw/none')} / "
          f"{res.count('loss')} | {', '.join(f'{k}:{v}' for k, v in reasons.items())} | {limit_endings(eps)} | "
          f"{sum(x['illegal_attempts'] for x in c)} | {sum(x['fallback_moves'] for x in c)} | "
          f"{sum(x['failed_calls'] for x in c)} | {sum(x['calls'] for x in c)} | "
          f"{f'{sum(lat) / len(lat):.3f}' if lat else 'n/a'} | {f'{max(clocks):.1f}' if clocks else 'n/a'} | "
          f"{tin} / {tout} | {cost(m.get('model'), tin, tout) if m['candidate'] == 'model' else '$0'} |")
print("\n`*` = held-out case. W/D/L are from the candidate's side. Under rule E1 (decided 2026-11-08), "
      "`timeout` and `call_limit` endings are losses for the player who ran out and are counted in W/L; "
      "'limit losses' says which side ('cand' or 'opp') lost that way. 'D-none' is draws plus the "
      "`step_limit` backstop. Runs before E1 (e.g. the drop-only pilot) may show `episode_timeout`, "
      "which had no winner.")
