"""Tests for the random network generator and the scaling script."""

from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

from humanitarian_route_planner.algorithms import a_star, dijkstra
from humanitarian_route_planner.models import CostWeights
from humanitarian_route_planner.synthetic import generate_network

ROOT = Path(__file__).resolve().parents[1]


def shape(network):
    return ([(n.node_id, n.latitude, n.longitude, n.node_type) for n in network.nodes.values()],
            [(e.source, e.target, e.mode, e.time_hours, e.cost_usd, e.risk_score) for e in network.edges.values()])


class GeneratorTests(unittest.TestCase):
    def test_same_seed_gives_the_same_network(self):
        self.assertEqual(shape(generate_network(150, seed=7)), shape(generate_network(150, seed=7)))

    def test_different_seeds_give_different_networks(self):
        self.assertNotEqual(shape(generate_network(150, seed=7)), shape(generate_network(150, seed=8)))

    def test_has_the_requested_hubs_and_all_three_modes(self):
        network = generate_network(300, seed=1)
        self.assertEqual(len(network.nodes), 300)
        self.assertEqual({e.mode for e in network.edges.values()}, {"road", "air", "sea"})
        self.assertIsNotNone(network.transfer)

    def test_every_hub_can_reach_every_other(self):
        network = generate_network(400, seed=3)
        start = network.metadata["default_origin"]
        seen, stack = {start}, [start]
        while stack:
            for nxt, _ in network.neighbors(stack.pop()):
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        self.assertEqual(seen, set(network.nodes))

    def test_rejects_a_one_hub_network(self):
        with self.assertRaises(ValueError):
            generate_network(1, seed=1)


class SearchTests(unittest.TestCase):
    def test_a_star_matches_dijkstra_on_random_networks(self):
        presets = {"Fastest": CostWeights(5, 0, 0), "Cheapest": CostWeights(0, 5, 0), "Balanced": CostWeights()}
        for size in (60, 400):
            for seed in (1, 2, 3):
                network = generate_network(size, seed)
                origin, goal = network.metadata["default_origin"], network.metadata["default_destination"]
                for name, weights in presets.items():
                    best = dijkstra(network, origin, goal, weights)
                    result = a_star(network, origin, goal, weights)
                    self.assertTrue(best.success)
                    self.assertAlmostEqual(result.objective_score, best.objective_score,
                                           msg=f"{size} hubs, seed {seed}, {name}")


class ScriptTests(unittest.TestCase):
    def test_scaling_script_writes_both_tables(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        try:
            import run_scaling
        finally:
            sys.path.pop(0)
        with tempfile.TemporaryDirectory() as folder:
            trials, summary = run_scaling.run([40, 80], seeds=[1], repeats=1, output_dir=Path(folder), plot=False)
            with trials.open(encoding="utf-8") as handle:
                self.assertEqual(len(list(csv.DictReader(handle))), 8)    # 2 sizes x 2 presets x 2 algorithms
            with summary.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 8)
            self.assertTrue(all(row["all_match_dijkstra"] == "True" for row in rows))


if __name__ == "__main__":
    unittest.main()
