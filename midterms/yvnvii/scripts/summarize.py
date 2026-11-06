"""Build the comparison table (Markdown) from results/*/summary.json.

Cost is computed from prices.json, which you fill in with the provider's published price on the
day you ran the evaluation (dated cost). Run from midterms/<github-login>/:
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
print("| run | cases | episodes | W / D-none / L | terminal reasons | illegal attempts | fallbacks | "
      "failed calls | calls | mean latency (s) | tokens in / out | est. cost |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|")
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
    tin, tout = sum(x["input_tokens"] for x in c), sum(x["output_tokens"] for x in c)
    cases = sorted({e["case"] + ("*" if e["heldout"] else "") for e in eps})
    print(f"| {m['run']} ({m['candidate']} vs {m['opponent']}, v{m['game_version']}, {m['date'][:10]}) "
          f"| {', '.join(cases)} | {len(eps)} | {res.count('win')} / {res.count('draw/none')} / "
          f"{res.count('loss')} | {', '.join(f'{k}:{v}' for k, v in reasons.items())} | "
          f"{sum(x['illegal_attempts'] for x in c)} | {sum(x['fallback_moves'] for x in c)} | "
          f"{sum(x['failed_calls'] for x in c)} | {sum(x['calls'] for x in c)} | "
          f"{(sum(lat) / len(lat)):.3f} | {tin} / {tout} | "
          f"{cost(m.get('model'), tin, tout) if m['candidate'] == 'model' else '$0'} |"
          if lat else "| ... | | | | | | | | | | | |")
print("\n`*` = held-out case. W/D/L are from the candidate's side; 'D-none' includes draws and "
      "limit endings with no winner.")
