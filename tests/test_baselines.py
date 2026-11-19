"""Tests for the baseline searches (humanitarian_route_planner/baselines.py)."""

from __future__ import annotations

import unittest
from pathlib import Path

from humanitarian_route_planner.algorithms import dijkstra
from humanitarian_route_planner.baselines import (
    breadth_first_search, compare_baselines, greedy_best_first, weighted_a_star,
)
from humanitarian_route_planner.models import CostWeights
from humanitarian_route_planner.network import RouteNetwork

ROOT = Path(__file__).resolve().parents[1]
HRP = RouteNetwork.from_json(ROOT / "data" / "hrp_network.json")
SAMPLE = RouteNetwork.from_json(ROOT / "data" / "sample_network.json")
SCENARIOS = {spec["id"]: spec for spec in HRP.metadata["scenarios"]}
PRESETS = {
    "Fastest": CostWeights(5, 0, 0), "Cheapest": CostWeights(0, 5, 0),
    "Safest": CostWeights(0, 0, 5), "Balanced": CostWeights(),
}


def leg_counts(blocked_edges: set[str], start: str = "IHC", goal: str = "ELO") -> list[int]:
    """Leg counts of every loop-free route through the (one-way) HRP network."""
    counts: list[int] = []

    def walk(node: str, legs: int, visited: set[str]) -> None:
        if node == goal:
            counts.append(legs)
            return
        for nxt, _ in HRP.neighbors(node, blocked_edges=blocked_edges):
            if nxt not in visited:
                walk(nxt, legs + 1, visited | {nxt})

    walk(start, 0, {start})
    return counts


def follows_its_legs(network: RouteNetwork, result) -> bool:
    """Every leg starts where the previous one ended, in an allowed direction."""
    for edge_id, here, there in zip(result.edge_path, result.node_path, result.node_path[1:]):
        edge = network.edges[edge_id]
        if network.directed and (edge.source, edge.target) != (here, there):
            return False
        if not network.directed and {edge.source, edge.target} != {here, there}:
            return False
    return len(result.node_path) == len(result.edge_path) + 1


class BreadthFirstTests(unittest.TestCase):
    def test_finds_the_fewest_legs_in_every_scenario(self):
        for spec in SCENARIOS.values():
            closed = set(spec["close_edges"])
            result = breadth_first_search(HRP, "IHC", "ELO", CostWeights(), blocked_edges=closed)
            self.assertEqual(result.hops, min(leg_counts(closed)), msg=spec["id"])
            self.assertTrue(follows_its_legs(HRP, result), msg=spec["id"])

    def test_avoids_closed_legs(self):
        closed = set(SCENARIOS["S5"]["close_edges"])   # El Obeid airport closed
        result = breadth_first_search(HRP, "IHC", "ELO", CostWeights(), blocked_edges=closed)
        self.assertTrue(result.success)
        self.assertFalse(closed & set(result.edge_path))

    def test_reports_no_route_when_the_destination_is_cut_off(self):
        into_elo = {edge_id for edge_id, edge in HRP.edges.items() if edge.target == "ELO"}
        self.assertFalse(breadth_first_search(HRP, "IHC", "ELO", CostWeights(), blocked_edges=into_elo).success)


class GreedyTests(unittest.TestCase):
    def test_route_is_valid_in_every_scenario(self):
        for spec in SCENARIOS.values():
            closed = set(spec["close_edges"])
            result = greedy_best_first(HRP, "IHC", "ELO", CostWeights(), blocked_edges=closed)
            self.assertTrue(result.success, msg=spec["id"])
            self.assertTrue(follows_its_legs(HRP, result), msg=spec["id"])
            self.assertFalse(closed & set(result.edge_path), msg=spec["id"])

    def test_never_beats_dijkstra(self):
        for name, weights in PRESETS.items():
            greedy = greedy_best_first(HRP, "IHC", "ELO", weights)
            best = dijkstra(HRP, "IHC", "ELO", weights)
            self.assertGreaterEqual(greedy.objective_score + 1e-9, best.objective_score, msg=name)


class WeightedAStarTests(unittest.TestCase):
    def test_score_stays_within_epsilon_of_optimal(self):
        for spec in SCENARIOS.values():
            network = HRP.with_adjustments(spec["time_mult"], spec["cost_mult"])
            closed = set(spec["close_edges"])
            for name, weights in PRESETS.items():
                best = dijkstra(network, "IHC", "ELO", weights, blocked_edges=closed).objective_score
                for epsilon in (1.0, 1.5, 2.0, 3.0):
                    result = weighted_a_star(network, "IHC", "ELO", weights, epsilon, blocked_edges=closed)
                    self.assertLessEqual(result.objective_score, epsilon * best + 1e-9,
                                         msg=f"{spec['id']} {name} ε={epsilon}")

    def test_epsilon_one_is_optimal(self):
        for name, weights in PRESETS.items():
            self.assertAlmostEqual(weighted_a_star(HRP, "IHC", "ELO", weights, 1.0).objective_score,
                                   dijkstra(HRP, "IHC", "ELO", weights).objective_score, msg=name)

    def test_epsilon_below_one_is_rejected(self):
        with self.assertRaises(ValueError):
            weighted_a_star(HRP, "IHC", "ELO", CostWeights(), 0.5)

    def test_works_on_a_two_way_network(self):
        best = dijkstra(SAMPLE, "DUBAI_HUB", "RELIEF_DESTINATION", CostWeights()).objective_score
        result = weighted_a_star(SAMPLE, "DUBAI_HUB", "RELIEF_DESTINATION", CostWeights(), 2.0)
        self.assertTrue(follows_its_legs(SAMPLE, result))
        self.assertLessEqual(result.objective_score, 2.0 * best + 1e-9)


class CompareTests(unittest.TestCase):
    def test_runs_all_three_baselines(self):
        names = [r.algorithm for r in compare_baselines(HRP, "IHC", "ELO", CostWeights())]
        self.assertEqual(names, ["BFS (fewest legs)", "Greedy best-first", "Weighted A* (ε=1.5)"])

    def test_unknown_closure_is_reported(self):
        result = breadth_first_search(HRP, "IHC", "ELO", CostWeights(), blocked_edges={"L99"})
        self.assertFalse(result.success)
        self.assertIn("Unknown", result.message)


if __name__ == "__main__":
    unittest.main()
