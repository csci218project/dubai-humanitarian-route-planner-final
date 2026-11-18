# Dubai Humanitarian — Humanitarian Route Planner

**CSCI218 Foundations of Artificial Intelligence | Autumn 2026 | University of Wollongong in Dubai**

An educational route-planning prototype for Project B, “Humanitarian Route Planner,” listed in the supplied Dubai Humanitarian project spreadsheet. It compares three AI search approaches on a relief network from Dubai to El Obeid in Sudan (23 hubs, 36 one-way legs) and shows how closures, slow-downs and cost shocks change the route.

> **Important limitation:** The network data was provided by Dubai Humanitarian for this student project. The app is a teaching prototype for comparing search algorithms, not an operational planning tool: it has no live schedules, permissions or security assessments, and its routes are not recommendations. Do not use it to plan actual aid movements.

## Features

- Streamlit interface in a Victorian chart-room style that updates instantly as settings change (no run button).
- Scroll-driven 3D opening: a Victorian globe turns as you scroll, from a Gemini-generated video.
- One-way air, sea, road and transfer legs. When cargo changes mode at a hub without its own transfer leg, the route pays a transfer in time and cost.
- Dijkstra, A*, and hierarchical (multi-layered) search.
- Configurable route objective balancing time, cost, and ordinal risk points.
- Ten disruption scenarios from the data (closures, slow-downs, cost shocks and a combined case), plus your own closures.
- Route details: stops, legs, typical and slow-case (p90) time, cost per tonne, risk, reliability, transfers, score, runtime and expanded states, plus what the disruption costs compared with normal conditions.
- Clickable schematic chart: click a hub or link to inspect it, close or reopen it, or make it the origin or destination.
- Before/after view: under any disruption, the normal-conditions route is drawn faded on the chart and both routes are compared in a table (legs, transfers, time, cost, risk, nodes explored), next to the reroute the data expects.
- Network data from Dubai Humanitarian, kept as the original spreadsheet and converted to the app's format by a script (see Data).
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
├── requirements.txt                   # Runtime dependencies
├── requirements-dev.txt               # Extra tools (data import, frame extraction, plots)
├── __init__.py                        # Project overview
├── data/hrp_network_data.xlsx         # The network data: locations, legs, scenarios
├── data/hrp_network.json              # The same data in the app's format (generated)
├── data/sample_network.json           # Small synthetic network used by the tests
├── humanitarian_route_planner/
│   ├── models.py                      # Domain objects and route result
│   ├── network.py                     # Input validation, graph, distances, metrics
│   └── algorithms.py                  # Dijkstra, A*, hierarchical search
├── meeting_log.md                     # Dubai Humanitarian meeting log (report Appendix B)
├── tests/                             # Core and front-end tests
├── scripts/run_benchmarks.py          # Benchmarks: every scenario and seeded random closures
├── scripts/make_sequence.py           # Turns a video into the opening's frame sequence
├── scripts/import_hrp_data.py         # Converts the spreadsheet into data/hrp_network.json
├── results/                           # Benchmark results on the Dubai Humanitarian network
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

1. Pick the origin and destination in the sidebar (by default, the Dubai hub to El Obeid).
2. Choose a priority preset (Fastest, Cheapest, Safest, Balanced) or fine-tune the time, cost and risk sliders.
3. Choose one of the ten scenarios from the data, or close hubs and legs yourself.
4. Read the summary: the route found, its totals (time, slow case, cost per tonne, risk, reliability, transfers) and what the disruption costs compared with normal conditions.
5. Click any hub, or the diamond halfway along a link, to inspect it and close or reopen it. The route updates at once, and the normal-conditions route appears faded on the chart with a before/after table.
6. Switch the chart between the A*, Dijkstra and hierarchical routes, and open the tabs to compare algorithms, read the leg-by-leg plan, or browse the network data.

See docs/ui_guide.md for how the front end works.

## Cost model

For each edge:

```text
edge_score = time_weight * time_hours
           + cost_weight * (cost_usd / 1000)
           + risk_weight * risk_points
```

The route score is the sum of edge scores, plus any transfers. Cost is in US dollars per tonne; dividing by 1,000 stops large numbers from automatically dominating, but it does not make dollars, hours and risk equivalent in real life. Risk is the data's ordinal 1–5 score per leg, not a probability or a security assessment.

**Transfers.** When cargo arrives at a hub by one of air, sea or road and leaves by another, and the hub has no transfer leg for that change, the route adds a transfer step scored the same way: 3.5 h, $18/t and risk 1, the median of the data's seven transfer legs. Legs whose mode is "transfer" already include that work, so they never add another. All weights must be non-negative and at least one must be positive. Raw time/cost/risk totals are shown separately to expose trade-offs.

## Algorithms

- **Dijkstra:** uses non-negative generalized edge costs and a priority queue; optimal for the configured graph. Standard adjacency-list/binary-heap complexity is `O((V + E) log V)`.
- **A\*:** prioritizes `g(n) + h(n)`. Its heuristic uses straight-line distance times the minimum active edge-score-per-kilometre ratio. Under the provided distance assumptions this is an admissible lower bound. It should match Dijkstra's optimal score, although runtime savings are not guaranteed on a tiny graph.
- **States with transfers:** on a network with a transfer rule, all three searches use the state (hub, mode the cargo arrived on), so they know when the next leg needs a transfer. Transfers only add cost, so the A* heuristic stays admissible. Legs are one-way when the data says so.
- **Hierarchical search:** first chooses a sequence of regions in an abstract graph, then searches the detailed network constrained to that region sequence. This can limit search but may exclude a globally better route or fail to realize an abstract path; this trade-off is part of the analysis.

