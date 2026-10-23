"""Network validation and metric aggregation tests."""
from pathlib import Path
import unittest
from humanitarian_route_planner.models import CostWeights, Edge, Node
from humanitarian_route_planner.network import RouteNetwork, haversine_km
ROOT = Path(__file__).resolve().parents[1]

class NetworkTests(unittest.TestCase):
    def test_sample_network_loads(self):
        n = RouteNetwork.from_json(ROOT / "data" / "sample_network.json")
        self.assertEqual(len(n.nodes), 10)
        self.assertEqual(len(n.edges), 15)

    def test_neighbors_respect_blocked_edge_and_node(self):
        n = RouteNetwork.from_json(ROOT / "data" / "sample_network.json")
        self.assertEqual(len(n.neighbors("DUBAI_HUB")), 3)
        self.assertEqual(len(n.neighbors("DUBAI_HUB", blocked_edges={"E01_DUBAI_DWC"})), 2)
        self.assertEqual(len(n.neighbors("DUBAI_HUB", blocked_nodes={"DWC_AIRPORT"})), 2)

    def test_haversine_zero_for_same_node(self):
        n = RouteNetwork.from_json(ROOT / "data" / "sample_network.json")
        self.assertAlmostEqual(haversine_km(n.nodes["DUBAI_HUB"], n.nodes["DUBAI_HUB"]), 0.0)

    def test_route_totals_add_metrics(self):
        n = RouteNetwork.from_json(ROOT / "data" / "sample_network.json")
        w = CostWeights(time=1.0, cost=0.75, risk=2.0)
        totals = n.route_totals(["E01_DUBAI_DWC", "E04_DWC_JEDDAH_AIR"], w)
        self.assertAlmostEqual(totals["total_time_hours"], 4.2)
        self.assertAlmostEqual(totals["total_cost_usd"], 18620)
        self.assertAlmostEqual(totals["total_risk_points"], 3.0)
        self.assertAlmostEqual(totals["objective_score"], 4.2 + 0.75 * 18.62 + 2 * 3.0)

    def test_duplicate_node_ids_are_rejected(self):
        a1 = Node("A", "A one", 0, 0, "R1", "hub")
        a2 = Node("A", "A two", 0, 1, "R1", "hub")
        with self.assertRaises(ValueError):
            RouteNetwork([a1, a2], [])

    def test_duplicate_edge_ids_are_rejected(self):
        nodes = [Node("A", "A", 0, 0, "R1", "hub"), Node("B", "B", 1, 1, "R1", "hub")]
        e1 = Edge("E", "A", "B", "road", 1, 1, 1, 1)
        e2 = Edge("E", "A", "B", "air", 2, 2, 2, 2)
        with self.assertRaises(ValueError):
            RouteNetwork(nodes, [e1, e2])

    def test_invalid_edge_endpoint_rejected(self):
        nodes = [Node("A", "A", 0, 0, "R1", "hub")]
        edges = [Edge("E", "A", "MISSING", "road", 1, 1, 1, 1)]
        with self.assertRaises(ValueError):
            RouteNetwork(nodes, edges)

    def test_invalid_risk_value_rejected(self):
        nodes = [Node("A", "A", 0, 0, "R1", "hub"), Node("B", "B", 1, 1, "R1", "hub")]
        edges = [Edge("E", "A", "B", "road", 1, 1, 11, 1)]
        with self.assertRaises(ValueError):
            RouteNetwork(nodes, edges)

if __name__ == "__main__":
    unittest.main()
