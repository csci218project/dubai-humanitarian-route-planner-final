# Dubai Humanitarian — Humanitarian Route Planner

**CSCI218 Foundations of Artificial Intelligence | Autumn 2026 | University of Wollongong in Dubai**

An educational route-planning prototype for Project B, “Humanitarian Route Planner,” listed in the supplied Dubai Humanitarian project spreadsheet. It compares three AI search approaches over a small multimodal logistics graph and demonstrates how an unavailable airport, port, hub, or corridor changes the route.

> **Important limitation:** All example connections, transport times, costs, capacities, and risk scores are synthetic. They are not verified facts or operational recommendations. This app contains no live access permissions, schedules, security assessments, official Dubai Humanitarian data, or verified routes. Do not use it to plan actual aid movements.

## Features

- Streamlit interface in a Victorian chart-room style that updates instantly as settings change (no run button).
- Scroll-driven 3D opening: a Victorian globe turns as you scroll, from a Gemini-generated video.
- Air, sea, road, and illustrative land-convoy connections.
- Dijkstra, A*, and hierarchical (multi-layered) search.
- Configurable route objective balancing time, cost, and ordinal risk points.
- Preconfigured disruption scenarios and custom unavailable nodes/edges.
- Route details for stops, links, time, cost, risk, score, runtime, and expanded states, plus the cost of the current closures compared with the open network.
- Clickable schematic chart: click a hub or link to inspect it, close or reopen it, or make it the origin or destination.
- Before/after view: closing anything draws the route before the closures, faded, on the chart, and compares both routes in a table (legs, time, cost, risk, nodes explored).
- Two networks: the 10-hub sample and a 40-hub extended network with real airport and port locations (see Data).
- Leg-by-leg journey strip and an account-book ledger comparing all three algorithms.
- Unit tests for correctness, closures, malformed inputs, metrics, and the front end.
- Seeded benchmark script producing trial-level CSV and summary statistics.

## Project structure

```text
dubai-humanitarian-route-planner-final/
├── app.py                             # Streamlit UI (page layout and wiring)
├── ui/                                # Front end: theme, chart, components, session state, opening sequence
├── static/fonts/                      # Bundled fonts (SIL Open Font Licence) so the demo works offline
├── static/sequence/                   # Opening globe frames (WebP) and manifest.json
├── .streamlit/config.toml             # Theme colours and fonts
├── render.yaml                        # Deployment settings for Render
├── requirements.txt                   # Runtime dependencies
├── requirements-dev.txt               # Extra tools (frame extraction)
├── __init__.py                        # Project overview
├── data/sample_network.json           # Synthetic network and data disclaimer
├── data/extended_network.json         # 40-hub network: real locations, illustrative link values
├── humanitarian_route_planner/
│   ├── models.py                      # Domain objects and route result
│   ├── network.py                     # Input validation, graph, distances, metrics
│   ├── algorithms.py                  # Dijkstra, A*, hierarchical search
│   └── scenarios.py                   # Preset disruptions
├── build_network.py                   # CSV-to-JSON network builder (Shahir)
├── hubs_template.csv                  # Network hubs as a spreadsheet (Shahir)
├── links_template.csv                 # Network links as a spreadsheet (Shahir)
├── meeting_log.md                     # Mentor meeting log, Appendix B (Shahir)
├── search.py                          # BFS, Greedy best-first, Weighted A* (Koushik)
├── heuristics.py                      # Heuristic checks and risk model (Mohammed)
├── synthetic.py                       # Seeded random networks (Shreya)
├── experiments.py                     # Scaling and Monte Carlo experiments (Shreya)
├── test_*.py                          # Tests for the four team files above
├── tests/                             # Core and front-end tests
├── scripts/run_benchmarks.py          # Repeatable experiments
├── scripts/make_sequence.py           # Turns a video into the opening's frame sequence
├── scripts/build_extended_network.py  # Rebuilds the extended network from public data
├── results/                           # Example/generated benchmark CSV files
└── docs/                              # Architecture, experiment, rubric, viva and UI notes
```

