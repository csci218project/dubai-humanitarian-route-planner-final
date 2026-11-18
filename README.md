# Dubai Humanitarian — Humanitarian Route Planner

**CSCI218 Foundations of Artificial Intelligence | Autumn 2026 | University of Wollongong in Dubai**

An educational route-planning prototype for Project B, “Humanitarian Route Planner,” listed in the supplied Dubai Humanitarian project spreadsheet. It compares three AI search approaches on a relief network from Dubai to El Obeid in Sudan (23 hubs, 36 one-way legs) and shows how closures, slow-downs and cost shocks change the route.

> **Important limitation:** The network is illustrative and was compiled by the project team. Locations are real; transit times, costs, capacities, risk scores and reliability are planning estimates, not official Dubai Humanitarian data, schedules or security assessments. Do not use it to plan actual aid movements.

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
- Network data kept in a spreadsheet the team can edit, converted to the app's format by a script (see Data).
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
├── scripts/import_hrp_data.py         # Converts the spreadsheet into data/hrp_network.json
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

The app uses one network: relief cargo from the Dubai humanitarian logistics hub (IHC) to the El Obeid distribution hub in Sudan (ELO), with Port Sudan, Gedaref and Kosti as alternative destinations. The team keeps it in `data/hrp_network_data.xlsx`:

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
