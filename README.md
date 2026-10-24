# Cost model and heuristics (Mohammed)

Your part: prove the A* heuristic is safe to use, compare other heuristics, and
model risk in a way you can defend.

## Already in the repo

- `CostWeights.edge_cost()` in `models.py`: each link costs
  time weight × hours + cost weight × (USD ÷ 1,000) + risk weight × risk points.
- `a_star()` in `algorithms.py`: its heuristic is straight-line distance × the
  cheapest score per km of any open link (see `_heuristic_scale()`).

## Your tasks

Must do:
- [ ] `check_admissible()`: for every hub, confirm h(n) ≤ the true cheapest cost to the goal. Get the true costs by running Dijkstra once from the goal (links are two-way here).
- [ ] `check_consistent()`: for every link, confirm h(a) ≤ cost(a, b) + h(b), in both directions.
- [ ] `time_lower_bound_heuristic()`: time weight × straight-line distance to the goal ÷ the fastest straight-line speed of any link. Explain why it can never overestimate.
- [ ] `survival_weight()`: turn a link's 0–10 risk score into a disruption probability p and use −ln(1 − p) as its weight, so adding weights along a route maximises the chance that the whole route stays open. State the score-to-probability mapping as an assumption.
- [ ] Sensitivity check: for a range of time, cost and risk weights, record which route wins, to show where the choice flips.

Stretch:
- [ ] A landmark (ALT) heuristic, compared with the distance heuristic by states expanded.

## Files

- `heuristics.py`: your functions (empty for now, except the zero heuristic).
- `test_heuristics.py`: tests describing what each function must do.

## How it plugs in

To compare heuristics inside A*, the search needs a `heuristic` argument; agree
on it with Koushik (it fits naturally in his `weighted_a_star()`). Shreya can
then add your heuristics to her experiments.

## Report sections you own

Heuristic justification (with the admissibility argument), the cost-model
trade-offs (why dollars are divided by 1,000, why ordinal risk isn't a
probability) and limitations.

## Viva questions to prepare

- Prove your heuristic never overestimates.
- When does a heuristic give A* no advantage over Dijkstra?
- What goes wrong if you add disruption probabilities directly instead of −ln(1 − p)?
