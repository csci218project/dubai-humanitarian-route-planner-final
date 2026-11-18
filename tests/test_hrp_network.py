"""Tests for the Dubai to El Obeid network (data/hrp_network.json).

Covers what this data needs from the core: one-way legs, the transfer rule for
mode changes, scenario slow-downs and cost shocks, and correct search results
in every scenario.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

from humanitarian_route_planner.algorithms import _heuristic_scale, compare_algorithms, dijkstra
from humanitarian_route_planner.models import CostWeights
from humanitarian_route_planner.network import RouteNetwork, haversine_km

ROOT = Path(__file__).resolve().parents[1]
HRP = RouteNetwork.from_json(ROOT / "data" / "hrp_network.json")
SCENARIOS = {spec["id"]: spec for spec in HRP.metadata["scenarios"]}
PRESETS = {
    "Fastest": CostWeights(5, 0, 0), "Cheapest": CostWeights(0, 5, 0),
    "Safest": CostWeights(0, 0, 5), "Balanced": CostWeights(),
}


def all_routes(start: str = "IHC", goal: str = "ELO") -> list[list[str]]:
    """Every loop-free route from start to goal, as lists of leg IDs."""
    routes: list[list[str]] = []

    def walk(node: str, legs: list[str], visited: set[str]) -> None:
        if node == goal:
            routes.append(legs)
            return
        for nxt, edge in HRP.neighbors(node):
            if nxt not in visited:
                walk(nxt, legs + [edge.edge_id], visited | {nxt})

    walk(start, [], {start})
    return routes


class DataTests(unittest.TestCase):
    def test_counts_and_endpoints(self):
        self.assertEqual((len(HRP.nodes), len(HRP.edges), len(SCENARIOS)), (23, 36, 10))
        self.assertEqual((HRP.metadata["default_origin"], HRP.metadata["default_destination"]), ("IHC", "ELO"))

    def test_legs_are_one_way(self):
        self.assertTrue(HRP.directed)
        self.assertEqual(HRP.neighbors("ELO"), [])
        self.assertEqual({nxt for nxt, _ in HRP.neighbors("IHC")}, {"DWC", "DXB", "JEA"})

    def test_every_hub_is_reachable_from_the_origin(self):
        seen, stack = {"IHC"}, ["IHC"]
        while stack:
            for nxt, _ in HRP.neighbors(stack.pop()):
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        self.assertEqual(seen, set(HRP.nodes))

    def test_json_matches_the_spreadsheet(self):
        if importlib.util.find_spec("openpyxl") is None:
            self.skipTest("openpyxl not installed (pip install -r requirements-dev.txt)")
        sys.path.insert(0, str(ROOT / "scripts"))
        try:
            import import_hrp_data
        finally:
            sys.path.pop(0)
        stored = json.loads((ROOT / "data" / "hrp_network.json").read_text(encoding="utf-8"))
        self.assertEqual(import_hrp_data.build(), stored)


class TransferTests(unittest.TestCase):
    def test_rule_is_the_median_transfer_leg(self):
        self.assertEqual((HRP.transfer.time_hours, HRP.transfer.cost_usd), (3.5, 18.0))

    def test_air_to_road_at_cairo_costs_one_transfer(self):
        # IHC>DWC is a transfer leg, DWC>CAI is air, CAI>ASW is road: one mode change, at Cairo.
        totals = HRP.route_totals(["L01", "L08", "L23"], CostWeights())
        self.assertEqual(totals["transfers"], 1)
        self.assertAlmostEqual(totals["total_time_hours"], 3.5 + 13.4 + 18.2 + 3.5)

    def test_transfer_legs_never_add_a_second_transfer(self):
        self.assertEqual(HRP.route_totals(["L01", "L04", "L27"], CostWeights())["transfers"], 0)

    def test_search_matches_brute_force_with_transfers(self):
        routes = all_routes()
        for name, weights in PRESETS.items():
            best = min(HRP.route_totals(legs, weights)["objective_score"] for legs in routes)
            self.assertAlmostEqual(dijkstra(HRP, "IHC", "ELO", weights).objective_score, best, msg=name)


class ScenarioTests(unittest.TestCase):
    def test_compound_scenario_combines_its_parts(self):
        self.assertEqual(set(SCENARIOS["S9"]["close_edges"]),
                         set(SCENARIOS["S1"]["close_edges"]) | set(SCENARIOS["S2"]["close_edges"]))

    def test_slow_down_multiplies_leg_times(self):
        slow = HRP.with_adjustments(SCENARIOS["S6"]["time_mult"], SCENARIOS["S6"]["cost_mult"])
        self.assertAlmostEqual(slow.edges["L22"].time_hours, HRP.edges["L22"].time_hours * 1.6)
        self.assertAlmostEqual(slow.edges["L22"].time_hours_p90, HRP.edges["L22"].time_hours_p90 * 1.6)
        self.assertEqual(slow.edges["L04"], HRP.edges["L04"])

    def test_cost_shock_multiplies_leg_costs(self):
        dear = HRP.with_adjustments(cost_mult=SCENARIOS["S8"]["cost_mult"])
        self.assertAlmostEqual(dear.edges["L17"].cost_usd, HRP.edges["L17"].cost_usd * 1.8)

    def test_closing_el_obeid_airport_reroutes(self):
        before = dijkstra(HRP, "IHC", "ELO", CostWeights())
        after = dijkstra(HRP, "IHC", "ELO", CostWeights(), blocked_edges=set(SCENARIOS["S5"]["close_edges"]))
        self.assertIn("EBD", before.node_path)
        self.assertTrue(after.success)
        self.assertNotIn("EBD", after.node_path)

    def test_unknown_leg_in_a_scenario_is_rejected(self):
        with self.assertRaises(ValueError):
            HRP.with_adjustments(time_mult={"L99": 2.0})


class SearchTests(unittest.TestCase):
    def test_a_star_matches_dijkstra_in_every_scenario(self):
        for spec in SCENARIOS.values():
            network = HRP.with_adjustments(spec["time_mult"], spec["cost_mult"])
            for name, weights in PRESETS.items():
                results = {r.algorithm: r for r in compare_algorithms(
                    network, "IHC", "ELO", weights, blocked_edges=set(spec["close_edges"]))}
                dij, ast = results["Dijkstra"], results["A*"]
                self.assertEqual(dij.success, ast.success, msg=f"{spec['id']} {name}")
                if dij.success:
                    self.assertAlmostEqual(dij.objective_score, ast.objective_score, msg=f"{spec['id']} {name}")

    def test_heuristic_never_overestimates(self):
        for name, weights in PRESETS.items():
            scale = _heuristic_scale(HRP, weights, set(), set())
            for node_id in HRP.nodes:
                if node_id == "ELO":
                    continue
                route = dijkstra(HRP, node_id, "ELO", weights)
                if route.success:
                    estimate = scale * haversine_km(HRP.nodes[node_id], HRP.nodes["ELO"])
                    self.assertLessEqual(estimate, route.objective_score + 1e-9, msg=f"{name} {node_id}")

    def test_hierarchical_search_finds_a_route(self):
        self.assertTrue(compare_algorithms(HRP, "IHC", "ELO", CostWeights())[2].success)


if __name__ == "__main__":
    unittest.main()