## Data

The app uses one network: relief cargo from the Dubai humanitarian logistics hub (IHC) to the El Obeid distribution hub in Sudan (ELO), with Port Sudan, Gedaref and Kosti as alternative destinations. Dubai Humanitarian provided it as `data/hrp_network_data.xlsx`:

- **locations** (23): airports, sea ports, hubs, border crossings, the origin and the destination, with coordinates.
- **network_legs** (36): one-way legs with distance, typical and slow-case (p90) transit time, cost per tonne, weekly capacity, a 1–5 risk score, reliability % and corridor.
- **disruption_scenarios** (10): S0 (baseline) to S9, built from four actions: CLOSE a leg, TIME_MULT (slower), COST_MULT (dearer) and COMBINE (other scenarios together). Each scenario also gives the reroute planners would expect.

The app reads `data/hrp_network.json`. After editing the spreadsheet, regenerate it:

```
pip install -r requirements-dev.txt
python scripts/import_hrp_data.py
```

`data/sample_network.json` is a small synthetic network kept for the unit tests.

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

This runs every test in `tests/`: graph loading and validation, one-way legs, the transfer rule, scenario adjustments, Dijkstra/A* agreement in every scenario, a brute-force check of Dijkstra, the A* heuristic never overestimating, closures, unknown IDs, metric totals, and the app itself. The spreadsheet check is skipped unless `openpyxl` is installed (`pip install -r requirements-dev.txt`).

## Deploy

The app runs on Streamlit Community Cloud from this repository (branch main, file app.py, Python 3.12). Pushing to main updates the live app automatically.

## Reproducible experiments

```bash
python scripts/run_benchmarks.py --trials 30 --seed 218 --repeats 5 --output-dir results
```

Two experiment sets, each solved by Dijkstra, A* and hierarchical search:

- `results/benchmark_scenarios.csv`: every scenario in the data (S0–S9) under the four weight presets.
- `results/benchmark_trials.csv`: 30 seeded random disruptions (closed legs and hubs) under the Balanced weights.
- `results/benchmark_summary.csv`: success rate, means and sample standard deviations for states expanded, runtime, score and gap versus Dijkstra, per set and algorithm.

Runtimes are the median of `--repeats` runs and are still noisy on a network this small, so report states expanded and the gap to Dijkstra as well. `results/benchmark_interpretation.md` discusses the recorded run.

## Programmatic example

```python
from pathlib import Path
from humanitarian_route_planner.network import RouteNetwork
from humanitarian_route_planner.models import CostWeights
from humanitarian_route_planner.algorithms import compare_algorithms

network = RouteNetwork.from_json(Path("data/hrp_network.json"))
scenario = {s["id"]: s for s in network.metadata["scenarios"]}["S5"]   # El Obeid airport closed
disrupted = network.with_adjustments(scenario["time_mult"], scenario["cost_mult"])
results = compare_algorithms(
    disrupted, start="IHC", goal="ELO", weights=CostWeights(time=1.0, cost=0.75, risk=2.0),
    blocked_edges=set(scenario["close_edges"]),
)
for result in results:
    print(result.algorithm, result.success, round(result.objective_score, 2), result.transfers, result.node_path)
```

## Limitations

- No live route data, schedules, geocoding, map tiles, customs/permit rules, road traffic, loading/handling, inventory, fleet availability, or shipment-specific capacity checks.
- The network is small and its values are estimates. A leg in the data does not establish that a corridor exists, is open, or is permitted.
- Reliability multiplies leg reliabilities as if legs were independent, and the slow case adds every leg's p90, which overstates a route's real 90th-percentile time.
- Capacity is only displayed as an edge property. The system does not allocate cargo or check packing and handling constraints.
- Risk is an ordinal teaching score added over links. It is not a calibrated probability or current security assessment.
- Real operational use would require authoritative timestamped data, domain validation, uncertainty handling, security review, and an authorized human decision-maker.

## Team

CSCI218 group project. Each member's contribution is recorded in the team contribution table (Appendix A of the group report) and in this repository's commit history.

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
2. Switch to your own branch: `git checkout -b <name>/<topic>` the first time; afterwards `git checkout <name>/<topic>`, then `git merge main`.
3. Work on your own files and run the tests (see Run tests).
4. Commit small steps and push: `git add <your files>`, then `git commit -m "Describe the change"`, then `git push -u origin <name>/<topic>`.
5. Open a pull request into `main` on GitHub, ask a teammate to review it, then merge.

Talk to the team before changing shared files (the core in `humanitarian_route_planner/`, the data, `app.py` and `ui/`). Commit in your own name, and never commit `.venv`, passwords or personal data.

## Submission notes

Use a shared Git repository and commit genuine work throughout the project; the supplied rubric treats history as evidence of contribution. All members should understand the entire codebase for the individual viva. The supplied brief also calls for a structured report, screenshots, repeatable experiments, results versus a baseline, limitations, references, and appendices. See `docs/project_alignment.md` and `docs/experiment_plan.md`. Follow the course's AI-tool policy and disclose assistance as required. Do not claim real industry engagement or mentor validation unless it occurred and is documented.
