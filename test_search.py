"""Tests for Koushik's searches. Remove each skip once that function works."""

from __future__ import annotations

import functools
import unittest
from pathlib import Path

from humanitarian_route_planner.algorithms import a_star, dijkstra
from humanitarian_route_planner.models import CostWeights
from humanitarian_route_planner.network import RouteNetwork
from team.koushik_search.search import breadth_first_search, greedy_best_first, weighted_a_star

ROOT = Path(__file__).resolve().parents[2]
NETWORK = RouteNetwork.from_json(ROOT / "data" / "sample_network.json")
START, GOAL = "DUBAI_HUB", "RELIEF_DESTINATION"
WEIGHTS = CostWeights()


class BreadthFirstTests(unittest.TestCase):
    @unittest.skip("TODO (Koushik): remove once breadth_first_search works")
    def test_finds_the_fewest_legs(self):
        result = breadth_first_search(NETWORK, START, GOAL, WEIGHTS)
        self.assertTrue(result.success)
        self.assertLessEqual(result.hops, dijkstra(NETWORK, START, GOAL, WEIGHTS).hops)


class GreedyTests(unittest.TestCase):
    @unittest.skip("TODO (Koushik): remove once greedy_best_first works")
    def test_finds_a_route_that_may_cost_more(self):
        result = greedy_best_first(NETWORK, START, GOAL, WEIGHTS)
        self.assertTrue(result.success)
        optimal = dijkstra(NETWORK, START, GOAL, WEIGHTS).objective_score
        self.assertGreaterEqual(result.objective_score, optimal - 1e-9)


class WeightedAStarTests(unittest.TestCase):
    @unittest.skip("TODO (Koushik): remove once weighted_a_star works")
    def test_epsilon_one_matches_a_star(self):
        result = weighted_a_star(NETWORK, START, GOAL, WEIGHTS, epsilon=1.0)
        self.assertAlmostEqual(result.objective_score, a_star(NETWORK, START, GOAL, WEIGHTS).objective_score)

    @unittest.skip("TODO (Koushik): remove once weighted_a_star works")
    def test_cost_stays_within_epsilon_of_optimal(self):
        optimal = dijkstra(NETWORK, START, GOAL, WEIGHTS).objective_score
        for epsilon in (1.5, 2.0, 3.0):
            result = weighted_a_star(NETWORK, START, GOAL, WEIGHTS, epsilon=epsilon)
            self.assertLessEqual(result.objective_score, epsilon * optimal + 1e-9)


class ClosureTests(unittest.TestCase):
    @unittest.skip("TODO (Koushik): remove once all three searches work")
    def test_every_search_avoids_a_closed_hub(self):
        searches = (breadth_first_search, greedy_best_first, functools.partial(weighted_a_star, epsilon=2.0))
        for search in searches:
            result = search(NETWORK, START, GOAL, WEIGHTS, blocked_nodes={"CAIRO_HUB"})
            self.assertNotIn("CAIRO_HUB", result.node_path)


if __name__ == "__main__":
    unittest.main()
