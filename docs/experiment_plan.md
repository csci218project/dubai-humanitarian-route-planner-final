# Experiment and results plan

Regenerate the results on your own machine and discuss that run; `results/benchmark_interpretation.md` discusses the recorded one.

## Research questions

1. Does A* always find the same minimum score as Dijkstra, transfers included?
2. When does A* expand fewer states than Dijkstra, and does that make it faster?
3. How often does hierarchical search find the optimal route, and why does it miss?
4. How do the data's scenarios change the route, and do the changes match the reroutes the data expects?

## Variables

- **Independent:** algorithm (Dijkstra, A*, hierarchical), scenario (S0–S9 or a seeded random disruption) and weight preset (Fastest, Cheapest, Safest, Balanced).
- **Dependent:** success, route score, time, slow-case time, cost per tonne, risk, reliability, transfers, states expanded, runtime and gap to Dijkstra.
- **Controlled:** the same network file, origin, destination, presets, random seed and number of repeats for every algorithm.

## Procedure

1. Run all tests: `python -m unittest discover`.
2. Run `python scripts/run_benchmarks.py --trials 30 --seed 218 --repeats 5 --output-dir results`.
3. Keep the three CSV files with the submission.
4. Check that A* matches Dijkstra in every run; investigate any mismatch before reporting.
5. Report success rates and mean ± sample standard deviation, with the number of runs behind each figure.
6. Discuss the hierarchical cases that are worse than Dijkstra or fail.
7. Optionally rerun with a second seed as a sensitivity check, without replacing the declared seed.

## Metrics

- **Baseline:** Dijkstra's optimal route under the same network, scenario and weights.
- **Gap:** `(algorithm score − Dijkstra score) / Dijkstra score × 100%`, when both succeed.
- **States expanded:** search states taken off the queue. With transfers, a state is a hub plus the mode the cargo arrived on, so it can exceed the number of hubs; hierarchical counts include both tiers.
- **Runtime:** median of the repeats, measured with `time.perf_counter`; noisy on a network this small.

## Threats to validity

- The network is small; results may not carry over to larger networks.
- The data's values describe one point in time and are planning figures, not measured outcomes.
- Random disruptions are uniform, while real disruptions are often correlated.
- Risk is ordinal and added along the route; reliability assumes independent legs; the slow case adds every leg's p90.
- Runtime depends on the machine and on Python overhead.
