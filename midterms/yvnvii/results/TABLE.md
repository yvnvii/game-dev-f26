Prices from prices.json, dated 2026-11-08.

| run | cases | episodes | W / D-none / L | terminal reasons | limit losses (E1) | illegal attempts | fallbacks | failed calls | calls | mean latency (s) | candidate clock used, max (s) | tokens in / out | est. cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline-vs-greedy (minimax vs greedy, v1959f17, 2026-11-08) | H1-twisted*, T1-empty, T2-centre, T3-twist-win | 8 | 8 / 0 / 0 | connect_four:8 | none | 0 | 0 | 0 | 0 | 0.268 | 1.6 | 0 / 0 | $0 |
| model-history-vs-greedy (model vs greedy, v6cd1cb2, 2026-11-08) | T1-empty, T2-centre, T3-twist-win | 6 | 0 / 0 / 6 | connect_four:6 | none | 2 | 0 | 0 | 34 | 2.228 | 42.4 | 30648 / 17361 | $0.0526 |
| model-v2-vs-greedy (model vs greedy, v1959f17, 2026-11-08) | H1-twisted*, T1-empty, T2-centre, T3-twist-win | 8 | 0 / 0 / 8 | connect_four:8 | none | 0 | 0 | 2 | 62 | 2.804 | 98.6 | 65191 / 37462 | $0.1132 |
| model-vs-greedy (model vs greedy, v6cd1cb2, 2026-11-08) | H1-twisted*, T1-empty, T2-centre, T3-twist-win | 8 | 0 / 0 / 8 | connect_four:8 | none | 1 | 0 | 0 | 64 | 2.234 | 29.2 | 54049 / 29940 | $0.0911 |
| model-vs-minimax (model vs minimax, v6cd1cb2, 2026-11-08) | H1-twisted*, T1-empty, T2-centre, T3-twist-win | 8 | 0 / 0 / 8 | connect_four:8 | none | 0 | 0 | 0 | 28 | 1.718 | 8.3 | 22954 / 5959 | $0.0218 |

`*` = held-out case. W/D/L are from the candidate's side. Under rule E1 (decided 2026-11-08), `timeout` and `call_limit` endings are losses for the player who ran out and are counted in W/L; 'limit losses' says which side ('cand' or 'opp') lost that way. 'D-none' is draws plus the `step_limit` backstop. Runs before E1 (e.g. the drop-only pilot) may show `episode_timeout`, which had no winner.