## Requirements

Python 3.10 or newer (recommended 3.11/3.12) and `pip`. The app does not call external APIs. Internet access is only needed to install Python dependencies.

## Install and run

### Windows PowerShell

```powershell
cd dubai-humanitarian-route-planner-final
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
cd dubai-humanitarian-route-planner-final
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit, usually `http://localhost:8501`.

## Use the prototype

1. Pick the network (sample or extended), the origin and the generic affected-area destination in the sidebar.
2. Choose a priority preset (Fastest, Cheapest, Safest, Balanced) or fine-tune the time, cost and risk sliders.
3. Choose a disruption scenario, or add closed hubs and links.
4. Read the summary: the route found, its totals, and what the closures cost compared with the open network.
5. Click any hub, or the diamond halfway along a link, to inspect it and close or reopen it. The route updates at once, and the route before the closures appears faded on the chart with a before/after table.
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

## Data

The app offers two networks; switch between them in the sidebar.

- **Sample network** (`data/sample_network.json`): the original 10 hubs and 15 links. All values are synthetic.
- **Extended network** (`data/extended_network.json`): the sample plus 30 real airports and ports, 40 hubs and 197 links in total. Locations come from OurAirports and UN/LOCODE, air links follow scheduled-route pairs in OpenFlights data, and sea distances follow shipping lanes (searoute). Every time, cost, risk and capacity value is an illustrative assumption: time and cost are fitted to the sample's own links so new links are on the same scale, and risk follows a fixed rule by mode and distance from the destination. New hubs reach the destination only through the sample's corridor links.

To rebuild the extended network (it downloads the public data first):

```
pip install -r requirements-dev.txt
python scripts/build_extended_network.py
```

Sources and licences: OurAirports (public domain), OpenFlights route data (ODbL 1.0), UN/LOCODE (UNECE) and searoute (Apache 2.0). These give locations, routes and distances, not humanitarian transit times, costs or risk, so those stay documented assumptions; Dubai Humanitarian's anonymised data would replace them if shared.

## Opening sequence

The globe at the top of the page is a 10-second video generated with Gemini, split into 120 WebP frames in `static/sequence/`. Scrolling picks which frame is drawn, so the camera orbits the globe as you scroll; **Skip to the planner** jumps straight to the tool. To use a different video:

```
pip install -r requirements-dev.txt
python scripts/make_sequence.py path\to\video.mp4
```

Then restart Streamlit. If `static/sequence/` is missing, the app shows a plain title instead.

## Run tests

From the repository root:

```
python -m unittest discover
```

This runs the core and front-end tests in `tests/` (graph loading and validation, Dijkstra/A* score agreement, hierarchical path continuity, closures, disconnected routes, unknown IDs, metric aggregation, and the app) and the team tests (`test_*.py` in the root). To run one group only:

```
python -m unittest discover -s tests
python -m unittest test_search test_heuristics test_experiments test_build_network
```

## Deploy

The app runs on Streamlit Community Cloud from this repository (branch main, file app.py, Python 3.12). Pushing to main updates the live app automatically.

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

## Team and responsibilities

| Files | Owner | Work | Report sections |
|---|---|---|---|
| `build_network.py`, `hubs_template.csv`, `links_template.csv`, `meeting_log.md` | Shahir | Bigger documented network, CSV-to-JSON builder, disruption scenarios, mentor log, coordination | Executive summary, motivation, requirements, appendices, final edit |
| `search.py` | Koushik | BFS, Greedy best-first and Weighted A* baselines, with instrumentation | Algorithm design and complexity |
| `heuristics.py` | Mohammed | Heuristic checks, a time-based heuristic, risk as probability, sensitivity | Heuristic justification, trade-offs, limitations |
| `synthetic.py`, `experiments.py` | Shreya | Synthetic networks, scaling and Monte Carlo experiments, plots | Experiments and results |
| `app.py`, `ui/`, `static/` | Arwin | Front end and opening sequence (done) | Implementation, screenshots, demo script |

