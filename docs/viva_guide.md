# Viva preparation guide

Use these prompts to confirm every member can explain the complete system, not just their own code. Prepare answers in your own words and practise using the actual implementation.

## Core questions and answer points

### Why Dijkstra?
Dijkstra finds an optimal path when all edge weights are non-negative. The generalized costs in this project are non-negative because weights and edge attributes are validated. Dijkstra is the baseline for checking A* and analysing alternatives.

### How does A* differ?
A* orders states by `g(n) + h(n)`: cost already incurred plus a lower-bound estimate of remaining cost. This implementation derives an admissible heuristic from straight-line distance and the smallest active edge-score-per-kilometre ratio. It should match Dijkstra's minimum score and may expand fewer states, although a speedup is not guaranteed on this small graph.

### What if an airport or corridor closes?
A disabled node or edge is excluded from graph expansion. The algorithms rerun on the remaining graph. If no path remains, the program reports failure instead of returning a route through a closed connection.

### Why use a weighted objective?
Time, cost and risk can produce competing route choices. Exposed weights let the group demonstrate the trade-offs. This is only a modelling device: USD is scaled by 1,000, risk is ordinal, and the values are not validated operational policy.

### Is the risk score a probability?
No. It is the data's ordinal score from 1 to 5 per leg, added along the route. Reliability (the share of trips that run as planned) is the closer thing to a probability, and the app multiplies it along the route as if legs were independent.

### How are transfers between modes handled?
Transfer legs in the data (for example truck shuttles to an airport) already include the handling. Where cargo switches between air, sea and road at a hub without such a leg, the route pays a transfer: 3.5 h, $18/t and risk 1, the median of the data's transfer legs. The search state is the hub plus the mode the cargo arrived on, so the algorithm knows when a transfer is needed.

### How do the scenarios work?
Each scenario closes legs, makes some slower (TIME_MULT) or dearer (COST_MULT), or combines other scenarios. The app solves the request under normal conditions and under the scenario with the same algorithm, and compares the two routes.

### Why can hierarchical search differ?
It selects a region sequence first, then searches detailed links restricted to that sequence. The abstraction omits some within-region travel costs and boundaries. It may therefore find a costlier route or fail to realize its abstract sequence even when another flat route exists.

### What is the role of the tests?
Tests check route continuity, Dijkstra/A* score agreement, metric sums, graph validation and closure behaviour. Further tests check one-way legs, transfers, scenarios, A*/Dijkstra agreement in every scenario, a brute-force optimality check and the heuristic never overestimating. They catch software errors but cannot prove the data's times and costs hold in real operations.

### Why run many benchmark trials?
One scenario may favour an algorithm by chance. A fixed-seed set of trials makes results reproducible; means and standard deviations show variation over scenarios. Runtime on a small graph is noisy, so expanded states and score gaps are also important. Here A* expands fewer states than Dijkstra under the Fastest preset but is slower in wall-clock time, because computing the heuristic costs more than it saves on 23 hubs.

### What would be required for operational use?
Verified, time-stamped route/access data; directed and time-dependent links; carrier schedules and capacities; permits, border and customs rules; cargo handling constraints; uncertainty and source provenance; partner validation; security review; monitoring; and authorized human decision-making. This project deliberately does not provide those.

## Individual contribution statement

The supplied course brief asks each student to evidence their own work, explain a technical decision and why it was made, describe a problem and its solution, reflect on what they would change, and discuss teamwork. Keep Git commits and notes that accurately show your personal contribution. Do not claim work performed by someone else or invent mentor feedback.
