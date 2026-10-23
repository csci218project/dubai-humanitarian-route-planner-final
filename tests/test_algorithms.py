"""Functional and edge-case tests for route-finding algorithms."""
from pathlib import Path
import unittest
from humanitarian_route_planner.algorithms import a_star, dijkstra, hierarchical_search
from humanitarian_route_planner.models import CostWeights
from humanitarian_route_planner.network import RouteNetwork
ROOT = Path(__file__).resolve().parents[1]

class RouteAlgorithmTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.network = RouteNetwork.from_json(ROOT / "data" / "sample_network.json")
        cls.weights = CostWeights(time=1.0, cost=0.75, risk=2.0)
        cls.start, cls.goal = "DUBAI_HUB", "RELIEF_DESTINATION"

    def test_dijkstra_finds_a_route(self):
        r = dijkstra(self.network, self.start, self.goal, self.weights)
        self.assertTrue(r.success, r.message)
        self.assertEqual(r.node_path[0], self.start)
        self.assertEqual(r.node_path[-1], self.goal)
        self.assertEqual(len(r.edge_path), len(r.node_path) - 1)
        self.assertGreater(r.total_time_hours, 0)
        self.assertGreater(r.total_cost_usd, 0)

    def test_a_star_matches_dijkstra_objective(self):
        dj = dijkstra(self.network, self.start, self.goal, self.weights)
        astar = a_star(self.network, self.start, self.goal, self.weights)
        self.assertTrue(dj.success and astar.success)
        self.assertAlmostEqual(dj.objective_score, astar.objective_score, places=8)

    def test_hierarchical_route_is_contiguous(self):
        r = hierarchical_search(self.network, self.start, self.goal, self.weights)
        self.assertTrue(r.success, r.message)
        self.assertEqual(r.node_path[0], self.start)
        self.assertEqual(r.node_path[-1], self.goal)
        self.assertEqual(len(r.edge_path), len(r.node_path) - 1)
        for left, right, edge_id in zip(r.node_path, r.node_path[1:], r.edge_path):
            e = self.network.edges[edge_id]
            self.assertIn((left, right), ((e.source, e.target), (e.target, e.source)))
        self.assertGreaterEqual(len(r.abstract_regions), 1)

    def test_closing_airport_forces_a_different_feasible_route(self):
        baseline = a_star(self.network, self.start, self.goal, self.weights)
        disrupted = a_star(self.network, self.start, self.goal, self.weights, blocked_nodes={"DWC_AIRPORT"})
        self.assertTrue(baseline.success and disrupted.success)
        self.assertNotIn("DWC_AIRPORT", disrupted.node_path)

    def test_blocked_destination_returns_failure(self):
        r = dijkstra(self.network, self.start, self.goal, self.weights, blocked_nodes={self.goal})
        self.assertFalse(r.success)
        self.assertIn("destination", r.message.lower())

    def test_closing_all_final_corridors_returns_no_route(self):
        r = a_star(self.network, self.start, self.goal, self.weights,
                   blocked_edges={"E14_ELARISH_DESTINATION", "E15_AQABA_DESTINATION"})
        self.assertFalse(r.success)
        self.assertEqual(r.node_path, [])

    def test_zero_weights_are_rejected(self):
        with self.assertRaises(ValueError):
            dijkstra(self.network, self.start, self.goal, CostWeights(0.0, 0.0, 0.0))

    def test_unknown_blocked_edge_is_reported(self):
        r = a_star(self.network, self.start, self.goal, self.weights, blocked_edges={"NOT_AN_EDGE"})
        self.assertFalse(r.success)
        self.assertIn("Unknown blocked edge", r.message)

if __name__ == "__main__":
    unittest.main()
