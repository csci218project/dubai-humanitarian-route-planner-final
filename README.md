# Dubai Humanitarian — Humanitarian Route Planner

**CSCI218 Foundations of Artificial Intelligence | Autumn 2026 | University of Wollongong in Dubai**

An educational route-planning prototype for Project B, “Humanitarian Route Planner,” listed in the supplied Dubai Humanitarian project spreadsheet. It compares three AI search approaches over a small multimodal logistics graph and demonstrates how an unavailable airport, port, hub, or corridor changes the route.

> **Important limitation:** All example connections, transport times, costs, capacities, and risk scores are synthetic. They are not verified facts or operational recommendations. This app contains no live access permissions, schedules, security assessments, official Dubai Humanitarian data, or verified routes. Do not use it to plan actual aid movements.

## Features

- Streamlit interface in a Victorian chart-room style that updates instantly as settings change (no run button).
- Scroll-driven 3D opening: a Victorian globe turns as you scroll, from a Gemini-generated video (see below).
- Air, sea, road, and illustrative land-convoy connections.
- Dijkstra, A*, and hierarchical (multi-layered) search.
- Configurable route objective balancing time, cost, and ordinal risk points.
- Preconfigured disruption scenarios and custom unavailable nodes/edges.
- Route details for stops, links, time, cost, risk, score, runtime, and expanded states, plus the cost of the current closures compared with the open network.
- Clickable schematic chart: click a hub or link to inspect it, close or reopen it, or make it the origin or destination.
- Leg-by-leg journey strip and an account-book ledger comparing all three algorithms.
- Unit tests for correctness, closures, malformed inputs, metrics, and the front end.
- Seeded benchmark script producing trial-level CSV and summary statistics.

## Project structure

```text
dubai_humanitarian_route_planner/
├── app.py                          # Streamlit UI (page layout and wiring)
├── ui/                             # Front end: theme, chart, components, session state
├── static/fonts/                   # Bundled fonts (SIL Open Font Licence) so the demo works offline
├── static/sequence/                # Opening globe frames (WebP) and manifest.json
├── .streamlit/config.toml          # Theme colours and fonts
├── requirements.txt                # Runtime dependencies
├── data/sample_network.json        # Synthetic network and data disclaimer
├── humanitarian_route_planner/
│   ├── models.py                   # Domain objects and route result
│   ├── network.py                  # Input validation, graph, distances, metrics
│   ├── algorithms.py               # Dijkstra, A*, hierarchical search
│   ├── scenarios.py                # Preset disruptions
│   └── visualization.py            # Static matplotlib drawing (not used by the app)
├── tests/                          # Functional and edge-case tests
├── scripts/run_benchmarks.py       # Repeatable experiments
├── scripts/make_sequence.py        # Turns a video into the opening's frame sequence
├── results/                        # Example/generated benchmark CSV files
└── docs/                           # Architecture, experiment, rubric, viva notes
```

## Requirements

Python 3.10 or newer (recommended 3.11/3.12) and `pip`. The app does not call external APIs. Internet access is only needed to install Python dependencies.

## Install and run

### Windows PowerShell

```powershell
cd dubai_humanitarian_route_planner
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

If script activation is restricted by your machine's policy, call the environment's interpreter directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

### macOS / Linux

```bash
cd dubai_humanitarian_route_planner
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit, usually `http://localhost:8501`.

## Use the prototype

1. Pick the origin and the generic affected-area destination in the sidebar.
2. Choose a priority preset (Fastest, Cheapest, Safest, Balanced) or fine-tune the time, cost and risk sliders.
3. Choose a disruption scenario, or add closed hubs and links.
4. Read the summary: the route found, its totals, and what the closures cost compared with the open network.
5. Click any hub, or the diamond halfway along a link, to inspect it and close or reopen it. The route updates at once.
6. Switch the chart between the A*, Dijkstra and hierarchical routes, and open the tabs to compare algorithms, read the leg-by-leg plan, or browse the network data.

See docs/ui_guide.md for how the front end works.

## Cost model

For each edge:

```text
edge_score = time_weight * time_hours
           + cost_weight * (cost_usd / 1000)
           + risk_weight * risk_points
```

