"""Tests for Shreya's generator and experiments. Remove each skip once that part works."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from humanitarian_route_planner.algorithms import a_star, dijkstra
from humanitarian_route_planner.models import CostWeights
from team.shreya_experiments.experiments import run_scaling
from team.shreya_experiments.synthetic import generate_network


class GeneratorTests(unittest.TestCase):
    @unittest.skip("TODO (Shreya): remove once generate_network works")
    def test_same_seed_gives_the_same_network(self):
        first, second = generate_network(50, seed=218), generate_network(50, seed=218)
        self.assertEqual(sorted(first.nodes), sorted(second.nodes))
        self.assertEqual(sorted(first.edges), sorted(second.edges))

    @unittest.skip("TODO (Shreya): remove once generate_network works")
    def test_every_hub_is_reachable(self):
        network = generate_network(100, seed=7)
        hubs = sorted(network.nodes)
        for goal in hubs[1:]:
            self.assertTrue(dijkstra(network, hubs[0], goal, CostWeights()).success)

    @unittest.skip("TODO (Shreya): remove once generate_network works")
    def test_a_star_matches_dijkstra_on_random_networks(self):
        for seed in range(10):
            network = generate_network(200, seed=seed)
            hubs = sorted(network.nodes)
            start, goal = hubs[0], hubs[-1]
            self.assertAlmostEqual(
                a_star(network, start, goal, CostWeights()).objective_score,
                dijkstra(network, start, goal, CostWeights()).objective_score,
            )


class ExperimentTests(unittest.TestCase):
    @unittest.skip("TODO (Shreya): remove once run_scaling works")
    def test_scaling_writes_a_csv(self):
        with tempfile.TemporaryDirectory() as folder:
            path = run_scaling(sizes=(50, 100), seeds=(1, 2), queries_per_network=2, output_dir=Path(folder))
            self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()