Each team file starts with empty functions to fill in, and has a matching `test_*.py` file describing what the code must do. Those tests are skipped until you remove the `@unittest.skip` line above each one.

### Shahir: network data and coordination

- [ ] Build a larger network (about 25–40 hubs) in `hubs_template.csv` and `links_template.csv`, with real coordinates from public sources (OurAirports for airports, the World Port Index for ports) and times, costs and risk scores labelled as assumptions.
- [ ] Write an assumptions table: speed and cost per km for each mode, with sources.
- [ ] Finish `build_network.py` so it turns the two CSVs into `data/extended_network.json`, in the same format as the sample.
- [ ] Add 3–5 named disruption scenarios for the new network, each with a one-line reason.
- [ ] Keep `meeting_log.md` current if the team goes for the industry bonus, and raise contribution problems with the lab instructor by Week 6.

### Koushik: search algorithms

- [ ] `breadth_first_search()`: the route with the fewest legs, ignoring time, cost and risk.
- [ ] `greedy_best_first()`: always expand the hub that looks closest to the goal.
- [ ] `weighted_a_star()`: A* with f = g + ε·h; the route cost must stay within ε × the optimal cost.
- [ ] Each takes the same arguments as `dijkstra()` and returns a `RouteResult` with states expanded and runtime, respecting closed hubs and links.
- [ ] Stretch: bidirectional Dijkstra, or Yen's algorithm for the k shortest routes.

### Mohammed: cost model and heuristics

- [ ] `check_admissible()` and `check_consistent()` for any heuristic.
- [ ] `time_lower_bound_heuristic()`, with the argument for why it never overestimates.
- [ ] `survival_weight()`: risk score to disruption probability p, then weight −ln(1 − p), with the mapping stated as an assumption.
- [ ] A sensitivity check of which route wins as the weights change.
- [ ] Agree a `heuristic` argument with Koushik so heuristics can be compared inside A*.

### Shreya: experiments and testing

- [ ] `generate_network()`: seeded, connected random networks with air, sea and road links.
- [ ] `run_scaling()`: states expanded and runtime against network size, over several seeds.
- [ ] `run_monte_carlo()`: random closures from risk scores, comparing how often the fastest and safest routes survive and the delay replanning adds.
- [ ] Plots saved to `results/`, with mean ± standard deviation and the seeds recorded.
- [ ] Later: a Weighted A* ε sweep once Koushik's `weighted_a_star()` is ready.

## Team workflow

One-time setup (you need to be a member of the `csci218project` GitHub organisation):

```
git clone https://github.com/csci218project/dubai-humanitarian-route-planner-final.git
cd dubai-humanitarian-route-planner-final
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

Every work session:

1. Get everyone's latest work: `git checkout main`, then `git pull`.
2. Switch to your own branch: `git checkout -b koushik/search` the first time; afterwards `git checkout koushik/search`, then `git merge main`. Use your own name and topic.
3. Work on your own files and run the tests (see Run tests).
4. Commit small steps and push, for example: `git add search.py test_search.py`, then `git commit -m "Add breadth-first search baseline"`, then `git push -u origin koushik/search`.
5. Open a pull request into `main` on GitHub, ask a teammate to review it, then merge.

Change only your own files, and talk to the owner before editing shared ones: `humanitarian_route_planner/algorithms.py` (Koushik), data and `network.py` (Shahir), `app.py` and `ui/` (Arwin). Commit in your own name, never commit `.venv`, passwords or personal data, and tell Arwin when your part is ready to appear in the app.

## Submission notes

Use a shared Git repository and commit genuine work throughout the project; the supplied rubric treats history as evidence of contribution. All members should understand the entire codebase for the individual viva. The supplied brief also calls for a structured report, screenshots, repeatable experiments, results versus a baseline, limitations, references, and appendices. See `docs/project_alignment.md` and `docs/experiment_plan.md`. Follow the course's AI-tool policy and disclose assistance as required. Do not claim real industry engagement or mentor validation unless it occurred and is documented.
