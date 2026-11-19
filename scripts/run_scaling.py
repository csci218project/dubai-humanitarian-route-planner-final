"""Scaling experiment: Dijkstra vs A* on seeded random networks of growing size.

Run from the repository root (the plot needs matplotlib from requirements-dev.txt):
    python scripts/run_scaling.py --sizes 100 250 500 1000 2500 5000 --seeds 5 --repeats 3 --output-dir results

For each size and seed it builds a network with humanitarian_route_planner.synthetic,
routes from the hub nearest Dubai to the hub nearest El Obeid under the Fastest and
Balanced presets, and records states expanded and runtime (median of --repeats runs).
Writes scaling.csv (every run), scaling_summary.csv (mean and SD per size) and
scaling.png. The networks are synthetic; the results measure the algorithms only.
"""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from humanitarian_route_planner.algorithms import a_star, dijkstra  # noqa: E402
from humanitarian_route_planner.models import CostWeights  # noqa: E402
from humanitarian_route_planner.synthetic import generate_network  # noqa: E402

PRESETS = {"Fastest": CostWeights(5.0, 0.0, 0.0), "Balanced": CostWeights(1.0, 0.75, 2.0)}
ALGORITHMS = {"Dijkstra": dijkstra, "A*": a_star}


def mean_sd(values: list[float]) -> tuple[float, float]:
    return statistics.mean(values), (statistics.stdev(values) if len(values) > 1 else 0.0)


def run(sizes: list[int], seeds: list[int], repeats: int, output_dir: Path, plot: bool = True) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for size in sizes:
        for seed in seeds:
            network = generate_network(size, seed)
            origin, goal = network.metadata["default_origin"], network.metadata["default_destination"]
            for preset, weights in PRESETS.items():
                results = {name: [solve(network, origin, goal, weights) for _ in range(repeats)]
                           for name, solve in ALGORITHMS.items()}
                best = results["Dijkstra"][0]
                for name, runs in results.items():
                    first = runs[0]
                    rows.append({
                        "hubs": size, "legs": len(network.edges), "seed": seed, "preset": preset,
                        "algorithm": name, "success": first.success, "objective_score": first.objective_score,
                        "matches_dijkstra": first.success and best.success
                        and abs(first.objective_score - best.objective_score) < 1e-9,
                        "nodes_expanded": first.nodes_expanded,
                        "runtime_ms_median": statistics.median(r.runtime_ms for r in runs),
                        "route_legs": first.hops, "transfers": first.transfers,
                    })

    summary: list[dict] = []
    for size in sizes:
        for preset in PRESETS:
            dijkstra_by_seed = {r["seed"]: r for r in rows
                                if (r["hubs"], r["preset"], r["algorithm"]) == (size, preset, "Dijkstra")}
            for name in ALGORITHMS:
                mine = [r for r in rows if (r["hubs"], r["preset"], r["algorithm"]) == (size, preset, name)]
                expanded = mean_sd([float(r["nodes_expanded"]) for r in mine])
                runtime = mean_sd([float(r["runtime_ms_median"]) for r in mine])
                share = [100.0 * r["nodes_expanded"] / dijkstra_by_seed[r["seed"]]["nodes_expanded"] for r in mine]
                summary.append({
                    "hubs": size, "preset": preset, "algorithm": name, "seeds": len(mine),
                    "mean_legs_in_network": statistics.mean(r["legs"] for r in mine),
                    "mean_nodes_expanded": expanded[0], "sd_nodes_expanded": expanded[1],
                    "mean_runtime_ms": runtime[0], "sd_runtime_ms": runtime[1],
                    "mean_states_vs_dijkstra_pct": statistics.mean(share),
                    "all_match_dijkstra": all(r["matches_dijkstra"] for r in mine),
                })

    paths = [output_dir / "scaling.csv", output_dir / "scaling_summary.csv"]
    for path, table in zip(paths, (rows, summary)):
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(table[0].keys()))
            writer.writeheader()
            writer.writerows(table)
    if plot:
        paths.append(draw(summary, sizes, len(seeds), repeats, output_dir / "scaling.png"))
    return paths


def draw(summary: list[dict], sizes: list[int], seeds: int, repeats: int, path: Path) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, (left, right) = plt.subplots(1, 2, figsize=(11, 4.3))
    for preset, line in (("Fastest", "-"), ("Balanced", "--")):
        for name, colour in (("Dijkstra", "#1F4436"), ("A*", "#A9853A")):
            mine = sorted((r for r in summary if (r["preset"], r["algorithm"]) == (preset, name)),
                          key=lambda r: r["hubs"])
            hubs = [r["hubs"] for r in mine]
            for axis, key in ((left, "nodes_expanded"), (right, "runtime_ms")):
                axis.errorbar(hubs, [r[f"mean_{key}"] for r in mine], yerr=[r[f"sd_{key}"] for r in mine],
                              linestyle=line, color=colour, marker="o", markersize=4, capsize=3,
                              label=f"{name}, {preset}")
    for axis, title in ((left, "States expanded"), (right, f"Runtime, ms (median of {repeats} runs)")):
        axis.set_xscale("log")
        axis.set_yscale("log")
        axis.set_xlabel("Hubs in the network")
        axis.set_title(title)
        axis.grid(True, which="both", alpha=0.25)
    left.legend(frameon=False)
    figure.suptitle(f"Dijkstra vs A* on random networks (mean ± SD over {seeds} seeds)")
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sizes", type=int, nargs="+", default=[100, 250, 500, 1000, 2500, 5000],
                        help="Network sizes in hubs (default 100 250 500 1000 2500 5000).")
    parser.add_argument("--seeds", type=int, default=5, help="Seeds per size, starting at 218 (default 5).")
    parser.add_argument("--repeats", type=int, default=3, help="Runs per case for the runtime median (default 3).")
    parser.add_argument("--output-dir", default="results", help="Folder for the CSV files and the plot.")
    parser.add_argument("--no-plot", action="store_true", help="Skip the plot (no matplotlib needed).")
    args = parser.parse_args()
    if args.seeds < 1 or args.repeats < 1 or min(args.sizes) < 2:
        parser.error("--seeds and --repeats must be at least 1, and sizes at least 2")
    seeds = [218 + i for i in range(args.seeds)]
    for path in run(args.sizes, seeds, args.repeats, Path(args.output_dir), plot=not args.no_plot):
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
