# System architecture

## Data flow

```text
sample_network.json
       │
       ▼
RouteNetwork ──────► Streamlit interface (app.py)
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

run_benchmarks.py ──► seeded scenarios ──► trial CSV + summary CSV
```

## Main constructs

- **Node**: hub, transfer point, staging node, or generic destination with coordinates, region, type, and description.
- **Edge**: undirected illustrative transport connection with mode, time, cost, ordinal risk score, capacity, and notes.
- **RouteNetwork**: validates endpoints and metric ranges, indexes adjacent edges, filters closures, estimates schematic edge distance, and totals route metrics.
- **CostWeights**: applies the weighted-sum objective consistently to all search algorithms.
- **RouteResult**: carries success/failure, path node IDs, edge IDs, component metrics, objective score, runtime, expanded states, abstract regions, and explanation.
- **Disruption model**: unavailable nodes and edges are excluded during neighbor expansion. The base network is not mutated, so runs can be compared against the same graph.

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
4. Search the detailed graph using state `(node_id, region_index)`, remaining within the current region or advancing to the next region in that sequence.
5. Return both the route and abstract sequence.

The abstraction omits some details, including the cost of reaching a particular boundary within a region. It can therefore select a suboptimal region sequence or fail to realize a sequence. This is an intended trade-off to analyse, not a claim that hierarchical search is always better.

## Validation and error handling

The loader rejects invalid coordinates, unknown edge endpoints, self-loops, negative time/cost, non-positive capacity, and risk scores outside 0–10. Search reports errors for unknown blocked IDs and unavailable origins/destinations. Disconnected scenarios return failure instead of fabricating a route.

## Future extension constraints

A domain-reviewed real-world design would need timestamped data provenance, explicit direction/time-dependent links, real carrier schedules/capacities, permits and border/customs constraints, cargo handling rules, uncertainty ranges, source reliability, access controls, security review, monitoring, and an authorized human approval step. This student prototype intentionally has none of those capabilities.
