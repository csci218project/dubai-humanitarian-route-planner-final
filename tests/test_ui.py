"""Tests for the Streamlit front end (ui package and app.py)."""

from __future__ import annotations

import itertools
import math
import unittest
from pathlib import Path

from humanitarian_route_planner.algorithms import a_star, compare_algorithms
from humanitarian_route_planner.models import CostWeights
from humanitarian_route_planner.network import RouteNetwork
from ui.chart import _ranges, build_route_figure, chart_label, place_labels, schematic_positions

ROOT = Path(__file__).resolve().parents[1]
NETWORK = RouteNetwork.from_json(ROOT / "data" / "sample_network.json")


class SchematicLayoutTests(unittest.TestCase):
    def test_every_hub_gets_a_position(self):
        positions = schematic_positions(NETWORK)
        self.assertEqual(set(positions), set(NETWORK.nodes))

    def test_layout_is_deterministic(self):
        self.assertEqual(schematic_positions(NETWORK), schematic_positions(NETWORK))

    def test_hubs_are_pushed_apart(self):
        positions = schematic_positions(NETWORK, min_gap=0.25)
        closest = min(math.dist(positions[a], positions[b]) for a, b in itertools.combinations(positions, 2))
        self.assertGreater(closest, 0.24)

    def test_west_stays_left_of_east(self):
        positions = schematic_positions(NETWORK)
        self.assertLess(positions["CAIRO_HUB"][0], positions["DUBAI_HUB"][0])


class LabelTests(unittest.TestCase):
    def test_long_names_wrap_onto_two_lines(self):
        self.assertIn("<br>", chart_label("Affected-Area Relief Destination"))
        self.assertEqual(chart_label("Cairo Logistics Hub"), "Cairo Hub")

    def test_every_label_gets_a_valid_side(self):
        positions = schematic_positions(NETWORK)
        labels = {i: chart_label(n.name) for i, n in NETWORK.nodes.items()}
        sides = place_labels(positions, labels, _ranges(positions))
        self.assertEqual(set(sides), set(NETWORK.nodes))
        self.assertTrue(set(sides.values()) <= {"top center", "bottom center", "middle right", "middle left"})


class RouteFigureTests(unittest.TestCase):
    def setUp(self):
        self.positions = schematic_positions(NETWORK)
        self.route = a_star(NETWORK, "DUBAI_HUB", "RELIEF_DESTINATION", CostWeights())

    def clickable_items(self, figure):
        items = set()
        for trace in figure.data:
            for entry in trace.customdata or []:
                items.add((entry[0], entry[1]))
        return items

    def test_every_hub_and_link_is_clickable(self):
        figure = build_route_figure(NETWORK, self.positions, self.route, set(), set(),
                                    "DUBAI_HUB", "RELIEF_DESTINATION")
        items = self.clickable_items(figure)
        self.assertTrue({("node", n) for n in NETWORK.nodes} <= items)
        self.assertTrue({("edge", e) for e in NETWORK.edges} <= items)

    def test_closed_hub_stays_clickable(self):
        figure = build_route_figure(NETWORK, self.positions, self.route, {"CAIRO_HUB"}, set(),
                                    "DUBAI_HUB", "RELIEF_DESTINATION")
        self.assertIn(("node", "CAIRO_HUB"), self.clickable_items(figure))

    def test_before_route_is_drawn_when_given(self):
        closed = {"CAIRO_HUB"}
        after = a_star(NETWORK, "DUBAI_HUB", "RELIEF_DESTINATION", CostWeights(), blocked_nodes=closed)
        figure = build_route_figure(NETWORK, self.positions, after, closed, set(),
                                    "DUBAI_HUB", "RELIEF_DESTINATION", baseline_route=self.route)
        self.assertIn("before", [trace.name for trace in figure.data])

    def test_figure_builds_without_a_route(self):
        figure = build_route_figure(NETWORK, self.positions, None, set(), set(),
                                    "DUBAI_HUB", "RELIEF_DESTINATION")
        self.assertEqual(len(figure.layout.annotations), len(NETWORK.nodes))


