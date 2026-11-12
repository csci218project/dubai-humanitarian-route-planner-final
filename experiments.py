"""Repeatable experiments. Write every result to results/ as CSV, with the seeds.

Owner: Shreya.
"""

from __future__ import annotations

from pathlib import Path

from humanitarian_route_planner.network import RouteNetwork

RESULTS_DIR = Path(__file__).resolve().parent / "results"


def run_scaling(
    sizes: tuple[int, ...] = (100, 1000, 5000),
    seeds: tuple[int, ...] = (1, 2, 3, 4, 5),
    queries_per_network: int = 10,
    output_dir: Path = RESULTS_DIR,
) -> Path:
    """For each size and seed, generate a network, pick random start and goal pairs,
    run each algorithm, and record states expanded and runtime. Return the CSV path."""
    raise NotImplementedError("Shreya: run_scaling is not written yet")


def run_monte_carlo(
    network: RouteNetwork,
    start: str,
    goal: str,
    trials: int = 1000,
    seed: int = 218,
    output_dir: Path = RESULTS_DIR,
) -> Path:
    """Plan the fastest and the safest route, then in each trial close links at random
    (probability from the risk score) and record whether each route survives and how
    much replanning delays it. Return the CSV path."""
    raise NotImplementedError("Shreya: run_monte_carlo is not written yet")


def plot_scaling(csv_path: Path, output_path: Path) -> None:
    """States expanded and runtime against network size, one line per algorithm,
    showing the mean with standard-deviation error bars."""
    raise NotImplementedError("Shreya: plot_scaling is not written yet")
