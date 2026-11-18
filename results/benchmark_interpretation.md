# Benchmark interpretation (Dubai Humanitarian network)

**Configuration:** `python scripts/run_benchmarks.py --trials 30 --seed 218 --repeats 5 --output-dir results`, on `data/hrp_network.json` (23 hubs, 36 one-way legs) from IHC (Dubai) to ELO (El Obeid). Runtimes are the median of 5 runs on the machine that produced these files; rerun the command to reproduce them on yours.

## Scenario set: 10 data scenarios × 4 weight presets (40 runs per algorithm)

| Algorithm | Success | States expanded (mean ± SD) | Runtime, ms (mean ± SD) | Gap to Dijkstra |
|---|---:|---:|---:|---|
| Dijkstra | 40/40 | 15.3 ± 4.5 | 0.072 ± 0.019 | baseline |
| A* | 40/40 | 14.1 ± 5.9 | 0.142 ± 0.030 | 0% in all 40 runs |
| Hierarchical | 40/40 | 13.7 ± 3.0 | 0.142 ± 0.023 | optimal in 37 of 40; mean 3.9%, worst 77.8% |

## Random set: 30 seeded disruptions, Balanced weights

| Algorithm | Success | States expanded (mean ± SD) | Runtime, ms (mean ± SD) | Gap to Dijkstra |
|---|---:|---:|---:|---|
| Dijkstra | 30/30 | 10.3 ± 1.8 | 0.050 ± 0.010 | baseline |
| A* | 30/30 | 10.2 ± 1.9 | 0.113 ± 0.019 | 0% in all 30 runs |
| Hierarchical | 29/30 | 11.7 ± 1.6 | 0.123 ± 0.017 | 0% in all 29 successful runs |

## What the results show

1. **A* is always optimal here.** It returned Dijkstra's score in all 70 runs, as an admissible heuristic should; the tests also check that the heuristic never overestimates at any hub.
2. **A* saves work only when time dominates.** Under Fastest it expanded 6 states against Dijkstra's 10–12 in nine of the ten scenarios (in S5 both expanded 19). Under Cheapest, Safest and Balanced the lowest score per kilometre on any leg is so small that the heuristic is close to zero, so A* behaves like Dijkstra.
3. **A* is slower in wall-clock time** (about 0.14 ms against 0.07 ms) even when it expands fewer states: computing the heuristic (a pass over every leg, then a distance per state) costs more than it saves on 23 hubs. This network is too small to show whether that reverses at scale.
4. **Hierarchical search trades optimality for structure.** It matched Dijkstra in 37 of 40 scenario runs. Under Safest in S1 and S9 it was 77.8% worse: its country-level graph scores each crossing by its cheapest single leg, so UAE → Saudi Arabia → Sudan looked safer than the direct UAE → Sudan flight once Port Sudan's airport closed, and the detailed route through Jeddah then had to use riskier roads inside Sudan that the abstraction ignores. In the random set it failed once to realise its region plan.
5. **The routes.** With Fastest, Safest and Balanced, the best route is the direct airbridge from Al Maktoum to El Obeid (20.8 h, $3,900/t, risk 9, 46% reliability) in every scenario except S5, where closing El Obeid airport moves it through Port Sudan and Omdurman (67.8 h, $2,574/t, 26%). Cheapest takes the sea route to Port Sudan (281.3 h, $744/t, one sea-to-road transfer); when the Red Sea legs close or get dearer (S2, S8, S9) it moves to the Djibouti–Ethiopia corridor (301.5 h, $892/t).
6. **Against the data's expected reroutes.** For S2 the planner's cheapest route matches the expected one (sea to Djibouti, then road through Ethiopia). For S8 the data expects the cheapest route to shift to air or land; the planner shifts to the Ethiopian land corridor but keeps the sea leg to Djibouti, which the cost shock doesn't touch. For S5 the data expects the last mile via Kosti; with Balanced weights the planner prefers the faster but riskier Omdurman road.

## Limits of these results

The network is small, so runtimes are tiny and machine-dependent; states expanded and gaps are more meaningful. Risk is an ordinal score added along the route, reliability treats legs as independent, and the data's values describe one point in time. The random disruptions are uniform, while real disruptions are often correlated.