class ExtendedNetworkTests(unittest.TestCase):
    def setUp(self):
        self.network = RouteNetwork.from_json(ROOT / "data" / "extended_network.json")

    def test_keeps_every_sample_hub_and_link(self):
        self.assertTrue(set(NETWORK.nodes) <= set(self.network.nodes))
        self.assertTrue(set(NETWORK.edges) <= set(self.network.edges))

    def test_a_star_matches_dijkstra(self):
        results = {r.algorithm: r for r in compare_algorithms(self.network, "DUBAI_HUB", "RELIEF_DESTINATION", CostWeights())}
        self.assertTrue(results["A*"].success)
        self.assertAlmostEqual(results["A*"].objective_score, results["Dijkstra"].objective_score)

    def test_chart_places_every_hub(self):
        self.assertEqual(set(schematic_positions(self.network)), set(self.network.nodes))


class OpeningSequenceTests(unittest.TestCase):
    def test_every_frame_in_the_manifest_exists(self):
        from ui.sequence import SEQUENCE_DIR, load_manifest
        manifest = load_manifest()
        self.assertIsNotNone(manifest)
        for index in range(manifest["count"]):
            self.assertTrue((SEQUENCE_DIR / manifest["pattern"].format(index=index)).exists())

    def test_frames_are_served_from_streamlit_static_folder(self):
        from ui.sequence import frame_urls, load_manifest
        urls = frame_urls(load_manifest())
        self.assertTrue(all(url.startswith("app/static/sequence/") for url in urls))


class AppSmokeTests(unittest.TestCase):
    """Run app.py headlessly with Streamlit's testing harness."""

    def setUp(self):
        from streamlit.testing.v1 import AppTest
        self.app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=300).run()

    def test_app_runs_without_errors(self):
        self.assertFalse(self.app.exception)

    def test_scenario_loads_its_closures(self):
        self.app.selectbox(key="scenario").set_value("Compound disruption").run()
        self.assertEqual(set(self.app.session_state.closed_nodes), {"DWC_AIRPORT", "JEBEL_ALI_PORT"})
        self.assertEqual(self.app.session_state.closed_edges, ["E14_ELARISH_DESTINATION"])
        self.assertFalse(self.app.exception)

    def test_moving_a_slider_clears_the_preset(self):
        self.app.slider(key="w_risk").set_value(4.0).run()
        self.assertIsNone(self.app.session_state.preset)

    def test_closed_origin_offers_a_reopen_button(self):
        self.app.multiselect(key="closed_nodes").set_value(["DUBAI_HUB"]).run()
        self.assertIn("Reopen Dubai Humanitarian Hub", [b.label for b in self.app.button])

    def test_switching_network_resets_the_request(self):
        names = self.app.selectbox(key="network_name").options
        self.app.multiselect(key="closed_nodes").set_value(["CAIRO_HUB"]).run()
        self.app.selectbox(key="network_name").set_value(names[-1]).run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.session_state.closed_nodes, [])
        self.assertEqual(self.app.session_state.origin, "DUBAI_HUB")

    def test_closing_a_hub_runs_the_before_and_after_view(self):
        self.app.multiselect(key="closed_nodes").set_value(["CAIRO_HUB"]).run()
        self.assertFalse(self.app.exception)

    def test_inspector_closes_and_reopens_a_hub(self):
        self.app.session_state["inspected"] = ("node", "CAIRO_HUB")
        self.app.run()
        self.app.button(key="inspector_toggle").click().run()
        self.assertEqual(self.app.session_state.closed_nodes, ["CAIRO_HUB"])
        self.app.button(key="inspector_toggle").click().run()
        self.assertEqual(self.app.session_state.closed_nodes, [])


if __name__ == "__main__":
    unittest.main()
