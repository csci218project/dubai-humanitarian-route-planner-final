# Data summary (for the report)

## Source

Dubai Humanitarian provided the network as a spreadsheet (`data/hrp_network_data.xlsx`) after giving feedback on the project proposal. It describes relief cargo from the Dubai humanitarian logistics hub (IHC) to the El Obeid distribution hub in Sudan (ELO), with Port Sudan, Gedaref and Kosti as alternative destinations.

## Contents

| Sheet | Rows | Main fields |
|---|---:|---|
| locations | 23 | ID, name, type (airport, sea port, hub, border crossing, warehouse, destination), country, coordinates, role |
| network_legs | 36 | one-way legs: mode (air, sea, road, transfer), distance, typical and p90 transit time, cost per tonne, weekly capacity, risk 1–5, reliability %, corridor |
| disruption_scenarios | 10 | S0–S9: CLOSE legs, TIME_MULT (slower), COST_MULT (dearer), COMBINE (other scenarios), with trigger, expected duration and expected reroute |

The data passed every check: no missing values or duplicate IDs, every leg references a real location, p90 times are never below typical times, and every location is reachable from the origin.

## How the planner uses it

- `scripts/import_hrp_data.py` converts the spreadsheet into `data/hrp_network.json`, the file the app reads; locations become hubs, legs become one-way edges, and countries become the regions for hierarchical search.
- **Weighted cost** of a step: time weight × hours + cost weight × (USD per tonne ÷ 1,000) + risk weight × risk score.
- **Transfers:** seven legs in the data are explicit transfers. At four hubs (Addis Ababa, Cairo, Djibouti port, Port Sudan port) cargo can switch mode without one, so the planner adds a transfer of 3.5 h, $18/t and risk 1, the median of the seven transfer legs. The search state is the hub plus the mode the cargo arrived on.
- **Scenarios:** closures remove legs; TIME_MULT and COST_MULT scale the affected legs' time and cost; COMBINE merges other scenarios. The app compares each disrupted route with the route under normal conditions, next to the data's expected reroute.

## Checks on the method

- A* returned Dijkstra's optimal score in all 10 scenarios under all four presets.
- The A* heuristic never overestimated the true remaining cost at any hub.
- Dijkstra's answer equals a brute-force check of every route in the network.

See `results/benchmark_interpretation.md` for the benchmark results and how the routes compare with the expected reroutes.
