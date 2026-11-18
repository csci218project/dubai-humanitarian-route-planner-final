# System architecture

## Data flow

```text
hrp_network_data.xlsx ──► import_hrp_data.py ──► hrp_network.json
                                                        │
                                                        ▼
RouteNetwork (+ with_adjustments for a scenario) ──► Streamlit interface (app.py)
       │                       │
       │ graph access           │ origin, destination, weights,
       │ + validation           │ unavailable nodes and links
       ▼                       ▼
Network metric helpers ◄─ Dijkstra / A* / hierarchical search
       │                       │
       └───────────┬───────────┘
                   ▼
         RouteResult + comparison table
                   │
                   ▼
      Route-leg details + schematic graph

run_benchmarks.py ──► data scenarios + seeded random disruptions ──► three CSVs
```

## Main constructs

- **Node**: hub, transfer point, staging node, or generic destination with coordinates, region, type, and description.
- **Edge**: a transport leg with mode, time, cost, ordinal risk score, capacity and notes, plus slow-case (p90) time, reliability, distance and corridor when the data has them. Legs are one-way when the network is directed.
- **TransferRule**: the time, cost and risk added when cargo switches between air, sea and road at a hub that has no transfer leg of its own (from the data's median transfer leg).
- **RouteNetwork**: validates endpoints and metric ranges, indexes outgoing legs (both directions for undirected networks), filters closures, applies a scenario's slower or dearer legs (`with_adjustments`), estimates schematic edge distance, and totals route metrics including transfers, slow-case time and reliability.
- **CostWeights**: applies the weighted-sum objective consistently to all search algorithms.
- **RouteResult**: carries success/failure, path node IDs, edge IDs, component metrics, objective score, runtime, expanded states, abstract regions, and explanation.
- **Disruption model**: closed hubs and legs are excluded during neighbour expansion; slower or dearer legs come from a scenario copy of the network. The base network is never changed, so every run can be compared with normal conditions.

## Algorithms

### Dijkstra

1. Set the origin distance to zero and other states to infinity.
2. Pop the minimum-distance state from a min-priority queue.
3. Ignore stale queue entries and already-expanded states.
4. Relax every available edge using its generalized score.
5. Reconstruct the route using parent pointers when the goal is popped.

### A*

A* prioritizes `g(n) + h(n)`, where `g(n)` is the accumulated score and `h(n)` lower-bounds the remaining score. The heuristic uses Haversine straight-line distance multiplied by the minimum active edge-score-per-kilometre ratio. In the provided teaching model, each estimated edge distance is no shorter than the direct separation of its endpoints, so the heuristic is admissible. Dijkstra and A* should return the same minimum objective score, modulo floating-point tolerance.

### Hierarchical / multi-layered search

1. Map each node to its configured region.
2. Build an abstract graph of available inter-region connections; for each region pair, keep the minimum crossing-edge score.
3. Search the abstract graph for a region sequence.
4. Search the detailed graph using state `(node_id, region_index)`, plus the arrival mode when transfers apply, remaining within the current region or advancing to the next region in that sequence.
5. Return both the route and abstract sequence.

The abstraction omits some details, including the cost of reaching a particular boundary within a region. It can therefore select a suboptimal region sequence or fail to realize a sequence. This is an intended trade-off to analyse, not a claim that hierarchical search is always better.

### States and transfers

On a network with a transfer rule, Dijkstra and A* use the state `(node_id, arrival_mode)`, so they know whether the next leg needs a transfer; its cost is added to that step. Transfers never reduce cost, so the A* heuristic stays admissible.

## Validation and error handling

The loader rejects invalid coordinates, unknown edge endpoints, self-loops, negative time/cost, non-positive capacity, risk scores outside 0–10, slow-case times below the typical time, and reliability outside 0–100%. Scenarios naming unknown legs are rejected. Search reports errors for unknown blocked IDs and unavailable origins/destinations. Disconnected scenarios return failure instead of fabricating a route.

## Future extension constraints

A domain-reviewed real-world design would need timestamped data provenance, time-dependent links, real carrier schedules/capacities, permits and border/customs constraints, cargo handling rules, uncertainty ranges, source reliability, access controls, security review, monitoring, and an authorized human approval step. This student prototype intentionally has none of those capabilities.
