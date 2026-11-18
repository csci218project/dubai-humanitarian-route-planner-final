"""Reproducible benchmark on the Dubai Humanitarian network (data/hrp_network.json).

Run from the repository root:
    python scripts/run_benchmarks.py --trials 30 --seed 218 --repeats 5 --output-dir results

Two experiment sets, each solved by Dijkstra, A* and hierarchical search:
1. scenarios: every scenario in the data (S0-S9) under four weight presets.
2. random: seeded random disruptions (closed legs and hubs) under the Balanced weights.

Writes benchmark_scenarios.csv, benchmark_trials.csv and benchmark_summary.csv.
Runtimes are the median of --repeats runs. The results measure the algorithms
on the provided data; they are not operational delivery outcomes.
"""

from __future__ import annotations

import argparse
import csv
import random
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from humanitarian_route_planner.algorithms import compare_algorithms  # noqa: E402
from humanitarian_route_planner.models import CostWeights, RouteResult  # noqa: E402
from humanitarian_route_planner.network import RouteNetwork  # noqa: E402

NETWORK_FILE = ROOT / "data" / "hrp_network.json"
ALGORITHMS = ["Dijkstra", "A*", "Hierarchical"]
PRESETS = {
    "Fastest": CostWeights(5.0, 0.0, 0.0),
    "Cheapest": CostWeights(0.0, 5.0, 0.0),
    "Safest": CostWeights(0.0, 0.0, 5.0),
    "Balanced": CostWeights(1.0, 0.75, 2.0),
}


def mean_sd(values: list[float]) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    if len(values) == 1:
        return statistics.mean(values), 0.0
    return statistics.mean(values), statistics.stdev(values)


def solve(network: RouteNetwork, origin: str, goal: str, weights: CostWeights,
          blocked_nodes: set[str], blocked_edges: set[str], repeats: int) -> dict[str, tuple[RouteResult, float]]:
    """Run all three algorithms `repeats` times; keep the first result and the median runtime."""
    runs = [compare_algorithms(network, origin, goal, weights, blocked_nodes, blocked_edges) for _ in range(repeats)]
    output = {}
    for index, algorithm in enumerate(ALGORITHMS):
        output[algorithm] = (runs[0][index], statistics.median(run[index].runtime_ms for run in runs))
    return output


def rows_for(experiment: str, case: str, preset: str, solved: dict, blocked_nodes: set[str],
             blocked_edges: set[str], seed: int | None) -> list[dict]:
    reference = solved["Dijkstra"][0]
    rows = []
    for algorithm in ALGORITHMS:
        result, runtime = solved[algorithm]
        gap = None
        if result.success and reference.success and reference.objective_score:
            gap = (result.objective_score - reference.objective_score) / reference.objective_score * 100.0
        rows.append({
            "experiment": experiment, "case": case, "preset": preset, "seed": seed, "algorithm": algorithm,
            "success": result.success, "objective_score": result.objective_score,
            "time_hours": result.total_time_hours, "time_p90_hours": result.total_time_p90_hours,
            "cost_usd_per_tonne": result.total_cost_usd, "risk_points": result.total_risk_points,
            "reliability_pct": result.reliability_pct, "transfers": result.transfers, "legs": result.hops,
            "nodes_expanded": result.nodes_expanded, "runtime_ms_median": runtime,
            "gap_pct_vs_dijkstra": gap,
            "blocked_nodes": ";".join(sorted(blocked_nodes)), "blocked_edges": ";".join(sorted(blocked_edges)),
            "path_node_ids": ">".join(result.node_path), "message": result.message,
        })
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def run(trials: int, seed: int, repeats: int, output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    base = RouteNetwork.from_json(NETWORK_FILE)
    origin, goal = base.metadata["default_origin"], base.metadata["default_destination"]

    scenario_rows: list[dict] = []
    for spec in base.metadata["scenarios"]:
        network = base.with_adjustments(spec["time_mult"], spec["cost_mult"])
        closed_edges = set(spec["close_edges"])
        for preset, weights in PRESETS.items():
            solved = solve(network, origin, goal, weights, set(), closed_edges, repeats)
            scenario_rows += rows_for("scenarios", spec["id"], preset, solved, set(), closed_edges, None)

    rng = random.Random(seed)
    legs = sorted(base.edges)
    hubs = [node_id for node_id in sorted(base.nodes) if node_id not in (origin, goal)]
    trial_rows: list[dict] = []
    for trial in range(1, trials + 1):
        # Seeded closures make the random disruptions repeatable.
        closed_edges = set(rng.sample(legs, rng.randint(1, 4)))
        closed_nodes = {hub for hub in hubs if rng.random() < 0.08}
        solved = solve(base, origin, goal, PRESETS["Balanced"], closed_nodes, closed_edges, repeats)
        trial_rows += rows_for("random", f"T{trial:02d}", "Balanced", solved, closed_nodes, closed_edges, seed)

    summary_rows: list[dict] = []
    for experiment, rows in (("scenarios", scenario_rows), ("random", trial_rows)):
        for algorithm in ALGORITHMS:
            mine = [row for row in rows if row["algorithm"] == algorithm]
            ok = [row for row in mine if row["success"]]
            gaps = [row["gap_pct_vs_dijkstra"] for row in mine if row["gap_pct_vs_dijkstra"] is not None]
            expanded = mean_sd([float(row["nodes_expanded"]) for row in ok])
            runtime = mean_sd([float(row["runtime_ms_median"]) for row in ok])
            score = mean_sd([float(row["objective_score"]) for row in ok])
            gap = mean_sd(gaps)
            summary_rows.append({
                "experiment": experiment, "algorithm": algorithm, "runs": len(mine), "successes": len(ok),
                "success_rate_pct": len(ok) / len(mine) * 100.0 if mine else 0.0,
                "mean_nodes_expanded": expanded[0], "sd_nodes_expanded": expanded[1],
                "mean_runtime_ms": runtime[0], "sd_runtime_ms": runtime[1],
                "mean_objective_score": score[0], "sd_objective_score": score[1],
                "mean_gap_pct_vs_dijkstra": gap[0], "sd_gap_pct_vs_dijkstra": gap[1],
                "max_gap_pct_vs_dijkstra": max(gaps) if gaps else None,
                "runs_matching_dijkstra": sum(1 for value in gaps if abs(value) < 1e-9),
                "seed": seed if experiment == "random" else None, "repeats": repeats,
            })

    paths = [output_dir / "benchmark_scenarios.csv", output_dir / "benchmark_trials.csv",
             output_dir / "benchmark_summary.csv"]
    for path, rows in zip(paths, (scenario_rows, trial_rows, summary_rows)):
        write_csv(path, rows)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--trials", type=int, default=30, help="Random disruptions to run (default 30).")
    parser.add_argument("--seed", type=int, default=218, help="Random seed (default 218).")
    parser.add_argument("--repeats", type=int, default=5, help="Runs per case for the runtime median (default 5).")
    parser.add_argument("--output-dir", default="results", help="Folder for the CSV files.")
    args = parser.parse_args()
    if args.trials < 1 or args.repeats < 1:
        parser.error("--trials and --repeats must be at least 1")
    for path in run(args.trials, args.seed, args.repeats, Path(args.output_dir)):
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
