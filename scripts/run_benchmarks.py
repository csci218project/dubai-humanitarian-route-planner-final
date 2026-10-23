"""Reproducible algorithm benchmark with seeded synthetic disruptions.

Run from the repository root:
    python scripts/run_benchmarks.py --trials 30 --seed 218 --output-dir results

The CSVs describe simulation performance only, not real-world delivery outcomes.
"""

from __future__ import annotations

import argparse
import csv
import random
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from humanitarian_route_planner.algorithms import compare_algorithms  # noqa: E402
from humanitarian_route_planner.models import CostWeights  # noqa: E402
from humanitarian_route_planner.network import RouteNetwork  # noqa: E402


def mean_sd(values: list[float]) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    if len(values) == 1:
        return statistics.mean(values), 0.0
    return statistics.mean(values), statistics.stdev(values)


def run(trials: int, seed: int, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    network = RouteNetwork.from_json(ROOT / "data" / "sample_network.json")
    weights = CostWeights(time=1.0, cost=0.75, risk=2.0)
    rng = random.Random(seed)
    edge_ids = sorted(network.edges)
    node_ids = sorted(network.nodes)
    protected_nodes = {"DUBAI_HUB", "RELIEF_DESTINATION"}
    algorithms = ["Dijkstra", "A*", "Hierarchical"]
    trial_rows: list[dict] = []

    for trial in range(1, trials + 1):
        # Seeded closures permit repeatable dynamic-environment experiments.
        number_closed_edges = rng.randint(0, max(1, len(edge_ids) // 5))
        blocked_edges = set(rng.sample(edge_ids, number_closed_edges))
        closeable_nodes = [node_id for node_id in node_ids if node_id not in protected_nodes]
        blocked_nodes = {node_id for node_id in closeable_nodes if rng.random() < 0.08}
        results = compare_algorithms(
            network, "DUBAI_HUB", "RELIEF_DESTINATION", weights,
            blocked_nodes=blocked_nodes,
            blocked_edges=blocked_edges,
        )
        by_name = {result.algorithm: result for result in results}
        baseline = by_name["Dijkstra"]

        for algorithm in algorithms:
            result = by_name[algorithm]
            if result.success and baseline.success and baseline.objective_score and baseline.objective_score > 0:
                gap = (result.objective_score - baseline.objective_score) / baseline.objective_score * 100.0
            elif result.success and baseline.success:
                gap = 0.0
            else:
                gap = None
            trial_rows.append({
                "trial": trial,
                "seed": seed,
                "algorithm": algorithm,
                "success": result.success,
                "objective_score": result.objective_score,
                "time_hours": result.total_time_hours,
                "cost_usd": result.total_cost_usd,
                "risk_points": result.total_risk_points,
                "nodes_expanded": result.nodes_expanded,
                "runtime_ms": result.runtime_ms,
                "optimality_gap_pct_vs_dijkstra": gap,
                "blocked_nodes": ";".join(sorted(blocked_nodes)),
                "blocked_edges": ";".join(sorted(blocked_edges)),
                "path_node_ids": ">".join(result.node_path),
                "path_edge_ids": ">".join(result.edge_path),
                "message": result.message,
            })

    trials_path = output_dir / "benchmark_trials.csv"
    with trials_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(trial_rows[0].keys()))
        writer.writeheader()
        writer.writerows(trial_rows)

    summary_rows: list[dict] = []
    for algorithm in algorithms:
        rows = [row for row in trial_rows if row["algorithm"] == algorithm]
        successes = [row for row in rows if row["success"]]
        runtime_values = [float(row["runtime_ms"]) for row in successes]
        expanded_values = [float(row["nodes_expanded"]) for row in successes]
        score_values = [float(row["objective_score"]) for row in successes if row["objective_score"] is not None]
        gaps = [float(row["optimality_gap_pct_vs_dijkstra"]) for row in rows if row["optimality_gap_pct_vs_dijkstra"] is not None]
        runtime_mean, runtime_sd = mean_sd(runtime_values)
        expanded_mean, expanded_sd = mean_sd(expanded_values)
        score_mean, score_sd = mean_sd(score_values)
        gap_mean, gap_sd = mean_sd(gaps)
        summary_rows.append({
            "algorithm": algorithm,
            "trials": trials,
            "successes": len(successes),
            "success_rate_pct": (len(successes) / trials * 100.0) if trials else 0.0,
            "mean_runtime_ms_successful": runtime_mean,
            "sd_runtime_ms_successful": runtime_sd,
            "mean_nodes_expanded_successful": expanded_mean,
            "sd_nodes_expanded_successful": expanded_sd,
            "mean_objective_score_successful": score_mean,
            "sd_objective_score_successful": score_sd,
            "mean_optimality_gap_pct_vs_dijkstra": gap_mean,
            "sd_optimality_gap_pct_vs_dijkstra": gap_sd,
            "seed": seed,
            "note": "Synthetic teaching benchmark; do not interpret as operational performance.",
        })

    summary_path = output_dir / "benchmark_summary.csv"
    with summary_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)
    return trials_path, summary_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=30, help="Number of disruption scenarios (default: 30).")
    parser.add_argument("--seed", type=int, default=218, help="Random seed for reproducibility (default: 218).")
    parser.add_argument("--output-dir", default="results", help="Directory for the two CSV output files.")
    args = parser.parse_args()
    if args.trials < 1:
        parser.error("--trials must be at least 1")
    trials_file, summary_file = run(args.trials, args.seed, Path(args.output_dir))
    print(f"Trial-level results: {trials_file}")
    print(f"Summary results:     {summary_file}")
    print("Reminder: these results use synthetic data and do not represent real humanitarian operations.")


if __name__ == "__main__":
    main()
