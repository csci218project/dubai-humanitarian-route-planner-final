# Experiment and results plan

Use this plan for the CSCI218 report. The repository includes a benchmark runner; regenerate the results on your own machine and discuss the output from that run.

## Research questions

1. Does A* find the same minimum generalized score as Dijkstra?
2. Does A* expand fewer states than Dijkstra for these synthetic scenarios?
3. How often does hierarchical search find a feasible route under closures?
4. When hierarchical search succeeds, how does its score compare with Dijkstra?
5. How do closures affect success rate, runtime, route score, and the number of expanded states?

## Variables

- **Independent:** algorithm (Dijkstra, A*, hierarchical), generated closure scenario, and objective weights.
- **Dependent:** route success, objective score, total time, illustrative cost, accumulated risk points, expanded states, runtime (ms), and optimality gap vs Dijkstra.
- **Controlled:** same JSON graph, origin, destination, weights, number of trials, and random seed for each algorithm comparison.

## Procedure

1. Install the listed dependencies.
2. Run all unit tests and record the result.
3. Run `python scripts/run_benchmarks.py --trials 30 --seed 218 --output-dir results`.
4. Preserve `benchmark_trials.csv` and `benchmark_summary.csv` with the submission.
5. Check Dijkstra/A* objective-score agreement for every scenario where both succeed; investigate any mismatch before reporting results.
6. Report success rates and mean ± sample standard deviation for runtime, expanded states, score, and score gap. Include the number of successful trials with each statistic.
7. Discuss hierarchical cases with higher cost or failures to realize an abstract region sequence.
8. Optionally rerun with a second seed as a sensitivity check. Do not replace the declared primary seed with the most favourable result.

## Baseline and metrics

- **Baseline:** Dijkstra's optimal generalized-score path under the same graph, weights, and closures.
- **A* optimality gap:** should be 0% within numerical tolerance when both methods succeed.
- **Hierarchical gap:** `(hierarchical score - Dijkstra score) / Dijkstra score × 100%`, only if both succeed and Dijkstra score is positive.
- **Success rate:** successful route count / number of trials × 100%.
- **Runtime:** `time.perf_counter` measurement; small-graph results are noisy.
- **Expanded states:** search states popped for expansion, including abstract states for hierarchical search. This is not exactly a count of unique physical nodes.

## Report table template

| Algorithm | Success rate | Mean runtime (ms) ± SD | Mean states expanded ± SD | Mean score ± SD | Mean gap vs Dijkstra |
|---|---:|---:|---:|---:|---:|
| Dijkstra | Copy from CSV | Copy from CSV | Copy from CSV | Copy from CSV | 0% baseline |
| A* | Copy from CSV | Copy from CSV | Copy from CSV | Copy from CSV | Expected 0% when both solve |
| Hierarchical | Copy from CSV | Copy from CSV | Copy from CSV | Copy from CSV | May be positive or unavailable |

Do not use predicted figures to complete this table. Add data from the generated CSV and label it as synthetic simulation results.

## Threats to validity

- The graph is small and manually authored; results may not generalize to larger operational networks.
- Edge values and disruptions are synthetic, not learned from real operations.
- Random closures are uniform in a bounded range, while real disruptions may be correlated.
- The risk score and weighted-sum objective simplify complex humanitarian decisions.
- Runtime is affected by machine load and Python overhead.
- Hierarchical expansion counts include both tiers and must be labelled clearly.
