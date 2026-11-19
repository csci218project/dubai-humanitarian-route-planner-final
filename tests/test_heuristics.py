"""Tests for the heuristics and their checks (humanitarian_route_planner/heuristics.py)."""

from __future__ import annotations

import unittest
from pathlib import Path

from humanitarian_route_planner.algorithms import dijkstra
from humanitarian_route_planner.heuristics import (
    a_star_with, check_admissible, check_consistent, compare_heuristics, distance_heuristic,
    max_heuristic, time_lower_bound_heuristic, zero_heuristic,
)
from humanitarian_route_planner.models import CostWeights
from humanitarian_route_planner.network import RouteNetwork

ROOT = Path(__file__).resolve().parents[1]
HRP = RouteNetwork.from_json(ROOT / "data" / "hrp_network.json")
SCENARIOS = {spec["id"]: spec for spec in HRP.metadata["scenarios"]}
PRESETS = {
    "Fastest": CostWeights(5, 0, 0), "Cheapest": CostWeights(0, 5, 0),
    "Safest": CostWeights(0, 0, 5), "Balanced": CostWeights(),
}
BUILDERS = {"zero": zero_heuristic, "distance": distance_heuristic, "time": time_lower_bound_heuristic}


def scenario(spec_id: str) -> tuple[RouteNetwork, set[str]]:
    spec = SCENARIOS[spec_id]
    return HRP.with_adjustments(spec["time_mult"], spec["cost_mult"]), set(spec["close_edges"])


class SafetyTests(unittest.TestCase):
    def test_every_heuristic_is_admissible_and_consistent(self):
        for spec_id in ("S0", "S5", "S6", "S9"):
            network, closed = scenario(spec_id)
            for preset, weights in PRESETS.items():
                built = {name: build(network, "ELO", weights, None, closed) for name, build in BUILDERS.items()}
                built["max"] = max_heuristic(built["distance"], built["time"])
                for name, heuristic in built.items():
                    label = f"{spec_id} {preset} {name}"
                    self.assertEqual(check_admissible(network, "ELO", weights, heuristic, None, closed), [], label)
                    self.assertEqual(check_consistent(network, "ELO", weights, heuristic, None, closed), [], label)

    def test_estimate_at_the_goal_is_zero(self):
        for name, build in BUILDERS.items():
            self.assertEqual(build(HRP, "ELO", CostWeights())("ELO"), 0.0, msg=name)

    def test_an_overestimate_is_caught(self):
        weights = CostWeights()
        distance = distance_heuristic(HRP, "ELO", weights)
        inflated = lambda node_id: 1000 * distance(node_id)  # noqa: E731
        self.assertNotEqual(check_admissible(HRP, "ELO", weights, inflated), [])
        self.assertNotEqual(check_consistent(HRP, "ELO", weights, inflated), [])

    def test_time_bound_is_zero_without_a_time_weight(self):
        self.assertEqual(time_lower_bound_heuristic(HRP, "ELO", CostWeights(0, 5, 0))("IHC"), 0.0)


class SearchTests(unittest.TestCase):
    def test_a_star_with_each_heuristic_is_optimal(self):
        for spec_id in ("S0", "S5"):
            network, closed = scenario(spec_id)
            for preset, weights in PRESETS.items():
                best = dijkstra(network, "IHC", "ELO", weights, blocked_edges=closed).objective_score
                for name, build in BUILDERS.items():
                    heuristic = build(network, "ELO", weights, None, closed)
                    result = a_star_with(network, "IHC", "ELO", weights, heuristic, blocked_edges=closed)
                    self.assertAlmostEqual(result.objective_score, best, msg=f"{spec_id} {preset} {name}")

    def test_zero_heuristic_expands_like_dijkstra(self):
        weights = CostWeights()
        result = a_star_with(HRP, "IHC", "ELO", weights, zero_heuristic(HRP, "ELO", weights))
        self.assertEqual(result.nodes_expanded, dijkstra(HRP, "IHC", "ELO", weights).nodes_expanded)

    def test_comparison_covers_every_heuristic(self):
        rows = compare_heuristics(HRP, "IHC", "ELO", CostWeights(5, 0, 0))
        self.assertEqual([row["heuristic"] for row in rows],
                         ["Zero (Dijkstra)", "Distance (used by A*)", "Time lower bound", "Max of distance and time"])
        self.assertTrue(all(row["admissible"] and row["consistent"] for row in rows))
        self.assertEqual(len({round(row["objective_score"], 9) for row in rows}), 1)


if __name__ == "__main__":
    unittest.main()