The route score is the sum of edge scores. The USD scaling stops large numeric units from automatically dominating, but it does not make dollars, hours, and risk equivalent in real life. Risk is an ordinal 0–10 teaching score, not a probability or a security assessment. All weights must be non-negative and at least one must be positive. Raw time/cost/risk totals are shown separately to expose trade-offs.

## Algorithms

- **Dijkstra:** uses non-negative generalized edge costs and a priority queue; optimal for the configured graph. Standard adjacency-list/binary-heap complexity is `O((V + E) log V)`.
- **A\*:** prioritizes `g(n) + h(n)`. Its heuristic uses straight-line distance times the minimum active edge-score-per-kilometre ratio. Under the provided distance assumptions this is an admissible lower bound. It should match Dijkstra's optimal score, although runtime savings are not guaranteed on a tiny graph.
- **Hierarchical search:** first chooses a sequence of regions in an abstract graph, then searches the detailed network constrained to that region sequence. This can limit search but may exclude a globally better route or fail to realize an abstract path; this trade-off is part of the analysis.

## Opening sequence

The globe at the top of the page is a 10-second video generated with Gemini, split into 120 WebP frames in `static/sequence/`. Scrolling picks which frame is drawn, so the camera orbits the globe as you scroll; **Skip to the planner** jumps straight to the tool. To use a different video:

```
pip install -r requirements-dev.txt
python scripts/make_sequence.py path\to\video.mp4
```

Then restart Streamlit. If `static/sequence/` is missing, the app shows a plain title instead.

## Run tests

From the repository root:

```bash
python -m unittest discover -s tests -v
```

The tests cover graph loading and validation, Dijkstra/A* score agreement, hierarchical path continuity, closures, disconnected routes, unknown IDs, and metric aggregation.

## Reproducible experiments

```bash
python scripts/run_benchmarks.py --trials 30 --seed 218 --output-dir results
```

- `results/benchmark_trials.csv`: each algorithm result in each seeded scenario.
- `results/benchmark_summary.csv`: success rate, means and sample standard deviations for runtime, expanded states, score, and gap versus Dijkstra.

Use at least 30 scenarios for the report, record the seed, and do not cherry-pick results. Small-graph runtime is noisy, so show nodes expanded and optimality gap as well. A fixed seed enables reproduction; a second seed can be a sensitivity check.

## Programmatic example

```python
from pathlib import Path
from humanitarian_route_planner.network import RouteNetwork
from humanitarian_route_planner.models import CostWeights
from humanitarian_route_planner.algorithms import compare_algorithms

network = RouteNetwork.from_json(Path("data/sample_network.json"))
weights = CostWeights(time=1.0, cost=0.75, risk=2.0)
results = compare_algorithms(
    network,
    start="DUBAI_HUB",
    goal="RELIEF_DESTINATION",
    weights=weights,
    blocked_nodes={"DWC_AIRPORT"},
    blocked_edges=set(),
)
for result in results:
    print(result.algorithm, result.success, result.objective_score, result.node_path)
```

## Limitations

- No live route data, schedules, geocoding, map tiles, customs/permit rules, road traffic, loading/handling, inventory, fleet availability, or shipment-specific capacity checks.
- The graph is small and undirected. Some cross-region connections are invented to demonstrate alternative paths; this does not establish that a corridor exists, is open, or is permitted.
- Capacity is only displayed as an edge property. The system does not allocate cargo or check packing and handling constraints.
- Risk is an ordinal teaching score added over links. It is not a calibrated probability or current security assessment.
- Real operational use would require authoritative timestamped data, domain validation, uncertainty handling, security review, and an authorized human decision-maker.

## Team workflow and submission notes

Use a shared Git repository and commit genuine work throughout the project; the supplied rubric treats history as evidence of contribution. All members should understand the entire codebase for the individual viva. The supplied brief also calls for a structured report, screenshots, repeatable experiments, results versus a baseline, limitations, references, and appendices. See `docs/project_alignment.md` and `docs/experiment_plan.md`. Follow the course's AI-tool policy and disclose assistance as required. Do not claim real industry engagement or mentor validation unless it occurred and is documented.
